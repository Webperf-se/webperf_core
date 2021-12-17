# -*- coding: utf-8 -*-
#from models import Rating
import datetime
from tests.lighthouse_base import run_test as lighthouse_base_run_test
import config
from tests.utils import *
import gettext
_local = gettext.gettext

# DEFAULTS
googlePageSpeedApiKey = config.googlePageSpeedApiKey


def run_test(_, langCode, url, strategy='mobile', category='accessibility'):

    language = gettext.translation(
        'a11y_lighthouse', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    test_result = lighthouse_base_run_test(
        _, langCode, url, googlePageSpeedApiKey, strategy, category)
    rating = test_result[0]
    test_return_dict = test_result[1]

    review = rating.overall_review
    points = rating.get_overall()

    if points >= 5.0:
        review = _local("TEXT_REVIEW_A11Y_VERY_GOOD") + review
    elif points >= 4.0:
        review = _local("TEXT_REVIEW_A11Y_IS_GOOD") + review
    elif points >= 3.0:
        review = _local("TEXT_REVIEW_A11Y_IS_OK") + review
    elif points > 1.0:
        review = _local("TEXT_REVIEW_A11Y_IS_BAD") + review
    elif points <= 1.0:
        review = _local("TEXT_REVIEW_A11Y_IS_VERY_BAD") + review

    rating.overall_review = review
    rating.set_a11y(points, review)

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, test_return_dict)
