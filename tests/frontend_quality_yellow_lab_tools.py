# -*- coding: utf-8 -*-
import os
from datetime import datetime
import json
import subprocess
from tests.utils import get_translation
from helpers.setting_helper import get_config
from models import Rating

def run_test(global_translation, lang_code, url):
    """
    Analyzes URL with Yellow Lab Tools docker image.
    Devices might be; phone, tablet, desktop
    """

    local_translation = get_translation('frontend_quality_yellow_lab_tools', lang_code)

    rating = Rating(global_translation, get_config('review_show_improvements_only'))

    print(local_translation("TEXT_RUNNING_TEST"))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    result_dict = get_ylt_result(url)
    # If we fail to connect to website the result_dict will be None and we should end test
    if result_dict is None:
        rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (rating, {'failed': True })

    return_dict = {}
    yellow_lab = 0

    for key in result_dict['scoreProfiles']['generic'].keys():
        if key == 'globalScore':
            yellow_lab = result_dict['scoreProfiles']['generic'][key]

    review = ''
    for key in result_dict['scoreProfiles']['generic']['categories'].keys():

        review += '- ' + global_translation('TEXT_TEST_REVIEW_RATING_ITEM').format(
            local_translation(
                result_dict['scoreProfiles']['generic']['categories'][key]['label']
                ), to_points(
            result_dict['scoreProfiles']['generic']['categories'][key]['categoryScore'])
            )

    points = to_points(yellow_lab)

    rating += add_category_ratings(global_translation, local_translation, result_dict)

    review_overall = ''
    if points >= 5:
        review_overall = local_translation("TEXT_WEBSITE_IS_VERY_GOOD")
    elif points >= 4:
        review_overall = local_translation("TEXT_WEBSITE_IS_GOOD")
    elif points >= 3:
        review_overall = local_translation("TEXT_WEBSITE_IS_OK")
    elif points >= 2:
        review_overall = local_translation("TEXT_WEBSITE_IS_BAD")
    elif points <= 1:
        review_overall = local_translation("TEXT_WEBSITE_IS_VERY_BAD")

    rating.set_overall(points, review_overall)

    rating.overall_review = rating.overall_review + review

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)

def get_ylt_result(url):
    """
    This function retrieves the Yellow Lab Tools (YLT) analysis result for a given URL and device.
    
    Parameters:
    url (str): The URL of the webpage to analyze.

    Returns:
    dict: The result of the YLT analysis in dictionary format.
    """
    result_json = None

    command = (
        f"node node_modules{os.path.sep}yellowlabtools{os.path.sep}bin"
        f"{os.path.sep}cli.js {url}")
    with subprocess.Popen(command.split(), stdout=subprocess.PIPE) as process:
        output, _ = process.communicate(
            timeout=get_config('http_request_timeout') * 10)
        result_json = output

    # If we fail to connect to website the result_dict should be None and we should end test
    if result_json is None or len(result_json) == 0:
        return None

    result_dict = json.loads(result_json)
    return result_dict

def add_category_ratings(global_translation, local_translation, result_dict):
    """
    This function adds category ratings to the Yellow Lab Tools (YLT) analysis result.
    
    Parameters:
    global_translation (function): Function to translate global terms.
    local_translation (function): Function to translate local terms.
    result_dict (dict): The YLT analysis result in dictionary format.

    Returns:
    Rating: The rating object with performance, integrity and security, and standards ratings.
    """
    performance_keys = ['totalWeight', 'imageOptimization',
                        'imagesTooLarge', 'compression', 'fileMinification',
                        'totalRequests', 'domains', 'notFound', 'identicalFiles',
                        'lazyLoadableImagesBelowTheFold', 'iframesCount', 'scriptDuration',
                        'DOMaccesses', 'eventsScrollBound', 'documentWriteCalls',
                        'synchronousXHR', 'cssRules', 'fontsCount',
                        'heavyFonts', 'nonWoff2Fonts', 'oldHttpProtocol',
                        'oldTlsProtocol', 'closedConnections', 'cachingNotSpecified',
                        'cachingDisabled', 'cachingTooShort']
    security_keys = ['jQueryVersion', 'oldTlsProtocol']
    standards_keys = ['compression', 'notFound', 'DOMidDuplicated',
                      'cssParsingErrors', 'oldTlsProtocol']

    rating = Rating(global_translation, get_config('review_show_improvements_only'))
    for rule_key, rule in result_dict['rules'].items():
        if 'score' not in rule:
            continue
        rule_score = to_points(rule['score'])

        if 'policy' not in rule:
            continue

        if 'label' not in rule['policy']:
            continue

        rule_label = f'- {local_translation(rule['policy']['label'])}'

        # only do stuff for rules we know how to place in category
        if rule_key in performance_keys:
            rule_rating = Rating(
                global_translation,
                get_config('review_show_improvements_only'))
            rule_rating.set_performance(
                rule_score, rule_label)
            rating += rule_rating

        if rule_key in security_keys:
            rule_rating = Rating(
                global_translation,
                get_config('review_show_improvements_only'))
            rule_rating.set_integrity_and_security(
                rule_score, rule_label)
            rating += rule_rating

        if rule_key in standards_keys:
            rule_rating = Rating(
                global_translation,
                get_config('review_show_improvements_only'))
            rule_rating.set_standards(
                rule_score, rule_label)
            rating += rule_rating
    return rating


def to_points(value):
    """
    This function converts a value to a point scale between 1.0 and 5.0.
    
    Parameters:
    value (int): The value to be converted to points.

    Returns:
    float: The value converted to points, rounded to two decimal places.
    """
    points = 5.0 * (int(value) / 100)
    points = min(points, 5.0)
    points = max(points, 1.0)
    points = float(f"{points:.2f}")
    return points
