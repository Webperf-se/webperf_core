# -*- coding: utf-8 -*-
import json
import os
import urllib
from urllib.parse import ParseResult, urlparse, urlunparse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import uuid
from helpers.models import Rating
from tests.utils import get_guid,\
    get_http_content, get_translation, is_file_older_than,\
    change_url_to_test_url
from tests.sitespeed_base import get_result, get_result_using_no_cache
from helpers.setting_helper import get_config, set_runtime_config_only

def get_webperf_json(filename):
    if not os.path.exists(filename):
        return None

    with open(filename, encoding='utf-8') as json_input_file:
        har_data = json.load(json_input_file)
        return har_data

def get_knowledge_data(url):
    folder = 'tmp'
    if get_config('general.cache.use'):
        folder = get_config('general.cache.folder')

    o = urlparse(url)
    hostname = o.hostname

    knowledge_folder_name = os.path.join(folder, hostname)

    data = None
    if os.path.exists(knowledge_folder_name):
        files_or_folders = os.listdir(knowledge_folder_name)
        for file_or_folder in files_or_folders:
            if not file_or_folder.endswith('webperf-core.json'):
                continue
            filename = os.path.join(knowledge_folder_name, file_or_folder)
            if is_file_older_than(filename, timedelta(minutes=get_config('general.cache.max-age'))):
                continue

            data = get_webperf_json(filename)
    if data is None:
        data = create_webperf_json(url)

    if data is None:
        return None
    if 'page-not-found' not in data:
        return None
    data = data['page-not-found']
    if 'knowledgeData' not in data:
        return None
    data = data['knowledgeData']
    return data

def create_webperf_json(url):
    # We don't need extra iterations for what we are using it for
    sitespeed_iterations = 1
    sitespeed_arg = (
            '--shm-size=1g -b chrome '
            '--plugins.add plugin-pagenotfound '
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

    if get_config('tests.page-not-found.override-url'):
        sitespeed_arg += ' --plugin-pagenotfound.override-url=true'

    (folder, _) = get_result(url,
        get_config('tests.sitespeed.docker.use'),
        sitespeed_arg,
        get_config('tests.sitespeed.timeout'))

    filename =  os.path.join(folder, 'webperf-core.json')
    data = get_webperf_json(filename)
    if data is not None:
        return data

    test_url = change_url_to_test_url(url, '404')
    (folder, _) = get_result(test_url,
        get_config('tests.sitespeed.docker.use'),
        sitespeed_arg,
        get_config('tests.sitespeed.timeout'))

    filename =  os.path.join(folder, 'webperf-core.json')
    return get_webperf_json(filename)

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

    result_dict = get_knowledge_data(org_url)
    nice_data = json.dumps(result_dict, indent=3)
    print('A', nice_data)
    # TODO: Handle where result_dict is None
    # TODO: Handle when unable to access website

    rating += rate_response_status_code(global_translation, local_translation, result_dict)

    rating += rate_response_title(global_translation, result_dict, local_translation)

    rating += rate_response_header1(global_translation, result_dict, local_translation)

    rating += rate_correct_language_text(result_dict,
        global_translation, local_translation)

    # hur långt är inehållet
    rating_text_is_150_or_more = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if 'body-text' in result_dict and len(result_dict['body-text']) > 150:
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

    rating_other_404s = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    nof_other_404_responses = 0
    if 'other-404-responses' in result_dict:
        nof_other_404_responses = len(result_dict['other-404-responses'])

    if nof_other_404_responses == 0:
        rating_other_404s.set_overall(
            5.0, local_translation('TEXT_REVIEW_ERROR_MSG_NO_UNEXPECTED_404'))
        rating_other_404s.set_standards(
            5.0, local_translation('TEXT_REVIEW_ERROR_MSG_NO_UNEXPECTED_404'))
    else:
        rating_other_404s.set_overall(
            1.0, local_translation('TEXT_REVIEW_ERROR_MSG_UNEXPECTED_404').format(nof_other_404_responses))
        rating_other_404s.set_standards(
            1.0, local_translation('TEXT_REVIEW_ERROR_MSG_UNEXPECTED_404').format(nof_other_404_responses))
    rating += rating_other_404s


    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)

def rate_correct_language_text(result_dict, global_translation, local_translation):
    found_match = False
    # kollar innehållet
    if 'lang' in result_dict and 'body-text' in result_dict:
        four_o_four_strings = get_404_texts(result_dict['lang'])
        text_from_page = result_dict['body-text'].lower()

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

def rate_response_header1(global_translation, result_dict, local_translation):
    rating_h1 = Rating(
        global_translation,
        get_config('general.review.improve-only'))

    if 'h1' in result_dict and len(result_dict['h1']) > 1:
        rating_h1.set_overall(5.0, local_translation('TEXT_REVIEW_MAIN_HEADER'))
        rating_h1.set_standards(5.0, local_translation('TEXT_REVIEW_MAIN_HEADER'))
        rating_h1.set_a11y(5.0, local_translation('TEXT_REVIEW_MAIN_HEADER'))
    else:
        rating_h1.set_overall(1.0, local_translation('TEXT_REVIEW_MAIN_HEADER'))
        rating_h1.set_standards(1.0, local_translation('TEXT_REVIEW_MAIN_HEADER'))
        rating_h1.set_a11y(1.0, local_translation('TEXT_REVIEW_MAIN_HEADER'))
    return rating_h1

def rate_response_title(global_translation, result_dict, local_translation):
    rating_title = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if 'page-title' in result_dict and len(result_dict['page-title']) > 1:
        rating_title.set_overall(5.0, local_translation('TEXT_REVIEW_NO_TITLE'))
        rating_title.set_standards(5.0, local_translation('TEXT_REVIEW_NO_TITLE'))
        rating_title.set_a11y(5.0, local_translation('TEXT_REVIEW_NO_TITLE'))
    else:
        rating_title.set_overall(1.0, local_translation('TEXT_REVIEW_NO_TITLE'))
        rating_title.set_standards(1.0, local_translation('TEXT_REVIEW_NO_TITLE'))
        rating_title.set_a11y(1.0, local_translation('TEXT_REVIEW_NO_TITLE'))
    return rating_title

def rate_response_status_code(global_translation, local_translation, result_dict):
    """
    Rates the response status code. If the code is 404,
    it sets the overall and standards rating to 5.0. Otherwise, it sets them to 1.0.
    """
    code = 'unknown'
    if 'status-code' in result_dict:
        code = result_dict['status-code']
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
