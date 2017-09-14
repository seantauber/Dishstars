from flask import Flask, request, abort, render_template, redirect, url_for, jsonify
from google.appengine.api import taskqueue
from geodish import GeoDish
from base64 import b64encode, b64decode, urlsafe_b64encode, urlsafe_b64decode


app = Flask(__name__)


@app.route('/', methods=['GET'])
def mainPage():
    return 'dishstars'
    # return render_template('dishstars_main.html')


@app.route('/findDishes', methods=['POST'])
def findDishes():

	nearLocation = request.form['near']
	
	geoDish = GeoDish()
	venues = geoDish.getRestaurants(nearLocation)

	locationName = geoDish.locationString()
	locationId = urlsafe_b64encode(locationName.encode('utf8'))

	# Check if there are dishes in the cache for this location
	if not geoDish.locationHasCachedDishes(locationId):

		# no dishes in cache. Go through the dish finding process.

		for venue in venues:
			params = {u'locationId': locationId, u'locationName': locationName, u'venue': venue}
			taskqueue.add(url='/tasks/processMenu', params=params)

	# return {'status': 200, 'locationId': locationId}
	return url_for(getDishes, locationId=locationId)


@app.route('/location/<locationId>/dishes', methods=['GET'])
def getDishes(locationId):

	geoDish = GeoDish()
	dishes = geoDish.readPopularDishes(locationId)
	locationName = urlsafe_b64decode(locationId)

	result = {'location': locationName, 'dishes': dishes}

	return jsonify(result)


@app.route('/tasks/processMenu', methods=['POST'])
def processMenu():

	params = request.form.to_dict()
	venue = params[u'venue']

	geoDish = GeoDish()
	dishes = geoDish.getDishesFromMenu(venue)

	if len(dishes) > 0:
		params[u'venue'][u'dishes'] = dishes
		taskqueue.add(url='/tasks/processTips', params=params)

	return 200


@app.route('/tasks/processTips', methods=['POST'])
def processTips():

	params = request.form.to_dict()
	venue = params[u'venue']

	geoDish = GeoDish()
	tips = geoDish.getTips(venue)

	if len(tips) > 0:
		params[u'venue'][u'tips'] = tips
		taskqueue.add(url='/tasks/processEntitySentiment', params=params)

	return 200


@app.route('/tasks/processEntitySentiment', methods=['POST'])
def processEntitySentiment():

	params = request.form.to_dict()
	venue = params[u'venue']

	geoDish = GeoDish()
	entitySentiment = geoDish.analyzeReviewSentiment(venue)

	if len(entitySentiment) > 0:
		params[u'venue'][u'entitySentiment'] = entitySentiment
		taskqueue.add(url='tasks/processPopularDishes')

	return 200


@app.route('/tasks/processPopularDishes', methods=['POST'])
def processPopularDishes():

	params = request.form.to_dict()
	venue = params[u'venue']
	locationId = params[u'locationId']

	geoDish = GeoDish()
	popularDishes = geoDish.findTopDishesForVenue(venue)

	if len(popularDishes) > 0:
		geoDish.savePopularDishes(locationId, popularDishes)

	return 200








