# -*- coding: utf-8 -*-
import os
import sys
import json
import time
from models import Rating
from tests.utils import get_config_or_default, get_http_content, is_file_older_than, get_cache_path_for_rule

REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USE_CACHE = get_config_or_default('cache_when_possible')
CACHE_TIME_DELTA = get_config_or_default('cache_time_delta')

def run_test(global_translation, lang_code, url, googlePageSpeedApiKey, strategy, category, review_show_improvements_only, lighthouse_use_api):
    """
    perf = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=performance&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    a11y = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=accessibility&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    practise = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=best-practices&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    pwa = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=pwa&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    seo = https://www.googleapis.com/pagespeedonline/v5/runPagespeed?category=seo&strategy=mobile&url=YOUR-SITE&key=YOUR-KEY
    """

    json_content = get_json_result(
        lang_code, url, googlePageSpeedApiKey, strategy, category, lighthouse_use_api)

    # look for words indicating item is insecure
    insecure_strings = ['security', 'säkerhet',
                        'insecure', 'osäkra', 'unsafe', 'insufficient security', 'otillräckliga säkerhetskontroller', 'HTTPS']

    # look for words indicating items is related to standard
    standard_strings = ['gzip, deflate',
                        'Deprecated', 'Utfasade ', 'quirks-mode']

    return_dict = {}
    weight_dict = {}
    rating = Rating(global_translation, review_show_improvements_only)

    # Service score (0-100)
    score = json_content['categories'][category]['score']

    total_weight = 0
    for item in json_content['categories'][category]['auditRefs']:
        total_weight += item['weight']
        weight_dict[item['id']] = item['weight']

    # print('score', score)
    # nice = json.dumps(json_content, indent=4)
    # print('A', nice)
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
            item_title = '{0}'.format(
                json_content['audits'][item]['title'])
            displayValue = ''
            item_description = json_content['audits'][item]['description']
            if 'displayValue' in json_content['audits'][item]:
                displayValue = json_content['audits'][item]['displayValue']
            if local_score == 0:
                item_review = "- {0}".format(
                    global_translation(item_title))
            elif local_points == 5.0:
                item_review = "- {0}".format(
                    global_translation(item_title))
            else:
                item_review = "- {0}: {1}".format(
                    global_translation(item_title), displayValue)

            reviews.append([local_points - weight_dict[item],
                            item_review, local_points])

            for insecure_str in insecure_strings:
                if insecure_str in item_review or insecure_str in item_description:

                    local_rating = Rating(global_translation, review_show_improvements_only)
                    if local_score == 1:
                        local_rating.set_integrity_and_security(
                            5.0, '- {0}'.format(item_title))
                    else:
                        local_rating.set_integrity_and_security(
                            1.0, '- {0}'.format(item_title))
                    rating += local_rating
                    break
            for standard_str in standard_strings:
                if standard_str in item_review or standard_str in item_description:
                    local_rating = Rating(global_translation, review_show_improvements_only)
                    if local_score == 1:
                        local_rating.set_standards(
                            5.0, '- {0}'.format(item_title))
                    else:
                        local_rating.set_standards(
                            1.0, '- {0}'.format(item_title))
                    rating += local_rating
                    break

        except:
            # has no 'numericValue'
            #print(item, 'har inget värde')
            pass

    reviews.sort()
    for review_item in reviews:
        review_rating = Rating(global_translation, review_show_improvements_only)
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

    return (rating, return_dict)


def str_to_json(content, url):
    json_content = ''

    try:
        json_content = json.loads(content)
        if 'lighthouseResult' in json_content:
            json_content = json_content['lighthouseResult']

    except:  # might crash if checked resource is not a webpage
        print('Error! JSON failed parsing for the URL "{0}"\nMessage:\n{1}'.format(
            url, sys.exc_info()[0]))
        pass

    return json_content


def get_json_result(langCode, url, googlePageSpeedApiKey, strategy, category, lighthouse_use_api):
    check_url = url.strip()

    if lighthouse_use_api:
        pagespeed_api_request = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed?locale={2}&category={0}&url={1}&key={3}'.format(
            category, check_url, langCode, googlePageSpeedApiKey)
        get_content = ''

        # print('pagespeed_api_request: {0}'.format(pagespeed_api_request))

        try:
            get_content = get_http_content(pagespeed_api_request)
            json_content = str_to_json(get_content, check_url)
            return json_content
        except:  # breaking and hoping for more luck with the next URL
            print(
                'Error! Unfortunately the request for URL "{0}" failed, message:\n{1}'.format(
                    check_url, sys.exc_info()[0]))
            return  {}
    elif USE_CACHE:
        try:
            cache_key_rule = 'lighthouse-{0}'
            cache_path = get_cache_path_for_rule(url, cache_key_rule)

            if not os.path.exists(cache_path):
                os.makedirs(cache_path)

            result_file = os.path.join(cache_path, 'result.json')
            command = "node node_modules{2}lighthouse{2}cli{2}index.js --output json --output-path {3} --locale {1} --form-factor {0} --chrome-flags=\"--headless\" --quiet".format(
                strategy, langCode, os.path.sep, result_file)
            artifacts_file = os.path.join(cache_path, 'artifacts.json')
            if os.path.exists(result_file) and not is_file_older_than(result_file, CACHE_TIME_DELTA):
                file_created_timestamp = os.path.getctime(result_file)
                file_created_date = time.ctime(file_created_timestamp)
                print('Cached entry found from {0}, using it instead of calling website again.'.format(
                    file_created_date))
                with open(result_file, 'r', encoding='utf-8', newline='') as file:
                    return str_to_json('\n'.join(file.readlines()), check_url)
            elif os.path.exists(artifacts_file) and not is_file_older_than(artifacts_file, CACHE_TIME_DELTA):
                file_created_timestamp = os.path.getctime(artifacts_file)
                file_created_date = time.ctime(file_created_timestamp)
                print('Cached entry found from {0}, using it instead of calling website again.'.format(
                    file_created_date))
                command += " -A={0}".format(cache_path)
            else:
                command += " -GA={0} {1}".format(cache_path, check_url)

            import subprocess

            process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
            output, error = process.communicate(timeout=REQUEST_TIMEOUT * 10)
            with open(result_file, 'r', encoding='utf-8', newline='') as file:
                return str_to_json('\n'.join(file.readlines()), check_url)
        except:
            print(
                'Error! Unfortunately the request for URL "{0}" failed, message:\n{1}'.format(
                    check_url, sys.exc_info()[0]))
            return {}
    else:
        command = "node node_modules{4}lighthouse{4}cli{4}index.js {1} --output json --output-path stdout --locale {3} --only-categories {0} --form-factor {2} --chrome-flags=\"--headless\" --quiet".format(
            category, check_url, strategy, langCode, os.path.sep)

        import subprocess

        process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
        output, error = process.communicate(timeout=REQUEST_TIMEOUT * 10)

        get_content = output

        json_content = str_to_json(get_content, check_url)
        return json_content
