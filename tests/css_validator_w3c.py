# -*- coding: utf-8 -*-
from datetime import datetime
import os
import re
import urllib  # https://docs.python.org/3/library/urllib.parse.html

from bs4 import BeautifulSoup
from models import Rating

from tests.utils import get_friendly_url_name, get_http_content,\
     get_translation, set_cache_file, get_config_or_default
from tests.w3c_base import get_errors, identify_files
from tests.sitespeed_base import get_result as get_sitespeed_result

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
USE_CACHE = get_config_or_default('cache_when_possible')
CACHE_TIME_DELTA = get_config_or_default('cache_time_delta')

CSS_REVIEW_GROUP_ERRORS = get_config_or_default('css_review_group_errors')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
SITESPEED_USE_DOCKER = get_config_or_default('sitespeed_use_docker')
SITESPEED_TIMEOUT = get_config_or_default('sitespeed_timeout')
GROUP_ERROR_MSG_REGEX = r"(“[^”]+”)"


def run_test(global_translation, lang_code, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    local_translation = get_translation('css_validator_w3c', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    result_dict = {
        'has_style_elements': False,
        'has_style_attributes': False,
        'has_css_files': False,
        'errors': {
            'all': [],
            'style_element': [],
            'style_attribute': [],
            'style_files': []
        }
    }

    # We don't need extra iterations for what we are using it for
    data = get_result(url)
    # 2. FIND ALL INLE CSS (AND CALCULTE)
    # 2.1 FINS ALL <STYLE>
    all_link_resources = []

    for entry in data['htmls']:
        tmp_all_link_resources, tmp_rating = handle_entry(
            entry,
            global_translation,
            url,
            local_translation,
            result_dict)
        rating += tmp_rating
        all_link_resources.extend(tmp_all_link_resources)

    # 4 Check if website inlcuded css files in other ways
    for link_resource in all_link_resources:
        data_resource_info_to_remove = None
        for data_resource_info in data['resources']:
            if data_resource_info['url'] == link_resource:
                data_resource_info_to_remove = data_resource_info
                break
        if data_resource_info_to_remove is not None:
            data['resources'].remove(data_resource_info_to_remove)

    tmp_rating = rate_css(
        global_translation,
        local_translation,
        data,
        result_dict)
    rating += tmp_rating

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)

def handle_entry(entry, global_translation, url, local_translation, result_dict):
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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

        # 2.3 GET ERRORS FROM SERVICE
        # 2.4 CALCULATE SCORE
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    has_css_contenttypes = False
    errors = []
    for data_resource_info in data['resources']:
        has_css_contenttypes = True
        errors += get_errors_for_url(
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_type_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_type_rating.set_overall(5.0)
    errors_type_rating.set_standards(5.0,
            '- `content-type=\".*css.*\"`' + local_translation('TEXT_REVIEW_RATING_GROUPED').format(
            0, 0.0))
    rating += errors_type_rating

    errors_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_type_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_type_rating.set_overall(5.0)
    txt = '- `<link rel=\"stylesheet\">`' +\
               local_translation('TEXT_REVIEW_RATING_GROUPED').format(0, 0.0)
    errors_type_rating.set_standards(5.0, txt)
    rating += errors_type_rating

    errors_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_type_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_type_rating.set_overall(5.0)
    errors_type_rating.set_standards(5.0,
            '- `style=""`'+ local_translation('TEXT_REVIEW_RATING_GROUPED').format(
            0, 0.0))
    rating += errors_type_rating

    errors_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_type_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_type_rating.set_overall(5.0)
    errors_type_rating.set_standards(5.0,
            '- `<style>`' + local_translation('TEXT_REVIEW_RATING_GROUPED').format(
            0, 0.0))
    rating += errors_type_rating

    errors_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_rating.set_overall(5.0)
    errors_rating.set_standards(5.0,
            '- `<style>`' + local_translation('TEXT_REVIEW_RATING_ITEMS').format(0, 0.0))
    rating += errors_rating
    return rating

def get_result(url):
    """
    This function performs a performance analysis of a given URL using the Sitespeed.io tool.

    The function constructs a string of command-line arguments for the Sitespeed.io tool,
    specifying various settings such as the browser to use (Chrome), the plugins to remove,
    the screenshot settings, the visual metrics settings, 
    the headless mode, the response bodies to include, the time zone, and the number of iterations.

    If the operating system is not Windows, the function also enables the Xvfb setting.
    The function then appends two postScript arguments to the command-line arguments string.

    The function calls the get_sitespeed_result function to run the Sitespeed.io tool with
    the constructed command-line arguments and get the result.
    The result is a filename of a file that contains the performance analysis result.

    Finally,
    the function calls the identify_files function to process the performance analysis result and
    returns the processed data.

    Parameters:
    url (str): The URL of the web page to analyze.

    Returns:
    dict: A dictionary that contains the processed performance analysis result.
    """
    sitespeed_iterations = 1
    sitespeed_arg = (
        '--shm-size=1g '
        '-b chrome '
        '--plugins.remove screenshot '
        '--plugins.remove html '
        '--plugins.remove metrics '
        '--browsertime.screenshot false '
        '--screenshot false '
        '--screenshotLCP false '
        '--browsertime.screenshotLCP false '
        '--chrome.cdp.performance false '
        '--browsertime.chrome.timeline false '
        '--videoParams.createFilmstrip false '
        '--visualMetrics false '
        '--visualMetricsPerceptual false '
        '--visualMetricsContentful false '
        '--browsertime.headless true '
        '--browsertime.chrome.includeResponseBodies all '
        '--utc true '
        f'--browsertime.chrome.args ignore-certificate-errors -n {sitespeed_iterations}')
    if 'nt' not in os.name:
        sitespeed_arg += ' --xvfb'

    sitespeed_arg += ' --postScript chrome-cookies.cjs --postScript chrome-versions.cjs'

    (_, filename) = get_sitespeed_result(
        url, SITESPEED_USE_DOCKER, sitespeed_arg, SITESPEED_TIMEOUT)

    # 1. Visit page like a normal user
    data = identify_files(filename)
    return data

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
            elif not resource_url.startswith('http://') and not resource_url.startswith('https://'):
                # relative url, but without starting /
                resource_url = parsed_url + '/' + resource_url

            # 3.1 GET ERRORS FROM SERVICE (FOR EVERY <LINK>) AND CALCULATE SCORE
            results += get_errors_for_url(
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
        results = get_errors_for_url(tmp_url)
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
        results = get_errors_for_url(tmp_url)
        temp_inline_css = ''

    return (elements, results)


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

def get_errors_for_url(url):
    """
    Returns CSS errors for a given URL in JSON format.
    """
    params = {'doc': url, 'out': 'json', 'level': 'error'}
    return get_errors('css', params)

def get_mdn_web_docs_css_features():
    """
    Returns a tuple containing 2 lists, first one of CSS features and
    second of CSS functions keys formatted as non-existent properties.
    """
    features = {}
    functions = {}

    html = get_http_content(
        'https://developer.mozilla.org/en-US/docs/Web/CSS/Reference')

    soup = BeautifulSoup(html, 'lxml')

    index_element = soup.find('div', class_='index')
    if index_element:
        links = index_element.find_all('a')
        for link in links:
            regex = r'(?P<name>[a-z\-0-9]+)(?P<func>[()]{0,2})[ ]*'
            matches = re.search(regex, link.string)
            if matches:
                property_name = matches.group('name')
                is_function = matches.group('func') in '()'
                if is_function:
                    functions[f"{property_name}"] = link.get('href')
                else:
                    features[f"{property_name}"] = link.get('href')
    else:
        print('no index element found')
    return (features, functions)


css_spec = get_mdn_web_docs_css_features()
css_features = css_spec[0]
css_functions = css_spec[1]


def get_properties_doesnt_exist_list():
    """
    Returns a list of CSS feature keys formatted as non-existent properties.
    """
    result = []
    css_features_keys = css_features.keys()
    for item in css_features_keys:
        result.append(f'Property “{item}” doesn\'t exist')
    return result

def get_function_is_not_a_value_list():
    """
    Returns a list of CSS function keys appended with an opening parenthesis.
    """
    result = []
    css_functions_keys = css_functions.keys()
    for item in css_functions_keys:
        result.append(f'{item}(')
    return result

css_properties_doesnt_exist = get_properties_doesnt_exist_list()
css_functions_no_support = get_function_is_not_a_value_list()


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
    whitelisted_words = css_properties_doesnt_exist

    whitelisted_words.append('“100%” is not a “font-stretch” value')
    whitelisted_words.extend(css_functions_no_support)

    number_of_errors = len(errors)

    error_message_dict = {}
    msg_grouped_dict = {}
    msg_grouped_for_rating_dict = {}
    if number_of_errors > 0:
        for item in errors:
            error_message = item['message']
            is_whitelisted = error_has_whitelisted_wording(error_message, whitelisted_words)

            if is_whitelisted:
                number_of_errors -= 1
            else:
                error_message_dict[error_message] = "1"

                tmp = re.sub(
                    GROUP_ERROR_MSG_REGEX, "X", error_message, 0, re.MULTILINE)
                if CSS_REVIEW_GROUP_ERRORS:
                    error_message = tmp

                if msg_grouped_dict.get(error_message, False):
                    msg_grouped_dict[error_message] = msg_grouped_dict[error_message] + 1
                else:
                    msg_grouped_dict[error_message] = 1

                if msg_grouped_for_rating_dict.get(tmp, False):
                    msg_grouped_for_rating_dict[tmp] = msg_grouped_for_rating_dict[tmp] + 1
                else:
                    msg_grouped_for_rating_dict[tmp] = 1


    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    number_of_error_types = len(msg_grouped_for_rating_dict)

    rating += get_rating(
        global_translation,
        get_error_types_review(review_header, number_of_error_types, local_translation),
        get_error_review(review_header, number_of_errors, local_translation),
        calculate_rating(number_of_error_types, number_of_errors))

    rating.standards_review = rating.standards_review +\
        get_reviews_from_errors(msg_grouped_dict, local_translation)

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


def error_has_whitelisted_wording(error_message, whitelisted_words):
    """
    Checks if the error message contains any of the whitelisted words.

    Parameters:
    error_message (str): The error message to be checked.
    whitelisted_words (list): The list of whitelisted words.

    Returns:
    bool: True if the error message contains a whitelisted word, False otherwise.
    """
    in_whitelisted = False
    for whitelisted_word in whitelisted_words:
        if whitelisted_word in error_message:
            in_whitelisted = True
            break
    return in_whitelisted

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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_type_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_type_rating.set_overall(result[0])
    errors_type_rating.set_standards(result[0], error_types_review)
    rating += errors_type_rating

    errors_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_rating.set_overall(result[1])
    errors_rating.set_standards(result[1], error_review)
    rating += errors_rating
    return rating
