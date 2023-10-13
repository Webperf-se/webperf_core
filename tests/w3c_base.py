# -*- coding: utf-8 -*-
import subprocess
import sys
import json
import requests
import json
import config
from tests.utils import *

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
css_review_group_errors = config.css_review_group_errors
review_show_improvements_only = config.review_show_improvements_only


def get_errors(test_type, params):

    url = ''
    arg = ''
    test_arg = ''
    errors = list()

    if 'css' in params or test_type == 'css':
        test_arg = ' --css --skip-non-css'
    if 'html' in params or test_type == 'html':
        test_arg = ' --html --skip-non-html'

    if 'doc' in params:
        url = params['doc']

        if 'https://' not in url and 'http://' not in url:
            raise Exception(
                'Tested url must start with \'https://\' or \'http://\': {0}'.format(url))
        
        file_path = get_cache_path(url, True)

        arg = '--exit-zero-always{1} --stdout --format json --errors-only {0}'.format(
            file_path, test_arg)

    bashCommand = "java -jar vnu.jar {0}".format(arg)
    process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    # print('bashCommand', bashCommand)
    # print('- output', output)
    # print('- error', error)

    json_result = json.loads(output)
    if 'messages' in json_result:
        errors = json_result['messages']

    return errors


def get_errors_from_service(test_type, headers, params, data=None):
    errors = list()
    try:
        service_url = 'https://validator.w3.org/nu/'
        if data == None:
            request = requests.get(service_url, allow_redirects=True,
                                   headers=headers,
                                   timeout=request_timeout * 2,
                                   params=params)
        else:
            request = requests.post(service_url, allow_redirects=True,
                                    headers=headers,
                                    timeout=request_timeout,
                                    params=params,
                                    data=data)

        # get JSON
        response = json.loads(request.text)
        if 'messages' in response:
            errors = response['messages']
        return errors
    except Exception:
        print('Unknown Error!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return errors
    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return errors
