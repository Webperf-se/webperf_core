# -*- coding: utf-8 -*-
import os
import subprocess
from datetime import datetime
from functools import lru_cache
import json
from tests.utils import get_translation,\
    get_http_content, flatten_issues_dict,\
    calculate_rating, get_domain
from helpers.setting_helper import get_config
from helpers.models import Rating

# webperf_core language code -> axe-core locale file (node_modules/axe-core/locales).
# Languages missing here keep axe's English rule texts.
AXE_LOCALES = {
    'sv': 'sv',
    'da': 'da',
    'no': 'nb'
}

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
            'issues': {},
            # pa11y only checks accessibility. Listing the category makes a page
            # where pa11y finds nothing get an a11y rating (5.0) instead of none.
            'categories': ['a11y']
        }

    errors = json_result

    language = get_config('general.language')
    try:
        local_translation = get_translation('a11y_pa11y', language)
    except FileNotFoundError:
        local_translation = get_translation('a11y_pa11y', 'en')

    return_dict['groups'][domain]['issues'] = get_unique_errors(
        url, errors, global_translation, local_translation, language)
    return_dict['groups'][domain]['issues'] = flatten_issues_dict(return_dict['groups'][domain]['issues'])

    rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    rating = calculate_rating(global_translation, rating, return_dict)

    return (rating, return_dict)

def get_unique_errors(url, errors, global_translation, local_translation, language):
    """
    Gets unique errors from a list of many errors

    Parameters:
    url (str): The tested URL.
    errors (list): The list of errors.
    global_translation (function): Translation for webperf-core strings.
    local_translation (function): Translation for a11y_pa11y strings.
    language (str): Language code, used to pick axe's rule texts.
    """
    unique_errors = {}
    for error in errors:
        if 'message' in error:
            err_mess = get_message(error, language)
            err_severity = get_severity(error)
            severity_text = global_translation(f"TEXT_SEVERITY_{err_severity.upper()}")
            error_review = f'{err_mess} ({severity_text})'
            if needs_further_review(error):
                note = local_translation('TEXT_REVIEW_NEEDS_MANUAL_REVIEW')
                error_review = f'{error_review}\n  {note}'
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

def needs_further_review(error):
    """
    True when axe could not decide on the finding.

    axe puts such findings in its "incomplete" bucket. pa11y merges those
    into the result list with the same type as confirmed violations and
    only marks them with runnerExtras.needsFurtherReview.

    Parameters:
    error (dict): One pa11y result.
    """
    return error.get("runnerExtras", {}).get("needsFurtherReview", False)

def get_severity(error):
    """
    Gets the severity to rate a pa11y error with.

    A finding that needs a human to confirm it (see needs_further_review)
    is rated as a notice (no deduction) instead of an error (10 points).
    It is still listed in the review text.

    Parameters:
    error (dict): One pa11y result.

    Returns:
    str: Severity, one of pa11y's types (error, warning, notice).
    """
    severity = error["type"]
    if needs_further_review(error) and severity == "error":
        return "notice"
    return severity

@lru_cache(maxsize=None)
def get_axe_rule_texts(language):
    """
    Loads the rule texts axe-core ships for a language.

    Parameters:
    language (str): webperf_core language code.

    Returns:
    dict: Rule id -> {'help': ..., 'description': ...}, empty when
    axe-core has no locale for the language.
    """
    locale = AXE_LOCALES.get(language)
    if locale is None:
        return {}
    path = os.path.join('node_modules', 'axe-core', 'locales', f'{locale}.json')
    try:
        with open(path, encoding='utf-8') as file:
            return json.load(file).get('rules', {})
    except (OSError, ValueError):
        return {}

def get_message(error, language):
    """
    Gets the message for a pa11y error, in the given language when possible.

    pa11y's axe runner builds the message as "<help> (<helpUrl>)" from axe's
    English texts. For languages axe-core has a locale for, the help text
    is swapped for the translated one. HTML CodeSniffer has no translations,
    so its messages are returned as they are.

    Parameters:
    error (dict): One pa11y result.
    language (str): webperf_core language code.

    Returns:
    str: The message.
    """
    message = error['message']
    if error.get('runner') != 'axe':
        return message
    rule = get_axe_rule_texts(language).get(error.get('code'))
    if rule is None or 'help' not in rule:
        return message
    help_url = error.get('runnerExtras', {}).get('helpUrl')
    if help_url:
        return f"{rule['help']} ({help_url})"
    return rule['help']

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
