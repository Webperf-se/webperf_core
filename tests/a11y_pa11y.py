# -*- coding: utf-8 -*-
import os
import subprocess
from datetime import datetime
import json
from tests.utils import get_config_or_default, get_translation
from models import Rating

def run_test(global_translation, lang_code, url):
    """
    Runs an accessibility test on a given URL and returns the results and ratings.

    This function runs the Pa11y accessibility tool on a specified URL. It calculates 
    the number of errors and unique error types, and then rates these errors. The function 
    returns the rating and the results of the accessibility test.

    Parameters:
    global_translation (function): Function to translate text to a global language.
    lang_code (str): The language code for the local translation.
    url (str): The URL to run the accessibility test on.

    Returns:
    tuple: A tuple containing the rating object and the results of the accessibility test.
    """
    local_translation = get_translation('a11y_pa11y', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    use_axe = False
    json_result = get_pa11y_errors(url, use_axe)
    # If we fail to connect to website the result_dict will be None and we should end test
    if json_result is None:
        error_rating = Rating(global_translation, get_config_or_default('review_show_improvements_only'))
        error_rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (error_rating, {'failed': True })

    num_errors = len(json_result)
    if num_errors == 0:
        use_axe = True
        json_result = get_pa11y_errors(url, use_axe)
        num_errors = len(json_result)

    num_errors = len(json_result)

    return_dict = json_result
    errors = json_result

    unique_errors = get_unique_errors(errors)
    num_unique_errors = len(unique_errors)

    rating = rate_errors(global_translation,
                         local_translation,
                         num_errors,
                         unique_errors,
                         num_unique_errors)

    return (rating, return_dict)

def get_unique_errors(errors):
    """
    Gets unique errors from a list of many errors

    Parameters:
    errors (list): The list of errors.
    """
    unique_errors = set()
    for error in errors:
        if 'message' in error:
            err_mess = error['message'].replace('This', 'A')
            error_review = f'- {err_mess}\n'
            unique_errors.add(error_review)
    return unique_errors

def rate_errors(
        global_translation,
        local_translation,
        num_errors,
        unique_errors,
        num_unique_errors):
    """
    Rates the accessibility errors based on their quantity and type.

    This function calculates ratings for the number of unique error types and the total 
    number of errors. It then generates a review based on these ratings and the unique 
    errors. The overall rating and review are determined based on the calculated ratings.

    Parameters:
    global_translation (function): Function to translate text to a global language.
    local_translation (function): Function to translate text to a local language.
    num_errors (int): The total number of errors.
    unique_errors (list): The list of unique errors.
    num_unique_errors (int): The number of unique error types.

    Returns:
    Rating: An object of the Rating class with the calculated ratings and reviews.
    """
    points_tuples = calculate_rating(num_unique_errors, num_errors)
    review = ''

    rating = Rating(global_translation, get_config_or_default('review_show_improvements_only'))
    errors_type_rating = Rating(global_translation, get_config_or_default('review_show_improvements_only'))
    errors_type_rating.set_overall(points_tuples[0])
    errors_type_rating.set_a11y(points_tuples[0],
                                local_translation('TEXT_REVIEW_RATING_GROUPED').format(
                                    num_unique_errors,
                                    0.0))
    rating += errors_type_rating

    errors_rating = Rating(global_translation, get_config_or_default('review_show_improvements_only'))
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

    return rating


def calculate_rating(number_of_error_types, number_of_errors):
    """
    Calculates ratings based on the number of error types and total errors.

    This function calculates two ratings: one based on the number of error types and 
    another based on the total number of errors. The ratings are calculated such that 
    a higher number of errors or error types results in a lower rating. The minimum 
    rating is 1.0.

    Parameters:
    number_of_error_types (int): The number of different types of errors.
    number_of_errors (int): The total number of errors.

    Returns:
    tuple: A tuple containing the rating based on the number of error types and the 
           rating based on the total number of errors.
    """
    rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)

    rating_number_of_errors = 5.0 - ((number_of_errors / 2.0) / 5.0)

    rating_number_of_error_types = max(rating_number_of_error_types, 1.0)
    rating_number_of_errors = max(rating_number_of_errors, 1.0)

    return (rating_number_of_error_types, rating_number_of_errors)


def get_pa11y_errors(url, use_axe):
    """
    Executes the Pa11y command line tool on a given URL and returns the result.

    This function runs the Pa11y accessibility tool on a specified URL. It can
    optionally use the Axe runner for additional accessibility checks. The function
    ignores color contrast issues. The result is returned as a JSON object.

    Parameters:
    url (str): The URL to check for accessibility issues.
    use_axe (bool): If True, use the Axe runner for additional checks.

    Returns:
    dict: The JSON result from the Pa11y tool.
    """
    additional_args = ''
    if use_axe:
        additional_args = '--runner axe '

    # NOTE: "--ignore color-contrast" was added to temporarly solve issue #204
    command = (f"node node_modules{os.path.sep}pa11y{os.path.sep}bin{os.path.sep}pa11y.js "
                   f"--ignore color-contrast --reporter json {additional_args}{url}")
    with subprocess.Popen(command.split(), stdout=subprocess.PIPE) as process:
        output, _ = process.communicate(timeout=get_config_or_default('http_request_timeout') * 10)

        # If we fail to connect to website the result_dict should be None and we should end test
        if output is None or len(output) == 0:
            return None
        json_result = json.loads(output)
        return json_result
