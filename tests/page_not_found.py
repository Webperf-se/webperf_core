# -*- coding: utf-8 -*-
from urllib.parse import ParseResult, urlunparse
import sys
from datetime import datetime
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import requests
from bs4 import BeautifulSoup
from models import Rating
from tests.utils import get_config_or_default, get_guid, get_http_content, get_translation

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
review_show_improvements_only = get_config_or_default('review_show_improvements_only')

def change_url_to_404_url(url):

    o = urllib.parse.urlparse(url)

    path = '{0}/finns-det-en-sida/pa-den-har-adressen/testanrop/'.format(get_guid(5))
    if len(o.path) + len(path) < 200:
        if o.path.endswith('/'):
            path = '{0}{1}'.format(o.path, path)
        else:
            path = '{0}/{1}'.format(o.path, path)

    o2 = ParseResult(scheme=o.scheme, netloc=o.netloc, path=path, params=o.params, query=o.query, fragment=o.fragment)
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

    headers = {'user-agent': USERAGENT,
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'}
    code = 'unknown'
    request = False
    # checks http status code
    try:
        request = requests.get(url, allow_redirects=True,
                               headers=headers, timeout=REQUEST_TIMEOUT)
        code = request.status_code
    except Exception:
        code = 'unknown'
    rating += rate_response_status_code(global_translation, local_translation, code)

    result_dict['status_code'] = code

    # We use variable to validate it once
    requestText = ''
    hasRequestText = False
    found_match = False

    if request != False:
        if request.text:
            requestText = request.text
            hasRequestText = True

    if hasRequestText:
        soup = BeautifulSoup(requestText, 'lxml')
        rating += rate_response_title(global_translation, result_dict, local_translation, soup)

        rating += rate_response_header1(global_translation, result_dict, local_translation, soup)

        # kollar innehållet
        page_lang = get_supported_lang_code_or_default(soup)
        if page_lang != 'sv':
            try:
                content_rootpage = get_http_content(
                    org_url, allow_redirects=True)
                soup_rootpage = BeautifulSoup(content_rootpage, 'lxml')
                rootpage_lang = get_supported_lang_code_or_default(
                    soup_rootpage)
                if rootpage_lang != page_lang:
                    page_lang = 'sv'
            except:
                page_lang = 'sv'
                print('Error getting page lang!\nMessage:\n{0}'.format(
                    sys.exc_info()[0]))

        four_o_four_strings = get_404_texts(page_lang)

        # print(four_o_four_strings)
        text_from_page = requestText.lower()

        # print(text_from_page)

        for item in four_o_four_strings:
            if item in text_from_page:
                #points += 1.5
                found_match = True
                break

    rating_swedish_text = Rating(global_translation, review_show_improvements_only)
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
    rating_text_is_150_or_more = Rating(global_translation, review_show_improvements_only)
    soup = BeautifulSoup(requestText, 'html.parser')
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
    rating_h1 = Rating(global_translation, review_show_improvements_only)
    try:
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

    except:
        print('Error getting H1!\nMessage:\n{0}'.format(sys.exc_info()[0]))
    return rating_h1


def rate_response_title(global_translation, result_dict, local_translation, soup):
    rating_title = Rating(global_translation, review_show_improvements_only)
    try:
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

    except:
        print('Error getting page title!\nMessage:\n{0}'.format(
            sys.exc_info()[0]))
        rating_title.set_overall(1.0, local_translation('TEXT_REVIEW_NO_TITLE'))
        rating_title.set_standards(1.0, local_translation('TEXT_REVIEW_NO_TITLE'))
        rating_title.set_a11y(1.0, local_translation('TEXT_REVIEW_NO_TITLE'))
    return rating_title


def rate_response_status_code(global_translation, local_translation, code):
    rating_404 = Rating(global_translation, review_show_improvements_only)
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
    try:
        html = soup.find('html')
        if html and html.has_attr('lang'):
            lang_code = html.get('lang')
            if 'sv' in lang_code:
                return 'sv'
            elif 'en' in lang_code:
                return 'en'
    except:
        print('Error getting page lang!\nMessage:\n{0}'.format(
            sys.exc_info()[0]))
    return 'sv'


def get_404_texts(lang_code):
    if 'en' in lang_code:
        return get_404_texts_in_english()
    else:
        return get_404_texts_in_swedish()


def get_404_texts_in_english():
    four_o_four_strings = []
    # Saknas
    four_o_four_strings.append('missing')

    # finns inte
    four_o_four_strings.append("doesn't exist")
    four_o_four_strings.append("does not exist")

    # inga resultat
    four_o_four_strings.append('no results')

    # inte hittas
    four_o_four_strings.append('be found')

    # inte hitta
    four_o_four_strings.append('found')

    # kunde inte
    four_o_four_strings.append("couldn't")
    four_o_four_strings.append('could not')

    # kunde ej
    # four_o_four_strings.append('kunde ej')

    # hittades inte
    four_o_four_strings.append("couldn't be found")
    four_o_four_strings.append('could not be found')

    # hittar inte
    four_o_four_strings.append("can't find")
    four_o_four_strings.append('can not find')

    # hittade vi inte
    four_o_four_strings.append("we couldn't find")
    four_o_four_strings.append('we could not find')

    # hittar vi inte
    four_o_four_strings.append("we can't find")
    four_o_four_strings.append('we can not find')

    # hittades tyvärr inte
    four_o_four_strings.append("unfortunately, couldn't find")
    four_o_four_strings.append('unfortunately, could not find')

    # tagits bort
    four_o_four_strings.append('been removed')

    # fel adress
    four_o_four_strings.append('wrong address')

    # trasig
    four_o_four_strings.append('broken')

    # inte hitta
    four_o_four_strings.append('not find')

    # ej hitta
    four_o_four_strings.append('not found')

    # ingen sida
    four_o_four_strings.append('no page')

    # borttagen
    four_o_four_strings.append('removed')

    # flyttad
    four_o_four_strings.append('moved')

    # inga resultat
    four_o_four_strings.append('no results')

    # inte tillgänglig
    four_o_four_strings.append('not available')

    # inte sidan
    four_o_four_strings.append('not the page')

    # kontrollera adressen
    four_o_four_strings.append('check the address')
    four_o_four_strings.append('check the link')
    four_o_four_strings.append('check the URL')

    # kommit utanför
    four_o_four_strings.append('left')

    # gick fel
    four_o_four_strings.append('went wrong')

    # blev något fel
    four_o_four_strings.append('something went wrong')

    # kan inte nås
    four_o_four_strings.append("can't be reached")
    four_o_four_strings.append('can not be reached')

    # gammal sida
    four_o_four_strings.append('old page')

    # hoppsan
    four_o_four_strings.append('ops')

    # finns inte
    four_o_four_strings.append("doesn't exist")
    four_o_four_strings.append('does not exist')

    # finns ej
    four_o_four_strings.append("doesn't exist")
    four_o_four_strings.append('does not exist')

    # byggt om
    four_o_four_strings.append('rebuilt')

    # inte finns
    four_o_four_strings.append("doesn't exist")
    four_o_four_strings.append('does not exist')

    # inte fungera
    four_o_four_strings.append("doesn't work")
    four_o_four_strings.append('does not work')

    # ursäkta
    four_o_four_strings.append('sorry')

    # uppstått ett fel
    four_o_four_strings.append('a problem has been encountered')
    four_o_four_strings.append('an issue has been encountered')

    # gick fel
    four_o_four_strings.append('went wrong')
    return four_o_four_strings


def get_404_texts_in_swedish():
    four_o_four_strings = []
    four_o_four_strings.append('saknas')
    four_o_four_strings.append('finns inte')
    four_o_four_strings.append('inga resultat')
    four_o_four_strings.append('inte hittas')
    four_o_four_strings.append('inte hitta')
    four_o_four_strings.append('kunde inte')
    four_o_four_strings.append('kunde ej')
    four_o_four_strings.append('hittades inte')
    four_o_four_strings.append('hittar inte')
    four_o_four_strings.append('hittade vi inte')
    four_o_four_strings.append('hittar vi inte')
    four_o_four_strings.append('hittades tyvärr inte')
    four_o_four_strings.append('tagits bort')
    four_o_four_strings.append('fel adress')
    four_o_four_strings.append('trasig')
    four_o_four_strings.append('inte hitta')
    four_o_four_strings.append('ej hitta')
    four_o_four_strings.append('ingen sida')
    four_o_four_strings.append('borttagen')
    four_o_four_strings.append('flyttad')
    four_o_four_strings.append('inga resultat')
    four_o_four_strings.append('inte tillgänglig')
    four_o_four_strings.append('inte sidan')
    four_o_four_strings.append('kontrollera adressen')
    four_o_four_strings.append('kommit utanför')
    four_o_four_strings.append('gick fel')
    four_o_four_strings.append('blev något fel')
    four_o_four_strings.append('kan inte nås')
    four_o_four_strings.append('gammal sida')
    four_o_four_strings.append('hoppsan')
    four_o_four_strings.append('finns inte')
    four_o_four_strings.append('finns ej')
    four_o_four_strings.append('byggt om')
    four_o_four_strings.append('inte finns')
    four_o_four_strings.append('inte fungera')
    four_o_four_strings.append('ursäkta')
    four_o_four_strings.append('uppstått ett fel')
    four_o_four_strings.append('gick fel')
    return four_o_four_strings
