# -*- coding: utf-8 -*-
import os
from datetime import datetime
import re
import urllib
import urllib.parse
import json
import hashlib
import base64
# https://docs.python.org/3/library/urllib.parse.html
import dns.name
import dns.query
import dns.dnssec
import dns.message
import dns.resolver
import dns.rdatatype
from helpers.csp_helper import default_csp_result_object, handle_csp_data, rate_csp
from helpers.tls_helper import check_tls_versions, rate_transfer_layers
from models import Rating
from tests.utils import change_url_to_test_url, dns_lookup,\
    get_translation, merge_dicts, get_config_or_default
from tests.sitespeed_base import get_result

# DEFAULTS
SITESPEED_TIMEOUT = get_config_or_default('sitespeed_timeout')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
SITESPEED_USE_DOCKER = get_config_or_default('sitespeed_use_docker')
USE_CSP_ONLY = get_config_or_default('CSP_ONLY')
csp_only_global_result_dict = {}

def run_test(global_translation, lang_code, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    global csp_only_global_result_dict

    result_dict = {}

    local_translation = get_translation('http_validator', lang_code)

    if USE_CSP_ONLY:
        print(local_translation('TEXT_RUNNING_TEST_CSP_ONLY'))
    else:
        print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # We must take in consideration "www." subdomains...
    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    if USE_CSP_ONLY:
        result_dict = merge_dicts(check_csp(url), csp_only_global_result_dict, True, True)
        if 'nof_pages' not in result_dict:
            result_dict['nof_pages'] = 1
        else:
            result_dict['nof_pages'] += 1

        csp_only_global_result_dict = result_dict
    else:
        if hostname.startswith('www.'):
            url = url.replace(hostname, hostname[4:])

        o = urllib.parse.urlparse(url)
        hostname = o.hostname

        result_dict = check_http_to_https(url)

        result_dict = check_tls_versions(result_dict)

        result_dict = check_ip_version(result_dict)

        result_dict = check_http_version(url, result_dict)

    result_dict = cleanup(result_dict)

    rating = rate(hostname, result_dict, global_translation, local_translation)

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)

def rate(org_domain, result_dict, global_translation, local_translation):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    org_www_domain = f'www.{org_domain}'

    for domain in result_dict.keys():
        if not isinstance(result_dict[domain], dict):
            continue

        if not USE_CSP_ONLY:
            rating += rate_protocols(
                result_dict,
                global_translation,
                local_translation,
                domain)
            rating += rate_schemas(
                result_dict,
                global_translation,
                local_translation,
                domain)
            rating += rate_hsts(
                result_dict,
                global_translation,
                local_translation,
                org_domain,
                domain)
            rating += rate_ip_versions(
                result_dict,
                global_translation,
                local_translation,
                domain)
            rating += rate_transfer_layers(
                result_dict,
                global_translation,
                local_translation,
                domain)
        rating += rate_csp(
            result_dict,
            global_translation,
            local_translation,
            org_domain,
            org_www_domain,
            domain,
            True)

    return rating

def rate_ip_versions(result_dict, global_translation, local_translation, domain):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if not isinstance(result_dict[domain], dict):
        return rating

    if 'IPv4' in result_dict[domain]['ip-versions'] or\
            'IPv4*' in result_dict[domain]['ip-versions']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                local_translation('TEXT_REVIEW_IP_VERSION_IPV4_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
                local_translation('TEXT_REVIEW_IP_VERSION_IPV4_NO_SUPPORT').format(domain))
        rating += sub_rating

    if 'IPv6' in result_dict[domain]['ip-versions'] or\
            'IPv6*' in result_dict[domain]['ip-versions']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                local_translation('TEXT_REVIEW_IP_VERSION_IPV6_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
                local_translation('TEXT_REVIEW_IP_VERSION_IPV6_NO_SUPPORT').format(domain))
        rating += sub_rating
    return rating

def rate_hsts(result_dict, global_translation, local_translation, org_domain, domain):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if not isinstance(result_dict[domain], dict):
        return rating
    # https://scotthelme.co.uk/hsts-cheat-sheet/
    if 'HSTS' in result_dict[domain]['features']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)

        if 'INVALIDATE-HSTS' in result_dict[domain]['features']:
            sub_rating.set_overall(1.5)
            sub_rating.set_integrity_and_security(1.5,
                local_translation('TEXT_REVIEW_HSTS_INVALIDATE').format(domain))
            sub_rating.set_standards(1.5,
                local_translation('TEXT_REVIEW_HSTS_INVALIDATE').format(domain))
        elif 'HSTS-HEADER-PRELOAD-FOUND' in result_dict[domain]['features'] and\
                ('HSTS-PRELOAD' in result_dict[domain]['features'] or\
                 'HSTS-PRELOAD*' in result_dict[domain]['features']):
            sub_rating.set_standards(5.0)
            sub_rating.set_integrity_and_security(5.0,
                local_translation('TEXT_REVIEW_HSTS_PRELOAD_FOUND').format(domain))
        elif 'HSTS-HEADER-MAXAGE-1YEAR' in result_dict[domain]['features']:
            if 'HSTS-HEADER-PRELOAD-FOUND' in result_dict[domain]['features']:
                sub_rating.set_standards(5.0)
                sub_rating.set_integrity_and_security(5.0,
                    local_translation('TEXT_REVIEW_HSTS_PRELOAD_FOUND_AND_MAXAGE_1YEAR').format(
                        domain))
            elif domain == org_domain:
                sub_rating.set_standards(5.0)
                sub_rating.set_integrity_and_security(4.95,
                    local_translation('TEXT_REVIEW_HSTS_MAXAGE_1YEAR').format(domain))
            else:
                sub_rating.set_standards(5.0)
                sub_rating.set_integrity_and_security(5.0,
                    local_translation('TEXT_REVIEW_HSTS_MAXAGE_1YEAR').format(domain))
        elif 'HSTS-HEADER-MAXAGE-TOO-LOW' in result_dict[domain]['features']:
            sub_rating.set_overall(4.5)
            sub_rating.set_standards(5.0)
            sub_rating.set_integrity_and_security(4.0,
                local_translation('TEXT_REVIEW_HSTS_MAXAGE_TOO_LOW').format(domain))
        elif 'HSTS-HEADER-MAXAGE-6MONTHS' in result_dict[domain]['features']:
            sub_rating.set_overall(4.0)
            sub_rating.set_standards(5.0)
            sub_rating.set_integrity_and_security(3.0,
                local_translation('TEXT_REVIEW_HSTS_MAXAGE_6MONTHS').format(domain))
        elif 'HSTS-HEADER-MAXAGE-1MONTH' in result_dict[domain]['features']:
            sub_rating.set_overall(3.5)
            sub_rating.set_standards(5.0)
            sub_rating.set_integrity_and_security(2.0,
                local_translation('TEXT_REVIEW_HSTS_MAXAGE_1MONTH').format(domain))
        else:
            sub_rating.set_overall(3.0)
            sub_rating.set_standards(1.0,
                local_translation('TEXT_REVIEW_HSTS_MAXAGE_NOT_FOUND').format(domain))
            sub_rating.set_integrity_and_security(1.0,
                local_translation('TEXT_REVIEW_HSTS_MAXAGE_NOT_FOUND').format(domain))
        rating += sub_rating
    elif 'HSTS-HEADER-ON-PARENTDOMAIN-FOUND' in result_dict[domain]['features'] and\
            'INVALIDATE-HSTS' not in result_dict[domain]['features']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(4.99,
            local_translation('TEXT_REVIEW_HSTS_USE_PARENTDOMAIN').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
            local_translation('TEXT_REVIEW_HSTS_NOT_FOUND').format(domain))
        sub_rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_HSTS_NOT_FOUND').format(domain))
        rating += sub_rating
    return rating

def rate_schemas(result_dict, global_translation, local_translation, domain):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if not isinstance(result_dict[domain], dict):
        return rating

    if 'HTTPS' in result_dict[domain]['schemes']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0,
            local_translation('TEXT_REVIEW_HTTPS_SUPPORT').format(domain))
        sub_rating.set_standards(5.0,
            local_translation('TEXT_REVIEW_HTTPS_NO_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
            local_translation('TEXT_REVIEW_HTTPS_NO_SUPPORT').format(domain))
        sub_rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_HTTPS_NO_SUPPORT').format(domain))
        rating += sub_rating

    if 'HTTP-REDIRECT' in result_dict[domain]['schemes'] or\
            'HTTP-REDIRECT*' in result_dict[domain]['schemes']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
            local_translation('TEXT_REVIEW_HTTP_REDIRECT').format(domain))
        rating += sub_rating

    if 'HTTPS-REDIRECT' in result_dict[domain]['schemes'] or\
            'HTTPS-REDIRECT*' in result_dict[domain]['schemes']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0,
            local_translation('TEXT_REVIEW_HTTPS_REDIRECT').format(domain))
        rating += sub_rating
    return rating

def rate_protocols(result_dict, global_translation, local_translation, domain):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if not isinstance(result_dict[domain], dict):
        return rating

    if 'HTTP/1.1' in result_dict[domain]['protocols']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
            local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_1_1_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_1_1_NO_SUPPORT').format(domain))
        rating += sub_rating

    if 'HTTP/2' in result_dict[domain]['protocols']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
            local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_2_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_2_NO_SUPPORT').format(domain))
        rating += sub_rating

    if 'HTTP/3' in result_dict[domain]['protocols']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
            local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_3_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_3_NO_SUPPORT').format(domain))
        rating += sub_rating
    return rating

def cleanup(result_dict):
    for domain in result_dict.keys():
        if not isinstance(result_dict[domain], dict):
            continue

        if 'urls' in result_dict[domain]:
            del result_dict[domain]['urls']
        if 'csp-policies' in result_dict[domain]:
            del result_dict[domain]['csp-policies']

        for subkey, subvalue in result_dict[domain].items():
            if isinstance(subvalue, list):
                result_dict[domain][subkey].extend(subvalue)
                result_dict[domain][subkey] = sorted(list(set(result_dict[domain][subkey])))
    return result_dict

def host_source_2_url(host_source):
    result = host_source
    if '*' in result:
        result = result.replace('*', 'webperf-core-wildcard')
    if '://' not in result:
        result = f'https://{result}'

    return result

def url_2_host_source(url, domain):
    if url.startswith('//'):
        return url.replace('//', 'https://')
    if 'https://' in url:
        return url
    if '://' in url:
        return url
    if ':' in url:
        return url
    return f'https://{domain}/{url}'

def sitespeed_result_2_test_result(filename, org_domain):
    result = {
        'visits': 0,
        org_domain: default_csp_result_object(True)
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

            csp_findings_match = False

            o = urllib.parse.urlparse(req_url)
            req_domain = o.hostname
            req_scheme = o.scheme.lower()

            if req_domain not in result:
                result[req_domain] = default_csp_result_object(False)

            result[req_domain]['schemes'].append(o.scheme.upper())
            result[req_domain]['urls'].append(req_url)

            if 'httpVersion' in req and req['httpVersion'] != '':
                result[req_domain]['protocols'].append(
                    req['httpVersion'].replace('h2', 'HTTP/2').replace('h3', 'HTTP/3').upper())

            if 'httpVersion' in res and res['httpVersion'] != '':
                result[req_domain]['protocols'].append(
                    res['httpVersion'].replace('h2', 'HTTP/2').replace('h3', 'HTTP/3').upper())

            if 'serverIPAddress' in entry:
                if ':' in entry['serverIPAddress']:
                    result[req_domain]['ip-versions'].append('IPv6')
                else:
                    result[req_domain]['ip-versions'].append('IPv4')

            scheme = f'{o.scheme.lower()}:'
            if scheme not in result[org_domain]['csp-findings']['scheme-sources'] and\
                    scheme != 'http:':
                result[org_domain]['csp-findings']['scheme-sources'].append(scheme)
                csp_findings_match = True

            for header in res['headers']:
                if 'name' not in header:
                    continue

                if 'value' not in header:
                    continue

                name = header['name'].lower()
                value = header['value'].strip()

                if 'HSTS' not in result[req_domain]['features'] and\
                        'strict-transport-security' in name:
                    handle_header_hsts(result, req_domain, header)
                elif 'location' in name:
                    handle_header_location(result, req_url, req_domain, req_scheme, value)
                    # result[req_domain]['features'].append('LOCATION:{0}'.format(value))
                elif 'content-security-policy' in name:
                    result[req_domain]['features'].append('CSP-HEADER-FOUND')
                    result = handle_csp_data(value, req_domain, result, True, org_domain)
                elif 'x-content-security-policy' in name or 'x-webkit-csp' in name:
                    result[req_domain]['features'].append('CSP-HEADER-FOUND')
                    result[req_domain]['features'].append('CSP-DEPRECATED')
                    result = handle_csp_data(value, req_domain, result, True, org_domain)
            if 'content' in res and 'text' in res['content']:
                if 'mimeType' in res['content'] and 'text/html' in res['content']['mimeType']:
                    csp_findings_match = csp_findings_match or handle_mimetype_html(
                        org_domain,
                        result,
                        res,
                        req_url,
                        req_domain)

                elif 'mimeType' in res['content'] and 'text/css' in res['content']['mimeType']:
                    csp_findings_match = csp_findings_match or handle_mimetype_css(
                        org_domain,
                        result,
                        res,
                        req_domain)
                elif 'mimeType' in res['content'] and\
                        ('text/javascript' in res['content']['mimeType'] or\
                         'application/javascript' in res['content']['mimeType']):
                    csp_findings_match = csp_findings_match or handle_mimetype_javascript(
                        org_domain,
                        result,
                        res,
                        req_domain)
            if 'mimeType' in res['content'] and 'image/' in res['content']['mimeType']:
                csp_findings_match = csp_findings_match or handle_mimetype_images(
                    org_domain,
                    result,
                    req_domain)
            elif ('mimeType' in res['content'] and 'font/' in res['content']['mimeType']) or\
                    req_url.endswith('.otf') or\
                    req_url.endswith('.woff') or\
                    req_url.endswith('.woff2'):
                csp_findings_match = csp_findings_match or handle_mimetype_fonts(
                    org_domain,
                    result,
                    res,
                    req_url,
                    req_domain)

            if not csp_findings_match:
                element_name = 'connect'
                if req_domain == org_domain:
                    key = f'\'self\'|{element_name}'
                    if key not in result[org_domain]['csp-findings']['quotes']:
                        result[org_domain]['csp-findings']['quotes'].append(key)
                    csp_findings_match = True
                else:
                    key = f'{req_domain}|{element_name}'
                    if key not in result[org_domain]['csp-findings']['host-sources']:
                        result[org_domain]['csp-findings']['host-sources'].append(key)
                    csp_findings_match = True


            result[req_domain]['protocols'] = list(set(result[req_domain]['protocols']))
            result[req_domain]['schemes'] = list(set(result[req_domain]['schemes']))
            result[req_domain]['ip-versions'] = list(set(result[req_domain]['ip-versions']))

    result['visits'] = 1

    return result

def handle_mimetype_html(org_domain, result, res, req_url, req_domain):
    csp_findings_match = False
    result[req_domain]['features'].append('HTML-FOUND')
    content = res['content']['text']
    regex = (
                                r'<meta http-equiv=\"(?P<name>Content-Security-Policy)\" '
                                r'content=\"(?P<value>[^\"]{5,10000})\"'
                            )
    matches = re.finditer(regex, content, re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        name2 = match.group('name').lower()
        value2 = match.group('value').replace('&#39;', '\'')

        if 'content-security-policy' in name2:
            result[req_domain]['features'].append('CSP-META-FOUND')
            result = handle_csp_data(value2, req_domain, result, False, org_domain)
        elif 'x-content-security-policy' in name2:
            result[req_domain]['features'].append('CSP-META-FOUND')
            result[req_domain]['features'].append('CSP-DEPRECATED')
            result = handle_csp_data(value2, req_domain, result, False, org_domain)

    regex = (
                            r'(?P<raw><(?P<type>style|link|script|img|iframe|form|base|frame)[^>]'
                            r'*((?P<attribute>src|nonce|action|href)="(?P<value>[^"]+)"[^>]*>))'
                        )
    matches = re.finditer(regex, content, re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        element_name = match.group('type').lower()
        attribute_name = match.group('attribute').lower()
        attribute_value = match.group('value').lower()

        element_url = url_2_host_source(attribute_value, req_domain)
        o = urllib.parse.urlparse(element_url)
        element_domain = o.hostname
        if element_domain is None and element_url.startswith('data:'):
            element_domain = 'data:'
        elif element_domain == org_domain:
            element_domain = '\'self\''

        if attribute_name == 'nonce':
            key = f'\'nonce-<your-nonce>\'|{element_name}'
            if key not in result[org_domain]['csp-findings']['quotes']:
                result[org_domain]['csp-findings']['quotes'].append(key)
            csp_findings_match = True
        elif attribute_name == 'src':
            if element_domain is not None:
                key = f'{element_domain}|{element_name}'
                if key not in result[org_domain]['csp-findings']['host-sources']:
                    result[org_domain]['csp-findings']['host-sources'].append(key)
                csp_findings_match = True
        elif attribute_name == 'action' and element_name == 'form':
            key = f'{element_domain}|form-action'
            if key not in result[org_domain]['csp-findings']['host-sources']:
                result[org_domain]['csp-findings']['host-sources'].append(key)
            csp_findings_match = True

    regex = r'<(?P<type>style|script|form)>'
    matches = re.finditer(regex, content, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        element_name = match.group('type').lower()
        if element_name in ('style', 'script'):
            key = f'\'unsafe-inline\'|{element_name}'
            if key not in result[org_domain]['csp-findings']['quotes']:
                result[org_domain]['csp-findings']['quotes'].append(key)
            csp_findings_match = True
        elif attribute_name == 'action' and element_name == 'form':
            element_url = url_2_host_source(req_url, req_domain)
            o = urllib.parse.urlparse(element_url)
            element_domain = o.hostname
            if element_domain == org_domain:
                key = f'\'self\'|{element_name}'
                if key not in result[org_domain]['csp-findings']['quotes']:
                    result[org_domain]['csp-findings']['quotes'].append(key)
                csp_findings_match = True
            else:
                key = f'{element_domain}|{element_name}'
                if key not in result[org_domain]['csp-findings']['host-sources']:
                    result[org_domain]['csp-findings']['host-sources'].append(key)
                csp_findings_match = True
    return csp_findings_match

def handle_mimetype_css(org_domain, result, res, element_domain):
    csp_findings_match = False
    content = res['content']['text']
    if 'data:image' in content:
        key = 'data:|img'
        if key not in result[org_domain]['csp-findings']['scheme-sources']:
            result[org_domain]['csp-findings']['scheme-sources'].append(key)
        csp_findings_match = True
    element_name = 'style'
    if element_domain == org_domain:
        key = f'\'self\'|{element_name}'
        if key not in result[org_domain]['csp-findings']['quotes']:
            result[org_domain]['csp-findings']['quotes'].append(key)
        csp_findings_match = True
    else:
        key = f'{element_domain}|{element_name}'
        if key not in result[org_domain]['csp-findings']['host-sources']:
            result[org_domain]['csp-findings']['host-sources'].append(key)
        csp_findings_match = True
    return csp_findings_match

def handle_mimetype_javascript(org_domain, result, res, req_domain):
    csp_findings_match = False
    content = res['content']['text']
    if 'eval(' in content:
        key = '\'unsafe-eval\'|script'
        if key not in result[org_domain]['csp-findings']['quotes']:
            result[org_domain]['csp-findings']['quotes'].append(key)
        csp_findings_match = True

    element_domain = req_domain
    element_name = 'script'
    if element_domain == org_domain:
        key = f'\'self\'|{element_name}'
        if key not in result[org_domain]['csp-findings']['quotes']:
            result[org_domain]['csp-findings']['quotes'].append(key)
        csp_findings_match = True
    else:
        key = f"{element_domain}|{element_name}"
        if key not in result[org_domain]['csp-findings']['host-sources']:
            result[org_domain]['csp-findings']['host-sources'].append(key)
        csp_findings_match = True
    return csp_findings_match

def handle_mimetype_images(org_domain, result, req_domain):
    csp_findings_match = False
    element_domain = req_domain
    element_name = 'img'
    if element_domain == org_domain:
        key = f'\'self\'|{element_name}'
        if key not in result[org_domain]['csp-findings']['quotes']:
            result[org_domain]['csp-findings']['quotes'].append(key)
        csp_findings_match = True
    else:
        key = f'{element_domain}|{element_name}'
        if key not in result[org_domain]['csp-findings']['host-sources']:
            result[org_domain]['csp-findings']['host-sources'].append(key)
        csp_findings_match = True
    return csp_findings_match

def handle_mimetype_fonts(org_domain, result, res, req_url, req_domain):
    element_domain = req_domain
    element_name = 'font'
                # woff and woff2 support is in all browser, add hash to our csp-findings
    has_font_hash = False
    csp_findings_match = False
    if req_url.endswith('.woff') or\
                        req_url.endswith('.woff2') or\
                        'font-woff' in res['content']['mimeType'] or\
                        'font/woff' in res['content']['mimeType']:
        key = f'{req_url}|{element_name}'
        if key not in result[org_domain]['csp-findings']['font-sources']:
            font_content = None
            font_hash = None
            if 'text' in res['content'] and\
                                'encoding' in res['content'] and\
                                res['content']['encoding'] == 'base64':
                            # we have base64 encoded content,
                            # decode it, calcuclate sha256 and add it.
                font_content = base64.decodebytes(
                                res['content']['text'].encode('utf-8'))
                font_hash = create_sha256_hash(font_content)
                key2 = f"{f'sha256-{font_hash}'}|{element_name}"
                if key not in result[org_domain]['csp-findings']['quotes']:
                    result[org_domain]['csp-findings']['quotes'].append(key2)
                    result[org_domain]['csp-findings']['font-sources'].append(key)
                has_font_hash = True
        else:
            has_font_hash = True
        csp_findings_match = True
    if not has_font_hash:
        if element_domain == org_domain:
            key = f'\'self\'|{element_name}'
            if key not in result[org_domain]['csp-findings']['quotes']:
                result[org_domain]['csp-findings']['quotes'].append(key)
            csp_findings_match = True
        else:
            key = f'{element_domain}|{element_name}'
            if key not in result[org_domain]['csp-findings']['host-sources']:
                result[org_domain]['csp-findings']['host-sources'].append(key)
            csp_findings_match = True
    return csp_findings_match

def handle_header_location(result, req_url, req_domain, req_scheme, value):
    if value.startswith(f'https://{req_domain}'):
        result[req_domain]['schemes'].append('HTTPS-REDIRECT')
    elif value.startswith('https://') and req_scheme == 'http':
        result[req_domain]['schemes'].append('HTTPS-REDIRECT-OTHERDOMAIN')
        result[req_domain]['features'].append('INVALIDATE-HSTS')
    elif value.startswith(f'http://{req_domain}'):
        if req_url.startswith('https://'):
            result[req_domain]['schemes'].append('HTTP-REDIRECT')
        else:
            result[req_domain]['schemes'].append('HTTP-REDIRECT')
            result[req_domain]['features'].append('INVALIDATE-HSTS')
    elif value.startswith('http://'):
        result[req_domain]['schemes'].append('HTTP-REDIRECT-OTHERDOMAIN')
        result[req_domain]['features'].append('INVALIDATE-HSTS')

def handle_header_hsts(result, req_domain, header):
    sections = header['value'].split(';')
    for section in sections:
        section = section.strip()

        pair = section.split('=')

        section_name = pair[0]
        section_value = None
        if len(pair) == 2:
            section_value = pair[1]

        if 'max-age' == section_name:
            result[req_domain]['features'].append('HSTS-HEADER-MAXAGE-FOUND')
            try:
                maxage = int(section_value)
                                # 1 month =   2628000
                                # 6 month =  15768000
                                # check if maxage is more then 1 year
                if maxage >= 31536000:
                    result[req_domain]['features'].append(
                                        'HSTS-HEADER-MAXAGE-1YEAR')
                elif maxage < 2628000:
                    result[req_domain]['features'].append(
                                        'HSTS-HEADER-MAXAGE-1MONTH')
                elif maxage < 15768000:
                    result[req_domain]['features'].append(
                                        'HSTS-HEADER-MAXAGE-6MONTHS')
                else:
                    result[req_domain]['features'].append(
                                        'HSTS-HEADER-MAXAGE-TOO-LOW')

                result[req_domain]['features'].append('HSTS')
            except (TypeError, ValueError):
                _ = 1
        elif 'includeSubDomains' == section_name:
            result[req_domain]['features'].append(
                                'HSTS-HEADER-SUBDOMAINS-FOUND')
        elif 'preload' == section_name:
            result[req_domain]['features'].append(
                                'HSTS-HEADER-PRELOAD-FOUND')

def create_sha256_hash(data):
    sha_signature = hashlib.sha256(data).digest()
    base64_encoded_sha_signature = base64.b64encode(sha_signature).decode()
    return base64_encoded_sha_signature


def check_csp(url):
    # Firefox
    # dom.security.https_only_mode

    o = urllib.parse.urlparse(url)
    o_domain = o.hostname

    browser = 'firefox'
    configuration = ''
    print('CSP ONLY', o_domain)
    result_dict = get_website_support_from_sitespeed(
        url,
        o_domain,
        configuration,
        browser,
        SITESPEED_TIMEOUT)

    return result_dict


def check_http_to_https(url):
    # Firefox
    # dom.security.https_only_mode

    http_url = ''
    o = urllib.parse.urlparse(url)
    o_domain = o.hostname

    if o.scheme == 'https':
        http_url = url.replace('https://', 'http://')
    else:
        http_url = url

    browser = 'firefox'
    configuration = ''
    print('HTTP', o_domain)
    result_dict = get_website_support_from_sitespeed(
        http_url,
        o_domain,
        configuration,
        browser,
        SITESPEED_TIMEOUT)

    # If website redirects to www. domain without first redirecting to HTTPS, make sure we test it.
    if o_domain in result_dict:
        if 'HTTPS' not in result_dict[o_domain]['schemes']:
            result_dict[o_domain]['schemes'].append('HTTP-REDIRECT*')
            https_url = url.replace('http://', 'https://')
            print('HTTPS', o_domain)
            result_dict = merge_dicts(
                get_website_support_from_sitespeed(
                    https_url,
                    o_domain,
                    configuration,
                    browser,
                    SITESPEED_TIMEOUT),
                result_dict, True, True)
        else:
            result_dict[o_domain]['schemes'].append('HTTPS-REDIRECT*')

        if 'HTTP' not in result_dict[o_domain]['schemes']:
            result_dict[o_domain]['features'].append('HSTS-PRELOAD*')

    # If we have www. domain, ensure we validate HTTP2HTTPS on that as well
    www_domain_key = f'www.{o_domain}'
    if www_domain_key in result_dict:
        if 'HTTP' not in result_dict[www_domain_key]['schemes']:
            result_dict[www_domain_key]['schemes'].append('HTTPS-REDIRECT*')
            www_http_url = http_url.replace(o_domain, www_domain_key)
            print('HTTP', www_domain_key)
            result_dict = merge_dicts(
                get_website_support_from_sitespeed(
                    www_http_url,
                    www_domain_key,
                    configuration,
                    browser,
                    SITESPEED_TIMEOUT),
                result_dict,True, True)
        else:
            result_dict[www_domain_key]['schemes'].append('HTTP-REDIRECT*')


    domains = list(result_dict.keys())
    hsts_domains = []
    for domain in domains:
        if not isinstance(result_dict[domain], dict):
            continue

        if 'HSTS-HEADER-SUBDOMAINS-FOUND' in result_dict[domain]['features'] and\
                'HSTS' in result_dict[domain]['features']:
            hsts_domains.append(domain)

    for hsts_domain in hsts_domains:
        for domain in domains:
            if domain.endswith(f'.{hsts_domain}'):
                result_dict[domain]['features'].append('HSTS-HEADER-ON-PARENTDOMAIN-FOUND')

    return result_dict

def check_ip_version(result_dict):
    # network.dns.ipv4OnlyDomains
    # network.dns.disableIPv6

    if not contains_value_for_all(result_dict, 'ip-versions', 'IPv4'):
        for domain in result_dict.keys():
            if not isinstance(result_dict[domain], dict):
                continue
            if 'IPv4' not in result_dict[domain]['ip-versions']:
                ip4_result = dns_lookup(domain, dns.rdatatype.A)
                if len(ip4_result) > 0:
                    result_dict[domain]['ip-versions'].append('IPv4*')

    if not contains_value_for_all(result_dict, 'ip-versions', 'IPv6'):
        for domain in result_dict.keys():
            if not isinstance(result_dict[domain], dict):
                continue
            if 'IPv6' not in result_dict[domain]['ip-versions']:
                ip4_result = dns_lookup(domain, dns.rdatatype.AAAA)
                if len(ip4_result) > 0:
                    result_dict[domain]['ip-versions'].append('IPv6*')

    return result_dict

def get_website_support_from_sitespeed(url, org_domain, configuration, browser, timeout):
    # We don't need extra iterations for what we are using it for
    sitespeed_iterations = 1
    sitespeed_arg = (
        '--plugins.remove screenshot '
        '--plugins.remove html '
        '--plugins.remove metrics '
        '--browsertime.screenshot false '
        '--screenshot false '
        '--screenshotLCP false '
        '--browsertime.screenshotLCP false '
        '--videoParams.createFilmstrip false '
        '--visualMetrics false '
        '--visualMetricsPerceptual false '
        '--visualMetricsContentful false '
        '--browsertime.headless true '
        f'--utc true -n {sitespeed_iterations}')

    if 'firefox' in browser:
        sitespeed_arg = (
            '-b firefox '
            '--firefox.includeResponseBodies all '
            '--firefox.preference privacy.trackingprotection.enabled:false '
            '--firefox.preference privacy.donottrackheader.enabled:false '
            '--firefox.preference browser.safebrowsing.malware.enabled:false '
            '--firefox.preference browser.safebrowsing.phishing.enabled:false'
            f'{configuration} '
            f'{sitespeed_arg}')
    else:
        sitespeed_arg = (
            '-b chrome '
            '--chrome.cdp.performance false '
            '--browsertime.chrome.timeline false '
            '--browsertime.chrome.includeResponseBodies all '
            '--browsertime.chrome.args ignore-certificate-errors '
            f'{sitespeed_arg}')

    sitespeed_arg = f'--shm-size=1g {sitespeed_arg}'

    if 'nt' not in os.name:
        sitespeed_arg += ' --xvfb'

    (_, filename) = get_result(
        url, SITESPEED_USE_DOCKER, sitespeed_arg, timeout)

    result = sitespeed_result_2_test_result(filename, org_domain)
    return result

def contains_value_for_all(result_dict, key, value):
    if result_dict is None:
        return False

    has_value = True
    for domain in result_dict.keys():
        if not isinstance(result_dict[domain], dict):
            continue
        if key not in result_dict[domain] or value not in result_dict[domain][key]:
            has_value = False
    return has_value

def check_http_version(url, result_dict):

    # SiteSpeed (firefox):
    # "httpVersion": "HTTP/1"
    # "httpVersion": "HTTP/1.1"
    # "httpVersion": "HTTP/2"
    # "httpVersion": "HTTP/3"

    # SiteSpeed (chrome):
    # "httpVersion": "http/1.1"
    # "httpVersion": "h2"
    # "httpVersion": "h3"

    # Chrome:
    # https://www.chromium.org/for-testers/providing-network-details/


    # Firefox:
    # about:networking
    # network.http.http2.enabled
    # network.http.http3.enable
    # network.http.version

    # network.http.version and their effects1:
    # - 0.9
    # - 1.0
    # - 1.1 (Default)
    # - 2.0
    # - 3.02

    o = urllib.parse.urlparse(url)
    o_domain = o.hostname


    if not contains_value_for_all(result_dict, 'protocols', 'HTTP/1.1'):
        browser = 'firefox'
        configuration = (
            ' --firefox.preference network.http.http2.enabled:false'
            ' --firefox.preference network.http.http3.enable:false')
        url2 = change_url_to_test_url(url, 'HTTPv1')
        print('HTTP/1.1')
        result_dict = merge_dicts(
            get_website_support_from_sitespeed(
                url2,
                o_domain,
                configuration,
                browser,
                SITESPEED_TIMEOUT),
            result_dict, True, True)

    if not contains_value_for_all(result_dict, 'protocols', 'HTTP/2'):
        browser = 'firefox'
        configuration = (
            ' --firefox.preference network.http.http2.enabled:true'
            ' --firefox.preference network.http.http3.enable:false'
            ' --firefox.preference network.http.version:3.0')
        url2 = change_url_to_test_url(url, 'HTTPv2')
        print('HTTP/2')
        result_dict = merge_dicts(
            get_website_support_from_sitespeed(
                url2,
                o_domain,
                configuration,
                browser,
                SITESPEED_TIMEOUT),
            result_dict, True, True)

    if not contains_value_for_all(result_dict, 'protocols', 'HTTP/3'):
        browser = 'firefox'
        configuration = (
            ' --firefox.preference network.http.http2.enabled:false'
            ' --firefox.preference network.http.http3.enable:true'
            ' --firefox.preference network.http.version:3.0')
        url2 = change_url_to_test_url(url, 'HTTPv3')
        print('HTTP/3')
        result_dict = merge_dicts(
            get_website_support_from_sitespeed(
                url2,
                o_domain,
                configuration,
                browser,
                SITESPEED_TIMEOUT),
            result_dict, True, True)

    return result_dict
