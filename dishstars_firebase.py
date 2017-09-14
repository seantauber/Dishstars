from base64 import b64encode, urlsafe_b64encode
from firebase_config import FIREBASE_CFG as _FIREBASE_CFG
import requests
from requests import HTTPError
from requests.packages.urllib3.contrib.appengine import is_appengine_sandbox
import requests_toolbelt
from requests_toolbelt.adapters import appengine
from oauth2client.service_account import ServiceAccountCredentials
import json

if is_appengine_sandbox():
    requests_toolbelt.adapters.appengine.monkeypatch()


_firebase_credentials = ServiceAccountCredentials.from_json_keyfile_name(_FIREBASE_CFG["serviceAccount"],
	_FIREBASE_CFG["scopes"])
_firebase_credentials.get_access_token()

_BASEURL = "https://dishstars-insight.firebaseio.com/"


class DishstarsFirebase:

	def __init__(self):
		'''
		'''
		self._BASEURL = _BASEURL
		self._credentials = _firebase_credentials

	def _access_token(self):
		'''
		'''
		if self._credentials.access_token_expired:
			self._credentials.get_access_token()

		return self._credentials.access_token

	def _build_headers(self):
		'''
		'''
		headers = {"content-type": "application/json; charset=UTF-8"}
		headers['Authorization'] = 'Bearer ' + self._access_token()
		return headers

	def _firebase_response(self, resp):
		'''
		'''
		if resp.ok:
			return resp.json()
		else:
			resp.raise_for_status()


	def putData(self, url, data):
		'''
		'''
		data.update({".sv": "timestamp"})
		response = self._firebase_response(requests.put(url,
			data=json.dumps(data).encode("utf-8"),
			headers=self._build_headers()))
		return response

	def postData(self, url, data):
		'''
		'''
		response = self._firebase_response(requests.post(url,
			data=json.dumps(data).encode("utf-8"),
			headers=self._build_headers()))
		return response['name']

	def getData(self, url):
		'''
		'''
		return self._firebase_response(requests.get(url, headers=self._build_headers()))


	
	def writeFoursquareMenu(self, venueId, data):
		url = self._BASEURL + "cache/foursquare/menu/%s.json" % venueId
		return self.putData(url, data)

	def writeFoursquareTips(self, venueId, data):
		url = self._BASEURL + "cache/foursquare/tips/%s.json" % venueId
		return self.putData(url, data)

	def writeGoogleNLPEntitySentiment(self, venueId, data):
		url = self._BASEURL + "cache/foursquare/tipsEntitySentiment/%s.json" % venueId
		return self.putData(url, data)


	def readFoursquareMenu(self, venueId):
		url = self._BASEURL + "cache/foursquare/menu/%s.json" % venueId
		return self.getData(url)

	def readFoursquareTips(self, venueId):
		url = self._BASEURL + "cache/foursquare/tips/%s.json" % venueId
		return self.getData(url)

	def readGoogleNLPEntitySentiment(self, venueId):
		url = self._BASEURL + "cache/foursquare/tipsEntitySentiment/%s.json" % venueId
		return self.getData(url)
	





