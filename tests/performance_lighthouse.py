# -*- coding: utf-8 -*-
from models import Rating
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


def run_test(langCode, url, strategy='mobile', category='performance'):
    """
    perf = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=performance&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    a11y = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=accessibility&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    practise = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=best-practices&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    pwa = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=pwa&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    seo = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=seo&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    """

    language = gettext.translation(
        'performance_lighthouse', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

    check_url = url.strip()

    pagespeed_api_request = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed?locale={4}&category={0}&url={1}&strategy={2}&key={3}'.format(
        category, check_url, strategy, googlePageSpeedApiKey, langCode)
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

    review = ''
    return_dict = {}

    # Service score (0-100)
    score = json_content['lighthouseResult']['categories'][category]['score']
    # change it to % and convert it to a 1-5 grading
    points = 5.0 * float(score)

    return_dict = json_content['lighthouseResult']['audits']['metrics']['details']['items'][0]

    for item in json_content['lighthouseResult']['audits'].keys():
        try:
            return_dict[item] = json_content['lighthouseResult']['audits'][item]['numericValue']
            review += _("* {0} - {1}\r\n").format(json_content['lighthouseResult']['audits'][item]['title'],
                                                  json_content['lighthouseResult']['audits'][item]['displayValue'])

        except:
            # has no 'numericValue'
            #print(item, 'har inget värde')
            pass

    if points <= 5.0:
        review = _("TEXT_REVIEW_VERY_GOOD") + review
    elif points >= 4.0:
        review = _("TEXT_REVIEW_IS_GOOD") + review
    elif points >= 3.0:
        review = _("TEXT_REVIEW_IS_OK") + review
    elif points > 1.0:
        review = _("TEXT_REVIEW_IS_BAD") + review
    elif points <= 1.0:
        review = _("TEXT_REVIEW_IS_VERY_BAD") + review

    rating = Rating()
    rating.set_overall(points, review)
    rating.set_performance(points, review)

    return (rating, return_dict)
