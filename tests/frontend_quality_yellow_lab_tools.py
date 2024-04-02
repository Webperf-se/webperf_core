# -*- coding: utf-8 -*-
import os
import time
from datetime import datetime
import json
import requests
from tests.utils import get_config_or_default, get_http_content, get_translation
from models import Rating

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
time_sleep = get_config_or_default('WEBBKOLL_SLEEP')
if time_sleep < 5:
    time_sleep = 5

YLT_SERVER_ADDRESS = get_config_or_default('YLT_SERVER_ADDRESS')
YLT_USE_API = get_config_or_default('YLT_USE_API')

def run_test(global_translation, lang_code, url, device='phone'):
    """
    Analyzes URL with Yellow Lab Tools docker image.
    Devices might be; phone, tablet, desktop
    """

    local_translation = get_translation('frontend_quality_yellow_lab_tools', lang_code)

    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    print(local_translation("TEXT_RUNNING_TEST"))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    if YLT_USE_API:
        r = requests.post('{0}/api/runs'.format(YLT_SERVER_ADDRESS),
                          data={'url': url, "waitForResponse": 'true', 'device': device})

        result_url = r.url

        running_info = json.loads(r.text)
        test_id = running_info['runId']

        running_status = 'running'
        while running_status == 'running':
            running_json = get_http_content(
                '{0}/api/runs/{1}'.format(YLT_SERVER_ADDRESS, test_id))
            running_info = json.loads(running_json)
            running_status = running_info['status']['statusCode']
            time.sleep(time_sleep)

        result_url = '{0}/api/results/{1}?exclude=toolsResults'.format(
            YLT_SERVER_ADDRESS, test_id)
        result_json = get_http_content(result_url)
    else:
        import subprocess

        command = "node node_modules{1}yellowlabtools{1}bin{1}cli.js {0}".format(
            url, os.path.sep)
        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output, _ = process.communicate(timeout=REQUEST_TIMEOUT * 10)

        result_json = output

    #print('result_url', result_url)

    result_dict = json.loads(result_json)

    #print('result_json', result_json)

    return_dict = {}
    yellow_lab = 0

    for key in result_dict['scoreProfiles']['generic'].keys():
        if key == 'globalScore':
            yellow_lab = result_dict['scoreProfiles']['generic'][key]

    review = ''
    for key in result_dict['scoreProfiles']['generic']['categories'].keys():

        review += '- ' + global_translation('TEXT_TEST_REVIEW_RATING_ITEM').format(local_translation(result_dict['scoreProfiles']['generic']['categories'][key]['label']), to_points(
            result_dict['scoreProfiles']['generic']['categories'][key]['categoryScore']))

    points = to_points(yellow_lab)

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

    try:
        for rule_key in result_dict['rules'].keys():
            rule = result_dict['rules'][rule_key]
            rule_score = to_points(rule['score'])
            #rule_value = rule['value']
            #rule_is_bad = rule['bad']
            #rule_is_abnormal = rule['abnormal']

            rule_label = '- {0}'.format(
                local_translation(rule['policy']['label']))

            matching_one_category_or_more = False
            # only do stuff for rules we know how to place in category
            if rule_key in performance_keys:
                matching_one_category_or_more = True
                rule_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                rule_rating.set_performance(
                    rule_score, rule_label)
                rating += rule_rating

            if rule_key in security_keys:
                matching_one_category_or_more = True
                rule_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                rule_rating.set_integrity_and_security(
                    rule_score, rule_label)
                rating += rule_rating

            if rule_key in standards_keys:
                matching_one_category_or_more = True
                rule_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                rule_rating.set_standards(
                    rule_score, rule_label)
                rating += rule_rating

            # if not matching_one_category_or_more:
            #     rule_rating = Rating(global_translation, review_show_improvements_only)
            #     rule_rating.over(
            #                 rule_score, rule_label)
            #     rating += rule_rating
            #     print('unmtached rule: {0}: {1}'.format(
            #        key, rule_score))

    except:
        do = None

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


def to_points(value):
    points = 5.0 * (int(value) / 100)
    if points > 5.0:
        points = 5.0
    if points < 1.0:
        points = 1.0
    points = float("{0:.2f}".format(points))
    return points
