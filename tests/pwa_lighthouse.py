# -*- coding: utf-8 -*-
import datetime
from tests.lighthouse_base import run_test as lighthouse_base_run_test
import config
from tests.utils import *
import gettext
_ = gettext.gettext

# DEFAULTS
googlePageSpeedApiKey = config.googlePageSpeedApiKey
review_show_improvements_only = config.review_show_improvements_only
lighthouse_use_api = config.lighthouse_use_api


def run_test(_, langCode, url, strategy='mobile', category='pwa'):
    language = gettext.translation(
        'pwa_lighthouse', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    test_result = lighthouse_base_run_test(
        _, langCode, url, googlePageSpeedApiKey, strategy, category, review_show_improvements_only, lighthouse_use_api)
    rating = test_result[0]
    test_return_dict = test_result[1]

    review = rating.overall_review
    points = rating.get_overall()

    if points >= 5.0:
        review = _local("TEXT_REVIEW_PWA_VERY_GOOD") + review
    elif points >= 4.0:
        review = _local("TEXT_REVIEW_PWA_IS_GOOD") + review
    elif points >= 3.0:
        review = _local("TEXT_REVIEW_PWA_IS_OK") + review
    elif points > 1.0:
        review = _local("TEXT_REVIEW_PWA_IS_BAD") + review
    elif points <= 1.0:
        review = _local("TEXT_REVIEW_PWA_IS_VERY_BAD") + review

    rating.overall_review = review

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, test_return_dict)
