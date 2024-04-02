# -*- coding: utf-8 -*-
import os
from datetime import datetime
import re
import urllib.parse
import sys
import ssl
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from requests.packages.urllib3.util import ssl_
# https://docs.python.org/3/library/urllib.parse.html
import urllib
from models import Rating
from tests.utils import change_url_to_test_url, dns_lookup, get_translation, merge_dicts, get_config_or_default
from tests.sitespeed_base import get_result
import dns.name
import dns.query
import dns.dnssec
import dns.message
import dns.resolver
import dns.rdatatype
import hashlib
import base64


# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
SITESPEED_TIMEOUT = get_config_or_default('sitespeed_timeout')
USERAGENT = get_config_or_default('useragent')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
SITESPEED_USE_DOCKER = get_config_or_default('sitespeed_use_docker')
SOFTWARE_BROWSER = get_config_or_default('SOFTWARE_BROWSER')
USE_CACHE = get_config_or_default('cache_when_possible')
CACHE_TIME_DELTA = get_config_or_default('cache_time_delta')

USE_DETAILED_REPORT = get_config_or_default('USE_DETAILED_REPORT')
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

        # result_dict = check_dnssec(hostname, result_dict)

    result_dict = cleanup(result_dict)

    rating = rate(hostname, result_dict, global_translation, local_translation)

    # nice_result = json.dumps(result_dict, indent=3)
    # print('DEBUG TOTAL', nice_result)

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)

def rate(org_domain, result_dict, global_translation, local_translation):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    org_www_domain = 'www.{0}'.format(org_domain)

    for domain in result_dict.keys():
        if type(result_dict[domain]) != dict:
            continue

        if not USE_CSP_ONLY:
            rating += rate_protocols(result_dict, global_translation, local_translation ,domain)
            # rating += rate_dnssec(result_dict, global_translation, local_translation, domain)
            rating += rate_schemas(result_dict, global_translation, local_translation, domain)
            rating += rate_hsts(result_dict, global_translation, local_translation, org_domain, domain)
            rating += rate_ip_versions(result_dict, global_translation, local_translation, domain)
            rating += rate_transfer_layers(result_dict, global_translation, local_translation, domain)
        rating += rate_csp(result_dict, global_translation, local_translation, org_domain, org_www_domain, domain, True)

    return rating

def rate_transfer_layers(result_dict, global_translation, local_translation, domain):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if type(result_dict[domain]) != dict:
        return rating
    
    if 'TLSv1.3' in result_dict[domain]['transport-layers']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_TLS1_3_SUPPORT').format(domain))
        sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_TLS1_3_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_TLS1_3_NO_SUPPORT').format(domain))
        sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_TLS1_3_NO_SUPPORT').format(domain))
        rating += sub_rating

    if 'TLSv1.2' in result_dict[domain]['transport-layers']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_TLS1_2_SUPPORT').format(domain))
        sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_TLS1_2_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_TLS1_2_NO_SUPPORT').format(domain))
        sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_TLS1_2_NO_SUPPORT').format(domain))
        rating += sub_rating

    if 'TLSv1.1' in result_dict[domain]['transport-layers']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_TLS1_1_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_TLS1_1_NO_SUPPORT').format(domain))
        rating += sub_rating

    if 'TLSv1.0' in result_dict[domain]['transport-layers']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_TLS1_0_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_TLS1_0_NO_SUPPORT').format(domain))
        rating += sub_rating
    return rating

def rate_ip_versions(result_dict, global_translation, local_translation, domain):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if type(result_dict[domain]) != dict:
        return rating
    
    if 'IPv4' in result_dict[domain]['ip-versions'] or 'IPv4*' in result_dict[domain]['ip-versions']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_IP_VERSION_IPV4_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_IP_VERSION_IPV4_NO_SUPPORT').format(domain))
        rating += sub_rating

    if 'IPv6' in result_dict[domain]['ip-versions'] or 'IPv6*' in result_dict[domain]['ip-versions']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_IP_VERSION_IPV6_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_IP_VERSION_IPV6_NO_SUPPORT').format(domain))
        rating += sub_rating
    return rating

def create_csp(csp_findings, org_domain):
    default_src = []
    img_src = []
    script_src = []
    form_action = []
    base_uri = []
    style_src = []
    child_src = []
    font_src = []

    object_src = []
    connect_src = []
    frame_ancestors = []

    csp_findings['quotes'] = list(set(csp_findings['quotes']))
    csp_findings['host-sources'] = list(set(csp_findings['host-sources']))
    csp_findings['scheme-sources'] = list(set(csp_findings['scheme-sources']))

    for source in csp_findings['quotes']:
        if '|' in source:
            pair = source.split('|')
            host_source = pair[0]
            element_name = pair[1]
            if host_source == org_domain:
                host_source = '\'self\''

            if element_name == 'img':
                img_src.append(host_source)
            elif element_name == 'script':
                script_src.append(host_source)
            elif element_name == 'form-action':
                form_action.append(host_source)
            elif element_name == 'style':
                style_src.append(host_source)
            elif element_name == 'font':
                font_src.append(host_source)
            elif element_name == 'connect':
                connect_src.append(host_source)
            elif element_name == 'link':
                child_src.append(host_source)
                default_src.append(host_source)
            else:
                default_src.append(host_source)

    for source in csp_findings['host-sources']:
        if '|' in source:
            pair = source.split('|')
            host_source = pair[0]
            element_name = pair[1]
            if host_source == org_domain:
                host_source = '\'self\''
            if element_name == 'img':
                img_src.append(host_source)
            elif element_name == 'script':
                script_src.append(host_source)
            elif element_name == 'form-action':
                form_action.append(host_source)
            elif element_name == 'style':
                style_src.append(host_source)
            elif element_name == 'font':
                font_src.append(host_source)
            elif element_name == 'connect':
                connect_src.append(host_source)
            elif element_name == 'link':
                # child_src.append(host_source)
                default_src.append(host_source)
            else:
                default_src.append(host_source)
        else:
            if source == org_domain:
                default_src.append('\'self\'')
            else:
                default_src.append(source)

    for source in csp_findings['scheme-sources']:
        if '|' in source:
            pair = source.split('|')
            host_source = pair[0]
            element_name = pair[1]
            if element_name == 'img':
                img_src.append(host_source)

    # Ensure policies that is NOT covered by a fallback
    if len(base_uri) == 0:
        base_uri.append('\'self\'')

    if len(object_src) == 0:
        object_src.append('\'none\'')

    if len(frame_ancestors) == 0:
        frame_ancestors.append('\'none\'')

    if len(default_src) == 0:
        default_src.append('\'none\'')

    if len(form_action) == 0:
        form_action.append('\'none\'')

    default_src = ' '.join(sorted(list(set(default_src))))
    img_src = ' '.join(sorted(list(set(img_src))))
    script_src = ' '.join(sorted(list(set(script_src))))
    form_action = ' '.join(sorted(list(set(form_action))))
    style_src = ' '.join(sorted(list(set(style_src))))
    child_src = ' '.join(sorted(list(set(child_src))))
    font_src = ' '.join(sorted(list(set(font_src))))

    base_uri = ' '.join(sorted(list(set(base_uri))))
    object_src = ' '.join(sorted(list(set(object_src))))
    frame_ancestors = ' '.join(sorted(list(set(frame_ancestors))))
    connect_src = ' '.join(sorted(list(set(connect_src))))


    default_src = default_src.strip()
    img_src = img_src.strip()
    script_src = script_src.strip()
    form_action = form_action.strip()
    style_src = style_src.strip()
    child_src = child_src.strip()
    font_src = font_src.strip()

    base_uri = base_uri.strip()
    object_src = object_src.strip()
    frame_ancestors = frame_ancestors.strip()
    connect_src = connect_src.strip()

    csp_recommendation = ''
    # csp_recommendation = 'Content-Security-Policy-Report-Only=\r\n'
    if len(default_src) > 0:
        csp_recommendation += '- default-src {0};\r\n'.format(default_src)
    if len(base_uri) > 0:
        csp_recommendation += '- base-uri {0};\r\n'.format(base_uri)
    if len(img_src) > 0:
        csp_recommendation += '- img-src {0};\r\n'.format(img_src)
    if len(script_src) > 0:
        csp_recommendation += '- script-src {0};\r\n'.format(script_src)
    if len(form_action) > 0:
        csp_recommendation += '- form-action {0};\r\n'.format(form_action)
    if len(style_src) > 0:
        csp_recommendation += '- style-src {0};\r\n'.format(style_src)
    if len(child_src) > 0:
        csp_recommendation += '- child-src {0};\r\n'.format(child_src)

    if len(object_src) > 0:
        csp_recommendation += '- object-src {0};\r\n'.format(object_src)
    if len(frame_ancestors) > 0:
        csp_recommendation += '- frame-ancestors {0};\r\n'.format(frame_ancestors)
    if len(connect_src) > 0:
        csp_recommendation += '- connect-src {0};\r\n'.format(connect_src)
    if len(font_src) > 0:
        csp_recommendation += '- font-src {0};\r\n'.format(font_src)

    return csp_recommendation

def rate_csp(result_dict, global_translation, local_translation, org_domain, org_www_domain, domain, create_recommendation):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if type(result_dict[domain]) != dict:
        return rating

    if domain != org_domain and domain != org_www_domain:
        return rating

    # TODO: We should check if X-Frame-Options is used and adjust rating for setting 'frame-ancestors' directive to 'none' is similar to X-Frame-Options: deny (which is also supported in older browsers).
    if 'CSP-HEADER-FOUND' in result_dict[domain]['features'] or 'CSP-META-FOUND' in result_dict[domain]['features']:
        total_number_of_sitespeedruns = result_dict['visits']

        if 'CSP-UNSUPPORTED-IN-META' in result_dict[domain]['features']:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(1.0)
            sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_CSP_UNSUPPORTED_IN_META').format(domain))
            rating += sub_rating

        # default-src|script-src|style-src|font-src|connect-src|frame-src|img-src|media-src|frame-ancestors|base-uri|form-action|block-all-mixed-content|child-src|connect-src|fenced-frame-src|font-src|img-src|manifest-src|media-src|object-src|plugin-types|prefetch-src|referrer|report-to|report-uri|require-trusted-types-for|sandbox|script-src-attr|script-src-elem|strict-dynamic|style-src-attr|style-src-elem|trusted-types|unsafe-hashes|upgrade-insecure-requests|worker-src
        supported_src_policies = ['default-src','script-src','style-src','font-src','connect-src','frame-src','img-src','media-src','frame-ancestors','base-uri','form-action','child-src','manifest-src','object-src','script-src-attr','script-src-elem','style-src-attr','style-src-elem','worker-src']
        self_allowed_policies = ['font-src','connect-src','frame-src','img-src','media-src','frame-ancestors','base-uri','form-action','child-src','manifest-src']
        other_supported_polices = ['report-to','sandbox','upgrade-insecure-requests']
        fallback_src_policies = ['base-uri', 'object-src', 'frame-ancestors', 'form-action', 'default-src']
        experimental_policies = ['fenced-frame-src', 'require-trusted-types-for','inline-speculation-rules', 'trusted-types']
        # Deprecated policies (According to https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
        deprecated_policies = ['block-all-mixed-content','plugin-types','prefetch-src', 'referrer', 'report-uri']
        is_using_deprecated_policy = False
        for policy_name in deprecated_policies:
            if policy_name in result_dict[domain]['csp-objects']:
                is_using_deprecated_policy = True
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(1.0)
                sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_DEPRECATED').format(policy_name, domain))
                rating += sub_rating

        if not is_using_deprecated_policy:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(5.0)
            sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_NOT_DEPRECATED').format(policy_name, domain))
            rating += sub_rating

        for policy_name in supported_src_policies:
            policy_object = None
            if policy_name in result_dict[domain]['csp-objects']:
                policy_object = result_dict[domain]['csp-objects'][policy_name]
            else:
                # policy_object = default_csp_policy_object()
                continue

            any_found = False

            is_using_wildcard_in_policy = False
            for wildcard in policy_object['wildcards']:
                is_using_wildcard_in_policy = True
                any_found = True
                if wildcard.endswith('*'):
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(1.0)
                    sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_USE_WILDCARD').format(policy_name, domain))
                    rating += sub_rating
                else:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(2.0)
                    sub_rating.set_integrity_and_security(2.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, local_translation('TEXT_REVIEW_CSP_WILDCARDS'), domain))
                    rating += sub_rating

            nof_wildcard_subdomains = len(policy_object['wildcard-subdomains'])
            if nof_wildcard_subdomains > 0:
                if policy_name in self_allowed_policies:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(5.0)
                    sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, local_translation('TEXT_REVIEW_CSP_WILDCARD_SUBDOMAIN'), domain))
                    rating += sub_rating
                else:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(2.7)
                    sub_rating.set_integrity_and_security(2.7, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, local_translation('TEXT_REVIEW_CSP_WILDCARD_SUBDOMAIN'), domain))
                    rating += sub_rating

            if not is_using_wildcard_in_policy:
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(5.0)
                sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_NOT_USE_WILDCARD').format(policy_name, domain))
                rating += sub_rating

            if "'none'" in policy_object['all']:
                if len(policy_object['all']) > 1:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(5.0)
                    sub_rating.set_standards(1.5, local_translation('TEXT_REVIEW_CSP_POLICY_NONE_NOT_ALONE').format(policy_name, "'none'", domain))
                    sub_rating.set_integrity_and_security(1.5, local_translation('TEXT_REVIEW_CSP_POLICY_NONE_NOT_ALONE').format(policy_name, "'none'", domain))
                    rating += sub_rating
                else:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(1.5)
                    sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "'none'", domain))
                    sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "'none'", domain))
                    rating += sub_rating
                any_found = True
            elif len(policy_object['hashes']) > 0:
                # TODO: Validate correct format ( '<hash-algorithm>-<base64-value>' )
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(5.0)
                sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "sha[256/384/512]", domain))
                sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "sha[256/384/512]", domain))
                rating += sub_rating
                any_found = True
            else:
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(1.0)
                sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(policy_name, "'none'", domain))
                sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(policy_name, "'none'", domain))
                rating += sub_rating


            nof_nonces = len(policy_object['nounces'])
            if nof_nonces > 0:
                # TODO: we should check nonce length as it should not be guessable.
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                if nof_nonces == 1 and total_number_of_sitespeedruns != nof_nonces:
                    sub_rating.set_overall(1.0)
                    sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_REUSE_NONCE').format(policy_name, domain))
                    sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_REUSE_NONCE').format(policy_name, domain))
                elif nof_nonces > total_number_of_sitespeedruns:
                    sub_rating.set_overall(4.75)
                    sub_rating.set_standards(4.99, local_translation('TEXT_REVIEW_CSP_POLICY_MULTIUSE_NONCE').format(policy_name, "'nonce's", domain))
                    sub_rating.set_integrity_and_security(4.5, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "nonce", domain))
                else:
                    sub_rating.set_overall(1.0)
                    sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(policy_name, "'self'", domain))
                    sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(policy_name, "'self'", domain))
                rating += sub_rating
                any_found = True

            if "'self'" in policy_object['all']:
                if policy_name in self_allowed_policies:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(5.0)
                    sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "'self'", domain))
                    sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "'self'", domain))                
                    rating += sub_rating
                else:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(3.0)
                    sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "'self'", domain))
                    sub_rating.set_integrity_and_security(3.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "'self'", domain))                
                    rating += sub_rating
                any_found = True
            else:
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(5.0)
                sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(policy_name, "'self'", domain))
                sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(policy_name, "'self'", domain))                
                rating += sub_rating


            nof_subdomains = len(policy_object['subdomains'])
            if nof_subdomains > 0:
                if policy_name in self_allowed_policies:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(5.0)
                    sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, local_translation('TEXT_REVIEW_CSP_SUBDOMAIN'), domain))
                    rating += sub_rating
                else:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(3.0)
                    sub_rating.set_integrity_and_security(3.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, local_translation('TEXT_REVIEW_CSP_SUBDOMAIN'), domain))
                    rating += sub_rating
            else:
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(5.0)
                sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(policy_name, local_translation('TEXT_REVIEW_CSP_SUBDOMAIN'), domain))
                sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(policy_name, local_translation('TEXT_REVIEW_CSP_SUBDOMAIN'), domain))                
                rating += sub_rating

            nof_domains = len(policy_object['domains'])
            if nof_domains > 0:
                if nof_domains > 15:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(1.5)
                    sub_rating.set_integrity_and_security(1.5, local_translation('TEXT_REVIEW_CSP_POLICY_USE_15_OR_MORE_DOMAINS').format(policy_name, local_translation('TEXT_REVIEW_CSP_DOMAIN'), domain))
                    rating += sub_rating

                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(2.5)
                sub_rating.set_integrity_and_security(2.5, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, local_translation('TEXT_REVIEW_CSP_DOMAIN'), domain))
                rating += sub_rating
                any_found = True
            else:
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(5.0)
                sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(policy_name, local_translation('TEXT_REVIEW_CSP_DOMAIN'), domain))
                sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(policy_name, local_translation('TEXT_REVIEW_CSP_DOMAIN'), domain))                
                rating += sub_rating

            nof_schemes = len(policy_object['schemes'])
            if nof_schemes > 0:
                if 'ws' in policy_object['schemes']:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(1.0)
                    sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_USE_UNSAFE_SCHEME').format(policy_name, "'ws'", domain))
                    rating += sub_rating
                if 'http' in policy_object['schemes']:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(1.0)
                    sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_USE_UNSAFE_SCHEME').format(policy_name, "'http'", domain))
                    rating += sub_rating
                if 'ftp' in policy_object['schemes']:
                    sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                    sub_rating.set_overall(1.0)
                    sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_USE_UNSAFE_SCHEME').format(policy_name, "'ftp'", domain))
                    rating += sub_rating
                any_found = True

            nof_malformed = len(policy_object['malformed'])
            if nof_malformed > 0:
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(1.0)
                sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_CSP_MALFORMED').format(policy_name, domain))
                rating += sub_rating

            if not any_found:
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(1.0)
                sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(policy_name, "'none', 'self' nonce, sha[256/384/512], domain or scheme", domain))
                rating += sub_rating

            # Handles unsafe sources
            is_using_unsafe = False
            if "'unsafe-eval'" in policy_object['all']:
                is_using_unsafe = True
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(1.0)
                sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "'unsafe-eval'", domain))                
                rating += sub_rating

            if "'wasm-unsafe-eval'" in policy_object['all']:
                is_using_unsafe = True
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(1.0)
                sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "'wasm-unsafe-eval'", domain))                
                rating += sub_rating

            if "'unsafe-hashes'" in policy_object['all']:
                is_using_unsafe = True
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(1.0)
                sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "'unsafe-hashes'", domain))                
                rating += sub_rating

            if "'unsafe-inline'" in policy_object['all']:
                is_using_unsafe = True
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(1.0)
                sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(policy_name, "'unsafe-inline'", domain))                
                rating += sub_rating

            if not is_using_unsafe:
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(5.0)
                sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(policy_name, "'unsafe-*'", domain))
                rating += sub_rating


            # Handle policy specific logic
            # if policy_name == 'base-uri':
            #     if len(policy_object['all']) == 0:
            #         sub_rating = Rating(global_translation, review_show_improvements_only)
            #         sub_rating.set_overall(5.0)
            #         sub_rating.set_standards(5.0)
            #         sub_rating.set_integrity_and_security(5.0)

        for policy_name in fallback_src_policies:
            if policy_name in result_dict[domain]['csp-objects']:
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(5.0)
                sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_FOUND').format(policy_name, domain))
                sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_CSP_POLICY_FOUND').format(policy_name, domain))
                rating += sub_rating
            else:
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(1.0)
                sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_NOT_FOUND').format(policy_name, domain))
                sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_CSP_POLICY_NOT_FOUND').format(policy_name, domain))
                rating += sub_rating

    elif 'HTML-FOUND' in result_dict[domain]['features'] and (domain == org_domain or domain == org_www_domain):
        rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        rating.set_overall(1.0)
        rating.set_standards(1.0, local_translation('TEXT_REVIEW_CSP_NOT_FOUND').format(domain))
        rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_CSP_NOT_FOUND').format(domain))

    final_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if rating.is_set:
        if USE_DETAILED_REPORT:
            final_rating.set_overall(rating.get_overall())
            final_rating.overall_review = rating.overall_review
            final_rating.set_standards(rating.get_standards())
            final_rating.standards_review = rating.standards_review
            final_rating.set_integrity_and_security(rating.get_integrity_and_security())
            final_rating.integrity_and_security_review = rating.integrity_and_security_review
        else:
            final_rating.set_overall(rating.get_overall())
            final_rating.set_standards(rating.get_standards(), local_translation('TEXT_REVIEW_CSP').format(domain))
            final_rating.set_integrity_and_security(rating.get_integrity_and_security(), local_translation('TEXT_REVIEW_CSP').format(domain))


    if create_recommendation:
        csp_recommendation = ''
        csp_recommendation_result = False
        if 'csp-findings' in result_dict[domain]:
            csp_recommendation_result = {
                'visits': 1,
                domain: default_csp_result_object(True)
            }
            csp_recommendation = create_csp(result_dict[domain]['csp-findings'], domain)

            raw_csp_recommendation = csp_recommendation.replace('- ','').replace('\r\n','')
            result_dict[domain]['csp-recommendation'] = [raw_csp_recommendation]

            csp_recommendation_result = handle_csp_data(raw_csp_recommendation, domain, csp_recommendation_result, True, domain)

            csp_recommendation_result[domain]['features'].append('CSP-HEADER-FOUND')
            csp_recommendation_rating = rate_csp(csp_recommendation_result, global_translation, local_translation, org_domain, org_www_domain, domain, False)

            csp_recommendation_rating_summary = local_translation('TEXT_REVIEW_CSP_RECOMMENDED_RATING').format(csp_recommendation_rating)

            nof_pages = 1
            if 'nof_pages' in result_dict:
                nof_pages = result_dict['nof_pages']

            text_recommendation = local_translation('TEXT_REVIEW_CSP_RECOMMENDED_TEXT').format(nof_pages, csp_recommendation, csp_recommendation_rating_summary)
            score = csp_recommendation_rating.get_integrity_and_security()
            if score > final_rating.get_integrity_and_security():
                final_rating.overall_review = text_recommendation + final_rating.overall_review

    return final_rating


def rate_hsts(result_dict, global_translation, local_translation, org_domain, domain):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if type(result_dict[domain]) != dict:
        return rating
    # https://scotthelme.co.uk/hsts-cheat-sheet/
    if 'HSTS' in result_dict[domain]['features']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)

        if 'INVALIDATE-HSTS' in result_dict[domain]['features']:
            sub_rating.set_overall(1.5)
            sub_rating.set_integrity_and_security(1.5, local_translation('TEXT_REVIEW_HSTS_INVALIDATE').format(domain))
            sub_rating.set_standards(1.5, local_translation('TEXT_REVIEW_HSTS_INVALIDATE').format(domain))
        elif 'HSTS-HEADER-PRELOAD-FOUND' in result_dict[domain]['features'] and ('HSTS-PRELOAD' in result_dict[domain]['features'] or 'HSTS-PRELOAD*' in result_dict[domain]['features']):
            sub_rating.set_standards(5.0)
            sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_HSTS_PRELOAD_FOUND').format(domain))
        elif 'HSTS-HEADER-MAXAGE-1YEAR' in result_dict[domain]['features']:
            if 'HSTS-HEADER-PRELOAD-FOUND' in result_dict[domain]['features']:
                sub_rating.set_standards(5.0)
                sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_HSTS_PRELOAD_FOUND_AND_MAXAGE_1YEAR').format(domain))
            elif domain == org_domain:
                sub_rating.set_standards(5.0)
                sub_rating.set_integrity_and_security(4.95, local_translation('TEXT_REVIEW_HSTS_MAXAGE_1YEAR').format(domain))
            else:
                sub_rating.set_standards(5.0)
                sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_HSTS_MAXAGE_1YEAR').format(domain))
        elif 'HSTS-HEADER-MAXAGE-TOO-LOW' in result_dict[domain]['features']:
            sub_rating.set_overall(4.5)
            sub_rating.set_standards(5.0)
            sub_rating.set_integrity_and_security(4.0, local_translation('TEXT_REVIEW_HSTS_MAXAGE_TOO_LOW').format(domain))
        elif 'HSTS-HEADER-MAXAGE-6MONTHS' in result_dict[domain]['features']:
            sub_rating.set_overall(4.0)
            sub_rating.set_standards(5.0)
            sub_rating.set_integrity_and_security(3.0, local_translation('TEXT_REVIEW_HSTS_MAXAGE_6MONTHS').format(domain))
        elif 'HSTS-HEADER-MAXAGE-1MONTH' in result_dict[domain]['features']:
            sub_rating.set_overall(3.5)
            sub_rating.set_standards(5.0)
            sub_rating.set_integrity_and_security(2.0, local_translation('TEXT_REVIEW_HSTS_MAXAGE_1MONTH').format(domain))
        else:
            sub_rating.set_overall(3.0)
            sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_HSTS_MAXAGE_NOT_FOUND').format(domain))
            sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_HSTS_MAXAGE_NOT_FOUND').format(domain))
        rating += sub_rating
    elif 'HSTS-HEADER-ON-PARENTDOMAIN-FOUND' in result_dict[domain]['features'] and 'INVALIDATE-HSTS' not in result_dict[domain]['features']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(4.99, local_translation('TEXT_REVIEW_HSTS_USE_PARENTDOMAIN').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_HSTS_NOT_FOUND').format(domain))
        sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_HSTS_NOT_FOUND').format(domain))
        rating += sub_rating
    return rating

def rate_schemas(result_dict, global_translation, local_translation, domain):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if type(result_dict[domain]) != dict:
        return rating
    
    if 'HTTPS' in result_dict[domain]['schemes']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_HTTPS_SUPPORT').format(domain))
        sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_HTTPS_NO_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_HTTPS_NO_SUPPORT').format(domain))
        sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_HTTPS_NO_SUPPORT').format(domain))
        rating += sub_rating

    if 'HTTP-REDIRECT' in result_dict[domain]['schemes'] or 'HTTP-REDIRECT*' in result_dict[domain]['schemes']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0, local_translation('TEXT_REVIEW_HTTP_REDIRECT').format(domain))
        rating += sub_rating

    if 'HTTPS-REDIRECT' in result_dict[domain]['schemes'] or 'HTTPS-REDIRECT*' in result_dict[domain]['schemes']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0, local_translation('TEXT_REVIEW_HTTPS_REDIRECT').format(domain))
        rating += sub_rating
    return rating

def rate_dnssec(result_dict, global_translation, local_translation, domain):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if 'DNSSEC' in result_dict[domain]['features']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0)
        sub_rating.set_standards(5.0)
        rating += sub_rating
    elif 'DNSSEC-IGNORE' in result_dict[domain]['features']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0)
        sub_rating.set_standards(5.0)
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0, '- {0}, No DNSSEC support'.format(domain))
        sub_rating.set_standards(1.0, '- {0}, No DNSSEC support'.format(domain))
        rating += sub_rating
    return rating

def rate_protocols(result_dict, global_translation, local_translation, domain):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if type(result_dict[domain]) != dict:
        return rating
    
    if 'HTTP/1.1' in result_dict[domain]['protocols']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_1_1_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_1_1_NO_SUPPORT').format(domain))
        rating += sub_rating

    if 'HTTP/2' in result_dict[domain]['protocols']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_2_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_2_NO_SUPPORT').format(domain))
        rating += sub_rating

    if 'HTTP/3' in result_dict[domain]['protocols']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0, local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_3_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0, local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_3_NO_SUPPORT').format(domain))
        rating += sub_rating
    return rating

def cleanup(result_dict):
    for domain in result_dict.keys():
        if type(result_dict[domain]) != dict:
            continue

        if 'urls' in result_dict[domain]:
            del result_dict[domain]['urls']
        if 'csp-policies' in result_dict[domain]:
            del result_dict[domain]['csp-policies']

        for subkey, subvalue in result_dict[domain].items():
            if type(subvalue) == dict:
                a = 1
            elif type(subvalue) == list:
                result_dict[domain][subkey].extend(subvalue)
                result_dict[domain][subkey] = sorted(list(set(result_dict[domain][subkey])))
    return result_dict

def host_source_2_url(host_source):
    result = host_source
    if '*' in result:
        result = result.replace('*', 'webperf-core-wildcard')
    if '://' not in result:
        result = 'https://{0}'.format(result)

    return result

def url_2_host_source(url, domain):
    if url.startswith('//'):
        return url.replace('//', 'https://')
    elif 'https://' in url:
        return url
    if '://' in url:
        return url
    elif ':' in url:
        return url
    else:
        return 'https://{0}/{1}'.format(domain, url)

def sitespeed_result_2_test_result(filename, org_domain):

    result = {
        'visits': 0,
        org_domain: default_csp_result_object(True)
    }

    if filename == '':
        return result
    
    # Fix for content having unallowed chars
    with open(filename) as json_input_file:
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
                result[req_domain]['protocols'].append(req['httpVersion'].replace('h2', 'HTTP/2').replace('h3', 'HTTP/3').upper())

            if 'httpVersion' in res and res['httpVersion'] != '':
                result[req_domain]['protocols'].append(res['httpVersion'].replace('h2', 'HTTP/2').replace('h3', 'HTTP/3').upper())

            if 'serverIPAddress' in entry:
                if ':' in entry['serverIPAddress']:
                    result[req_domain]['ip-versions'].append('IPv6')
                else:
                    result[req_domain]['ip-versions'].append('IPv4')

            scheme = f'{o.scheme.lower()}:'
            if scheme not in result[org_domain]['csp-findings']['scheme-sources'] and scheme != 'http:':
                result[org_domain]['csp-findings']['scheme-sources'].append(scheme)
                csp_findings_match = True

            for header in res['headers']:
                if 'name' not in header:
                    continue

                if 'value' not in header:
                    continue

                name = header['name'].lower()
                value = header['value'].strip()

                if 'HSTS' not in result[req_domain]['features'] and 'strict-transport-security' in name:
                    sections = header['value'].split(';')
                    for section in sections:
                        section = section.strip()

                        pair = section.split('=')

                        name = pair[0]
                        value = None
                        if len(pair) == 2:
                            value = pair[1]

                        if 'max-age' == name:
                            result[req_domain]['features'].append('HSTS-HEADER-MAXAGE-FOUND')
                            try:
                                maxage = int(value)
                                # 1 month =   2628000
                                # 6 month =  15768000
                                # check if maxage is more then 1 year
                                if maxage >= 31536000:
                                    result[req_domain]['features'].append('HSTS-HEADER-MAXAGE-1YEAR')
                                elif maxage < 2628000:
                                    result[req_domain]['features'].append('HSTS-HEADER-MAXAGE-1MONTH')
                                elif maxage < 15768000:
                                    result[req_domain]['features'].append('HSTS-HEADER-MAXAGE-6MONTHS')
                                else:
                                    result[req_domain]['features'].append('HSTS-HEADER-MAXAGE-TOO-LOW')

                                result[req_domain]['features'].append('HSTS')
                            except:
                                a = 1
                        elif 'includeSubDomains' == name:
                            result[req_domain]['features'].append('HSTS-HEADER-SUBDOMAINS-FOUND')
                        elif 'preload' == name:
                            result[req_domain]['features'].append('HSTS-HEADER-PRELOAD-FOUND')
                elif 'location' in name:
                    if value.startswith('https://{0}'.format(req_domain)):
                        result[req_domain]['schemes'].append('HTTPS-REDIRECT')
                    elif value.startswith('https://') and req_scheme == 'http':
                        result[req_domain]['schemes'].append('HTTPS-REDIRECT-OTHERDOMAIN')
                        result[req_domain]['features'].append('INVALIDATE-HSTS')
                    elif value.startswith('http://{0}'.format(req_domain)):
                        if req_url.startswith('https://'):
                            result[req_domain]['schemes'].append('HTTP-REDIRECT')
                        else:
                            result[req_domain]['schemes'].append('HTTP-REDIRECT')
                            result[req_domain]['features'].append('INVALIDATE-HSTS')
                    elif value.startswith('http://'):
                        result[req_domain]['schemes'].append('HTTP-REDIRECT-OTHERDOMAIN')
                        result[req_domain]['features'].append('INVALIDATE-HSTS')

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
                    result[req_domain]['features'].append('HTML-FOUND')
                    content = res['content']['text']
                    regex = r'<meta http-equiv=\"(?P<name>Content-Security-Policy)\" content=\"(?P<value>[^\"]{5,1000})\"'
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
                    
                    regex = r'(?P<raw><(?P<type>style|link|script|img|iframe|form|base|frame)[^>]*((?P<attribute>src|nonce|action|href)="(?P<value>[^"]+)"[^>]*>))'
                    matches = re.finditer(regex, content, re.MULTILINE)
                    for _, match in enumerate(matches, start=1):
                        element_name = match.group('type').lower()
                        attribute_name = match.group('attribute').lower()
                        attribute_value = match.group('value').lower()
                        # element_raw = match.group('raw').lower()

                        element_url = url_2_host_source(attribute_value, req_domain)
                        o = urllib.parse.urlparse(element_url)
                        element_domain = o.hostname
                        if element_domain == None and element_url.startswith('data:'):
                            element_domain = 'data:'
                        elif element_domain == org_domain:
                            element_domain = '\'self\''

                        if attribute_name == 'nonce':
                            key = '\'nonce-<your-nonce>\'|{0}'.format(element_name)
                            if key not in result[org_domain]['csp-findings']['quotes']:
                                result[org_domain]['csp-findings']['quotes'].append(key)
                            csp_findings_match = True
                        elif attribute_name == 'src':
                            if element_domain != None:
                                key = '{0}|{1}'.format(element_domain, element_name)
                                if key not in result[org_domain]['csp-findings']['host-sources']:
                                    result[org_domain]['csp-findings']['host-sources'].append(key)
                                csp_findings_match = True
                        # Commenting out this part as it got too many false positives (meaning, got 'self' but matched 'sha-<hash>' for example)
                        # elif attribute_name == 'href':
                        #     if 'link' == element_name:
                        #         if 'rel="stylesheet"' in element_raw or 'as="style"' in element_raw:
                        #             element_name = 'style'
                        #         elif 'rel="icon"' in element_raw or 'as="image"' in element_raw or 'type="image/' in element_raw:
                        #             element_name = 'img'
                        #         elif 'as="script"' in element_raw:
                        #             element_name = 'script'
                        #         # elif 'as="font"' in element_raw or 'type="font' in element_raw:
                        #         #     element_name = 'font'
                        #         elif 'rel="stylesheet"="script"' in element_raw:
                        #             element_name = 'script'
                        #         else:
                        #             continue

                        #     key = '{0}|{1}'.format(element_domain, element_name)
                        #     if key not in result[org_domain]['csp-findings']['host-sources']:
                        #         result[org_domain]['csp-findings']['host-sources'].append(key)
                        elif attribute_name == 'action' and element_name == 'form':
                            key = '{0}|form-action'.format(element_domain)
                            if key not in result[org_domain]['csp-findings']['host-sources']:
                                result[org_domain]['csp-findings']['host-sources'].append(key)
                            csp_findings_match = True

                    regex = r'<(?P<type>style|script|form)>'
                    matches = re.finditer(regex, content, re.DOTALL | re.IGNORECASE | re.MULTILINE)
                    for matchNum, match in enumerate(matches, start=1):
                        element_name = match.group('type').lower()
                        if element_name == 'style' or element_name == 'script':
                            key = '\'unsafe-inline\'|{0}'.format(element_name)
                            if key not in result[org_domain]['csp-findings']['quotes']:
                                result[org_domain]['csp-findings']['quotes'].append(key)
                            csp_findings_match = True
                        elif attribute_name == 'action' and element_name == 'form':
                            element_url = url_2_host_source(req_url, req_domain)
                            o = urllib.parse.urlparse(element_url)
                            element_domain = o.hostname
                            if element_domain == org_domain:
                                key = '\'self\'|{0}'.format(element_name)
                                if key not in result[org_domain]['csp-findings']['quotes']:
                                    result[org_domain]['csp-findings']['quotes'].append(key)
                                csp_findings_match = True
                            else:
                                key = '{0}|{1}'.format(element_domain, element_name)
                                if key not in result[org_domain]['csp-findings']['host-sources']:
                                    result[org_domain]['csp-findings']['host-sources'].append(key)
                                csp_findings_match = True

                elif 'mimeType' in res['content'] and 'text/css' in res['content']['mimeType']:
                    content = res['content']['text']
                    if 'data:image' in content:
                        key = 'data:|img'
                        if key not in result[org_domain]['csp-findings']['scheme-sources']:
                            result[org_domain]['csp-findings']['scheme-sources'].append(key)
                        csp_findings_match = True
                    element_name = 'style'
                    if element_domain == org_domain:
                        key = '\'self\'|{0}'.format(element_name)
                        if key not in result[org_domain]['csp-findings']['quotes']:
                            result[org_domain]['csp-findings']['quotes'].append(key)
                        csp_findings_match = True
                    else:
                        key = '{0}|{1}'.format(element_domain, element_name)
                        if key not in result[org_domain]['csp-findings']['host-sources']:
                            result[org_domain]['csp-findings']['host-sources'].append(key)
                        csp_findings_match = True
                elif 'mimeType' in res['content'] and ('text/javascript' in res['content']['mimeType'] or 'application/javascript' in res['content']['mimeType']):
                    content = res['content']['text']
                    if 'eval(' in content:
                        key = '\'unsafe-eval\'|script'
                        if key not in result[org_domain]['csp-findings']['quotes']:
                            result[org_domain]['csp-findings']['quotes'].append(key)
                        csp_findings_match = True

                    element_domain = req_domain
                    element_name = 'script'
                    if element_domain == org_domain:
                        key = '\'self\'|{0}'.format(element_name)
                        if key not in result[org_domain]['csp-findings']['quotes']:
                            result[org_domain]['csp-findings']['quotes'].append(key)
                        csp_findings_match = True
                    else:
                        key = '{0}|{1}'.format(element_domain, element_name)
                        if key not in result[org_domain]['csp-findings']['host-sources']:
                            result[org_domain]['csp-findings']['host-sources'].append(key)
                        csp_findings_match = True
            if 'mimeType' in res['content'] and 'image/' in res['content']['mimeType']:
                element_domain = req_domain
                element_name = 'img'
                if element_domain == org_domain:
                    key = '\'self\'|{0}'.format(element_name)
                    if key not in result[org_domain]['csp-findings']['quotes']:
                        result[org_domain]['csp-findings']['quotes'].append(key)
                    csp_findings_match = True
                else:
                    key = '{0}|{1}'.format(element_domain, element_name)
                    if key not in result[org_domain]['csp-findings']['host-sources']:
                        result[org_domain]['csp-findings']['host-sources'].append(key)
                    csp_findings_match = True
            elif ('mimeType' in res['content'] and 'font/' in res['content']['mimeType']) or req_url.endswith('.otf') or req_url.endswith('.woff') or req_url.endswith('.woff2'):
                element_domain = req_domain
                element_name = 'font'
                # woff and woff2 support is in all browser, add hash to our csp-findings
                has_font_hash = False
                if req_url.endswith('.woff') or req_url.endswith('.woff2') or 'font-woff' in res['content']['mimeType'] or 'font/woff' in res['content']['mimeType']:
                    key = '{0}|{1}'.format(req_url, element_name)
                    if key not in result[org_domain]['csp-findings']['font-sources']:
                        font_content = None
                        font_hash = None
                        if 'text' in res['content'] and 'encoding' in res['content'] and res['content']['encoding'] == 'base64':
                            # we have base64 encoded content, decode it, calcuclate sha256 and add it.
                            font_content = base64.decodebytes(res['content']['text'].encode('utf-8'))
                            font_hash = create_sha256_hash(font_content)
                            key2 = '{0}|{1}'.format("'sha256-{0}'".format(font_hash), element_name)
                            if key not in result[org_domain]['csp-findings']['quotes']:
                                result[org_domain]['csp-findings']['quotes'].append(key2)
                                result[org_domain]['csp-findings']['font-sources'].append(key)
                            has_font_hash = True
                    else:
                        has_font_hash = True
                    csp_findings_match = True
                if not has_font_hash:
                    if element_domain == org_domain:
                        key = '\'self\'|{0}'.format(element_name)
                        if key not in result[org_domain]['csp-findings']['quotes']:
                            result[org_domain]['csp-findings']['quotes'].append(key)
                        csp_findings_match = True
                    else:
                        key = '{0}|{1}'.format(element_domain, element_name)
                        if key not in result[org_domain]['csp-findings']['host-sources']:
                            result[org_domain]['csp-findings']['host-sources'].append(key)
                        csp_findings_match = True


            if not csp_findings_match:
                element_name = 'connect'
                if req_domain == org_domain:
                    key = '\'self\'|{0}'.format(element_name)
                    if key not in result[org_domain]['csp-findings']['quotes']:
                        result[org_domain]['csp-findings']['quotes'].append(key)
                    csp_findings_match = True
                else:
                    key = '{0}|{1}'.format(req_domain, element_name)
                    if key not in result[org_domain]['csp-findings']['host-sources']:
                        result[org_domain]['csp-findings']['host-sources'].append(key)
                    csp_findings_match = True





            result[req_domain]['protocols'] = list(set(result[req_domain]['protocols']))
            result[req_domain]['schemes'] = list(set(result[req_domain]['schemes']))
            result[req_domain]['ip-versions'] = list(set(result[req_domain]['ip-versions']))

    result['visits'] = 1

    return result

def create_sha256_hash(data):
    sha_signature = hashlib.sha256(data).digest()
    base64_encoded_sha_signature = base64.b64encode(sha_signature).decode()
    return base64_encoded_sha_signature

def validate_dnssec(domain, domain_entry):
    # subdomain = 'static.internetstiftelsen.se'
    # domain = 'internetstiftelsen.se'
    print('  ', domain)

    # Get the name object for 'www.example.com'
    # name = dns.name.from_text(domain)

    # response_dnskey_ns = testdns(name, dns.rdatatype.NS, True)
    # response_dnskey_dnssec = testdns(name, dns.rdatatype.DNSKEY, True)
    # response_dnskey_dnssec = testdns(name, dns.rdatatype.DNSKEY, False)
    # response_dnskey_cname = testdns(name, dns.rdatatype.CNAME, True)
    # response_dnskey_a = testdns(name, dns.rdatatype.A, True)
    # response_dnskey_aaaa = testdns(name, dns.rdatatype.AAAA, True)
    # response_dnskey_soa = testdns(name, dns.rdatatype.SOA, True)
    # response_dnskey_txt = testdns(name, dns.rdatatype.TXT, True)
    # response_dnskey_mx = testdns(name, dns.rdatatype.MX, True)
    # response_dnskey_ds = testdns(name, dns.rdatatype.DS, True)


    # Get the DNSKEY for the domain
    # dnskeys = []
    # if dnskeys_response.rcode() != 0:
    #     # HANDLE QUERY FAILED (SERVER ERROR OR NO DNSKEY RECORD)
    #     print('\t\tA.1', dnskeys_response.rcode())
    #     domain_entry['features'].append('DNSSEC-NO-DNSKEY(S):{0}'.format(nsname))
    #     return domain_entry
    #     # continue
    # else:
    #     print('\t\tA.2', dnskeys_response.rcode())
    #     domain_entry['features'].append('DNSSEC-DNSKEYS:{0}'.format(nsname))
    #     dnskeys = dnskeys_response.answer
    
    # # Get the DS for the domain
    # ds_answer = dns.resolver.resolve(subdomain, dns.rdatatype.DS)

    # request = dns.message.make_query(domain, dns.rdatatype.A, want_dnssec=True)
    # request = dns.message.make_query(domain, dns.rdatatype.DNSKEY, want_dnssec=True)

    domain_name = dns.name.from_text(domain)
    request = dns.message.make_query(domain_name, dns.rdatatype.DNSKEY, want_dnssec=True)
    # request = dns.message.make_query(domain_name, dns.rdatatype.A, want_dnssec=True)
    #request = dns.message.make_query(domain_name, dns.rdatatype.A, want_dnssec=True)
    response = dns.query.udp(request, '8.8.8.8')

    nsname = '8.8.8.8'

    if response.rcode() != 0:
        # HANDLE QUERY FAILED (SERVER ERROR OR NO DNSKEY RECORD)
        print('\tERROR, RCODE is INVALID:', response.rcode())
        domain_entry['features'].append('DNSSEC-NO-RCODE:{0}'.format(nsname))
        return domain_entry
        # continue
    else:
        print('\tVALID RCODE')
        domain_entry['features'].append('DNSSEC-RCODE:{0}'.format(nsname))

    dnskey = None
    rrsig = None

    # print('E', answer)
    if len(response.answer) < 2:
        # SOMETHING WENT WRONG
        print('\tWARNING, to few answers:', len(response.answer))

        # find the associated RRSIG RRset
        rrsig = None

        print('\t\tQ.answer', response.answer)
        print('\t\tQ.authority', response.authority)
        print('\t\tQ.additional', response.additional)


        print('\tRRSET(s):')
        for rrset in response.answer + response.authority + response.additional:
            print('\t\tRRSET:', rrset)
            if rrset.rdtype == dns.rdatatype.RRSIG:
                rrsig = rrset
                print('\t\t\tRRSIG found')
                domain_entry['features'].append('DNSSEC-RRSIG-FOUND')
            if rrset.rdtype == dns.rdatatype.DNSKEY:
                dnskey = rrset
                print('\t\tDNSKEY found')
                domain_entry['features'].append('DNSSEC-DNSKEY-FOUND')

        domain_entry['features'].append('DNSSEC-NO-ANSWER:{0}'.format(nsname))
        return domain_entry
        # continue
    else:
        print('\tParsing Answers, nof answers:', len(response.answer))

        # find DNSKEY and RRSIG in answer
        # dnskey = None
        # rrsig = None
        for rrset in response.answer:
            print('\tRRSET', rrset)
            if dnskey == None and rrset.rdtype == dns.rdatatype.DNSKEY:
                dnskey = rrset
                print('\t\tDNSKEY found')
                domain_entry['features'].append('DNSSEC-DNSKEY-FOUND')
            elif rrsig == None and rrset.rdtype == dns.rdatatype.RRSIG:
                rrsig = rrset
                print('\t\tRRSIG found')
                domain_entry['features'].append('DNSSEC-RRSIG-FOUND')

        domain_entry['features'].append('DNSSEC-ANSWER:{0}'.format(nsname))

        # # validate the answer
        # if rrsig is not None:                       

    # if dnskey == None and len(dnskeys) > 0:
    #     print('\tNO DNS KEY')
    #     dnskey = dnskeys[0]
    print('\n\n')
    print('\t# {0} - DNSKEY ='.format(domain), dnskey)
    print('\t# {0} - RRSIG = '.format(domain), rrsig)

    # import dns.zone

    # Validate the DNSKEY with the DS
    if dnskey == None:
        print('\tRETRY DNSKEY')
        validate_rrsig_no_dnskey(domain, rrsig, domain_entry)
    else:
        validate_dnskey_and_rrsig(domain, dnskey, rrsig, domain_entry)
    # try:
    #     dns.dnssec.validate(dnskey, rrsig, dnskey)
    #     # dns.dnssec.validate(dnskey, rrsig, {name: dnskey})
    #     # dns.dnssec.validate(dnskey, rrsig)
    #     print("DNSSEC validation passed")
    # except dns.dnssec.ValidationFailure as vf:
    #     print('DNSSEC VALIDATION FAIL', vf)
    #     domain_entry['features'].append('DNSSEC-FALIED-VALIDATION:{0}'.format(nsname))
    # else:
    #     domain_entry['features'].append('DNSSEC')
    #     print('\t\tG.3 - VALIDATION SUCCESS\r\n')

    # print('\t3')

def testdns(key, datatype, use_dnssec):
    try:
        query = None

        print('     testdns', key, datatype, use_dnssec)

        # Create a query for the 'www.example.com' domain
        if use_dnssec:
            query = dns.message.make_query(key, datatype, want_dnssec=True)
        else:
            query = dns.message.make_query(key, datatype, want_dnssec=False)

        # Send the query and get the response
        response = dns.query.udp(query, '8.8.8.8')

        if response.rcode() != 0:
            # HANDLE QUERY FAILED (SERVER ERROR OR NO DNSKEY RECORD)
            print('\tERROR, RCODE is INVALID:', response.rcode())
            return None
            # continue

        # Get the answer section from the response
        # answer_section = response.answer

        print('\tanswer')
        print('\t\tanswer.length', len(response.answer))
        for answer in response.answer:
            print('\t\t\tanswer', answer)

        return response.answer

    except dns.dnssec.ValidationFailure as vf:
        print('\t\t\tDNS FAIL', vf)
    except Exception as ex:
        print('\t\t\tDNS GENERAL FAIL', ex)

    return None

def validate_rrsig_no_dnskey(domain, rrsig, domain_entry):
    nsname = '8.8.8.8'
    try:
        #dns.dnssec.validate(dnskey, rrsig, dnskey)
        import dns.message
        # Create a query for the 'www.example.com' domain
        query = dns.message.make_query(domain, dns.rdatatype.A, want_dnssec=True)

        # Send the query and get the response
        response = dns.query.udp(query, '8.8.8.8')

        # Get the answer section from the response
        answer_section = response.answer

        # Get the name object for 'www.example.com'
        name = dns.name.from_text(domain)

        # Get the RRset from the answer section
        rrset = response.get_rrset(answer_section, name, dns.rdataclass.IN, dns.rdatatype.DNSKEY)        

        # name = dns.name.from_text(domain)
        # Assuming 'answers' is an dns.resolver.Answer object containing the DNSKEY records
        # rrset = answers.get_rrset(dnskeys, name, dns.rdataclass.IN, dns.rdatatype.DNSKEY)
        dns.dnssec.validate(rrset, rrsig, {name: rrset})        
        # name = dns.name.from_text(domain)
        # dns.dnssec.validate(dnskey, rrsig, {name, dnskey})
        # dns.dnssec.validate(dnskey, rrsig)
        print("\t\t\tDNSSEC validation passed")
    except dns.dnssec.ValidationFailure as vf:
        print('\t\t\tDNSSEC VALIDATION FAIL', vf)
        domain_entry['features'].append('DNSSEC-FALIED-VALIDATION:{0}'.format(nsname))
    except Exception as ex:
        print('\t\t\tDNSSEC GENERAL FAIL', ex)
        domain_entry['features'].append('DNSSEC-FALIED-VALIDATION:{0}'.format(nsname))
    else:
        domain_entry['features'].append('DNSSEC')
        print('\t\tG.3 - VALIDATION SUCCESS\r\n')

def validate_dnskey_and_rrsig(domain, dnskey, rrsig, domain_entry):
    nsname = '8.8.8.8'
    try:
        #dns.dnssec.validate(dnskey, rrsig, dnskey)
        name = dns.name.from_text(domain)
        dns.dnssec.validate(dnskey, rrsig, {name: dnskey})
        # dns.dnssec.validate(dnskey, rrsig)
        print("\t\t\tDNSSEC validation passed")
    except dns.dnssec.ValidationFailure as vf:
        print('\t\t\tDNSSEC VALIDATION FAIL', vf)
        domain_entry['features'].append('DNSSEC-FALIED-VALIDATION:{0}'.format(nsname))
    else:
        domain_entry['features'].append('DNSSEC')
        print('\t\tG.3 - VALIDATION SUCCESS\r\n')

def check_dnssec(hostname, result_dict):
    print('DNSSEC')
    new_entries = []
    for domainA in result_dict.keys():
        try:
            domain = domainA
            domain_entry = result_dict[domain]

            if hostname != domain:
                domain_entry['features'].append('DNSSEC-IGNORE')
                continue
            # print('# {0}'.format(domain))
            validate_dnssec(domain, domain_entry)

        except Exception as e:
            print('DNSSEC EXCEPTION', e)
    for entry in new_entries:
        name = entry['name']
        del entry['name']
        result_dict[name] = entry
        
    return result_dict

def check_dnssec2(hostname, result_dict):
    print('DNSSEC')

    # NOTE: https://www.cloudflare.com/dns/dnssec/how-dnssec-works/
    # NOTE: https://github.com/dnsviz/dnsviz/blob/master/dnsviz/resolver.py
    
    # TODO: DNSSEC (BUT NOT ON ALL NAMESERVERS: internetstiftelsen.se)

    # To facilitate signature validation, DNSSEC adds a few new DNS record types4:

    # RRSIG - Contains a cryptographic signature
    # DNSKEY - Contains a public signing key
    # DS - Contains the hash of a DNSKEY record
    # NSEC and NSEC3 - For explicit denial-of-existence of a DNS record
    # CDNSKEY and CDS - For a child zone requesting updates to DS record(s) in the parent zone
    # get nameservers for target domain




    # IMPROVE DNSSEC QUERIES:
    # Analyzing polisen.se
    # Querying polisen.se/NS (referral)...
    # Querying polisen.se/NS (auth, detecting cookies)...
    # Querying polisen.se/A...
    # Preparing 0x20 query PoLISEN.SE/SOA...
    # Preparing DNS cookie diagnostic query polisen.se/SOA...
    # Preparing query polisen.se/NSEC3PARAM...
    # Preparing query hfsp0za3wj.polisen.se/A (NXDOMAIN)...
    # Preparing query polisen.se/CNAME (NODATA)...
    # Preparing query polisen.se/MX...
    # Preparing query polisen.se/TXT...
    # Preparing query polisen.se/SOA...
    # Preparing query polisen.se/DNSKEY...
    # Preparing query polisen.se/DS...
    # Preparing query polisen.se/AAAA...
    # Executing queries...
    # Analysis Complete
    

    # Analyzing eskilstuna.se
    # Querying eskilstuna.se/NS (referral)...
    # Querying eskilstuna.se/NS (auth, detecting cookies)...
    # Querying eskilstuna.se/A...
    # Preparing 0x20 query EsKILStUNa.sE/SOA...
    # Preparing DNS cookie diagnostic query eskilstuna.se/SOA...
    # Preparing query eskilstuna.se/NSEC3PARAM...
    # Preparing query 5gweac9poq.eskilstuna.se/A (NXDOMAIN)...
    # Preparing query eskilstuna.se/CNAME (NODATA)...
    # Preparing query eskilstuna.se/MX...
    # Preparing query eskilstuna.se/TXT...
    # Preparing query eskilstuna.se/SOA...
    # Preparing query eskilstuna.se/DNSKEY...
    # Preparing query eskilstuna.se/DS...
    # Preparing query eskilstuna.se/AAAA...
    # Executing queries...
    # Analyzing www.eskilstuna.se
    # Querying www.eskilstuna.se/NS (referral)...
    # Preparing query www.eskilstuna.se/A...
    # Preparing query www.eskilstuna.se/AAAA...
    # Executing queries...
    # Analysis Complete    



    import dns.zone

    new_entries = []
    for domainA in result_dict.keys():
        try:
            domain = domainA
            domain_entry = result_dict[domain]

            if hostname != domain:
                domain_entry['features'].append('DNSSEC-IGNORE')
                continue

            # validate_dnssec(domain)
            print('# {0}'.format(domain))

            # if 'svanalytics.piwik.pro' == domainA:
            #     domain = 'piwik.pro'
            #     domain_entry = {
            #         'name': domain,
            #         'protocols': [],
            #         'schemes': [],
            #         'ip-versions': [],
            #         'transport-layers': [],
            #         'features': [],
            #         'urls': []
            #     }
            #     new_entries.append(domain_entry)
            # domain_entry = result_dict[domain]

            dnskeys = dns_lookup(domain, dns.rdatatype.DNSKEY)
            # print('\t\tDNSKEY', dnskey)
            print('\tDNSKEY(S):', len(dnskeys))
            if len(dnskeys) == 0:
                domain_entry['features'].append('DNSSEC-NO-DNSKEY')
            else:
                domain_entry['features'].append('DNSSEC-DNSKEY')

            import dns.resolver

            resolver = dns.resolver.Resolver()
            # resolver.nameservers = [ '8.8.8.8' ]

            response = resolver.query('{0}.'.format(domain), dns.rdatatype.NS)
            nsnames = dns_lookup('{0}.'.format(domain), dns.rdatatype.NS)
            print('\tNAMESERVER(S):', len(nsnames))

            # we'll use the first nameserver in this example
            # nof_nsnames = len(response.rrset)
            #nsnames = []
            for nsname in nsnames:
                #nsnames.append(entry.to_text())

                # print('A', nsnames)
                # nsname = entry.to_text()  # name
                #nsname = response.rrset[1].to_text()  # name
                print('\tA', nsname)

                # test = dns_lookup(domain, dns.rdatatype.RRSIG)
                # print('\t\tRRSIG', test)


                # get DNSKEY for zone
                # ADDITIONAL_RDCLASS = 4096
                # request = dns.message.make_query('{0}.'.format(domain), dns.rdatatype.A, want_dnssec=True)
                # request.flags |= dns.flags.AD
                # request.find_rrset(request.additional, dns.name.root, ADDITIONAL_RDCLASS,
                #                 dns.rdatatype.OPT, create=True, force_unique=True)                
                request = dns.message.make_query(domain, dns.rdatatype.DNSKEY, want_dnssec=True)
                # request = dns.message.make_query(domain, dns.rdatatype.A, want_dnssec=True)
                # request = dns.message.make_query(domain, dns.rdatatype.DNSKEY)
                # name = dns.name.from_text('{0}.'.format(domain))
                name = dns.name.from_text(domain)
                print('\t\tA.1', name)
                # print('\t\tA.1.1', domain_entry)


                if 'IPv4' in domain_entry['ip-versions'] or 'IPv4*' in domain_entry['ip-versions']:
                    # print('\t\tA.2')
                    response = resolver.query(nsname, dns.rdatatype.A)
                    print('\t\tA.3', response)
                    nsaddr = response.rrset[0].to_text()  # IPv4

                    print('\t\tA.4', nsaddr)

                    # send the query
                    response = dns.query.udp(request, nsaddr)
                    # response = dns.query.udp(request, '8.8.8.8')

                    # print('\t\tA.5', response)
                    print('\t\tA.5')

                    if response.rcode() != 0:
                        # HANDLE QUERY FAILED (SERVER ERROR OR NO DNSKEY RECORD)
                        print('\t\tD.1', response.rcode())
                        domain_entry['features'].append('DNSSEC-NO-RCODE:{0}'.format(nsname))
                        continue
                    else:
                        print('\t\tD.2', response.rcode())
                        domain_entry['features'].append('DNSSEC-RCODE:{0}'.format(nsname))

                    # answer should contain two RRSET: DNSKEY and RRSIG (DNSKEY)
                    # answer = response.answer
                    dnskey = None
                    rrsig = None

                    # print('E', answer)
                    if len(response.answer) < 2:
                        # SOMETHING WENT WRONG
                        print('\t\tE.1', len(response.answer))

                        # find the associated RRSIG RRset
                        rrsig = None

                        print('\t\t\tQ.answer', response.answer)
                        print('\t\t\tQ.authority', response.authority)
                        print('\t\t\tQ.additional', response.additional)

                        for rrset in response.answer + response.authority + response.additional:
                            print('\t\tE.2', rrset)
                            if rrset.rdtype == dns.rdatatype.RRSIG:
                                rrsig = rrset
                                break


                        domain_entry['features'].append('DNSSEC-NO-ANSWER:{0}'.format(nsname))
                        continue
                    else:
                        print('\t\tE.2', len(response.answer))

                        # find DNSKEY and RRSIG in answer
                        dnskey = None
                        rrsig = None
                        for rrset in response.answer:
                            if rrset.rdtype == dns.rdatatype.DNSKEY:
                                dnskey = rrset
                            elif rrset.rdtype == dns.rdatatype.RRSIG:
                                rrsig = rrset
                        domain_entry['features'].append('DNSSEC-ANSWER:{0}'.format(nsname))

                        # # validate the answer
                        # if rrsig is not None:                       

                    if dnskey == None and len(dnskeys) > 0:
                        dnskey = dnskeys[0]

                    # the DNSKEY should be self-signed, validate it
                    try:
                        # print('F')
                        # dns.dnssec.validate(answer[0], answer[1], {name: answer[0]})

                        print('\t\tF.1', dnskey)
                        print('\t\tF.2', rrsig)


                        # dns.dnssec.validate(answer, rrsig)
                        dns.dnssec.validate(dnskey, rrsig, {name: dnskey})
                        print('\t\tG.1\r\n')
                    except dns.dnssec.ValidationFailure as vf:
                        # BE SUSPICIOUS
                        a = False
                        # print('G VALIDATION FAIL')
                        print('DNSSEC VALIDATION FAIL', vf)
                        domain_entry['features'].append('DNSSEC-FALIED-VALIDATION:{0}'.format(nsname))
                        print('\t\tG.2 - VALIDATION FAIL\r\n')
                    else:
                        # WE'RE GOOD, THERE'S A VALID DNSSEC SELF-SIGNED KEY FOR example.com
                        # print('G VALIDATION SUCCESS')
                        domain_entry['features'].append('DNSSEC')
                        domain_entry['features'].append('DNSSEC:{0}'.format(nsname))
                        print('\t\tG.3 - VALIDATION SUCCESS\r\n')
                        
                        # a = True

            # if 'IPv6' in result_dict[domain]['ip-versions'] or 'IPv6*' in result_dict[domain]['ip-versions']:
            #     b = 1
            #     print('B IPv6')
        except Exception as e:
            print('DNSSEC EXCEPTION', e)

    for entry in new_entries:
        name = entry['name']
        del entry['name']
        result_dict[name] = entry
        
    return result_dict

def check_csp(url):
    # Firefox
    # dom.security.https_only_mode

    o = urllib.parse.urlparse(url)
    o_domain = o.hostname

    browser = 'firefox'
    configuration = ''
    print('CSP ONLY', o_domain)
    result_dict = get_website_support_from_sitespeed(url, o_domain, configuration, browser, SITESPEED_TIMEOUT)

    return result_dict


def check_http_to_https(url):
    # Firefox
    # dom.security.https_only_mode

    http_url = ''

    o = urllib.parse.urlparse(url)
    o_domain = o.hostname

    if (o.scheme == 'https'):
        http_url = url.replace('https://', 'http://')
    else:
        http_url = url

    browser = 'firefox'
    configuration = ''
    print('HTTP', o_domain)
    result_dict = get_website_support_from_sitespeed(http_url, o_domain, configuration, browser, SITESPEED_TIMEOUT)

    # If website redirects to www. domain without first redirecting to HTTPS, make sure we test it.
    if o_domain in result_dict:
        if 'HTTPS' not in result_dict[o_domain]['schemes']:
            result_dict[o_domain]['schemes'].append('HTTP-REDIRECT*')
            https_url = url.replace('http://', 'https://')
            print('HTTPS', o_domain)
            result_dict = merge_dicts(get_website_support_from_sitespeed(https_url, o_domain, configuration, browser, SITESPEED_TIMEOUT), result_dict, True, True)
        else:
            result_dict[o_domain]['schemes'].append('HTTPS-REDIRECT*')

        # TODO: Should we add check for HSTS and if website is in preload list (example: start.stockholm)
        # being in preload list means http:// requests will be converted to https:// request before leaving browser.
        # preload list source can be collected here: https://source.chromium.org/chromium/chromium/src/+/main:net/http/transport_security_state_static.json
        # or is below good enough?
        if 'HTTP' not in result_dict[o_domain]['schemes']:
            result_dict[o_domain]['features'].append('HSTS-PRELOAD*')

    # If we have www. domain, ensure we validate HTTP2HTTPS on that as well
    www_domain_key = 'www.{0}'.format(o_domain)
    if www_domain_key in result_dict:
        if 'HTTP' not in result_dict[www_domain_key]['schemes']:
            result_dict[www_domain_key]['schemes'].append('HTTPS-REDIRECT*')
            www_http_url = http_url.replace(o_domain, www_domain_key)
            print('HTTP', www_domain_key)
            result_dict = merge_dicts(get_website_support_from_sitespeed(www_http_url, www_domain_key, configuration, browser, SITESPEED_TIMEOUT), result_dict, True, True)
        else:
            result_dict[www_domain_key]['schemes'].append('HTTP-REDIRECT*')


    domains = list(result_dict.keys())
    hsts_domains = []
    for domain in domains:
        if type(result_dict[domain]) != dict:
            continue

        if 'HSTS-HEADER-SUBDOMAINS-FOUND' in result_dict[domain]['features'] and 'HSTS' in result_dict[domain]['features']:
            hsts_domains.append(domain)

    for hsts_domain in hsts_domains:
        for domain in domains:
            if domain.endswith('.{0}'.format(hsts_domain)):
                result_dict[domain]['features'].append('HSTS-HEADER-ON-PARENTDOMAIN-FOUND')

    return result_dict

def check_ip_version(result_dict):
    # network.dns.ipv4OnlyDomains
    # network.dns.disableIPv6

    if not contains_value_for_all(result_dict, 'ip-versions', 'IPv4'):
        for domain in result_dict.keys():
            if type(result_dict[domain]) != dict:
                continue
            if 'IPv4' not in result_dict[domain]['ip-versions']:
                ip4_result = dns_lookup(domain, dns.rdatatype.A)
                if len(ip4_result) > 0:
                    result_dict[domain]['ip-versions'].append('IPv4*')

    if not contains_value_for_all(result_dict, 'ip-versions', 'IPv6'):
        for domain in result_dict.keys():
            if type(result_dict[domain]) != dict:
                continue
            if 'IPv6' not in result_dict[domain]['ip-versions']:
                ip4_result = dns_lookup(domain, dns.rdatatype.AAAA)
                if len(ip4_result) > 0:
                    result_dict[domain]['ip-versions'].append('IPv6*')

    return result_dict

def check_tls_version(url, domain, protocol_version, result_dict):
    protocol_rule = False
    protocol_name = ''

    try:
        if protocol_version == ssl.PROTOCOL_TLS:
            protocol_name = 'TLSv1.3'
            assert ssl.HAS_TLSv1_3
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2
        elif protocol_version == ssl.PROTOCOL_TLSv1_2:
            protocol_name = 'TLSv1.2'
            assert ssl.HAS_TLSv1_2
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_3
        elif protocol_version == ssl.PROTOCOL_TLSv1_1:
            protocol_name = 'TLSv1.1'
            assert ssl.HAS_TLSv1_1
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
        elif protocol_version == ssl.PROTOCOL_TLSv1:
            protocol_name = 'TLSv1.0'
            assert ssl.HAS_TLSv1
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
        elif protocol_version == ssl.PROTOCOL_SSLv3:
            protocol_name = 'SSLv3'
            assert ssl.HAS_SSLv3
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
        elif protocol_version == ssl.PROTOCOL_SSLv2:
            protocol_name = 'SSLv2'
            protocol_rule = ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
            assert ssl.HAS_SSLv2

        if has_tls_version(
            url, True, protocol_rule)[0]:
            result_dict[domain]['transport-layers'].append(protocol_name)
        elif has_tls_version(
            url, False, protocol_rule)[0]:
            result_dict[domain]['transport-layers'].append('{0}-'.format(protocol_name))

    except ssl.SSLError as sslex:
        print('error 0.0s', sslex)
        pass
    except AssertionError:
        print('### No {0} support on your machine, unable to test ###'.format(
            protocol_name))
        pass
    except:
        print('error protocol_version_score: {0}'.format(sys.exc_info()[0]))
        pass

    return result_dict

def check_tls_versions(result_dict):
    for domain in result_dict.keys():
        if type(result_dict[domain]) != dict:
            continue
        # TODO: Make sure to find https:// based url instead of creating one.
        https_url = result_dict[domain]['urls'][0].replace('http://', 'https://')
        result_dict = check_tls_version(https_url, domain, ssl.PROTOCOL_TLS, result_dict)
        result_dict = check_tls_version(https_url, domain, ssl.PROTOCOL_TLSv1_2, result_dict)
        result_dict = check_tls_version(https_url, domain, ssl.PROTOCOL_TLSv1_1, result_dict)
        result_dict = check_tls_version(https_url, domain, ssl.PROTOCOL_TLSv1, result_dict)

    # Firefox:
    # security.tls.version.min
    # security.tls.version.max

    # 1 = TLS 1.0
    # 2 = TLS 1.1
    # 3 = TLS 1.2
    # 4 = TLS 1.3

    # o = urllib.parse.urlparse(url)
    # domain = o.hostname

    # url = url.replace('http://', 'https://')

    # browser = 'firefox'
    # # configuration = ' --firefox.preference network.http.http2.enabled:false --firefox.preference network.http.http3.enable:false --firefox.preference network.http.version:1.1'
    # configuration = ' --firefox.preference security.tls.version.min:4 --firefox.preference security.tls.version.max:4'
    # url2 = change_url_to_test_url(url, 'TLS1_3')
    # print('TLS/1.3')
    # tls1_3_result = get_website_support_from_sitespeed(url2, configuration, browser, 2 * 60)
    # for domain in tls1_3_result.keys():
    #     result_dict[domain]['transport-layers'].append('TLSv1.3')

    # configuration = ' --firefox.preference security.tls.version.min:3 --firefox.preference security.tls.version.max:3'
    # url2 = change_url_to_test_url(url, 'TLS1_2')
    # print('TLS/1.2')
    # tls1_2_result = get_website_support_from_sitespeed(url2, configuration, browser, 2 * 60)
    # for domain in tls1_2_result.keys():
    #     result_dict[domain]['transport-layers'].append('TLSv1.2')

    # configuration = ' --firefox.preference security.tls.version.min:2 --firefox.preference security.tls.version.max:2'
    # url2 = change_url_to_test_url(url, 'TLS1_1')
    # print('TLS/1.1')
    # tls1_1_result = get_website_support_from_sitespeed(url2, configuration, browser, 2 * 60)
    # for domain in tls1_1_result.keys():
    #     result_dict[domain]['transport-layers'].append('TLSv1.1')

    # configuration = ' --firefox.preference security.tls.version.min:1 --firefox.preference security.tls.version.max:1'
    # url2 = change_url_to_test_url(url, 'TLS1_0')
    # print('TLS/1.0')
    # tls1_0_result = get_website_support_from_sitespeed(url2, configuration, browser, 2 * 60)
    # for domain in tls1_0_result.keys():
    #     result_dict[domain]['transport-layers'].append('TLSv1.0')

    # TODO: check cipher security
    # TODO: re add support for identify wrong certificate

    return result_dict

def get_website_support_from_sitespeed(url, org_domain, configuration, browser, timeout):
    # We don't need extra iterations for what we are using it for
    sitespeed_iterations = 1
    sitespeed_arg = '--plugins.remove screenshot --plugins.remove html --plugins.remove metrics --browsertime.screenshot false --screenshot false --screenshotLCP false --browsertime.screenshotLCP false --videoParams.createFilmstrip false --visualMetrics false --visualMetricsPerceptual false --visualMetricsContentful false --browsertime.headless true --utc true -n {0}'.format(
        sitespeed_iterations)

    if 'firefox' in browser:
        sitespeed_arg = '-b firefox --firefox.includeResponseBodies all --firefox.preference privacy.trackingprotection.enabled:false --firefox.preference privacy.donottrackheader.enabled:false --firefox.preference browser.safebrowsing.malware.enabled:false --firefox.preference browser.safebrowsing.phishing.enabled:false{1} {0}'.format(
            sitespeed_arg, configuration)
    else:
        sitespeed_arg = '-b chrome --chrome.cdp.performance false --browsertime.chrome.timeline false --browsertime.chrome.includeResponseBodies all --browsertime.chrome.args ignore-certificate-errors {0}'.format(
            sitespeed_arg)

    sitespeed_arg = '--shm-size=1g {0}'.format(
        sitespeed_arg)

    if 'nt' not in os.name:
        sitespeed_arg += ' --xvfb'

    (result_folder_name, filename) = get_result(
        url, SITESPEED_USE_DOCKER, sitespeed_arg, timeout)
    
    result = sitespeed_result_2_test_result(filename, org_domain)

    return result

def contains_value_for_all(result_dict, key, value):
    if result_dict == None:
        return False

    has_value = True    
    for domain in result_dict.keys():
        if type(result_dict[domain]) != dict:
            continue
        if key not in result_dict[domain] or value not in result_dict[domain][key]:
            has_value = False
    return has_value

def default_csp_policy_object():
    return {
            'all': [],
            'malformed': [],
            'hashes': [],
            'nounces': [],
            'wildcards': [],
            'domains': [],
            'schemes': [],
            'subdomains': [],
            'wildcard-subdomains': [],
        }

def default_csp_result_object(is_org_domain):
    obj = {
                    'protocols': [],
                    'schemes': [],
                    'ip-versions': [],
                    'transport-layers': [],
                    'features': [],
                    'urls': [],
                    'csp-policies': {}
                }
    if is_org_domain:
        obj['csp-findings'] = {
                            'quotes': [],
                            'host-sources': [],
                            'scheme-sources': [],
                            'font-sources': []
                        }
    return obj

def handle_csp_data(content, domain, result_dict, is_from_response_header, org_domain):
    # print('CSP', domain)
    # print('CSP', domain, content)
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP
    # https://scotthelme.co.uk/csp-cheat-sheet/
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/frame-ancestors

    parse_csp(content, domain, result_dict, is_from_response_header)

    # Add style-src policies to all who uses it as fallback
    ensure_csp_policy_fallbacks(domain, result_dict)

    # convert polices to objects
    convert_csp_policies_2_csp_objects(domain, result_dict, org_domain)

    return result_dict

def convert_csp_policies_2_csp_objects(domain, result_dict, org_domain):
    wildcard_org_domain = 'webperf-core-wildcard.{0}'.format(org_domain)
    subdomain_org_domain = '.{0}'.format(org_domain)

    for policy_name, items in result_dict[domain]['csp-policies'].items():
        policy_object = default_csp_policy_object()
        for value in items:
            policy_object['all'].append(value)
            if value == '' or (value.startswith("'") and not value.endswith("'")) or (value.endswith("'") and not value.startswith("'")):
                # Malformed value, probably missing space or have two.
                policy_object['malformed'].append(value)
            elif value.startswith("'sha256-") or value.startswith("'sha384-") or value.startswith("'sha512-"):
                policy_object['hashes'].append(value)
            elif "'nonce-" in value:
                policy_object['nounces'].append(value)
            else:
                if '*' in value:
                    policy_object['wildcards'].append(value)
                if '.' in value:
                    try:
                        host_source_url = host_source_2_url(value)
                        host_source_o = urllib.parse.urlparse(host_source_url)
                        host_source_hostname = host_source_o.hostname
                        if host_source_hostname.endswith(wildcard_org_domain):
                            policy_object['wildcard-subdomains'].append(value)
                        elif host_source_hostname.endswith(subdomain_org_domain):
                            policy_object['subdomains'].append(value)
                        else:
                            policy_object['domains'].append(value)
                    except:
                        policy_object['domains'].append(value)
                    
                scheme = re.match(r'^(?P<scheme>[a-z]+)\:', value)
                if scheme != None:
                    policy_object['schemes'].append(value)
        
        if 'csp-objects' not in result_dict[domain]:
            result_dict[domain]['csp-objects'] = {}
        if policy_name not in result_dict[domain]['csp-objects']:
            result_dict[domain]['csp-objects'][policy_name] = policy_object
        else:
            result_dict[domain]['csp-objects'][policy_name].update(policy_object)

def ensure_csp_policy_fallbacks(domain, result_dict):
    if 'style-src' in result_dict[domain]['csp-policies']:
        style_items = result_dict[domain]['csp-policies']['style-src']
        append_csp_policy('style-src-attr', style_items, domain, result_dict)
        append_csp_policy('style-src-elem', style_items, domain, result_dict)

    # Add script-src policies to all who uses it as fallback
    if 'script-src' in result_dict[domain]['csp-policies']:
        script_items = result_dict[domain]['csp-policies']['script-src']
        append_csp_policy('script-src-attr', script_items, domain, result_dict)
        append_csp_policy('script-src-elem', script_items, domain, result_dict)
        append_csp_policy('worker-src', script_items, domain, result_dict)

    # Add child-src policies to all who uses it as fallback
    if 'child-src' in result_dict[domain]['csp-policies']:
        child_items = result_dict[domain]['csp-policies']['child-src']
        append_csp_policy('frame-src', child_items, domain, result_dict)
        append_csp_policy('worker-src', child_items, domain, result_dict)

    # Add default-src policies to all who uses it as fallback
    if 'default-src' in result_dict[domain]['csp-policies']:
        default_items = result_dict[domain]['csp-policies']['default-src']

        append_csp_policy('child-src', default_items, domain, result_dict)
        append_csp_policy('connect-src', default_items, domain, result_dict)
        append_csp_policy('font-src', default_items, domain, result_dict)
        append_csp_policy('frame-src', default_items, domain, result_dict)
        append_csp_policy('img-src', default_items, domain, result_dict)
        append_csp_policy('manifest-src', default_items, domain, result_dict)
        append_csp_policy('media-src', default_items, domain, result_dict)
        append_csp_policy('object-src', default_items, domain, result_dict)
        # comment out as it it deprecated
        # append_csp_policy('prefetch-src', default_items, domain, result_dict)
        append_csp_policy('script-src', default_items, domain, result_dict)
        append_csp_policy('script-src-elem', default_items, domain, result_dict)
        append_csp_policy('script-src-attr', default_items, domain, result_dict)
        append_csp_policy('style-src', default_items, domain, result_dict)
        append_csp_policy('style-src-elem', default_items, domain, result_dict)
        append_csp_policy('style-src-attr', default_items, domain, result_dict)
        append_csp_policy('worker-src', default_items, domain, result_dict)

def parse_csp(content, domain, result_dict, is_from_response_header):
    regex = r'(?P<name>(default-src|script-src|style-src|font-src|connect-src|frame-src|img-src|media-src|frame-ancestors|base-uri|form-action|block-all-mixed-content|child-src|connect-src|fenced-frame-src|font-src|img-src|manifest-src|media-src|object-src|plugin-types|prefetch-src|referrer|report-to|report-uri|require-trusted-types-for|sandbox|script-src-attr|script-src-elem|strict-dynamic|style-src-attr|style-src-elem|trusted-types|upgrade-insecure-requests|worker-src)) (?P<value>[^;]{5,1000})[;]{0,1}'
    matches = re.finditer(regex, content, re.MULTILINE | re.IGNORECASE)
    for matchNum, match in enumerate(matches, start=1):
        name = match.group('name')
        value = match.group('value')

        tmp_name = name.upper()
        policy_name = name.lower()

        if policy_name not in result_dict[domain]['csp-policies']:
            result_dict[domain]['csp-policies'][policy_name] = []

        if not is_from_response_header and (policy_name == 'frame-ancestors' or policy_name == 'report-uri' or policy_name == 'sandbox'):
            result_dict[domain]['features'].append('CSP-UNSUPPORTED-IN-META')
            result_dict[domain]['features'].append('CSP-UNSUPPORTED-IN-META-{0}'.format(tmp_name))

        values = value.split(' ')

        result_dict[domain]['csp-policies'][policy_name].extend(values)
        result_dict[domain]['csp-policies'][policy_name] = sorted(list(set(result_dict[domain]['csp-policies'][policy_name])))

def append_csp_policy(policy_name, items, domain, result_dict):
    if policy_name not in result_dict[domain]['csp-policies']:
        result_dict[domain]['csp-policies'][policy_name] = []

    if len(items) == 0:
        return
    
    if len(result_dict[domain]['csp-policies'][policy_name]) == 0:
        result_dict[domain]['csp-policies'][policy_name].extend(items)

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

    # Response Header: alt-svc
    # h3=\":443\"; ma=2592000, h3-29=\":443\"; ma=2592000, h3-Q050=\":443\"; ma=2592000, h3-Q046=\":443\"; ma=2592000, h3-Q043=\":443\"; ma=2592000, quic=\":443\"; ma=2592000; v=\"43,46\"
    # h3=":443";
    # ma=2592000, h3-29=":443";
    # ma=2592000, h3-Q050=":443";
    # ma=2592000, h3-Q046=":443";
    # ma=2592000, h3-Q043=":443";
    # ma=2592000, quic=":443";
    # ma=2592000; v="43,46"

    # https://www.http3check.net/?host=https%3A%2F%2Fwebperf.se
    # 0-RTT
    # H3
    # H3-29
    # H3-Q050
    # H3-Q046
    # H3-Q043
    # Q043
    # Q046

    o = urllib.parse.urlparse(url)
    o_domain = o.hostname


    if not contains_value_for_all(result_dict, 'protocols', 'HTTP/1.1'):
        browser = 'firefox'
        # configuration = ' --firefox.preference network.http.http2.enabled:false --firefox.preference network.http.http3.enable:false --firefox.preference network.http.version:1.1'
        configuration = ' --firefox.preference network.http.http2.enabled:false --firefox.preference network.http.http3.enable:false'
        url2 = change_url_to_test_url(url, 'HTTPv1')
        print('HTTP/1.1')
        result_dict = merge_dicts(get_website_support_from_sitespeed(url2, o_domain, configuration, browser, SITESPEED_TIMEOUT), result_dict, True, True)

    if not contains_value_for_all(result_dict, 'protocols', 'HTTP/2'):
        browser = 'firefox'
        configuration = ' --firefox.preference network.http.http2.enabled:true --firefox.preference network.http.http3.enable:false --firefox.preference network.http.version:3.0'
        url2 = change_url_to_test_url(url, 'HTTPv2')
        print('HTTP/2')
        result_dict = merge_dicts(get_website_support_from_sitespeed(url2, o_domain, configuration, browser, SITESPEED_TIMEOUT), result_dict, True, True)

    if not contains_value_for_all(result_dict, 'protocols', 'HTTP/3'):
        browser = 'firefox'
        configuration = ' --firefox.preference network.http.http2.enabled:false --firefox.preference network.http.http3.enable:true --firefox.preference network.http.version:3.0'
        url2 = change_url_to_test_url(url, 'HTTPv3')
        print('HTTP/3')
        result_dict = merge_dicts(get_website_support_from_sitespeed(url2, o_domain, configuration, browser, SITESPEED_TIMEOUT), result_dict, True, True)

    return result_dict

# Read post at: https://hussainaliakbar.github.io/restricting-tls-version-and-cipher-suites-in-python-requests-and-testing-wireshark/
WEAK_CIPHERS = (
    'ECDHE+AES128+CBC+SHA:'
    'ECDHE+AES256+CBC+SHA:'
    'ECDHE+RSA+3DES+EDE+CBC+SHA:'
    'ECDHE+RSA+AES256+GCM+SHA383:'
    'RSA+AES128+CBC+SHA:'
    'RSA+AES256+CBC+SHA:'
    'RSA+AES128+GCM+SHA256:'
    'RSA+AES256+GCM+SHA:'
    'RSA+AES256+GCM+SHA383:'
    'RSA+CAMELLIA128+CBC+SHA:'
    'RSA+CAMELLIA256+CBC+SHA:'
    'RSA+IDEA+CBC+SHA:'
    'RSA+AES256+GCM+SHA:'
    'RSA+3DES+EDE+CBC+SHA:'
    'RSA+SEED+CBC+SHA:'
    'DHE+RSA+3DES+EDE+CBC+SHA:'
    'DHE+RSA+AES128+CBC+SHA:'
    'DHE+RSA+AES256+CBC+SHA:'
    'DHE+RSA+CAMELLIA128+CBC+SHA:'
    'DHE+RSA+CAMELLIA256+CBC+SHA:'
    'DHE+RSA+SEED+CBC+SHA:'
)


class TlsAdapterWeakCiphers(HTTPAdapter):

    def __init__(self, ssl_options=0, **kwargs):
        self.ssl_options = ssl_options
        super(TlsAdapterWeakCiphers, self).__init__(**kwargs)

    def init_poolmanager(self, *pool_args, **pool_kwargs):
        ctx = ssl_.create_urllib3_context(
            ciphers=WEAK_CIPHERS,
            cert_reqs=ssl.CERT_REQUIRED, options=self.ssl_options)

        self.poolmanager = PoolManager(*pool_args,
                                       ssl_context=ctx,
                                       **pool_kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = ssl_.create_urllib3_context(ciphers=WEAK_CIPHERS)
        kwargs['ssl_context'] = context
        return super(TlsAdapterWeakCiphers, self).proxy_manager_for(*args, **kwargs)


def has_weak_cipher(url, protocol_version):
    session = False

    try:
        # print('ssl._DEFAULT_CIPHERS', ssl._DEFAULT_CIPHERS)

        session = requests.session()
        adapter = TlsAdapterWeakCiphers(protocol_version)

        session.mount(url, adapter)

    except ssl.SSLError as sslex:
        # print('### No weak cipher support on your machine, unable to test: {0} ###'.format(
        #    WEAK_CIPHERS))
        return (False, 'weak_cipher SSLError {0}'.format(sslex))

    try:
        allow_redirects = False

        headers = {'user-agent': USERAGENT}
        a = session.get(url, verify=False, allow_redirects=allow_redirects,
                        headers=headers, timeout=REQUEST_TIMEOUT)

        if a.status_code == 200 or a.status_code == 301 or a.status_code == 302 or a.status_code == 404:
            # print('is ok')
            return (True, 'is ok')

        resulted_in_html = '<html' in a.text

        # if resulted_in_html:
        #    print('has html')
        # else:
        #    print('no html')
        return (resulted_in_html, 'has <html tag in result')
    except ssl.SSLCertVerificationError as sslcertex:
        # print('weak_cipher SSLCertVerificationError', sslcertex)
        return (True, 'weak_cipher SSLCertVerificationError: {0}'.format(sslcertex))
    except ssl.SSLError as sslex:
        # print('error has_weak_cipher SSLError1', sslex)
        return (False, 'weak_cipher SSLError {0}'.format(sslex))
    except ConnectionResetError as resetex:
        # print('error ConnectionResetError', resetex)
        return (False, 'weak_cipher ConnectionResetError {0}'.format(resetex))
    except requests.exceptions.SSLError as sslerror:
        # print('error weak_cipher SSLError2', sslerror)
        return (False, 'Unable to verify: SSL error occured')
    except requests.exceptions.ConnectionError as conex:
        # print('error weak_cipher ConnectionError', conex)
        return (False, 'Unable to verify: connection error occured')
    except Exception as exception:
        # print('weak_cipher test', exception)
        return (False, 'weak_cipher Exception {0}'.format(exception))


# Read post at: https://hussainaliakbar.github.io/restricting-tls-version-and-cipher-suites-in-python-requests-and-testing-wireshark/
INSECURE_CIPHERS = (
    'RSA+RC4+MD5:'
    'RSA+RC4128+MD5:'
    'RSA+RC4+SHA:'
    'RSA+RC4128+SHA:'
    'ECDHE+RSA+RC4+SHA:'
    'ECDHE+RSA+RC4+SHA:'
    'ECDHE+RSA+RC4128+MD5:'
    'ECDHE+RSA+RC4128+MD5:'
)


class TlsAdapterInsecureCiphers(HTTPAdapter):

    def __init__(self, ssl_options=0, **kwargs):
        self.ssl_options = ssl_options
        super(TlsAdapterInsecureCiphers, self).__init__(**kwargs)

    def init_poolmanager(self, *pool_args, **pool_kwargs):
        ctx = ssl_.create_urllib3_context(
            ciphers=INSECURE_CIPHERS,
            cert_reqs=ssl.CERT_REQUIRED, options=self.ssl_options)

        self.poolmanager = PoolManager(*pool_args,
                                       ssl_context=ctx,
                                       **pool_kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = ssl_.create_urllib3_context(ciphers=INSECURE_CIPHERS)
        kwargs['ssl_context'] = context
        return super(TlsAdapterInsecureCiphers, self).proxy_manager_for(*args, **kwargs)


def has_insecure_cipher(url, protocol_version):
    session = False

    try:
        # print('ssl._DEFAULT_CIPHERS', ssl._DEFAULT_CIPHERS)

        session = requests.session()
        adapter = TlsAdapterInsecureCiphers(protocol_version)

        session.mount(url, adapter)

    except ssl.SSLError as sslex:
        # print('### No weak cipher support on your machine, unable to test: {0} ###'.format(
        #    WEAK_CIPHERS))
        return (False, 'insecure_cipher SSLError {0}'.format(sslex))

    try:
        allow_redirects = False

        headers = {'user-agent': USERAGENT}
        a = session.get(url, verify=False, allow_redirects=allow_redirects,
                        headers=headers, timeout=REQUEST_TIMEOUT)

        if a.status_code == 200 or a.status_code == 301 or a.status_code == 302 or a.status_code == 404:
            # print('is ok')
            return (True, 'is ok')

        resulted_in_html = '<html' in a.text

        # if resulted_in_html:
        #    print('has html')
        # else:
        #    print('no html')
        return (resulted_in_html, 'has <html tag in result')
    except ssl.SSLCertVerificationError as sslcertex:
        # print('weak_cipher SSLCertVerificationError', sslcertex)
        return (True, 'insecure_cipher SSLCertVerificationError: {0}'.format(sslcertex))
    except ssl.SSLError as sslex:
        # print('error has_weak_cipher SSLError1', sslex)
        return (False, 'insecure_cipher SSLError {0}'.format(sslex))
    except ConnectionResetError as resetex:
        # print('error ConnectionResetError', resetex)
        return (False, 'insecure_cipher ConnectionResetError {0}'.format(resetex))
    except requests.exceptions.SSLError as sslerror:
        # print('error weak_cipher SSLError2', sslerror)
        return (False, 'Unable to verify: SSL error occured')
    except requests.exceptions.ConnectionError as conex:
        # print('error weak_cipher ConnectionError', conex)
        return (False, 'Unable to verify: connection error occured')
    except Exception as exception:
        # print('weak_cipher test', exception)
        return (False, 'insecure_cipher Exception {0}'.format(exception))


class TlsAdapterCertRequired(HTTPAdapter):

    def __init__(self, ssl_options=0, **kwargs):
        self.ssl_options = ssl_options
        super(TlsAdapterCertRequired, self).__init__(**kwargs)

    def init_poolmanager(self, *pool_args, **pool_kwargs):
        ctx = ssl_.create_urllib3_context(
            cert_reqs=ssl.CERT_REQUIRED, options=self.ssl_options)

        self.poolmanager = PoolManager(*pool_args,
                                       ssl_context=ctx,
                                       **pool_kwargs)


class TlsAdapterNoCert(HTTPAdapter):

    def __init__(self, ssl_options=0, **kwargs):
        self.ssl_options = ssl_options
        super(TlsAdapterNoCert, self).__init__(**kwargs)

    def init_poolmanager(self, *pool_args, **pool_kwargs):
        ctx = ssl_.create_urllib3_context(
            cert_reqs=ssl.CERT_NONE,
            options=self.ssl_options)

        self.poolmanager = PoolManager(*pool_args,
                                       ssl_context=ctx,
                                       **pool_kwargs)


def has_tls_version(url, validate_hostname, protocol_version):
    session = requests.session()
    if validate_hostname:
        adapter = TlsAdapterCertRequired(protocol_version)
    else:
        adapter = TlsAdapterNoCert(protocol_version)

    session.mount("https://", adapter)

    try:
        allow_redirects = False

        headers = {'user-agent': USERAGENT}
        session.get(url, verify=validate_hostname, allow_redirects=allow_redirects,
                        headers=headers, timeout=REQUEST_TIMEOUT)

        return (True, 'is ok')

    except ssl.SSLCertVerificationError as sslcertex:
        # print('protocol version SSLCertVerificationError', sslcertex)
        if validate_hostname:
            return (True, 'protocol version SSLCertVerificationError: {0}'.format(sslcertex))
        else:
            return (False, 'protocol version SSLCertVerificationError: {0}'.format(sslcertex))
    except ssl.SSLError as sslex:
        # print('protocol version SSLError', sslex)
        return (False, 'protocol version SSLError: {0}'.format(sslex))
    except ssl.SSLCertVerificationError as sslcertex:
        # print('protocol version SSLCertVerificationError', sslcertex)
        return (True, 'protocol version SSLCertVerificationError: {0}'.format(sslcertex))
    except ssl.SSLError as sslex:
        # print('error protocol version ', sslex)
        return (False, 'protocol version SSLError {0}'.format(sslex))
    except ConnectionResetError as resetex:
        # print('error protocol version  ConnectionResetError', resetex)
        return (False, 'protocol version  ConnectionResetError {0}'.format(resetex))
    except requests.exceptions.SSLError as sslerror:
        # print('error protocol version  SSLError', sslerror)
        return (False, 'Unable to verify: SSL error occured')
    except requests.exceptions.ConnectionError as conex:
        # print('error protocol version  ConnectionError', conex)
        return (False, 'Unable to verify: connection error occured')
    except Exception as exception:
        # print('protocol version  test', exception)
        return (False, 'protocol version  Exception {0}'.format(exception))
