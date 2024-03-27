# -*- coding: utf-8 -*-
from datetime import datetime
from tests.lighthouse_base import run_test as lighthouse_base_run_test
from tests.utils import get_config_or_default, get_translation

# DEFAULTS
GOOGLEPAGESPEEDAPIKEY = get_config_or_default('googlePageSpeedApiKey')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
LIGHTHOUSE_USE_API = get_config_or_default('lighthouse_use_api')

def run_test(global_translation, lang_code, url, strategy='mobile', category='accessibility'):

    local_translation = get_translation('a11y_lighthouse', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    test_result = lighthouse_base_run_test(
                        global_translation,
                        lang_code,
                        url,
                        GOOGLEPAGESPEEDAPIKEY,
                        strategy,
                        category,
                        REVIEW_SHOW_IMPROVEMENTS_ONLY,
                        LIGHTHOUSE_USE_API)
    rating = test_result[0]
    test_return_dict = test_result[1]

    review = rating.overall_review
    points = rating.get_overall()
    if points >= 5.0:
        review = local_translation("TEXT_REVIEW_A11Y_VERY_GOOD")
    elif points >= 4.0:
        review = local_translation("TEXT_REVIEW_A11Y_IS_GOOD")
    elif points >= 3.0:
        review = local_translation("TEXT_REVIEW_A11Y_IS_OK")
    elif points > 1.0:
        review = local_translation("TEXT_REVIEW_A11Y_IS_BAD")
    elif points <= 1.0:
        review = local_translation("TEXT_REVIEW_A11Y_IS_VERY_BAD")

    rating.overall_review = review

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, test_return_dict)
