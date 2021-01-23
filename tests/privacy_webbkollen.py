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
time_sleep = config.webbkoll_sleep
if time_sleep < 5:
    time_sleep = 5


def run_test(langCode, url):
    import time
    points = 5.0
    review = ''
    return_dict = dict()

    language = gettext.translation(
        'privacy_webbkollen', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

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
            print(_('TEXT_RESULT_NOT_READY').format(
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
        return (-1.0, '* TEST FAILED', return_dict)

    review_messages = ''

    for result in results:
        points_to_remove_for_current_result = 0.0
        header = result.find("h3")
        header_id = header.get('id')
        if header_id == 'what' or header_id == 'raw-headers':
            continue

        number_of_success = len(header.find_all("i", class_="success"))

        # - alert
        number_of_alerts = len(header.find_all("i", class_="alert"))
        points_to_remove_for_current_result += (number_of_alerts * 1.0)

        # - warning
        number_of_warnings = len(header.find_all("i", class_="warning"))
        points_to_remove_for_current_result += (number_of_warnings * 0.5)

        number_of_sub_alerts = 0
        number_of_sub_warnings = 0
        divs = result.find_all("div")

        more_info = ''
        if len(divs) > 0:
            div = divs[0]
            # -- alert
            number_of_sub_alerts = len(div.find_all("i", class_="alert"))
            points_to_remove_for_current_result += (
                number_of_sub_alerts * 0.1)
            # -- warning
            number_of_sub_warnings = len(
                div.find_all("i", class_="warning"))
            points_to_remove_for_current_result += (
                number_of_sub_warnings * 0.05)

        paragraphs = result.find_all("p")
        if len(paragraphs) > 0:
            for paragraph_text in paragraphs[0].strings:
                more_info += paragraph_text + " "
        else:
            more_info = "!" + result.text
        more_info = more_info.replace("  ", " ").strip()

        # make sure every category can max remove 1.0 points
        if points_to_remove_for_current_result > 1.0:
            points_to_remove_for_current_result = 1.0

        # only try to remove points if we have more then one
        if points_to_remove_for_current_result > 0.0:
            points -= points_to_remove_for_current_result

        # add review info
        review_messages += '* ' + header.text.strip()
        if number_of_success > 0 and number_of_sub_alerts == 0 and number_of_sub_warnings == 0:
            review_messages += _('TEXT_REVIEW_CATEGORY_VERY_GOOD')
        elif number_of_alerts > 0:
            review_messages += _('TEXT_REVIEW_CATEGORY_IS_VERY_BAD').format(
                points_to_remove_for_current_result)
        elif number_of_warnings > 0:
            review_messages += _('TEXT_REVIEW_CATEGORY_IS_BAD').format(
                points_to_remove_for_current_result)
        elif number_of_sub_alerts > 0 and number_of_sub_warnings > 0:
            review_messages += _('TEXT_REVIEW_CATEGORY_IS_OK').format(
                number_of_sub_alerts, number_of_sub_warnings, points_to_remove_for_current_result)
        elif number_of_sub_alerts > 0:
            review_messages += _('TEXT_REVIEW_CATEGORY_IS_OK').format(
                number_of_sub_alerts, number_of_sub_warnings, points_to_remove_for_current_result)
        elif number_of_sub_warnings > 0:
            review_messages += _('TEXT_REVIEW_CATEGORY_IS_GOOD').format(
                number_of_sub_warnings, points_to_remove_for_current_result)
        else:
            review_messages += ": " + more_info + "\n"

    # give us result date (for when dataskydd.net generated report)
    result_title_beta = result_title.find_all('div', class_="beta")
    if len(result_title_beta) > 0:
        for header_info in result_title_beta[0].strings:
            info = header_info.strip()
            if info.startswith('20'):
                review_messages += _('TEXT_REVIEW_GENERATED').format(info)

    if points == 5:
        review = _('TEXT_REVIEW_VERY_GOOD')
    elif points >= 4:
        review = _('TEXT_REVIEW_IS_GOOD')
    elif points >= 3:
        review = _('TEXT_REVIEW_IS_OK')
    elif points >= 2:
        review = _('TEXT_REVIEW_IS_BAD')
    elif points >= 1:
        review = _('TEXT_REVIEW_IS_VERY_BAD')
    else:
        review = _('TEXT_REVIEW_IS_VERY_BAD')
        points = 1.0

    review += review_messages

    return (float("{0:.2f}".format(points)), review, return_dict)
