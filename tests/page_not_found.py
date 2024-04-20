# -*- coding: utf-8 -*-
import ssl
import sys
from urllib.parse import ParseResult, urlunparse
from datetime import datetime
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import requests
from bs4 import BeautifulSoup
from models import Rating
from tests.utils import get_config_or_default, get_guid, get_http_content, get_translation

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')

def change_url_to_404_url(url):

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


def run_test(global_translation, lang_code, org_url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    rating = Rating(global_translation)
    result_dict = {}

    local_translation = get_translation('page_not_found', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    url = change_url_to_404_url(org_url)

    headers = {
        'user-agent': USERAGENT,
        'Accept': ('text/html,'
                   'application/xhtml+xml,'
                   'application/xml;q=0.9,'
                   'image/avif,'
                   'image/webp,'
                   '*/*;'
                   'q=0.8')
        }
    code = 'unknown'
    response = False
    # checks http status code
    try:
        response = requests.get(url, allow_redirects=True,
                               headers=headers, timeout=REQUEST_TIMEOUT)
        code = response.status_code
    except ssl.CertificateError as error:
        print(f'Info: Certificate error. {error.reason}')
    except requests.exceptions.SSLError as error:
        if 'http://' in url:  # trying the same URL over SSL/TLS
            print('Info: Trying SSL before giving up.')
            return get_http_content(url.replace('http://', 'https://'))
        print(f'Info: SSLError. {error}')
    except requests.exceptions.ConnectionError as error:
        if 'http://' in url:  # trying the same URL over SSL/TLS
            print('Connection error! Info: Trying SSL before giving up.')
            return get_http_content(url.replace('http://', 'https://'))
        print(
            'Connection error! Unfortunately the request for URL '
            f'"{url}" failed.\nMessage:\n{sys.exc_info()[0]}')
    except requests.exceptions.MissingSchema as error:
        print(
            'Connection error! Missing Schema for '
            f'"{url}"')
    except requests.exceptions.TooManyRedirects as error:
        print(
            'Connection error! Too many redirects for '
            f'"{url}"')
    except TimeoutError:
        print(
            'Error! Unfortunately the request for URL '
            f'"{url}" timed out.'
            f'The timeout is set to {REQUEST_TIMEOUT} seconds.\nMessage:\n{sys.exc_info()[0]}')
        code = 'unknown'
    rating += rate_response_status_code(global_translation, local_translation, code)

    result_dict['status_code'] = code

    # We use variable to validate it once
    request_text = ''
    has_request_text = False
    found_match = False

    if response is not False:
        if response.text:
            request_text = response.text
            has_request_text = True

    if has_request_text:
        soup = BeautifulSoup(request_text, 'lxml')
        rating += rate_response_title(global_translation, result_dict, local_translation, soup)

        rating += rate_response_header1(global_translation, result_dict, local_translation, soup)

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

        # print(four_o_four_strings)
        text_from_page = request_text.lower()

        # print(text_from_page)

        for item in four_o_four_strings:
            if item in text_from_page:
                #points += 1.5
                found_match = True
                break

    rating_swedish_text = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating += rating_swedish_text

    # hur långt är inehållet
    rating_text_is_150_or_more = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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


def rate_response_header1(global_translation, result_dict, local_translation, soup):
    rating_h1 = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating_title = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating_404 = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    html = soup.find('html')
    if html and html.has_attr('lang'):
        lang_code = html.get('lang')
        if 'sv' in lang_code:
            return 'sv'
        if 'en' in lang_code:
            return 'en'
    return 'sv'


def get_404_texts(lang_code):
    if 'en' in lang_code:
        return get_404_texts_in_english()
    return get_404_texts_in_swedish()


def get_404_texts_in_english():
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
