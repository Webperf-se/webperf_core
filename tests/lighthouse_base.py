# -*- coding: utf-8 -*-
import os
import json
import time
from datetime import datetime
import subprocess
from models import Rating
from tests.utils import get_config_or_default,\
                        get_http_content,\
                        is_file_older_than,\
                        get_cache_path_for_rule,\
                        get_translation

# DEFAULTS
GOOGLEPAGESPEEDAPIKEY = get_config_or_default('googlePageSpeedApiKey')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
LIGHTHOUSE_USE_API = get_config_or_default('lighthouse_use_api')
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USE_CACHE = get_config_or_default('cache_when_possible')
CACHE_TIME_DELTA = get_config_or_default('cache_time_delta')

# look for words indicating item is insecure
INSECURE_STRINGS = ['security', 'säkerhet',
    'insecure', 'osäkra', 'unsafe',
    'insufficient security', 'otillräckliga säkerhetskontroller',
    'HTTPS']

# look for words indicating items is related to standard
STANDARD_STRINGS = ['gzip, deflate',
    'Deprecated', 'Utfasade ', 'quirks-mode', 'http/2']


def get_lighthouse_translations(module_name, lang_code, global_translation):
    """
    Retrieves the local and global translations for a given module and language code.

    Args:
        module_name (str): The name of the module for which translations are to be fetched.
        lang_code (str): The language code for which translations are to be fetched.
        global_translation (dict): The global translation dictionary.

    Returns:
        dict: A dictionary containing the language code,
              local translation for the module, and global translation.
    """
    local_translation = get_translation(module_name, lang_code)

    return {
        'code': lang_code,
        'module': local_translation,
        'global': global_translation
    }

def run_test(url, strategy, category, silance, lighthouse_translations):
    """
    https://www.googleapis.com/pagespeedonline/v5/runPagespeed?
        category=(performance/accessibility/best-practices/pwa/seo)
        &strategy=mobile
        &url=YOUR-SITE&
        key=YOUR-KEY
    """

    global_translation = lighthouse_translations['global']
    local_translation = lighthouse_translations['module']
    lang_code = lighthouse_translations['code']

    if not silance:
        print(local_translation('TEXT_RUNNING_TEST'))

        print(global_translation('TEXT_TEST_START').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))


    json_content = get_json_result(
        lang_code, url, strategy, category, GOOGLEPAGESPEEDAPIKEY)

    return_dict = {}
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    rating += create_rating_from_audits(category, global_translation, json_content, return_dict)
    review = rating.overall_review

    # Service score (0-100)
    score = json_content['categories'][category]['score']
    set_overall_rating_and_review(category, local_translation, score, rating, review)

    if not silance:
        print(global_translation('TEXT_TEST_END').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)

def create_rating_from_audit(item, global_translation, weight):
    """
    Creates a rating from a single audit item.

    The function first creates a Rating object and initializes several variables. It then checks
    if the item has a score and, if so, calculates the local points based on this score.

    The function then sets the item title, description, and display value if they exist in the
    item. It also sets the item review based on the local score and points.

    The function then checks if the item review or description contains any insecure or standard
    strings. If so, it adds the corresponding rating to the overall rating.

    The function finally returns a dictionary with the key as the local points minus the weight
    and the value as the rating.

    Args:
        item (dict): The audit item to be rated.
        global_translation (function): Function to get the globalized text.
        weight (float): The weight of the audit item.

    Returns:
        dict: A dictionary with the key as the local points minus the weight and the value as
              the rating.
    """
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    item_review = ''
    item_title = ''
    display_value = ''
    item_description = ''

    if 'score' not in item or item['score'] is None:
        return None

    local_score = float(
        item['score'])

    local_points = 5.0 * local_score
    if local_points < 1.0:
        local_points = 1
    if local_points >= 4.95:
        local_points = 5.0

    if 'title' in item:
        item_title = f'{item['title']}'

    if 'description' in item:
        item_description = item['description']

    if 'displayValue' in item:
        display_value = item['displayValue']

    if local_score == 0:
        item_review = f"- {global_translation(item_title)}"
    elif local_points == 5.0:
        item_review = f"- {global_translation(item_title)}"
    else:
        item_review = f"- {global_translation(item_title)}: {display_value}"

    rating.set_overall(local_points, item_review)

    item_review = item_review.lower()
    item_description = item_description.lower()

    has_insecure_string = contains_insecure_string(item_review, item_description)
    if has_insecure_string:
        rating += rate_containing_insecure_string(global_translation, local_score, item_title)

    has_standard_string = contains_standard_string(item_review, item_description)
    if has_standard_string:
        rating += rate_containing_standard_string(global_translation, local_score, item_title)

    return {
            'key': local_points - weight,
            'value': rating
        }


def create_rating_from_audits(category, global_translation, json_content, return_dict):
    """
    Creates a rating from audits contained in the provided JSON content.

    The function first creates a Rating object and a weight dictionary. It then iterates over the
    audits in the JSON content. For each audit, if it has a numeric value, this value is added to
    the return dictionary. If the audit key is in the weight dictionary, a review item is created
    from the audit, and if this review item is not None, it is added to the reviews list.

    The reviews are then sorted and added to the rating. The final rating is returned.

    Args:
        category (str): The category for the rating.
        global_translation (function): Function to get the globalized text.
        json_content (dict): The JSON content containing the audits.
        return_dict (dict): The dictionary to return the numeric values of the audits.

    Returns:
        Rating: The Rating object with the set ratings and reviews.
    """
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    weight_dict = create_weight_dict(category, json_content)
    reviews = []
    for audit_key, item in json_content['audits'].items():
        if 'numericValue' in item:
            return_dict[audit_key] = item['numericValue']

        if audit_key not in weight_dict:
            continue

        weight = weight_dict[audit_key]
        review_item = create_rating_from_audit(item, global_translation, weight)
        if review_item is None:
            continue
        reviews.append(review_item)

    sorted_reviews = sorted(reviews,
                            key=lambda x: x['key'])
    for review_item in sorted_reviews:
        rating += review_item['value']

    return rating

def rate_containing_standard_string(global_translation, local_score, item_title):
    """
    Rates an item based on whether it contains an 'standard' string.

    The function creates a Rating object with the given global translation and a constant review
    type. If the local score is 1, it sets the overall and standard ratings to 5.0.
    Otherwise, it sets these ratings to 1.0. The item title is included in the standard review.

    Args:
        global_translation (function): Function to get the globalized text.
        local_score (int): The local score of the item (1 or other).
        item_title (str): The title of the item to be rated.

    Returns:
        Rating: The Rating object with the set ratings and reviews.
    """
    local_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if local_score == 1:
        local_rating.set_overall(
                        5.0)
        local_rating.set_standards(
                        5.0, f'- {item_title}')
    else:
        local_rating.set_overall(
                        1.0)
        local_rating.set_standards(
                        1.0, f'- {item_title}')
    return local_rating

def rate_containing_insecure_string(global_translation, local_score, item_title):
    """
    Rates an item based on whether it contains an insecure string.

    The function creates a Rating object with the given global translation and a constant review
    type. If the local score is 1, it sets the overall and integrity and security ratings to 5.0.
    Otherwise, it sets these ratings to 1.0. The item title is included in the integrity and
    security review.

    Args:
        global_translation (function): Function to get the globalized text.
        local_score (int): The local score of the item (1 or other).
        item_title (str): The title of the item to be rated.

    Returns:
        Rating: The Rating object with the set ratings and reviews.
    """
    local_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if local_score == 1:
        local_rating.set_overall(
                        5.0)
        local_rating.set_integrity_and_security(
                        5.0, f'- {item_title}')
    else:
        local_rating.set_overall(
                        1.0)
        local_rating.set_integrity_and_security(
                        1.0, f'- {item_title}')
    return local_rating

def contains_standard_string(item_review, item_description):
    """
    Checks if the item review or description contains any 'standard' strings.

    The function iterates over a predefined list of standard strings. If any of these strings
    are found in the item review or description, the function returns True. If no standard
    strings are found, it returns False.

    Args:
        item_review (str): The review of the item to be checked.
        item_description (str): The description of the item to be checked.

    Returns:
        bool: True if an standard string is found, False otherwise.
    """
    has_standard_string = False
    for standard_str in STANDARD_STRINGS:
        if standard_str in item_review or standard_str in item_description:
            has_standard_string = True
            break
    return has_standard_string

def contains_insecure_string(item_review, item_description):
    """
    Checks if the item review or description contains any insecure strings.

    The function iterates over a predefined list of insecure strings. If any of these strings
    are found in the item review or description, the function returns True. If no insecure
    strings are found, it returns False.

    Args:
        item_review (str): The review of the item to be checked.
        item_description (str): The description of the item to be checked.

    Returns:
        bool: True if an insecure string is found, False otherwise.
    """
    has_insecure_string = False
    for insecure_str in INSECURE_STRINGS:
        if insecure_str in item_review or insecure_str in item_description:
            has_insecure_string = True
            break
    return has_insecure_string

def set_overall_rating_and_review(category, local_translation, score, rating, review):
    """
    Sets the overall rating and review based on the given category and score.

    The function first converts the score to a 1-5 grading system. Then, based on the category,
    it sets the overall and specific category rating and review. The overall count is set to 1.

    The function then adjusts the overall review based on the overall points. The review is set
    using the local_translation function with different keys based on the points range.

    Args:
        category (str): The category for the rating ('performance', 'accessibility', or other).
        local_translation (function): Function to get the localized text.
        score (float): The score to be converted to a 1-5 grading.
        rating (Rating): The Rating object to be updated.
        review (str): The initial review text.

    """
    # change it to % and convert it to a 1-5 grading
    points = 5.0 * float(score)

    if category == 'performance':
        rating.set_overall(points)
        rating.set_performance(points)
        rating.performance_review = review
    elif category == 'accessibility':
        rating.set_overall(points)
        rating.set_a11y(points)
        rating.a11y_review = review
    else:
        rating.set_overall(points)
        rating.overall_review = review
    rating.overall_count = 1

    review = rating.overall_review
    points = rating.get_overall()
    if points >= 5.0:
        review = local_translation("TEXT_REVIEW_VERY_GOOD")
    elif points >= 4.0:
        review = local_translation("TEXT_REVIEW_IS_GOOD")
    elif points >= 3.0:
        review = local_translation("TEXT_REVIEW_IS_OK")
    elif points > 1.0:
        review = local_translation("TEXT_REVIEW_IS_BAD")
    elif points <= 1.0:
        review = local_translation("TEXT_REVIEW_IS_VERY_BAD")
    rating.overall_review = review

def create_weight_dict(category, json_content):
    """
    Creates a dictionary of weights for each audit in a specific category.

    This function iterates over the 'auditRefs' field of a specific category in a JSON object,
    and creates a dictionary where the keys are the audit IDs and the values are the audit weights.

    Parameters:
    category (str): The category of audits to include in the dictionary.
    json_content (dict): The JSON object that contains the audit data.

    Returns:
    dict: A dictionary where the keys are audit IDs and the values are audit weights.
    """
    weight_dict = {}
    for item in json_content['categories'][category]['auditRefs']:
        weight_dict[item['id']] = item['weight']
    return weight_dict


def str_to_json(content, url):
    """
    Converts a string to a JSON object.

    This function attempts to load a string into a JSON object.
    If the string contains a 'lighthouseResult'
    field, it extracts this field into the JSON object.
    If the string cannot be loaded into a JSON object,
    it prints an error message and returns an empty JSON object.

    Parameters:
    content (str): The string to convert to a JSON object.
    url (str): The URL associated with the content.
               This is used in the error message if the content cannot
               be loaded into a JSON object.

    Returns:
    dict: The JSON object loaded from the string,
          or an empty JSON object if the string cannot be loaded.
    """
    json_content = {}

    try:
        json_content = json.loads(content)
        if 'lighthouseResult' in json_content:
            json_content = json_content['lighthouseResult']

    except json.JSONDecodeError:
        # might crash if checked resource is not a webpage
        print(
            (
                "Error! Failed to decode JSON for: content:\r\n"
                f"\turl: {url}\r\n"
                f"\tcontent: {content}\r\n"
                )
            )

    return json_content

def get_json_result_from_api(lang_code, url, category, google_pagespeed_apikey):
    """
    Retrieves the JSON result of a Lighthouse audit for
    a specific URL using the Google Pagespeed API.

    This function sends a request to the Google Pagespeed API to
    perform the audit and returns the JSON result.

    Parameters:
    lang_code (str): The locale to use for the audit.
    url (str): The URL to audit.
    category (str): The category of audits to perform
        (e.g., 'performance' or 'accessibility').
    google_pagespeed_apikey (str): The API key for the Google Pagespeed API.

    Returns:
    dict: The JSON result of the audit.
    """
    pagespeed_api_request = (
        'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
        f'?locale={lang_code}'
        f'&category={category}'
        f'&url={url}'
        f'&key={google_pagespeed_apikey}')
    get_content = ''

    get_content = get_http_content(pagespeed_api_request)
    json_content = str_to_json(get_content, url)
    return json_content

def get_json_result_using_caching(lang_code, url, strategy):
    """
    Retrieves the JSON result of a Lighthouse audit for a URL using caching.

    This function uses a local Lighthouse CLI to perform the audit. If a cached result
    exists and is not older than the defined cache time delta, it will be used instead
    of performing a new audit.

    Parameters:
    lang_code (str): The locale to use for the audit.
    url (str): The URL to audit.
    strategy (str): The form factor to use for the audit (e.g., 'mobile' or 'desktop').

    Returns:
    dict: The JSON result of the audit, either from the cache or a new audit.
    """
    cache_key_rule = 'lighthouse-{0}'
    cache_path = get_cache_path_for_rule(url, cache_key_rule)

    if not os.path.exists(cache_path):
        os.makedirs(cache_path)

    result_file = os.path.join(cache_path, 'result.json')
    command = (
        f"node node_modules{os.path.sep}lighthouse{os.path.sep}cli{os.path.sep}index.js"
        f" --output json --output-path {result_file} --locale {lang_code}"
        f" --form-factor {strategy} --chrome-flags=\"--headless\" --quiet")

    artifacts_file = os.path.join(cache_path, 'artifacts.json')
    if os.path.exists(result_file) and \
        not is_file_older_than(result_file, CACHE_TIME_DELTA):

        file_created_timestamp = os.path.getctime(result_file)
        file_created_date = time.ctime(file_created_timestamp)
        print((f'Cached entry found from {file_created_date},'
            ' using it instead of calling website again.'))
        with open(result_file, 'r', encoding='utf-8', newline='') as file:
            return str_to_json('\n'.join(file.readlines()), url)
    elif os.path.exists(artifacts_file) and \
        not is_file_older_than(artifacts_file, CACHE_TIME_DELTA):

        file_created_timestamp = os.path.getctime(artifacts_file)
        file_created_date = time.ctime(file_created_timestamp)
        print((
            f'Cached entry found from {file_created_date},'
            ' using it instead of calling website again.'))
        command += f" -A={cache_path}"
    else:
        command += f" -GA={cache_path} {url}"

    with subprocess.Popen(command.split(), stdout=subprocess.PIPE) as process:
        _, _ = process.communicate(timeout=REQUEST_TIMEOUT * 10)
        with open(result_file, 'r', encoding='utf-8', newline='') as file:
            return str_to_json('\n'.join(file.readlines()), url)



def get_json_result(lang_code, url, strategy, category, google_pagespeed_apikey):
    """
    Retrieves the JSON result of a Lighthouse audit for a specific URL.
    This function uses either the Google Pagespeed API or
    a local Lighthouse CLI to perform the audit,
    depending on whether a valid API key is provided.
    If caching is enabled, it will attempt to retrieve
    the result from the cache before performing a new audit.

    Parameters:
    lang_code (str): The locale to use for the audit.
    url (str): The URL to audit.
    strategy (str):
        The form factor to use for the audit (e.g., 'mobile' or 'desktop').
    category (str):
        The category of audits to perform (e.g., 'performance' or 'accessibility').
    google_pagespeed_apikey (str):
        The API key for the Google Pagespeed API. If this is None or an empty string,
        the function will use the local Lighthouse CLI to perform the audit.

    Returns:
    dict: The JSON result of the audit.
    """
    json_content = {}
    check_url = url.strip()

    lighthouse_use_api = google_pagespeed_apikey is not None and google_pagespeed_apikey != ''

    if lighthouse_use_api:
        return get_json_result_from_api(lang_code, check_url, category, google_pagespeed_apikey)

    if USE_CACHE:
        return get_json_result_using_caching(lang_code, check_url, strategy)

    command = (
        f"node node_modules{os.path.sep}lighthouse{os.path.sep}cli{os.path.sep}index.js"
        f" {check_url} --output json --output-path stdout --locale {lang_code}"
        f" --only-categories {category} --form-factor {strategy}"
        " --chrome-flags=\"--headless\" --quiet")

    with subprocess.Popen(command.split(), stdout=subprocess.PIPE) as process:
        output, _ = process.communicate(timeout=REQUEST_TIMEOUT * 10)
        get_content = output
        json_content = str_to_json(get_content, check_url)

    return json_content
