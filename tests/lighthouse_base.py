# -*- coding: utf-8 -*-
import os
import json
import time
from datetime import datetime
import subprocess
from models import Rating
from tests.utils import get_config_or_default,\
                        get_http_content,\
                        is_file_older_than,\
                        get_cache_path_for_rule,\
                        get_translation

# DEFAULTS
GOOGLEPAGESPEEDAPIKEY = get_config_or_default('googlePageSpeedApiKey')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
LIGHTHOUSE_USE_API = get_config_or_default('lighthouse_use_api')
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USE_CACHE = get_config_or_default('cache_when_possible')
CACHE_TIME_DELTA = get_config_or_default('cache_time_delta')

def get_lighthouse_translations(module_name, lang_code, global_translation):
    local_translation = get_translation(module_name, lang_code)

    return {
        'code': lang_code,
        'module': local_translation,
        'global': global_translation
    }

def run_test(url, strategy, category, silance, lighthouse_translations):
    """
    https://www.googleapis.com/pagespeedonline/v5/runPagespeed?
        category=(performance/accessibility/best-practices/pwa/seo)
        &strategy=mobile
        &url=YOUR-SITE&
        key=YOUR-KEY
    """

    global_translation = lighthouse_translations['global']
    local_translation = lighthouse_translations['module']
    lang_code = lighthouse_translations['code']

    if not silance:
        print(local_translation('TEXT_RUNNING_TEST'))

        print(global_translation('TEXT_TEST_START').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))


    json_content = get_json_result(
        lang_code, url, strategy, category, GOOGLEPAGESPEEDAPIKEY)

    # look for words indicating item is insecure
    insecure_strings = ['security', 'säkerhet',
                        'insecure', 'osäkra', 'unsafe',
                        'insufficient security', 'otillräckliga säkerhetskontroller',
                        'HTTPS']

    # look for words indicating items is related to standard
    standard_strings = ['gzip, deflate',
                        'Deprecated', 'Utfasade ', 'quirks-mode']

    return_dict = {}
    weight_dict = {}
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    # Service score (0-100)
    score = json_content['categories'][category]['score']

    total_weight = 0
    for item in json_content['categories'][category]['auditRefs']:
        total_weight += item['weight']
        weight_dict[item['id']] = item['weight']

    # change it to % and convert it to a 1-5 grading
    points = 5.0 * float(score)
    reviews = []

    for item in json_content['audits'].keys():
        try:
            if 'numericValue' in json_content['audits'][item]:
                return_dict[item] = json_content['audits'][item]['numericValue']

            local_score = float(
                json_content['audits'][item]['score'])

            local_points = 5.0 * local_score
            if local_points < 1.0:
                local_points = 1
            if local_points >= 4.95:
                local_points = 5.0

            item_review = ''
            item_title = f'{json_content['audits'][item]['title']}'
            display_value = ''
            item_description = json_content['audits'][item]['description']
            if 'displayValue' in json_content['audits'][item]:
                display_value = json_content['audits'][item]['displayValue']
            if local_score == 0:
                item_review = f"- {global_translation(item_title)}"
            elif local_points == 5.0:
                item_review = f"- {global_translation(item_title)}"
            else:
                item_review = f"- {global_translation(item_title)}: {display_value}"

            reviews.append([local_points - weight_dict[item],
                            item_review, local_points])

            for insecure_str in insecure_strings:
                if insecure_str in item_review or insecure_str in item_description:

                    local_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    if local_score == 1:
                        local_rating.set_integrity_and_security(
                            5.0, f'- {item_title}')
                    else:
                        local_rating.set_integrity_and_security(
                            1.0, f'- {item_title}')
                    rating += local_rating
                    break
            for standard_str in standard_strings:
                if standard_str in item_review or standard_str in item_description:
                    local_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    if local_score == 1:
                        local_rating.set_standards(
                            5.0, '- {item_title}')
                    else:
                        local_rating.set_standards(
                            1.0, '- {item_title}')
                    rating += local_rating
                    break

        except:
            # has no 'numericValue'
            #print(item, 'har inget värde')
            pass

    reviews.sort()
    for review_item in reviews:
        review_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        review_rating.set_overall(review_item[2], review_item[1])
        rating += review_rating
    review = rating.overall_review

    if category == 'performance':
        rating.set_overall(points)
        rating.set_performance(points)
        rating.performance_review = review
    elif category == 'accessibility':
        rating.set_overall(points)
        rating.set_a11y(points)
        rating.a11y_review = review
    else:
        rating.set_overall(points)
        rating.overall_review = review
    rating.overall_count = 1

    review = rating.overall_review
    points = rating.get_overall()
    if points >= 5.0:
        review = local_translation("TEXT_REVIEW_VERY_GOOD")
    elif points >= 4.0:
        review = local_translation("TEXT_REVIEW_IS_GOOD")
    elif points >= 3.0:
        review = local_translation("TEXT_REVIEW_IS_OK")
    elif points > 1.0:
        review = local_translation("TEXT_REVIEW_IS_BAD")
    elif points <= 1.0:
        review = local_translation("TEXT_REVIEW_IS_VERY_BAD")
    rating.overall_review = review


    if not silance:
        print(global_translation('TEXT_TEST_END').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)


def str_to_json(content, url):
    json_content = {}

    try:
        json_content = json.loads(content)
        if 'lighthouseResult' in json_content:
            json_content = json_content['lighthouseResult']

    except json.JSONDecodeError:
        # might crash if checked resource is not a webpage
        print(
            (
                "Error! Failed to decode JSON for: content:\r\n"
                f"\turl: {url}\r\n"
                f"\tcontent: {content}\r\n"
                )
            )

    return json_content

def get_json_result_from_api(lang_code, url, category, google_pagespeed_apikey):
    pagespeed_api_request = (
        'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
        f'?locale={lang_code}'
        f'&category={category}'
        f'&url={url}'
        f'&key={google_pagespeed_apikey}')
    get_content = ''

    get_content = get_http_content(pagespeed_api_request)
    json_content = str_to_json(get_content, url)
    return json_content

def get_json_result_using_caching(lang_code, url, strategy):
    cache_key_rule = 'lighthouse-{0}'
    cache_path = get_cache_path_for_rule(url, cache_key_rule)

    if not os.path.exists(cache_path):
        os.makedirs(cache_path)

    result_file = os.path.join(cache_path, 'result.json')
    command = (
        f"node node_modules{os.path.sep}lighthouse{os.path.sep}cli{os.path.sep}index.js"
        f" --output json --output-path {result_file} --locale {lang_code}"
        f" --form-factor {strategy} --chrome-flags=\"--headless\" --quiet")

    artifacts_file = os.path.join(cache_path, 'artifacts.json')
    if os.path.exists(result_file) and \
        not is_file_older_than(result_file, CACHE_TIME_DELTA):

        file_created_timestamp = os.path.getctime(result_file)
        file_created_date = time.ctime(file_created_timestamp)
        print((f'Cached entry found from {file_created_date},'
            ' using it instead of calling website again.'))
        with open(result_file, 'r', encoding='utf-8', newline='') as file:
            return str_to_json('\n'.join(file.readlines()), url)
    elif os.path.exists(artifacts_file) and \
        not is_file_older_than(artifacts_file, CACHE_TIME_DELTA):

        file_created_timestamp = os.path.getctime(artifacts_file)
        file_created_date = time.ctime(file_created_timestamp)
        print((
            f'Cached entry found from {file_created_date},'
            ' using it instead of calling website again.'))
        command += f" -A={cache_path}"
    else:
        command += f" -GA={cache_path} {url}"

    with subprocess.Popen(command.split(), stdout=subprocess.PIPE) as process:
        _, _ = process.communicate(timeout=REQUEST_TIMEOUT * 10)
        with open(result_file, 'r', encoding='utf-8', newline='') as file:
            return str_to_json('\n'.join(file.readlines()), url)



def get_json_result(lang_code, url, strategy, category, google_pagespeed_apikey):
    json_content = {}
    check_url = url.strip()

    lighthouse_use_api = google_pagespeed_apikey is not None and google_pagespeed_apikey != ''

    if lighthouse_use_api:
        return get_json_result_from_api(lang_code, check_url, category, google_pagespeed_apikey)

    if USE_CACHE:
        return get_json_result_using_caching(lang_code, check_url, strategy)

    command = (
        f"node node_modules{os.path.sep}lighthouse{os.path.sep}cli{os.path.sep}index.js"
        f" {check_url} --output json --output-path stdout --locale {lang_code}"
        f" --only-categories {category} --form-factor {strategy}"
        " --chrome-flags=\"--headless\" --quiet")

    with subprocess.Popen(command.split(), stdout=subprocess.PIPE) as process:
        output, _ = process.communicate(timeout=REQUEST_TIMEOUT * 10)
        get_content = output
        json_content = str_to_json(get_content, check_url)

    return json_content
