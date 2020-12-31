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
        'html_validator_w3c', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

    # kollar koden
    try:
        url = 'https://validator.w3.org/nu/?doc={0}'.format(
            url.replace('/', '%2F').replace(':', '%3A'))
        headers = {'user-agent': useragent}
        params = {'out': 'json'}
        request = requests.get(url, allow_redirects=False,
                               headers=headers,
                               timeout=request_timeout,
                               params=params)

        # get JSON
        response = json.loads(request.text)
        errors = response['messages']
        number_of_errors = len(errors)
        # print(len(errors))
    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None

    error_message_dict = {}
    error_message_grouped_dict = {}
    if number_of_errors > 0:
        regex = r"(“[^”]+”)"
        for item in errors:
            error_message_dict[item['message']] = "1"
            error_message = item['message']
            error_message = re.sub(
                regex, "X", error_message, 0, re.MULTILINE)

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

                review += _('TEXT_REVIEW_ERRORS_ITEM').format(item_text, item_value)

    number_of_error_types = len(error_message_grouped_dict)

    points = calculate_rating(number_of_error_types, number_of_errors)

    if points == 5.0:
        review = _('TEXT_REVIEW_HTML_VERY_GOOD')
    elif points >= 4.0:
        review = _('TEXT_REVIEW_HTML_IS_GOOD').format(number_of_errors)
    elif points >= 3.0:
        review = _('TEXT_REVIEW_HTML_IS_OK').format(number_of_errors)
    elif points > 1.0:
        review = _('TEXT_REVIEW_HTML_IS_BAD').format(number_of_errors)
    elif points <= 1.0:
        review = _('TEXT_REVIEW_HTML_IS_VERY_BAD').format(number_of_errors)

    return (points, review, error_message_dict)


def calculate_rating(number_of_error_types, number_of_errors):
    rating = 0.0

    rating = 5.0 - (number_of_error_types / 5.0)

    rating2 = ((number_of_errors / 2.0) / 5.0)

    rating3 = rating - rating2
    rating_result = rating3
    if rating3 < 1.0:
        rating_result = 1.0

    return rating_result
