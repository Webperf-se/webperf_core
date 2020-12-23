# -*- coding: utf-8 -*-
import sys
import socket
import ssl
import json
import requests
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
import json
from bs4 import BeautifulSoup
import config
from tests.utils import *
import gettext
_ = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent


def run_test(langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    points = 0.0
    review = ''

    language = gettext.translation(
        'css_validator_w3c', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

    # kollar koden
    try:
        url = ('https://jigsaw.w3.org/css-validator/validator?uri={0}&output=json&profile=css3svg&usermedium=all&warning=1&vextwarning=&lang=' + langCode).format(
            url.replace('/', '%2F').replace(':', '%3A'))
        headers = {'user-agent': useragent}
        request = requests.get(url, allow_redirects=False,
                               headers=headers, timeout=request_timeout)

        # hämta HTML
        response = json.loads(request.text)
        errors = {}
        number_of_errors = 0

        if 'cssvalidation' in response and 'errors' in response['cssvalidation']:
            errors = response['cssvalidation']['errors']
            number_of_errors = len(errors)

    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None

    if number_of_errors == 0:
        points = 5.0
        review = _('TEXT_REVIEW_CSS_VERY_GOOD')
    elif number_of_errors <= 5:
        points = 4.0
        review = _('TEXT_REVIEW_CSS_IS_GOOD').format(number_of_errors)
    elif number_of_errors <= 10:
        points = 3.0
        review = _('TEXT_REVIEW_CSS_IS_OK').format(number_of_errors)
    elif number_of_errors <= 20:
        points = 2.0
        review = _('TEXT_REVIEW_CSS_IS_BAD').format(number_of_errors)
    elif number_of_errors > 20:
        points = 1.0
        review = _('TEXT_REVIEW_CSS_IS_VERY_BAD').format(number_of_errors)

    error_message_dict = {}
    error_message_grouped_dict = {}
    if number_of_errors > 0:
        regex = r"(“[^”]+”)"
        regex2 = r" at line [0-9]+\, column [0-9]+\."
        for item in errors:
            error_message_dict[item['message']] = "1"
            error_message = item['message']
            error_message = re.sub(
                regex, "X", error_message, 0, re.MULTILINE)

            error_message = re.sub(
                regex2, ".", error_message, 0, re.MULTILINE)

            if error_message_grouped_dict.get(error_message, False):
                error_message_grouped_dict[error_message] = error_message_grouped_dict[error_message] + 1
            else:
                error_message_grouped_dict[error_message] = 1

        if len(error_message_grouped_dict) > 0:
            review += _('TEXT_REVIEW_ERRORS_GROUPED')
            error_message_grouped_sorted = sorted(
                error_message_grouped_dict.items(), key=lambda x: x[1], reverse=True)

            for item in error_message_grouped_sorted:

                item_value = item[1]
                item_text = item[0]

                review += _('TEXT_REVIEW_ERRORS_ITEM').format(item_text, error_message_grouped_dict.get(
                    item_text, 0))

    return (points, review, error_message_dict)
