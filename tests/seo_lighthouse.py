# -*- coding: utf-8 -*-
import datetime
from tests.lighthouse_base import run_test as lighthouse_base_run_test
from tests.utils import get_config_or_default
import gettext
_ = gettext.gettext

# DEFAULTS
googlePageSpeedApiKey = get_config_or_default('googlePageSpeedApiKey')
review_show_improvements_only = get_config_or_default('review_show_improvements_only')
lighthouse_use_api = get_config_or_default('lighthouse_use_api')


def run_test(_, langCode, url, strategy='mobile', category='seo'):

    language = gettext.translation(
        'seo_lighthouse', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    test_result = lighthouse_base_run_test(
        _, langCode, url, googlePageSpeedApiKey, strategy, category, review_show_improvements_only, lighthouse_use_api)
    rating = test_result[0]
    test_return_dict = test_result[1]

    review = rating.overall_review
    points = rating.get_overall()

    if points >= 5.0:
        review = _local("TEXT_REVIEW_SEO_VERY_GOOD") + review
    elif points >= 4.0:
        review = _local("TEXT_REVIEW_SEO_IS_GOOD") + review
    elif points >= 3.0:
        review = _local("TEXT_REVIEW_SEO_IS_OK") + review
    elif points > 1.0:
        review = _local("TEXT_REVIEW_SEO_IS_BAD") + review
    elif points <= 1.0:
        review = _local("TEXT_REVIEW_SEO_IS_VERY_BAD") + review

    rating.overall_review = review

    print(_('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, test_return_dict)
