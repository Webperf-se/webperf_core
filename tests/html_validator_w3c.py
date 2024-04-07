# -*- coding: utf-8 -*-
import os
from datetime import datetime
import re
from models import Rating
from tests.utils import get_config_or_default,\
                        get_friendly_url_name,\
                        get_translation,\
                        set_cache_file
from tests.w3c_base import get_errors, identify_files
from tests.sitespeed_base import get_result

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
SITESPEED_USE_DOCKER = get_config_or_default('sitespeed_use_docker')
SITESPEED_TIMEOUT = get_config_or_default('sitespeed_timeout')
USE_CACHE = get_config_or_default('cache_when_possible')
CACHE_TIME_DELTA = get_config_or_default('cache_time_delta')

HTML_STRINGS = [
        'Start tag seen without seeing a doctype first. Expected “<!DOCTYPE html>”',
        'Element “head” is missing a required instance of child element “title”.'
    ]


def run_test(global_translation, lang_code, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    local_translation = get_translation('html_validator_w3c', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    errors = []

    data = get_data_for_url(url)

    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    points = 0.0
    review = ''

    number_of_errors = 0
    for entry in data['htmls']:
        tmp_rating, tmp__errors = rate_entry(entry, global_translation, local_translation)
        rating += tmp_rating
        errors.extend(tmp__errors)

    number_of_errors = len(errors)

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

def get_data_for_url(url):
    """
    This function retrieves data for a given URL using the Sitespeed.io tool.

    The function configures Sitespeed.io to run with specific parameters,
    including running in headless mode, ignoring certificate errors,
    and capturing all response bodies.

    Parameters:
    url (str): The URL for which to retrieve data.

    Returns:
    data (dict): A dictionary containing the data retrieved from the URL.
    """

    # We don't need extra iterations for what we are using it for
    sitespeed_iterations = 1
    sitespeed_arg = (
            '--shm-size=1g -b chrome '
            '--plugins.remove screenshot --plugins.remove html --plugins.remove metrics '
            '--browsertime.screenshot false --screenshot false --screenshotLCP false '
            '--browsertime.screenshotLCP false --chrome.cdp.performance false '
            '--browsertime.chrome.timeline false --videoParams.createFilmstrip false '
            '--visualMetrics false --visualMetricsPerceptual false '
            '--visualMetricsContentful false --browsertime.headless true '
            '--browsertime.chrome.includeResponseBodies all --utc true '
            '--browsertime.chrome.args ignore-certificate-errors '
            f'-n {sitespeed_iterations}')
    if 'nt' not in os.name:
        sitespeed_arg += ' --xvfb'

    sitespeed_arg += ' --postScript chrome-cookies.cjs --postScript chrome-versions.cjs'

    (_, filename) = get_result(
        url, SITESPEED_USE_DOCKER, sitespeed_arg, SITESPEED_TIMEOUT)

    # 1. Visit page like a normal user
    data = identify_files(filename)
    return data

def rate_entry(entry, global_translation, local_translation):
    """
    Rates an entry based on the number and types of HTML errors.

    This function takes an entry, global translations, and local translations as input.
    It calculates a rating for the entry based on the number and
    types of HTML errors present in the content of the entry.
    The function also groups the error messages and calculates an overall rating.

    Parameters:
    entry (dict): A dictionary containing the details of the entry including the URL and content.
    global_translation (function): A function for translating text globally.
    local_translation (function): A function for translating text locally.

    Returns:
    tuple: A tuple containing the overall rating (Rating object) and the errors (list).
    """
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    req_url = entry['url']
    name = get_friendly_url_name(global_translation, req_url, entry['index'])
    review_header = f'- {name} '

    set_cache_file(req_url, entry['content'], True)

    errors = get_errors('html',
                        {
                            'doc': req_url,
                            'out': 'json',
                            'level': 'error'
                        })
    number_of_errors = len(errors)

    error_message_grouped_dict = {}
    if number_of_errors > 0:
        error_message_grouped_dict = get_grouped_error_messages(
                                        entry,
                                        local_translation,
                                        errors,
                                        number_of_errors)

    number_of_error_types = len(error_message_grouped_dict)
    result = calculate_rating(number_of_error_types, number_of_errors)

    error_types_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    error_types_rating.set_overall(
            result[0],
            review_header + local_translation('TEXT_REVIEW_RATING_GROUPED').format(
                number_of_error_types,
                0.0))
    rating += error_types_rating

    error_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    error_rating.set_overall(result[1], review_header + local_translation(
        'TEXT_REVIEW_RATING_ITEMS').format(number_of_errors, 0.0))
    rating += error_rating
    return (rating, errors)

def get_grouped_error_messages(entry, local_translation, errors, number_of_errors):
    """
    Groups HTML error messages and counts their occurrences.

    This function takes an entry, local translations, a list of errors,
    and the total number of errors as input.
    It filters out irrelevant errors and groups the remaining ones by their messages.
    The function also counts the occurrences of each error message.

    Parameters:
    entry (dict): A dictionary containing the details of the entry including the URL and content.
    local_translation (function): A function for translating text locally.
    errors (list): A list of error messages.
    number_of_errors (int): The total number of errors.

    Returns:
    dict: A dictionary where the keys are the error messages and the values are their counts.
    """
    error_message_grouped_dict = {}
    regex = r"(“[^”]+”)"
    for item in errors:
        error_message = item['message']

            # Filter out CSS: entries that should not be here
        if error_message.startswith('CSS: '):
            number_of_errors -= 1
            continue

            # Filter out start html document stuff if not start webpage
        if entry['index'] > 1:
            is_html = False
            for html_str in HTML_STRINGS:
                if html_str in error_message:
                    number_of_errors -= 1
                    is_html = True
                    break

            if is_html:
                continue

        error_message = re.sub(
                regex, "X", error_message, 0, re.MULTILINE)

        if error_message_grouped_dict.get(error_message, False):
            error_message_grouped_dict[error_message] = \
                    error_message_grouped_dict[error_message] + 1
        else:
            error_message_grouped_dict[error_message] = 1

    if len(error_message_grouped_dict) > 0:
        error_message_grouped_sorted = sorted(
                error_message_grouped_dict.items(), key=lambda x: x[1], reverse=True)

        for item in error_message_grouped_sorted:
            item_value = item[1]
            item_text = item[0]

            review += local_translation(
                    'TEXT_REVIEW_ERRORS_ITEM'
                    ).format(item_text, item_value)

    return error_message_grouped_dict


def calculate_rating(number_of_error_types, number_of_errors):
    """
    Calculates ratings based on the number of error types and errors.

    This function takes the number of error types and the total number of errors as input.
    It calculates two ratings: one based on the number of error types and
    the other based on the total number of errors.
    The ratings are calculated such that a higher number of errors or
    error types will result in a lower rating. The minimum rating is 1.0.

    Parameters:
    number_of_error_types (int): The number of different types of errors.
    number_of_errors (int): The total number of errors.

    Returns:
    tuple: A tuple containing the rating based on the number of error types and
    the rating based on the total number of errors.
    """
    rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)

    rating_number_of_errors = 5.0 - ((number_of_errors / 2.0) / 5.0)

    rating_number_of_error_types = max(rating_number_of_error_types, 1.0)
    rating_number_of_errors = max(rating_number_of_errors, 1.0)

    return (rating_number_of_error_types, rating_number_of_errors)
