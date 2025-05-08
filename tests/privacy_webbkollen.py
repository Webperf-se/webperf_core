# -*- coding: utf-8 -*-
from datetime import datetime
import time
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import re
import requests
import json
from bs4 import BeautifulSoup
from helpers.models import Rating
from tests.utils import get_translation
from helpers.setting_helper import get_config

# DEFAULTS
REGEX_ALLOWED_CHARS = r"[^\u00E5\u00E4\u00F6\u00C5\u00C4\u00D6a-zA-Zå-öÅ-Ö 0-9\-:\/]+"

def run_test(global_translation, url):
    """
    This function runs a webbkollen (privacy) test on a given URL and
    returns a rating and a dictionary.

    The test involves fetching the HTML content of the URL, parsing it,
    and rating the results based on certain criteria.
    The rating and review are determined by the integrity and
    security points obtained from the test results.

    Parameters:
    global_translation (function): A function to translate text to a global language.
    url (str): The URL to be tested.

    Returns:
    tuple: A tuple containing the rating object and a dictionary.
    The rating object contains the overall rating, review, and integrity and security points.
    The dictionary is currently empty but can be used to return additional data if needed.
    """
    review = ''
    return_dict = {}
    rating = Rating(global_translation, get_config('general.review.improve-only'))

    local_translation = get_translation('privacy_webbkollen', get_config('general.language'))

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # Get result from webbkollen website
    html_content = get_html_content(url, get_config('general.language'), local_translation)
    soup2 = BeautifulSoup(html_content, 'html.parser')

    results = soup2.find_all(class_="result")
    result_title = soup2.find(id="results-title")
    if not result_title:
        error_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        error_rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (error_rating, {'failed': True })

    for result in results:
        rating += rate_result(result, global_translation, local_translation, return_dict)

    points = rating.get_integrity_and_security()
    if points >= 5:
        review = local_translation('TEXT_REVIEW_VERY_GOOD') + review
    elif points >= 4:
        review = local_translation('TEXT_REVIEW_IS_GOOD') + review
    elif points >= 3:
        review = local_translation('TEXT_REVIEW_IS_OK') + review
    elif points >= 2:
        review = local_translation('TEXT_REVIEW_IS_BAD') + review
    elif points >= 1:
        review = local_translation('TEXT_REVIEW_IS_VERY_BAD') + review
    else:
        review = local_translation('TEXT_REVIEW_IS_VERY_BAD') + review
        points = 1.0

    # give us result date (for when 5july.net generated report)
    extend_review_with_date_for_last_run(review, local_translation, result_title)

    rating.set_overall(points)
    rating.overall_review = review

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    reviews = rating.get_reviews()
    print(global_translation('TEXT_SITE_RATING'), rating)
    if get_config('general.review.show'):
        print(
            global_translation('TEXT_SITE_REVIEW'),
            reviews)

    if get_config('general.review.data'):
        nice_json_data = json.dumps(return_dict, indent=3)
        print(
            global_translation('TEXT_SITE_REVIEW_DATA'),
            f'```json\r\n{nice_json_data}\r\n```')

    return (rating, return_dict)

def extend_review_with_date_for_last_run(review, local_translation, result_title):
    """
    Extends the review with the date of the last run.

    Args:
        review (str): The review to be extended.
        local_translation (function): A function that translates text to the local language.
        result_title (bs4.element.Tag): The title of the result.

    Returns:
        str: The extended review.
    """
    result_title_beta = result_title.find_all('div', class_="beta")
    if len(result_title_beta) > 0:
        for header_info in result_title_beta[0].strings:
            info = re.sub(REGEX_ALLOWED_CHARS, '',
                          header_info, 0, re.MULTILINE).strip()
            if info.startswith('20'):
                review += local_translation('TEXT_REVIEW_GENERATED').format(info)

def get_html_content(orginal_url, lang_code, local_translation):
    """
    Retrieves test result as HTML content from webbkollen website by 5July.

    Args:
        orginal_url (str): The URL of the webpage to be retrieved.
        lang_code (str): The language code for the webpage.
        local_translation (function): A function that translates text to the local language.

    Returns:
        str: Test result as HTML content.

    """
    html_content = ''
    headers = {
        'user-agent': 'Mozilla/5.0 (compatible; Webperf; +https://webperf.se)'}

    has_refresh_statement = True
    had_refresh_statement = False
    session = requests.Session()
    while has_refresh_statement:
        has_refresh_statement = False
        request = session.get(
            (f'https://webbkoll.5july.net/{lang_code}'
             f'/check?url={urllib.parse.quote(orginal_url)}'),
            allow_redirects=True,
            headers=headers,
            timeout=get_config('general.request.timeout'))

        if f'type="search" value="{orginal_url}">' in request.text:
            # headers[''] = ''
            regex = r"_csrf_token[^>]*value=\"(?P<csrf>[^\"]+)\""
            matches = re.finditer(regex, request.text, re.MULTILINE)
            csrf_value = ''
            for _, match in enumerate(matches, start=1):
                csrf_value = match.group('csrf')

            data = {
                '_csrf_token': csrf_value,
                'url': orginal_url,
                'submit': ''}
            service_url = f'https://webbkoll.5july.net/{lang_code}/check'
            request = session.post(service_url, allow_redirects=True,
                                   headers=headers,
                                   timeout=get_config('general.request.timeout'),
                                   data=data)
            html_content = request.text

        if '<meta http-equiv="refresh"' in html_content:
            has_refresh_statement = True
            had_refresh_statement = True
            print(local_translation('TEXT_RESULT_NOT_READY').format(
                max(get_config('tests.webbkoll.sleep'), 5)))
            time.sleep(max(get_config('tests.webbkoll.sleep'), 5))

    if not had_refresh_statement:
        time.sleep(max(get_config('tests.webbkoll.sleep'), 5))
    return html_content

def rate_result(result, global_translation, local_translation, return_dict):# pylint: disable=too-many-locals
    """
    Rates is calculated by the number of:
    successes, alerts, warnings, sub-alerts, and sub-warnings in the result.
    Based on these numbers, it calculates the points to remove from the current result.
    It also gathers more information from the result.
    Finally, it creates a review using the `create_review` function and
    sets the integrity and security of the `heading_rating` using the calculated points and
    the created review.

    Args:
        result (bs4.element.Tag): The result to be rated.
        global_translation (function): A function that translates text to a global language.
        local_translation (function): A function that translates text to the local language.

    Returns:
        Rating: The rating of the result.

    """
    heading_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))

    points_to_remove_for_current_result = 0.0

    header = result.find("h3")

    if header.get('id') in ('what', 'raw-headers', 'server-location', 'localstorage', 'requests'):
        return heading_rating

    number_of_success = len(header.find_all("span", class_="success"))

    # - alert
    number_of_alerts = len(header.find_all("span", class_="alert"))
    points_to_remove_for_current_result += (number_of_alerts * 5.0)

    # - warning
    number_of_warnings = len(header.find_all("span", class_="warning"))
    points_to_remove_for_current_result += (number_of_warnings * 2.5)

    number_of_sub_alerts = 0
    number_of_sub_warnings = 0
    divs = result.find_all("div")

    more_info = ''
    if len(divs) > 0:
        div = divs[0]
        # -- alert
        number_of_sub_alerts = len(div.find_all("span", class_="alert"))
        points_to_remove_for_current_result += (
            number_of_sub_alerts * 0.5)
        # -- warning
        number_of_sub_warnings = len(
            div.find_all("span", class_="warning"))
        points_to_remove_for_current_result += (
            number_of_sub_warnings * 0.25)

    paragraphs = result.find_all("p")
    if len(paragraphs) > 0:
        for paragraph_text in paragraphs[0].strings:
            more_info += re.sub(REGEX_ALLOWED_CHARS, '',
                                paragraph_text, 0, re.MULTILINE) + " "
    else:
        more_info = "!" + re.sub(REGEX_ALLOWED_CHARS, '',
                                result.text, 0, re.MULTILINE)
    more_info = more_info.replace("  ", " ").strip()

    points_for_current_result = 5.0

    # only try to remove points if we have more then one
    if points_to_remove_for_current_result > 0.0:
        points_for_current_result -= points_to_remove_for_current_result

    points_for_current_result = max(points_for_current_result, 1.0)

    # add review info
    review = create_review(local_translation,
                                    header,
                                    number_of_success,
                                    number_of_alerts,
                                    number_of_warnings,
                                    number_of_sub_alerts,
                                    number_of_sub_warnings,
                                    more_info)

    header_key = re.sub(REGEX_ALLOWED_CHARS, '',
                                    header.text, 0, re.MULTILINE).strip()

    return_dict[header_key] = {
        "number_of_success": number_of_success,
        "number_of_alerts": number_of_alerts,
        "number_of_warnings": number_of_warnings,
        "number_of_sub_alerts": number_of_sub_alerts,
        "number_of_sub_warnings": number_of_sub_warnings,
        "more_info": more_info
    }

    heading_rating.set_integrity_and_security(
        points_for_current_result, review)
    return heading_rating

def create_review(local_translation, header, # pylint: disable=too-many-arguments
                  number_of_success, number_of_alerts, number_of_warnings,
                  number_of_sub_alerts, number_of_sub_warnings, more_info):
    """
    Creates a review.
    The review is created based on the number of:
    successes, alerts, warnings, sub-alerts, and sub-warnings.
    The review text is translated to the local language using the `local_translation` function.

    Args:
        local_translation (function): A function that translates text to the local language.
        header (str): The header text of the review.
        number_of_success (int): The number of successful operations.
        number_of_alerts (int): The number of alerts generated.
        number_of_warnings (int): The number of warnings generated.
        number_of_sub_alerts (int): The number of sub-alerts generated.
        number_of_sub_warnings (int): The number of sub-warnings generated.
        more_info (str): Additional information to be added to the review.

    Returns:
        str: The review text.
    """
    review = '- ' + re.sub(REGEX_ALLOWED_CHARS, '',
                                    header.text, 0, re.MULTILINE).strip()

    if number_of_success > 0 and number_of_sub_alerts == 0 and number_of_sub_warnings == 0:
        review += local_translation('TEXT_REVIEW_CATEGORY_VERY_GOOD')
    elif number_of_alerts > 0:
        review += local_translation('TEXT_REVIEW_CATEGORY_IS_VERY_BAD').format(
            0)
    elif number_of_warnings > 0:
        review += local_translation('TEXT_REVIEW_CATEGORY_IS_BAD').format(
            0)
    elif number_of_sub_alerts > 0 and number_of_sub_warnings > 0:
        review += local_translation('TEXT_REVIEW_CATEGORY_IS_OK').format(
            number_of_sub_alerts, number_of_sub_warnings, 0)
    elif number_of_sub_alerts > 0:
        review += local_translation('TEXT_REVIEW_CATEGORY_IS_OK').format(
            number_of_sub_alerts, number_of_sub_warnings, 0)
    elif number_of_sub_warnings > 0:
        review += local_translation('TEXT_REVIEW_CATEGORY_IS_GOOD').format(
            number_of_sub_warnings, 0)
    elif header.get('id') in ('headers', 'cookies'):
        review += local_translation('TEXT_REVIEW_CATEGORY_VERY_GOOD')
    else:
        review += ": " + more_info
    return review
