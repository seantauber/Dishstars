import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from scipy import sparse


class DishRecommender:
	"""A tool for dish recommendations based on 
	item-based collabortive filtering.
	"""

	def __init__(self, locationDishes):
		"""Creates a dish hashtable, user-item matrix and an item-item
		similarity matrix for the dishes in locationDishes.
		"""
		self.locationDishes = locationDishes
		self.dishLookup = self.createDishLookup(self.locationDishes)
		self.matrix = self.userByDishMatrix(self.locationDishes)
		self.matrix = self.normalizeMatrix(self.matrix)
		# Build the similarity matrix
		self.similarityMatrix = self.calculateSimilarity(self.matrix)


	def createDishLookup(self, dishes):
		"""Returns a hashtable for looking up dishes by dish key."""
		lookup = {}
		for key, val in dishes.items():
			lookup[key] = val['dish']
		return lookup

	def userByDishMatrix(self, dishes):
		"""Returns a user by dish matrix.
		Cell i,j is 1 or 0: where 1 indicates user (row i)
		positively reviewed dish (col j).
		"""
		dishUserLookup = {}
		userDishLookup = {}

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

		ui = dict(zip(userDishLookup.keys(), range(len(userDishLookup.keys()))))
		di = dict(zip(dishUserLookup.keys(), range(len(dishUserLookup.keys()))))
		userLabels = sorted(ui, key=ui.get)
		dishLabels = sorted(di, key=di.get)

		mat = np.zeros((len(ui), len(di)))
		for user, dishes in userDishLookup.items():
			for dish in dishes:
				mat[ui[user], di[dish]] = 1

		mat = pd.DataFrame(mat, columns=dishLabels)

		self.ui = ui
		self.di = di

		return mat

	def normalizeMatrix(self, mat):
		"""Returns a normalized similarity matrix.
		User vectors (rows) are normalized to unit vectors.
		"""
		# magnitude = sqrt(x2 + y2 + z2 + ...)
		magnitude = np.sqrt(np.square(mat).sum(axis=1))
		# unitvector = (x / magnitude, y / magnitude, z / magnitude, ...)
		mat = mat.divide(magnitude, axis='index')

		return mat

	def calculateSimilarity(self, data_items):
		""" Calculate the column-wise cosine similarity for a sparse
		matrix. Return a new dataframe matrix with similarities.
		"""
		data_sparse = sparse.csr_matrix(data_items)
		similarities = cosine_similarity(data_sparse.transpose())
		sim = pd.DataFrame(data=similarities, index= data_items.columns, columns= data_items.columns)
		return sim

	def getSimilar(self, dishKey, n=5):
		"""Returns the n dishes most similar to dish represented
		by dishKey.
		"""
		similar = self.similarityMatrix.loc[dishKey].nlargest(n)
		return similar


	def recommendSimilarDishes(self, likedDishes, n=10, minSimilarity=.175):
		"""Returns a maximum of n dishes with highest similarity to the dishes
		in likedDishes.
		minSimilarity specifies the minimum similarity required for dish
		to be included in the recommendations.
		"""
		similar = []
		# get top n similar for each liked dish
		for likedDish in likedDishes:
			sim = self.getSimilar(likedDish, n)
			# drop first value because it's the liked dish; convert to dict
			similar += [{'dish':item[0], 'similarity':item[1], 'similarTo':likedDish} for item in sim[sim.index[1:]].to_dict().items()]
		
		# sort them all by similarity
		similar = sorted(similar, key=lambda x: x['similarity'])[::-1]

		# get the top n unique dishes and return all dish info
		results = {}
		recDishStrings = []
		totalItems = 0
		for item in similar:
			if totalItems < n and item['similarity'] >= minSimilarity:
				# skip dish if already added (first instance has highest similarity to a liked dish)
				recommendedDish = self.locationDishes[item['dish']]
				recDishString = recommendedDish['dish'] + recommendedDish['venueName']
				similarDish = self.locationDishes[item['similarTo']]
				simDishString = similarDish['dish'] + similarDish['venueName']

				# make sure the recommended dish is not same as similar dish based on name/venue
				# just using dish key not always reliable if duplicates
				# also make sure the dish/venue string has not already been added to recommended
				valid = (recDishString != simDishString) and (recDishString not in recDishStrings)
				if valid and item['dish'] not in results:
					results[item['dish']] = recommendedDish
					results[item['dish']]
					similarTo = {'dish': similarDish['dish'], 'venueName': similarDish['venueName'], 'similarity': item['similarity']}
					results[item['dish']]['similarTo'] = similarTo

					recDishStrings.append(recDishString)
					totalItems += 1
			else:
				return results
		return results


