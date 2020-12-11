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

def run_test(langCode, url, strategy='mobile', category='performance'):
	"""
	perf = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=performance&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
	a11y = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=accessibility&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
	practise = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=best-practices&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
	pwa = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=pwa&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
	seo = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=seo&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
	"""
	check_url = url.strip()
	
	pagespeed_api_request = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category={0}&url={1}&strategy={2}&key={3}'.format(category, check_url, strategy, googlePageSpeedApiKey)
	
	get_content = ''
	
	try:
		get_content = httpRequestGetContent(pagespeed_api_request)
	except:  # breaking and hoping for more luck with the next URL
		print(
			'Error! Unfortunately the request for URL "{0}" failed, message:\n{1}'.format(
				check_url, sys.exc_info()[0]))
		pass
	
	json_content = ''

	try:
		json_content = json.loads(get_content)
	except:  # might crash if checked resource is not a webpage
		print('Error! JSON failed parsing for the URL "{0}"\nMessage:\n{1}'.format(
			check_url, sys.exc_info()[0]))
		pass
	
	return_dict = {}
	return_dict = json_content['lighthouseResult']['audits']['metrics']['details']['items'][0]
	
	for item in json_content['lighthouseResult']['audits'].keys():
		try:
			return_dict[item] = json_content['lighthouseResult']['audits'][item]['numericValue']
		except:
			# has no 'numericValue'
			#print(item, 'har inget värde')
			pass
	
	speedindex = int(return_dict['observedSpeedIndex'])
	review = ''
	
	if speedindex <= 500:
		points = 5
		review = '* Webbplatsen laddar in mycket snabbt!\n'
	elif speedindex <= 1200:
		points = 4
		review = '* Webbplatsen är snabb.\n'
	elif speedindex <= 2500:
		points = 3
		review = '* Genomsnittlig hastighet.\n'
	elif speedindex <= 3999:
		points = 2
		review = '* Webbplatsen är ganska långsam.\n'
	elif speedindex > 3999:
		points = 1
		review = '* Webbplatsen är väldigt långsam!\n'
	
	review += '* Observerad hastighet: {} sekunder\n'.format(convert_to_seconds(return_dict["observedSpeedIndex"], False))
	review += '* Första meningsfulla visuella ändring: {} sek\n'.format(convert_to_seconds(return_dict["firstMeaningfulPaint"], False))
	review += '* Första meningsfulla visuella ändring på 3G: {} sek\n'.format(convert_to_seconds(return_dict["first-contentful-paint-3g"], False))
	review += '* CPU vilar efter: {} sek\n'.format(convert_to_seconds(return_dict["firstCPUIdle"], False))
	review += '* Webbplatsen är interaktiv: {} sek\n'.format(convert_to_seconds(return_dict["interactive"], False))
	review += '* Antal hänvisningar: {} st\n'.format(return_dict["redirects"])
	review += '* Sidans totala vikt: {} kb\n'.format(int(return_dict["total-byte-weight"]/1000))
	
	return (points, review, return_dict)
