import sys
import os
import json
from base64 import b64encode, urlsafe_b64encode

import foursquare
import six
from fuzzywuzzy import process

from google_language import GoogleLanguage
from fscred import CLIENT_ID, CLIENT_SECRET
from dishstars_firebase import DishstarsFirebase



class GeoDish:

	def __init__(self, minSentimentScore=0.2, minFuzzyDishMatchingScore=90):
		"""Initialize the Geodish object

		minSentiment score is the minumum score for an entity to be
		considered to have positive sentiment: Range is from -1 to +1.

		minFuzzyDishMatchingScore is the minimum score for success when
		matching entities from tip text to menu items: Range is from 0 to 100.
		"""
		self.fsClient = foursquare.Foursquare(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
		self.fsExploreParams = {'section': 'food', 'limit': 500, 'openNow': 0}
		self.googleLanguage = GoogleLanguage()
		self.foursquareApiCallCount = 0
		self.googleApiCallCount = 0
		self.cache = Cache()
		self.minSentimentScore = minSentimentScore
		self.minFuzzyDishMatchingScore = minFuzzyDishMatchingScore


	def processLocation(self, nearLocation):
		"""All steps to find and save top dishes for a location."""
		print "getting dishes"
		self.getDishes(nearLocation)
		print "analyzing entity sentiment"
		self.entitySentimentAnalysis()
		print "finding top dishes"
		self.findTopDishes()
		print "saving"
		self.savePopularDishes(self.locationId(), self.topDishes)


	def getDishes(self, nearLocation):
		"""Get restaurants, menus and tips from Foursquare"""
		self.location = nearLocation
		updatedVenues = []
		venues = self.getRestaurants(nearLocation)
		for venue in venues:
			dishes = self.getDishesFromMenu(venue)
			# only get tips if there are dishes for this restaurant
			if len(dishes) > 0:
				tips = self.getTips(venue)
				venue.update({u'dishes': dishes, u'tips': tips})
				updatedVenues.append(venue)

		self.venues = {}
		for venue in updatedVenues:
			self.venues.update({venue['id']: venue})


	def entitySentimentAnalysis(self):
		"""Run entity sentiment analysis for each venue."""
		for venue in self.venues.values():
			venue['entitySentiment'] = self.analyzeReviewSentiment(venue)


	def findTopDishes(self):
		"""Find top dishes for each venue and then use these to find top
		dishes overall for the location.
		"""
		n = len(self.venues)
		for i, venue in enumerate(self.venues.values()):
			print "%s/%s %s" % (i, n, venue['name'])
			topDishes = self.findTopDishesForVenue(venue)
			if topDishes is not None:
				venue['topDishes'] = topDishes
			else:
				venue['topDishes'] = []

		self.findTopDishesForLocation()


	def save(self):
		"""Save loaded venue information for the location to a json file."""
		fname = 'saved_locations/%s.json' % self.location
		f = open(fname, 'wb')
		json.dump(self.venues, f)
		f.close()


	def load(self, location):
		"""Load venue information for location from json file (must exist)"""
		self.location = location
		fname = 'saved_locations/%s.json' % self.location
		f = open(fname, 'rb')
		self.venues = json.load(f)
		f.close()


	def getRestaurants(self, nearLocation):
		"""Get restaurants from Foursquare.
		Returns only restaurants with menu data available.
		"""
		items = self.foursquareExplore(nearLocation)

		venuesWithMenus = []
		for item in items:
			venue = item['venue']
			if u'hasMenu' in venue:
				venuesWithMenus.append(venue)

		return venuesWithMenus


	def foursquareExplore(self, nearLocation):
		"""Query the Foursquare Explore API for venues."""
		params = self.fsExploreParams
		params.update({'near': nearLocation})

		r = self.fsClient.venues.explore(params=params)
		self.foursquareApiCallCount += 1
		# save the geocode info which has the proper location info.
		self.geocode = r['geocode']

		return r['groups'][0]['items']



	def getDishesFromMenu(self, venue):
		"""Get menu data from Foursquare."""
		
		# check if menu in cache
		menu = self.cache.readMenu(venue['id'])

		if menu is None:
			menu = self.fsClient.venues.menu(venue['id'])
			self.foursquareApiCallCount += 1
			# cache the menu
			self.cache.writeMenu(venue['id'], menu)
		dishes = self.parseMenu(menu)
		return dishes

	def parseMenu(self, menuDict):
		"""Parse the json menu data received from Foursquare and return
		a list of menu items.
		"""
		
		menuItems = []

		def getMenuItem(d, sectionPath=""):
			"""Recursuve function to parse json menu data"""

			if 'menuId' in d or 'sectionId' in d:
				# this node is a menu or section header
				if 'name' in d:
					# add section header to the current section path
					if sectionPath != "":
						sectionPath += " | %s" % d['name']
					else:
						sectionPath = d['name']
				try:
					if d['entries']['count'] > 0:
						for item in d['entries']['items']:
							getMenuItem(item, sectionPath=sectionPath)
				except:
					print d
					raise
			elif 'entryId' in d:
				menuItem = {}
				menuItem['name'] = d['name']
				menuItem['menuSection'] = sectionPath
				if 'description' in d:
					menuItem['description'] = d['description']
				if 'price' in d:
					menuItem['price'] = d['price']
				menuItems.append(menuItem)


		try:
			if menuDict['menu']['menus']['count'] > 0:
				for menu in menuDict['menu']['menus']['items']:
					getMenuItem(menu)
		except:
			raise
			# return []

		return menuItems



	def getTips(self, venue):
		"""Get tips for venue from Foursquare."""
		
		# check cache
		tips = self.cache.readTips(venue['id'])

		if tips is None:
			r = self.fsClient.venues.tips(venue['id'], params={'limit': 500})
			self.foursquareApiCallCount += 1
			tips = r['tips']['items']

			# cache the tips
			self.cache.writeTips(venue['id'], tips)

		return tips


	def createTipOffsetLookup(self, tips):
		"""Create a list with cumulative sum of tip lengths."""
		lenSum = [len(tips[0]['text'])]
		if len(tips) > 1:
			for tip in tips[1:]:
				lenSum.append(lenSum[-1] + len(tip['text']))

		return lenSum

	
	def tipIndexFromOffset(self, offsetLookup, offset):
		"""Returns the tip index that contains the offset vale.
		Requires a precomputed offsetLookup.
		"""
		if len(offsetLookup) == 1:
			return 0

		if offset > offsetLookup[-2]:
			# it's the last index
			return len(offsetLookup) - 1
		else:
			return map(lambda x: x < offset, offsetLookup).index(False)


	def tipText(self, tips):
		"""Returns a string containing the concatenated text from all the
		tips, separated by a newline character.
		"""
		text = u''
		for tip in tips:
			text += tip['text'] + "\n"

		return text


	def analyzeReviewSentiment(self, venue):
		"""Get entity sentiment analysis results for a venue's tips"""
		
		# check cache
		entitySentiment = self.cache.readEntity(venue['id'])

		if entitySentiment is None:
			tipText = self.tipText(venue['tips'])
			result = self.googleLanguage.analyzeEntitySentiment(tipText)
			entitySentiment = self.reformatEntitySentimentObject(result, venue['tips'])

			# cache entity sentiment results
			self.cache.writeEntity(venue['id'], entitySentiment)

		return entitySentiment

	def reformatEntitySentimentObject(self, rawEntitySentimentObject, tips):
		"""Prepare the entity sentiment data."""
		r = []
		for entity in rawEntitySentimentObject:
			d = {}
			d['name'] = entity['name']
			d['salience'] = entity['salience']
			d['score'] = entity['sentiment']['score']
			d['magnitude'] = entity['sentiment']['magnitude']
			# get the tips associated with each entity
			d['dishTips'] = self.tipsForDish(entity['mentions'], tips)
			r.append(d)

		return r

	def tipIndexForMention(self, mentions, tips):
		"""Find the index of the tip associated with each of the mentions
		obtained from sentiment analysis.
		"""
		offsetLookup = self.createTipOffsetLookup(tips)
		tipIndex = []
		for mention in mentions:
			tipIndex.append(self.tipIndexFromOffset(offsetLookup, mention['text']['beginOffset']))

		return tipIndex

	def tipsForDish(self, mentions, tips):
		"""Get the tips associated with each mention."""
		tipIndex = self.tipIndexForMention(mentions, tips)
		dishTips = []
		for i in tipIndex:
			tip = {'tipIndex': i, 'user': tips[i]['user']['id'], 'text':tips[i]['text']}
			dishTips.append(tip)

		return dishTips


	def findTopDishesForVenue(self, venue, debug=False):
		"""Find the dishes with the most positive mentions for this venue"""
		try:
			if len(venue['entitySentiment']) == 0:
				# No positive mentions
				venue['topDishes'] = []
				return

			entities = venue['entitySentiment']
			dishes = venue['dishes']

			dishLookup = {}
			for dish in dishes:
				# Create a dish lookup hash
				dishLookup[dish['name']] = dish

			# Ensure no missing attributes
			for dish in dishes:
				if 'price' not in dish:
					dish['price'] = None
				if 'description' not in dish:
					dish['description'] = None

			# filter out entities with negative or neutral sentiment
			posEntities = []
			for entity in entities:
				if entity['score'] > self.minSentimentScore:
					entity['compositeScore'] = 1
					posEntities.append(entity)

			dishNames = [dish['name'] for dish in dishes]
			posNames = [entity['name'] for entity in posEntities]

			# Fuzzy string matching to find the best matching dish item for each entity
			dishMatch = map(lambda x: process.extractOne(x, dishNames), posNames)

			# Find all the dish names that meet minimum matching criteria
			highMatch = []
			for i, entity in enumerate(posEntities):
				if dishMatch[i][1] >= self.minFuzzyDishMatchingScore:
					entity['dish'] = dishMatch[i][0]
					entity['matchScore'] = dishMatch[i][1]
					highMatch.append(entity)

			# Aggregate the score for each of the top dishes.
			topDishes = {}
			for entity in highMatch:
				if entity['dish'] in topDishes:
					topDishes[entity['dish']]['compositeScore'] += entity['compositeScore']
					topDishes[entity['dish']]['dishTips'] += entity['dishTips']
				else:
					topDishes[entity['dish']] = entity

			# Add some details to the top dish items.
			for dish in topDishes.values():
				info = dishLookup[dish['dish']]
				dish['price'] = info['price']
				dish['description'] = info['description']
				dish['venueId'] = venue['id']
				dish['venueName'] = venue['name']
				dish['location'] = venue['location']
				dish['categories'] = venue['categories']

			topDishes = topDishes.values()

		except:
			raise
			return []

		if topDishes is None:
			return []

		return topDishes


	def findTopDishesForLocation(self):
		"""Get a list of top dishes from all venues."""
		topDishes = []
		for venue in self.venues.values():
			topDishes += venue['topDishes']

		# sort by composite score
		topDishes = sorted(topDishes, key=lambda k: k['compositeScore'], reverse=True)

		self.topDishes = topDishes


	def locationString(self):
		"""Return the geocoded location as a string"""
		try:
			return self.geocode['displayString']
		except:
			return u''

	def locationId(self):
		"""Return the id of the location"""
		return urlsafe_b64encode(self.locationString().encode('utf8'))


	def savePopularDishes(self, locationId, dishes):
		self.cache.writePopularDishes(locationId, dishes)

	def loadPopularDishes(self, locationId):
		dishes = self.cache.readPopularDishes(locationId)
		if dishes is None:
			return {}
		return dishes

	def locationHasCachedDishes(self, locationId):
		return self.cache.locationHasCachedDishes(locationId)

	def pushQueueData(self, data):
		return self.cache.pushQueueData(data)

	def pullQueueData(self, key):
		return self.cache.pullQueueData(key)

	def saveUserDishList(self, data):
		return self.cache.saveUserDishList(data)

	def loadUserDishList(self, key):
		return self.cache.loadUserDishList(key)

	def loadUserRecommended(self, key):
		return self.cache.loadUserRecommended(key)





class Cache:

	def __init__(self):
		self.dishfire = DishstarsFirebase()

	def readTips(self, venueId):
		r = self.dishfire.readFoursquareTips(venueId)
		if r is not None:
			if 'tips' in r:
				r = r['tips']
			else:
				r = []
		return r

	def readMenu(self, venueId):
		return self.dishfire.readFoursquareMenu(venueId)

	def readEntity(self, venueId):
		r = self.dishfire.readGoogleNLPEntitySentiment(venueId)
		if r is not None:
			if 'entities' in r:
				r = r['entities']
			else:
				r= []
		return r

	def writeTips(self, venueId, data):
		return self.dishfire.writeFoursquareTips(venueId, {'tips': data})

	def writeMenu(self, venueId, data):
		return self.dishfire.writeFoursquareMenu(venueId, data)

	def writeEntity(self, venueId, data):
		return self.dishfire.writeGoogleNLPEntitySentiment(venueId, {'entities': data})


	def readPopularDishes(self, locationId):
		r = self.dishfire.readPopularDishes(locationId)
		if r is not None:
			r = r['dishes']
			if 'timestamp' in r:
				del r['timestamp']
		return r

	def locationHasCachedDishes(self, locationId):
		r = self.dishfire.readLocationCacheTimestamp(locationId)
		if r is None:
			return False
		return True


	def writePopularDishes(self, locationId, dishes):
		return self.dishfire.writePopularDishes(locationId, dishes)



	def pushQueueData(self, data):
		return self.dishfire.pushQueueData(data)

	def pullQueueData(self, key):
		return self.dishfire.pullQueueData(key)


	def saveUserDishList(self, data):
		return self.dishfire.writeSavedDishList(data)

	def loadUserDishList(self, key):
		r = self.dishfire.readSavedDishList(key)
		if r is not None:
			if 'timestamp' in r:
				del r['timestamp']
		return r

	def loadUserRecommended(self, key):
		r = self.dishfire.readUserRecommended(key)
		if r is not None:
			if 'timestamp' in r:
				del r['timestamp']
		return r






