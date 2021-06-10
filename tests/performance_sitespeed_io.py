# -*- coding: utf-8 -*-
from models import Rating
import sys
import socket
import ssl
import json
import requests
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
import docker
from bs4 import BeautifulSoup
import config
from tests.utils import *
import gettext
_ = gettext.gettext


def run_test(langCode, url):
    """
    Checking an URL against Sitespeed.io (Docker version). 
    For installation, check out:
    - https://hub.docker.com/r/sitespeedio/sitespeed.io/
    - https://www.sitespeed.io
    """
    arg = '--rm --shm-size=1g -b chrome --plugins.remove screenshot --browsertime.videoParams.createFilmstrip false --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        config.sitespeed_iterations, url)

    image = "sitespeedio/sitespeed.io:latest"

    language = gettext.translation(
        'performance_sitespeed_io', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

    docker_client = docker.from_env()
    result = str(docker_client.containers.run(image, arg))
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

    # give 0.5 seconds in credit
    speedindex_adjusted = speedindex - 500
    if speedindex_adjusted <= 0:
        # speed index is 500 or below, give highest score
        points = 5.0
    else:
        points = 5.0 - (speedindex_adjusted / 1000)

    if points >= 5.0:
        review = _('TEXT_REVIEW_VERY_GOOD')
    elif points >= 4.0:
        review = _('TEXT_REVIEW_IS_GOOD')
    elif points >= 3.0:
        review = _('TEXT_REVIEW_IS_OK')
    elif points > 1.0:
        review = _('TEXT_REVIEW_IS_BAD')
    elif points <= 1.0:
        review = _('TEXT_REVIEW_IS_VERY_BAD')

    review += '* Speedindex: {}\n'.format(speedindex)
    if 's' in result_dict['load']:
        review += _("TEXT_REVIEW_LOAD_TIME").format(result_dict['load'])
    else:
        review += _("TEXT_REVIEW_LOAD_TIME_SECONDS").format(
            result_dict['load'])

    review += _("TEXT_REVIEW_NUMBER_OF_REQUESTS").format(
        result_dict['requests'])

    rating = Rating()
    rating.set_overall(points, review)
    rating.set_performance(points, review)

    return (rating, result_dict)
