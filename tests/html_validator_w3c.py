# -*- coding: utf-8 -*-
from models import Rating
import datetime
import re
import config
from tests.utils import *
from tests.w3c_base import get_errors, identify_files
from tests.sitespeed_base import get_result
import gettext
_local = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
review_show_improvements_only = config.review_show_improvements_only
sitespeed_use_docker = config.sitespeed_use_docker
try:
    use_cache = config.cache_when_possible
    cache_time_delta = config.cache_time_delta
except:
    # If cache_when_possible variable is not set in config.py this will be the default
    use_cache = False
    cache_time_delta = timedelta(hours=1)


def run_test(_, langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    rating = Rating(_, review_show_improvements_only)
    points = 0.0
    review = ''

    language = gettext.translation(
        'html_validator_w3c', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    errors = list()
    error_message_dict = {}

    # We don't need extra iterations for what we are using it for
    sitespeed_iterations = 1
    sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --plugins.remove html --plugins.remove metrics --browsertime.screenshot false --screenshot false --screenshotLCP false --browsertime.screenshotLCP false --chrome.cdp.performance false --browsertime.chrome.timeline false --videoParams.createFilmstrip false --visualMetrics false --visualMetricsPerceptual false --visualMetricsContentful false --browsertime.headless true --browsertime.chrome.includeResponseBodies all --utc true --browsertime.chrome.args ignore-certificate-errors -n {0}'.format(
        sitespeed_iterations)
    if 'nt' not in os.name:
        sitespeed_arg += ' --xvfb'

    (result_folder_name, filename) = get_result(
        url, sitespeed_use_docker, sitespeed_arg)

    # 1. Visit page like a normal user
    data = identify_files(filename)


    for entry in data['htmls']:
        req_url = entry['url']
        name = get_friendly_url_name(_, req_url, entry['index'])
        review_header = '- {0} '.format(name)
        html = entry['content']
        set_cache_file(req_url, html, True)

        params = {'doc': req_url,
                'out': 'json',
                'level': 'error'}
        errors = get_errors('html', params)
        number_of_errors = len(errors)


        error_message_grouped_dict = {}
        if number_of_errors > 0:
            regex = r"(“[^”]+”)"
            for item in errors:
                error_message = item['message']

                # Filter out CSS: entries that should not be here
                if error_message.startswith('CSS: '):
                    number_of_errors -= 1
                    continue

                # Filter out start html document stuff if not start webpage
                if entry['index'] > 1:
                    if 'Start tag seen without seeing a doctype first. Expected “<!DOCTYPE html>”' in error_message:
                        number_of_errors -= 1
                        continue
                    if 'Element “head” is missing a required instance of child element “title”.' in error_message:
                        number_of_errors -= 1
                        continue
                    
                error_message = re.sub(
                    regex, "X", error_message, 0, re.MULTILINE)

                if error_message_grouped_dict.get(error_message, False):
                    error_message_grouped_dict[error_message] = error_message_grouped_dict[error_message] + 1
                else:
                    error_message_grouped_dict[error_message] = 1

            if len(error_message_grouped_dict) > 0:
                error_message_grouped_sorted = sorted(
                    error_message_grouped_dict.items(), key=lambda x: x[1], reverse=True)

                for item in error_message_grouped_sorted:

                    item_value = item[1]
                    item_text = item[0]

                    review += _local('TEXT_REVIEW_ERRORS_ITEM').format(item_text, item_value)

        number_of_error_types = len(error_message_grouped_dict)

        result = calculate_rating(number_of_error_types, number_of_errors)

        # if number_of_error_types > 0:
        error_types_rating = Rating(_, review_show_improvements_only)
        error_types_rating.set_overall(result[0], review_header + _local('TEXT_REVIEW_RATING_GROUPED').format(
            number_of_error_types, 0.0))
        rating += error_types_rating

        # if number_of_errors > 0:
        error_rating = Rating(_, review_show_improvements_only)
        error_rating.set_overall(result[1], review_header + _local(
            'TEXT_REVIEW_RATING_ITEMS').format(number_of_errors, 0.0))
        rating += error_rating


    points = rating.get_overall()
    rating.set_standards(points)
    rating.standards_review = review

    review = ''
    if points == 5.0:
        review = _local('TEXT_REVIEW_HTML_VERY_GOOD')
    elif points >= 4.0:
        review = _local('TEXT_REVIEW_HTML_IS_GOOD').format(
            number_of_errors)
    elif points >= 3.0:
        review = _local('TEXT_REVIEW_HTML_IS_OK').format(
            number_of_errors)
    elif points > 1.0:
        review = _local('TEXT_REVIEW_HTML_IS_BAD').format(
            number_of_errors)
    elif points <= 1.0:
        review = _local('TEXT_REVIEW_HTML_IS_VERY_BAD').format(
            number_of_errors)

    # rating.set_overall(points)
    rating.standards_review = rating.overall_review + rating.standards_review
    rating.overall_review = review

    print(_('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, errors)


def calculate_rating(number_of_error_types, number_of_errors):

    rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)

    rating_number_of_errors = 5.0 - ((number_of_errors / 2.0) / 5.0)

    if rating_number_of_error_types < 1.0:
        rating_number_of_error_types = 1.0
    if rating_number_of_errors < 1.0:
        rating_number_of_errors = 1.0

    return (rating_number_of_error_types, rating_number_of_errors)
