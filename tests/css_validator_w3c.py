# -*- coding: utf-8 -*-
import time
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

    # TODO:
    # 1. Get ROOT PAGE HTML
    html = get_source(url)
    # 2. FIND ALL INLE CSS (AND CALCULTE)
    # 2.1 FINS ALL <STYLE>
    regex = r"<style.*>(?P<css>[^<]+)<\/style>"
    matches = re.finditer(regex, html, re.MULTILINE)
    results = list()
    for matchNum, match in enumerate(matches, start=1):
        inline_style = match.group('css')
        print('style-tag:')
        result_inline_css = calculate_rating_for_markup(inline_style, _)
        results.append(result_inline_css)
        #print('result_inline_css:', result_inline_css[0])
    # 2.2 FIND ALL style=""
    #   regex = r"<(?P<tag>[a-z0-1]+) .*style=[\"|'](?P<css>[^\"|']+)"
    # 2.3 GET ERRORS FROM SERVICE
    # 2.4 CALCULATE SCORE
    # 3 FIND ALL <LINK> (rel=\"stylesheet\")
    regex = r"(?P<markup><link.*(href|src)=[\"|'](?P<resource>[^\"|']+)[^>]*>)"
    matches = re.finditer(regex, html, re.MULTILINE)
    results = list()

    o = urllib.parse.urlparse(url)
    parsed_url = '{0}://{1}'.format(o.scheme, o.netloc)
    parsed_url_scheme = o.scheme

    for matchNum, match in enumerate(matches, start=1):
        markup = match.group('markup')
        if 'stylesheet' in markup:
            resource_url = match.group('resource')
            if resource_url.startswith('//'):
                # do nothing, complete url
                resource_url = parsed_url_scheme + ':' + resource_url
                #print('- do nothing, complete url')
            elif resource_url.startswith('/'):
                # relative url, complement with dns
                resource_url = parsed_url + resource_url
                #print('- relative url, complement with dns')
            elif resource_url.startswith('http://') or resource_url.startswith('https://'):
                resource_url = resource_url
            else:
                # relative url, but without starting /
                resource_url = parsed_url + '/' + resource_url

            print('resource_url:', resource_url)
            # 3.1 GET ERRORS FROM SERVICE (FOR EVERY <LINK>)
            result_link_css = calculate_rating_for_resource(resource_url, _)
            results.append(result_link_css)
            time.sleep(5)

    # 3.2 CALCULATE SCORE
    # 4 COMBINE SCORE(s)
    number_of_results = len(results)
    points = 0.0
    error_message_dict = {}
    for result in results:
        points += result[0]
        review += result[1]
        #print('result[i]:', result)

    points = points / number_of_results

    #points = result_page[0]
    #review += result_page[1]
    #error_message_dict = result_page[2]

    if points == 5.0:
        review = _('TEXT_REVIEW_CSS_VERY_GOOD') + review
    elif points >= 4.0:
        review = _('TEXT_REVIEW_CSS_IS_GOOD') + review
    elif points >= 3.0:
        review = _('TEXT_REVIEW_CSS_IS_OK') + review
    elif points > 1.0:
        review = _('TEXT_REVIEW_CSS_IS_BAD') + review
    elif points <= 1.0:
        review = _('TEXT_REVIEW_CSS_IS_VERY_BAD') + review

    return (points, review, error_message_dict)


def calculate_rating(number_of_error_types, number_of_errors):
    rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)

    rating_number_of_errors = ((number_of_errors / 2.0) / 5.0)

    rating_result = float("{0:.2f}".format(
        rating_number_of_error_types - rating_number_of_errors))
    if rating_result < 1.0:
        rating_result = 1.0

    return (rating_result, rating_number_of_error_types, rating_number_of_errors)


def get_errors_for_url(url):
    try:
        service_url = 'https://validator.w3.org/nu/'
        headers = {'user-agent': useragent}
        params = {'doc': url, 'out': 'json', 'level': 'error'}
        request = requests.get(service_url, allow_redirects=True,
                               headers=headers,
                               timeout=request_timeout,
                               params=params)

        # get JSON
        response = json.loads(request.text)
        errors = response['messages']
        # errors = list()
        # for message in response['messages']:
        #   if message.get('type') == 'error':
        #     errors.append(message)

        return errors
        # print(len(errors))
    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None


def get_errors_for_css(data):
    try:
        data = data.strip()

        # service_url = 'https://validator.w3.org/nu/'
        # headers = {'user-agent': useragent,
        #           'Content-Type': 'text/css; charset=utf-8'}
        # params = {'showsource': 'yes', 'css': 'yes',
        #          'out': 'json', 'level': 'error'}
        # request = requests.post(service_url, allow_redirects=True,
        #                        headers=headers,
        #                        params=params,
        #                        timeout=request_timeout,
        #                        files={'content': data.encode('utf-8')}
        #                        )

        service_url = 'https://validator.w3.org/nu/'
        headers = {'user-agent': useragent,
                   'Content-Type': 'text/css; charset=utf-8'}
        params = {'showsource': 'yes', 'css': 'yes',
                  'out': 'json', 'level': 'error'}
        request = requests.post(service_url, allow_redirects=True,
                                headers=headers,
                                params=params,
                                timeout=request_timeout,
                                data=data.encode('utf-8')
                                )

        # get JSON
        # print(request.text)
        response = json.loads(request.text)
        errors = response['messages']

        #print('source:', response['source']['code'])
        # errors = list()
        # for message in response['messages']:
        #   if message.get('type') == 'error':
        #     errors.append(message)

        return errors
        # print(len(errors))
    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None


def calculate_rating_for_markup(data, _):
    errors = get_errors_for_css(data)
    result = create_review_and_rating(errors, _)
    return result


def calculate_rating_for_resource(url, _):
    errors = get_errors_for_url(url)
    result = create_review_and_rating(errors, _)
    return result


def create_review_and_rating(errors, _):
    review = ''
    whitelisted_words = ['font-display',
                         'font-variation-settings', 'font-stretch']

    number_of_errors = len(errors)

    error_message_dict = {}
    error_message_grouped_dict = {}
    if number_of_errors > 0:
        regex = r"(“[^”]+”)"
        for item in errors:
            error_message = item['message']
            is_whitelisted = False
            for whitelisted_word in whitelisted_words:
                if whitelisted_word in error_message:
                    is_whitelisted = True
                    number_of_errors -= 1
                    break

            if not is_whitelisted:
                error_message_dict[error_message] = "1"

                print(' - error-message:', error_message)

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

    print(' - number_of_errors:', number_of_errors)

    number_of_error_types = len(error_message_grouped_dict)

    result = calculate_rating(number_of_error_types, number_of_errors)

    if number_of_errors > 0:
        review = _('TEXT_REVIEW_RATING_ITEMS').format(number_of_errors,
                                                      result[2]) + review
    if number_of_error_types > 0:
        review = _('TEXT_REVIEW_RATING_GROUPED').format(
            number_of_error_types, result[1]) + review

    points = result[0]
    return (points, review, error_message_dict)


def get_source(url):
    try:
        headers = {'user-agent': useragent}
        request = requests.get(url, allow_redirects=True,
                               headers=headers,
                               timeout=request_timeout)

        # get source
        return request.text

    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None
