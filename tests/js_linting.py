# -*- coding: utf-8 -*-
from datetime import datetime
import json
import os
from pathlib import Path
import re
import urllib
from bs4 import BeautifulSoup
from helpers.models import Rating
from helpers.setting_helper import get_config
from tests.utils import get_friendly_url_name, get_translation, set_cache_file
from tests.lint_base import calculate_rating, get_data_for_url,\
    get_error_review, get_error_types_review,\
    get_errors_for_url, get_rating, get_reviews_from_errors

# DEFAULTS
GROUP_ERROR_MSG_REGEX = r"(\'[^\']+\')"
FIRST_USED_AT_LINE_REGEX = r", first used at line [0-9]+"

def run_test(global_translation, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    local_translation = get_translation('js_linting', get_config('general.language'))

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    rating = Rating(global_translation, get_config('general.review.improve-only'))
    data = get_data_for_url(url)
    if data is None:
        rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (rating, {'failed': True })

    all_script_resources = []

    result_dict = {
        'has_script_elements': False,
        'has_script_files': False,
        'errors': {
            'all': [],
            'script_element': [],
            'script_files': []
        },
        'sources': []
    }

    for html_entry in data['htmls']:
        tmp_all_script_resources, tmp_rating = handle_html_markup_entry(
            html_entry,
            global_translation,
            url,
            local_translation,
            result_dict)
        rating += tmp_rating
        all_script_resources.extend(tmp_all_script_resources)

    for resource_url in all_script_resources:
        for entry in data['all']:
            if resource_url == entry['url']:
                result_dict['sources'].append({
                    'url': resource_url,
                    'index': entry['index']
                })

    for script_resource in all_script_resources:
        data_resource_info_to_remove = None
        for data_resource_info in data['scripts']:
            if data_resource_info['url'] == script_resource:
                data_resource_info_to_remove = data_resource_info
                break
        if data_resource_info_to_remove is not None:
            data['scripts'].remove(data_resource_info_to_remove)

    rating += rate_js(
        global_translation,
        local_translation,
        data,
        result_dict)

    points = rating.get_overall()

    review = ''
    if points >= 5.0:
        review = local_translation('TEXT_REVIEW_JS_VERY_GOOD')
    elif points >= 4.0:
        review = local_translation('TEXT_REVIEW_JS_IS_GOOD')
    elif points >= 3.0:
        review = local_translation('TEXT_REVIEW_JS_IS_OK')
    elif points > 1.0:
        review = local_translation('TEXT_REVIEW_JS_IS_BAD')
    elif points <= 1.0:
        review = local_translation('TEXT_REVIEW_JS_IS_VERY_BAD')

    rating.overall_review = review

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)

def handle_html_markup_entry(entry, global_translation, url, local_translation, result_dict):
    """
    Handles an entry in the webpage data, checks for JS related errors and rates them.

    Parameters:
    entry (dict): The entry in the webpage data to handle.
    global_translation (function): Function to translate text globally.
    url (str): The URL of the webpage.
    local_translation (function): Function to translate text locally.
    result_dict (dict): Dictionary containing results of previous checks.

    Returns:
    list: All script resources found in the entry.
    Rating: The rating after evaluating the JS related errors in the entry.
    """
    all_script_resources = []
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    req_url = entry['url']
    name = get_friendly_url_name(global_translation, req_url, entry['index'])
    html = entry['content']
    (elements, errors) = get_errors_for_script_tags(req_url, html)
    if len(elements) > 0:
        result_dict['has_script_elements'] = True
        result_dict['errors']['all'].extend(errors)
        result_dict['errors']['script_element'].extend(errors)
        rating += create_review_and_rating(
                errors,
                global_translation,
                local_translation,
                f'- `<script>` in: {name}')

    if 'has_script_elements' in result_dict:
        all_script_resources.append(req_url)

    (script_resources, errors) = get_errors_for_script_files(html, url)
    if len(script_resources) > 0:
        all_script_resources.extend(script_resources)
        result_dict['has_script_files'] = True
        result_dict['errors']['all'].extend(errors)
        result_dict['errors']['script_files'].extend(errors)
        rating += create_review_and_rating(
                errors,
                global_translation,
                local_translation,
                f'- `<script src=\"...\">` in: {name}')
    return all_script_resources, rating

def rate_js(global_translation, local_translation, data, result_dict):
    """
    Rates the JS of a webpage based on various criteria.

    Parameters:
    global_translation (function): Function to translate text globally.
    local_translation (function): Function to translate text locally.
    data (dict): Data about the webpage resources.
    result_dict (dict): Dictionary containing results of previous checks.

    Returns:
    Rating: The final rating after evaluating the JS of the webpage.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    has_js_contenttypes = False
    errors = []
    for data_resource_info in data['scripts']:
        has_js_contenttypes = True
        result_dict['sources'].append({
            'url': data_resource_info['url'],
            'index': data_resource_info['index']
        })
        errors += get_errors_for_url(
            'js',
            data_resource_info['url'])
        request_index = data_resource_info['index']
        name = get_friendly_url_name(global_translation, data_resource_info['url'], request_index)
        rating += create_review_and_rating(
            errors,
            global_translation,
            local_translation,
            f'- `content-type=\".*javascript.*\"` in: {name}')

    if not result_dict['has_script_elements']:
        rating += rate_script_elements(global_translation, local_translation)

    if not result_dict['has_script_files']:
        rating += rate_script_files(global_translation, local_translation)

    if not has_js_contenttypes:
        rating += rate_js_contenttypes(global_translation, local_translation)

    return rating

def rate_js_contenttypes(global_translation, local_translation):
    """
    This function rates the content types of JS files based on certain criteria.

    Parameters:
    global_translation (function): A function to translate text globally.
    local_translation (function): A function to translate text locally.

    Returns:
    Rating: The final rating after evaluating the content types of the JS files.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    errors_type_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_type_rating.set_overall(5.0)
    errors_type_rating.set_standards(5.0,
            '- `content-type=\".*javascript.*\"`' + local_translation(
                'TEXT_REVIEW_RATING_GROUPED'
            ).format(
            0, 0.0))
    rating += errors_type_rating

    errors_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_rating.set_overall(5.0)
    errors_rating.set_standards(5.0,
            '- `content-type=\".*javascript.*\"`' +\
            local_translation('TEXT_REVIEW_RATING_ITEMS').format(0, 0.0))
    rating += errors_rating
    return rating

def rate_script_files(global_translation, local_translation):
    """
    This function rates JS files based on certain criteria.

    Parameters:
    global_translation (function): A function to translate text globally.
    local_translation (function): A function to translate text locally.

    Returns:
    Rating: The final rating after evaluating the JS files.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    errors_type_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    txt = '- `<script src=\"...\">`' +\
               local_translation('TEXT_REVIEW_RATING_GROUPED').format(0, 0.0)
    errors_type_rating.set_standards(5.0, txt)
    rating += errors_type_rating

    errors_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_rating.set_overall(5.0)
    errors_rating.set_standards(5.0,
            '- `<script src=\"...\">`' +\
            local_translation('TEXT_REVIEW_RATING_ITEMS').format(0, 0.0))
    rating += errors_rating
    return rating

def rate_script_elements(global_translation, local_translation):
    """
    Rates the script elements of a webpage based on certain standards. 

    The function creates two Rating objects, one for error types and one for errors. 
    Both ratings are initialized with a perfect score of 5.0. The function then adds 
    these ratings to a cumulative rating and returns it.

    Parameters:
    global_translation (function): Function to translate text to a global language.
    local_translation (function): Function to translate text to a local language.

    Returns:
    Rating: A cumulative rating of the script elements.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    errors_type_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_type_rating.set_overall(5.0)
    errors_type_rating.set_standards(5.0,
            '- `<script>`' + local_translation('TEXT_REVIEW_RATING_GROUPED').format(
            0, 0.0))
    rating += errors_type_rating

    errors_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_rating.set_overall(5.0)
    errors_rating.set_standards(5.0,
            '- `<script>`' + local_translation('TEXT_REVIEW_RATING_ITEMS').format(0, 0.0))
    rating += errors_rating
    return rating

def get_errors_for_script_files(html, url):
    """
    This function extracts all script elements with src attributes from the given HTML content,
    resolves their URLs, and checks for errors in the JS rules associated with these URLs.

    The function uses BeautifulSoup to parse the HTML content and find all script elements.
    It then checks each script element to see if it has a src attribute.
    If a script element has a src attribute, the function resolves the URL of the JS resource
    associated with the script element. The function supports absolute URLs, protocol-relative URLs,
    root-relative URLs, and path-relative URLs.

    Finally, the function checks for errors in the JS rules associated with each resolved URL,
    and returns a tuple containing the list of resolved URLs and the list of errors found.

    Parameters:
    html (str): The HTML content of the web page.
    url (str): The URL of the web page.

    Returns:
    tuple: A tuple where the first element is a list of resolved URLs of JS resources, 
           and the second element is a list of errors found in the JS rules.
    """
    results = []

    soup = BeautifulSoup(html, 'lxml')
    elements = soup.find_all('script')

    o = urllib.parse.urlparse(url)
    parsed_url = f'{o.scheme}://{o.netloc}'
    parsed_url_scheme = o.scheme

    matching_elements = []

    resource_index = 1
    for element in elements:
        if not element.has_attr('src'):
            continue
        resource_url = element['src']

        if resource_url.startswith('//'):
            resource_url = parsed_url_scheme + ':' + resource_url
        elif resource_url.startswith('../'):
            test_url = o.path
            while resource_url.startswith('../'):
                rindex = test_url.rfind('/')
                test_url = f'{test_url[:rindex]}'
                rindex = test_url.rfind('/')
                test_url = f'{test_url[:rindex]}'

                resource_url = resource_url.lstrip('../')
            resource_url = parsed_url + test_url + '/' + resource_url
        elif resource_url.startswith('/'):
            resource_url = parsed_url + resource_url
        elif not resource_url.startswith('http://') and\
                not resource_url.startswith('https://'):
            resource_url = parsed_url + '/' + resource_url

        results += get_errors_for_url(
            'js',
            resource_url)
        resource_index += 1
        matching_elements.append(resource_url)

    return (matching_elements, results)

def get_errors_for_script_tags(url, html):
    """
    Extracts the 'script' tags from the HTML of a given URL and checks for JS errors.

    The function uses BeautifulSoup to parse the HTML and find all 'script' elements.
    The text of these elements is concatenated and checked for JS errors.
    If any inline JS is found,
    it is temporarily saved and the URL is updated to include '#script-elements'.
    The JS errors for this updated URL are then retrieved.

    Parameters:
    url (str): The URL of the webpage to check.
    html (str): The HTML of the webpage to check.

    Returns:
    tuple: A tuple containing the 'script' elements and the JS errors for the URL.
    """
    soup = BeautifulSoup(html, 'lxml')
    elements = soup.find_all('script')

    results = []
    temp_inline_js = ''
    for element in elements:
        if element.string:
            temp_inline_js += '' + element.string

    if temp_inline_js != '':
        tmp_url = f'{url}#script-elements'
        set_cache_file(tmp_url, temp_inline_js, True)
        results = get_errors_for_url(
            'js',
            tmp_url)
        temp_inline_js = ''

    return (elements, results)

def replacer(match):
    text = match.group(1)
    text = re.sub(r'([\'])', '“', text, 1)
    text = re.sub(r'([\'])', '”', text, 1)
    return text

def create_review_and_rating(errors, global_translation, local_translation, review_header):
    """
    Creates a review and rating based on the provided errors and translations.

    Parameters:
    errors (list): The list of errors to be reviewed.
    global_translation (function): The function to translate the global text.
    local_translation (function): The function to translate the local text.
    review_header (str): The header of the review.

    Returns:
    Rating: The overall rating calculated based on the errors and translations.
    """

    number_of_errors = len(errors)

    error_message_dict = {}
    msg_grouped_dict = {}
    msg_grouped_for_rating_dict = {}
    if number_of_errors > 0:
        for item in errors:
            error_message = item['message']
            error_message = re.sub(r"(['][^']+['])", replacer, error_message)
            error_message_dict[error_message] = "1"

            tmp = re.sub(
                r"(“[^”]+”)", "X", error_message, 0, re.MULTILINE)
            if not get_config('general.review.details'):
                error_message = tmp

            if msg_grouped_dict.get(error_message, False):
                msg_grouped_dict[error_message] = msg_grouped_dict[error_message] + 1
            else:
                msg_grouped_dict[error_message] = 1

            if msg_grouped_for_rating_dict.get(tmp, False):
                msg_grouped_for_rating_dict[tmp] = msg_grouped_for_rating_dict[tmp] + 1
            else:
                msg_grouped_for_rating_dict[tmp] = 1


    rating = Rating(global_translation, get_config('general.review.improve-only'))

    number_of_error_types = len(msg_grouped_for_rating_dict)

    rating += get_rating(
        global_translation,
        get_error_types_review(review_header, number_of_error_types, local_translation),
        get_error_review(review_header, number_of_errors, local_translation),
        calculate_rating(number_of_error_types, number_of_errors))

    rating.standards_review = rating.standards_review +\
        get_reviews_from_errors(msg_grouped_dict, local_translation)

    return rating
