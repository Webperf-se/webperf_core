# -*- coding: utf-8 -*-
import os
import subprocess
import json
from tests.utils import get_cache_path, get_config_or_default, has_cache_file, set_cache_file

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
CSS_REVIEW_GROUP_ERRORS = get_config_or_default('css_review_group_errors')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
USE_CACHE = get_config_or_default('cache_when_possible')
CACHE_TIME_DELTA = get_config_or_default('cache_time_delta')


def get_errors(test_type, params):

    url = ''
    arg = ''
    test_arg = ''
    errors = list()
    is_html = False

    if 'css' in params or test_type == 'css':
        test_arg = ' --css --skip-non-css'
    if 'html' in params or test_type == 'html':
        test_arg = ' --html --skip-non-html'
        is_html = True

    if 'doc' in params:
        url = params['doc']

        if 'https://' not in url and 'http://' not in url:
            raise Exception(
                'Tested url must start with \'https://\' or \'http://\': {0}'.format(url))
        
        file_path = get_cache_path(url, True)
        if is_html:
            html_file_ending_fix = file_path.replace('.cache', '.cache.html')
            if has_cache_file(url, True, CACHE_TIME_DELTA) and not os.path.exists(html_file_ending_fix):
                os.rename(file_path, html_file_ending_fix)
            file_path = html_file_ending_fix

        arg = '--exit-zero-always{1} --stdout --format json --errors-only {0}'.format(
            file_path, test_arg)

    bashCommand = "java -jar vnu.jar {0}".format(arg)
    process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
    output, error = process.communicate(timeout=REQUEST_TIMEOUT * 10)

    json_result = json.loads(output)
    if 'messages' in json_result:
        errors = json_result['messages']

    return errors

def identify_files(filename):
    data = {
        'htmls': [],
        'elements': [],
        'attributes': [],
        'resources': []
    }

    with open(filename) as json_input_file:
        har_data = json.load(json_input_file)

        if 'log' in har_data:
            har_data = har_data['log']

        req_index = 1
        for entry in har_data["entries"]:
            req = entry['request']
            res = entry['response']
            req_url = req['url']

            if 'content' not in res:
                continue
            if 'mimeType' not in res['content']:
                continue
            if 'size' not in res['content']:
                continue
            if res['content']['size'] <= 0:
                continue

            if 'html' in res['content']['mimeType']:
                if not has_cache_file(req_url, True, CACHE_TIME_DELTA):
                    set_cache_file(req_url, res['content']['text'], True)
                data['htmls'].append({
                    'url': req_url,
                    'content': res['content']['text'],
                    'index': req_index
                    })
            elif 'css' in res['content']['mimeType']:
                if not has_cache_file(req_url, True, CACHE_TIME_DELTA):
                    set_cache_file(req_url, res['content']['text'], True)
                data['resources'].append({
                    'url': req_url,
                    'content': res['content']['text'],
                    'index': req_index
                    })
            req_index += 1

    return data
