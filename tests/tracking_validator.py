# -*- coding: utf-8 -*-
from models import Rating
import os
import json
import config
import re
# https://docs.python.org/3/library/urllib.parse.html
from urllib.parse import urlparse
from tests.utils import *
import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.options import Options
import gettext
_ = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
review_show_improvements_only = config.review_show_improvements_only
sitespeed_use_docker = config.sitespeed_use_docker


def get_domains_from_url(url):
    domains = set()
    o = urlparse(url)
    hostname = o.hostname
    domains.add(hostname)

    hostname_sections = hostname.split(".")
    if len(hostname_sections) > 2:
        tmp_hostname = ".".join(hostname_sections[-3:])
        domains.add(tmp_hostname)

    tmp_hostname = ".".join(hostname_sections[-2:])
    domains.add(tmp_hostname)

    return domains


def get_urls_from_har(content):
    urls = dict()

    entries = list()
    json_content = list()
    try:
        json_content = json.loads(content)

        json_content = json_content['log']

        if 'entries' in json_content:
            entries = json_content['entries']

        for entry in entries:
            url = False
            if 'request' in entry:
                request = entry['request']
                if 'url' in request:
                    url = request['url']
                    urls[url] = ''

            content_text = False
            if 'response' in entry:
                response = entry['response']
                if 'content' in response:
                    content = response['content']
                    if 'text' in content:
                        content_text = content['text']
                        urls[url] = content_text

    except Exception as ex:  # might crash if checked resource is not a webpage
        print('crash get_urls_from_har', ex)
        return urls

    return urls


def get_domains_from_blocklistproject_file(filename):
    domains = set()

    try:
        with open(filename, 'r', encoding='utf-8') as file:
            data = file.readlines()
            index = 0
            for line in data:
                if index <= 35:
                    index += 1
                if line and not line.startswith('#'):
                    domains.add(line.strip('\n'))
    except:
        print('no blocklistproject file found at: {0}'.format(filename))
        return domains
    return domains


def get_domains_from_disconnect_file(filename, sections):
    domains = set()

    try:
        with open(filename, 'r', encoding='utf-8') as json_input_file:
            data = json.load(json_input_file)

            if 'categories' in data:
                data = data['categories']
            # current_index = 0
            for section_name in sections:
                for entity in data[section_name]:
                    for entity_name in entity.keys():
                        for entity_website in entity[entity_name].keys():
                            for domain in entity[entity_name][entity_website]:
                                domains.add(domain)
    except:
        print('no disconnect file found at: {0}'.format(filename))
        return domains
    return domains


def get_foldername_from_url(url):
    o = urlparse(url)
    hostname = o.hostname
    relative_path = o.path

    test_str = '{0}{1}'.format(hostname, relative_path)

    regex = r"[^a-z0-9\-\/]"
    subst = "_"

    # You can manually specify the number of replacements by changing the 4th argument
    folder_result = re.sub(regex, subst, test_str, 0, re.MULTILINE)

    # NOTE: hopefully temporary fix for "index.html"
    folder_result = folder_result.replace('index_html', 'index.html')

    return folder_result


def get_friendly_url_name(_local, url, request_index):

    request_friendly_name = _local(
        'TEXT_REQUEST_UNKNOWN').format(request_index)
    if request_index == 1:
        request_friendly_name = _local(
            'TEXT_REQUEST_WEBPAGE').format(request_index)

    try:
        o = urlparse(url)
        tmp = o.path.strip('/').split('/')
        length = len(tmp)
        tmp = tmp[length - 1]

        regex = r"[^a-z0-9.]"
        subst = "-"

        tmp = re.sub(regex, subst, tmp, 0, re.MULTILINE)
        length = len(tmp)
        if length > 15:
            request_friendly_name = '#{0}: {1}'.format(request_index, tmp[:15])
        elif length > 1:
            request_friendly_name = '#{0}: {1}'.format(request_index, tmp)
    except:
        return request_friendly_name
    return request_friendly_name


def get_file_content(input_filename):
    # print('input_filename=' + input_filename)
    lines = list()
    try:
        with open(input_filename, 'r', encoding='utf-8') as file:
            data = file.readlines()
            for line in data:
                lines.append(line)
                # print(line)
    except:
        print('error in get_local_file_content. No such file or directory: {0}'.format(
            input_filename))
        return '\n'.join(lines)
    return '\n'.join(lines)


def rate_cookies(browser, url, _local, _):
    rating = Rating(_, review_show_improvements_only)

    o = urlparse(url)
    hostname = o.hostname

    cookies = browser.get_cookies()

    number_of_potential_cookies = len(cookies)

    number_of_cookies = 0
    cookies_index = 0

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
                    elif months9_from_now < cookie_expires_date:
                        cookies_number_of_valid_over_9months += 1
                    elif months6_from_now < cookie_expires_date:
                        cookies_number_of_valid_over_6months += 1
                    elif months3_from_now < cookie_expires_date:
                        cookies_number_of_valid_over_3months += 1

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
        valid_3months_rating.set_overall(valid_3months_points)

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

    integrity_and_security_review = rating.integrity_and_security_review

    result_rating = Rating(_, review_show_improvements_only)
    points = rating.get_overall()

    if number_of_cookies > 0 and rating.isused():
        if points <= 1.0:
            points = 1.0
            result_rating.set_integrity_and_security(
                points, _local('TEXT_COOKIE'))
            result_rating.set_overall(points)
        else:
            result_rating.set_integrity_and_security(
                points, _local('TEXT_COOKIE'))
            result_rating.set_overall(points)
    else:
        no_cookie_points = 5.0
        result_rating.set_integrity_and_security(
            no_cookie_points, _local('TEXT_COOKIE'))

        result_rating.set_overall(no_cookie_points)

    result_rating.integrity_and_security_review = result_rating.integrity_and_security_review + \
        rating.integrity_and_security_review + \
        integrity_and_security_review

    return result_rating


def rate_gdpr_and_schrems(content, _local, _):
    rating = Rating(_, review_show_improvements_only)

    points = 5.0
    review = ''
    countries = {}
    countries_outside_eu_or_exception_list = {}

    json_content = ''
    try:
        json_content = json.loads(content)

        json_content = json_content['log']

        entries = json_content['entries']
        number_of_entries = len(entries)
        page_entry = entries[0]
        page_countrycode = ''

        page_ip_address = page_entry['serverIPAddress']

        page_countrycode = get_best_country_code(
            page_ip_address, page_countrycode)
        if page_countrycode == '':
            page_countrycode = 'unknown'

        entries_index = 0
        while entries_index < number_of_entries:
            entry_country_code = ''

            entry_ip_address = entries[entries_index]['serverIPAddress']
            entry_country_code = get_best_country_code(
                entry_ip_address, entry_country_code)

            if entry_country_code == '' or entry_country_code == '-':
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


def rate_tracking(website_urls, _local, _):
    rating = Rating(_, review_show_improvements_only)

    allowed_nof_trackers = 2
    max_nof_trackers_showed = 5

    limit_message_index = max_nof_trackers_showed + 1
    number_of_tracking = 0
    analytics_used = dict()

    tracking_domains = get_domains_from_blocklistproject_file(
        os.path.join('data', 'blocklistproject-tracking-nl.txt'))

    request_index = 1
    for website_url, website_url_content in website_urls.items():
        url_is_tracker = False
        website_domains = get_domains_from_url(website_url)
        for website_domain in website_domains:
            if website_domain in tracking_domains:
                url_is_tracker = True
                number_of_tracking += 1
                break

        resource_analytics_used = dict()
        resource_analytics_used.update(
            get_analytics(_local, website_url, website_url_content, request_index))

        if len(resource_analytics_used):
            if not url_is_tracker:
                number_of_tracking += 1
            url_is_tracker = True

        analytics_used.update(resource_analytics_used)

        url_rating = Rating(_, review_show_improvements_only)
        if url_is_tracker:
            request_friendly_name = get_friendly_url_name(_local,
                                                          website_url, request_index)

            if number_of_tracking <= allowed_nof_trackers:
                url_rating.set_integrity_and_security(
                    5.0, _local('TEXT_TRACKING_FOUND_ALLOWED').format(request_friendly_name, allowed_nof_trackers))
                url_rating.set_overall(5.0)
            elif number_of_tracking <= max_nof_trackers_showed:
                url_rating.set_integrity_and_security(
                    1.0, _local('TEXT_TRACKING_FOUND').format(request_friendly_name))
                url_rating.set_overall(1.0)
            elif number_of_tracking == limit_message_index:
                url_rating.set_integrity_and_security(
                    1.0, _local('TEXT_TRACKING_MAX_SHOWED').format(max_nof_trackers_showed))
                url_rating.set_overall(1.0)
            else:
                url_rating.set_integrity_and_security(1.0)
                url_rating.set_overall(1.0)
        else:
            url_rating.set_integrity_and_security(5.0)
            url_rating.set_overall(5.0)
        rating += url_rating

        request_index += 1

    review_analytics = ''

    number_of_analytics_used = len(analytics_used)
    if number_of_analytics_used > 0:
        # '-- Visitor analytics used:\r\n'
        review_analytics += _local('TEXT_VISITOR_ANALYTICS_USED')
        analytics_used_items = analytics_used.items()
        for analytics_name, analytics_should_count in analytics_used_items:
            review_analytics += '    - {0}\r\n'.format(analytics_name)

    integrity_and_security_review = rating.integrity_and_security_review

    if number_of_tracking >= 6:
        integrity_and_security_review += _local('TEXT_TRACKING_TOTAL_FOUND').format(
            number_of_tracking)

    integrity_and_security_review += review_analytics

    result_rating = Rating(_, review_show_improvements_only)

    points = rating.get_overall()
    if points <= 1.0:
        points = 1.0
        # '* Tracking ({0} points)\r\n'
        result_rating.set_integrity_and_security(
            points, _local('TEXT_TRACKING'))
        result_rating.set_overall(points)
    else:
        # '* Tracking (+{0} points)\r\n'
        result_rating.set_integrity_and_security(
            points, _local('TEXT_TRACKING'))
        result_rating.set_overall(points)

    result_rating.integrity_and_security_review = result_rating.integrity_and_security_review + \
        integrity_and_security_review

    return result_rating


def rate_fingerprint(website_urls, _local, _):
    rating = Rating(_, review_show_improvements_only)

    max_nof_fingerprints_showed = 5

    limit_message_index = max_nof_fingerprints_showed + 1
    disconnect_sections = ('FingerprintingInvasive', 'FingerprintingGeneral')
    fingerprinting_domains = get_domains_from_disconnect_file(
        os.path.join('data', 'disconnect-services.json'), disconnect_sections)

    fingerprint_requests = 0

    request_index = 1
    for website_url, website_url_content in website_urls.items():
        url_is_adserver_requests = False
        website_domains = get_domains_from_url(website_url)
        for website_domain in website_domains:
            if website_domain in fingerprinting_domains:
                url_is_adserver_requests = True
                fingerprint_requests += 1
                break

        url_rating = Rating(_, review_show_improvements_only)
        if url_is_adserver_requests:
            if fingerprint_requests <= max_nof_fingerprints_showed:
                request_friendly_name = get_friendly_url_name(_local,
                                                              website_url, request_index)
                url_rating.set_integrity_and_security(
                    1.0, _local('TEXT_FINGERPRINTING_FOUND').format(request_friendly_name))
                url_rating.set_overall(1.0)
            elif fingerprint_requests == limit_message_index:
                url_rating.set_integrity_and_security(
                    1.0, _local('TEXT_FINGERPRINTING_MAX_SHOWED').format(max_nof_fingerprints_showed))
                url_rating.set_overall(1.0)
            else:
                url_rating.set_integrity_and_security(1.0)
                url_rating.set_overall(1.0)
        rating += url_rating

        request_index += 1

    integrity_and_security_review = rating.integrity_and_security_review

    if fingerprint_requests >= 6:
        integrity_and_security_review += _local('TEXT_FINGERPRINTING_TOTAL_FOUND').format(
            fingerprint_requests)

    if fingerprint_requests == 0:
        rating.set_integrity_and_security(5.0)
        rating.set_overall(5.0)

    result_rating = Rating(_, review_show_improvements_only)
    points = rating.get_overall()
    if points <= 1.0:
        points = 1.0
        # '* Tracking ({0} points)\r\n'
        result_rating.set_integrity_and_security(
            points, _local('TEXT_FINGERPRINTING'))
        result_rating.set_overall(points)
    else:
        # '* Tracking (+{0} points)\r\n'
        result_rating.set_integrity_and_security(
            points, _local('TEXT_FINGERPRINTING'))
        result_rating.set_overall(points)

    result_rating.integrity_and_security_review = result_rating.integrity_and_security_review + \
        integrity_and_security_review

    return result_rating


def rate_ads(website_urls, _local, _):
    rating = Rating(_, review_show_improvements_only)

    allowed_nof_ads = 2
    max_nof_ads_showed = 5

    limit_message_index = max_nof_ads_showed + 1
    adserver_requests = 0

    tracking_domains = get_domains_from_blocklistproject_file(
        os.path.join('data', 'blocklistproject-ads-nl.txt'))

    request_index = 1
    for website_url, website_url_content in website_urls.items():
        url_is_adserver_requests = False
        website_domains = get_domains_from_url(website_url)
        for website_domain in website_domains:
            if website_domain in tracking_domains:
                url_is_adserver_requests = True
                adserver_requests += 1
                break

        url_rating = Rating(_, review_show_improvements_only)
        if url_is_adserver_requests:
            request_friendly_name = get_friendly_url_name(_local,
                                                          website_url, request_index)
            if adserver_requests <= allowed_nof_ads:
                url_rating.set_integrity_and_security(
                    5.0, _local('TEXT_ADS_FOUND_ALLOWED').format(request_friendly_name, allowed_nof_ads))
                url_rating.set_overall(5.0)
            elif adserver_requests <= max_nof_ads_showed:
                url_rating.set_integrity_and_security(
                    1.0, _local('TEXT_ADS_FOUND').format(request_friendly_name))
                url_rating.set_overall(1.0)
            elif adserver_requests == limit_message_index:
                url_rating.set_integrity_and_security(
                    1.0, _local('TEXT_ADS_MAX_SHOWED').format(max_nof_ads_showed))
                url_rating.set_overall(1.0)
            else:
                url_rating.set_integrity_and_security(1.0)
                url_rating.set_overall(1.0)
        else:
            url_rating.set_integrity_and_security(5.0)
            url_rating.set_overall(5.0)
        rating += url_rating

        request_index += 1

    integrity_and_security_review = rating.integrity_and_security_review

    if adserver_requests >= 6:
        integrity_and_security_review += _local('TEXT_ADS_TOTAL_FOUND').format(
            adserver_requests)

    result_rating = Rating(_, review_show_improvements_only)
    points = rating.get_overall()
    if points <= 1.0:
        points = 1.0
        # '* Ads ({0} points)\r\n'
        result_rating.set_integrity_and_security(
            points, _local('TEXT_ADS'))
        result_rating.set_overall(points)
    else:
        # '* Ads (+{0} points)\r\n'
        result_rating.set_integrity_and_security(
            points, _local('TEXT_ADS'))
        result_rating.set_overall(points)

    result_rating.integrity_and_security_review = result_rating.integrity_and_security_review + \
        integrity_and_security_review

    return result_rating


def get_rating_from_sitespeed(url, _local, _):
    rating = Rating(_, review_show_improvements_only)

    # TODO: CHANGE THIS IF YOU WANT TO DEBUG
    result_folder_name = os.path.join(
        'data', 'results-{0}'.format(str(uuid.uuid4())))
    #result_folder_name = os.path.join('data', 'results')

    from tests.performance_sitespeed_io import get_result as sitespeed_run_test

    sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --browsertime.chrome.collectPerfLog --browsertime.chrome.includeResponseBodies "all" --html.fetchHARFiles true --outputFolder {2} --firstParty --utc true --xvfb --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        config.sitespeed_iterations, url, result_folder_name)
    if 'nt' in os.name:
        sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --browsertime.chrome.collectPerfLog --browsertime.chrome.includeResponseBodies "all" --html.fetchHARFiles true --outputFolder {2} --firstParty --utc true --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
            config.sitespeed_iterations, url, result_folder_name)

    sitespeed_run_test(sitespeed_use_docker, sitespeed_arg)

    website_folder_name = get_foldername_from_url(url)

    filename = os.path.join(result_folder_name, 'pages',
                            website_folder_name,  'data', 'browsertime.har')

    http_archive_content = get_file_content(filename)

    # - GDPR and Schrems ( 5.00 rating )
    rating += rate_gdpr_and_schrems(http_archive_content, _local, _)

    website_urls = get_urls_from_har(http_archive_content)

    # - Tracking ( 5.00 rating )
    try:
        rating += rate_tracking(website_urls, _local, _)
    except Exception as ex:
        print('tracking exception', ex)
    # - Fingerprinting/Identifying technique ( 5.00 rating )
    try:
        rating += rate_fingerprint(website_urls, _local, _)
    except Exception as ex:
        print('fingerprint exception', ex)
    # - Ads ( 5.00 rating )
    try:
        rating += rate_ads(website_urls, _local, _)
    except Exception as ex:
        print('ads exception', ex)

    return rating


def get_rating_from_selenium(url, _local, _):
    rating = Rating(_, review_show_improvements_only)

    browser = False
    try:
        # Remove options if you want to see browser windows (good for debugging)
        options = Options()
        options.add_argument("--headless")

        browser = webdriver.Firefox(options=options)
        browser.implicitly_wait(120)

        browser.get(url)

        # - Cookies ( 5.00 rating )
        rating += rate_cookies(browser, url, _local, _)

        # TODO: Add localStorage and other storage here

        WebDriverWait(browser, 120)

        browser.quit()

        return rating
    except Exception as ex:
        print('errorssss', ex)

        if browser != False:
            browser.quit()
        return rating


def run_test(_, langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    result_dict = {}
    rating = Rating(_, review_show_improvements_only)

    language = gettext.translation(
        'tracking_validator', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # TODO: Read sitespeed manual on how to return cookies and localStorage (This way we could remove dependency on Selenium)
    rating += get_rating_from_selenium(url, _local, _)

    rating += get_rating_from_sitespeed(url, _local, _)

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)


def get_analytics(_local, url, content, request_index):
    analytics = {}

    request_friendly_name = get_friendly_url_name(_local,
                                                  url, request_index)

    text = _local('TEXT_TRACKING_REFERENCE')

    url_and_content = url + content

    if has_matomo(url_and_content):
        analytics[text.format(request_friendly_name, 'Matomo')] = True
    if has_matomo_tagmanager(url_and_content):
        analytics[text.format(request_friendly_name,
                              'Matomo Tag Manager')] = True
    if has_google_analytics(url_and_content):
        analytics[text.format(request_friendly_name,
                              'Google Analytics')] = False
    if has_google_tagmanager(url_and_content):
        analytics[text.format(request_friendly_name,
                              'Google Tag Manager')] = False
    if has_siteimprove_analytics(url_and_content):
        analytics[text.format(request_friendly_name,
                              'SiteImprove Analytics')] = False
    if has_Vizzit(url_and_content):
        analytics[text.format(request_friendly_name, 'Vizzit')] = True
    if has_fathom(url_and_content):
        analytics[text.format(request_friendly_name,
                              'Fathom Analytics')] = True

    return analytics


def has_matomo(content):
    # Look for cookie name
    if '"name": "_pk_' in content:
        return True
    if '"name": "MATOMO_' in content:
        return True
    if '"name": "PIWIK_' in content:
        return True

    # Look for javascript objects
    if 'window.Matomo=' in content:
        return True
    if 'window.Piwik=' in content:
        return True

    # Look for file names
    if 'piwik.js' in content:
        return True
    if 'matomo.php' in content:
        return True

    return False


def has_fathom(content):
    # Look for javascript objects
    if 'window.fathom' in content:
        return True
    if 'locationchangefathom' in content:
        return True
    if 'blockFathomTracking' in content:
        return True
    if 'fathomScript' in content:
        return True

    # Look for file names
    if 'cdn.usefathom.com' in content:
        return True

    return False


def has_matomo_tagmanager(content):
    # Look for javascript objects
    if 'window.MatomoT' in content:
        return True

    return False


def has_google_analytics(content):
    # Look for javascript objects
    if 'window.GoogleAnalyticsObject' in content:
        return True

    # Look for file names
    if 'google-analytics.com/analytics.js' in content:
        return True
    if 'google-analytics.com/ga.js' in content:
        return True

    return False


def has_google_tagmanager(content):
    # Look for file names
    if 'googletagmanager.com/gtm.js' in content:
        return True
    if 'googletagmanager.com/gtag' in content:
        return True
    # Look server name
    if '"value": "Google Tag Manager"' in content:
        return True

    return False


def has_siteimprove_analytics(content):
    # Look for file names
    if 'siteimproveanalytics.io' in content:
        return True
    if 'siteimproveanalytics.com/js/siteanalyze' in content:
        return True

    return False


def has_Vizzit(content):
    # Look for javascript objects
    if '___vizzit' in content:
        return True
    if '$vizzit_' in content:
        return True
    if '$vizzit =' in content:
        return True
    # Look for file names
    if 'vizzit.se/vizzittag' in content:
        return True

    return False
