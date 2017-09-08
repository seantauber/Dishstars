import foursquare
from fscred import CLIENT_ID, CLIENT_SECRET

from google.cloud import language_v1beta2
from google.cloud.language_v1beta2 import enums
from google.cloud.language_v1beta2 import types


class GeoDish:

	def __init__(self):
		self.fsClient = foursquare.Foursquare(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
		self.fsExploreParams = {'section': 'food', 'limit': 500, 'openNow': 0}


	def getDishes(self, nearLocation):
		'''
		'''
		self.venues = self.getRestaurants(nearLocation)
		for venue in self.venues:
			dishes = self.getMenu(venue)
			tips = self.getTips(venue)
			venue.update({'dishes': dishes, 'tips': tips})

		# remove venues with no dishes listed in menu
		n = len(self.venues)
		for i in range(n):
			if self.venues[i]['dishes'] == []:
				self.venues.pop(i)


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

		def getMenuItem(d):
			if "menuId" in d or "sectionId" in d:
				for item in d['entries']['items']:
					getMenuItem(item)
			elif "entryId" in d:
				menuItem = {}
				menuItem['name'] = d['name']
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
		result = self.entity_sentiment_text(tipText)
		venue['rawSentimentResult'] = result



	def entity_sentiment_text(text, verbose=False):
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












