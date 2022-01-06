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
review_show_improvements_only = config.review_show_improvements_only


def run_test(_, langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    rating = Rating(_)
    result_dict = {}

    language = gettext.translation(
        'page_not_found', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # kollar koden
    o = urllib.parse.urlparse(url)
    url = '{0}://{1}/{3}/{2}'.format(o.scheme, o.netloc,
                                     'finns-det-en-sida/pa-den-har-adressen/testanrop/', get_guid(5))
    headers = {'user-agent': useragent,
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'}
    code = 'unknown'
    request = False
    try:
        request = requests.get(url, allow_redirects=True,
                               headers=headers, timeout=request_timeout)
        code = request.status_code
    except Exception:
        code = 'unknown'
    rating_404 = Rating(_, review_show_improvements_only)
    if code == 404:
        rating_404.set_overall(5.0, _local(
            'TEXT_REVIEW_WRONG_STATUS_CODE').format(code))
        rating_404.set_standards(5.0, _local(
            'TEXT_REVIEW_WRONG_STATUS_CODE').format(code))
    else:
        rating_404.set_overall(
            1.0, _local('TEXT_REVIEW_WRONG_STATUS_CODE').format(code))
        rating_404.set_standards(
            1.0, _local('TEXT_REVIEW_WRONG_STATUS_CODE').format(code))
    rating += rating_404

    result_dict['status_code'] = code

    # We use variable to validate it once
    requestText = ''
    hasRequestText = False
    found_match = False

    if request != False:
        if request.text:
            requestText = request.text
            hasRequestText = True

    if hasRequestText:
        soup = BeautifulSoup(requestText, 'lxml')
        rating_title = Rating(_, review_show_improvements_only)
        try:
            title = soup.find('title')
            if title:
                result_dict['page_title'] = title.string
                rating_title.set_overall(5.0, _local('TEXT_REVIEW_NO_TITLE'))
                rating_title.set_standards(5.0, _local('TEXT_REVIEW_NO_TITLE'))
                rating_title.set_a11y(5.0, _local('TEXT_REVIEW_NO_TITLE'))
            else:
                rating_title.set_overall(1.0, _local('TEXT_REVIEW_NO_TITLE'))
                rating_title.set_standards(1.0, _local('TEXT_REVIEW_NO_TITLE'))
                rating_title.set_a11y(1.0, _local('TEXT_REVIEW_NO_TITLE'))

        except:
            print('Error getting page title!\nMessage:\n{0}'.format(
                sys.exc_info()[0]))
            rating_title.set_overall(1.0, _local('TEXT_REVIEW_NO_TITLE'))
            rating_title.set_standards(1.0, _local('TEXT_REVIEW_NO_TITLE'))
            rating_title.set_a11y(1.0, _local('TEXT_REVIEW_NO_TITLE'))
        rating += rating_title

        rating_h1 = Rating(_, review_show_improvements_only)
        try:
            h1 = soup.find('h1')
            if h1:
                result_dict['h1'] = h1.string
                rating_h1.set_overall(5.0, _local('TEXT_REVIEW_MAIN_HEADER'))
                rating_h1.set_standards(5.0, _local('TEXT_REVIEW_MAIN_HEADER'))
                rating_h1.set_a11y(5.0, _local('TEXT_REVIEW_MAIN_HEADER'))
            else:
                rating_h1.set_overall(1.0, _local('TEXT_REVIEW_MAIN_HEADER'))
                rating_h1.set_standards(1.0, _local('TEXT_REVIEW_MAIN_HEADER'))
                rating_h1.set_a11y(1.0, _local('TEXT_REVIEW_MAIN_HEADER'))

        except:
            print('Error getting H1!\nMessage:\n{0}'.format(sys.exc_info()[0]))

        rating += rating_h1

        # kollar innehållet
        four_o_four_strings = []
        four_o_four_strings.append('saknas')
        four_o_four_strings.append('finns inte')
        four_o_four_strings.append('inga resultat')
        four_o_four_strings.append('inte hittas')
        four_o_four_strings.append('inte hitta')
        four_o_four_strings.append('kunde inte')
        four_o_four_strings.append('kunde ej')
        four_o_four_strings.append('hittades inte')
        four_o_four_strings.append('hittar inte')
        four_o_four_strings.append('hittade vi inte')
        four_o_four_strings.append('hittar vi inte')
        four_o_four_strings.append('hittades tyvärr inte')
        four_o_four_strings.append('tagits bort')
        four_o_four_strings.append('fel adress')
        four_o_four_strings.append('trasig')
        four_o_four_strings.append('inte hitta')
        four_o_four_strings.append('ej hitta')
        four_o_four_strings.append('ingen sida')
        four_o_four_strings.append('borttagen')
        four_o_four_strings.append('flyttad')
        four_o_four_strings.append('inga resultat')
        four_o_four_strings.append('inte tillgänglig')
        four_o_four_strings.append('inte sidan')
        four_o_four_strings.append('kontrollera adressen')
        four_o_four_strings.append('kommit utanför')
        four_o_four_strings.append('gick fel')
        four_o_four_strings.append('blev något fel')
        four_o_four_strings.append('kan inte nås')
        four_o_four_strings.append('gammal sida')
        four_o_four_strings.append('hoppsan')
        four_o_four_strings.append('finns inte')
        four_o_four_strings.append('finns ej')
        four_o_four_strings.append('byggt om')
        four_o_four_strings.append('inte finns')
        four_o_four_strings.append('inte fungera')
        four_o_four_strings.append('ursäkta')
        four_o_four_strings.append('uppstått ett fel')
        four_o_four_strings.append('gick fel')

        # print(four_o_four_strings)
        text_from_page = requestText.lower()

        # print(text_from_page)

        for item in four_o_four_strings:
            if item in text_from_page:
                #points += 1.5
                found_match = True
                break

    rating_swedish_text = Rating(_, review_show_improvements_only)
    if found_match:
        rating_swedish_text.set_overall(
            5.0, _local('TEXT_REVIEW_NO_SWEDISH_ERROR_MSG'))
        rating_swedish_text.set_a11y(5.0, _local(
            'TEXT_REVIEW_NO_SWEDISH_ERROR_MSG'))
    else:
        rating_swedish_text.set_overall(
            1.0, _local('TEXT_REVIEW_NO_SWEDISH_ERROR_MSG'))
        rating_swedish_text.set_a11y(
            1.0, _local('TEXT_REVIEW_NO_SWEDISH_ERROR_MSG'))
    rating += rating_swedish_text

    # hur långt är inehållet
    rating_text_is_150_or_more = Rating(_, review_show_improvements_only)
    soup = BeautifulSoup(requestText, 'html.parser')
    if len(soup.get_text()) > 150:
        rating_text_is_150_or_more.set_overall(
            5.0, _local('TEXT_REVIEW_ERROR_MSG_UNDER_150'))
        rating_text_is_150_or_more.set_a11y(
            5.0, _local('TEXT_REVIEW_ERROR_MSG_UNDER_150'))
    else:
        # '* Information är under 150 tecken, vilket tyder på att användaren inte vägleds vidare.\n'
        rating_text_is_150_or_more.set_overall(
            1.0, _local('TEXT_REVIEW_ERROR_MSG_UNDER_150'))
        rating_text_is_150_or_more.set_a11y(
            1.0, _local('TEXT_REVIEW_ERROR_MSG_UNDER_150'))
    rating += rating_text_is_150_or_more

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)
