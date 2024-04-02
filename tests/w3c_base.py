# -*- coding: utf-8 -*-
import os
import subprocess
import json
from tests.utils import get_cache_path_for_file, get_config_or_default, has_cache_file, set_cache_file

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
CSS_REVIEW_GROUP_ERRORS = get_config_or_default('css_review_group_errors')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
USE_CACHE = get_config_or_default('cache_when_possible')
CACHE_TIME_DELTA = get_config_or_default('cache_time_delta')


def get_errors(test_type, params):
    """
    This function takes a test type and parameters as input and
    returns any errors found during the test.

    The function checks if the test type is 'css' or 'html' and
    sets the test arguments accordingly.
    It then checks if a document URL is provided in the parameters.
    If the URL does not start with 'https://' or 'http://', it raises a ValueError.
    It then checks if the file is cached and if not, it caches the file.
    It then runs a command using the vnu.jar validator and returns any errors found.

    Parameters:
    test_type (str): The type of the test to be run. It can be 'css' or 'html'.
    params (dict): A dictionary containing the parameters for the test.
    It should contain a 'doc' key with the URL of the document to be tested.

    Returns:
    list: A list of dictionaries where each dictionary represents an error message.
    """

    url = ''
    arg = ''
    test_arg = ''
    errors = []
    is_html = False

    if 'css' in params or test_type == 'css':
        test_arg = ' --css --skip-non-css'
    if 'html' in params or test_type == 'html':
        test_arg = ' --html --skip-non-html'
        is_html = True

    if 'doc' in params:
        url = params['doc']

        if 'https://' not in url and 'http://' not in url:
            raise ValueError(
                f'Tested url must start with \'https://\' or \'http://\': {url}')

        file_path = get_cache_path_for_file(url, True)
        if is_html:
            html_file_ending_fix = file_path.replace('.cache', '.cache.html')
            if has_cache_file(url, True, CACHE_TIME_DELTA) \
                    and not os.path.exists(html_file_ending_fix):
                os.rename(file_path, html_file_ending_fix)
            file_path = html_file_ending_fix

        arg = f'--exit-zero-always{test_arg} --stdout --format json --errors-only {file_path}'

    command = f'java -jar vnu.jar {arg}'
    with subprocess.Popen(command.split(), stdout=subprocess.PIPE) as process:
        output, _ = process.communicate(timeout=REQUEST_TIMEOUT * 10)

        json_result = json.loads(output)
        if 'messages' in json_result:
            errors = json_result['messages']

    return errors

def identify_files(filename):
    """
    This function takes a filename as input and identifies different types of files in the HAR data.

    The function reads the HAR data from the file, iterates over the entries,
    and categorizes them into HTML and CSS files.
    It also checks if the file is already cached and if not, it caches the file.

    Parameters:
    filename (str): The name of the file containing the HAR data.

    Returns:
    dict: A dictionary containing categorized file data.
    The dictionary has four keys - 'htmls', 'elements', 'attributes', and 'resources'.
    Each key maps to a list of dictionaries where each dictionary contains:
    - 'url',
    - 'content'
    - 'index'
    of the file.
    """

    data = {
        'htmls': [],
        'elements': [],
        'attributes': [],
        'resources': []
    }

    with open(filename, encoding='utf-8') as json_input_file:
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
