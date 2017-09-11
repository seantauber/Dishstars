import foursquare
from fscred import CLIENT_ID, CLIENT_SECRET

import six, sys
from google.cloud import language_v1beta2
from google.cloud.language_v1beta2 import enums
from google.cloud.language_v1beta2 import types


class GeoDish:

	def __init__(self):
		self.fsClient = foursquare.Foursquare(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
		self.fsExploreParams = {'section': 'food', 'limit': 500, 'openNow': 0}
		self.apiCallCount = 0


	def getDishes(self, nearLocation):
		'''
		'''
		updatedVenues = []
		self.venues = self.getRestaurants(nearLocation)
		for venue in self.venues:
			dishes = self.getMenu(venue)
			if len(dishes) > 0:
				tips = self.getTips(venue)
				venue.update({u'dishes': dishes, u'tips': tips})
				updatedVenues.append(venue)
		self.venues = updatedVenues

	def entitySentimentAnalysis(self):
		'''
		'''
		for venue in self.venues:
			self.analyzeReviewSentiment(venue)


	def getRestaurants(self, nearLocation):
		'''
		'''
		params = self.fsExploreParams
		params.update({'near': nearLocation})

		r = self.fsClient.venues.explore(params=params)

		items = r['groups'][0]['items']

		venuesWithMenus = []
		for item in items:
			venue = item['venue']
			if u'hasMenu' in venue:
				venuesWithMenus.append(venue)

		return venuesWithMenus


	def getMenu(self, venue):
		'''
		'''
		menu = self.fsClient.venues.menu(venue['id'])
		menu = self.parseMenu(menu)
		return menu

	def parseMenu(self, menuDict):
		'''
		'''
		
		menuItems = []

		def getMenuItem(d, sectionPath=None):
			if 'menuId' in d or 'sectionId' in d:
				parentName = None
				if 'name' in d:
					parentName = d['name']
				for item in d['entries']['items']:
					getMenuItem(item, sectionPath=sectionPath + " | " + parentName)
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
			for menu in menuDict['menu']['menus']['items']:
				getMenuItem(menu)
		except:
			return []

		return menuItems



	def getTips(self, venue):
		'''
		'''
		r = self.fsClient.venues.tips(venue['id'], params={'limit': 500})
		tips = r['tips']['items']
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
		tipText = self.tipText(venue['tips'])
		result = self.entitySentimentText(tipText)
		venue['entitySentiment'] = self.entitySentimentResultToJsonCompatible(result)



	def entitySentimentText(self, text, verbose=False):
		"""Detects entity sentiment in the provided text."""
		client = language_v1beta2.LanguageServiceClient()

		if isinstance(text, six.binary_type):
			text = text.decode('utf-8')

		document = types.Document(
			content=text.encode('utf-8'),
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













