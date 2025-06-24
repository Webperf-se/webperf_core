# -*- coding: utf-8 -*-
import os
import subprocess
from datetime import datetime
import json
from tests.utils import get_translation,\
    get_http_content, flatten_issues_dict,\
    calculate_rating, get_domain
from helpers.setting_helper import get_config
from helpers.models import Rating

def run_test(global_translation, url):
    """
    Runs an accessibility test on a given URL and returns the results and ratings.

    This function runs the Pa11y accessibility tool on a specified URL. It calculates 
    the number of errors and unique error types, and then rates these errors. The function 
    returns the rating and the results of the accessibility test.

    Parameters:
    global_translation (function): Function to translate text to a global language.
    url (str): The URL to run the accessibility test on.

    Returns:
    tuple: A tuple containing the rating object and the results of the accessibility test.
    """

    use_axe = False
    json_result = get_pa11y_errors(url, use_axe)
    # If we fail to connect to website the result_dict will be None and we should end test
    if json_result is None:
        error_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        error_rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (error_rating, {'failed': True })

    num_errors = len(json_result)
    if num_errors == 0:
        use_axe = True
        json_result = get_pa11y_errors(url, use_axe)
        num_errors = len(json_result)

    num_errors = len(json_result)

    return_dict = {
        "groups": {}
    }

    domain = get_domain(url)
    return_dict['groups'][domain] = {
            'issues': {}
        }

    errors = json_result

    return_dict['groups'][domain]['issues'] = get_unique_errors(url, errors)
    return_dict['groups'][domain]['issues'] = flatten_issues_dict(return_dict['groups'][domain]['issues'])

    rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    rating = calculate_rating(global_translation, rating, return_dict)

    return (rating, return_dict)

def get_unique_errors(url, errors):
    """
    Gets unique errors from a list of many errors

    Parameters:
    errors (list): The list of errors.
    """
    unique_errors = {}
    for error in errors:
        if 'message' in error:
            err_mess = error['message']
            err_severity = error["type"]
            error_review = f'{err_mess} ({err_severity})'
            if error_review not in unique_errors:
                unique_errors[error_review] = {
                    "test": "pa11y",
                    "text": error_review,
                    "rule": error["code"],
                    "category": "a11y",
                    "severity": err_severity,
                    "subIssues": []
                    }

            unique_errors[error_review]["subIssues"].append({
                    "test": "pa11y",
                    "url": url,
                    "text": error_review,
                    "rule": error["code"],
                    "category": "a11y",
                    "severity": err_severity,
                    "extra": error
                    })
            
    return unique_errors

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
        output, _ = process.communicate(timeout=get_config('general.request.timeout') * 10)

        # If we fail to connect to website the result_dict should be None and we should end test
        if output is None or len(output) == 0:
            return None
        json_result = json.loads(output)
        return json_result
