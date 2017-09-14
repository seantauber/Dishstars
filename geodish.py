import sys, os
import json
import foursquare
from fscred import CLIENT_ID, CLIENT_SECRET

import six
from google.cloud import language_v1beta2
from google.cloud.language_v1beta2 import enums
from google.cloud.language_v1beta2 import types

import pandas as pd
from fuzzywuzzy import process


class GeoDish:

	def __init__(self):
		self.fsClient = foursquare.Foursquare(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
		self.fsExploreParams = {'section': 'food', 'limit': 500, 'openNow': 0}
		self.apiCallCount = 0


	def getDishes(self, nearLocation):
		'''
		'''
		self.location = nearLocation
		updatedVenues = []
		venues = self.getRestaurants(nearLocation)
		for venue in venues:
			dishes = self.getMenu(venue)
			if len(dishes) > 0:
				tips = self.getTips(venue)
				venue.update({u'dishes': dishes, u'tips': tips})
				updatedVenues.append(venue)

		self.venues = {}
		for venue in updatedVenues:
			self.venues.update({venue['id']: venue})


	def entitySentimentAnalysis(self):
		'''
		'''
		for venue in self.venues.values():
			self.analyzeReviewSentiment(venue)


	def findTopDishes(self):
		'''
		'''
		n = len(self.venues)
		for i, venue in enumerate(self.venues.values()):
			print "%s/%s %s" % (i, n, venue['name'])
			self.findTopDishesForVenue(venue)

		self.findTopDishesForLocation()


	def save(self):
		'''
		'''
		fname = 'saved_locations/%s.json' % self.location
		f = open(fname, 'wb')
		json.dump(self.venues, f)
		f.close()


	def load(self, location):
		'''
		'''
		self.location = location
		fname = 'saved_locations/%s.json' % self.location
		f = open(fname, 'rb')
		self.venues = json.load(f)
		f.close()


	def getRestaurants(self, nearLocation):
		'''
		'''
		items = foursquareExplore(nearLocation)

		venuesWithMenus = []
		for item in items:
			venue = item['venue']
			if u'hasMenu' in venue:
				venuesWithMenus.append(venue)

		return venuesWithMenus


	def foursquareExplore(self, nearLocation):
		'''
		'''
		params = self.fsExploreParams
		params.update({'near': nearLocation})

		r = self.fsClient.venues.explore(params=params)
		self.geocode = r['geocode']

		return r['groups'][0]['items']



	def getMenu(self, venue):
		'''
		'''
		# check cache
		cachedPath = 'cache/menu/%s' % venue['id']
		if os.path.isfile(cachedPath):
			# get menu from cache
			f = open(cachedPath, 'rb')
			menu = json.load(f)
			f.close()
		else:
			menu = self.fsClient.venues.menu(venue['id'])
			# cache the menu
			f = open(cachedPath, 'wb')
			json.dump(menu, f)
			f.close()
		menu = self.parseMenu(menu)
		return menu

	def parseMenu(self, menuDict):
		'''
		'''
		
		menuItems = []

		def getMenuItem(d, sectionPath=""):
			if 'menuId' in d or 'sectionId' in d:
				if 'name' in d:
					if sectionPath != "":
						sectionPath += " | %s" % d['name']
					else:
						sectionPath = d['name']
				for item in d['entries']['items']:
					getMenuItem(item, sectionPath=sectionPath)
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
		'''
		'''
		# check cache
		cachedPath = 'cache/tips/%s' % venue['id']
		if os.path.isfile(cachedPath):
			# get cached tips
			f = open(cachedPath, 'rb')
			tips = json.load(f)
			f.close()
		
		else:
			r = self.fsClient.venues.tips(venue['id'], params={'limit': 500})
			tips = r['tips']['items']

			# cache the tips
			f = open(cachedPath, 'wb')
			json.dump(tips, f)
			f.close()

		return tips

	def tipText(self, tips):
		'''
		'''
		text = u''
		for tip in tips:
			text += tip['text'] + "\n"

		return text


	def analyzeReviewSentiment(self, venue):
		'''
		'''
		# check cache
		cachedPath = 'cache/entity/%s' % venue['id']
		if os.path.isfile(cachedPath):
			# get cached entities
			f = open(cachedPath, 'rb')
			entitySentiment = json.load(f)
			f.close()
			venue['entitySentiment'] = entitySentiment
		else:
			tipText = self.tipText(venue['tips'])
			result = self.entitySentimentText(tipText)
			venue['entitySentiment'] = self.entitySentimentResultToJsonCompatible(result)

			# cache entity sentiment results
			f = open(cachedPath, 'wb')
			json.dump(venue['entitySentiment'], f)
			f.close()



	def entitySentimentText(self, text, verbose=False):
		"""Detects entity sentiment in the provided text."""
		client = language_v1beta2.LanguageServiceClient()

		if isinstance(text, six.binary_type):
			text = text.decode('utf-8')

		document = types.Document(
			content=text.encode('utf-8'),
			language='en',
			type=enums.Document.Type.PLAIN_TEXT)

		# Pass in encoding type to get useful offsets in the response.
		encoding = enums.EncodingType.UTF32
		if sys.maxunicode == 65535:
			encoding = enums.EncodingType.UTF16

		result = client.analyze_entity_sentiment(document, encoding)

		if verbose:
			for entity in result.entities:
				print('Mentions: ')
				print(u'Name: "{}"'.format(entity.name))
				for mention in entity.mentions:
					print(u'  Begin Offset : {}'.format(mention.text.begin_offset))
					print(u'  Content : {}'.format(mention.text.content))
					print(u'  Magnitude : {}'.format(mention.sentiment.magnitude))
					print(u'  Sentiment : {}'.format(mention.sentiment.score))
					print(u'  Type : {}'.format(mention.type))
				print(u'Salience: {}'.format(entity.salience))
				print(u'Sentiment: {}\n'.format(entity.sentiment))

		return result


	def entitySentimentResultToJsonCompatible(self, result):
		'''
		'''
		r = []
		for entity in result.entities:
			d = {}
			d['name'] = entity.name
			d['salience'] = entity.salience
			d['score'] = entity.sentiment.score
			d['magnitude'] = entity.sentiment.magnitude
			d['mentions'] = []
			for mention in entity.mentions:
				m = {}
				m['beginOffset'] = mention.text.begin_offset
				m['content'] = mention.text.content
				m['magnitude'] = mention.sentiment.magnitude
				m['sentiment'] = mention.sentiment.score
				m['type'] = mention.type
				d['mentions'].append(m)
			r.append(d)

		return r



	def printEntitySentimentResult(self, result):
		'''
		'''
		for entity in result.entities:
			print('Mentions: ')
			print(u'Name: "{}"'.format(entity.name))
			for mention in entity.mentions:
				print(u'  Begin Offset : {}'.format(mention.text.begin_offset))
				print(u'  Content : {}'.format(mention.text.content))
				print(u'  Magnitude : {}'.format(mention.sentiment.magnitude))
				print(u'  Sentiment : {}'.format(mention.sentiment.score))
				print(u'  Type : {}'.format(mention.type))
			print(u'Salience: {}'.format(entity.salience))
			print(u'Sentiment: {}\n'.format(entity.sentiment))



	def findTopDishesForVenue(self, venue, debug=False):
		'''
		'''

		try:
			if len(venue['entitySentiment']) == 0:
				venue['topDishes'] = []
				return

			df = pd.DataFrame(venue['entitySentiment'], columns=['name','score','magnitude'])
			dishDf = pd.DataFrame(venue['dishes'])
			if 'price' not in dishDf.columns:
				dishDf['price'] = None
			if 'description' not in dishDf.columns:
				dishDf['description'] = None
			
			# filter out entities with negative or neutral sentiment
			df = df[df.score >= .2]
			df['compositeScore'] = df.score * df.magnitude


			# Fuzzy string matching to find the best matching dish item for each entity
			dishMatch = df.apply(lambda x: process.extractOne(x['name'], dishDf.name), axis=1)

			df['dish'] = [result[0] for result in dishMatch]
			df['matchScore'] = [result[1] for result in dishMatch]

			# filter out low match scores
			df = df[df.matchScore >= 90]

			if debug:
				print df
				print


			# Group by dish and combine the score
			topDishes = df.groupby('dish').compositeScore.sum().to_frame().reset_index()

			if len(topDishes):

				if debug:
					print topDishes

				topDishes['price'] = [dishDf[dishDf.name==topDish].price.values[0] for topDish in topDishes.dish]
				topDishes['description'] = [dishDf[dishDf.name==topDish].description.values[0] for topDish in topDishes.dish]

				topDishes['venueId'] = venue['id']

				venue['topDishes'] = topDishes.to_dict(orient='records')

			else:
				venue['topDishes'] = []

		except:
			venue['topDishes'] = []



	def findTopDishesForLocation(self):
		'''
		'''
		# get a list of top dishes from all venues
		topDishes = []
		for venue in self.venues.values():
			topDishes += venue['topDishes']

		# sort by composite score
		topDishes = sorted(topDishes, key=lambda k: k['compositeScore'], reverse=True)

		for dish in topDishes:
			venueId = dish['venueId']
			dish['venueName'] = self.venues[venueId]['name']
			if 'location' in self.venues[venueId]:
				dish['location'] = self.venues[venueId]['location']
			if 'categories' in self.venues[venueId]:
				dish['venueCategories'] = self.venues[venueId]['categories']
			if 'url' in self.venues[venueId]:
				dish['venueUrl'] = self.venues[venueId]['url']
			if 'contact' in self.venues[venueId]:
				dish['contact'] = self.venues[venueId]['contact']

		self.topDishes = topDishes


	def locationString(self):
		try:
			return self.geocode['displayString']
		except:
			return u''











