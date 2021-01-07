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
try:
	ylt_server_address = config.ylt_server_address
except:
	# If YLT URL is not set in config.py this will be the default
	ylt_server_address = 'https://yellowlab.tools'

def run_test(langCode, url, device='phone'):
	"""
	Analyzes URL with Yellow Lab Tools docker image.
	Devices might be; phone, tablet, desktop
	"""

	language = gettext.translation('frontend_quality_yellow_lab_tools', localedir='locales', languages=[langCode])
	language.install()
	_ = language.gettext

	print(_("TEXT_RUNNING_TEST"))

	r = requests.post('{}/api/runs'.format(ylt_server_address), data = {'url':url, "waitForResponse":'true', 'device': device})

	result_url = r.url
	test_id = result_url.rsplit('/', 1)[1]

	result_json = httpRequestGetContent('{0}/api/results/{1}?exclude=toolsResults'.format(ylt_server_address, test_id))
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
		review = _("TEXT_WEBSITE_IS_VERY_GOOD")
	elif rating >= 4:
		review = _("TEXT_WEBSITE_IS_GOOD")
	elif rating >= 3:
		review = _("TEXT_WEBSITE_IS_OK")
	elif rating >= 2:
		review = _("TEXT_WEBSITE_IS_BAD")
	elif rating <= 1:
		review = _("TEXT_WEBSITE_IS_VERY_BAD")

	review += _("TEXT_OVERALL_GRADE").format(return_dict["globalScore"])
	review += _("TEXT_TESTED_ON_DEVICETYPE").format(device)
	review += _("TEXT_PAGE_WEIGHT").format(return_dict["pageWeight"])
	review += _("TEXT_PAGE_REQUESTS").format(return_dict["requests"])
	review += _("TEXT_PAGE_DOM_COMPLEXITY").format(return_dict["domComplexity"])
	review += _("TEXT_PAGE_DOM_MANIPULATIONS").format(return_dict["domManipulations"])
	review += _("TEXT_PAGE_SCROLL").format(return_dict["scroll"])
	review += _("TEXT_PAGE_BAD_JS").format(return_dict["badJavascript"])
	review += _("TEXT_PAGE_JQUERY").format(return_dict["jQuery"])
	review += _("TEXT_PAGE_CSS_COMPLEXITY").format(return_dict["cssComplexity"])
	review += _("TEXT_PAGE_BAD_CSS").format(return_dict["badCSS"])
	review += _("TEXT_PAGE_FONTS").format(return_dict["fonts"])
	review += _("TEXT_SERVER_CONFIG").format(return_dict["serverConfig"])

	return (rating, review, return_dict)