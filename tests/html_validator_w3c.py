# -*- coding: utf-8 -*-
from models import Rating
import datetime
import re
import config
from tests.w3c_base import get_errors
from tests.utils import *
import gettext
_local = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
review_show_improvements_only = config.review_show_improvements_only


def run_test(_, langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    rating = Rating(_, review_show_improvements_only)
    points = 0.0
    review = ''

    language = gettext.translation(
        'html_validator_w3c', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    headers = {'user-agent': useragent}
    params = {'doc': url,
              'out': 'json',
              'level': 'error'}
    errors = get_errors('html', headers, params)
    number_of_errors = len(errors)

    error_message_grouped_dict = {}
    if number_of_errors > 0:
        regex = r"(“[^”]+”)"
        for item in errors:
            error_message = item['message']
            error_message = re.sub(
                regex, "X", error_message, 0, re.MULTILINE)

            if error_message_grouped_dict.get(error_message, False):
                error_message_grouped_dict[error_message] = error_message_grouped_dict[error_message] + 1
            else:
                error_message_grouped_dict[error_message] = 1

        if len(error_message_grouped_dict) > 0:
            error_message_grouped_sorted = sorted(
                error_message_grouped_dict.items(), key=lambda x: x[1], reverse=True)

            for item in error_message_grouped_sorted:

                item_value = item[1]
                item_text = item[0]

                review += _local('TEXT_REVIEW_ERRORS_ITEM').format(item_text, item_value)

    number_of_error_types = len(error_message_grouped_dict)

    result = calculate_rating(number_of_error_types, number_of_errors)

    # if number_of_error_types > 0:
    error_types_rating = Rating(_, review_show_improvements_only)
    error_types_rating.set_overall(result[0], _local('TEXT_REVIEW_RATING_GROUPED').format(
        number_of_error_types, 0.0))
    rating += error_types_rating

    # if number_of_errors > 0:
    error_rating = Rating(_, review_show_improvements_only)
    error_rating.set_overall(result[1], _local(
        'TEXT_REVIEW_RATING_ITEMS').format(number_of_errors, 0.0))
    rating += error_rating

    points = rating.get_overall()
    rating.set_standards(points)
    rating.standards_review = review

    review = ''
    if points == 5.0:
        review = _local('TEXT_REVIEW_HTML_VERY_GOOD')
    elif points >= 4.0:
        review = _local('TEXT_REVIEW_HTML_IS_GOOD').format(
            number_of_errors)
    elif points >= 3.0:
        review = _local('TEXT_REVIEW_HTML_IS_OK').format(
            number_of_errors)
    elif points > 1.0:
        review = _local('TEXT_REVIEW_HTML_IS_BAD').format(
            number_of_errors)
    elif points <= 1.0:
        review = _local('TEXT_REVIEW_HTML_IS_VERY_BAD').format(
            number_of_errors)

    # rating.set_overall(points)
    rating.standards_review = rating.overall_review + rating.standards_review
    rating.overall_review = review

    print(_('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, errors)


def calculate_rating(number_of_error_types, number_of_errors):

    rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)

    rating_number_of_errors = 5.0 - ((number_of_errors / 2.0) / 5.0)

    if rating_number_of_error_types < 1.0:
        rating_number_of_error_types = 1.0
    if rating_number_of_errors < 1.0:
        rating_number_of_errors = 1.0

    return (rating_number_of_error_types, rating_number_of_errors)
