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
time_sleep = config.webbkoll_sleep
if time_sleep < 5:
    time_sleep = 5

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

    import time
    language = gettext.translation(
        'frontend_quality_yellow_lab_tools', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_("TEXT_RUNNING_TEST"))

    r = requests.post('{0}/api/runs'.format(ylt_server_address),
                      data={'url': url, "waitForResponse": 'true', 'device': device})

    result_url = r.url

    running_info = json.loads(r.text)
    test_id = running_info['runId']

    running_status = 'running'
    while running_status == 'running':
        running_json = httpRequestGetContent(
            '{0}/api/runs/{1}'.format(ylt_server_address, test_id))
        running_info = json.loads(running_json)
        running_status = running_info['status']['statusCode']
        time.sleep(time_sleep)

    result_json = httpRequestGetContent(
        '{0}/api/results/{1}?exclude=toolsResults'.format(ylt_server_address, test_id))

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
