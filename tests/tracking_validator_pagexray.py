# -*- coding: utf-8 -*-
from models import Rating
import os
import json
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import config
import re
import urllib.parse
from tests.utils import *
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.firefox.options import Options
import IP2Location
import gettext
_ = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
use_ip2location = config.use_ip2location
useragent = config.useragent
review_show_improvements_only = config.review_show_improvements_only
tracking_use_website = config.tracking_use_website
sitespeed_use_docker = config.sitespeed_use_docker

ip2location_db = False
if use_ip2location:
    try:
        ip2location_db = IP2Location.IP2Location(
            os.path.join("data", "IP2LOCATION-LITE-DB1.IPV6.BIN"))
    except Exception as ex:
        print('Unable to load IP2Location Database from "data/IP2LOCATION-LITE-DB1.IPV6.BIN"', ex)


def get_file_content(input_filename):
    # print('input_filename=' + input_filename)
    with open(input_filename, 'r', encoding='utf-8') as file:
        lines = list()
        data = file.readlines()
        for line in data:
            lines.append(line)
            # print(line)
    return '\n'.join(lines)


def get_foldername_from_url(url):
    o = urllib.parse.urlparse(url)
    hostname = o.hostname
    relative_path = o.path

    test_str = '{0}{1}'.format(hostname, relative_path)

    regex = r"[^a-z0-9\-\/]"
    subst = "_"

    # You can manually specify the number of replacements by changing the 4th argument
    folder_result = re.sub(regex, subst, test_str, 0, re.MULTILINE)

    return folder_result


def get_data_from_sitespeed(url):
    http_archive_content = ''
    detailed_results_content = ''
    number_of_tracking = 0
    adserver_requests = 0

    result_folder_name = 'results-{0}'.format(str(uuid.uuid4()))

    from tests.performance_sitespeed_io import get_result as sitespeed_run_test
    sitespeed_arg = '--rm --shm-size=1g -b chrome --plugins.remove screenshot --browsertime.chrome.includeResponseBodies "all" --html.fetchHARFiles true --outputFolder {2} --firstParty --utc true --xvfb --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        config.sitespeed_iterations, url, result_folder_name)
    # sitespeed_arg = '--rm --shm-size=1g -b chrome --plugins.remove screenshot --browsertime.chrome.includeResponseBodies "all" --html.fetchHARFiles true --logToFile true --outputFolder {2} --firstParty --utc true --xvfb --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
    #     config.sitespeed_iterations, url, result_folder_name)
    result = sitespeed_run_test(sitespeed_use_docker, sitespeed_arg)

    website_folder_name = get_foldername_from_url(url)

    filename = '{0}/pages/{1}/data/browsertime.har'.format(
        result_folder_name, website_folder_name)

    from tests.performance_sitespeed_io import get_file_content as sitespeed_get_file_content
    http_archive_content = sitespeed_get_file_content(
        sitespeed_use_docker, filename)

    # http_archive_content = get_file_content(os.path.join(
    #     'data', 'webperf.se-har.json'))
    # detailed_results_content = get_file_content(os.path.join(
    #     'data', 'webperf.se-results.json'))

    # from tests.performance_sitespeed_io import remove_folder as sitespeed_remove_folder
    # sitespeed_remove_folder(
    #     sitespeed_use_docker, result_folder_name)
    # os.rmdir(result_folder_name)

    return (http_archive_content, detailed_results_content, number_of_tracking, adserver_requests)


def get_data(url):
    if tracking_use_website:
        return get_data_from_website(url)
    else:
        return get_data_from_sitespeed(url)
        # return get_data_from_file(url)


def get_data_from_file(url):
    http_archive_content = ''
    detailed_results_content = ''
    number_of_tracking = 0
    adserver_requests = 0

    http_archive_content = get_file_content(os.path.join(
        'data', 'webperf.se-har.json'))
    # detailed_results_content = get_file_content(os.path.join(
    #     'data', 'webperf.se-results.json'))

    return (http_archive_content, detailed_results_content, number_of_tracking, adserver_requests)


def get_data_from_website(url):
    http_archive_content = False
    detailed_results_content = False
    number_of_tracking = 0
    adserver_requests = 0

    browser = False
    try:
        # Remove options if you want to see browser windows (good for debugging)
        options = Options()
        options.add_argument("--headless")
        browser = webdriver.Firefox(firefox_options=options)

        browser.get('https://pagexray-eu.fouanalytics.com/')

        elem = browser.find_element(By.NAME, 'domain')  # Find the domain box
        elem.send_keys(url + Keys.RETURN)
    except:
        if browser != False:
            browser.quit()
        # rating.set_overall(1.0, _local('TEXT_SERVICE_UNABLE_TO_CONNECT'))
        return (http_archive_content, detailed_results_content, number_of_tracking, adserver_requests)

    try:
        # wait for element(s) to appear
        wait = WebDriverWait(browser, 60, poll_frequency=5)
        wait.until(ec.visibility_of_element_located(
            (By.CLASS_NAME, 'adserver-request-count')))
    except:
        if browser != False:
            browser.quit()
        # rating.set_overall(1.0, _local('TEXT_SERVICES_ENCOUNTERED_ERROR'))
        return (http_archive_content, detailed_results_content, number_of_tracking, adserver_requests)

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

        elem_tracking_requests_count = browser.find_element(
            By.CLASS_NAME, 'tracking-request-count')  # tracking requests

        number_of_tracking = int(elem_tracking_requests_count.text[19:])

        elem_ad_requests_count = browser.find_element(
            By.CLASS_NAME, 'adserver-request-count')  # Ad requests
        adserver_requests = int(elem_ad_requests_count.text[19:])

        # time.sleep(30)
    finally:
        if browser != False:
            browser.quit()

    return (http_archive_content, detailed_results_content, number_of_tracking, adserver_requests)


def run_test(_, langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    result_dict = {}
    rating = Rating(_, review_show_improvements_only)

    language = gettext.translation(
        'tracking_validator_pagexray', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    result = get_data(url)
    http_archive_content = result[0]
    detailed_results_content = result[1]
    number_of_tracking = result[2]
    adserver_requests = result[3]
    # print('GET countries and tracking')
    if http_archive_content:
        rating += check_har_results(http_archive_content, _local, _)

        rating += check_tracking(
            number_of_tracking, http_archive_content + detailed_results_content, _local, _)

    # print('GET fingerprints, ads and cookies')
    if len(detailed_results_content) > 0:
        o = urllib.parse.urlparse(url)
        hostname = o.hostname

        rating += check_detailed_results(
            adserver_requests, detailed_results_content, hostname, _local, _)

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)


def check_tracking(number_of_tracking, json_content, _local, _):
    rating = Rating(_, review_show_improvements_only)

    # elem_tracking_requests_count = browser.find_element(
    #     By.CLASS_NAME, 'tracking-request-count')  # tracking requests

    # number_of_tracking = int(elem_tracking_requests_count.text[19:])

    review_analytics = ''
    analytics_used = get_analytics(json_content)
    number_of_analytics_used = len(analytics_used)
    if number_of_analytics_used > 0:
        # '-- Visitor analytics used:\r\n'
        review_analytics += _local('TEXT_VISITOR_ANALYTICS_USED')
        analytics_used_items = analytics_used.items()
        for analytics_name, analytics_should_count in analytics_used_items:
            if analytics_should_count:
                number_of_tracking += 1
            review_analytics += '    - {0}\r\n'.format(analytics_name)

    points = 5.0

    # Ignore up to 2 tracker requests
    number_of_tracking_for_points = number_of_tracking - 2
    if number_of_tracking_for_points <= 0:
        number_of_tracking_for_points = 0

    points -= (number_of_tracking_for_points * 0.5)
    points = float("{0:.2f}".format(points))

    if points <= 1.0:
        points = 1.0
        # '* Tracking ({0} points)\r\n'
        rating.set_integrity_and_security(
            points, _local('TEXT_TRACKING_NO_POINTS'))
        rating.set_overall(points)
    else:
        # '* Tracking (+{0} points)\r\n'
        rating.set_integrity_and_security(
            points, _local('TEXT_TRACKING_HAS_POINTS'))
        rating.set_overall(points)

    if len(review_analytics) > 0:
        # review += review_analytics
        rating.integrity_and_security_review = rating.integrity_and_security_review + review_analytics

    if number_of_tracking > 0:
        # '-- Tracking requests: {0}\r\n'
        rating.integrity_and_security_review = rating.integrity_and_security_review + _local('TEXT_TRACKING_HAS_REQUESTS').format(
            number_of_tracking)
    else:
        # '-- No tracking requests\r\n'
        rating.integrity_and_security_review = rating.integrity_and_security_review + \
            _local('TEXT_TRACKING_NO_REQUESTS')

    return rating


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


def check_fingerprint(json_content, _local, _):
    fingerprints = {}
    possible_fingerprints = json_content['fingerprints']
    number_of_potential_fingerprints = len(possible_fingerprints)
    fingerprints_index = 0
    fingerprints_points = 1.0
    number_of_fingerprints = 0
    fingerprints_review = ''

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

    rating = Rating(_, review_show_improvements_only)

    if number_of_fingerprints == 0:
        fingerprints_points = 5.0
        rating.set_integrity_and_security(
            fingerprints_points, _local('TEXT_FINGERPRINTING_HAS_POINTS'))
        rating.set_overall(fingerprints_points)

    else:
        rating.set_integrity_and_security(
            fingerprints_points, _local('TEXT_FINGERPRINTING_NO_POINTS'))
        rating.integrity_and_security_review = rating.integrity_and_security_review + \
            fingerprints_review
        rating.set_overall(fingerprints_points)

    return rating


def check_ads(json_content, adserver_requests, _local, _):
    ads = json_content['ads']
    number_of_ads = len(ads)
    ads_points = 5.0
    rating = Rating(_, review_show_improvements_only)

    if adserver_requests > 0 or number_of_ads > 0:
        ads_points = 1.0
        rating.set_integrity_and_security(
            ads_points, _local('TEXT_ADS_NO_POINTS'))
        rating.set_overall(ads_points)

        if adserver_requests > 0:
            rating.integrity_and_security_review = rating.integrity_and_security_review + _local('TEXT_ADS_HAS_REQUESTS').format(
                adserver_requests)

        if number_of_ads > 0:
            rating.integrity_and_security_review = rating.integrity_and_security_review + _local('TEXT_ADS_VISIBLE_ADS').format(
                number_of_ads)
    else:
        ads_points = 5.0
        rating.set_integrity_and_security(
            ads_points, _local('TEXT_ADS_NO_REQUESTS'))
        rating.set_overall(ads_points)

    return rating


def check_cookies(json_content, hostname, _local, _):
    rating = Rating(_, review_show_improvements_only)
    cookies = json_content['cookies']
    number_of_potential_cookies = len(cookies)
    number_of_cookies = 0
    cookies_index = 0
    cookies_points = 1.0

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
        nof_points = 5.0 - cookies_number_of_thirdparties * 0.5
        if nof_points < 1.0:
            nof_points = 1.0

        nof_rating = Rating(_, review_show_improvements_only)
        nof_rating.set_integrity_and_security(nof_points, _local('TEXT_COOKIES_HAS_THIRDPARTY').format(
            cookies_number_of_thirdparties))
        nof_rating.set_overall(nof_points)
        rating += nof_rating
    if cookies_number_of_valid_over_1year > 0:
        # '-- Valid over 1 year: {0}\r\n'
        valid_1year_points = 5.0 - cookies_number_of_valid_over_1year * 5.0
        if valid_1year_points < 1.0:
            valid_1year_points = 1.0

        valid_1year_rating = Rating(_, review_show_improvements_only)
        valid_1year_rating.set_integrity_and_security(valid_1year_points, _local('TEXT_COOKIE_HAS_OVER_1YEAR').format(
            cookies_number_of_valid_over_1year))
        valid_1year_rating.set_overall(valid_1year_points)
        rating += valid_1year_rating
    elif cookies_number_of_valid_over_9months > 0:
        # '-- Valid over 9 months: {0}\r\n'
        valid_9months_points = 5.0 - cookies_number_of_valid_over_9months * 4.0
        if valid_9months_points < 1.0:
            valid_9months_points = 1.0

        valid_9months_rating = Rating(_, review_show_improvements_only)
        valid_9months_rating.set_integrity_and_security(valid_9months_points, _local('TEXT_COOKIE_HAS_OVER_9MONTH').format(
            cookies_number_of_valid_over_9months))
        valid_9months_rating.set_overall(valid_9months_points)
        rating += valid_9months_rating
    elif cookies_number_of_valid_over_6months > 0:
        # '-- Valid over 6 months: {0}\r\n'
        valid_6months_points = 5.0 - cookies_number_of_valid_over_6months * 3.0
        if valid_6months_points < 1.0:
            valid_6months_points = 1.0

        valid_6months_rating = Rating(_, review_show_improvements_only)
        valid_6months_rating.set_integrity_and_security(valid_6months_points, _local('TEXT_COOKIE_HAS_OVER_6MONTH').format(
            cookies_number_of_valid_over_6months))
        valid_6months_rating.set_overall(valid_6months_points)
        rating += valid_6months_rating
    elif cookies_number_of_valid_over_3months > 0:
        # '-- Valid over 3 months: {0}\r\n'
        valid_3months_points = 5.0 - cookies_number_of_valid_over_3months * 3.0
        if valid_3months_points < 1.0:
            valid_3months_points = 1.0

        valid_3months_rating = Rating(_, review_show_improvements_only)
        valid_3months_rating.set_integrity_and_security(valid_3months_points, _local('TEXT_COOKIE_HAS_OVER_3MONTH').format(
            cookies_number_of_valid_over_3months))
        valid_3months_rating.overall(valid_3months_points)
        rating += valid_3months_rating
    if cookies_number_of_secure > 0:
        # '-- Not secure: {0}\r\n'
        secure_points = 5.0 - cookies_number_of_secure * 3.0
        if secure_points < 1.0:
            secure_points = 1.0

        secure_rating = Rating(_, review_show_improvements_only)
        secure_rating.set_integrity_and_security(secure_points, _local('TEXT_COOKIE_NOT_SECURE').format(
            cookies_number_of_secure))
        secure_rating.set_overall(secure_points)
        rating += secure_rating

    tmp_review = rating.integrity_and_security_review
    rating.integrity_and_security_review = ''

    if number_of_cookies > 0:
        if rating.get_overall() > 1.0:
            # '* Cookies (+{0} points)\r\n{1}'
            rating.integrity_and_security_review = _local('TEXT_COOKIE_HAS_POINTS').format(
                rating.get_overall(), '')
        else:
            # '* Cookies ({0} points)\r\n{1}'
            rating.integrity_and_security_review = _local('TEXT_COOKIE_NO_POINTS').format(
                rating.get_overall(), '')
    else:
        no_cookie_points = 5.0
        rating.set_integrity_and_security(no_cookie_points, _local('TEXT_COOKIE_HAS_POINTS').format(
            0.0, ''))

        rating.set_overall(no_cookie_points)

    rating.integrity_and_security_review = rating.integrity_and_security_review + tmp_review

    return rating


def check_detailed_results(adserver_requests, content, hostname, _local, _):
    rating = Rating(_, review_show_improvements_only)

    adserver_requests = 0
    json_content = ''
    try:
        json_content = json.loads(content)
    except:  # might crash if checked resource is not a webpage
        return rating

    rating += check_fingerprint(json_content, _local, _)

    rating += check_ads(json_content, adserver_requests, _local, _)

    rating += check_cookies(json_content, hostname, _local, _)

    return rating


def check_har_results(content, _local, _):
    rating = Rating(_, review_show_improvements_only)
    points = 5.0
    review = ''
    countries = {}
    countries_outside_eu_or_exception_list = {}

    json_content = ''
    try:
        json_content = json.loads(content)

        json_content = json_content['log']

        # general_info = json_content['pages'][0]
        # pageId = general_info['id']
        # tested = general_info['startedDateTime']

        entries = json_content['entries']
        number_of_entries = len(entries)
        page_entry = entries[0]
        page_countrycode = ''

        # website has info in a field called 'comment', local version has not
        if 'comment' in page_entry:
            page_isp_and_countrycode = json.loads(page_entry['comment'])
            page_countrycode = page_isp_and_countrycode['country_code']

        page_ip_address = page_entry['serverIPAddress']

        page_countrycode = get_best_country_code(
            page_ip_address, page_countrycode)
        if page_countrycode == '':
            page_countrycode = 'unknown'

        entries_index = 0
        while entries_index < number_of_entries:
            entry_country_code = ''
            # website has info in a field called 'comment', local version has not
            if 'comment' in entries[entries_index]:
                entry_isp_and_countrycode = json.loads(
                    entries[entries_index]['comment'])
                entry_country_code = entry_isp_and_countrycode['country_code']

            entry_ip_address = entries[entries_index]['serverIPAddress']
            entry_country_code = get_best_country_code(
                entry_ip_address, entry_country_code)

            if entry_country_code == '':
                entry_country_code = 'unknown'
            if entry_country_code in countries:
                countries[entry_country_code] = countries[entry_country_code] + 1
            else:
                countries[entry_country_code] = 1
                if not is_country_code_in_eu_or_on_exception_list(entry_country_code):
                    countries_outside_eu_or_exception_list[entry_country_code] = 1

            entries_index += 1

        number_of_countries = len(countries)

        # '-- Number of countries: {0}\r\n'
        review += _local('TEXT_GDPR_COUNTRIES').format(
            number_of_countries)
        # for country_code in countries:
        #    review += '    - {0} (number of requests: {1})\r\n'.format(country_code,
        #                                                               countries[country_code])

        number_of_countries_outside_eu = len(
            countries_outside_eu_or_exception_list)
        if number_of_countries_outside_eu > 0:
            # '-- Countries outside EU: {0}\r\n'
            # '-- Countries without adequate level of data protection: {0}\r\n'
            review += _local('TEXT_GDPR_NONE_COMPLIANT_COUNTRIES').format(
                number_of_countries_outside_eu)
            for country_code in countries_outside_eu_or_exception_list:
                review += _local('TEXT_GDPR_NONE_COMPLIANT_COUNTRIES_REQUESTS').format(country_code,
                                                                                       countries[country_code])

            points = 1.0

        page_is_hosted_in_sweden = page_countrycode == 'SE'
        # '-- Page hosted in Sweden: {0}\r\n'
        review += _local('TEXT_GDPR_PAGE_IN_SWEDEN').format(
            _local('TEXT_GDPR_{0}'.format(page_is_hosted_in_sweden)))

        if points > 0.0:
            rating.set_integrity_and_security(points, _local('TEXT_GDPR_HAS_POINTS').format(
                0.0, ''))
            rating.set_overall(points)
        else:
            rating.set_integrity_and_security(points, _local('TEXT_GDPR_NO_POINTS').format(
                0.0, ''))
            rating.set_overall(points)

        rating.integrity_and_security_review = rating.integrity_and_security_review + review

        return rating

    except Exception as ex:  # might crash if checked resource is not a webpage
        print('crash', ex)
        return rating


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


def get_exception_countries():
    # Countries in below list comes from this page: https://ec.europa.eu/info/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en
    # Country codes for every country comes from Wikipedia when searching on country name, example: https://en.wikipedia.org/wiki/Iceland
    exception_countrycodes = {
        'NO': 'Norway',
        'LI': 'Liechtenstein',
        'IS': 'Iceland',
        'AD': 'Andorra',
        'AR': 'Argentina',
        'CA': 'Canada',
        'FO': 'Faroe Islands',
        'GG': 'Guernsey',
        'IL': 'Israel',
        'IM': 'Isle of Man',
        'JP': 'Japan',
        'JE': 'Jersey',
        'NZ': 'New Zealand',
        'CH': 'Switzerland',
        'UY': 'Uruguay',
        'KR': 'South Korea',
        'GB': 'United Kingdom',
        'AX': 'Åland Islands',
        # If we are unable to guess country, give it the benefit of the doubt.
        'unknown': 'Unknown'
    }
    return exception_countrycodes


def is_country_code_in_eu(country_code):
    country_codes = get_eu_countries()
    if country_code in country_codes:
        return True

    return False


def is_country_code_in_exception_list(country_code):
    country_codes = get_exception_countries()
    if country_code in country_codes:
        return True

    return False


def is_country_code_in_eu_or_on_exception_list(country_code):
    return is_country_code_in_eu(country_code) or is_country_code_in_exception_list(country_code)


def get_country_name_from_country_code(country_code):
    eu_countrycodes = get_eu_countries()
    if country_code in eu_countrycodes:
        return eu_countrycodes[country_code]
    return country_code


def get_country_code_from_ip2location(ip_address):
    if use_ip2location:
        rec = False
        try:
            rec = ip2location_db.get_all(ip_address)
        except Exception as ex:
            return ''
        try:
            countrycode = rec.country_short
            return countrycode
        except Exception as ex:
            return ''

    return ''


def get_best_country_code(ip_address, default_country_code):
    if is_country_code_in_eu_or_on_exception_list(default_country_code):
        return default_country_code

    country_code = get_country_code_from_ip2location(ip_address)
    if country_code == '':
        return default_country_code

    return country_code
