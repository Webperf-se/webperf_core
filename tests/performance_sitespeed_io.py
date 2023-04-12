# -*- coding: utf-8 -*-
from pathlib import Path
import os
from models import Rating
import datetime
import config
from tests.utils import *
import gettext
_local = gettext.gettext

sitespeed_use_docker = config.sitespeed_use_docker


def get_result(sitespeed_use_docker, arg):

    result = ''
    if sitespeed_use_docker:
        dir = Path(os.path.dirname(
            os.path.realpath(__file__)) + os.path.sep).parent
        data_dir = dir.resolve()

        bashCommand = "docker run --rm -v {1}:/sitespeed.io sitespeedio/sitespeed.io:latest {0}".format(
            arg, data_dir)

        import subprocess
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        result = str(output)
    else:
        import subprocess

        bashCommand = "node node_modules{1}sitespeed.io{1}bin{1}sitespeed.js {0}".format(
            arg, os.path.sep)

        process = subprocess.Popen(
            bashCommand.split(), stdout=subprocess.PIPE)

        output, error = process.communicate()
        result = str(output)

    return result


def run_test(_, langCode, url):
    """
    Checking an URL against Sitespeed.io (Docker version). 
    For installation, check out:
    - https://hub.docker.com/r/sitespeedio/sitespeed.io/
    - https://www.sitespeed.io
    """
    language = gettext.translation(
        'performance_sitespeed_io', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    rating = Rating(_)
    result_dict = {}
    (desktop_rating, desktop_result_dict) = validate_on_desktop(url, _, _local)
    rating += desktop_rating
    result_dict.update(desktop_result_dict)

    (mobile_rating, mobile_result_dict) = validate_on_mobile(url, _, _local)
    rating += mobile_rating
    result_dict.update(mobile_result_dict)

    (no_external_rating, no_external_result_dict) = validate_on_mobile_no_external_domain(
        url, _, _local, mobile_rating, mobile_result_dict)
    rating += no_external_rating
    result_dict.update(no_external_result_dict)

    (nojs_rating, nojs_result_dict) = validate_on_mobile_no_javascript(
        url, _, _local, mobile_rating, mobile_result_dict)
    rating += nojs_rating
    result_dict.update(nojs_result_dict)

    print(_('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)


def validate_on_mobile_no_external_domain(url, _, _local, mobile_rating, mobile_result_dict):
    rating = Rating(_)
    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    if hostname.startswith('www.'):
        tmp_url = url.replace(hostname, hostname[4:])
        o = urllib.parse.urlparse(tmp_url)
        hostname = o.hostname

    arg = '--shm-size=1g -b chrome --blockDomainsExcept *.{2} --mobile true --connectivity.profile 3gfast --visualMetrics true --plugins.remove screenshot --speedIndex true --xvfb --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        config.sitespeed_iterations, url, hostname)
    if 'nt' in os.name:
        arg = '--shm-size=1g -b chrome --mobile true --connectivity.profile 3gfast --visualMetrics true --plugins.remove screenshot --speedIndex true --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
            config.sitespeed_iterations, url)

    result_dict = get_result_dict(get_result(
        sitespeed_use_docker, arg), 'mobile no third parties')

    limit = 250

    external_to_remove = list()

    for pair in mobile_result_dict.items():
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

        if mobile_obj['median'] > (limit + noxternal_obj['median']):
            value_diff = mobile_obj['median'] - noxternal_obj['median']
            tmp_points = 5.0 - ((value_diff / limit) * 0.1)

            tmp_rating = Rating(_)
            tmp_rating.set_overall(
                tmp_points, '- [mobile] {0} could be improved by {1:.2f}ms by removing external resources'.format(key, value_diff))
            rating += tmp_rating
            key_matching = True

        if 'range' not in mobile_obj:
            continue
        if 'range' not in noxternal_obj:
            continue

        if mobile_obj['range'] > (limit + noxternal_obj['range']):
            value_diff = mobile_obj['range'] - noxternal_obj['range']
            tmp_points = 5.0 - ((value_diff / limit) * 0.1)
            tmp_rating = Rating(_)
            tmp_rating.set_overall(
                tmp_points, '- [mobile] {0} could be ±{1:.2f}ms less "vobbly" by removing external resources'.format(key, value_diff))
            rating += tmp_rating
            key_matching = True

        if not key_matching:
            external_to_remove.append(key)

    for key in external_to_remove:
        del result_dict[key]

    rating += rate_result_dict(result_dict,
                               'mobile no third parties', _, _local)

    if mobile_rating.get_overall() < rating.get_overall():
        points = 5.0 - (rating.get_overall() - mobile_rating.get_overall())
        tmp_rating = Rating(_)
        tmp_rating.set_overall(
            points, '- [mobile] Performance rating could be improved by removing some/all external resources')
        rating += tmp_rating

    return (rating, result_dict)


def validate_on_mobile_no_javascript(url, _, _local, mobile_rating, mobile_result_dict):
    rating = Rating(_)
    arg = '--shm-size=1g -b chrome --block .js --mobile true --connectivity.profile 3gfast --visualMetrics true --plugins.remove screenshot --speedIndex true --xvfb --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors --browsertime.chrome.args disable-javascript -n {0} {1}'.format(
        config.sitespeed_iterations, url)
    if 'nt' in os.name:
        arg = '--shm-size=1g -b chrome --block .js --mobile true --connectivity.profile 3gfast --visualMetrics true --plugins.remove screenshot --speedIndex true --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors --browsertime.chrome.args disable-javascript -n {0} {1}'.format(
            config.sitespeed_iterations, url)

    result_dict = get_result_dict(get_result(
        sitespeed_use_docker, arg), 'mobile no js')

    limit = 250
    nojs_to_remove = list()
    for pair in mobile_result_dict.items():
        key = pair[0]
        mobile_obj = pair[1]
        key_matching = False

        if key not in result_dict:
            continue

        nojs_obj = result_dict[key]

        if 'median' not in mobile_obj:
            continue
        if 'median' not in nojs_obj:
            continue

        if mobile_obj['median'] > (limit + nojs_obj['median']):
            value_diff = mobile_obj['median'] - nojs_obj['median']
            tmp_points = 5.0 - ((value_diff / limit) * 0.1)
            tmp_rating = Rating(_)
            tmp_rating.set_overall(
                tmp_points, '- [mobile] {0} could be improved by {1:.2f}ms by removing javascript files'.format(key, value_diff))
            rating += tmp_rating
            key_matching = True

        if 'range' not in mobile_obj:
            continue
        if 'range' not in nojs_obj:
            continue

        if mobile_obj['range'] > (limit + nojs_obj['range']):
            value_diff = mobile_obj['range'] - nojs_obj['range']
            tmp_points = 5.0 - ((value_diff / limit) * 0.1)
            tmp_rating = Rating(_)
            tmp_rating.set_overall(
                tmp_points, '- [mobile] {0} could be ±{1:.2f}ms less "vobbly" by removing javascript files'.format(key, value_diff))
            rating += tmp_rating
            key_matching = True

        if not key_matching:
            nojs_to_remove.append(key)

    for key in nojs_to_remove:
        del result_dict[key]

    rating += rate_result_dict(result_dict, 'mobile no js', _, _local)

    if mobile_rating.get_overall() < rating.get_overall():
        points = 5.0 - (rating.get_overall() - mobile_rating.get_overall())
        tmp_rating = Rating(_)
        tmp_rating.set_overall(
            points, '- [mobile] Performance rating could be improved by removing some/all javascript files')
        rating += tmp_rating

    return (rating, result_dict)


def validate_on_desktop(url, _, _local):
    arg = '--shm-size=1g -b chrome --connectivity.profile native --visualMetrics true --plugins.remove screenshot --speedIndex true --xvfb --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        config.sitespeed_iterations, url)
    if 'nt' in os.name:
        arg = '--shm-size=1g -b chrome --connectivity.profile native --visualMetrics true --plugins.remove screenshot --speedIndex true --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
            config.sitespeed_iterations, url)

    result = get_result_dict(get_result(sitespeed_use_docker, arg), 'desktop')
    rating = rate_result_dict(result, 'desktop', _, _local)

    return (rating, result)


def validate_on_mobile(url, _, _local):
    arg = '--shm-size=1g -b chrome --mobile true --connectivity.profile 3gfast --visualMetrics true --plugins.remove screenshot --speedIndex true --xvfb --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        config.sitespeed_iterations, url)
    if 'nt' in os.name:
        arg = '--shm-size=1g -b chrome --mobile true --connectivity.profile 3gfast --visualMetrics true --plugins.remove screenshot --speedIndex true --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
            config.sitespeed_iterations, url)

    result = get_result_dict(get_result(sitespeed_use_docker, arg), 'mobile')
    rating = rate_result_dict(result, 'mobile', _, _local)

    return (rating, result)


def rate_result_dict(result_dict, mode, _, _local):
    points = int(result_dict['Points'])

    review = ''

    review_overall = ''
    if mode == 'desktop' or mode == 'mobile':
        if points >= 5.0:
            review_overall = _local('TEXT_REVIEW_VERY_GOOD')
        elif points >= 4.0:
            review_overall = _local('TEXT_REVIEW_IS_GOOD')
        elif points >= 3.0:
            review_overall = _local('TEXT_REVIEW_IS_OK')
        elif points > 1.0:
            review_overall = _local('TEXT_REVIEW_IS_BAD')
        elif points <= 1.0:
            review_overall = _local('TEXT_REVIEW_IS_VERY_BAD')

    del result_dict['Points']

    rating = Rating(_)
    rating.set_overall(points, review_overall.replace(
        '- ', '- [{0}] '.format(mode)))
    rating.set_performance(points, review)

    review = rating.performance_review
    for pair in result_dict.items():
        value = pair[1]
        if 'msg' in value:
            review += value['msg']

    # review += _local("TEXT_REVIEW_NUMBER_OF_REQUESTS").format(
    #     result_dict['Requests'])

    rating.performance_review = review
    return rating


def get_result_dict(data, mode):
    result_dict = {}
    tmp_dict = {}
    regex = r"(?P<name>TTFB|DOMContentLoaded|firstPaint|FCP|LCP|Load|TBT|CLS|FirstVisualChange|SpeedIndex|VisualComplete85|LastVisualChange)\:[ ]{0,1}(?P<value>[0-9\.ms]+)"
    matches = re.finditer(regex, data, re.MULTILINE)

    for matchNum, match in enumerate(matches, start=1):
        name = match.group('name')
        value = match.group('value')
        # print('PAIR: ', name, value, '± 10')
        if name not in tmp_dict:
            tmp_dict[name] = list()
        tmp_dict[name].append(value)

    for pair in tmp_dict.items():
        key = pair[0]
        values = pair[1]
        biggest = 0
        total = 0
        value_range = 0
        result = 0
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

        tmp = {
            'median': median,
            'range': value_range,
            'mode': mode,
            'points': -1,
            'msg': '- [{2}] {3}: {0:.2f}ms (±{1:.2f}ms)\r\n'.format(result, value_range, mode, key)
        }

        if 'SpeedIndex' in key:
            points = 5.0

            adjustment = 500
            if 'mobile' in mode:
                adjustment = 1500

            # give 0.5 seconds in credit
            speedindex_adjusted = result - adjustment
            if speedindex_adjusted <= 0:
                # speed index is 500 or below, give highest score
                points = 5.0
            else:
                points = 5.0 - (speedindex_adjusted / 1000)

            result_dict['Points'] = points
        result_dict[key] = tmp
    return result_dict
