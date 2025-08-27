# -*- coding: utf-8 -*-
from datetime import timedelta
import os
import subprocess
import json
from helpers.models import Rating
from tests.sitespeed_base import get_result
from tests.utils import get_cache_path_for_file,\
                        has_cache_file,\
                        set_cache_file
from helpers.setting_helper import get_config

def get_errors_for_url(test_type, url):
    """
    Returns CSS errors for a given URL in JSON format.
    """
    params = {'doc': url, 'out': 'json', 'level': 'error'}
    return get_errors(test_type, params)

def get_errors(test_type, params):
    """
    This function takes a test type and parameters as input and
    returns any errors found during the test.

    The function checks if the test type is 'css' or 'html' and
    sets the test arguments accordingly.
    It then checks if a document URL is provided in the parameters.
    If the URL does not start with 'https://' or 'http://', it raises a ValueError.
    It then checks if the file is cached and if not, it caches the file.
    It then runs a command using the vnu.jar validator and returns any errors found.

    Parameters:
    test_type (str): The type of the test to be run. It can be 'css' or 'html'.
    params (dict): A dictionary containing the parameters for the test.
    It should contain a 'doc' key with the URL of the document to be tested.

    Returns:
    list: A list of dictionaries where each dictionary represents an error message.
    """

    url = ''
    arg = ''
    test_arg = ''
    errors = []
    is_html = False

    if 'css' in params or test_type == 'css':
        test_arg = ' --css --skip-non-css'
    if 'html' in params or test_type == 'html':
        test_arg = ' --html --skip-non-html'
        is_html = True

    if 'doc' in params:
        url = params['doc']

        if 'https://' not in url and 'http://' not in url:
            raise ValueError(
                f'Tested url must start with \'https://\' or \'http://\': {url}')

        file_path = get_cache_path_for_file(url, True)
        if is_html:
            html_file_ending_fix = file_path.replace('.cache', '.cache.html')
            html_file_ending_fix = html_file_ending_fix.replace('.tmp', '.tmp.html')
            if has_cache_file(url, True, timedelta(minutes=get_config('general.cache.max-age'))) \
                    and not os.path.exists(html_file_ending_fix):
                os.rename(file_path, html_file_ending_fix)
            file_path = html_file_ending_fix

        arg = f'--exit-zero-always{test_arg} --stdout --format json --errors-only {file_path}'

    command = (f'java -jar node_modules{os.path.sep}vnu-jar'
               f'{os.path.sep}build{os.path.sep}dist{os.path.sep}'
               f'vnu.jar {arg}')
    with subprocess.Popen(command.split(), stdout=subprocess.PIPE) as process:
        output, _ = process.communicate(timeout=get_config('general.request.timeout') * 10)

        json_result = json.loads(output)
        if 'messages' in json_result:
            errors = json_result['messages']

    for error in errors:
        if 'url' in error and get_config('general.cache.use'):
            error['file'] = error['url']
        error['url'] = url

    return errors

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
    if get_config('tests.sitespeed.xvfb'):
        sitespeed_arg += ' --xvfb'

    (_, filename) = get_result(
        url,
        get_config('tests.sitespeed.docker.use'),
        sitespeed_arg,
        get_config('tests.sitespeed.timeout'))

    # 1. Visit page like a normal user
    data = identify_files(filename)
    return data


def identify_files(filename):
    """
    This function takes a filename as input and identifies different types of files in the HAR data.

    The function reads the HAR data from the file, iterates over the entries,
    and categorizes them into HTML and CSS files.
    It also checks if the file is already cached and if not, it caches the file.

    Parameters:
    filename (str): The name of the file containing the HAR data.

    Returns:
    dict: A dictionary containing categorized file data.
    The dictionary has four keys - 'htmls', 'elements', 'attributes', and 'resources'.
    Each key maps to a list of dictionaries where each dictionary contains:
    - 'url',
    - 'content'
    - 'index'
    of the file.
    """

    data = {
        'all': [],
        'htmls': [],
        'elements': [],
        'attributes': [],
        'resources': []
    }

    if not os.path.exists(filename):
        return None

    with open(filename, encoding='utf-8') as json_input_file:
        har_data = json.load(json_input_file)

        if 'log' in har_data:
            har_data = har_data['log']

        req_index = 1
        for entry in har_data["entries"]:
            req = entry['request']
            res = entry['response']
            req_url = req['url']

            if 'content' not in res:
                continue
            if 'mimeType' not in res['content']:
                continue
            if 'size' not in res['content']:
                continue
            if res['content']['size'] <= 0:
                continue

            if 'html' in res['content']['mimeType']:
                if not has_cache_file(
                        req_url,
                        True,
                        timedelta(minutes=get_config('general.cache.max-age'))):
                    set_cache_file(req_url, res['content']['text'], True)
                obj = {
                    'url': req_url,
                    'content': res['content']['text'],
                    'index': req_index
                    }
                data['all'].append(obj)
                data['htmls'].append(obj)
            elif 'css' in res['content']['mimeType']:
                if not has_cache_file(
                        req_url,
                        True,
                        timedelta(minutes=get_config('general.cache.max-age'))):
                    set_cache_file(req_url, res['content']['text'], True)
                obj = {
                    'url': req_url,
                    'content': res['content']['text'],
                    'index': req_index
                    }
                data['all'].append(obj)
                data['resources'].append(obj)
            req_index += 1

    return data

def get_rating(global_translation,
               error_types_review,
               error_review,
               result):
    """
    Calculates and returns the overall rating based on the given parameters.

    Parameters:
    global_translation (function): A function to translate text to a global language.
    error_types_review (str): The review of error types.
    error_review (str): The review of errors.
    result (tuple): The result object containing overall and standards ratings.

    Returns:
    Rating: The overall rating calculated based on error types and errors.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    errors_type_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_type_rating.set_overall(result[0])
    errors_type_rating.set_standards(result[0], error_types_review)
    rating += errors_type_rating

    errors_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_rating.set_overall(result[1])
    errors_rating.set_standards(result[1], error_review)
    rating += errors_rating
    return rating

def get_error_review(review_header, number_of_errors, local_translation):
    """
    Generates a review string for the errors.

    Parameters:
    review_header (str): The header of the review.
    number_of_errors (int): The number of error.
    local_translation (function): The function to translate the review text.

    Returns:
    str: The review string for the errors.
    """
    return review_header + local_translation('TEXT_REVIEW_RATING_ITEMS').format(
            number_of_errors, 0.0)

def get_error_types_review(review_header, number_of_error_types, local_translation):
    """
    Generates a review string for the error types.

    Parameters:
    review_header (str): The header of the review.
    number_of_error_types (int): The number of error types.
    local_translation (function): The function to translate the review text.

    Returns:
    str: The review string for the error types.
    """
    return review_header + local_translation('TEXT_REVIEW_RATING_GROUPED').format(
        number_of_error_types, 0.0)

def get_reviews_from_errors(msg_grouped_dict, local_translation):
    """
    Generates a review string from the grouped error messages.

    Parameters:
    msg_grouped_dict (dict): The dictionary of grouped error messages.
    local_translation (function): The function to translate the review text.

    Returns:
    str: The review string generated from the error messages.
    """
    review = ''
    if len(msg_grouped_dict) > 0:
        error_message_grouped_sorted = sorted(
            msg_grouped_dict.items(), key=lambda x: x[1], reverse=True)

        for item in error_message_grouped_sorted:
            item_value = item[1]
            item_text = item[0]

            review += local_translation('TEXT_REVIEW_ERRORS_ITEM').format(item_text, item_value)
    return review

def calculate_rating(number_of_error_types, number_of_errors):
    """
    Calculates and returns the ratings based on the number of error types and
    total number of errors.

    The rating for number of error types is calculated
    as 5.0 minus the number of error types divided by 5.0.
    The rating for number of errors is calculated
    as 5.0 minus half of the number of errors divided by 5.0.
    Both ratings are ensured to be at least 1.0.

    Parameters:
    number_of_error_types (int): The number of different types of errors.
    number_of_errors (int): The total number of errors.

    Returns:
    tuple: A tuple containing the rating for number of error types and
    the rating for number of errors.
    """

    rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)

    rating_number_of_errors = 5.0 - ((number_of_errors / 2.0) / 5.0)

    rating_number_of_error_types = max(rating_number_of_error_types, 1.0)
    rating_number_of_errors = max(rating_number_of_errors, 1.0)

    return (rating_number_of_error_types, rating_number_of_errors)
