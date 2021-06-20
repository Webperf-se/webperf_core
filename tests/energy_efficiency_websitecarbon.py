# -*- coding: utf-8 -*-
from models import Rating
import datetime
import sys
import socket
import ssl
import json
import requests
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
from bs4 import BeautifulSoup
from decimal import Decimal

import config
from tests.utils import *
import gettext
_local = gettext.gettext


def run_test(_, langCode, url):
    """
    Analyzes URL with Website Carbon Calculator API.
    API documentation: https://api.websitecarbon.com
    https://gitlab.com/wholegrain/carbon-api-2-0
    """

    language = gettext.translation(
        'energy_efficiency_websitecarbon', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local("TEXT_RUNNING_TEST"))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    result_json = httpRequestGetContent(
        'https://api.websitecarbon.com/site?url={0}'.format(url))
    result_dict = json.loads(result_json)

    # print(result_json)

    green = str(result_dict['green'])
    #print("Grön?", green)

    co2 = Decimal(result_dict['statistics']['co2']['grid']['grams'])
    #print('Co2', round(co2, 2), 'gram')

    cleaner_than = int(Decimal(result_dict['cleanerThan']) * 100)
    #print("Renare än:", cleaner_than, "%")

    review = ''

    # handicap points
    co2_with_handicap = float(co2) - 0.8

    points = float("{0:.2f}".format(5 - co2_with_handicap))

    # print(points)

    if points <= 5:
        review = _local("TEXT_WEBSITE_IS_VERY_GOOD")
    elif points >= 4:
        review = _local("TEXT_WEBSITE_IS_GOOD")
    elif points >= 3:
        review = _local("TEXT_WEBSITE_IS_OK")
    elif points >= 2:
        review = _local("TEXT_WEBSITE_IS_BAD")
    elif points <= 1:
        review = _local("TEXT_WEBSITE_IS_VERY_BAD")

    review += _local("TEXT_GRAMS_OF_CO2").format(round(co2, 2))
    review += _local("TEXT_BETTER_THAN").format(cleaner_than)
    if 'false' in green.lower():
        review += _local("TEXT_GREEN_ENERGY_FALSE")
    elif 'true' in green.lower():
        review += _local("TEXT_GREEN_ENERGY_TRUE")

    rating = Rating(_)
    rating.set_overall(points, review)

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)
