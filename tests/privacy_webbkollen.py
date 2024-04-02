# -*- coding: utf-8 -*-
from datetime import datetime
import time
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import re
import requests
from bs4 import BeautifulSoup
from models import Rating
from tests.utils import get_config_or_default, get_translation


# DEFAULTS
regex_allowed_chars = r"[^\u00E5\u00E4\u00F6\u00C5\u00C4\u00D6a-zA-Zå-öÅ-Ö 0-9\-:\/]+"
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
time_sleep = get_config_or_default('WEBBKOLL_SLEEP')
if time_sleep < 5:
    time_sleep = 5
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')

def run_test(global_translation, lang_code, url):
    points = 5.0
    review = ''
    return_dict = {}
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    local_translation = get_translation('privacy_webbkollen', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    orginal_url = url
    url = 'https://webbkoll.dataskydd.net/{1}/check?url={0}'.format(
        urllib.parse.quote(url), lang_code)
    headers = {
        'user-agent': 'Mozilla/5.0 (compatible; Webperf; +https://webperf.se)'}

    has_refresh_statement = True
    had_refresh_statement = False
    session = requests.Session()
    while has_refresh_statement:
        has_refresh_statement = False
        request = session.get(url, allow_redirects=True,
                              headers=headers, timeout=REQUEST_TIMEOUT)

        if 'type="search" value="{0}">'.format(orginal_url) in request.text:
            # headers[''] = ''
            regex = r"_csrf_token[^>]*value=\"(?P<csrf>[^\"]+)\""
            matches = re.finditer(regex, request.text, re.MULTILINE)
            csrf_value = ''
            for _, match in enumerate(matches, start=1):
                csrf_value = match.group('csrf')

            data = {
                '_csrf_token': csrf_value,
                'url': orginal_url,
                'submit': ''}
            service_url = 'https://webbkoll.dataskydd.net/{0}/check'.format(
                lang_code)
            request = session.post(service_url, allow_redirects=True,
                                   headers=headers, timeout=REQUEST_TIMEOUT, data=data)

        if '<meta http-equiv="refresh"' in request.text:
            has_refresh_statement = True
            had_refresh_statement = True
            print(local_translation('TEXT_RESULT_NOT_READY').format(
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

        heading_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

        number_of_success = len(header.find_all("span", class_="success"))

        # - alert
        number_of_alerts = len(header.find_all("span", class_="alert"))
        points_to_remove_for_current_result += (number_of_alerts * 5.0)

        # - warning
        number_of_warnings = len(header.find_all("span", class_="warning"))
        points_to_remove_for_current_result += (number_of_warnings * 2.5)

        number_of_sub_alerts = 0
        number_of_sub_warnings = 0
        divs = result.find_all("div")

        more_info = ''
        if len(divs) > 0:
            div = divs[0]
            # -- alert
            number_of_sub_alerts = len(div.find_all("span", class_="alert"))
            points_to_remove_for_current_result += (
                number_of_sub_alerts * 0.5)
            # -- warning
            number_of_sub_warnings = len(
                div.find_all("span", class_="warning"))
            points_to_remove_for_current_result += (
                number_of_sub_warnings * 0.25)

        paragraphs = result.find_all("p")
        if len(paragraphs) > 0:
            for paragraph_text in paragraphs[0].strings:
                more_info += re.sub(regex_allowed_chars, '',
                                    paragraph_text, 0, re.MULTILINE) + " "
        else:
            more_info = "!" + re.sub(regex_allowed_chars, '',
                                     result.text, 0, re.MULTILINE)
        more_info = more_info.replace("  ", " ").strip()

        points_for_current_result = 5.0

        # only try to remove points if we have more then one
        if points_to_remove_for_current_result > 0.0:
            points_for_current_result -= points_to_remove_for_current_result
            points -= points_to_remove_for_current_result

        if points_for_current_result < 1.0:
            points_for_current_result = 1.0

        # add review info
        review_messages += '- ' + re.sub(regex_allowed_chars, '',
                                         header.text, 0, re.MULTILINE).strip()

        if number_of_success > 0 and number_of_sub_alerts == 0 and number_of_sub_warnings == 0:
            review_messages += local_translation('TEXT_REVIEW_CATEGORY_VERY_GOOD')
        elif number_of_alerts > 0:
            review_messages += local_translation('TEXT_REVIEW_CATEGORY_IS_VERY_BAD').format(
                0)
        elif number_of_warnings > 0:
            review_messages += local_translation('TEXT_REVIEW_CATEGORY_IS_BAD').format(
                0)
        elif number_of_sub_alerts > 0 and number_of_sub_warnings > 0:
            review_messages += local_translation('TEXT_REVIEW_CATEGORY_IS_OK').format(
                number_of_sub_alerts, number_of_sub_warnings, 0)
        elif number_of_sub_alerts > 0:
            review_messages += local_translation('TEXT_REVIEW_CATEGORY_IS_OK').format(
                number_of_sub_alerts, number_of_sub_warnings, 0)
        elif number_of_sub_warnings > 0:
            review_messages += local_translation('TEXT_REVIEW_CATEGORY_IS_GOOD').format(
                number_of_sub_warnings, 0)
        elif header_id == 'headers' or header_id == 'cookies':
            review_messages += local_translation('TEXT_REVIEW_CATEGORY_VERY_GOOD')
        else:
            review_messages += ": " + more_info

        heading_rating.set_integrity_and_security(
            points_for_current_result, review_messages)
        rating += heading_rating

    points = rating.get_integrity_and_security()
    if points >= 5:
        review = local_translation('TEXT_REVIEW_VERY_GOOD') + review
    elif points >= 4:
        review = local_translation('TEXT_REVIEW_IS_GOOD') + review
    elif points >= 3:
        review = local_translation('TEXT_REVIEW_IS_OK') + review
    elif points >= 2:
        review = local_translation('TEXT_REVIEW_IS_BAD') + review
    elif points >= 1:
        review = local_translation('TEXT_REVIEW_IS_VERY_BAD') + review
    else:
        review = local_translation('TEXT_REVIEW_IS_VERY_BAD') + review
        points = 1.0

    # give us result date (for when dataskydd.net generated report)
    result_title_beta = result_title.find_all('div', class_="beta")
    if len(result_title_beta) > 0:
        for header_info in result_title_beta[0].strings:
            info = re.sub(regex_allowed_chars, '',
                          header_info, 0, re.MULTILINE).strip()
            if info.startswith('20'):
                review += local_translation('TEXT_REVIEW_GENERATED').format(info)

    # review += review_messages

    rating.set_overall(points)
    rating.overall_review = review

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)
