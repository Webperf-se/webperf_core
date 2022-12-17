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
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    arg = '--shm-size=1g -b chrome --plugins.remove screenshot --speedIndex true --xvfb --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        config.sitespeed_iterations, url)
    if 'nt' in os.name:
        arg = '--shm-size=1g -b chrome --plugins.remove screenshot --speedIndex true --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
            config.sitespeed_iterations, url)

    result = get_result(sitespeed_use_docker, arg)

    result = result.replace('\\n', ' ')

    old_val = None
    old_val_unsliced = None
    result_dict = {}

    for line in result.split(' '):
        if old_val == 'speedindex' or old_val == 'load' or old_val == 'backendtime' or old_val == 'firstpaint' or old_val == 'firstvisualchange' or old_val == 'domcontentloaded' or old_val == 'visualcomplete85' or old_val == 'lastvisualchange' or old_val == 'rumspeedindex' or old_val == 'dominteractivetime' or old_val == 'domcontentloadedtime' or old_val == 'pageloadtime' or old_val == 'perceptualspeedindex':
            result_dict[old_val] = line.replace('ms', '')

        if line[:-1].lower() == 'requests':
            result_dict['requests'] = old_val_unsliced

        old_val = line[:-1].lower()
        old_val_unsliced = line

    if 's' in result_dict['speedindex']:
        """
        Changes speedindex to a number if for instance 1.1s it becomes 1100
        """
        result_dict['speedindex'] = int(
            float(result_dict['speedindex'].replace('s', '')) * 1000)

    speedindex = int(result_dict['speedindex'])

    review = ''
    points = 5.0

    # give 0.5 seconds in credit
    speedindex_adjusted = speedindex - 500
    if speedindex_adjusted <= 0:
        # speed index is 500 or below, give highest score
        points = 5.0
    else:
        points = 5.0 - (speedindex_adjusted / 1000)

    review_overall = ''
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

    review += '- Speedindex: {}\n'.format(speedindex)

    rating = Rating(_)
    rating.set_overall(points, review_overall)
    rating.set_performance(points, review)

    review = rating.performance_review
    if 's' in result_dict['load']:
        review += _local("TEXT_REVIEW_LOAD_TIME").format(result_dict['load'])
    else:
        review += _local("TEXT_REVIEW_LOAD_TIME_SECONDS").format(
            result_dict['load'])

    review += _local("TEXT_REVIEW_NUMBER_OF_REQUESTS").format(
        result_dict['requests'])

    rating.performance_review = review

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)
