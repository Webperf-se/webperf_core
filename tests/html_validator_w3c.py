# -*- coding: utf-8 -*-
from datetime import datetime
import re

from bs4 import BeautifulSoup
from models import Rating
from tests.utils import get_friendly_url_name, get_http_content,\
    get_translation,\
    set_cache_file
from tests.w3c_base import calculate_rating, get_data_for_url,\
    get_error_review, get_error_types_review,\
    get_errors_for_url, get_rating, get_reviews_from_errors
from helpers.setting_helper import get_config

# DEFAULTS
HTML_REVIEW_GROUP_ERRORS = True
HTML_START_STRINGS = [
        'Start tag seen without seeing a doctype first. Expected “<!DOCTYPE html>”',
        'Element “head” is missing a required instance of child element “title”.'
    ]


def run_test(global_translation, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    local_translation = get_translation('html_validator_w3c', get_config('general.language'))

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    rating = Rating(global_translation, get_config('general.review.improve-only'))
    data = get_data_for_url(url)
    if data is None:
        rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (rating, {'failed': True })

    result_dict = {
        'errors': {
            'all': [],
            'html_files': []
        }
    }

    for html_entry in data['htmls']:
        tmp_rating = handle_html_markup_entry(
            html_entry,
            global_translation,
            local_translation,
            result_dict)
        rating += tmp_rating

    number_of_errors = len(result_dict['errors']['html_files'])
    points = rating.get_overall()

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

    rating.standards_review = rating.overall_review + rating.standards_review
    rating.overall_review = review

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)

def handle_html_markup_entry(entry, global_translation, local_translation, result_dict):
    """
    Handles an entry in the webpage data, checks for HTML related errors and rates them.

    Parameters:
    entry (dict): The entry in the webpage data to handle.
    global_translation (function): Function to translate text globally.
    url (str): The URL of the webpage.
    local_translation (function): Function to translate text locally.
    result_dict (dict): Dictionary containing results of previous checks.

    Returns:
    list: All link resources found in the entry.
    Rating: The rating after evaluating the HTML related errors in the entry.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    req_url = entry['url']
    name = get_friendly_url_name(global_translation, req_url, entry['index'])
    html = entry['content']
    errors = get_errors_for_html(req_url, html, local_translation)
    result_dict['errors']['all'].extend(errors)
    result_dict['errors']['html_files'].extend(errors)
    is_first_entry = entry['index'] <= 1
    rating += create_review_and_rating(
        is_first_entry,
        errors,
        global_translation,
        local_translation,
        f'- {name}')

    return rating

def create_review_and_rating(
        is_first_entry,
        errors,
        global_translation,
        local_translation,
        review_header):
    """
    Creates a review and rating based on the provided errors and translations.

    Parameters:
    is_first_entry (bool): Specify if this is the first entry
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

            # Filter out CSS: entries that should not be here
            if error_message.startswith('CSS: '):
                number_of_errors -= 1
                continue

            # Filter out start html document stuff if not start webpage
            if not is_first_entry and is_start_html_error(error_message):
                number_of_errors -= 1
                continue

            error_message_dict[error_message] = "1"

            tmp = re.sub(
                r"(“[^”]+”)", "X", error_message, 0, re.MULTILINE)
            if HTML_REVIEW_GROUP_ERRORS:
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

def is_start_html_error(error_message):
    """
    Checks if any string in HTML_START_STRINGS is present in the error_message.

    Args:
        error_message (str): The error message to check.

    Returns:
        bool: True if a HTML start string is found in error_message, False otherwise.
    """
    for html_str in HTML_START_STRINGS:
        if html_str in error_message:
            return True
    return False

def get_mdn_web_docs_deprecated_elements():
    """
    Returns a list of strings, of deprecated html elements.
    """
    elements = []

    html = get_http_content(
        ('https://developer.mozilla.org/'
         'en-US/docs/Web/HTML/Element'
         '#obsolete_and_deprecated_elements'))

    soup = BeautifulSoup(html, 'lxml')

    header = soup.find('h2', id = 'obsolete_and_deprecated_elements')
    if header is None:
        return []

    section = header.parent
    if section is None:
        return []

    tbody = section.find('tbody')
    if tbody is None:
        return []

    table_rows = tbody.find_all('tr')
    if table_rows is None:
        return []

    for table_row in table_rows:
        if table_row is None:
            continue

        first_td = table_row.find('td')
        if first_td is None:
            continue

        code = first_td.find('code')
        if code is None:
            continue

        regex = r'(\&lt;|<)(?P<name>[^<>]+)(\&gt;|>)'
        matches = re.search(regex, code.string)
        if matches:
            property_name = '<' + matches.group('name')
            elements.append(property_name)

    return sorted(list(set(elements)))


# TODO: change this to just in time, right now it is called every time webperf_core is being called.
html_deprecated_elements = get_mdn_web_docs_deprecated_elements()


def get_errors_for_html(url, html, local_translation):
    """
    Caches the HTML content of a URL and retrieves the errors associated with it.

    Args:
        url (str): The URL to check for errors.
        html (str): The HTML content of the URL.

    Returns:
        list: A list of errors associated with the URL.
    """
    set_cache_file(url, html, True)
    results = get_errors_for_url(
        'html',
        url)

    for element in html_deprecated_elements:
        if element not in html:
            continue
        results.append({
                'type': 'error',
                'message': local_translation('TEXT_REVIEW_DEPRECATED_ELEMENT').format(element)
            })

    return results
