from base64 import b64encode, urlsafe_b64encode
import json

import requests
from requests import HTTPError
from requests.packages.urllib3.contrib.appengine import is_appengine_sandbox
import requests_toolbelt
from requests_toolbelt.adapters import appengine
from oauth2client.service_account import ServiceAccountCredentials

from firebase_config import FIREBASE_CFG as _FIREBASE_CFG


if is_appengine_sandbox():
    requests_toolbelt.adapters.appengine.monkeypatch()


_firebase_credentials = ServiceAccountCredentials.from_json_keyfile_name(_FIREBASE_CFG["serviceAccount"],
	_FIREBASE_CFG["scopes"])
_firebase_credentials.get_access_token()



class DishstarsFirebase:
	"""Class for reading/writing dishstars data to/from Firebase."""

	def __init__(self):
		"""Initialize connection to Firebase."""
		self._BASEURL = FIREBASE_CFG['datebaseURL']
		self._credentials = _firebase_credentials

	def _access_token(self):
		if self._credentials.access_token_expired:
			self._credentials.get_access_token()

		return self._credentials.access_token

	def _build_headers(self):
		headers = {"content-type": "application/json; charset=UTF-8"}
		headers['Authorization'] = 'Bearer ' + self._access_token()
		return headers

	def _firebase_response(self, resp):
		if resp.ok:
			return resp.json()
		else:
			resp.raise_for_status()


	def putData(self, url, data):
		"""Use a put request to write data to url with predifined key"""
		data['timestamp'] = {'.sv': 'timestamp'}
		response = self._firebase_response(requests.put(url,
			data=json.dumps(data).encode("utf-8"),
			headers=self._build_headers()))
		return response

	def postData(self, url, data):
		"""Use a post request to write data to url and return 
		a new key to the data
		"""
		response = self._firebase_response(requests.post(url,
			data=json.dumps(data).encode("utf-8"),
			headers=self._build_headers()))
		# return the new key
		return response['name']

	def patchData(self, url, data):
		"""Use a patch request to update data to url without
		overwriting existing fields.
		"""
		data['timestamp'] = {'.sv': 'timestamp'}
		response = self._firebase_response(requests.patch(url,
			data=json.dumps(data).encode("utf-8"),
			headers=self._build_headers()))

		return response

	def getData(self, url):
		"""Use a get request to fetch data from a url."""
		return self._firebase_response(requests.get(url, headers=self._build_headers()))

	def deleteData(self, url):
		"""Use a delete request to delete data at a url"""
		return self._firebase_response(requests.delete(url, headers=self._build_headers()))

	
	def writeFoursquareMenu(self, venueId, data):
		"""Save a venue's menu to the cache"""
		url = self._BASEURL + "cache/foursquare/menu/%s.json" % venueId
		return self.putData(url, data)

	def writeFoursquareTips(self, venueId, data):
		"""Save a venue's tips to the cache"""
		url = self._BASEURL + "cache/foursquare/tips/%s.json" % venueId
		return self.putData(url, data)

	def writeGoogleNLPEntitySentiment(self, venueId, data):
		"""Save a venue's entity sentiment results to the cache"""
		url = self._BASEURL + "cache/foursquare/tipsEntitySentiment/%s.json" % venueId
		return self.putData(url, data)


	def readFoursquareMenu(self, venueId):
		"""Load a venue's menu from the cache"""
		url = self._BASEURL + "cache/foursquare/menu/%s.json" % venueId
		return self.getData(url)

	def readFoursquareTips(self, venueId):
		"""Load a venue's tips from the cache"""
		url = self._BASEURL + "cache/foursquare/tips/%s.json" % venueId
		return self.getData(url)

	def readGoogleNLPEntitySentiment(self, venueId):
		"""Load a venue's entity sentiment results from the cache"""
		url = self._BASEURL + "cache/foursquare/tipsEntitySentiment/%s.json" % venueId
		return self.getData(url)


	def writePopularDishes(self, locationId, dishes):
		"""Save a list of popular dishes for the location."""
		url = self._BASEURL + "cache/popularDishes/location/%s/dishes.json" % locationId
		# write a timestamp to location so we know when it was last refreshed.
		self.patchData(self._BASEURL + "cache/popularDishes/location/%s.json" % locationId, {})
		# Save all dishes with post to generate new keys for each one.
		for dish in dishes:
			self.postData(url, dish)

	def readPopularDishes(self, locationId):
		"""Load a list of popular dishes for the location."""
		url = self._BASEURL + "cache/popularDishes/location/%s.json" % locationId
		return self.getData(url)

	def readLocationCacheTimestamp(self, locationId):
		"""Get the time that the popular dishes were last refreshed."""
		url = self._BASEURL + "cache/popularDishes/location/%s/timestamp.json" % locationId
		return self.getData(url)


	def pushQueueData(self, data):
		"""Save data to the queue data cache and return a reference key."""
		url = self._BASEURL + "cache/queueData.json"
		return self.postData(url, data)

	def pullQueueData(self, key):
		"""Load data from te queue data cache using the key."""
		url = self._BASEURL + "cache/queueData/%s.json" % key
		data = self.getData(url)
		self.deleteData(url)
		return data


	def writeSavedDishList(self, data):
		"""Save a user dish list."""
		url = self._BASEURL + "/userData/savedDishList.json"
		return self.postData(url, data)


	def readSavedDishList(self, key):
		"""Load a user dish list."""
		url = self._BASEURL + "/userData/savedDishList/%s.json" % key
		data = self.getData(url)
		return data

	def writeUserRecommended(self, key, data):
		"""Save recommended dishes."""
		url = self._BASEURL + "/userData/suggested/%s.json" % key
		return self.putData(url, data)

	def readUserRecommended(self, key):
		"""Load recommended dishes"""
		url = self._BASEURL + "/userData/suggested/%s.json" % key
		data = self.getData(url)
		return data


	def getTipsForDish(self, locationId, dishKey):
		"""Load the tips for a dish."""
		url = self._BASEURL + "/cache/popularDishes/location/%s/dishes/%s/tipIndex.json" % (locationId, dishKey)
		data = self.getData(url)
		return data








