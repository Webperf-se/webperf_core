# -*- coding: utf-8 -*-
import os
from datetime import datetime
import re
from models import Rating
from tests.utils import get_config_or_default, get_friendly_url_name, get_translation, set_cache_file
from tests.w3c_base import get_errors, identify_files
from tests.sitespeed_base import get_result

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
review_show_improvements_only = get_config_or_default('review_show_improvements_only')
sitespeed_use_docker = get_config_or_default('sitespeed_use_docker')

sitespeed_timeout = get_config_or_default('sitespeed_timeout')
USE_CACHE = get_config_or_default('cache_when_possible')
CACHE_TIME_DELTA = get_config_or_default('cache_time_delta')

def run_test(global_translation, lang_code, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    rating = Rating(global_translation, review_show_improvements_only)
    points = 0.0
    review = ''

    local_translation = get_translation('html_validator_w3c', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    errors = []

    # We don't need extra iterations for what we are using it for
    sitespeed_iterations = 1
    sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --plugins.remove html --plugins.remove metrics --browsertime.screenshot false --screenshot false --screenshotLCP false --browsertime.screenshotLCP false --chrome.cdp.performance false --browsertime.chrome.timeline false --videoParams.createFilmstrip false --visualMetrics false --visualMetricsPerceptual false --visualMetricsContentful false --browsertime.headless true --browsertime.chrome.includeResponseBodies all --utc true --browsertime.chrome.args ignore-certificate-errors -n {0}'.format(
        sitespeed_iterations)
    if 'nt' not in os.name:
        sitespeed_arg += ' --xvfb'

    sitespeed_arg += ' --postScript chrome-cookies.cjs --postScript chrome-versions.cjs'

    (_, filename) = get_result(
        url, sitespeed_use_docker, sitespeed_arg, sitespeed_timeout)

    # 1. Visit page like a normal user
    data = identify_files(filename)


    for entry in data['htmls']:
        req_url = entry['url']
        name = get_friendly_url_name(global_translation, req_url, entry['index'])
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

                    review += local_translation('TEXT_REVIEW_ERRORS_ITEM').format(item_text, item_value)

        number_of_error_types = len(error_message_grouped_dict)

        result = calculate_rating(number_of_error_types, number_of_errors)

        # if number_of_error_types > 0:
        error_types_rating = Rating(global_translation, review_show_improvements_only)
        error_types_rating.set_overall(result[0], review_header + local_translation('TEXT_REVIEW_RATING_GROUPED').format(
            number_of_error_types, 0.0))
        rating += error_types_rating

        # if number_of_errors > 0:
        error_rating = Rating(global_translation, review_show_improvements_only)
        error_rating.set_overall(result[1], review_header + local_translation(
            'TEXT_REVIEW_RATING_ITEMS').format(number_of_errors, 0.0))
        rating += error_rating


    points = rating.get_overall()
    rating.set_standards(points)
    rating.standards_review = review

    review = ''
    if points == 5.0:
        review = local_translation('TEXT_REVIEW_HTML_VERY_GOOD')
    elif points >= 4.0:
        review = local_translation('TEXT_REVIEW_HTML_IS_GOOD').format(
            number_of_errors)
    elif points >= 3.0:
        review = local_translation('TEXT_REVIEW_HTML_IS_OK').format(
            number_of_errors)
    elif points > 1.0:
        review = local_translation('TEXT_REVIEW_HTML_IS_BAD').format(
            number_of_errors)
    elif points <= 1.0:
        review = local_translation('TEXT_REVIEW_HTML_IS_VERY_BAD').format(
            number_of_errors)

    # rating.set_overall(points)
    rating.standards_review = rating.overall_review + rating.standards_review
    rating.overall_review = review

    print(global_translation('TEXT_TEST_END').format(
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
