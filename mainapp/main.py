from flask import Flask, request, abort, render_template, redirect, url_for, jsonify, json
from google.appengine.api import taskqueue
from google.appengine.api import mail
from google.appengine.api import app_identity
from geodish import GeoDish
from base64 import b64encode, b64decode, urlsafe_b64encode, urlsafe_b64decode


app = Flask(__name__)

#Nonsense
@app.route('/', methods=['GET'])
def mainPage():
	demo = 0
	if 'demo' in request.args:
		demo = 1
	return render_template('searchresults.html', demo=demo)


@app.route('/slides', methods=['GET'])
def projectSlides():
	"""Google slides for insight project."""
	return redirect('https://docs.google.com/presentation/d/1LcKsxwMTPtc2H9iPjcmpotoB5iI0Q3Yuu65gCtwi4sA/edit?usp=sharing')


@app.route('/demo', methods=['GET'])
def demoList():
	"""Fixed url for demo saved list"""
	return redirect('https://dishstars.com/dishlist/-Kv2fjIaupVAyBHUH57r?demo=1')

@app.route('/findDishes', methods=['POST'])
def findDishes():
	"""Initiate the search process for dishes in a location.
	If dishes are not cached alread, initiates a task queue sequence that
	will process the dishes for the location.

	Returns info about the location so dishes can be retrieved
	via JS on the front end.
	"""

	nearLocation = request.form['near']

	geoDish = GeoDish()
	venues = geoDish.getRestaurants(nearLocation)

	locationName = geoDish.locationString()
	locationId = urlsafe_b64encode(locationName.encode('utf8'))

	geo = geoDish.geocode

	# Check if there are dishes in the cache for this location
	if not geoDish.locationHasCachedDishes(locationId):

		# no dishes in cache. Go through the dish finding process.

		for venue in venues:
			data = {u'locationId': locationId, u'locationName': locationName, u'venue': venue}
			dataKey = geoDish.pushQueueData(data)
			taskqueue.add(url='/tasks/processMenu', payload=json.dumps({'dataKey': dataKey}))


	data = {'locationId': locationId, 'locationName': locationName, 'latLng': geo['center']}
	return jsonify(data)


@app.route('/results/location/<locationId>', methods=['GET'])
def locationResults(locationId):
	"""Render the the location results template
	along with some location info.
	"""

	geoDish = GeoDish()
	locationName = urlsafe_b64decode(locationId.encode('utf8')).decode('utf8')
	latLng = [request.args['lat'], request.args['lng']]

	return render_template('searchresults.html', locationId=locationId,
		locationName=locationName, latLng=latLng)


@app.route('/api/searchResults/location/<locationId>/dishes', methods=['GET'])
def getPopularDishes(locationId):
	"""Returns the dishes for location."""

	geoDish = GeoDish()
	dishes = geoDish.loadPopularDishes(locationId)
	count = len(dishes)

	return jsonify({'count': count, 'dishes': dishes})


@app.route('/api/saveDishList', methods=['POST'])
def saveDishList():
	"""Save a user dish list"""

	data = request.get_json(force=True)

	geoDish = GeoDish()
	listKey = geoDish.saveUserDishList(data)
	likedDishes = data['dishes'].keys()
	locationIds = data['locationIds']

	taskData = {'likedDishes': likedDishes, 'locationIds': locationIds, 'savedListId': listKey}

	# initiate recommend dishes task
	taskqueue.add(url='/tasks/generateRecommendations',
		target='flxone',
		payload=json.dumps(taskData))

	return jsonify({'listKey': listKey})


@app.route('/dishlist/<key>', methods=['GET'])
def loadDishList(key):
	"""Render saved dish list template."""

	demo = 0
	if 'demo' in request.args:
		demo = 1
	return render_template('savedlist.html', key=key, demo=demo)

@app.route('/api/dishlist/<key>', methods=['GET'])
def getDishList(key):
	"""Returns a saved dish list."""

	geoDish = GeoDish()
	userData = geoDish.loadUserDishList(key)
	if userData is None:
		abort(404)
	userSugg = geoDish.loadUserRecommended(key)
	if userSugg is None:
		userSugg = {}
	userData['sugg'] = userSugg
	return jsonify(userData)


@app.route('/dishlist/sendEmail', methods=['POST'])
def sendDishListByEmail():
	"""Send email notification containing dish list info"""

	email = request.form['email']
	url = request.form['urlField']
	location = request.form['locationField']

	sendEmail(email, url, location)

	return 'ok'


def sendEmail(email, url, location):
	"""Sends the email."""

	mail.send_mail(sender="Dishstars <seanetauber@gmail.com>",
                   to=email,
                   subject="Your Dishes for %s" % location,
                   body="""Here is a link to your saved in dishes in %s.

%s

Bon Apetite!

The Dishstars Team
""" % (location, url) )

@app.route('/_ah/mail/', methods=['GET', 'POST'])
def incomingEmail():
	"""Handle incoming mail."""
	pass



@app.route('/tasks/processMenu', methods=['POST'])
def processMenu():

	geoDish = GeoDish()

	dataKey = json.loads(request.data)['dataKey']
	data = geoDish.pullQueueData(dataKey)
	if data is None:
		return 'ok'
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
	if data is None:
		return 'ok'
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
	if data is None:
		return 'ok'
	venue = data[u'venue']

	geoDish = GeoDish()
	entitySentiment = geoDish.analyzeReviewSentiment(venue)

	if len(entitySentiment) > 0:
		data[u'venue'][u'entitySentiment'] = entitySentiment
		dataKey = geoDish.pushQueueData(data)
		taskqueue.add(url='/tasks/processPopularDishes',
			target='flxone',
			payload=json.dumps({'dataKey': dataKey}))

	return 'ok'

