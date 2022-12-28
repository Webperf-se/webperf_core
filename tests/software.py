# -*- coding: utf-8 -*-
from pathlib import Path
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

    regex = r"[^a-zA-Z0-9\-\/]"
    subst = "_"

    # You can manually specify the number of replacements by changing the 4th argument
    folder_result = re.sub(regex, subst, test_str, 0, re.MULTILINE)

    # NOTE: hopefully temporary fix for "index.html" and Gullspangs-kommun.html
    folder_result = folder_result.replace('_html', '.html')

    folder_result = folder_result.replace('/', os.sep)

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
    # result_folder_name = os.path.join('data', 'results')

    from tests.performance_sitespeed_io import get_result as sitespeed_run_test

    sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --browsertime.chrome.collectPerfLog --browsertime.chrome.includeResponseBodies "all" --html.fetchHARFiles true --outputFolder {2} --firstParty --utc true --xvfb --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        config.sitespeed_iterations, url, result_folder_name)
    if 'nt' in os.name:
        sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --browsertime.chrome.collectPerfLog --browsertime.chrome.includeResponseBodies "all" --html.fetchHARFiles true --outputFolder {2} --firstParty --utc true --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
            config.sitespeed_iterations, url, result_folder_name)

    use_stealth = True

    filename = ''

    # TODO: Remove cache when done
    import engines.sitespeed_result as input
    sites = input.read_sites('', -1, -1)
    for site in sites:
        if url == site[1]:
            filename = site[0]

    if filename == '':
        sitespeed_run_test(sitespeed_use_docker, sitespeed_arg)

        website_folder_name = get_foldername_from_url(url)

        filename = os.path.join(result_folder_name, 'pages',
                                website_folder_name, 'data', 'browsertime.har')

    data = list()

    import json
    with open(filename) as json_input_file:
        har_data = json.load(json_input_file)
        if 'log' in har_data:
            har_data = har_data['log']
        for entry in har_data["entries"]:
            req = entry['request']
            res = entry['response']
            req_url = req['url']

            url_data = lookup_request_url(req_url)
            if url_data != None or len(url_data) > 0:
                data.extend(url_data)

            # TODO: Check for https://docs.2sxc.org/index.html ?

            # if 'matomo.php' in req_url or 'matomo.js' in req_url or 'piwik.php' in req_url or 'piwik.js' in req_url:
            #     analytics_dict = {}
            #     analytics_dict['name'] = 'Matomo'
            #     analytics_dict['url'] = req_url
            #     matomo_version = 'Matomo'

            #     check_matomo_version = 'matomo' not in result['analytics']
            #     if check_matomo_version and not use_stealth:
            #         matomo_o = urlparse(req_url)
            #         matomo_hostname = matomo_o.hostname
            #         matomo_url = '{0}://{1}/CHANGELOG.md'.format(
            #             matomo_o.scheme, matomo_hostname)

            #         matomo_changelog_url_regex = r"(?P<url>.*)\/(matomo|piwik).(js|php)"
            #         matches = re.finditer(
            #             matomo_changelog_url_regex, req_url, re.MULTILINE)
            #         for matchNum, match in enumerate(matches, start=1):
            #             matomo_url = match.group('url') + '/CHANGELOG.md'

            #         # print('matomo_url', matomo_url)

            #         matomo_content = httpRequestGetContent(matomo_url)
            #         matomo_regex = r"## Matomo (?P<version>[\.0-9]+)"

            #         matches = re.finditer(
            #             matomo_regex, matomo_content, re.MULTILINE)
            #         for matchNum, match in enumerate(matches, start=1):
            #             matomo_version = match.group('version')
            #             analytics_dict['version'] = matomo_version
            #             break

            #         if 'version' in analytics_dict:
            #             analytics_dict['versions-behind'] = -1
            #             analytics_dict['latest-version'] = ''

            #             matomo_version_index = 0

            #             # TODO: Change this request
            #             # matomo_changelog_feed = httpRequestGetContent(
            #             #     'https://matomo.org/changelog/feed/')
            #             matomo_changelog_feed = get_file_content(
            #                 'data\\matomo-org-changelog-feed.txt')

            #             matomo_changelog_regex = r"<title>Matomo (?P<version>[\.0-9]+)<\/title>"
            #             matches = re.finditer(
            #                 matomo_changelog_regex, matomo_changelog_feed, re.MULTILINE)
            #             for matchNum, match in enumerate(matches, start=1):
            #                 matomo_changelog_version = match.group('version')
            #                 if analytics_dict['latest-version'] == '':
            #                     analytics_dict['latest-version'] = matomo_changelog_version
            #                 # print('changelog version:', matomo_changelog_version)
            #                 if matomo_changelog_version in matomo_version:
            #                     analytics_dict['versions-behind'] = matomo_version_index
            #                     break
            #                 matomo_version_index = matomo_version_index + 1
            #     if check_matomo_version:
            #         result['analytics']['matomo'] = analytics_dict

            if 'headers' in res:
                headers = res['headers']
                header_data = lookup_response_headers(req_url, headers)
                if header_data != None or len(header_data) > 0:
                    data.extend(header_data)

    if not use_stealth:
        # TODO: Check if we are missing any type and try to find this info
        if len(result['cms']) == 0:
            o = urlparse(url)
            hostname = o.hostname
            episerver_url = '{0}://{1}/App_Themes/Default/Styles/system.css'.format(
                o.scheme, hostname)
            content = httpRequestGetContent(episerver_url)
            if 'EPiServer' in content:
                result['cms']['episerver'] = episerver_url
                result['tech']['asp.net'] = episerver_url
                result['tech']['csharp'] = episerver_url
            else:
                episerver_url = '{0}://{1}/util/login.aspx'.format(
                    o.scheme, hostname)
                content = httpRequestGetContent(episerver_url)
                if 'episerver-white.svg' in content or "__epiXSRF" in content:
                    result['cms']['episerver'] = episerver_url
                    result['tech']['asp.net'] = episerver_url
                    result['tech']['csharp'] = episerver_url
        if len(result['cms']) == 0:
            # https://wordpress.org/support/article/upgrading-wordpress-extended-instructions/
            o = urlparse(url)
            hostname = o.hostname
            wordpress_url = '{0}://{1}/wp-includes/css/dashicons.min.css'.format(
                o.scheme, hostname)
            content = httpRequestGetContent(wordpress_url)
            if 'dashicons-wordpress' in content:
                result['cms']['wordpress'] = req_url
                result['tech']['php'] = req_url
            else:
                o = urlparse(url)
                hostname = o.hostname
                wordpress_url = '{0}://{1}/wp-login.php'.format(
                    o.scheme, hostname)
                content = httpRequestGetContent(wordpress_url)
                if '/wp-admin/' in content or '/wp-includes/' in content:
                    result['cms']['wordpress'] = req_url
                    result['tech']['php'] = req_url

        # if len(result['cms']) == 0:
            # https://typo3.org/
            # <meta name="generator" content="TYPO3 CMS" />

    result = {}

    for item in data:
        domain_item = None
        if item['domain'] not in result:
            domain_item = {}
        else:
            domain_item = result[item['domain']]

        key = None
        if 'tech' in item:
            key = 'tech'
        elif 'webserver' in item:
            key = 'webserver'
        elif 'cms' in item:
            key = 'cms'
        elif 'os' in item:
            key = 'os'
        elif 'analytics' in item:
            key = 'analytics'
        else:
            key = 'unknown'

        value = item[key]
        pos = value.find(' ')
        key2 = value
        if pos > 0:
            key2 = value[:pos]

        if key not in domain_item:
            domain_item[key] = {}
        if key2 not in domain_item[key]:
            domain_item[key][key2] = {
                'name': value, 'precision': 0.0}

        if domain_item[key][key2]['precision'] < item['precision']:
            obj = {}
            obj['name'] = value
            obj['precision'] = item['precision']
            domain_item[key][key2] = obj

        result[item['domain']] = domain_item

    pretty_result = json.dumps(result, indent=4)
    print('result', pretty_result)
    return rating


def get_default_info(url, method, precision, key, value):
    result = {}

    o = urlparse(url)
    hostname = o.hostname
    result['domain'] = hostname

    result['url'] = url
    result['method'] = method
    result['precision'] = precision
    result[key] = value

    return result


def lookup_request_url(req_url):
    data = list()

    # print('# ', req_url)
    if '.aspx' in req_url or '.ashx' in req_url:
        data.append(get_default_info(req_url, 'url', 0.5, 'tech', 'asp.net'))

    if '/contentassets/' in req_url or '/globalassets/' in req_url or 'epi-util/find.js' in req_url or 'dl.episerver.net' in req_url:
        data.append(get_default_info(req_url, 'url', 0.1, 'tech', 'asp.net'))
        data.append(get_default_info(req_url, 'url', 0.5, 'cms', 'episerver'))
        data.append(get_default_info(req_url, 'url', 0.5, 'tech', 'csharp'))
    elif '/sitevision/' in req_url:
        data.append(get_default_info(req_url, 'url', 0.1, 'tech', 'java'))
        data.append(get_default_info(req_url, 'url', 0.5, 'cms', 'sitevision'))
        data.append(get_default_info(
            req_url, 'url', 0.5, 'webserver', 'tomcat'))
    elif '/wp-content/' in req_url or '/wp-content/' in req_url:
        # https://wordpress.org/support/article/upgrading-wordpress-extended-instructions/
        data.append(get_default_info(req_url, 'url', 0.1, 'tech', 'php'))
        data.append(get_default_info(req_url, 'url', 0.5, 'cms', 'wordpress'))
    elif '/typo3temp/' in req_url or '/typo3conf/' in req_url or '/t3olayout/' in req_url:
        # https://typo3.org/
        data.append(get_default_info(req_url, 'url', 0.1, 'tech', 'php'))
        data.append(get_default_info(req_url, 'url', 0.5, 'cms', 'typo3'))

        # TODO: Check for https://docs.2sxc.org/index.html ?

    if 'matomo.php' in req_url or 'matomo.js' in req_url or 'piwik.php' in req_url or 'piwik.js' in req_url:
        data.append(get_default_info(req_url, 'url', 0.5, 'tech', 'matomo'))
    if '.js' in req_url:
        # TODO: check framework name and version in comment
        # TODO: check if ".map" is mentioned in file, if so, check it for above framework name and version
        # TODO: check use of node_modules
        # https://www.tranemo.se/wp-includes/js/jquery/jquery.min.js?ver=3.6.1
        # https://www.tranemo.se/wp-includes/js/dist/vendor/regenerator-runtime.min.js?ver=0.13.9
        data.append(get_default_info(req_url, 'url', 0.5, 'tech', 'js'))
    if '.svg' in req_url:
        # TODO: Check Generator comment
        # https://www.pajala.se/static/gfx/pajala-kommunvapen.svg
        # <!-- Generator: Adobe Illustrator 24.0.2, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->
        # https://start.stockholm/ui/assets/img/logotype.svg
        # <!-- Generator: Adobe Illustrator 19.2.1, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->
        data.append(get_default_info(
            req_url, 'url', 0.5, 'tech', 'svg'))
    if '/imagevault/' in req_url:
        data.append(get_default_info(
            req_url, 'url', 0.5, 'tech', 'imagevault'))

    return data


def lookup_response_headers(req_url, headers):
    data = list()

    for header in headers:
        header_name = header['name'].upper()
        header_value = header['value'].upper()

        # print('header', header_name, header_value)
        tmp_data = lookup_response_header(req_url, header_name, header_value)
        if len(tmp_data) != 0:
            data.extend(tmp_data)
    return data


def lookup_response_header(req_url, header_name, header_value):
    data = list()

    if 'SET-COOKIE' in header_name:
        if 'ASP.NET_SESSIONID' in header_value:
            data.append(get_default_info(
                req_url, 'cookie', 0.5, 'webserver', 'iis'))
            data.append(get_default_info(
                req_url, 'cookie', 0.5, 'tech', 'asp.net'))
            if 'SAMESITE=LAX' in header_value:
                # https://learn.microsoft.com/en-us/aspnet/samesite/system-web-samesite
                data.append(get_default_info(req_url, 'header',
                            0.9, 'tech', 'asp.net >=4.7.2'))

            if 'JSESSIONID' in header_value:
                data.append(get_default_info(
                    req_url, 'cookie', 0.3, 'webserver', 'tomcat'))
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'tech', 'java'))
            if 'SITEVISION' in header_value:
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'cms', 'sitevision'))
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'tech', 'java'))
                data.append(get_default_info(
                    req_url, 'cookie', 0.3, 'webserver', 'tomcat'))
            if 'SITEVISIONLTM' in header_value:
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'cms', 'sitevision'))
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'tech', 'java'))
                data.append(get_default_info(
                    req_url, 'cookie', 0.3, 'webserver', 'tomcat'))
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'cms', 'sitevision-cloud'))
    if 'CONTENT-TYPE' in header_name:
        if 'image/vnd.microsoft.icon' in header_value:
            data.append(get_default_info(
                req_url, 'header', 0.3, 'os', 'windows'))
        if 'X-OPNET-TRANSACTION-TRACE' in header_name:
            data.append(get_default_info(
                req_url, 'header', 0.8, 'tech', 'riverbed-steelcentral-transaction-analyzer'))
            # https://en.wikipedia.org/wiki/OPNET
            # https://support.riverbed.com/content/support/software/opnet-performance/apptransaction-xpert.html
        if 'X-POWERED-BY' in header_name:
            if 'ASP.NET' in header_value:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'webserver', 'iis'))
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'tech', 'asp.net'))
            if 'SERVLET/' in header_value:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'webserver', 'websphere'))
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'tech', 'java'))
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'tech', 'servlet'))
        if 'SERVER' in header_name:
            server_regex = r"(?P<webservername>[a-zA-Z\-]+)\/{0,1}(?P<webserverversion>[0-9.]+){0,1}[ ]{0,1}\({0,1}(?P<osname>[a-zA-Z]*)\){0,1}"
            matches = re.finditer(
                server_regex, header_value, re.MULTILINE)
            webserver_name = ''
            webserver_version = ''
            os_name = ''
            for matchNum, match in enumerate(matches, start=1):
                webserver_name = match.group('webservername')
                webserver_version = match.group('webserverversion')
                os_name = match.group('osname')

                if 'MICROSOFT-IIS' in webserver_name:
                    data.append(get_default_info(
                        req_url, 'header', 0.7, 'webserver', 'iis'))
                    data.append(get_default_info(
                        req_url, 'header', 0.5, 'os', 'windows'))

                    if '10.0' in webserver_version:
                        data.append(get_default_info(
                            req_url, 'header', 0.8, 'os', 'windows server 2016/2019'))
                        data.append(get_default_info(
                            req_url, 'header', 0.9, 'webserver', 'iis 10'))
                    elif '8.5' in webserver_version or '8.0' in webserver_version:
                        data.append(get_default_info(
                            req_url, 'header', 0.9, 'os', 'windows server 2012'))
                        data.append(get_default_info(
                            req_url, 'header', 0.9, 'webserver', 'iis 8.x'))
                    elif '7.5' in webserver_version or '7.0' in webserver_version:
                        data.append(get_default_info(
                            req_url, 'header', 0.9, 'os', 'windows server 2008'))
                        data.append(get_default_info(
                            req_url, 'header', 0.9, 'webserver', 'iis 7.x'))
                    elif '6.0' in webserver_version:
                        data.append(get_default_info(
                            req_url, 'header', 0.9, 'os', 'windows server 2003'))
                        data.append(get_default_info(
                            req_url, 'header', 0.9, 'webserver', 'iis 6.x'))
                    elif None != webserver_version:
                        data.append(get_default_info(
                            req_url, 'header', 0.6, 'webserver', 'iis {0}'.format(
                                webserver_version)))

                if 'APACHE' in webserver_name:
                    data.append(get_default_info(
                        req_url, 'header', 0.5, 'webserver', 'apache'))
                    if webserver_version != None:
                        data.append(get_default_info(
                            req_url, 'header', 0.5, 'webserver', 'apache {0}'.format(
                                webserver_version)))

                if 'UBUNTU' in os_name:
                    data.append(get_default_info(
                        req_url, 'header', 0.5, 'os', 'ubuntu'))
                elif 'NGINX' in webserver_name:
                    data.append(get_default_info(
                        req_url, 'header', 0.5, 'os', 'nginx'))
                elif None == os_name or '' == os_name:
                    ignore = 1
                else:
                    print('UNHANDLED OS:', os_name)

        if 'X-ASPNET-VERSION' in header_name:
            data.append(get_default_info(
                req_url, 'header', 0.5, 'webserver', 'iis'))
            data.append(get_default_info(
                req_url, 'header', 0.5, 'tech', 'asp.net'))
            # TODO: Fix validation of header_value, it can now include infected data
            data.append(get_default_info(
                req_url, 'header', 0.8, 'tech', 'asp.net {0}'.format(
                    header_value)))
        if 'CONTENT-SECURITY-POLICY' in header_name:
            regex = r"(?P<name>[a-zA-Z\-]+) (?P<value>[^;]+);*[ ]*"
            matches = re.finditer(
                regex, header_value, re.MULTILINE)
            for matchNum, match in enumerate(matches, start=1):
                # TODO: look at more values and uses in CSP
                csp_rule_name = match.group('name').upper()
                csp_rule_value = match.group('value').upper()
                if 'DL.EPISERVER.NET' in csp_rule_value:
                    data.append(get_default_info(
                        req_url, 'header', 0.7, 'cms', 'episerver'))
                    data.append(get_default_info(
                        req_url, 'header', 0.4, 'tech', 'asp.net'))
                    data.append(get_default_info(
                        req_url, 'header', 0.4, 'tech', 'tech'))

    return data


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

    # TODO: Re add handling from selenium
    # rating += get_rating_from_selenium(url, _local, _)

    rating += get_rating_from_sitespeed(url, _local, _)

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)
