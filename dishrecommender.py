import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from scipy import sparse


class DishRecommender:

	def __init__(self, userLikedDishes, locationDishes):
		'''
		'''
		self.locationDishes = locationDishes
		self.userLikedDishes = userLikedDishes

		self.dishLookup = self.createDishLookup(self.locationDishes)
		self.matrix = self.userByDishMatrix(self.locationDishes)
		self.matrix = self.normalizeMatrix(self.matrix)

		self.userlikedVec = self.userlikedDishesVec(self.userLikedDishes)
		
		# Build the similarity matrix
		self.similarityMatrix = self.calculateSimilarity(self.matrix)

		self.dataNeighbors = self.getDataNeighbors(self.similarityMatrix)





	def createDishLookup(self, dishes):
		'''
		'''
		lookup = {}
		for key, val in dishes.items():
			lookup[key] = val['dish']
		return lookup

	def userByDishMatrix(self, dishes):
		'''
		'''
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

	def userlikedDishesVec(self, dishes):
		'''
		'''
		vec = np.zeros(len(self.di))
		for dish in dishes:
			if dish in self.di:
				vec[self.di[dish]] = 1

		return vec


	def normalizeMatrix(self, mat):
		'''
		'''
		# Normalize the user vectors to unit vectors.

		# magnitude = sqrt(x2 + y2 + z2 + ...)
		magnitude = np.sqrt(np.square(mat).sum(axis=1))
		# unitvector = (x / magnitude, y / magnitude, z / magnitude, ...)
		mat = mat.divide(magnitude, axis='index')

		return mat


	def calculateSimilarity(self, data_items):
		'''
		Calculate the column-wise cosine similarity for a sparse
		matrix. Return a new dataframe matrix with similarities.
		'''
		data_sparse = sparse.csr_matrix(data_items)
		similarities = cosine_similarity(data_sparse.transpose())
		sim = pd.DataFrame(data=similarities, index= data_items.columns, columns= data_items.columns)
		return sim


	def getSimilar(self, dishKey, n=5):
		'''
		'''
		similar = self.similarityMatrix.loc[dishKey].nlargest(n)
		return similar


	def getSimilarToLiked(self, likedDishes, n=5):
		'''
		'''
		similar = []
		# get top n similar for each liked dish
		for likedDish in likedDishes:
			sim = self.getSimilar(likedDish, n)
			# drop first value because it's the liked dish; convert to dict
			similar += [{'dish':item[0], 'similarity':item[1], 'similarTo':likedDish} for item in sim[sim.index[1:]].to_dict().items()]
		
		# sort them all by similarity
		similar = sorted(similar, key=lambda x: x['similarity'])[::-1][:n]
		
		# get the top n unique dishes and return all dish info
		results = {}
		totalItems = 0
		for item in similar:
			if totalItems < n and item['similarity'] >= .1:
				# skip dish if already added (first instance has highest similarity to a liked dish)
				if item['dish'] not in results:
					results[item['dish']] = self.locationDishes[item['dish']]
					similarDish = self.locationDishes[item['similarTo']]
					similarTo = {'dish': similarDish['dish'], 'venueName': similarDish['venueName']}
					results[item['dish']]['similarTo'] = similarTo
					totalItems += 1
			else:
				return results
		return results




	
	def getDataNeighbors(self, simMat):
		'''
		Construct a new dataframe with the 10 closest neighbours (most similar)
		for each artist.
		'''
		dataNeighbours = pd.DataFrame(index=simMat.columns, columns=range(1,11))
		for i in xrange(0, len(simMat.columns)):
			dataNeighbours.ix[i,:10] = simMat.ix[0:,i].sort_values(ascending=False)[:10].index

		return dataNeighbours


	def predictUserNeighborhood(self):
		'''
		Construct the neighbourhood from the most similar items to the
		ones our user has already liked.
		'''
		mostSimilarToLikes = self.dataNeighbors.ix[self.userLikedDishes]
		similarList = mostSimilarToLikes.values.tolist()
		similarList = list(set([item for sublist in similarList for item in sublist]))
		neighbourhood = self.similarityMatrix[similarList].ix[similarList]

		# A user vector containing only the neighbourhood items and
		# the known user likes.
		userVector = self.userlikedVec.ix[similarList]

		# Calculate the score.
		score = neighbourhood.dot(userVector).div(neighbourhood.sum(axis=1))

		# Drop the known likes.
		score = score.drop(self.userLikedDishes)

		return score









