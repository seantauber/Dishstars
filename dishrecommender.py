from geodish import GeoDish


class DishRecommender:

	def __init__(self):
		'''
		'''
		self. geodish = GeoDish()


	def dishUserMatrix(self, locationId):
		'''
		'''
		dishes = geodish.loadPopularDishes(locationId, keysOnly=True)
