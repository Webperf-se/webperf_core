# -*- coding: utf-8 -*-
import json
import urllib
import urllib.parse

from helpers.data_helper import append_domain_entry
from helpers.http_header_helper import append_data_from_response_headers
from helpers.mime_type_helper import append_data_from_mimetypes

def get_data_from_sitespeed(filename, org_domain):
    result = {
        'visits': 0
    }

    if filename == '':
        return result

    # Fix for content having unallowed chars
    with open(filename, encoding='utf-8') as json_input_file:
        har_data = json.load(json_input_file)

        if 'log' in har_data:
            har_data = har_data['log']

        for entry in har_data["entries"]:
            req = entry['request']
            res = entry['response']
            req_url = req['url']

            o = urllib.parse.urlparse(req_url)
            req_domain = o.hostname

            append_domain_entry(req_domain, 'schemes', o.scheme.upper(), result)
            append_domain_entry(req_domain, 'urls', req_url, result)

            if 'httpVersion' in req and req['httpVersion'] != '':
                http_version = req['httpVersion'].replace('h2', 'HTTP/2')
                http_version = http_version.replace('h3', 'HTTP/3')
                http_version = http_version.upper()
                append_domain_entry(req_domain, 'protocols', http_version, result)

            if 'httpVersion' in res and res['httpVersion'] != '':
                http_version = res['httpVersion'].replace('h2', 'HTTP/2')
                http_version = http_version.replace('h3', 'HTTP/3')
                http_version = http_version.upper()
                append_domain_entry(req_domain, 'protocols', http_version, result)

            if 'serverIPAddress' in entry:
                if ':' in entry['serverIPAddress']:
                    append_domain_entry(req_domain, 'ip-versions', 'IPv6', result)
                else:
                    append_domain_entry(req_domain, 'ip-versions', 'IPv4', result)

            append_data_from_response_headers(
                res['headers'],
                req_url,
                org_domain,
                req_domain,
                result)

            append_data_from_mimetypes(res, req_url, org_domain, req_domain, result)

    result['visits'] = 1
    return result
