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
request_timeout = config.http_request_timeout
useragent = config.useragent


def run_test(langCode, url):
    import time

    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    points = 5.0
    review = ''
    result_dict = {}

    language = gettext.translation(
        'http_validator', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

    # kollar koden
    o = urllib.parse.urlparse(url)
    host = o.netloc
    url = 'https://http3check.net/?host={0}'.format(host)
    headers = {'user-agent': useragent}
    request = requests.get(url, allow_redirects=True,
                           headers=headers, timeout=request_timeout)

    # We use variable to validate it once
    requestText = ''
    hasRequestText = False
    has_quic_support = False
    has_http3_support = False

    if request.text:
        requestText = request.text
        hasRequestText = True

    if hasRequestText:
        soup = BeautifulSoup(requestText, 'lxml')
        # try:
        #    title = soup.find('title')
        #    if title:
        #        result_dict['page_title'] = title.string
        #    else:
        #        review = review + _('TEXT_REVIEW_NO_TITLE')
        #
        # except:
        #    print('Error getting page title!\nMessage:\n{0}'.format(sys.exc_info()[0]))

        try:
            elements_success = soup.find_all(
                class_="uk-text-success")
            for result in elements_success:
                supportText = result.text.lower()
                has_quic_support = has_quic_support or 'quic' in supportText
                has_http3_support = has_quic_support or 'http/3' in supportText

        except:
            print('Error getting H1!\nMessage:\n{0}'.format(sys.exc_info()[0]))

        if has_quic_support:
            review += _('TEXT_REVIEW_HTTP_VERSION_QUICK')
            points = 5.0

        if has_http3_support:
            review += _('TEXT_REVIEW_HTTP_VERSION_HTTP_3')
            points = 5.0

    if points == 0:
        points = 1.0

    time.sleep(30)

    return (points, review, result_dict)
