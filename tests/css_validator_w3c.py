# -*- coding: utf-8 -*-
from datetime import datetime
import os
import re
import sys
import urllib  # https://docs.python.org/3/library/urllib.parse.html

from bs4 import BeautifulSoup
from models import Rating

from tests.utils import get_friendly_url_name, get_http_content, get_translation, set_cache_file, get_config_or_default
from tests.w3c_base import get_errors, identify_files
from tests.sitespeed_base import get_result

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
USE_CACHE = get_config_or_default('cache_when_possible')
CACHE_TIME_DELTA = get_config_or_default('cache_time_delta')

CSS_REVIEW_GROUP_ERRORS = get_config_or_default('css_review_group_errors')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
SITESPEED_USE_DOCKER = get_config_or_default('sitespeed_use_docker')
SITESPEED_TIMEOUT = get_config_or_default('sitespeed_timeout')

global css_features
global css_properties_doesnt_exist


def run_test(global_translation, lang_code, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    local_translation = get_translation('css_validator_w3c', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    errors = []

    # We don't need extra iterations for what we are using it for
    sitespeed_iterations = 1
    sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --plugins.remove html --plugins.remove metrics --browsertime.screenshot false --screenshot false --screenshotLCP false --browsertime.screenshotLCP false --chrome.cdp.performance false --browsertime.chrome.timeline false --videoParams.createFilmstrip false --visualMetrics false --visualMetricsPerceptual false --visualMetricsContentful false --browsertime.headless true --browsertime.chrome.includeResponseBodies all --utc true --browsertime.chrome.args ignore-certificate-errors -n {0}'.format(
        sitespeed_iterations)
    if 'nt' not in os.name:
        sitespeed_arg += ' --xvfb'

    sitespeed_arg += ' --postScript chrome-cookies.cjs --postScript chrome-versions.cjs'

    (_, filename) = get_result(
        url, SITESPEED_USE_DOCKER, sitespeed_arg, SITESPEED_TIMEOUT)

    # 1. Visit page like a normal user
    data = identify_files(filename)
    # 2. FIND ALL INLE CSS (AND CALCULTE)
    # 2.1 FINS ALL <STYLE>
    has_style_elements = False
    has_style_attributes = False
    has_css_files = False
    has_css_contenttypes = False
    all_link_resources = []

    for entry in data['htmls']:
        req_url = entry['url']
        name = get_friendly_url_name(global_translation, req_url, entry['index'])
        html = entry['content']
        (elements, errors) = get_errors_for_style_tags(req_url, html)
        if len(elements) > 0:
            has_style_elements = True
            rating += create_review_and_rating(errors, global_translation, local_translation, '- `<style>` in: {0}'.format(name))

        # 2.2 FIND ALL style=""
        (elements, errors) = get_errors_for_style_attributes(req_url, html)
        if len(elements) > 0:
            has_style_attributes = True
            rating += create_review_and_rating(errors, global_translation, local_translation, '- `style=""` in: {0}'.format(name))

        # 2.3 GET ERRORS FROM SERVICE
        # 2.4 CALCULATE SCORE
        # 3 FIND ALL <LINK> (rel=\"stylesheet\")
        (link_resources, errors) = get_errors_for_link_tags(html, url)
        if len(link_resources) > 0:
            all_link_resources.extend(link_resources)
            has_css_files = True
            rating += create_review_and_rating(errors,
                                            global_translation,  local_translation, '- `<link rel=\"stylesheet\">` in: {0}'.format(name))
            

    # 4 Check if website inlcuded css files in other ways
    for link_resource in all_link_resources:
        data_resource_info_to_remove = None
        for data_resource_info in data['resources']:
            if data_resource_info['url'] == link_resource:
                data_resource_info_to_remove = data_resource_info
                break
        if data_resource_info_to_remove != None:
            data['resources'].remove(data_resource_info_to_remove)
        
    errors = []
    for data_resource_info in data['resources']:
        has_css_contenttypes = True
        errors += get_errors_for_url(
            data_resource_info['url'])
        request_index = data_resource_info['index']
        name = get_friendly_url_name(global_translation, data_resource_info['url'], request_index)
        rating += create_review_and_rating(errors,
            global_translation,  local_translation, '- `content-type=\".*css.*\"` in: {0}'.format(name))

    # Give full points if nothing was found
    if not has_style_elements:
        errors_type_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        errors_type_rating.set_overall(5.0)
        errors_type_rating.set_standards(5.0, '- `<style>`' + local_translation('TEXT_REVIEW_RATING_GROUPED').format(
            0, 0.0))
        rating += errors_type_rating

        errors_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        errors_rating.set_overall(5.0)
        errors_rating.set_standards(5.0, '- `<style>`' + local_translation('TEXT_REVIEW_RATING_ITEMS').format(0, 0.0)),
        rating += errors_rating
    if not has_style_attributes:
        errors_type_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        errors_type_rating.set_overall(5.0)
        errors_type_rating.set_standards(5.0, '- `style=""`'+ local_translation('TEXT_REVIEW_RATING_GROUPED').format(
            0, 0.0))
        rating += errors_type_rating

        errors_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        errors_rating.set_overall(5.0)
        errors_rating.set_standards(5.0, '- `style=""`' + local_translation('TEXT_REVIEW_RATING_ITEMS').format(0, 0.0)),
        rating += errors_rating
    if not has_css_files:
        errors_type_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        errors_type_rating.set_overall(5.0)
        errors_type_rating.set_standards(5.0, '- `<link rel=\"stylesheet\">`' + local_translation('TEXT_REVIEW_RATING_GROUPED').format(
            0, 0.0))
        rating += errors_type_rating

        errors_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        errors_rating.set_overall(5.0)
        errors_rating.set_standards(5.0, '- `<link rel=\"stylesheet\">`' + local_translation('TEXT_REVIEW_RATING_ITEMS').format(0, 0.0)),
        rating += errors_rating

    if not has_css_contenttypes:
        errors_type_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        errors_type_rating.set_overall(5.0)
        errors_type_rating.set_standards(5.0, '- `content-type=\".*css.*\"`' + local_translation('TEXT_REVIEW_RATING_GROUPED').format(
            0, 0.0))
        rating += errors_type_rating

        errors_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        errors_rating.set_overall(5.0)
        errors_rating.set_standards(5.0, '- `content-type=\".*css.*\"`' + local_translation('TEXT_REVIEW_RATING_ITEMS').format(0, 0.0)),
        rating += errors_rating


    points = rating.get_overall()

    review = ''
    if points >= 5.0:
        review = local_translation('TEXT_REVIEW_CSS_VERY_GOOD')
    elif points >= 4.0:
        review = local_translation('TEXT_REVIEW_CSS_IS_GOOD')
    elif points >= 3.0:
        review = local_translation('TEXT_REVIEW_CSS_IS_OK')
    elif points > 1.0:
        review = local_translation('TEXT_REVIEW_CSS_IS_BAD')
    elif points <= 1.0:
        review = local_translation('TEXT_REVIEW_CSS_IS_VERY_BAD')

    rating.overall_review = review

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, errors)

def get_errors_for_link_tags(html, url):
    results = []

    soup = BeautifulSoup(html, 'lxml')
    elements = soup.find_all('link')

    o = urllib.parse.urlparse(url)
    parsed_url = '{0}://{1}'.format(o.scheme, o.netloc)
    parsed_url_scheme = o.scheme

    matching_elements = []
    
    resource_index = 1
    for element in elements:
        if not element.has_attr('rel'):
            continue
        resource_type = element['rel']
        is_css_link = False
        if 'stylesheet' in resource_type:
            is_css_link = True
        if 'prefetch' in resource_type and element.has_attr('as') and 'style' == element['as']:
            is_css_link = True
        if is_css_link:
            if not element.has_attr('href'):
                continue
            resource_url = element['href']

            if resource_url.startswith('//'):
                # do nothing, complete url
                resource_url = parsed_url_scheme + ':' + resource_url
            elif resource_url.startswith('/'):
                # relative url, complement with dns
                resource_url = parsed_url + resource_url
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
            resource_index += 1
            matching_elements.append(resource_url)

    return (matching_elements, results)


def get_errors_for_style_attributes(url, html):
    soup = BeautifulSoup(html, 'lxml')
    elements = soup.find_all(attrs={"style": True})

    results = []
    temp_attribute_css = ''

    for element in elements:
        temp_attribute_css += '' + "{0}{{{1}}}".format(
            element.name, element['style'])

    if temp_attribute_css != '':
        tmp_url = '{0}#styles-attributes'.format(url)
        set_cache_file(tmp_url, temp_attribute_css, True)
        results = get_errors_for_url(tmp_url)
        temp_attribute_css = ''

    return (elements, results)


def get_errors_for_style_tags(url, html):
    soup = BeautifulSoup(html, 'lxml')
    elements = soup.find_all('style')

    results = []
    temp_inline_css = ''
    for element in elements:
        temp_inline_css += '' + element.text

    if temp_inline_css != '':
        tmp_url = '{0}#style-elements'.format(url)
        set_cache_file(tmp_url, temp_inline_css, True)
        results = get_errors_for_url(tmp_url)
        temp_inline_css = ''

    return (elements, results)


def calculate_rating(number_of_error_types, number_of_errors):

    rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)

    rating_number_of_errors = 5.0 - ((number_of_errors / 2.0) / 5.0)

    if rating_number_of_error_types < 1.0:
        rating_number_of_error_types = 1.0
    if rating_number_of_errors < 1.0:
        rating_number_of_errors = 1.0

    return (rating_number_of_error_types, rating_number_of_errors)

def get_errors_for_url(url):
    params = {'doc': url, 'out': 'json', 'level': 'error'}
    return get_errors('css', params)

def get_mdn_web_docs_css_features():
    css_features = {}
    css_functions = {}

    html = get_http_content(
        'https://developer.mozilla.org/en-US/docs/Web/CSS/Reference')

    soup = BeautifulSoup(html, 'lxml')

    try:
        index_element = soup.find('div', class_='index')
        if index_element:
            links = index_element.find_all('a')
            for link in links:
                regex = r'(?P<name>[a-z\-0-9]+)(?P<func>[()]{0,2})[ ]*'
                matches = re.search(regex, link.string)
                if matches:
                    property_name = matches.group('name')
                    is_function = matches.group('func') in '()'
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
    return (css_features, css_functions)


css_spec = get_mdn_web_docs_css_features()
css_features = css_spec[0]
css_functions = css_spec[1]


def get_properties_doesnt_exist_list():
    result = []
    css_features_keys = css_features.keys()
    for item in css_features_keys:
        result.append('Property “{0}” doesn\'t exist'.format(item))

    # TODO: css_functions
    # [a-z]+: env\([^)]+\) is not a [a-z]+ value

    return result


def get_function_is_not_a_value_list():
    result = []
    css_functions_keys = css_functions.keys()
    for item in css_functions_keys:
        result.append('{0}('.format(item))

    # TODO: css_functions
    # [a-z]+: env\([^)]+\) is not a [a-z]+ value

    return result


css_properties_doesnt_exist = get_properties_doesnt_exist_list()
css_functions_no_support = get_function_is_not_a_value_list()


def create_review_and_rating(errors, global_translation, local_translation, review_header):
    review = ''
    whitelisted_words = css_properties_doesnt_exist

    whitelisted_words.append('“100%” is not a “font-stretch” value')
    whitelisted_words.extend(css_functions_no_support)

    number_of_errors = len(errors)

    error_message_dict = {}
    error_message_grouped_dict = {}
    error_message_grouped_for_rating_dict = {}
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

                tmp = re.sub(
                    regex, "X", error_message, 0, re.MULTILINE)
                if CSS_REVIEW_GROUP_ERRORS:
                    error_message = tmp

                if error_message_grouped_dict.get(error_message, False):
                    error_message_grouped_dict[error_message] = error_message_grouped_dict[error_message] + 1
                else:
                    error_message_grouped_dict[error_message] = 1

                if error_message_grouped_for_rating_dict.get(tmp, False):
                    error_message_grouped_for_rating_dict[tmp] = error_message_grouped_for_rating_dict[tmp] + 1
                else:
                    error_message_grouped_for_rating_dict[tmp] = 1


        if len(error_message_grouped_dict) > 0:
            error_message_grouped_sorted = sorted(
                error_message_grouped_dict.items(), key=lambda x: x[1], reverse=True)

            for item in error_message_grouped_sorted:

                item_value = item[1]
                item_text = item[0]

                review += local_translation('TEXT_REVIEW_ERRORS_ITEM').format(item_text, item_value)

    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    number_of_error_types = len(error_message_grouped_for_rating_dict)

    result = calculate_rating(number_of_error_types, number_of_errors)

    errors_type_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_type_rating.set_overall(result[0])
    errors_type_rating.set_standards(result[0], review_header + local_translation('TEXT_REVIEW_RATING_GROUPED').format(
        number_of_error_types, 0.0))
    rating += errors_type_rating

    errors_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    errors_rating.set_overall(result[1])
    errors_rating.set_standards(result[1], review_header + local_translation('TEXT_REVIEW_RATING_ITEMS').format(number_of_errors,
                                                                                                     0.0))
    rating += errors_rating

    rating.standards_review = rating.standards_review + review

    return rating
