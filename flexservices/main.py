from flask import Flask, request, abort, render_template, redirect, url_for, jsonify, json
from dishrecommender import DishRecommender
from dishstars_firebase import DishstarsFirebase
from geodish import GeoDish


app = Flask(__name__)


@app.route('/tasks/generateRecommendations', methods=['POST'])
def generateRecommendations():
	"""A task that takes a user's list of saved dishes and
	generates a list of recommended dishes based on the list.
	"""

	dishfire = DishstarsFirebase()
	
	data = json.loads(request.data)
	locationIds = data['locationIds']
	likedDishes = data['likedDishes']
	savedListId = data['savedListId']

	locDishes = {}

	# get all the popular dishes for the locations
	for locationId in locationIds:
		r = dishfire.readPopularDishes(locationId)
		if r is not None:
			dishes = r['dishes']
			if 'timestamp' in dishes:
				del dishes['timestamp']
		
		locDishes.update(dishes)

	# Get recommended dishes based on the users saved dish list.
	dishrec = DishRecommender(locDishes)
	recDishes = dishrec.recommendSimilarDishes(likedDishes, n=10, minSimilarity=.175)

	# Save the dish recommendations
	dishfire.writeUserRecommended(savedListId, recDishes)

	return 'ok'



@app.route('/tasks/processPopularDishes', methods=['POST'])
def processPopularDishes():
	"""A task that process the most popular dishes for a venue."""

	geoDish = GeoDish()

	# Get the data for this task from the tasks data queue
	dataKey = json.loads(request.data)['dataKey']
	data = geoDish.pullQueueData(dataKey)
	if data is None:
		return 'ok'
	venue = data[u'venue']
	locationId = data[u'locationId']

	# Find the top dishes for the venue/
	geoDish = GeoDish()
	popularDishes = geoDish.findTopDishesForVenue(venue)

	# Save the top dishes.
	if len(popularDishes) > 0:
		geoDish.savePopularDishes(locationId, popularDishes)

	return 'ok'





