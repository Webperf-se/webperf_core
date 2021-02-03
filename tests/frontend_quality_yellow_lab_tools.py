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


def run_test(langCode, url, device='phone'):
    """
    Analyzes URL with Yellow Lab Tools docker image.
    Devices might be; phone, tablet, desktop
    """

    language = gettext.translation(
        'frontend_quality_yellow_lab_tools', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_("TEXT_RUNNING_TEST"))

    r = requests.post('https://yellowlab.tools/api/runs',
                      data={'url': url, "waitForResponse": 'true', 'device': device})

    result_url = r.url
    test_id = result_url.rsplit('/', 1)[1]

    print(
        'TEST:', 'https://yellowlab.tools/api/results/{0}?exclude=toolsResults'.format(test_id))

    result_json = httpRequestGetContent(
        'https://yellowlab.tools/api/results/{0}?exclude=toolsResults'.format(test_id))
    result_dict = json.loads(result_json)

    return_dict = {}
    yellow_lab = 0

    for key in result_dict['scoreProfiles']['generic'].keys():
        if key == 'globalScore':
            yellow_lab = result_dict['scoreProfiles']['generic'][key]

    review = ''
    for key in result_dict['scoreProfiles']['generic']['categories'].keys():
        review += "* {0}: {1} {2}\n".format(_(result_dict['scoreProfiles']['generic']['categories'][key]['label']),
                                            result_dict['scoreProfiles']['generic']['categories'][key]['categoryScore'],
                                            _("of 100"))

    rating = (int(yellow_lab) / 20) + 0.5

    if rating > 5:
        rating = 5
    elif rating < 1:
        rating = 1

    if rating == 5:
        review = _("TEXT_WEBSITE_IS_VERY_GOOD") + review
    elif rating >= 4:
        review = _("TEXT_WEBSITE_IS_GOOD") + review
    elif rating >= 3:
        review = _("TEXT_WEBSITE_IS_OK") + review
    elif rating >= 2:
        review = _("TEXT_WEBSITE_IS_BAD") + review
    elif rating <= 1:
        review = _("TEXT_WEBSITE_IS_VERY_BAD") + review

    return (rating, review, return_dict)
