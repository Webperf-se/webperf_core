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

    results = list()

    # 0. Get list of CSS property names from MDN Web Docs
    #css_features = get_mdn_web_docs_css_features(True)

    # 1. Get ROOT PAGE HTML
    html = get_source(url)
    # 2. FIND ALL INLE CSS (AND CALCULTE)
    # 2.1 FINS ALL <STYLE>
    results_style_tags = get_errors_for_style_tags(html, css_features, _)
    for result in results_style_tags:
        results.append(result)

    # 2.2 FIND ALL style=""
    results_style_attributes = get_errors_for_style_attributes(
        html, css_features, _)
    for result in results_style_attributes:
        results.append(result)

    # 2.3 GET ERRORS FROM SERVICE
    # 2.4 CALCULATE SCORE
    # 3 FIND ALL <LINK> (rel=\"stylesheet\")
    results_link_tags = get_errors_for_link_tags(html, css_features, url, _)
    for result in results_link_tags:
        results.append(result)

    # 4 COMBINE SCORE(s)
    # Medelvärdsuträkning för alla resultat
    if css_scoring_method == 'average':
        number_of_results = len(results)
        points = 0.0
        error_message_dict = {}
        for result in results:
            current_points = result[0]
            points += current_points
            if current_points < 5.0:
                review += result[1]
    elif css_scoring_method == 'median':
        # Medelvärde för de resultat som EJ fått 5.0 av 5.0
        number_of_results = 0
        points = 0.0
        error_message_dict = {}
        for result in results:
            current_points = result[0]
            if current_points < 5.0:
                review += result[1]
                number_of_results += 1
                points += current_points
    else:
        # Använd lägsta värdet för alla resultat som värde
        number_of_results = 1
        points = 5.0
        error_message_dict = {}
        for result in results:
            current_points = result[0]
            if current_points < points:
                review += result[1]
                number_of_results = 1
                points = current_points

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


def get_errors_for_link_tags(html, css_features, url, _):
    results = list()

    regex = r"(?P<markup><link[^>]+(href|src)=[\"|'](?P<resource>[^\"|']+)[^>]*>)"
    matches = re.finditer(regex, html, re.MULTILINE)

    o = urllib.parse.urlparse(url)
    parsed_url = '{0}://{1}'.format(o.scheme, o.netloc)
    parsed_url_scheme = o.scheme

    resource_index = 1
    for matchNum, match in enumerate(matches, start=1):
        markup = match.group('markup')
        if 'stylesheet' in markup:
            resource_url = match.group('resource')
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

            #print('resource_url', resource_url)
            # print('stylesheet resource #{0}:'.format(resource_index))
            review_header = '* <link rel="stylesheet" #{0}>:\n'.format(
                resource_index)
            # 3.1 GET ERRORS FROM SERVICE (FOR EVERY <LINK>) AND CALCULATE SCORE
            result_link_css = calculate_rating_for_resource(
                resource_url, css_features, _, review_header)
            results.append(result_link_css)
            resource_index += 1
            time.sleep(10)

    return results


def get_errors_for_style_attributes(html, css_features, _):
    results = list()
    regex = r"<(?P<tag>[a-z0-1]+) .*style=[\"|'](?P<css>[^\"|']+)"
    matches = re.finditer(regex, html, re.MULTILINE)
    temp_attribute_css = ''
    for matchNum, match in enumerate(matches, start=1):
        attribute_tag = match.group('tag')
        attribute_style = match.group('css')
        # limit number of calls to service (combine rules)
        temp_attribute_css += "{0}{{{1}}}".format(
            attribute_tag, attribute_style)

    if temp_attribute_css != '':
        # print('style-attribute(s):')
        review_header = '* style="...":\n'
        result_attribute_css = calculate_rating_for_markup(
            temp_attribute_css, css_features, _, review_header)
        results.append(result_attribute_css)
        temp_attribute_css = ''
        time.sleep(10)

    return results


def get_errors_for_style_tags(html, css_features, _):
    regex = r"<style.*>(?P<css>[^<]+)<\/style>"
    matches = re.finditer(regex, html, re.MULTILINE)
    results = list()
    temp_inline_css = ''
    for matchNum, match in enumerate(matches, start=1):
        inline_style = match.group('css')
        # limit number of calls to service (combine rules)
        temp_inline_css += inline_style
    if temp_inline_css != '':
        # print('style-tag(s):')
        review_header = '* <style>:\n'
        result_inline_css = calculate_rating_for_markup(
            temp_inline_css, css_features, _, review_header)
        results.append(result_inline_css)
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
                               timeout=request_timeout,
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

        return errors
        # print(len(errors))
    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None


def calculate_rating_for_markup(data, css_features, _, review_header):
    errors = get_errors_for_css(data)
    result = create_review_and_rating(errors, css_features, _, review_header)
    return result


def calculate_rating_for_resource(url, css_features, _, review_header):
    errors = get_errors_for_url(url)
    result = create_review_and_rating(errors, css_features, _, review_header)
    return result


def get_mdn_web_docs_css_features():
    css_features = list()

    html = httpRequestGetContent(
        'https://developer.mozilla.org/en-US/docs/Web/CSS/Reference')

    soup = BeautifulSoup(html, 'lxml')

    try:
        index_element = soup.find('div', class_='index')
        if index_element:
            links = index_element.find_all('a')
            for link in links:
                #print('link: {0}'.format(link.string))
                regex = '(?P<name>[a-z\-0-9]+)[ ]*'
                matches = re.search(regex, link.string)
                if matches:
                    property_name = matches.group('name')
                    # print('-', property_name)
                    css_features.append(property_name)
        else:
            print('no index element found')
    except:
        print(
            'Error! "{0}" '.format(sys.exc_info()[0]))
        pass

    result = list()
    for item in css_features:
        result.append('Property “{0}” doesn\'t exist'.format(item))

    return result


css_features = get_mdn_web_docs_css_features()


def create_review_and_rating(errors, css_features, _, review_header):
    review = ''
    whitelisted_words = css_features

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

                #print(' - error-message:', error_message)

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

    #print(' - number_of_errors:', number_of_errors)

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
