from flask import Flask, request, abort, render_template, redirect, url_for, jsonify, json
from dishrecommender import DishRecommender
from dishstars_firebase import DishstarsFirebase
from geodish import GeoDish


app = Flask(__name__)


@app.route('/tasks/generateRecommendations', methods=['POST'])
def generateRecommendations():

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

	dishrec = DishRecommender(likedDishes, locDishes)
	recDishes = dishrec.recommendSimilarDishes(likedDishes, n=10, minSimilarity=.175)

	dishfire.writeUserRecommended(savedListId, recDishes)

	return 'ok'



@app.route('/tasks/processPopularDishes', methods=['POST'])
def processPopularDishes():

	geoDish = GeoDish()

	dataKey = json.loads(request.data)['dataKey']
	data = geoDish.pullQueueData(dataKey)
	if data is None:
		return 'ok'
	venue = data[u'venue']
	locationId = data[u'locationId']

	geoDish = GeoDish()
	popularDishes = geoDish.findTopDishesForVenue(venue)

	if len(popularDishes) > 0:
		geoDish.savePopularDishes(locationId, popularDishes)

	return 'ok'





