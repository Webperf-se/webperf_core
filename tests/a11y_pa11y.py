# -*- coding: utf-8 -*-
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

    bashCommand = "pa11y-ci --reporter json {0}".format(url)
    process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    json_result = json.loads(output)

    result_list = list()
    if 'results' in json_result:
        result_list = json_result['results']

    num_errors = 0

    if 'errors' in json_result:
        num_errors = json_result['errors']

    return_dict = {}

    points = 0
    review_overall = ''
    review_a11y = ''
    review = ''

    if num_errors == 0:
        points = 5
        review_overall = _local('TEXT_REVIEW_A11Y_VERY_GOOD')
    elif num_errors == 1:
        points = 4
        review_overall = _local('TEXT_REVIEW_A11Y_IS_GOOD')
    elif num_errors > 8:
        points = 1
        review_overall = _local('TEXT_REVIEW_A11Y_IS_VERY_BAD')
    elif num_errors >= 4:
        points = 2
        review_overall = _local('TEXT_REVIEW_A11Y_IS_BAD')
    elif num_errors >= 2:
        points = 3
        review_overall = _local('TEXT_REVIEW_A11Y_IS_OK')

    review_a11y = _local(
        'TEXT_REVIEW_A11Y_NUMBER_OF_PROBLEMS').format(num_errors)
    return_dict['antal_problem'] = num_errors

    unique_errors = set()

    errors = list()
    if url in result_list:
        errors = result_list[url]

    for error in errors:
        if 'message' in error:
            err_mess = error['message'].replace('This', 'A')
            error_review = '- {0}\n'.format(err_mess)
            unique_errors.add(error_review)
            if 'code' in error:
                # '{0}-{1}'.format(error.get('code'), i)
                key = error['code']
                return_dict.update({key: err_mess})

    i = 1

    if len(unique_errors) > 0:
        review += _local('TEXT_REVIEW_A11Y_PROBLEMS')

    for error in unique_errors:
        review += error
        i += 1
        if i > 10:
            review += _local('TEXT_REVIEW_A11Y_TOO_MANY_PROBLEMS')
            break

    rating = Rating(_, review_show_improvements_only)
    rating.set_overall(points, review_overall)
    rating.set_a11y(points, review_a11y)

    rating.a11y_review = rating.a11y_review + review

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    print(run_test('sv', 'https://webperf.se'))
