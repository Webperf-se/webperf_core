# -*- coding: utf-8 -*-
from datetime import datetime
import gettext
from tests.lighthouse_base import run_test as lighthouse_base_run_test
from tests.utils import get_config_or_default
_local = gettext.gettext

# DEFAULTS
googlePageSpeedApiKey = get_config_or_default('googlePageSpeedApiKey')
review_show_improvements_only = get_config_or_default('review_show_improvements_only')
lighthouse_use_api = get_config_or_default('lighthouse_use_api')
strategy = 'mobile'
category = 'performance'


def run_test(global_translation, lang_code, url, silance=False):
    """
    perf = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=performance&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    a11y = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=accessibility&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    practise = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=best-practices&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    pwa = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=pwa&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    seo = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=seo&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    """

    language = gettext.translation(
        'performance_lighthouse', localedir='locales', languages=[lang_code])
    language.install()
    local_translation = language.gettext

    if not silance:
        print(local_translation('TEXT_RUNNING_TEST'))

        print(global_translation('TEXT_TEST_START').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    test_result = lighthouse_base_run_test(
        global_translation, lang_code, url, googlePageSpeedApiKey, strategy, category, review_show_improvements_only, lighthouse_use_api)
    rating = test_result[0]
    test_return_dict = test_result[1]

    review = rating.overall_review
    points = rating.get_overall()
    if points >= 5.0:
        review = local_translation("TEXT_REVIEW_VERY_GOOD")
    elif points >= 4.0:
        review = local_translation("TEXT_REVIEW_IS_GOOD")
    elif points >= 3.0:
        review = local_translation("TEXT_REVIEW_IS_OK")
    elif points > 1.0:
        review = local_translation("TEXT_REVIEW_IS_BAD")
    elif points <= 1.0:
        review = local_translation("TEXT_REVIEW_IS_VERY_BAD")
    rating.overall_review = review

    if not silance:
        print(global_translation('TEXT_TEST_END').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, test_return_dict)
