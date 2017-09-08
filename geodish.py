import foursquare
from fscred import CLIENT_ID, CLIENT_SECRET

class GeoDish:

	def __init__(self):
		self.fsClient = foursquare.Foursquare(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
		self.fsExploreParams = {'section': 'food', 'limit': 500, 'openNow': 0}


	def getDishes(self, nearLocation):
		'''
		'''
		self.venues = self.getRestaurants(nearLocation)
		for venue in self.venues:
			menu = self.getMenu(venue)
			tips = self.getTips(venue)
			venue.update({'menu': menu, 'tips': tips})


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

	def parseMenu(self, menu):
		'''
		'''
		return menu


	def getTips(self, venue):
		'''
		'''
		r = self.fsClient.venues.tips(venue['id'], params={'limit': 500})
		tips = r['tips']['items']
		return tips











