import requests
from requests import HTTPError
from requests.packages.urllib3.contrib.appengine import is_appengine_sandbox
import requests_toolbelt
from requests_toolbelt.adapters import appengine
import json
from nlpcred import GOOGLE_API_KEY

if is_appengine_sandbox():
	requests_toolbelt.adapters.appengine.monkeypatch()


class GoogleLanguage:

	def __init__(self):
		'''
		'''
		self.url = 'https://language.googleapis.com/v1beta2/documents:analyzeEntitySentiment'

	
	def analyzeEntitySentiment(self, text):
		'''
		'''

		params = {'key': GOOGLE_API_KEY}

		data = {}
		data['document'] = {'type': 'PLAIN_TEXT', 'language': 'en', 'content': text}
		data['encodingType'] = 'UTF8'

		headers = {"content-type": "application/json; charset=UTF-8"}

		response = requests.post(self.url,
			data=json.dumps(data).encode("utf-8"),
			headers=headers,
			params=params)

		if response.ok:
			data = json.loads(response.content)
			return data['entities']
		else:
			response.raise_for_status()

