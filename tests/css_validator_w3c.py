# -*- coding: utf-8 -*-
import time
import sys
import socket
import ssl
import json
import requests
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
import json
from bs4 import BeautifulSoup
import config
from tests.utils import *
import gettext
_ = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
css_review_group_errors = config.css_review_group_errors
css_scoring_method = config.css_scoring_method

global css_features
global css_properties_doesnt_exist


def run_test(langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    points = 0.0
    review = ''

    language = gettext.translation(
        'css_validator_w3c', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

    errors = list()

    # 1. Get ROOT PAGE HTML
    html = get_source(url)
    # 2. FIND ALL INLE CSS (AND CALCULTE)
    # 2.1 FINS ALL <STYLE>
    errors += get_errors_for_style_tags(html, _)

    # 2.2 FIND ALL style=""
    errors += get_errors_for_style_attributes(html, _)

    # 2.3 GET ERRORS FROM SERVICE
    # 2.4 CALCULATE SCORE
    # 3 FIND ALL <LINK> (rel=\"stylesheet\")
    errors += get_errors_for_link_tags(html, url, _)

    result = create_review_and_rating(errors, _, '')

    number_of_results = 1
    points = result[0]
    review += result[1]
    error_message_dict = result[2]

    points = float("{0:.3f}".format(points / number_of_results))

    if points > 5.0:
        points = 5.0

    if points < 1.0:
        points = 1.0

    if points == 5.0:
        review = _('TEXT_REVIEW_CSS_VERY_GOOD') + review
    elif points >= 4.0:
        review = _('TEXT_REVIEW_CSS_IS_GOOD') + review
    elif points >= 3.0:
        review = _('TEXT_REVIEW_CSS_IS_OK') + review
    elif points > 1.0:
        review = _('TEXT_REVIEW_CSS_IS_BAD') + review
    elif points <= 1.0:
        review = _('TEXT_REVIEW_CSS_IS_VERY_BAD') + review

    return (points, review, error_message_dict)


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
        time.sleep(10)
    return results


def calculate_rating(number_of_error_types, number_of_errors):
    rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)

    temp_number_of_errors = number_of_errors - number_of_error_types
    if number_of_errors <= 0:
        rating_number_of_errors = 0.0
    else:
        rating_number_of_errors = ((temp_number_of_errors / 2.0) / 5.0)

    rating_result = float("{0:.2f}".format(
        rating_number_of_error_types - rating_number_of_errors))
    if rating_result < 1.0:
        rating_result = 1.0

    return (rating_result, rating_number_of_error_types, rating_number_of_errors)


def get_errors_for_url(url):
    try:
        service_url = 'https://validator.w3.org/nu/'
        headers = {'user-agent': useragent}
        params = {'doc': url, 'out': 'json', 'level': 'error'}
        request = requests.get(service_url, allow_redirects=True,
                               headers=headers,
                               timeout=request_timeout * 2,
                               params=params)

        # get JSON
        response = json.loads(request.text)
        errors = response['messages']

        return errors
    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None


def get_errors_for_css(data):
    try:
        data = data.strip()

        # print('data:', data)

        service_url = 'https://validator.w3.org/nu/'
        headers = {'user-agent': useragent,
                   'Content-Type': 'text/css; charset=utf-8'}
        params = {'showsource': 'yes', 'css': 'yes',
                  'out': 'json', 'level': 'error'}
        request = requests.post(service_url, allow_redirects=True,
                                headers=headers,
                                params=params,
                                timeout=request_timeout,
                                data=data.encode('utf-8')
                                )

        # get JSON
        response = json.loads(request.text)
        errors = response['messages']

        #print('errors css:', errors)

        return errors
        # print(len(errors))
    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None


def get_mdn_web_docs_css_features():
    css_features = {}

    html = httpRequestGetContent(
        'https://developer.mozilla.org/en-US/docs/Web/CSS/Reference')

    soup = BeautifulSoup(html, 'lxml')

    try:
        index_element = soup.find('div', class_='index')
        if index_element:
            links = index_element.find_all('a')
            for link in links:
                # print('link: {0}'.format(link.string))
                regex = '(?P<name>[a-z\-0-9]+)[ ]*'
                matches = re.search(regex, link.string)
                if matches:
                    property_name = matches.group('name')
                    # print('-', property_name)
                    # css_features.append(property_name)
                    css_features["{0}".format(
                        property_name)] = link.get('href')
        else:
            print('no index element found')
    except:
        print(
            'Error! "{0}" '.format(sys.exc_info()[0]))
        pass
    return css_features


css_features = get_mdn_web_docs_css_features()


def get_properties_doesnt_exist_list():
    result = list()
    css_features_keys = css_features.keys()
    for item in css_features_keys:
        result.append('Property “{0}” doesn\'t exist'.format(item))

    return result


css_properties_doesnt_exist = get_properties_doesnt_exist_list()


def create_review_and_rating(errors, _, review_header):
    review = ''
    whitelisted_words = css_properties_doesnt_exist

    whitelisted_words.append('“100%” is not a “font-stretch” value')

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

                # print(' - error-message:', error_message)

                if css_review_group_errors:
                    error_message = re.sub(
                        regex, "X", error_message, 0, re.MULTILINE)

                if error_message_grouped_dict.get(error_message, False):
                    error_message_grouped_dict[error_message] = error_message_grouped_dict[error_message] + 1
                else:
                    error_message_grouped_dict[error_message] = 1

        if len(error_message_grouped_dict) > 0:
            if css_review_group_errors:
                review += _('TEXT_REVIEW_ERRORS_GROUPED')
            error_message_grouped_sorted = sorted(
                error_message_grouped_dict.items(), key=lambda x: x[1], reverse=True)

            for item in error_message_grouped_sorted:

                item_value = item[1]
                item_text = item[0]

                review += _('TEXT_REVIEW_ERRORS_ITEM').format(item_text, item_value)

    # print(' - number_of_errors:', number_of_errors)

    number_of_error_types = len(error_message_grouped_dict)

    result = calculate_rating(number_of_error_types, number_of_errors)

    if number_of_errors > 0:
        review = _('TEXT_REVIEW_RATING_ITEMS').format(number_of_errors,
                                                      result[2]) + review
    if number_of_error_types > 0:
        review = _('TEXT_REVIEW_RATING_GROUPED').format(
            number_of_error_types, result[1]) + review

    if review_header != '':
        review = review_header + review

    points = result[0]
    return (points, review, error_message_dict)


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
