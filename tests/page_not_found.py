# -*- coding: utf-8 -*-
import json
import os
import urllib
from urllib.parse import ParseResult, urlparse, urlunparse
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import uuid
from helpers.models import Rating
from helpers.browser_helper import get_chromium_browser
from tests.utils import get_guid,\
    get_http_content, get_translation, is_file_older_than,\
    change_url_to_test_url
from tests.sitespeed_base import get_result, get_result_using_no_cache,\
    get_sanitized_browsertime
from helpers.setting_helper import get_config, set_runtime_config_only

def get_webperf_json(filename):
    if not os.path.exists(filename):
        return None

    data_str = get_sanitized_browsertime(filename)
    return json.loads(data_str)

def create_webperf_json(url):
    # We don't need extra iterations for what we are using it for
    sitespeed_iterations = 1
    sitespeed_arg = (
            f'--shm-size=1g -b {get_chromium_browser()} '
            '--plugins.add plugin-html '
            '--plugins.add plugin-css '
            '--plugins.add plugin-javascript '
            '--plugins.add plugin-accessibility-statement '
            '--plugins.add plugin-pagenotfound '
            '--plugins.add plugin-webperf-core '
            '--plugins.remove screenshot --plugins.remove html --plugins.remove metrics '
            '--browsertime.screenshot false --screenshot false --screenshotLCP false '
            '--browsertime.screenshotLCP false --chrome.cdp.performance false '
            '--browsertime.chrome.timeline false --videoParams.createFilmstrip false '
            '--visualMetrics false --visualMetricsPerceptual false '
            '--visualMetricsContentful false --browsertime.headless true '
            '--utc true '
            '--browsertime.chrome.args ignore-certificate-errors '
            f'-n {sitespeed_iterations}')
    if get_config('tests.sitespeed.xvfb'):
        sitespeed_arg += ' --xvfb'

    (folder, filename) = get_result(url,
        get_config('tests.sitespeed.docker.use'),
        sitespeed_arg,
        get_config('tests.sitespeed.timeout'))

    # filename =  os.path.join(folder, 'webperf-core.json')
    data = get_webperf_json(filename)
    return data

def run_test(global_translation, org_url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    rating = Rating(global_translation)
    result_dict = {}

    local_translation = get_translation('page_not_found', get_config('general.language'))

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    result_dict = create_webperf_json(org_url)
    # TODO: Handle where result_dict is None
    # TODO: Handle when unable to access website

    severity_order = {"critical": 1, "error": 2, "warning": 3, "info": 4}
    issues_standard =[]
    issues_security = []
    issues_a11y = []
    issues_performance = []
    for group_name, info in result_dict["groups"].items():
        for issue in info["issues"]:
            if get_config('general.review.improve-only') and issue["severity"] == "resolved":
                continue
            if issue['category'] == 'standard':
                issues_standard.append(f"{issue['rule']} ({issue['severity']})")
            elif issue['category'] == 'security':
                issues_security.append(f"{issue['rule']} ({issue['severity']})")
            elif issue['category'] == 'a11y':
                issues_a11y.append(f"{issue['rule']} ({issue['severity']})")
            elif issue['category'] == 'performance':
                issues_performance.append(f"{issue['rule']} ({issue['severity']})")

        if 'overall' in info["score"]:
            overall = (info["score"]["overall"] / 100) * 5
            rating.set_overall(overall)
        if 'standard' in info["score"]:
            standard = (info["score"]["standard"] / 100) * 5
            rating.set_standards(standard)
            rating.standards_review = "\n".join([f"- {item}" for item in issues_standard]) + "\n"
        if 'security' in info["score"]:
            security = (info["score"]["security"] / 100) * 5
            rating.set_integrity_and_security(security)
            rating.integrity_and_security_review = "\n".join([f"- {item}" for item in issues_security]) + "\n"
        if 'a11y' in info["score"]:
            a11y = (info["score"]["a11y"] / 100) * 5
            rating.set_a11y(a11y)
            rating.a11y_review = "\n".join([f"- {item}" for item in issues_a11y]) + "\n"
        if 'performance' in info["score"]:
            performance = (info["score"]["performance"] / 100) * 5
            rating.set_performance(performance)
            rating.performance_review = "\n".join([f"- {item}" for item in issues_performance]) + "\n"

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)


