# -*- coding: utf-8 -*-
import os
import subprocess
from datetime import datetime
import json
from tests.utils import get_config_or_default, get_translation
from models import Rating

review_show_improvements_only = get_config_or_default('review_show_improvements_only')
request_timeout = get_config_or_default('http_request_timeout')

def run_test(global_translation, lang_code, url):
    """

    """

    local_translation = get_translation('a11y_pa11y', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    use_axe = False
    json_result = get_pa11y_errors(url, use_axe)
    num_errors = len(json_result)
    if num_errors == 0:
        use_axe = True
        json_result = get_pa11y_errors(url, use_axe)
        num_errors = len(json_result)

    num_errors = len(json_result)

    unique_errors = set()
    return_dict = json_result
    errors = json_result

    for error in errors:
        if 'message' in error:
            err_mess = error['message'].replace('This', 'A')
            error_review = f'- {err_mess}\n'
            unique_errors.add(error_review)

    num_unique_errors = len(unique_errors)

    points_tuples = calculate_rating(num_unique_errors, num_errors)
    review = ''

    rating = Rating(global_translation, review_show_improvements_only)
    errors_type_rating = Rating(global_translation, review_show_improvements_only)
    errors_type_rating.set_overall(points_tuples[0])
    errors_type_rating.set_a11y(points_tuples[0],
                                local_translation('TEXT_REVIEW_RATING_GROUPED').format(
                                    num_unique_errors,
                                    0.0))
    rating += errors_type_rating

    errors_rating = Rating(global_translation, review_show_improvements_only)
    errors_rating.set_overall(points_tuples[1])
    errors_rating.set_a11y(points_tuples[1], local_translation(
        'TEXT_REVIEW_RATING_ITEMS').format(num_errors, 0.0))
    rating += errors_rating

    i = 1
    if len(unique_errors) > 0:
        review += local_translation('TEXT_REVIEW_A11Y_PROBLEMS')
    for error in unique_errors:
        review += error
        i += 1
        if i > 10:
            review += local_translation('TEXT_REVIEW_A11Y_TOO_MANY_PROBLEMS')
            break

    rating.a11y_review = rating.a11y_review + review
    overall = rating.get_overall()
    if overall == 5:
        rating.overall_review = local_translation('TEXT_REVIEW_A11Y_VERY_GOOD')
    elif overall >= 4:
        rating.overall_review = local_translation('TEXT_REVIEW_A11Y_IS_GOOD')
    elif overall > 2:
        rating.overall_review = local_translation('TEXT_REVIEW_A11Y_IS_VERY_BAD')
    elif overall > 3:
        rating.overall_review = local_translation('TEXT_REVIEW_A11Y_IS_BAD')
    elif overall > 4:
        rating.overall_review = local_translation('TEXT_REVIEW_A11Y_IS_OK')

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)


def calculate_rating(number_of_error_types, number_of_errors):

    rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)

    rating_number_of_errors = 5.0 - ((number_of_errors / 2.0) / 5.0)

    if rating_number_of_error_types < 1.0:
        rating_number_of_error_types = 1.0
    if rating_number_of_errors < 1.0:
        rating_number_of_errors = 1.0

    return (rating_number_of_error_types, rating_number_of_errors)


def get_pa11y_errors(url, use_axe):
    additional_args = ''
    if use_axe:
        additional_args = '--runner axe '

    # NOTE: "--ignore color-contrast" was added to temporarly solve issue #204
    command = (f"node node_modules{os.path.sep}pa11y{os.path.sep}bin{os.path.sep}pa11y.js "
                   f"--ignore color-contrast --reporter json {additional_args}{url}")
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, _ = process.communicate(timeout=request_timeout * 10)

    json_result = json.loads(output)
    return json_result
