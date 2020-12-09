#-*- coding: utf-8 -*-
import sys
import socket
import ssl
import json
import requests
import urllib # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
from bs4 import BeautifulSoup
import config
from tests.utils import *

### DEFAULTS
request_timeout = config.http_request_timeout
googlePageSpeedApiKey = config.googlePageSpeedApiKey

def run_test(url, device='phone'):
	"""
	Analyzes URL with Yellow Lab Tools docker image.
	Devices might be; phone, tablet, desktop
	"""
	r = requests.post('https://yellowlab.tools/api/runs', data = {'url':url, "waitForResponse":'true', 'device': device})

	result_url = r.url
	test_id = result_url.rsplit('/', 1)[1]

	result_json = httpRequestGetContent('https://yellowlab.tools/api/results/{0}?exclude=toolsResults'.format(test_id))
	result_dict = json.loads(result_json)

	return_dict = {}

	for key in result_dict['scoreProfiles']['generic'].keys():
		if key == 'globalScore':
			return_dict[key] = result_dict['scoreProfiles']['generic'][key]

	for key in result_dict['scoreProfiles']['generic']['categories'].keys():
		return_dict[key] = result_dict['scoreProfiles']['generic']['categories'][key]['categoryScore']

	review = ''
	yellow_lab = return_dict["globalScore"]

	rating = (int(yellow_lab) / 20) + 0.5

	if rating > 5:
		rating = 5
	elif rating < 1:
		rating = 1
	
	if rating == 5:
		review = '* Webbplatsen är välbyggd!\n'
	elif rating >= 4:
		review = '* Webbplatsen är bra.\n'
	elif rating >= 3:
		review = '* Helt ok.\n'
	elif rating >= 2:
		review = '* Webbplatsen är rätt långsam eller har dålig frontend-kod.\n'
	elif rating <= 1:
		review = '* Väldigt dåligt betyg enligt Yellow Lab Tools!\n'

	review += '* Övergripande betyg: {} av 100\n'.format(return_dict["globalScore"])
	review += '* Testat för devicetyp: {}\n'.format(device)
	review += '* pageWeight: {}\n'.format(return_dict["pageWeight"])
	review += '* requests: {}\n'.format(return_dict["requests"])
	review += '* domComplexity: {}\n'.format(return_dict["domComplexity"])
	review += '* domManipulations: {}\n'.format(return_dict["domManipulations"])
	review += '* scroll: {}\n'.format(return_dict["scroll"])
	review += '* badJavascript: {}\n'.format(return_dict["badJavascript"])
	review += '* jQuery: {}\n'.format(return_dict["jQuery"])
	review += '* cssComplexity: {}\n'.format(return_dict["cssComplexity"])
	review += '* badCSS: {}\n'.format(return_dict["badCSS"])
	review += '* fonts: {}\n'.format(return_dict["fonts"])
	review += '* serverConfig: {}\n'.format(return_dict["serverConfig"])

	return (rating, review, return_dict)