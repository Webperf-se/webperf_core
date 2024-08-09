# -*- coding: utf-8 -*-
import json
import os
from urllib.parse import ParseResult, urlunparse
from datetime import datetime
import urllib  # https://docs.python.org/3/library/urllib.parse.html
from bs4 import BeautifulSoup
from models import Rating
from tests.utils import get_guid,\
    get_http_content, get_translation
from tests.sitespeed_base import get_result
from helpers.setting_helper import get_config

def change_url_to_404_url(url):
    """
    This function modifies the given URL to simulate a 404 error page by appending a unique path.
    It ensures that the total length of the new path does not exceed 200 characters.

    Parameters:
    url (str): The original URL to be modified.

    Returns:
    url2 (str): The modified URL simulating a 404 error page.
    """
    o = urllib.parse.urlparse(url)

    path = f'{get_guid(5)}/finns-det-en-sida/pa-den-har-adressen/testanrop/'
    if len(o.path) + len(path) < 200:
        if o.path.endswith('/'):
            path = f'{o.path}{path}'
        else:
            path = f'{o.path}/{path}'

    o2 = ParseResult(
        scheme=o.scheme,
        netloc=o.netloc,
        path=path,
        params=o.params,
        query=o.query,
        fragment=o.fragment)
    url2 = urlunparse(o2)
    return url2

def get_http_content_with_status(url):
    """
    Retrieves HTTP content from the specified URL and returns the content along with its status.

    Args:
        url (str): The URL to fetch content from.

    Returns:
        tuple or None: A tuple containing the HTML content (as a string) and the HTTP status code.
            If no content is available or an error occurs, returns None.
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
    if not ('nt' in os.name or 'Darwin' in os.uname().sysname):
        sitespeed_arg += ' --xvfb'

    sitespeed_arg += ' --postScript chrome-cookies.cjs --postScript chrome-versions.cjs'

    (_, filename) = get_result(
        url,
        get_config('tests.sitespeed.docker.use'),
        sitespeed_arg,
        get_config('tests.sitespeed.timeout'))

    data = identify_files(filename)

    if data is None:
        return None, None

    if 'htmls' not in data:
        return None, None

    if len(data['htmls']) == 0:
        return None, None

    return data['htmls'][0]['content'], data['htmls'][0]['status']

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
        'htmls': []
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
            if 'status' not in res:
                continue

            if 'html' in res['content']['mimeType']:
                data['htmls'].append({
                    'url': req_url,
                    'content': res['content']['text'],
                    'status': res['status'],
                    'index': req_index
                    })
            req_index += 1

    return data

def run_test(global_translation, org_url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    rating = Rating(global_translation)
    result_dict = {}

    local_translation = get_translation('page_not_found', get_config('general.language'))

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    url = change_url_to_404_url(org_url)

    # checks http status code and content for url
    request_text, code = get_http_content_with_status(url)

    # Error, was unable to load the page you requested.
    if code is None and (request_text is None or request_text == ''):
        # very if we can connect to orginal url,
        # if not there is a bigger problem, geo block for example
        request_text2, code2 = get_http_content_with_status(org_url)
        if code2 is None and (request_text2 is None or request_text2 == ''):
            rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
            return (rating, result_dict)

    if code is None:
        code = 'unknown'

    rating += rate_response_status_code(global_translation, local_translation, code)

    result_dict['status_code'] = code

    # We use variable to validate it once
    has_request_text = False

    if request_text != '':
        has_request_text = True

    if has_request_text:
        soup = BeautifulSoup(request_text, 'lxml')
        rating += rate_response_title(global_translation, result_dict, local_translation, soup)

        rating += rate_response_header1(global_translation, result_dict, local_translation, soup)

        rating += rate_correct_language_text(soup, request_text, org_url,
                                    global_translation, local_translation)

    # hur långt är inehållet
    rating_text_is_150_or_more = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    soup = BeautifulSoup(request_text, 'html.parser')
    if len(soup.get_text()) > 150:
        rating_text_is_150_or_more.set_overall(
            5.0, local_translation('TEXT_REVIEW_ERROR_MSG_UNDER_150'))
        rating_text_is_150_or_more.set_a11y(
            5.0, local_translation('TEXT_REVIEW_ERROR_MSG_UNDER_150'))
    else:
        # '* Information är under 150 tecken, vilket tyder på att användaren inte vägleds vidare.\n'
        rating_text_is_150_or_more.set_overall(
            1.0, local_translation('TEXT_REVIEW_ERROR_MSG_UNDER_150'))
        rating_text_is_150_or_more.set_a11y(
            1.0, local_translation('TEXT_REVIEW_ERROR_MSG_UNDER_150'))
    rating += rating_text_is_150_or_more

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)

def rate_correct_language_text(soup, request_text, org_url, global_translation, local_translation):
    """
    This function checks if the language of the text on a webpage matches the
    expected language ('sv' for Swedish).
    It rates the text based on whether it matches certain strings associated with a 404 error
    in the expected language.
    The function returns a Rating object with overall and accessibility scores set based on
    the language match.

    Parameters:
    soup (BeautifulSoup object): Parsed webpage content.
    request_text (str): Text from the webpage.
    org_url (str): Original URL of the webpage.
    global_translation (function): Function to translate text globally.
    local_translation (function): Function to translate text locally.

    Returns:
    rating_swedish_text (Rating object): Rating object with overall and accessibility scores.
    """
    found_match = False
    # kollar innehållet
    page_lang = get_supported_lang_code_or_default(soup)
    if page_lang != 'sv':
        content_rootpage = get_http_content(
            org_url, allow_redirects=True)
        soup_rootpage = BeautifulSoup(content_rootpage, 'lxml')
        rootpage_lang = get_supported_lang_code_or_default(
            soup_rootpage)
        if rootpage_lang != page_lang:
            page_lang = 'sv'

    four_o_four_strings = get_404_texts(page_lang)

    text_from_page = request_text.lower()

    for item in four_o_four_strings:
        if item in text_from_page:
            found_match = True
            break

    rating_swedish_text = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if found_match:
        rating_swedish_text.set_overall(
            5.0, local_translation('TEXT_REVIEW_NO_SWEDISH_ERROR_MSG'))
        rating_swedish_text.set_a11y(5.0, local_translation(
            'TEXT_REVIEW_NO_SWEDISH_ERROR_MSG'))
    else:
        rating_swedish_text.set_overall(
            1.0, local_translation('TEXT_REVIEW_NO_SWEDISH_ERROR_MSG'))
        rating_swedish_text.set_a11y(
            1.0, local_translation('TEXT_REVIEW_NO_SWEDISH_ERROR_MSG'))
    return rating_swedish_text

def rate_response_header1(global_translation, result_dict, local_translation, soup):
    """
    Rates the response header (h1). If an h1 is found in the HTML soup,
    it sets the overall, standards, and a11y ratings to 5.0. Otherwise, it sets them to 1.0.
    """
    rating_h1 = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    h1 = soup.find('h1')
    if h1:
        result_dict['h1'] = h1.string
        rating_h1.set_overall(5.0, local_translation('TEXT_REVIEW_MAIN_HEADER'))
        rating_h1.set_standards(5.0, local_translation('TEXT_REVIEW_MAIN_HEADER'))
        rating_h1.set_a11y(5.0, local_translation('TEXT_REVIEW_MAIN_HEADER'))
    else:
        rating_h1.set_overall(1.0, local_translation('TEXT_REVIEW_MAIN_HEADER'))
        rating_h1.set_standards(1.0, local_translation('TEXT_REVIEW_MAIN_HEADER'))
        rating_h1.set_a11y(1.0, local_translation('TEXT_REVIEW_MAIN_HEADER'))
    return rating_h1


def rate_response_title(global_translation, result_dict, local_translation, soup):
    """
    Rates the response title. If a title is found in the HTML soup,
    it sets the overall, standards, and a11y ratings to 5.0. Otherwise, it sets them to 1.0.
    """
    rating_title = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    title = soup.find('title')
    if title:
        result_dict['page_title'] = title.string
        rating_title.set_overall(5.0, local_translation('TEXT_REVIEW_NO_TITLE'))
        rating_title.set_standards(5.0, local_translation('TEXT_REVIEW_NO_TITLE'))
        rating_title.set_a11y(5.0, local_translation('TEXT_REVIEW_NO_TITLE'))
    else:
        rating_title.set_overall(1.0, local_translation('TEXT_REVIEW_NO_TITLE'))
        rating_title.set_standards(1.0, local_translation('TEXT_REVIEW_NO_TITLE'))
        rating_title.set_a11y(1.0, local_translation('TEXT_REVIEW_NO_TITLE'))
    return rating_title


def rate_response_status_code(global_translation, local_translation, code):
    """
    Rates the response status code. If the code is 404,
    it sets the overall and standards rating to 5.0. Otherwise, it sets them to 1.0.
    """
    rating_404 = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if code == 404:
        rating_404.set_overall(5.0, local_translation(
            'TEXT_REVIEW_WRONG_STATUS_CODE').format(code))
        rating_404.set_standards(5.0, local_translation(
            'TEXT_REVIEW_WRONG_STATUS_CODE').format(code))
    else:
        rating_404.set_overall(
            1.0, local_translation('TEXT_REVIEW_WRONG_STATUS_CODE').format(code))
        rating_404.set_standards(
            1.0, local_translation('TEXT_REVIEW_WRONG_STATUS_CODE').format(code))

    return rating_404


def get_supported_lang_code_or_default(soup):
    """
    Returns the language code ('sv' or 'en') from the HTML soup if present,
    otherwise defaults to 'sv'.
    """
    html = soup.find('html')
    if html and html.has_attr('lang'):
        lang_code = html.get('lang')
        if 'sv' in lang_code:
            return 'sv'
        if 'en' in lang_code:
            return 'en'
    return 'sv'


def get_404_texts(lang_code):
    """
    Returns a list of Swedish or English phrases commonly used in 404 error messages.
    """
    if 'en' in lang_code:
        return get_404_texts_in_english()
    return get_404_texts_in_swedish()


def get_404_texts_in_english():
    """
    Returns a list of English phrases commonly used in 404 error messages.
    """
    four_o_four_strings = [
        # Saknas
        'missing',

        # finns inte
        "doesn't exist",
        "does not exist",

        # inga resultat
        'no results',

        # inte hittas
        'be found',

        # inte hitta
        'found',

        # kunde inte
        "couldn't",
        'could not',

        # kunde ej
        # 'kunde ej',

        # hittades inte
        "couldn't be found",
        'could not be found',

        # hittar inte
        "can't find",
        'can not find',

        # hittade vi inte
        "we couldn't find",
        'we could not find',

        # hittar vi inte
        "we can't find",
        'we can not find',

        # hittades tyvärr inte
        "unfortunately, couldn't find",
        'unfortunately, could not find',

        # tagits bort
        'been removed',

        # fel adress
        'wrong address',

        # trasig
        'broken',

        # inte hitta
        'not find',

        # ej hitta
        'not found',

        # ingen sida
        'no page',

        # borttagen
        'removed',

        # flyttad
        'moved',

        # inga resultat
        'no results',

        # inte tillgänglig
        'not available',

        # inte sidan
        'not the page',

        # kontrollera adressen
        'check the address',
        'check the link',
        'check the URL',

        # kommit utanför
        'left',

        # gick fel
        'went wrong',

        # blev något fel
        'something went wrong',

        # kan inte nås
        "can't be reached",
        'can not be reached',

        # gammal sida
        'old page',

        # hoppsan
        'ops',

        # finns inte
        "doesn't exist",
        'does not exist',

        # finns ej
        "doesn't exist",
        'does not exist',

        # byggt om
        'rebuilt',

        # inte finns
        "doesn't exist",
        'does not exist',

        # inte fungera
        "doesn't work",
        'does not work',

        # ursäkta
        'sorry',

        # uppstått ett fel
        'a problem has been encountered',
        'an issue has been encountered',

        # gick fel
        'went wrong'
    ]
    return four_o_four_strings


def get_404_texts_in_swedish():
    """
    Returns a list of Swedish phrases commonly used in 404 error messages.
    """
    four_o_four_strings = [
        'saknas',
        'finns inte',
        'inga resultat',
        'inte hittas',
        'inte hitta',
        'kunde inte',
        'kunde ej',
        'hittades inte',
        'hittar inte',
        'hittade vi inte',
        'hittar vi inte',
        'hittades tyvärr inte',
        'tagits bort',
        'fel adress',
        'trasig',
        'inte hitta',
        'ej hitta',
        'ingen sida',
        'borttagen',
        'flyttad',
        'inga resultat',
        'inte tillgänglig',
        'inte sidan',
        'kontrollera adressen',
        'kommit utanför',
        'gick fel',
        'blev något fel',
        'kan inte nås',
        'gammal sida',
        'hoppsan',
        'finns inte',
        'finns ej',
        'byggt om',
        'inte finns',
        'inte fungera',
        'ursäkta',
        'uppstått ett fel',
        'gick fel'
    ]
    return four_o_four_strings
