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
    points = 5.0
    review = ''
    return_dict = dict()

    language = gettext.translation(
        'privacy_webbkollen', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

    url = 'https://webbkoll.dataskydd.net/{1}/check?url={0}'.format(
        url.replace('/', '%2F').replace(':', '%3A'), langCode)
    headers = {
        'user-agent': 'Mozilla/5.0 (compatible; Webperf; +https://webperf.se)'}
    request = requests.get(url, allow_redirects=True,
                           headers=headers, timeout=request_timeout)

    time.sleep(20)

    # hämta det faktiska resultatet
    soup2 = BeautifulSoup(request.text, 'html.parser')
    # final_url = None
    # for link in soup.find_all('a'):
    #    final_url = 'https://webbkoll.dataskydd.net{0}'.format(
    #        link.get('href'))

    if True:  # final_url != None:
        # request2 = requests.get(
        #    final_url, allow_redirects=True, headers=headers, timeout=request_timeout*2)
        # soup2 = BeautifulSoup(request2.text, 'html.parser')
        summary = soup2.find_all("div", class_="summary")
        results = soup2.find_all(class_="result")
        result_title = soup2.find(id="results-title")
        if not result_title:
            print(
                'Error! Unfortunately the request for URL "{0}" failed, message:\nUnexpected result')
            return (-1.0, '* TEST FAILED', return_dict)

        review_messages = ''

        for result in results:
            header = result.find("h3")
            header_id = header.get('id')
            if header_id == 'what' or header_id == 'raw-headers':
                continue
            # print(type(header.contents))
            number_of_success = len(header.find_all("i", class_="success"))

            # - alert
            number_of_alerts = len(header.find_all("i", class_="alert"))
            points -= (number_of_alerts * 1.0)

            # - warning
            number_of_warnings = len(header.find_all("i", class_="warning"))
            points -= (number_of_warnings * 1.0)

            number_of_sub_alerts = 0
            number_of_sub_warnings = 0
            divs = result.find_all("div")

            more_info = ''
            if len(divs) > 0:
                div = divs[0]
                # print(type(h3a.contents))
                # -- alert
                number_of_sub_alerts = len(div.find_all("i", class_="alert"))
                points -= (number_of_sub_alerts * 0.1)
                # -- warning
                number_of_sub_warnings = len(
                    div.find_all("i", class_="warning"))
                points -= (number_of_sub_warnings * 0.05)

            paragraphs = result.find_all("p")
            if len(paragraphs) > 0:
                for paragraph_text in paragraphs[0].strings:
                    more_info += paragraph_text + " "
            else:
                more_info = "!" + result.text
            more_info = more_info.replace("  ", " ").strip()

            review_messages += '* ' + header.text.strip()
            if number_of_success > 0:
                review_messages += ": VERY_GOOD.\n"
            elif number_of_alerts > 0:
                review_messages += ": VERY_BAD.\n"
            elif number_of_warnings > 0:
                review_messages += ": BAD.\n"
            elif number_of_sub_alerts > 0 and number_of_sub_warnings > 0:
                review_messages += ": BAD, with {0} error(s) and {1} warning(s).\n".format(
                    number_of_sub_alerts, number_of_sub_warnings)
            elif number_of_sub_alerts > 0:
                review_messages += ": OK, but with {0} error(s).\n".format(
                    number_of_sub_alerts)
            elif number_of_sub_warnings > 0:
                review_messages += ": GOOD, but with {0} warning(s).".format(
                    number_of_sub_warnings)
            else:
                review_messages += ": " + more_info + "\n"

        # give us result date (for when dataskydd.net generated report)
        result_title_beta = result_title.find_all('div', class_="beta")
        if len(result_title_beta) > 0:
            for header_info in result_title_beta[0].strings:
                info = header_info.strip()
                if info.startswith('20'):
                    review_messages += "* GENERATED: " + info + ".\n"

        #review_messages += "\nAdditional info:\n"
        # for line in summary:
        #    review_messages += '* {0}'.format(re.sub(' +', ' ', line.text.strip()).replace(
        #        '\n', ' ').replace('    ', '\n* ').replace('Kolla upp', '').replace('Look up', '').replace('  ', ' '))

        if points == 5:
            review = ('TEXT_REVIEW_VERY_GOOD')
        elif points >= 4:
            review = _('TEXT_REVIEW_IS_GOOD')
        elif points >= 3:
            review = _('TEXT_REVIEW_IS_OK')
        elif points >= 2:
            review = _('TEXT_REVIEW_IS_BAD')
        else:
            review = _('TEXT_REVIEW_IS_VERY_BAD')
            points = 1.0

        review += review_messages

        return (points, review, return_dict)
