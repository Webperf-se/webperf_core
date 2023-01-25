# -*- coding: utf-8 -*-
import os
import subprocess
import datetime
import json
from models import Rating
import config
import gettext
_ = gettext.gettext

review_show_improvements_only = config.review_show_improvements_only


def run_test(_, langCode, url):
    """

    """

    language = gettext.translation(
        'a11y_pa11y', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

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
            error_review = '- {0}\n'.format(err_mess)
            unique_errors.add(error_review)

    num_unique_errors = len(unique_errors)

    points_tuples = calculate_rating(num_unique_errors, num_errors)
    review = ''

    rating = Rating(_, review_show_improvements_only)
    errors_type_rating = Rating(_, review_show_improvements_only)
    errors_type_rating.set_overall(points_tuples[0])
    errors_type_rating.set_a11y(points_tuples[0], _local('TEXT_REVIEW_RATING_GROUPED').format(
        num_unique_errors, 0.0))
    rating += errors_type_rating

    errors_rating = Rating(_, review_show_improvements_only)
    errors_rating.set_overall(points_tuples[1])
    errors_rating.set_a11y(points_tuples[1], _local(
        'TEXT_REVIEW_RATING_ITEMS').format(num_errors, 0.0))
    rating += errors_rating

    i = 1
    if len(unique_errors) > 0:
        review += _local('TEXT_REVIEW_A11Y_PROBLEMS')
    for error in unique_errors:
        review += error
        i += 1
        if i > 10:
            review += _local('TEXT_REVIEW_A11Y_TOO_MANY_PROBLEMS')
            break

    rating.a11y_review = rating.a11y_review + review
    overall = rating.get_overall()
    if overall == 5:
        rating.overall_review = _local('TEXT_REVIEW_A11Y_VERY_GOOD')
    elif overall >= 4:
        rating.overall_review = _local('TEXT_REVIEW_A11Y_IS_GOOD')
    elif overall > 2:
        rating.overall_review = _local('TEXT_REVIEW_A11Y_IS_VERY_BAD')
    elif overall > 3:
        rating.overall_review = _local('TEXT_REVIEW_A11Y_IS_BAD')
    elif overall > 4:
        rating.overall_review = _local('TEXT_REVIEW_A11Y_IS_OK')

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

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

    bashCommand = "node node_modules{1}pa11y{1}bin{1}pa11y.js --reporter json {2}{0}".format(
        url, os.path.sep, additional_args)

    process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    json_result = json.loads(output)
    return json_result


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    print(run_test('sv', 'https://webperf.se'))
