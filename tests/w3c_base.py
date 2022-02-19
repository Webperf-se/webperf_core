# -*- coding: utf-8 -*-
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


def get_errors_from_service(headers, params, data=None):
    try:
        service_url = 'https://validator.w3.org/nu/'
        if data == None:
            print('data1:', data)
            request = requests.get(service_url, allow_redirects=True,
                                   headers=headers,
                                   timeout=request_timeout * 2,
                                   params=params)
        else:
            print('data2:', data)
            request = requests.get(service_url, allow_redirects=True,
                                   headers=headers,
                                   timeout=request_timeout * 2,
                                   params=params,
                                   data=data)

        # get JSON
        print('request:', request.text)
        response = json.loads(request.text)
        errors = response['messages']

        return errors
    except Exception:
        print('Unknown Error!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None
    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None


def get_errors_for_url(url):
    headers = {'user-agent': useragent}
    params = {'doc': url, 'out': 'json', 'level': 'error'}
    return get_errors_from_service(headers, params)


def get_errors_for_css(data):

    data = data.strip()

    headers = {'user-agent': useragent,
               'Content-Type': 'text/css; charset=utf-8'}
    params = {'showsource': 'yes', 'css': 'yes',
              'out': 'json', 'level': 'error'}
    return get_errors_from_service(headers, params, data.encode('utf-8'))


def get_source(url):
    try:
        headers = {'user-agent': useragent}
        request = requests.get(url, allow_redirects=True,
                               headers=headers,
                               timeout=request_timeout)

        # get source
        return request.text

    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None
