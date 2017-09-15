from flask import Flask, request, abort, render_template, redirect, url_for, jsonify, json
from google.appengine.api import taskqueue
from geodish import GeoDish
from base64 import b64encode, b64decode, urlsafe_b64encode, urlsafe_b64decode


app = Flask(__name__)


@app.route('/', methods=['GET'])
def mainPage():
    return render_template('dishstars_main.html')


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
			data = {u'locationId': locationId, u'locationName': locationName, u'venue': venue}
			dataKey = geoDish.pushQueueData(data)
			taskqueue.add(url='/tasks/processMenu', payload=json.dumps({'dataKey': dataKey}))

	# return {'status': 200, 'locationId': locationId}
	return redirect(url_for('getDishes', locationId=locationId))


@app.route('/location/<locationId>/dishes', methods=['GET'])
def getDishes(locationId):

	geoDish = GeoDish()
	dishes = geoDish.loadPopularDishes(locationId)
	locationName = urlsafe_b64decode(locationId.encode('utf8')).decode('utf8')

	result = {'location': locationName, 'dishes': dishes}

	return jsonify(result)


@app.route('/tasks/processMenu', methods=['POST'])
def processMenu():

	geoDish = GeoDish()

	dataKey = json.loads(request.data)['dataKey']
	data = geoDish.pullQueueData(dataKey)
	venue = data[u'venue']

	geoDish = GeoDish()
	dishes = geoDish.getDishesFromMenu(venue)

	if len(dishes) > 0:
		data[u'venue'][u'dishes'] = dishes
		dataKey = geoDish.pushQueueData(data)
		taskqueue.add(url='/tasks/processTips', payload=json.dumps({'dataKey': dataKey}))

	return 'ok'


@app.route('/tasks/processTips', methods=['POST'])
def processTips():

	geoDish = GeoDish()

	dataKey = json.loads(request.data)['dataKey']
	data = geoDish.pullQueueData(dataKey)
	venue = data[u'venue']

	geoDish = GeoDish()
	tips = geoDish.getTips(venue)

	if len(tips) > 0:
		data[u'venue'][u'tips'] = tips
		dataKey = geoDish.pushQueueData(data)
		taskqueue.add(url='/tasks/processEntitySentiment', payload=json.dumps({'dataKey': dataKey}))

	return 'ok'


@app.route('/tasks/processEntitySentiment', methods=['POST'])
def processEntitySentiment():

	geoDish = GeoDish()

	dataKey = json.loads(request.data)['dataKey']
	data = geoDish.pullQueueData(dataKey)
	venue = data[u'venue']

	geoDish = GeoDish()
	entitySentiment = geoDish.analyzeReviewSentiment(venue)

	if len(entitySentiment) > 0:
		data[u'venue'][u'entitySentiment'] = entitySentiment
		dataKey = geoDish.pushQueueData(data)
		taskqueue.add(url='/tasks/processPopularDishes', payload=json.dumps({'dataKey': dataKey}))

	return 'ok'


@app.route('/tasks/processPopularDishes', methods=['POST'])
def processPopularDishes():

	geoDish = GeoDish()

	dataKey = json.loads(request.data)['dataKey']
	data = geoDish.pullQueueData(dataKey)
	venue = data[u'venue']
	locationId = data[u'locationId']

	geoDish = GeoDish()
	popularDishes = geoDish.findTopDishesForVenue(venue)

	if len(popularDishes) > 0:
		geoDish.savePopularDishes(locationId, popularDishes)

	return 'ok'








