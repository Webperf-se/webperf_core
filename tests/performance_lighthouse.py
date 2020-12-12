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
import gettext
_ = gettext.gettext

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

	language = gettext.translation('performance_lighthouse', localedir='locales', languages=[langCode])
	language.install()
	_ = language.gettext

	print(_('TEXT_RUNNING_TEST'))

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
		review = _("TEXT_REVIEW_VERY_GOOD")
	elif speedindex <= 1200:
		points = 4
		review = _("TEXT_REVIEW_IS_GOOD")
	elif speedindex <= 2500:
		points = 3
		review = _("TEXT_REVIEW_IS_OK")
	elif speedindex <= 3999:
		points = 2
		review = _("TEXT_REVIEW_IS_BAD")
	elif speedindex > 3999:
		points = 1
		review = _("TEXT_REVIEW_IS_VERY_BAD")
	
	review += _("TEXT_REVIEW_OBSERVED_SPEED").format(convert_to_seconds(return_dict["observedSpeedIndex"], False))#'* Observerad hastighet: {} sekunder\n'.format(convert_to_seconds(return_dict["observedSpeedIndex"], False))
	review += _("TEXT_REVIEW_FIRST_MEANINGFUL_PAINT").format(convert_to_seconds(return_dict["firstMeaningfulPaint"], False))#'* Första meningsfulla visuella ändring: {} sek\n'.format(convert_to_seconds(return_dict["firstMeaningfulPaint"], False))
	review += _("TEXT_REVIEW_FIRST_MEANINGFUL_PAINT_3G").format(convert_to_seconds(return_dict["first-contentful-paint-3g"], False))#'* Första meningsfulla visuella ändring på 3G: {} sek\n'.format(convert_to_seconds(return_dict["first-contentful-paint-3g"], False))
	review += _("TEXT_REVIEW_CPU_IDLE").format(convert_to_seconds(return_dict["firstCPUIdle"], False))#'* CPU vilar efter: {} sek\n'.format(convert_to_seconds(return_dict["firstCPUIdle"], False))
	review += _("TEXT_REVIEW_INTERACTIVE").format(convert_to_seconds(return_dict["interactive"], False))#'* Webbplatsen är interaktiv: {} sek\n'.format(convert_to_seconds(return_dict["interactive"], False))
	review += _("TEXT_REVIEW_REDIRECTS").format(return_dict["redirects"])#'* Antal hänvisningar: {} st\n'.format(return_dict["redirects"])
	review += _("TEXT_REVIEW_TOTAL_WEIGHT").format(int(return_dict["total-byte-weight"]/1000))#'* Sidans totala vikt: {} kb\n'.format(int(return_dict["total-byte-weight"]/1000))
	
	return (points, review, return_dict)
