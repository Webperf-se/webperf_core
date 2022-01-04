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
import config
from tests.utils import *
import gettext
_ = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
time_sleep = config.webbkoll_sleep
if time_sleep < 5:
    time_sleep = 5
review_show_improvements_only = config.review_show_improvements_only


def run_test(_, langCode, url):
    import time
    points = 5.0
    review = ''
    return_dict = dict()
    rating = Rating(_, review_show_improvements_only)

    language = gettext.translation(
        'privacy_webbkollen', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    orginal_url = url
    url = 'https://webbkoll.dataskydd.net/{1}/check?url={0}'.format(
        url.replace('/', '%2F').replace(':', '%3A'), langCode)
    headers = {
        'user-agent': 'Mozilla/5.0 (compatible; Webperf; +https://webperf.se)'}

    has_refresh_statement = True
    had_refresh_statement = False
    session = requests.Session()
    while has_refresh_statement:
        has_refresh_statement = False
        request = session.get(url, allow_redirects=True,
                              headers=headers, timeout=request_timeout)

        if 'type="search" value="{0}">'.format(orginal_url) in request.text:
            # headers[''] = ''
            regex = r"_csrf_token[^>]*value=\"(?P<csrf>[^\"]+)\""
            matches = re.finditer(regex, request.text, re.MULTILINE)
            csrf_value = ''
            for matchNum, match in enumerate(matches, start=1):
                csrf_value = match.group('csrf')

            data = {
                '_csrf_token': csrf_value,
                'url': orginal_url,
                'submit': ''}
            service_url = 'https://webbkoll.dataskydd.net/{0}/check'.format(
                langCode)
            request = session.post(service_url, allow_redirects=True,
                                   headers=headers, timeout=request_timeout, data=data)

        if '<meta http-equiv="refresh"' in request.text:
            has_refresh_statement = True
            had_refresh_statement = True
            print(_local('TEXT_RESULT_NOT_READY').format(
                time_sleep))
            time.sleep(time_sleep)

    if not had_refresh_statement:
        time.sleep(time_sleep)

    # hämta det faktiska resultatet
    soup2 = BeautifulSoup(request.text, 'html.parser')

    results = soup2.find_all(class_="result")
    result_title = soup2.find(id="results-title")
    if not result_title:
        print(
            'Error! Unfortunately the request for URL "{0}" failed, message:\nUnexpected result')
        print('request.text:' + request.text)
        return (rating, return_dict)

    #review_messages = ''

    for result in results:
        review_messages = ''
        points_to_remove_for_current_result = 0.0

        header = result.find("h3")
        header_id = header.get('id')
        if header_id == 'what' or header_id == 'raw-headers' or header_id == 'server-location' or header_id == 'localstorage' or header_id == 'requests':
            continue

        heading_rating = Rating(_, review_show_improvements_only)

        number_of_success = len(header.find_all("i", class_="success"))

        # - alert
        number_of_alerts = len(header.find_all("i", class_="alert"))
        points_to_remove_for_current_result += (number_of_alerts * 5.0)

        # - warning
        number_of_warnings = len(header.find_all("i", class_="warning"))
        points_to_remove_for_current_result += (number_of_warnings * 2.5)

        number_of_sub_alerts = 0
        number_of_sub_warnings = 0
        divs = result.find_all("div")

        more_info = ''
        if len(divs) > 0:
            div = divs[0]
            # -- alert
            number_of_sub_alerts = len(div.find_all("i", class_="alert"))
            points_to_remove_for_current_result += (
                number_of_sub_alerts * 0.5)
            # -- warning
            number_of_sub_warnings = len(
                div.find_all("i", class_="warning"))
            points_to_remove_for_current_result += (
                number_of_sub_warnings * 0.25)

        paragraphs = result.find_all("p")
        if len(paragraphs) > 0:
            for paragraph_text in paragraphs[0].strings:
                more_info += paragraph_text + " "
        else:
            more_info = "!" + result.text
        more_info = more_info.replace("  ", " ").strip()

        points_for_current_result = 5.0

        # only try to remove points if we have more then one
        if points_to_remove_for_current_result > 0.0:
            points_for_current_result -= points_to_remove_for_current_result
            points -= points_to_remove_for_current_result

        if points_for_current_result < 1.0:
            points_for_current_result = 1.0

        # add review info
        review_messages += '- ' + header.text.strip()
        if number_of_success > 0 and number_of_sub_alerts == 0 and number_of_sub_warnings == 0:
            review_messages += _local('TEXT_REVIEW_CATEGORY_VERY_GOOD')
        elif number_of_alerts > 0:
            review_messages += _local('TEXT_REVIEW_CATEGORY_IS_VERY_BAD').format(
                0)
        elif number_of_warnings > 0:
            review_messages += _local('TEXT_REVIEW_CATEGORY_IS_BAD').format(
                0)
        elif number_of_sub_alerts > 0 and number_of_sub_warnings > 0:
            review_messages += _local('TEXT_REVIEW_CATEGORY_IS_OK').format(
                number_of_sub_alerts, number_of_sub_warnings, 0)
        elif number_of_sub_alerts > 0:
            review_messages += _local('TEXT_REVIEW_CATEGORY_IS_OK').format(
                number_of_sub_alerts, number_of_sub_warnings, 0)
        elif number_of_sub_warnings > 0:
            review_messages += _local('TEXT_REVIEW_CATEGORY_IS_GOOD').format(
                number_of_sub_warnings, 0)
        elif header_id == 'headers' or header_id == 'cookies':
            review_messages += _local('TEXT_REVIEW_CATEGORY_VERY_GOOD')
        else:
            review_messages += ": " + more_info

        heading_rating.set_integrity_and_security(
            points_for_current_result, review_messages)
        rating += heading_rating

    points = rating.get_integrity_and_security()
    if points >= 5:
        review = _local('TEXT_REVIEW_VERY_GOOD') + review
    elif points >= 4:
        review = _local('TEXT_REVIEW_IS_GOOD') + review
    elif points >= 3:
        review = _local('TEXT_REVIEW_IS_OK') + review
    elif points >= 2:
        review = _local('TEXT_REVIEW_IS_BAD') + review
    elif points >= 1:
        review = _local('TEXT_REVIEW_IS_VERY_BAD') + review
    else:
        review = _local('TEXT_REVIEW_IS_VERY_BAD') + review
        points = 1.0

    # give us result date (for when dataskydd.net generated report)
    result_title_beta = result_title.find_all('div', class_="beta")
    if len(result_title_beta) > 0:
        for header_info in result_title_beta[0].strings:
            info = header_info.strip()
            if info.startswith('20'):
                review += _local('TEXT_REVIEW_GENERATED').format(info)

    # review += review_messages

    rating.set_overall(points)
    rating.overall_review = review

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)
