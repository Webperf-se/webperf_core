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
from selenium.webdriver.firefox.options import Options
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
        'tracking_validator_pagexray', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

    browser = False
    try:
        o = urllib.parse.urlparse(url)
        hostname = o.hostname

        # Remove options if you want to see browser windows (good for debugging)
        options = Options()
        options.add_argument("--headless")
        browser = webdriver.Firefox(firefox_options=options)
        #browser = webdriver.Firefox()

        browser.get('https://pagexray.fouanalytics.com/')

        elem = browser.find_element(By.NAME, 'domain')  # Find the domain box
        elem.send_keys(url + Keys.RETURN)
    except:
        if browser != False:
            browser.quit()
        return (1.0, _('TEXT_SERVICE_UNABLE_TO_CONNECT'), result_dict)

    try:
        # wait for element(s) to appear
        wait = WebDriverWait(browser, 60, poll_frequency=5)
        wait.until(ec.visibility_of_element_located(
            (By.CLASS_NAME, 'adserver-request-count')))
    except:
        if browser != False:
            browser.quit()
        return (1.0, _('TEXT_SERVICES_ENCOUNTERED_ERROR'), result_dict)

    try:
        elements_download_links = browser.find_elements_by_css_selector(
            'a[download]')  # download links

        number_of_download_links = len(elements_download_links)
        download_link_index = 0

        http_archive_content = False
        detailed_results_content = False

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
                detailed_results_content = download_link_content

            if 'Download HTTP Archive' in download_link_text:
                http_archive_content = download_link_content

        # print('GET countries and tracking')
        if http_archive_content:
            result = check_har_results(http_archive_content, _)
            points += result[0]
            review += result[1]

            result = check_tracking(
                browser, http_archive_content + detailed_results_content, _)
            points += result[0]
            review += result[1]

        # print('GET fingerprints, ads and cookies')
        if detailed_results_content:
            result = check_detailed_results(
                browser, detailed_results_content, hostname, _)
            points += result[0]
            review += result[1]

        # time.sleep(30)
    finally:
        if browser != False:
            browser.quit()

    if points < 1.0:
        points = 1.0

    points = float("{0:.2f}".format(points))

    return (points, review, result_dict)


def check_tracking(browser, json_content, _):
    review = ''
    points = 0.0

    elem_tracking_requests_count = browser.find_element(
        By.CLASS_NAME, 'tracking-request-count')  # tracking requests

    number_of_tracking = int(elem_tracking_requests_count.text[19:])

    review_analytics = ''
    analytics_used = get_analytics(json_content)
    number_of_analytics_used = len(analytics_used)
    if number_of_analytics_used > 0:
        # '-- Visitor analytics used:\r\n'
        review_analytics += _('TEXT_VISITOR_ANALYTICS_USED')
        analytics_used_items = analytics_used.items()
        for analytics_name, analytics_should_count in analytics_used_items:
            if analytics_should_count:
                number_of_tracking += 1
            review_analytics += '---- {0}\r\n'.format(analytics_name)

    points = 1.0

    # Ignore up to 2 tracker requests
    number_of_tracking_for_points = number_of_tracking - 2
    if number_of_tracking_for_points <= 0:
        number_of_tracking_for_points = 0

    points -= (number_of_tracking_for_points * 0.1)
    points = float("{0:.2f}".format(points))

    if points <= 0.0:
        points = 0.0
        # '* Tracking ({0} points)\r\n'
        review += _('TEXT_TRACKING_NO_POINTS').format(
            points)
    else:
        # '* Tracking (+{0} points)\r\n'
        review += _('TEXT_TRACKING_HAS_POINTS').format(
            points)

    if len(review_analytics) > 0:
        review += review_analytics

    if number_of_tracking > 0:
        # '-- Tracking requests: {0}\r\n'
        review += _('TEXT_TRACKING_HAS_REQUESTS').format(
            number_of_tracking)
    else:
        # '-- No tracking requests\r\n'
        review += _('TEXT_TRACKING_NO_REQUESTS')

    return (points, review)


def get_analytics(json_content):
    analytics = {}

    if has_matomo(json_content):
        analytics['Matomo'] = True
    if has_matomo_tagmanager(json_content):
        analytics['Matomo Tag Manager'] = True
    if has_google_analytics(json_content):
        # TODO: Check if asking for anonymizing IP ("[xxx]*google-analytics.com/j/collect[xxx]*aip=1[xxx]*")
        # TODO: Check doubleclick? https://stats.g.doubleclick.net/j/collect?[xxx]aip=1[xxx]
        analytics['Google Analytics'] = False
    if has_google_tagmanager(json_content):
        analytics['Google Tag Manager'] = False
    if has_siteimprove_analytics(json_content):
        analytics['SiteImprove Analytics'] = False
    if has_Vizzit(json_content):
        analytics['Vizzit'] = True

    return analytics


def has_matomo(json_content):
    # Look for cookie name
    if '"name": "_pk_' in json_content:
        return True
    if '"name": "MATOMO_' in json_content:
        return True
    if '"name": "PIWIK_' in json_content:
        return True

    # Look for javascript objects
    if 'window.Matomo=' in json_content:
        return True
    if 'window.Piwik=' in json_content:
        return True

    # Look for file names
    if 'piwik.js' in json_content:
        return True
    if 'matomo.php' in json_content:
        return True

    return False


def has_matomo_tagmanager(json_content):
    # Look for javascript objects
    if 'window.MatomoT' in json_content:
        return True

    return False


def has_google_analytics(json_content):
    # Look for javascript objects
    if 'window.GoogleAnalyticsObject' in json_content:
        return True

    # Look for file names
    if 'google-analytics.com/analytics.js' in json_content:
        return True
    if 'google-analytics.com/ga.js' in json_content:
        return True

    return False


def has_google_tagmanager(json_content):
    # Look for file names
    if 'googletagmanager.com/gtm.js' in json_content:
        return True
    if 'googletagmanager.com/gtag' in json_content:
        return True
    # Look server name
    if '"value": "Google Tag Manager"' in json_content:
        return True

    return False


def has_siteimprove_analytics(json_content):
    # Look for file names
    if 'siteimproveanalytics.io' in json_content:
        return True
    if 'siteimproveanalytics.com/js/siteanalyze' in json_content:
        return True

    return False


def has_Vizzit(json_content):
    # Look for javascript objects
    if '___vizzit' in json_content:
        return True
    if '$vizzit_' in json_content:
        return True
    if '$vizzit =' in json_content:
        return True
    # Look for file names
    if 'vizzit.se/vizzittag' in json_content:
        return True

    return False


def check_fingerprint(json_content, _):
    fingerprints = {}
    possible_fingerprints = json_content['fingerprints']
    number_of_potential_fingerprints = len(possible_fingerprints)
    fingerprints_index = 0
    fingerprints_points = 0.0
    number_of_fingerprints = 0
    # '* Fingerprinting ({0} points)\r\n'
    fingerprints_review = _('TEXT_FINGERPRINTING_NO_POINTS').format(
        fingerprints_points)
    if number_of_potential_fingerprints > 0:
        while fingerprints_index < number_of_potential_fingerprints:
            fingerprint = possible_fingerprints[fingerprints_index]
            fingerprints_index += 1

            if 'level' in fingerprint and ('danger' in fingerprint['level'] or 'warning' in fingerprint['level']):

                fingerprint_key = "{0} ({1})".format(
                    fingerprint['category'], fingerprint['level'])

                fingerprint_count = int(fingerprint['count'])

                if fingerprint_key in fingerprints:
                    fingerprints[fingerprint_key] = fingerprints[fingerprint_key] + \
                        fingerprint_count
                else:
                    fingerprints[fingerprint_key] = fingerprint_count

    number_of_fingerprints = len(fingerprints)
    fingerprints_list = fingerprints.items()
    for key, value in fingerprints_list:
        fingerprints_review += '-- {0}: {1}\r\n'.format(
            key, value)

    if number_of_fingerprints == 0:
        fingerprints_points = 1.0
        # '* Fingerprinting (+{0} points)\r\n-- No fingerprinting\r\n'
        fingerprints_review = _('TEXT_FINGERPRINTING_HAS_POINTS').format(
            fingerprints_points)

    return (fingerprints_points, fingerprints_review)


def check_ads(json_content, adserver_requests, _):
    ads = json_content['ads']
    number_of_ads = len(ads)
    ads_points = 0.0
    ads_review = ''
    if adserver_requests > 0 or number_of_ads > 0:
        ads_points = 0.0
        # '* Ads ({0} points)\r\n'
        ads_review = _('TEXT_ADS_NO_POINTS').format(
            ads_points)
    else:
        ads_points = 1.0
        # '* Ads (+{0} points)\r\n-- No Adserver requests\r\n'
        ads_review = _('TEXT_ADS_NO_REQUESTS').format(
            ads_points)

    if adserver_requests > 0:
        # '-- Adserver requests: {0}\r\n'
        ads_review += _('TEXT_ADS_HAS_REQUESTS').format(
            adserver_requests)

    if number_of_ads > 0:
        # '-- Visibile Ads: {0}\r\n'
        ads_review += _('TEXT_ADS_VISIBLE_ADS').format(
            number_of_ads)

    return (ads_points, ads_review)


def check_cookies(json_content, hostname, _):
    cookies = json_content['cookies']
    number_of_potential_cookies = len(cookies)
    number_of_cookies = 0
    cookies_index = 0
    cookies_points = 1.0
    cookies_review = ''

    cookies_number_of_firstparties = 0
    cookies_number_of_thirdparties = 0
    cookies_number_of_secure = 0
    cookies_number_of_valid_over_3months = 0
    cookies_number_of_valid_over_6months = 0
    cookies_number_of_valid_over_9months = 0
    cookies_number_of_valid_over_1year = 0

    # I know it differs around the year but lets get websites the benefit for it..
    days_in_month = 31

    year1_from_now = (datetime.datetime.now() +
                      datetime.timedelta(days=365)).date()
    months9_from_now = (datetime.datetime.now() +
                        datetime.timedelta(days=9 * days_in_month)).date()
    months6_from_now = (datetime.datetime.now() +
                        datetime.timedelta(days=6 * days_in_month)).date()
    months3_from_now = (datetime.datetime.now() +
                        datetime.timedelta(days=3 * days_in_month)).date()

    if number_of_potential_cookies > 0:
        while cookies_index < number_of_potential_cookies:
            cookie = cookies[cookies_index]
            cookies_index += 1

            # if 'httpOnly' in cookie and cookie['httpOnly'] == False:
            #     cookies_number_of_httponly += 1

            if 'secure' in cookie and cookie['secure'] == False:
                cookies_number_of_secure += 1

            if 'domain' in cookie and cookie['domain'].endswith(hostname):
                cookies_number_of_firstparties += 1
                number_of_cookies += 1
            else:
                cookies_number_of_thirdparties += 1
                number_of_cookies += 1

            if 'session' in cookie and cookie['session'] == False:
                if 'expires' in cookie:
                    cookie_expires_timestamp = int(cookie['expires'])
                    # sanity check
                    if cookie_expires_timestamp > 25340230080:
                        cookie_expires_timestamp = 25340230080
                    cookie_expires_date = datetime.date.fromtimestamp(
                        cookie_expires_timestamp)

                    if year1_from_now < cookie_expires_date:
                        cookies_number_of_valid_over_1year += 1
                        cookies_points -= 1.0
                    elif months9_from_now < cookie_expires_date:
                        cookies_number_of_valid_over_9months += 1
                        cookies_points -= 0.9
                    elif months6_from_now < cookie_expires_date:
                        cookies_number_of_valid_over_6months += 1
                        cookies_points -= 0.6
                    elif months3_from_now < cookie_expires_date:
                        cookies_number_of_valid_over_3months += 1
                        cookies_points -= 0.3

            number_of_cookies += 1

    if cookies_number_of_thirdparties > 0:
        # '-- Thirdparty: {0}\r\n'
        cookies_review += _('TEXT_COOKIES_HAS_THIRDPARTY').format(
            cookies_number_of_thirdparties)
        cookies_points -= 0.1

    if cookies_number_of_valid_over_1year > 0:
        # '-- Valid over 1 year: {0}\r\n'
        cookies_review += _('TEXT_COOKIE_HAS_OVER_1YEAR').format(
            cookies_number_of_valid_over_1year)
    elif cookies_number_of_valid_over_9months > 0:
        # '-- Valid over 9 months: {0}\r\n'
        cookies_review += _('TEXT_COOKIE_HAS_OVER_9MONTH').format(
            cookies_number_of_valid_over_9months)
    elif cookies_number_of_valid_over_6months > 0:
        # '-- Valid over 6 months: {0}\r\n'
        cookies_review += _('TEXT_COOKIE_HAS_OVER_6MONTH').format(
            cookies_number_of_valid_over_6months)
    elif cookies_number_of_valid_over_3months > 0:
        # '-- Valid over 3 months: {0}\r\n'
        cookies_review += _('TEXT_COOKIE_HAS_OVER_3MONTH').format(
            cookies_number_of_valid_over_3months)

    if cookies_number_of_secure > 0:
        # '-- Not secure: {0}\r\n'
        cookies_review += _('TEXT_COOKIE_NOT_SECURE').format(
            cookies_number_of_secure)
        cookies_points -= 0.1

    if cookies_points < 0.0:
        cookies_points = 0.0

    cookies_points = float("{0:.2f}".format(cookies_points))

    if number_of_cookies > 0:
        if cookies_points > 0.0:
            # '* Cookies (+{0} points)\r\n{1}'
            cookies_review = _('TEXT_COOKIE_HAS_POINTS').format(
                cookies_points, cookies_review)
        else:
            # '* Cookies ({0} points)\r\n{1}'
            cookies_review = _('TEXT_COOKIE_NO_POINTS').format(
                cookies_points, cookies_review)
    else:
        # '* Cookies (+{0} points)\r\n{1}'
        cookies_review = _('TEXT_COOKIE_HAS_POINTS').format(
            cookies_points, cookies_review)
        # '{0}-- No Cookies\r\n'
        cookies_review = _('TEXT_COOKIE_NO_COOKIES').format(
            cookies_review)

    return (cookies_points, cookies_review)


def check_detailed_results(browser, content, hostname, _):
    points = 0.0
    review = ''

    adserver_requests = 0
    json_content = ''
    try:
        elem_ad_requests_count = browser.find_element(
            By.CLASS_NAME, 'adserver-request-count')  # Ad requests
        adserver_requests = int(elem_ad_requests_count.text[19:])

        json_content = json.loads(content)
    except:  # might crash if checked resource is not a webpage
        return (points, review)

    fingerprint_result = check_fingerprint(json_content, _)
    points += fingerprint_result[0]
    review += fingerprint_result[1]

    ads_result = check_ads(json_content, adserver_requests, _)
    points += ads_result[0]
    review += ads_result[1]

    cookies_result = check_cookies(json_content, hostname, _)
    points += cookies_result[0]
    review += cookies_result[1]

    return (points, review)


def check_har_results(content, _):
    points = 1.0
    review = ''
    countries = {}
    countries_outside_eu = {}

    json_content = ''
    try:
        json_content = json.loads(content)

        json_content = json_content['log']

        general_info = json_content['pages'][0]
        # pageId = general_info['id']
        # tested = general_info['startedDateTime']

        entries = json_content['entries']
        number_of_entries = len(entries)
        page_entry = entries[0]
        page_isp_and_countrycode = json.loads(page_entry['comment'])

        entries_index = 0
        while entries_index < number_of_entries:
            entry_isp_and_countrycode = json.loads(
                entries[entries_index]['comment'])
            entry_country_code = entry_isp_and_countrycode['country_code']
            if entry_country_code in countries:
                countries[entry_country_code] = countries[entry_country_code] + 1
            else:
                countries[entry_country_code] = 1
                if not is_country_code_in_eu(entry_country_code):
                    countries_outside_eu[entry_country_code] = 1

            entries_index += 1

        number_of_countries = len(countries)

        # '-- Number of countries: {0}\r\n'
        review += _('TEXT_GDPR_COUNTRIES').format(
            number_of_countries)
        # for country_code in countries:
        #    review += '---- {0} (number of requests: {1})\r\n'.format(country_code,
        #                                                              countries[country_code])

        number_of_countries_outside_eu = len(countries_outside_eu)
        if number_of_countries_outside_eu > 0:
            # '-- Countries outside EU: {0}\r\n'
            review += _('TEXT_GDPR_COUNTRIES_OUTSIDE_EU').format(
                number_of_countries_outside_eu)
            for country_code in countries_outside_eu:
                review += _('TEXT_GDPR_COUNTRIES_OUTSIDE_EU_REQUESTS').format(country_code,
                                                                              countries[country_code])

            points = 0.0

        page_is_hosted_in_sweden = page_isp_and_countrycode['country_code'] == 'SE'
        # '-- Page hosted in Sweden: {0}\r\n'
        review += _('TEXT_GDPR_PAGE_IN_SWEDEN').format(
            _('TEXT_GDPR_{0}'.format(page_is_hosted_in_sweden)))

        if points > 0.0:
            # '* GDPR and Schrems: (+{0} points)\r\n{1}'
            review = _('TEXT_GDPR_HAS_POINTS').format(
                points, review)
        else:
            # '* GDPR and Schrems: ({0} points)\r\n{1}'
            review = _('TEXT_GDPR_NO_POINTS').format(
                points, review)

        return (points, review)

    except Exception as ex:  # might crash if checked resource is not a webpage
        print('crash', ex)
        return (points, review)


def get_eu_countries():
    eu_countrycodes = {
        'BE': 'Belgium',
        'BG': 'Bulgaria',
        'CZ': 'Czechia',
        'DK': 'Denmark',
        'DE': 'Germany',
        'EE': 'Estonia',
        'IE': 'Ireland',
        'EL': 'Greece',
        'ES': 'Spain',
        'FR': 'France',
        'HR': 'Croatia',
        'IT': 'Italy',
        'CY': 'Cyprus',
        'LV': 'Latvia',
        'LT': 'Lithuania',
        'LU': 'Luxembourg',
        'HU': 'Hungary',
        'MT': 'Malta',
        'NL': 'Netherlands',
        'AT': 'Austria',
        'PL': 'Poland',
        'PT': 'Portugal',
        'RO': 'Romania',
        'SI': 'Slovenia',
        'SK': 'Slovakia',
        'FI': 'Finland',
        'SE': 'Sweden'
    }
    return eu_countrycodes


def is_country_code_in_eu(country_code):
    eu_countrycodes = get_eu_countries()
    if country_code in eu_countrycodes:
        return True

    return False


def get_country_name_from_country_code(country_code):
    eu_countrycodes = get_eu_countries()
    if country_code in eu_countrycodes:
        return eu_countrycodes[country_code]
    return country_code
