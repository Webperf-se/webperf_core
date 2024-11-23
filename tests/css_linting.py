# -*- coding: utf-8 -*-
from datetime import datetime
import json
import os
from pathlib import Path
import re
import urllib  # https://docs.python.org/3/library/urllib.parse.html
from bs4 import BeautifulSoup
from helpers.models import Rating
from helpers.setting_helper import get_config
from tests.utils import get_friendly_url_name, get_translation, set_cache_file
from tests.lint_base import calculate_rating, get_data_for_url,\
    get_error_review, get_error_types_review,\
    get_errors_for_url, get_rating, get_reviews_from_errors

# DEFAULTS
GROUP_ERROR_MSG_REGEX = r"(\"[^\"]+\")"

def run_test(global_translation, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    local_translation = get_translation('css_validator_w3c', get_config('general.language'))

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    rating = Rating(global_translation, get_config('general.review.improve-only'))
    data = get_data_for_url(url)
    if data is None:
        rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (rating, {'failed': True })


    # 2. FIND ALL INLE CSS (AND CALCULTE)
    # 2.1 FINS ALL <STYLE>
    all_link_resources = []

    result_dict = {
        'has_style_elements': False,
        'has_style_attributes': False,
        'has_css_files': False,
        'errors': {
            'all': [],
            'style_element': [],
            'style_attribute': [],
            'style_files': []
        },
        'sources': []
    }

    for html_entry in data['htmls']:
        tmp_all_link_resources, tmp_rating = handle_html_markup_entry(
            html_entry,
            global_translation,
            url,
            local_translation,
            result_dict)
        rating += tmp_rating
        all_link_resources.extend(tmp_all_link_resources)

    for resource_url in all_link_resources:
        for entry in data['all']:
            if resource_url == entry['url']:
                result_dict['sources'].append({
                    'url': resource_url,
                    'index': entry['index']
                })

    # 4 Check if website inlcuded css files in other ways
    for link_resource in all_link_resources:
        data_resource_info_to_remove = None
        for data_resource_info in data['resources']:
            if data_resource_info['url'] == link_resource:
                data_resource_info_to_remove = data_resource_info
                break
        if data_resource_info_to_remove is not None:
            data['resources'].remove(data_resource_info_to_remove)

    rating += rate_css(
        global_translation,
        local_translation,
        data,
        result_dict)

    points = rating.get_overall()

    review = ''
    if points >= 5.0:
        review = local_translation('TEXT_REVIEW_CSS_VERY_GOOD')
    elif points >= 4.0:
        review = local_translation('TEXT_REVIEW_CSS_IS_GOOD')
    elif points >= 3.0:
        review = local_translation('TEXT_REVIEW_CSS_IS_OK')
    elif points > 1.0:
        review = local_translation('TEXT_REVIEW_CSS_IS_BAD')
    elif points <= 1.0:
        review = local_translation('TEXT_REVIEW_CSS_IS_VERY_BAD')

    rating.overall_review = review

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)

def handle_html_markup_entry(entry, global_translation, url, local_translation, result_dict):
    """
    Handles an entry in the webpage data, checks for CSS related errors and rates them.

    Parameters:
    entry (dict): The entry in the webpage data to handle.
    global_translation (function): Function to translate text globally.
    url (str): The URL of the webpage.
    local_translation (function): Function to translate text locally.
    result_dict (dict): Dictionary containing results of previous checks.

    Returns:
    list: All link resources found in the entry.
    Rating: The rating after evaluating the CSS related errors in the entry.
    """
    all_link_resources = []
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    req_url = entry['url']
    name = get_friendly_url_name(global_translation, req_url, entry['index'])
    html = entry['content']
    (elements, errors) = get_errors_for_style_tags(req_url, html)
    if len(elements) > 0:
        result_dict['has_style_elements'] = True
        result_dict['errors']['all'].extend(errors)
        result_dict['errors']['style_element'].extend(errors)
        rating += create_review_and_rating(
                errors,
                global_translation,
                local_translation,
                f'- `<style>` in: {name}')

        # 2.2 FIND ALL style=""
    (elements, errors) = get_errors_for_style_attributes(req_url, html)
    if len(elements) > 0:
        result_dict['has_style_attributes'] = True
        result_dict['errors']['all'].extend(errors)
        result_dict['errors']['style_attribute'].extend(errors)
        rating += create_review_and_rating(
                errors,
                global_translation,
                local_translation,
                f'- `style=""` in: {name}')

    if 'has_style_elements' in result_dict or\
            'has_style_attributes' in result_dict:
        all_link_resources.append(req_url)

        # 3 FIND ALL <LINK> (rel=\"stylesheet\")
    (link_resources, errors) = get_errors_for_link_tags(html, url)
    if len(link_resources) > 0:
        all_link_resources.extend(link_resources)
        result_dict['has_css_files'] = True
        result_dict['errors']['all'].extend(errors)
        result_dict['errors']['style_files'].extend(errors)
        rating += create_review_and_rating(
                errors,
                global_translation,
                local_translation,
                f'- `<link rel=\"stylesheet\">` in: {name}')
    return all_link_resources, rating

def rate_css(global_translation, local_translation, data, result_dict):
    """
    Rates the CSS of a webpage based on various criteria.

    Parameters:
    global_translation (function): Function to translate text globally.
    local_translation (function): Function to translate text locally.
    data (dict): Data about the webpage resources.
    result_dict (dict): Dictionary containing results of previous checks.

    Returns:
    Rating: The final rating after evaluating the CSS of the webpage.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    has_css_contenttypes = False
    errors = []
    for data_resource_info in data['resources']:
        has_css_contenttypes = True
        errors += get_errors_for_url(
            'css',
            data_resource_info['url'])
        request_index = data_resource_info['index']
        name = get_friendly_url_name(global_translation, data_resource_info['url'], request_index)
        rating += create_review_and_rating(
            errors,
            global_translation,
            local_translation,
            f'- `content-type=\".*css.*\"` in: {name}')

    # Give full points if nothing was found
    if not result_dict['has_style_elements']:
        rating += rate_style_elements(global_translation, local_translation)

    if not result_dict['has_style_attributes']:
        rating += rate_style_attributes(global_translation, local_translation)

    if not result_dict['has_css_files']:
        rating += rate_css_files(global_translation, local_translation)

    if not has_css_contenttypes:
        rating += rate_css_contenttypes(global_translation, local_translation)

    return rating

def rate_css_contenttypes(global_translation, local_translation):
    """
    This function rates the content types of CSS files based on certain criteria.

    Parameters:
    global_translation (function): A function to translate text globally.
    local_translation (function): A function to translate text locally.

    Returns:
    Rating: The final rating after evaluating the content types of the CSS files.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    errors_type_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_type_rating.set_overall(5.0)
    errors_type_rating.set_standards(5.0,
            '- `content-type=\".*css.*\"`' + local_translation(
                'TEXT_REVIEW_RATING_GROUPED'
            ).format(
            0, 0.0))
    rating += errors_type_rating

    errors_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_rating.set_overall(5.0)
    errors_rating.set_standards(5.0,
            '- `content-type=\".*css.*\"`' +\
            local_translation('TEXT_REVIEW_RATING_ITEMS').format(0, 0.0))
    rating += errors_rating
    return rating

def rate_css_files(global_translation, local_translation):
    """
    This function rates CSS files based on certain criteria.

    Parameters:
    global_translation (function): A function to translate text globally.
    local_translation (function): A function to translate text locally.

    Returns:
    Rating: The final rating after evaluating the CSS files.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    errors_type_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_type_rating.set_overall(5.0)
    txt = '- `<link rel=\"stylesheet\">`' +\
               local_translation('TEXT_REVIEW_RATING_GROUPED').format(0, 0.0)
    errors_type_rating.set_standards(5.0, txt)
    rating += errors_type_rating

    errors_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_rating.set_overall(5.0)
    errors_rating.set_standards(5.0,
            '- `<link rel=\"stylesheet\">`' +\
            local_translation('TEXT_REVIEW_RATING_ITEMS').format(0, 0.0))
    rating += errors_rating
    return rating

def rate_style_attributes(global_translation, local_translation):
    """
    Rates the style attributes of a webpage based on certain standards. 

    The function creates two Rating objects, one for error types and one for errors. 
    Both ratings are initialized with a perfect score of 5.0. The function then adds 
    these ratings to a cumulative rating and returns it.

    Parameters:
    global_translation (function): Function to translate text to a global language.
    local_translation (function): Function to translate text to a local language.

    Returns:
    Rating: A cumulative rating of the style attributes.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    errors_type_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_type_rating.set_overall(5.0)
    errors_type_rating.set_standards(5.0,
            '- `style=""`'+ local_translation('TEXT_REVIEW_RATING_GROUPED').format(
            0, 0.0))
    rating += errors_type_rating

    errors_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_rating.set_overall(5.0)
    errors_rating.set_standards(5.0,
            '- `style=""`' + local_translation('TEXT_REVIEW_RATING_ITEMS').format(0, 0.0))
    rating += errors_rating
    return rating

def rate_style_elements(global_translation, local_translation):
    """
    Rates the style elements of a webpage based on certain standards. 

    The function creates two Rating objects, one for error types and one for errors. 
    Both ratings are initialized with a perfect score of 5.0. The function then adds 
    these ratings to a cumulative rating and returns it.

    Parameters:
    global_translation (function): Function to translate text to a global language.
    local_translation (function): Function to translate text to a local language.

    Returns:
    Rating: A cumulative rating of the style elements.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    errors_type_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_type_rating.set_overall(5.0)
    errors_type_rating.set_standards(5.0,
            '- `<style>`' + local_translation('TEXT_REVIEW_RATING_GROUPED').format(
            0, 0.0))
    rating += errors_type_rating

    errors_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    errors_rating.set_overall(5.0)
    errors_rating.set_standards(5.0,
            '- `<style>`' + local_translation('TEXT_REVIEW_RATING_ITEMS').format(0, 0.0))
    rating += errors_rating
    return rating

def get_errors_for_link_tags(html, url):
    """
    This function extracts all link elements from the given HTML content,
    checks if they are CSS links, resolves their URLs,
    and checks for errors in the CSS rules associated with these URLs.

    The function uses BeautifulSoup to parse the HTML content and find all link elements.
    It then checks each link element to see if it is a CSS link.
    A link element is considered a CSS link if its 'rel' attribute contains 'stylesheet' or
    if its 'rel' attribute contains 'prefetch' and its 'as' attribute is 'style'.

    If a link element is a CSS link and has an 'href' attribute,
    the function resolves the URL of the CSS resource associated with the link element.
    The function supports absolute URLs, protocol-relative URLs, root-relative URLs, 
    and path-relative URLs.

    Finally, the function checks for errors in the CSS rules associated with each resolved URL,
    and returns a tuple containing the list of resolved URLs and the list of errors found.

    Parameters:
    html (str): The HTML content of the web page.
    url (str): The URL of the web page.

    Returns:
    tuple: A tuple where the first element is a list of resolved URLs of CSS resources, 
           and the second element is a list of errors found in the CSS rules.
    """
    results = []

    soup = BeautifulSoup(html, 'lxml')
    elements = soup.find_all('link')

    o = urllib.parse.urlparse(url)
    parsed_url = f'{o.scheme}://{o.netloc}'
    parsed_url_scheme = o.scheme

    matching_elements = []

    resource_index = 1
    for element in elements:
        if not element.has_attr('rel'):
            continue
        resource_type = element['rel']
        is_css_link = False
        if 'stylesheet' in resource_type:
            is_css_link = True
        if 'prefetch' in resource_type and element.has_attr('as') and 'style' == element['as']:
            is_css_link = True
        if is_css_link:
            if not element.has_attr('href'):
                continue
            resource_url = element['href']

            if resource_url.startswith('//'):
                # do nothing, complete url
                resource_url = parsed_url_scheme + ':' + resource_url
            elif resource_url.startswith('/'):
                # relative url, complement with dns
                resource_url = parsed_url + resource_url
            elif not resource_url.startswith('http://') and\
                    not resource_url.startswith('https://'):
                # relative url, but without starting /
                resource_url = parsed_url + '/' + resource_url

            # 3.1 GET ERRORS FROM SERVICE (FOR EVERY <LINK>) AND CALCULATE SCORE
            results += get_errors_for_url(
                'css',
                resource_url)
            resource_index += 1
            matching_elements.append(resource_url)

    return (matching_elements, results)


def get_errors_for_style_attributes(url, html):
    """
    This function extracts all HTML elements with style attributes from the given HTML content, 
    constructs CSS rules from these style attributes, and checks for errors in these rules.

    The function uses BeautifulSoup to parse the HTML content and
    find all elements with style attributes. 
    It then constructs a string of CSS rules from these style attributes,
    with each rule consisting of the element name and the style attribute content.

    If the constructed CSS string is not empty,
    the function creates a temporary URL by appending '#styles-attributes' to the given URL,
    and stores the CSS string in a cache file associated with this temporary URL. 

    Finally, the function checks for errors in the CSS rules associated with the temporary URL,
    and returns a tuple containing the list of elements with style attributes and
    the list of errors found.

    Parameters:
    url (str): The URL of the web page.
    html (str): The HTML content of the web page.

    Returns:
    tuple: A tuple where the first element is a list of elements with style attributes, 
           and the second element is a list of errors found in the CSS rules.
    """
    soup = BeautifulSoup(html, 'lxml')
    elements = soup.find_all(attrs={"style": True})

    results = []
    temp_attribute_css = ''

    for element in elements:
        temp_attribute_css += '' + f"{element.name}{{{element['style']}}}"

    if temp_attribute_css != '':
        tmp_url = f'{url}#styles-attributes'
        set_cache_file(tmp_url, temp_attribute_css, True)
        results = get_errors_for_url(
            'css',
            tmp_url)
        temp_attribute_css = ''

    return (elements, results)


def get_errors_for_style_tags(url, html):
    """
    Extracts the 'style' tags from the HTML of a given URL and checks for CSS errors.

    The function uses BeautifulSoup to parse the HTML and find all 'style' elements.
    The text of these elements is concatenated and checked for CSS errors.
    If any inline CSS is found,
    it is temporarily saved and the URL is updated to include '#style-elements'.
    The CSS errors for this updated URL are then retrieved.

    Parameters:
    url (str): The URL of the webpage to check.
    html (str): The HTML of the webpage to check.

    Returns:
    tuple: A tuple containing the 'style' elements and the CSS errors for the URL.
    """
    soup = BeautifulSoup(html, 'lxml')
    elements = soup.find_all('style')

    results = []
    temp_inline_css = ''
    for element in elements:
        temp_inline_css += '' + element.text

    if temp_inline_css != '':
        tmp_url = f'{url}#style-elements'
        set_cache_file(tmp_url, temp_inline_css, True)
        results = get_errors_for_url(
            'css',
            tmp_url)
        temp_inline_css = ''

    return (elements, results)


def get_mdn_web_docs_css_features():
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    file_path = os.path.join(base_directory, 'defaults', 'mdn-rules.json')
    if not os.path.isfile(file_path):
        print(f"ERROR: No {file_path} file found!")
        return ({}, {})

    with open(file_path) as json_rules_file:
        rules = json.load(json_rules_file)
        css_rules = rules['css']

        return (css_rules['features'], css_rules['functions'])


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
            error_message = item['text']
            error_message_dict[error_message] = "1"

            tmp = re.sub(
                GROUP_ERROR_MSG_REGEX, "X", error_message, 0, re.MULTILINE)
            if not get_config('general.review.details'):
                error_message = tmp

            if msg_grouped_dict.get(item['text'], False):
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
