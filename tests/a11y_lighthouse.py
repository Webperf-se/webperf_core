# -*- coding: utf-8 -*-
import datetime
from tests.lighthouse_base import run_test as lighthouse_base_run_test
import config
from tests.utils import *
import gettext

# DEFAULTS
googlePageSpeedApiKey = config.googlePageSpeedApiKey
review_show_improvements_only = config.review_show_improvements_only
lighthouse_use_api = config.lighthouse_use_api


def run_test(_, langCode, url, strategy='mobile', category='accessibility'):

    language = gettext.translation(
        'a11y_lighthouse', localedir='locales', languages=[langCode])
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
        review = _local("TEXT_REVIEW_A11Y_VERY_GOOD")
    elif points >= 4.0:
        review = _local("TEXT_REVIEW_A11Y_IS_GOOD")
    elif points >= 3.0:
        review = _local("TEXT_REVIEW_A11Y_IS_OK")
    elif points > 1.0:
        review = _local("TEXT_REVIEW_A11Y_IS_BAD")
    elif points <= 1.0:
        review = _local("TEXT_REVIEW_A11Y_IS_VERY_BAD")

    rating.overall_review = review

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, test_return_dict)
