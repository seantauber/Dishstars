from geodish import GeoDish


class DishRecommender:

	def __init__(self):
		'''
		'''
		self.geodish = GeoDish()


	def dishUserMatrix(self, locationId):
		'''
		'''
		dishUserLookup = {}
		userDishLookup = {}

		dishes = self.geodish.loadPopularDishes(locationId)

		for dishKey, dishDetails in dishes.items():
			for tip in dishDetails['dishTips']:
				
				if dishKey in dishUserLookup:
					dishUserLookup[dishKey].append(tip['user'])
				else:
					dishUserLookup[dishKey] = [tip['user']]

				if tip['user'] in userDishLookup:
					userDishLookup[tip['user']].append(dishKey)
				else:
					userDishLookup[tip['user']] = [dishKey]

		return {'dishUser': dishUserLookup, 'userDish':userDishLookup}


