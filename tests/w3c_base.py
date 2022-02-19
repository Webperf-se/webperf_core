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
w3c_use_website = config.w3c_use_website


def get_errors(headers, params, data=None):
    if w3c_use_website:
        return get_errors_from_service(headers, params, data)
    else:
        return get_errors_from_npm(params, data)


def get_errors_from_npm(params, data=None):

    url = ''
    arg = ''
    css_only = ''
    errors = list()

    if 'css' in params:
        css_only = ' -skip-non-css --css'

    if 'doc' in params:
        url = params['doc']
        arg = '--exit-zero-always{1} --errors-only {0}'.format(
            url, css_only)
    else:
        arg = '--exit-zero-always{1} --errors-only \'{0}\''.format(
            data, css_only)

    bashCommand = "java -jar vnu {0}".format(arg)
    process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    json_result = json.loads(output)
    if 'messages' in json_result:
        errors = json_result['messages']

    return errors


def get_errors_from_service(headers, params, data=None):
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
