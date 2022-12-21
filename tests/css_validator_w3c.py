# -*- coding: utf-8 -*-
import datetime
import gettext
import re
import sys
import time
import urllib  # https://docs.python.org/3/library/urllib.parse.html

import config
import requests
from bs4 import BeautifulSoup
from models import Rating

from tests.utils import *
from tests.w3c_base import get_errors

_local = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
css_review_group_errors = config.css_review_group_errors
review_show_improvements_only = config.review_show_improvements_only
w3c_use_website = config.w3c_use_website

global css_features
global css_properties_doesnt_exist


def run_test(_, langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    rating = Rating(_, review_show_improvements_only)

    language = gettext.translation(
        'css_validator_w3c', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    errors = list()
    error_message_dict = {}

    # 1. Get ROOT PAGE HTML
    html = get_source(url)
    # 2. FIND ALL INLE CSS (AND CALCULTE)
    # 2.1 FINS ALL <STYLE>
    errors = get_errors_for_style_tags(html, _local)
    rating += create_review_and_rating(errors, _, _local, '- `<style>`')

    # 2.2 FIND ALL style=""
    errors = get_errors_for_style_attributes(html, _local)
    rating += create_review_and_rating(errors, _, _local, '- `style=""`')

    # 2.3 GET ERRORS FROM SERVICE
    # 2.4 CALCULATE SCORE
    # 3 FIND ALL <LINK> (rel=\"stylesheet\")
    errors = get_errors_for_link_tags(html, url, _local)
    rating += create_review_and_rating(errors,
                                       _,  _local, '- `<link rel=\"stylesheet\">`')

    points = rating.get_overall()

    review = ''
    if points >= 5.0:
        review = _local('TEXT_REVIEW_CSS_VERY_GOOD')
    elif points >= 4.0:
        review = _local('TEXT_REVIEW_CSS_IS_GOOD')
    elif points >= 3.0:
        review = _local('TEXT_REVIEW_CSS_IS_OK')
    elif points > 1.0:
        review = _local('TEXT_REVIEW_CSS_IS_BAD')
    elif points <= 1.0:
        review = _local('TEXT_REVIEW_CSS_IS_VERY_BAD')

    rating.overall_review = review

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, errors)


def get_errors_for_link_tags(html, url, _):
    #print('link tag(s)')
    results = list()

    soup = BeautifulSoup(html, 'lxml')
    elements = soup.find_all('link')

    o = urllib.parse.urlparse(url)
    parsed_url = '{0}://{1}'.format(o.scheme, o.netloc)
    parsed_url_scheme = o.scheme

    resource_index = 1
    for element in elements:
        # print(element.contents)
        resource_type = element['rel']
        if 'stylesheet' in resource_type:
            resource_url = element['href']
            #temp_inline_css += '' + element['href'].text

            if resource_url.startswith('//'):
                # do nothing, complete url
                resource_url = parsed_url_scheme + ':' + resource_url
                # print('- do nothing, complete url')
            elif resource_url.startswith('/'):
                # relative url, complement with dns
                resource_url = parsed_url + resource_url
                # print('- relative url, complement with dns')
            elif resource_url.startswith('http://') or resource_url.startswith('https://'):
                resource_url = resource_url
            else:
                # relative url, but without starting /
                resource_url = parsed_url + '/' + resource_url

            # print('resource_url', resource_url)
            # print('stylesheet resource #{0}:'.format(resource_index))
            # review_header = '* <link rel="stylesheet" #{0}>:\n'.format(
            #    resource_index)
            # 3.1 GET ERRORS FROM SERVICE (FOR EVERY <LINK>) AND CALCULATE SCORE
            results += get_errors_for_url(
                resource_url)
            # results.append(result_link_css)
            resource_index += 1
            if w3c_use_website:
                time.sleep(10)

    return results


def get_errors_for_style_attributes(html, _):
    #print('style attribute(s)')

    soup = BeautifulSoup(html, 'lxml')
    elements = soup.find_all(attrs={"style": True})

    results = list()
    temp_attribute_css = ''

    for element in elements:
        # print(element.contents)
        temp_attribute_css += '' + "{0}{{{1}}}".format(
            element.name, element['style'])

    if temp_attribute_css != '':
        results = get_errors_for_css(temp_attribute_css)
        temp_attribute_css = ''
        if w3c_use_website:
            time.sleep(10)

    return results


def get_errors_for_style_tags(html, _):
    #print('style tag(s)')

    soup = BeautifulSoup(html, 'lxml')
    elements = soup.find_all('style')

    results = list()
    temp_inline_css = ''
    for element in elements:
        # print(element.contents)
        temp_inline_css += '' + element.text

    if temp_inline_css != '':
        # print('style-tag(s):')
        #review_header = '* <style>:\n'
        results = get_errors_for_css(temp_inline_css)
        # results.append(result_inline_css)
        temp_inline_css = ''
        if w3c_use_website:
            time.sleep(10)
    return results


def calculate_rating(number_of_error_types, number_of_errors):

    rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)

    rating_number_of_errors = 5.0 - ((number_of_errors / 2.0) / 5.0)

    if rating_number_of_error_types < 1.0:
        rating_number_of_error_types = 1.0
    if rating_number_of_errors < 1.0:
        rating_number_of_errors = 1.0

    return (rating_number_of_error_types, rating_number_of_errors)


def get_errors_for_url(url):
    headers = {'user-agent': useragent}
    params = {'doc': url, 'out': 'json', 'level': 'error'}
    return get_errors('css', headers, params)


def get_errors_for_css(data):

    data = data.strip()

    headers = {'user-agent': useragent,
               'Content-Type': 'text/css; charset=utf-8'}
    params = {'showsource': 'yes', 'css': 'yes',
              'out': 'json', 'level': 'error'}
    return get_errors('css', headers, params, data.encode('utf-8'))


def get_mdn_web_docs_css_features():
    css_features = {}
    css_functions = {}

    html = httpRequestGetContent(
        'https://developer.mozilla.org/en-US/docs/Web/CSS/Reference')

    soup = BeautifulSoup(html, 'lxml')

    try:
        index_element = soup.find('div', class_='index')
        if index_element:
            links = index_element.find_all('a')
            for link in links:
                # print('link: {0}'.format(link.string))
                regex = '(?P<name>[a-z\-0-9]+)(?P<func>[()]{0,2})[ ]*'
                matches = re.search(regex, link.string)
                if matches:
                    property_name = matches.group('name')
                    is_function = matches.group('func') in '()'
                    # print('-', property_name)
                    # css_features.append(property_name)
                    if is_function:
                        css_functions["{0}".format(
                            property_name)] = link.get('href')
                    else:
                        css_features["{0}".format(
                            property_name)] = link.get('href')
        else:
            print('no index element found')
    except:
        print(
            'Error! "{0}" '.format(sys.exc_info()[0]))
        pass
    return (css_features, css_functions)


css_spec = get_mdn_web_docs_css_features()
css_features = css_spec[0]
css_functions = css_spec[1]


def get_properties_doesnt_exist_list():
    result = list()
    css_features_keys = css_features.keys()
    for item in css_features_keys:
        result.append('Property “{0}” doesn\'t exist'.format(item))

    # TODO: css_functions
    # [a-z]+: env\([^)]+\) is not a [a-z]+ value

    return result


def get_function_is_not_a_value_list():
    result = list()
    css_functions_keys = css_functions.keys()
    for item in css_functions_keys:
        result.append('{0}('.format(item))

    # TODO: css_functions
    # [a-z]+: env\([^)]+\) is not a [a-z]+ value

    return result


css_properties_doesnt_exist = get_properties_doesnt_exist_list()
css_functions_no_support = get_function_is_not_a_value_list()


def create_review_and_rating(errors, _, _local, review_header):
    review = ''
    whitelisted_words = css_properties_doesnt_exist

    whitelisted_words.append('“100%” is not a “font-stretch” value')
    whitelisted_words.extend(css_functions_no_support)

    number_of_errors = len(errors)

    error_message_dict = {}
    error_message_grouped_dict = {}
    if number_of_errors > 0:
        regex = r"(“[^”]+”)"
        for item in errors:
            error_message = item['message']
            is_whitelisted = False
            for whitelisted_word in whitelisted_words:
                if whitelisted_word in error_message:
                    is_whitelisted = True
                    number_of_errors -= 1
                    break

            if not is_whitelisted:
                error_message_dict[error_message] = "1"

                if css_review_group_errors:
                    error_message = re.sub(
                        regex, "X", error_message, 0, re.MULTILINE)

                if error_message_grouped_dict.get(error_message, False):
                    error_message_grouped_dict[error_message] = error_message_grouped_dict[error_message] + 1
                else:
                    error_message_grouped_dict[error_message] = 1

        if len(error_message_grouped_dict) > 0:
            error_message_grouped_sorted = sorted(
                error_message_grouped_dict.items(), key=lambda x: x[1], reverse=True)

            for item in error_message_grouped_sorted:

                item_value = item[1]
                item_text = item[0]

                review += _local('TEXT_REVIEW_ERRORS_ITEM').format(item_text, item_value)

    rating = Rating(_, review_show_improvements_only)

    number_of_error_types = len(error_message_grouped_dict)

    result = calculate_rating(number_of_error_types, number_of_errors)

    errors_type_rating = Rating(_, review_show_improvements_only)
    errors_type_rating.set_overall(result[0])
    errors_type_rating.set_standards(result[0], review_header + _local('TEXT_REVIEW_RATING_GROUPED').format(
        number_of_error_types, 0.0))
    rating += errors_type_rating

    errors_rating = Rating(_, review_show_improvements_only)
    errors_rating.set_overall(result[1])
    errors_rating.set_standards(result[1], review_header + _local('TEXT_REVIEW_RATING_ITEMS').format(number_of_errors,
                                                                                                     0.0))
    rating += errors_rating

    rating.standards_review = rating.standards_review + review

    return rating


def get_source(url):
    try:
        headers = {'user-agent': useragent}
        request = requests.get(url, allow_redirects=True,
                               headers=headers,
                               timeout=request_timeout)

        # get source
        return request.text

    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None
