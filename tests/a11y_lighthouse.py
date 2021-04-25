# -*- coding: utf-8 -*-
import sys
import socket
import ssl
import json
import requests
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
from bs4 import BeautifulSoup
import config
from tests.utils import *
import gettext
_ = gettext.gettext

# DEFAULTS
googlePageSpeedApiKey = config.googlePageSpeedApiKey


def run_test(langCode, url, strategy='mobile', category='accessibility'):

    language = gettext.translation(
        'a11y_lighthouse', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

    check_url = url.strip()

    pagespeed_api_request = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category={0}&url={1}&key={2}'.format(
        category, check_url, googlePageSpeedApiKey)

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

    score = 0
    fails = 0
    fail_dict = {}

    for item in json_content['lighthouseResult']['audits'].keys():
        try:
            return_dict[item] = json_content['lighthouseResult']['audits'][item]['score']

            score = score + \
                int(json_content['lighthouseResult']['audits'][item]['score'])

            if int(json_content['lighthouseResult']['audits'][item]['score']) == 0:
                fails += 1
                fail_dict[item] = json_content['lighthouseResult']['audits'][item]['title']
        except:
            # has no 'numericValue'
            #print(item, 'har inget värde')
            pass

    review = ''
    points = 0

    if fails == 0:
        points = 5
        review = _('TEXT_REVIEW_A11Y_VERY_GOOD')
    elif fails <= 2:
        points = 4
        review = _('TEXT_REVIEW_A11Y_IS_GOOD')
    elif fails <= 3:
        points = 3
        review = _('TEXT_REVIEW_A11Y_IS_OK')
    elif fails <= 5:
        points = 2
        review = _('TEXT_REVIEW_A11Y_IS_BAD')
    elif fails > 5:
        points = 1
        review = _('TEXT_REVIEW_A11Y_IS_VERY_BAD')

    if fails != 0:
        review += _('TEXT_REVIEW_A11Y_NUMBER_OF_PROBLEMS').format(fails)

        for key, value in return_dict.items():
            if value == 0:
                review += '* {}\n'.format(fail_dict[key])

    return (points, review, return_dict)
