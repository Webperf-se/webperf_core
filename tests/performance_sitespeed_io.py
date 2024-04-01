# -*- coding: utf-8 -*-
import json
from pathlib import Path
import os
import re
from datetime import datetime
from models import Rating
from tests.utils import get_config_or_default, get_translation

REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
SITESPEED_USE_DOCKER = get_config_or_default('sitespeed_use_docker')

def get_result(sitespeed_use_docker, arg):

    result = ''
    if sitespeed_use_docker:
        base_directory = Path(os.path.dirname(
            os.path.realpath(__file__)) + os.path.sep).parent
        data_dir = base_directory.resolve()

        command = "docker run --rm -v {1}:/sitespeed.io sitespeedio/sitespeed.io:latest {0}".format(
            arg, data_dir)

        import subprocess
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output, _ = process.communicate(timeout=REQUEST_TIMEOUT * 10)
        result = str(output)
    else:
        import subprocess

        command = "node node_modules{1}sitespeed.io{1}bin{1}sitespeed.js {0}".format(
            arg, os.path.sep)

        process = subprocess.Popen(
            command.split(), stdout=subprocess.PIPE)

        output, _ = process.communicate(timeout=REQUEST_TIMEOUT * 10)
        result = str(output)

    return result


def run_test(global_translation, lang_code, url):
    """
    Checking an URL against Sitespeed.io (Docker version). 
    For installation, check out:
    - https://hub.docker.com/r/sitespeedio/sitespeed.io/
    - https://www.sitespeed.io
    """

    local_translation = get_translation('performance_sitespeed_io', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    rating = Rating(global_translation)
    result_dict = {}

    validator_result_dicts = []

    validators = get_validators()
    for validator in validators:
        if validator['name'].startswith('mobile'):
            validator_result_dicts.append(
                validate_on_mobile_using_validator(url, validator))
        if validator['name'].startswith('desktop'):
            validator_result_dicts.append(
                validate_on_desktop_using_validator(url, validator))

    # Are they still not ready they need to fix it...
    desktop_result_dict = validate_on_desktop(url)

    mobile_result_dict = validate_on_mobile(url)

    desktop_rating = rate_result_dict(desktop_result_dict, None,
                                      'desktop', global_translation, local_translation)

    rating += desktop_rating
    result_dict.update(desktop_result_dict)

    mobile_rating = rate_result_dict(mobile_result_dict, None,
                                     'mobile', global_translation, local_translation)

    rating += mobile_rating
    result_dict.update(mobile_result_dict)

    for validator_result_dict in validator_result_dicts:
        validator_name = validator_result_dict['name']
        reference_name = None
        reference_rating = None
        reference_result_dict = None
        use_reference = validator_result_dict['use_reference']
        if use_reference:
            if validator['name'].startswith('mobile'):
                reference_name = 'mobile'
                reference_rating = mobile_rating.get_overall()
                reference_result_dict = mobile_result_dict
            if validator['name'].startswith('desktop'):
                reference_name = 'desktop'
                reference_rating = desktop_rating.get_overall()
                reference_result_dict = desktop_result_dict

        validator_rating = rate_result_dict(validator_result_dict, reference_result_dict,
                                            validator_name, global_translation, local_translation)
        rating += validator_rating
        result_dict.update(validator_result_dict)

        if use_reference and reference_rating != None:
            validator_rating_overall = validator_rating.get_overall()
            if reference_rating < validator_rating_overall and validator_rating_overall != -1 and validator_rating_overall != -1:
                rating.overall_review += '- [{2}] Advice: Rating may improve from {0} to {1} with {3} changes\r\n'.format(
                    reference_rating, validator_rating_overall, reference_name, validator_name)

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)


def get_validators():
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent
    config_file = os.path.join(
        base_directory.resolve(), 'sitespeed-rules.json')
    if not os.path.exists(config_file):
        return []
    with open(config_file) as json_config_file:
        data = json.load(json_config_file)
        return data


def validate_on_mobile_using_validator(url, validator_config):
    browertime_plugin_options = ''

    if 'headers' in validator_config:
        index = 1
        for header in validator_config['headers']:
            browertime_plugin_options += ' --browsertime.webperf.header0{0} {1}={2}'.format(
                index, header['name'].replace(' ', '%20').replace('=', '%3D'), header['value'].replace(' ', '%20').replace('=', '%3D'))
            index += 1
    if 'htmls' in validator_config:
        index = 1
        for header in validator_config['htmls']:
            browertime_plugin_options += ' --browsertime.webperf.HTML0{0} {1}={2}'.format(
                index, header['replace'].replace(' ', '%20').replace('=', '%3D'), header['replaceWith'].replace(' ', '%20').replace('=', '%3D'))
            index += 1

    arg = '--shm-size=1g -b chrome --mobile true --chrome.CPUThrottlingRate 3 --connectivity.profile 3gfast --visualMetrics true --plugins.remove screenshot --speedIndex true --xvfb --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} --preScript chrome-custom.cjs {1}{2}'.format(
        get_config_or_default('SITESPEED_ITERATIONS'), url, browertime_plugin_options)
    if 'nt' in os.name:
        arg = '--shm-size=1g -b chrome --mobile true --chrome.CPUThrottlingRate 3 --connectivity.profile 3gfast --visualMetrics true --plugins.remove screenshot --speedIndex true --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} --preScript chrome-custom.cjs {1}{2}'.format(
            get_config_or_default('SITESPEED_ITERATIONS'), url, browertime_plugin_options)

    result_dict = get_result_dict(get_result(
        SITESPEED_USE_DOCKER, arg), validator_config['name'])
    result_dict['name'] = validator_config['name']
    result_dict['use_reference'] = validator_config['use_reference']

    return result_dict


def validate_on_desktop_using_validator(url, validator_config):
    browertime_plugin_options = ''

    if 'headers' in validator_config:
        index = 1
        for header in validator_config['headers']:
            browertime_plugin_options += ' --browsertime.webperf.header0{0} {1}={2}'.format(
                index, header['name'].replace(' ', '%20').replace('=', '%3D'), header['value'].replace(' ', '%20').replace('=', '%3D'))
            index += 1
    if 'htmls' in validator_config:
        index = 1
        for header in validator_config['htmls']:
            browertime_plugin_options += ' --browsertime.webperf.HTML0{0} {1}={2}'.format(
                index, header['replace'].replace(' ', '%20').replace('=', '%3D'), header['replaceWith'].replace(' ', '%20').replace('=', '%3D'))
            index += 1

    arg = '--shm-size=1g -b chrome --connectivity.profile native --visualMetrics true --plugins.remove screenshot --speedIndex true --xvfb --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} --preScript chrome-custom.cjs {1}{2}'.format(
        get_config_or_default('SITESPEED_ITERATIONS'), url, browertime_plugin_options)
    if 'nt' in os.name:
        arg = '--shm-size=1g -b chrome --connectivity.profile native --visualMetrics true --plugins.remove screenshot --speedIndex true --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} --preScript chrome-custom.cjs {1}{2}'.format(
            get_config_or_default('SITESPEED_ITERATIONS'), url, browertime_plugin_options)

    result_dict = get_result_dict(get_result(
        SITESPEED_USE_DOCKER, arg), validator_config['name'])
    result_dict['name'] = validator_config['name']
    result_dict['use_reference'] = validator_config['use_reference']

    return result_dict


def validate_on_desktop(url):
    arg = '--shm-size=1g -b chrome --connectivity.profile native --visualMetrics true --plugins.remove screenshot --speedIndex true --xvfb --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        get_config_or_default('SITESPEED_ITERATIONS'), url)
    if 'nt' in os.name:
        arg = '--shm-size=1g -b chrome --connectivity.profile native --visualMetrics true --plugins.remove screenshot --speedIndex true --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
            get_config_or_default('SITESPEED_ITERATIONS'), url)

    result_dict = get_result_dict(get_result(
        SITESPEED_USE_DOCKER, arg), 'desktop')

    return result_dict


def validate_on_mobile(url):
    arg = '--shm-size=1g -b chrome --mobile true --connectivity.profile 3gfast --visualMetrics true --plugins.remove screenshot --speedIndex true --xvfb --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        get_config_or_default('SITESPEED_ITERATIONS'), url)
    if 'nt' in os.name:
        arg = '--shm-size=1g -b chrome --mobile true --connectivity.profile 3gfast --visualMetrics true --plugins.remove screenshot --speedIndex true --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
            get_config_or_default('SITESPEED_ITERATIONS'), url)

    result_dict = get_result_dict(get_result(
        SITESPEED_USE_DOCKER, arg), 'mobile')

    return result_dict


def rate_result_dict(result_dict, reference_result_dict, mode, global_translation, local_translation):
    limit = 500

    rating = Rating(_)
    performance_review = ''
    overview_review = ''

    if reference_result_dict != None:
        reference_name = 'UNKNOWN'
        if result_dict['name'].startswith('mobile'):
            reference_name = 'mobile'
        if result_dict['name'].startswith('desktop'):
            reference_name = 'desktop'
        external_to_remove = []
        for pair in reference_result_dict.items():
            key = pair[0]
            mobile_obj = pair[1]
            key_matching = False

            if key not in result_dict:
                continue

            noxternal_obj = result_dict[key]

            if 'median' not in mobile_obj:
                continue
            if 'median' not in noxternal_obj:
                continue

            value_diff = 0
            if mobile_obj['median'] > (limit + noxternal_obj['median']):
                value_diff = mobile_obj['median'] - noxternal_obj['median']

                txt = '- [{2}] Advice: {0} may improve by {1:.2f}ms with {3} changes\r\n'.format(
                    key, value_diff, reference_name, mode)

                overview_review += txt
                key_matching = True

            if 'range' not in mobile_obj:
                continue
            if 'range' not in noxternal_obj:
                continue
            value_diff = 0
            if mobile_obj['range'] > (limit + noxternal_obj['range']):
                value_diff = mobile_obj['range'] - noxternal_obj['range']

                txt = '- [{2}] Advice: {0} could be ±{1:.2f}ms less "bumpy" with {3} changes\r\n'.format(
                    key, value_diff, reference_name, mode)

                overview_review += txt
                key_matching = True

            if not key_matching:
                external_to_remove.append(key)

        for key in external_to_remove:
            del result_dict[key]

    if 'Points' in result_dict:
        del result_dict['Points']
    if 'name' in result_dict:
        del result_dict['name']
    if 'use_reference' in result_dict:
        del result_dict['use_reference']

    for pair in result_dict.items():
        value = pair[1]
        if 'msg' not in value:
            continue
        if 'points' in value and value['points'] != -1:
            points = value['points']
            entry_rating = Rating(_)
            entry_rating.set_overall(points)
            entry_rating.set_performance(
                points, value['msg'])
            rating += entry_rating
        else:
            performance_review += '{0}\r\n'.format(value['msg'])

    rating.overall_review = rating.overall_review + overview_review
    rating.performance_review = rating.performance_review + performance_review
    return rating


def get_result_dict(data, mode):
    result_dict = {}
    tmp_dict = {}
    regex = r"(?P<name>TTFB|DOMContentLoaded|firstPaint|FCP|LCP|Load|TBT|CLS|FirstVisualChange|SpeedIndex|VisualComplete85|LastVisualChange)\:[ ]{0,1}(?P<value>[0-9\.ms]+)"
    matches = re.finditer(regex, data, re.MULTILINE)

    for _, match in enumerate(matches, start=1):
        name = match.group('name')
        value = match.group('value')

        if name not in tmp_dict:
            tmp_dict[name] = []
        tmp_dict[name].append(value)

    for pair in tmp_dict.items():
        key = pair[0]
        values = pair[1]
        biggest = 0
        total = 0
        value_range = 0
        result = 0
        median = 0
        for value in values:
            number = 0
            if 'ms' in value:
                number = float(value.replace('ms', ''))
            elif 's' in value:
                number = float(
                    value.replace('s', '')) * 1000
            total += number
            if number > biggest:
                biggest = number
            # print('  ', number, total)
        value_count = len(values)
        if value_count < 2:
            value_range = 0
            result = total
        else:
            median = total / value_count
            value_range = biggest - median
            result = median

        fullname = key
        points = -1
        if 'TTFB' in key:
            # https://web.dev/ttfb/
            fullname = 'TTFB (Time to First Byte)'
            if 'desktop' in mode:
                if median <= 250:
                    points = 5.0
                elif median <= 450:
                    points = 3.0
                else:
                    points = 1.0
            elif 'mobile' in mode:
                if median <= 800:
                    points = 5.0
                elif median <= 1800:
                    points = 3.0
                else:
                    points = 1.0
        elif 'TBT' in key:
            # https://web.dev/tbt/
            # https://developer.chrome.com/docs/lighthouse/performance/lighthouse-total-blocking-time/#how-lighthouse-determines-your-tbt-score
            fullname = 'TBT (Total Blocking Time)'
            if median <= 200:
                points = 5.0
            elif median <= 600:
                points = 3.0
            else:
                points = 1.0
        elif 'FCP' in key:
            # https://web.dev/fcp/
            fullname = 'FCP (First Contentful Paint)'
            if median <= 1800:
                points = 5.0
            elif median <= 3000:
                points = 3.0
            else:
                points = 1.0
        elif 'LCP' in key:
            # https://web.dev/lcp/
            fullname = 'LCP (Largest Contentful Paint)'
            if 'desktop' in mode:
                if median <= 500:
                    points = 5.0
                elif median <= 1000:
                    points = 3.0
                else:
                    points = 1.0
            elif 'mobile' in mode:
                if median <= 1500:
                    points = 5.0
                elif median <= 2500:
                    points = 3.0
                else:
                    points = 1.0
        elif 'CLS' in key:
            # https://web.dev/cls/
            fullname = 'CLS (Cumulative Layout Shift)'
            if median <= 0.1:
                points = 5.0
            elif median <= 0.25:
                points = 3.0
            else:
                points = 1.0

        elif 'SpeedIndex' in key or 'FirstVisualChange' in key or 'VisualComplete85' in key or 'Load' in key:
            # https://docs.webpagetest.org/metrics/speedindex/
            adjustment = 500
            if 'mobile' in mode:
                adjustment = 1500

            limit = 500
            # give 0.5 seconds in credit
            speedindex_adjusted = result - adjustment
            if speedindex_adjusted <= 0:
                # speed index is 500 or below, give highest score
                points = 5.0
            else:
                points = 5.0 - ((speedindex_adjusted / limit) * 1.0)

        tmp = {
            'median': median,
            'range': value_range,
            'mode': mode,
            'points': points,
            'msg': '- [{2}] {3}: {0:.2f}ms, ±{1:.2f}ms'.format(result, value_range, mode, fullname),
            'values': values
        }

        result_dict[key] = tmp
    return result_dict
