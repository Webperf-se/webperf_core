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
import time
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
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
    result_dict = {}

    language = gettext.translation(
        'page_not_found', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    # print(_('TEXT_RUNNING_TEST'))
    print(_('###############################\r\nRunning test: 23 - Tracking and Privacy\r\n###############################'))

    browser = False
    try:
        o = urllib.parse.urlparse(url)
        hostname = o.hostname

        browser = webdriver.Firefox()

        browser.get('https://pagexray.fouanalytics.com/')
        # print('title', browser.title)

        elem = browser.find_element(By.NAME, 'domain')  # Find the domain box
        elem.send_keys(url + Keys.RETURN)

        # wait for element(s) to appear
        wait = WebDriverWait(browser, 60, poll_frequency=5)
        wait.until(ec.visibility_of_element_located(
            (By.CLASS_NAME, 'adserver-request-count')))

        elem_ad_requests_count = browser.find_element(
            By.CLASS_NAME, 'adserver-request-count')  # Ad requests
        adserver_requests = int(elem_ad_requests_count.text[19:])

        elem_tracking_requests_count = browser.find_element(
            By.CLASS_NAME, 'tracking-request-count')  # tracking requests
        review += '* Tracking requests: {0}\r\n'.format(
            elem_tracking_requests_count.text[19:])

        elements_download_links = browser.find_elements_by_css_selector(
            'a[download]')  # download links

        number_of_download_links = len(elements_download_links)
        download_link_index = 0
        # for download_link in elements_download_links:
        while download_link_index < number_of_download_links:
            download_link = elements_download_links[download_link_index]
            download_link_index += 1
            download_link_text = download_link.text
            download_link_url = download_link.get_attribute(
                'href')
            if '.json' in download_link_url:
                download_link_content = httpRequestGetContent(
                    download_link_url, True)

            if 'Download detailed results' in download_link_text:
                #print('GET fingerprints, ads and cookies')
                result = check_detailed_results(
                    download_link_content, adserver_requests, hostname)
                points += result[0]
                review += result[1]

            if 'Download HTTP Archive' in download_link_text:
                #print('GET countries')
                result = check_har_results(download_link_content)
                points += result[0]
                review += result[1]

        # time.sleep(30)
    finally:
        if browser != False:
            browser.quit()

    # if found_match == False:
    #    review = review + _('TEXT_REVIEW_NO_SWEDISH_ERROR_MSG')

    # if len(review) == 0:
    #    review = _('TEXT_REVIEW_NO_REMARKS')

    if points == 0:
        points = 1.0

    return (points, review, result_dict)


def check_fingerprint(json_content):
    fingerprints = json_content['fingerprints']
    number_of_potential_fingerprints = len(fingerprints)
    fingerprints_index = 0
    fingerprints_points = 0.0
    number_of_fingerprints = 0
    fingerprints_review = '* Fingerprinting ({0} points)\r\n'.format(
        number_of_potential_fingerprints)
    if number_of_potential_fingerprints > 0:
        while fingerprints_index < number_of_potential_fingerprints:
            fingerprint = fingerprints[fingerprints_index]
            fingerprints_index += 1

            if 'level' in fingerprint and ('danger' in fingerprint['level'] or 'warning' in fingerprint['level']):
                fingerprints_review += '-- {0} ({1}): {2}\r\n'.format(
                    fingerprint['category'], fingerprint['level'], fingerprint['count'])
                fingerprints_points = 0.0
                number_of_fingerprints += 1

    if number_of_fingerprints == 0:
        fingerprints_points = 1.0
        fingerprints_review = '* Fingerprinting (+{0} points):\r\n-- No fingerprinting\r\n'.format(
            fingerprints_points)

    return (fingerprints_points, fingerprints_review)


def check_ads(json_content, adserver_requests):
    ads = json_content['ads']
    number_of_ads = len(ads)
    ads_index = 0
    ads_points = 0.0
    ads_review = ''
    if adserver_requests > 0 or number_of_ads > 0:
        ads_points = 0.0
        ads_review = '* Ads ({0} points)\r\n'.format(
            ads_points)
    else:
        ads_points = 1.0
        ads_review = '* Ads (+{0} points)\r\n-- No Adserver requests\r\n'.format(
            ads_points)

    if adserver_requests > 0:
        ads_review += '-- Adserver requests: {0}\r\n'.format(
            adserver_requests)

    if number_of_ads > 0:
        ads_review += '-- Visibile Ads: {0}\r\n'.format(
            number_of_ads)
        # while ads_index < number_of_ads:
        #     ad = ads[ads_index]
        #     ads_index += 1

        #     if 'bidder' in ad:
        #         ads_review += '---- {0} ({1})\r\n'.format(
        #             ad['bidder'], ads_index)

    return (ads_points, ads_review)


def check_cookies(json_content, hostname):
    from datetime import datetime
    cookies = json_content['cookies']
    number_of_potential_cookies = len(cookies)
    number_of_cookies = 0
    cookies_index = 0
    cookies_points = 0.0
    cookies_review = ''

    cookies_number_of_firstparties = 0
    cookies_number_of_thirdparties = 0
    cookies_number_of_httponly = 0
    cookies_number_of_secure = 0
    cookies_number_of_valid_over_3months = 0
    cookies_number_of_valid_over_6months = 0
    cookies_number_of_valid_over_9months = 0
    cookies_number_of_valid_over_1year = 0

    if number_of_potential_cookies > 0:
        while cookies_index < number_of_potential_cookies:
            cookie = cookies[cookies_index]
            cookies_index += 1

            if 'httpOnly' in cookie and cookie['httpOnly'] == False:
                cookies_number_of_httponly += 1

            if 'secure' in cookie and cookie['secure'] == False:
                cookies_number_of_secure += 1

            if 'domain' in cookie and cookie['domain'].endswith(hostname):
                cookies_number_of_firstparties += 1
                number_of_cookies += 1
            else:
                cookies_number_of_thirdparties += 1
                number_of_cookies += 1

            # if 'session' in cookie and cookie['session'] == False:
            #     if 'expires' in cookie:
            #         cookie_expires_timestamp = int(cookie['expires'])
            #         cookie_expires_date = datetime.fromtimestamp(
            #             cookie_expires_timestamp)

            #         year1 = datetime.now() + datetime.timedelta(months=12)
            #         months9 = datetime.now() + datetime.timedelta(months=9)
            #         months6 = datetime.now() + datetime.timedelta(months=6)
            #         months3 = datetime.now() + datetime.timedelta(months=3)
            #         if year1 > cookie_expires_date:
            #             cookies_number_of_valid_over_1year += 1
            #         elif months9 > cookie_expires_date:
            #             cookies_number_of_valid_over_9months += 1
            #         elif months6 > cookie_expires_date:
            #             cookies_number_of_valid_over_6months += 1
            #         elif months3 > cookie_expires_date:
            #             cookies_number_of_valid_over_3months += 1

            number_of_cookies += 1

    if cookies_number_of_firstparties > 0:
        cookies_review += '-- Firstparty: {0}\r\n'.format(
            cookies_number_of_firstparties)
    if cookies_number_of_thirdparties > 0:
        cookies_review += '-- Thirdparty: {0}\r\n'.format(
            cookies_number_of_thirdparties)

    if cookies_number_of_valid_over_1year > 0:
        cookies_review += '-- Over 1 year valid: {0}\r\n'.format(
            cookies_number_of_valid_over_1year)
    elif cookies_number_of_valid_over_9months > 0:
        cookies_review += '-- Over 9 months valid: {0}\r\n'.format(
            cookies_number_of_valid_over_9months)
    elif cookies_number_of_valid_over_6months > 0:
        cookies_review += '-- Over 6 months valid: {0}\r\n'.format(
            cookies_number_of_valid_over_6months)
    elif cookies_number_of_valid_over_3months > 0:
        cookies_review += '-- Over 3 months valid: {0}\r\n'.format(
            cookies_number_of_valid_over_3months)

    if cookies_number_of_httponly > 0:
        cookies_review += '-- Not HttpOnly: {0}\r\n'.format(
            cookies_number_of_httponly)

    if cookies_number_of_secure > 0:
        cookies_review += '-- Not Secure: {0}\r\n'.format(
            cookies_number_of_secure)

    if number_of_cookies > 0:
        cookies_points = 0.0
        cookies_review = '* Cookies ({0} points)\r\n{1}'.format(
            cookies_points, cookies_review)
    else:
        cookies_points = 1.0
        cookies_review = '* Cookies (+{0} points)\r\n-- No Cookies\r\n'.format(
            cookies_points)

    return (cookies_points, cookies_review)


def check_detailed_results(content, adserver_requests, hostname):
    points = 0.0
    review = ''

    json_content = ''
    try:
        json_content = json.loads(content)
    except:  # might crash if checked resource is not a webpage
        return (points, review)

    fingerprint_result = check_fingerprint(json_content)
    points += fingerprint_result[0]
    review += fingerprint_result[1]

    ads_result = check_ads(json_content, adserver_requests)
    points += ads_result[0]
    review += ads_result[1]

    cookies_result = check_cookies(json_content, hostname)
    points += cookies_result[0]
    review += cookies_result[1]

    return (points, review)


def check_har_results(content):
    points = 0.0
    review = ''

    json_content = ''
    try:
        json_content = json.loads(content)
    except:  # might crash if checked resource is not a webpage
        return (points, review)

    review += '* Countries: {0}\r\n'.format(
        4)
    review += '-- Countries outside EU: {0}\r\n'.format(
        1)
    review += '-- Page hosted in Sweden: {0}\r\n'.format(
        False)

    return (points, review)


def get_text_excluding_children(driver, element):
    return driver.execute_script("""
    return jQuery(arguments[0]).contents().filter(function() {
        return this.nodeType == Node.TEXT_NODE;
    }).text();
    """, element)


def get_downloadtext_excluding_children(driver, element):
    return driver.execute_script("""
    return jQuery(arguments[0]).contents().filter(function() {
        return this.nodeType == Node.TEXT_NODE;
    }).text();
    """, element)
