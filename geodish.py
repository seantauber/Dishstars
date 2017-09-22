import sys, os
import json
import foursquare
from fscred import CLIENT_ID, CLIENT_SECRET
from base64 import b64encode, urlsafe_b64encode
import six
from google_language import GoogleLanguage
from fuzzywuzzy import process
from dishstars_firebase import DishstarsFirebase



class GeoDish:

	def __init__(self):
		self.fsClient = foursquare.Foursquare(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
		self.fsExploreParams = {'section': 'food', 'limit': 500, 'openNow': 0}
		self.googleLanguage = GoogleLanguage()
		self.foursquareApiCallCount = 0
		self.googleApiCallCount = 0
		self.cache = Cache()


	def processLocation(self, nearLocation):
		'''
		'''
		print "getting dishes"
		self.getDishes('nearLocation')
		print "analyzing entity sentiment"
		self.entitySentimentAnalysis()
		print "finding top dishes"
		self.findTopDishes()
		print "saving"
		self.savePopularDishes(self.locationId(), self.topDishes)


	def getDishes(self, nearLocation):
		'''
		'''
		self.location = nearLocation
		updatedVenues = []
		venues = self.getRestaurants(nearLocation)
		for venue in venues:
			dishes = self.getDishesFromMenu(venue)
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
			venue['entitySentiment'] = self.analyzeReviewSentiment(venue)


	def findTopDishes(self):
		'''
		'''
		n = len(self.venues)
		for i, venue in enumerate(self.venues.values()):
			print "%s/%s %s" % (i, n, venue['name'])
			topDishes = self.findTopDishesForVenue(venue)
			venue['topDishes'] = topDishes

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
		items = self.foursquareExplore(nearLocation)

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
		self.foursquareApiCallCount += 1
		self.geocode = r['geocode']

		return r['groups'][0]['items']



	def getDishesFromMenu(self, venue):
		'''
		'''
		# check cache
		menu = self.cache.readMenu(venue['id'])

		if menu is None:
			menu = self.fsClient.venues.menu(venue['id'])
			self.foursquareApiCallCount += 1
			# cache the menu
			self.cache.writeMenu(venue['id'], menu)
		dishes = self.parseMenu(menu)
		return dishes

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
		'''
		'''
		# check cache
		tips = self.cache.readTips(venue['id'])

		if tips is None:
			r = self.fsClient.venues.tips(venue['id'], params={'limit': 500})
			self.foursquareApiCallCount += 1
			tips = r['tips']['items']

			# cache the tips
			self.cache.writeTips(venue['id'], tips)

		self.createTipIndex(tips)

		return tips


	def createTipIndex(self, tips):
		'''
		'''

		lenSum = [len(tips[0]['text'])]
		for tip in tips[1:]:
			lenSum.append(lenSum[-1] + len(tip['text']))

		self.tipLengthSum = lenSum

	
	def tipIndexFromOffset(self, offset):
		'''
		'''
		if offset > self.tipLengthSum[-2]:
			# it's the last index
			return len(self.tipLengthSum) - 1
		else:
			return map(lambda x: x < offset, self.tipLengthSum).index(False)


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
		entitySentiment = self.cache.readEntity(venue['id'])

		if entitySentiment is None:
			tipText = self.tipText(venue['tips'])
			# result = self.entitySentimentText(tipText)
			# entitySentiment = self.entitySentimentResultToJsonCompatible(result)
			result = self.googleLanguage.analyzeEntitySentiment(tipText)
			entitySentiment = self.reformatEntitySentimentObject(result)

			# cache entity sentiment results
			self.cache.writeEntity(venue['id'], entitySentiment)

		return entitySentiment



	# def entitySentimentText(self, text, verbose=False):
	# 	"""Detects entity sentiment in the provided text."""
	# 	client = language_v1beta2.LanguageServiceClient()

	# 	if isinstance(text, six.binary_type):
	# 		text = text.decode('utf-8')

	# 	document = types.Document(
	# 		content=text.encode('utf-8'),
	# 		language='en',
	# 		type=enums.Document.Type.PLAIN_TEXT)

	# 	# Pass in encoding type to get useful offsets in the response.
	# 	encoding = enums.EncodingType.UTF32
	# 	if sys.maxunicode == 65535:
	# 		encoding = enums.EncodingType.UTF16

	# 	result = client.analyze_entity_sentiment(document, encoding)
	# 	self.googleApiCallCount += 1

	# 	if verbose:
	# 		for entity in result.entities:
	# 			print('Mentions: ')
	# 			print(u'Name: "{}"'.format(entity.name))
	# 			for mention in entity.mentions:
	# 				print(u'  Begin Offset : {}'.format(mention.text.begin_offset))
	# 				print(u'  Content : {}'.format(mention.text.content))
	# 				print(u'  Magnitude : {}'.format(mention.sentiment.magnitude))
	# 				print(u'  Sentiment : {}'.format(mention.sentiment.score))
	# 				print(u'  Type : {}'.format(mention.type))
	# 			print(u'Salience: {}'.format(entity.salience))
	# 			print(u'Sentiment: {}\n'.format(entity.sentiment))

	# 	return result


	# def entitySentimentResultToJsonCompatible(self, result):
	# 	'''
	# 	'''
	# 	r = []
	# 	for entity in result.entities:
	# 		d = {}
	# 		d['name'] = entity.name
	# 		d['salience'] = entity.salience
	# 		d['score'] = entity.sentiment.score
	# 		d['magnitude'] = entity.sentiment.magnitude
	# 		d['mentions'] = []
	# 		for mention in entity.mentions:
	# 			m = {}
	# 			m['beginOffset'] = mention.text.begin_offset
	# 			m['content'] = mention.text.content
	# 			m['magnitude'] = mention.sentiment.magnitude
	# 			m['sentiment'] = mention.sentiment.score
	# 			m['type'] = mention.type
	# 			d['mentions'].append(m)
	# 		r.append(d)

	# 	return r

	def reformatEntitySentimentObject(self, rawEntitySentimentObject):
		'''
		'''
		r = []
		for entity in rawEntitySentimentObject:
			d = {}
			d['name'] = entity['name']
			d['salience'] = entity['salience']
			d['score'] = entity['sentiment']['score']
			d['magnitude'] = entity['sentiment']['magnitude']
			d['tipIndex'] = self.tipIndexForMention(entity['mentions'])

			# d['mentions'] = []
			# for mention in entity['mentions']:
			# 	m = {}
			# 	m['beginOffset'] = mention['text']['beginOffset']
			# 	m['content'] = mention['text']['content']
			# 	m['magnitude'] = mention['sentiment']['magnitude']
			# 	m['sentiment'] = mention['sentiment']['score']
			# 	m['type'] = mention['type']
			# 	d['mentions'].append(m)

			r.append(d)

		return r

	def tipIndexForMention(self, mentions):
		'''
		'''
		tipIndex = []
		for mention in mentions:
			tipIndex.append(self.tipIndexFromOffset(mention['text']['beginOffset']))

		return tipIndex



	# def printEntitySentimentResult(self, result):
	# 	'''
	# 	'''
	# 	for entity in result.entities:
	# 		print('Mentions: ')
	# 		print(u'Name: "{}"'.format(entity.name))
	# 		for mention in entity.mentions:
	# 			print(u'  Begin Offset : {}'.format(mention.text.begin_offset))
	# 			print(u'  Content : {}'.format(mention.text.content))
	# 			print(u'  Magnitude : {}'.format(mention.sentiment.magnitude))
	# 			print(u'  Sentiment : {}'.format(mention.sentiment.score))
	# 			print(u'  Type : {}'.format(mention.type))
	# 		print(u'Salience: {}'.format(entity.salience))
	# 		print(u'Sentiment: {}\n'.format(entity.sentiment))



	def findTopDishesForVenue(self, venue, debug=False):
		'''
		'''

		try:
			if len(venue['entitySentiment']) == 0:
				venue['topDishes'] = []
				return

			entities = venue['entitySentiment']
			dishes = venue['dishes']

			dishLookup = {}
			for dish in dishes:
				dishLookup[dish['name']] = dish

			for dish in dishes:
				if 'price' not in dish:
					dish['price'] = None
				if 'description' not in dish:
					dish['description'] = None

			# filter out entities with negative or neutral sentiment
			posEntities = []
			for entity in entities:
				if entity['score'] > 0.2:
					# entity['compositeScore'] = entity['score'] * entity['magnitude']
					entity['compositeScore'] = 1
					posEntities.append(entity)

			dishNames = [dish['name'] for dish in dishes]
			posNames = [entity['name'] for entity in posEntities]

			# Fuzzy string matching to find the best matching dish item for each entity
			dishMatch = map(lambda x: process.extractOne(x, dishNames), posNames)

			highMatch = []
			for i, entity in enumerate(posEntities):
				if dishMatch[i][1] >= 90:
					entity['dish'] = dishMatch[i][0]
					entity['matchScore'] = dishMatch[i][1]
					highMatch.append(entity)

			topDishes = {}
			for entity in highMatch:
				if entity['dish'] in topDishes:
					topDishes[entity['dish']]['compositeScore'] += entity['compositeScore']
				else:
					topDishes[entity['dish']] = entity

			for dish in topDishes.values():
				info = dishLookup[dish['dish']]
				dish['price'] = info['price']
				dish['description'] = info['description']
				dish['venueId'] = venue['id']
				dish['venueName'] = venue['name']
				dish['location'] = venue['location']
				dish['categories'] = venue['categories']

			topDishes = topDishes.values()


			# df = pd.DataFrame(venue['entitySentiment'], columns=['name','score','magnitude'])
			# dishDf = pd.DataFrame(venue['dishes'])
			# if 'price' not in dishDf.columns:
			# 	dishDf['price'] = None
			# if 'description' not in dishDf.columns:
			# 	dishDf['description'] = None
			
			# filter out entities with negative or neutral sentiment
			# df = df[df.score >= .2]
			# df['compositeScore'] = df.score * df.magnitude


			# Fuzzy string matching to find the best matching dish item for each entity
			# dishMatch = df.apply(lambda x: process.extractOne(x['name'], dishDf.name), axis=1)

			# df['dish'] = [result[0] for result in dishMatch]
			# df['matchScore'] = [result[1] for result in dishMatch]

			# filter out low match scores
			# df = df[df.matchScore >= 90]

			# if debug:
			# 	print df
			# 	print


			# # Group by dish and combine the score
			# topDishes = df.groupby('dish').compositeScore.sum().to_frame().reset_index()

			# if len(topDishes):

			# 	if debug:
			# 		print topDishes

			# 	topDishes['price'] = [dishDf[dishDf.name==topDish].price.values[0] for topDish in topDishes.dish]
			# 	topDishes['description'] = [dishDf[dishDf.name==topDish].description.values[0] for topDish in topDishes.dish]

			# 	topDishes['venueId'] = venue['id']

			# 	topDishes = topDishes.to_dict(orient='records')

			# else:
			# 	topDishes = []

		except:
			raise
			topDishes = []

		return topDishes



	def findTopDishesForLocation(self):
		'''
		'''
		# get a list of top dishes from all venues
		topDishes = []
		for venue in self.venues.values():
			topDishes += venue['topDishes']

		# sort by composite score
		topDishes = sorted(topDishes, key=lambda k: k['compositeScore'], reverse=True)

		# for dish in topDishes:
		# 	venueId = dish['venueId']
		# 	dish['venueName'] = self.venues[venueId]['name']
		# 	if 'location' in self.venues[venueId]:
		# 		dish['location'] = self.venues[venueId]['location']
		# 	if 'categories' in self.venues[venueId]:
		# 		dish['venueCategories'] = self.venues[venueId]['categories']
		# 	if 'url' in self.venues[venueId]:
		# 		dish['venueUrl'] = self.venues[venueId]['url']
		# 	if 'contact' in self.venues[venueId]:
		# 		dish['contact'] = self.venues[venueId]['contact']

		self.topDishes = topDishes


	def locationString(self):
		try:
			return self.geocode['displayString']
		except:
			return u''

	def locationId(self):
		return urlsafe_b64encode(self.locationString().encode('utf8'))


	def savePopularDishes(self, locationId, dishes):
		'''
		'''
		self.cache.writePopularDishes(locationId, dishes)

	def loadPopularDishes(self, locationId):
		'''
		'''
		dishes = self.cache.readPopularDishes(locationId)
		# if dishes is not None:
		# 	dishes = sorted(dishes, key=lambda k: k['compositeScore'], reverse=True)
		# else:
		# 	dishes = []
		if dishes is None:
			return {}
		return dishes

	def locationHasCachedDishes(self, locationId):
		'''
		'''
		return self.cache.locationHasCachedDishes(locationId)


	def pushQueueData(self, data):
		return self.cache.pushQueueData(data)

	def pullQueueData(self, key):
		return self.cache.pullQueueData(key)

	def saveUserDishList(self, data):
		return self.cache.saveUserDishList(data)

	def loadUserDishList(self, key):
		return self.cache.loadUserDishList(key)





class Cache:

	def __init__(self):
		self.dishfire = DishstarsFirebase()

	def readTips(self, venueId):
		r = self.dishfire.readFoursquareTips(venueId)
		if r is not None:
			r = r['tips']
		return r

	def readMenu(self, venueId):
		return self.dishfire.readFoursquareMenu(venueId)

	def readEntity(self, venueId):
		r = self.dishfire.readGoogleNLPEntitySentiment(venueId)
		if r is not None:
			r = r['entities']
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
			# r = r.values()
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
		return self.dishfire.readSavedDishList(key)






