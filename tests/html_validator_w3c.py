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
useragent = config.useragent

def run_test(langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    points = 0.0
    review = ''

    language = gettext.translation('html_validator_w3c', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))
    
    ## kollar koden
    try:
        url = 'https://validator.w3.org/nu/?doc={0}'.format(url.replace('/', '%2F').replace(':', '%3A'))
        headers = {'user-agent': useragent}
        request = requests.get(url, allow_redirects=False, headers=headers, timeout=request_timeout)

        ## hämta HTML
        soup = BeautifulSoup(request.text, 'html.parser')
        errors = len(soup.find_all("li", {"class": "error"}))
        # print(len(errors))
    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None

    if errors == 0:
        points = 5.0
        review = _('TEXT_REVIEW_HTML_VERY_GOOD')
    elif errors <= 5:
        points = 4.0
        review = _('TEXT_REVIEW_HTML_IS_GOOD').format(errors)
    elif errors <= 15:
        points = 3.0
        review = _('TEXT_REVIEW_HTML_IS_OK').format(errors)
    elif errors <= 30:
        points = 2.0
        review = _('TEXT_REVIEW_HTML_IS_BAD').format(errors)
    elif errors > 30:
        points = 1.0
        review = _('TEXT_REVIEW_HTML_IS_VERY_BAD').format(errors)

    return (points, review)
