# -*- coding: utf-8 -*-
import re
import datetime
import json
import os
import urllib.parse
from models import Rating
import config
from tests.sitespeed_base import get_result
from bs4 import BeautifulSoup
import gettext

from tests.utils import httpRequestGetContent
_ = gettext.gettext

review_show_improvements_only = config.review_show_improvements_only
sitespeed_use_docker = config.sitespeed_use_docker


def run_test(_, langCode, url):
    """

    """

    language = gettext.translation(
        'a11y_pa11y', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return_dict = {}
    rating = Rating(_, review_show_improvements_only)

    o = urllib.parse.urlparse(url)
    org_url_start = '{0}://{1}'.format(o.scheme,
                                       o.hostname)

    content = httpRequestGetContent(url, True)
    statement_urls = get_availability_statement_urls(content, org_url_start)

    about_urls = get_about_urls(content, org_url_start)

    if about_urls != None:
        tmp_urls = {}
        for about_url in about_urls.keys():
            if statement_urls != None:
                break
            print('about_url', about_url, about_urls[about_url])

            about_content = httpRequestGetContent(about_url, True)
            statement_urls = get_availability_statement_urls(
                about_content, url)
            if statement_urls == None:
                tmps = get_about_urls(about_content, url)
                for tmp in tmps.keys():
                    if tmp not in about_urls.keys():
                        print('-', tmp, tmps[tmp])
                        tmp_urls[tmp] = tmps[tmp]
            else:
                print('- STATEMENT')

        for about_url in tmp_urls.keys():
            if statement_urls != None:
                break
            # print('about_url2', about_url)

            about_content = httpRequestGetContent(about_url, True)
            statement_urls = get_availability_statement_urls(
                about_content, url)

    if statement_urls != None:
        # print('statement_url', statement_urls)
        for statement_url in statement_urls:
            rating += rate_statement(statement_url, _)
            # Should we test all found urls or just best match?
            break
    else:
        rating += rate_statement(statement_urls, _)

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)


def rate_statement(statement_url, _):
    # https://www.digg.se/kunskap-och-stod/digital-tillganglighet/skapa-en-tillganglighetsredogorelse
    rating = Rating(_, review_show_improvements_only)

    if statement_url != None:
        rating.set_overall(
            5.0, '- Tillgänglighetsredogörelse: {0}'.format(statement_url))
        # rating.set_overall(
        #     5.0, '- Tillgänglighetsredogörelse hittad')
        statement_content = httpRequestGetContent(statement_url, True)
        soup = BeautifulSoup(statement_content, 'lxml')

        # STATEMENTS MUST INCLUDE (ACCORDING TO https://www.digg.se/kunskap-och-stod/digital-tillganglighet/skapa-en-tillganglighetsredogorelse ):
        # - Namnet på den offentliga aktören.
        # - Namnet på den digitala servicen (till exempel webbplatsens, e-tjänstens eller appens namn).
        # - Följsamhet till lagkraven med formuleringen: helt förenlig, delvis förenlig eller inte förenlig.
        rating += rate_compatible_text(_, soup)
        # - Detaljerad, fullständig och tydlig förteckning av innehåll som inte är tillgängligt och skälen till varför det inte är tillgängligt.
        # - Datum för bedömning av följsamhet till lagkraven.
        # - Datum för senaste uppdatering.
        # - Utvärderingsmetod (till exempel självskattning, granskning av extern part).
        # - Meddelandefunktion eller länk till sådan.
        # - Länk till DIGG:s anmälningsfunktion (https://www.digg.se/tdosanmalan).
        rating += rate_notification_function_url(_, soup)
        # - Redogörelse av innehåll som undantagits på grund av oskäligt betungande anpassning (12 §) med tydlig motivering.
        rating += rate_unreasonably_burdensome_accommodation(_, soup)
        # - Redogörelse av innehåll som inte omfattas av lagkraven (9 §).

        # - Redogörelsen ska vara lätt att hitta
        #   - Tillgänglighetsredogörelsen ska vara publicerad i ett tillgängligt format (det bör vara en webbsida).
        #   - För en webbplats ska en länk till tillgänglighetsredogörelsen finnas tydligt presenterad på webbplatsens startsida, alternativt finnas åtkomlig från alla sidor exempelvis i en sidfot.
    else:
        rating.set_overall(1.0, '- Ingen tillgänglighetsredogörelse hittad')

    return rating


def rate_unreasonably_burdensome_accommodation(_, soup):
    match = soup.find(string=re.compile(
        "(Oskäligt betungande anpassning|12[ \t\r\n]§ lagen)", flags=re.MULTILINE | re.IGNORECASE))
    rating = Rating(_, review_show_improvements_only)
    if match:
        rating.set_overall(
            5.0, '- Anger oskäligt betungande anpassning (12 §)')
        rating.set_a11y(
            4.0, '- Anger oskäligt betungande anpassning (12 §)')
    else:
        rating.set_overall(
            5.0, '- Anger ej oskäligt betungande anpassning (12 §)')
        rating.set_a11y(
            5.0, '- Anger ej oskäligt betungande anpassning (12 §)')

    return rating


def rate_notification_function_url(_, soup):
    match = soup.find(href='https://www.digg.se/tdosanmalan')
    # TODO: Lookup https://www.digg.se/tdosanmalan and look for canonical url
    # https://www.digg.se/for-privatpersoner/digital-tillganglighet-for-dig-som-privatperson/anmal-bristande-tillganglighet
    # match_incorrect_url_but_correct_destionation = soup.find(
    #     href='https://www.digg.se/analys-och-uppfoljning/lagen-om-tillganglighet-till-digital-offentlig-service-dos-lagen/anmal-bristande-tillganglighet')
    # match_incorrect_url_but_correct_destionation2 = soup.find(
    #     href='https://www.digg.se/digital-tillganglighet/anmal-bristande-tillganglighet')
    rating = Rating(_, review_show_improvements_only)
    if match:
        rating.set_overall(
            5.0, '- Korrekt länk till DIGG:s anmälningsfunktion')
    # elif match_incorrect_url_but_correct_destionation:
    #     rating.set_overall(1.9)
    #     rating.set_a11y(
    #         1.9, '- Felaktig länk till DIGG:s anmälningsfunktion')
    # elif match_incorrect_url_but_correct_destionation2:
    #     rating.set_overall(1.5)
    #     rating.set_a11y(
    #         1.5, '- Länk till DIGG:s anmälningsfunktion')
    else:
        rating.set_overall(
            1.0, '- Saknar eller har felaktig länk till DIGG:s anmälningsfunktion')

    return rating


def rate_compatible_text(_, soup):
    element = soup.find(string=re.compile(
        "(?P<test>helt|delvis|inte) förenlig", flags=re.MULTILINE | re.IGNORECASE))
    rating = Rating(_, review_show_improvements_only)
    if element:
        text = element.get_text()
        regex = r'(?P<test>helt|delvis|inte) förenlig'
        match = re.search(regex, text, flags=re.IGNORECASE)
        test = match.group('test').lower()
        if 'inte' in test:
            rating.set_overall(
                5.0, '- Har följsamhet till lagkraven med formuleringen "inte förenlig"')
            rating.set_a11y(
                1.0, '- Anger själv att webbplats "inte" är förenlig med lagkraven')
        elif 'delvis' in test:
            rating.set_overall(
                5.0, '- Har följsamhet till lagkraven med formuleringen "delvis förenlig"')
            rating.set_a11y(
                3.0, '- Anger själv att webbplats bara "delvis" är förenlig med lagkraven')
        else:
            rating.set_overall(
                5.0, '- Har följsamhet till lagkraven med formuleringen "helt förenlig"')
            rating.set_a11y(
                5.0, '- Anger själv att webbplats är "helt" förenlig med lagkraven')
    else:
        rating.set_overall(
            1.0, '- Saknar följsamhet till lagkraven med formuleringen')

    return rating


def get_availability_statement_urls(content, org_url_start):
    urls = {}
    soup = BeautifulSoup(content, 'lxml')
    links = soup.find_all("a")

    for link in links:
        # if not link.find(string=re.compile(
        #         "tillg(.{1,6}|ä|&auml;|&#228;)nglighet(sredog(.{1,6}|ö|&ouml;|&#246;)relse){0,1}", flags=re.MULTILINE | re.IGNORECASE)):
        #     continue
        if not link.find(string=re.compile(
                "tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse", flags=re.MULTILINE | re.IGNORECASE)):
            continue

        url = link.get('href')
        if url == None:
            continue
        elif url.endswith('.pdf'):
            continue
        elif url.startswith('//'):
            continue
        elif url.startswith('/'):
            url = '{0}{1}'.format(org_url_start, url)
        elif url.startswith('#'):
            continue

        if not url.startswith(org_url_start):
            continue

        text = link.get_text().strip()
        urls[url] = text

    if len(urls) > 0:
        urls = dict(sorted(urls.items(), key=get_sort_statement_text))
        return urls

    return None


def get_sort_statement_text(item):
    text = item[1]
    if re.match(r'^tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse$', text, flags=re.MULTILINE | re.IGNORECASE) != None:
        return '0.{0}'.format(text)
    if re.match(r'^tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse', text, flags=re.MULTILINE | re.IGNORECASE) != None:
        return '1.{0}'.format(text)
    if re.match(r'^tillg(.{1,6}|ä|&auml;|&#228;)nglighet$', text, flags=re.MULTILINE | re.IGNORECASE) != None:
        return '2.{0}'.format(text)
    if re.match(r'^tillg(.{1,6}|ä|&auml;|&#228;)nglighet', text, flags=re.MULTILINE | re.IGNORECASE) != None:
        return '3.{0}'.format(text)

    return '4.{0}'.format(text)


def get_sort_about_text(item):
    text = item[1]
    if re.search(r'om webbplats', text, flags=re.MULTILINE | re.IGNORECASE) != None:
        return '0.{0}'.format(text)
    if re.match(r'^[ \t\r\n]*om [a-z]+$', text, flags=re.MULTILINE | re.IGNORECASE) != None:
        return '1.{0}'.format(text)
    if re.match(r'^[ \t\r\n]*om [a-z]+', text, flags=re.MULTILINE | re.IGNORECASE) != None:
        return '2.{0}'.format(text)

    return '3.{0}'.format(text)


def get_about_urls(content, org_url_start):
    urls = {}

    soup = BeautifulSoup(content, 'lxml')
    links = soup.find_all("a")

    for link in links:
        # if not link.find(string=re.compile(
        #         "(om [a-z]+|tillg(.{1,6}|ä|&auml;|&#228;)nglighet)", flags=re.MULTILINE | re.IGNORECASE)):
        if not link.find(string=re.compile(
                "om [a-z]+", flags=re.MULTILINE | re.IGNORECASE)):
            continue

        url = '{0}'.format(link.get('href'))
        if url == None:
            continue
        elif url.endswith('.pdf'):
            continue
        elif url.startswith('//'):
            continue
        elif url.startswith('/'):
            url = '{0}{1}'.format(org_url_start, url)
        elif url.startswith('#'):
            continue

        if not url.startswith(org_url_start):
            continue

        text = link.get_text().strip()
        urls[url] = text

    if len(urls) > 0:
        urls = dict(sorted(urls.items(), key=get_sort_about_text))

        return urls

    return None


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    print(run_test('sv', 'https://webperf.se'))
