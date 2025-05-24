# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime
from urllib.parse import urlparse
# https://docs.python.org/3/library/urllib.parse.html
import dns.name
import dns.query
import dns.dnssec
import dns.message
import dns.resolver
import dns.rdatatype
from helpers.csp_helper import rate_csp
from helpers.data_helper import append_domain_entry, has_domain_entry
from helpers.sitespeed_helper import get_data_from_sitespeed
from helpers.sri_helper import rate_sri
from helpers.tls_helper import rate_transfer_layers
from helpers.setting_helper import get_config
from helpers.browser_helper import get_chromium_browser
from helpers.models import Rating
from tests.utils import change_url_to_test_url, dns_lookup,\
    get_translation, merge_dicts
from tests.sitespeed_base import get_result
from engines.sitespeed_result import read_sites_from_directory

csp_only_global_result_dict = {}

def run_test(global_translation, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    global csp_only_global_result_dict # pylint: disable=global-statement

    result_dict = {}

    local_translation = get_translation(
            'http_validator',
            get_config('general.language')
        )

    if get_config('tests.http.csp-only'):
        print(local_translation('TEXT_RUNNING_TEST_CSP_ONLY'))
    else:
        print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # We must take in consideration "www." subdomains...
    o = urlparse(url)
    org_hostname = o.hostname
    org_url = url

    hostname = org_hostname
    if hostname.startswith('www.'):
        url = org_url.replace(hostname, hostname[4:])
        o = urlparse(url)
        hostname = o.hostname

    if get_config('tests.http.csp-only'):
        result_dict = merge_dicts(check_csp(org_url, global_translation), csp_only_global_result_dict, True, True)
        if 'nof_pages' not in result_dict:
            result_dict['nof_pages'] = 1
        else:
            result_dict['nof_pages'] += 1

        csp_only_global_result_dict = result_dict
    else:
        result_dict = check_http_to_https(url, global_translation)
        result_dict = check_tls_versions(url, result_dict, global_translation)
        if org_hostname != hostname:
            result_dict = check_tls_versions(org_url, result_dict, global_translation)
        result_dict = check_ip_version(result_dict)
        result_dict = check_http_version(url, result_dict, global_translation)

    result_dict = cleanup(result_dict)

    rating = rate(hostname, result_dict, global_translation, local_translation)

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    reviews = rating.get_reviews()
    print(global_translation('TEXT_SITE_RATING'), rating)
    if get_config('general.review.show'):
        print(
            global_translation('TEXT_SITE_REVIEW'),
            reviews)

    if get_config('general.review.data'):
        nice_json_data = json.dumps(result_dict, indent=3)
        print(
            global_translation('TEXT_SITE_REVIEW_DATA'),
            f'```json\r\n{nice_json_data}\r\n```')

    return (rating, result_dict)

def check_tls_versions(url, result_dict, global_translation):
    """
    Checks the TLS versions for all domains in the result dictionary.

    Args:
        url (str): The URL whose HTTP version support is to be checked.
        result_dict (dict): The result dictionary where each key is a domain name and
                            the value is another dictionary with details about the domain.

    Returns:
        dict: The updated result dictionary with the TLS version information for each domain.
    """

    o = urlparse(url)
    o_domain = o.hostname

    result_dict = check_tls_version_1_3(url, result_dict, o_domain, global_translation)
    result_dict = check_tls_version_1_2(url, result_dict, o_domain, global_translation)
    result_dict = check_tls_version_1_1(url, result_dict, o_domain, global_translation)
    result_dict = check_tls_version_1_0(url, result_dict, o_domain, global_translation)
    return result_dict

def check_tls_version_1_0(url, result_dict, o_domain, global_translation):
    """
    Checks if the given URL supports TLSv1.0 and updates the result dictionary.

    Args:
        url (str): The URL to test.
        result_dict (dict): A dictionary containing test results.
        o_domain (str): The original domain associated with the URL.

    Returns:
        dict: Updated result dictionary with TLSv1.0 information.
    """
    if not contains_value_for_all(result_dict, 'transport-layers', 'TLSv1.0'):
        browser = 'firefox'
        configuration = (
            ' --firefox.preference security.tls.version.min:1'
            ' --firefox.preference security.tls.version.max:1'
            ' --pageCompleteCheckNetworkIdle true')
        url2 = change_url_to_test_url(url, 'TLSv1.0')
        print('TLSv1.0', o_domain)
        tmp_result = get_website_support_from_sitespeed(
                url2,
                o_domain,
                configuration,
                browser,
                get_config('tests.sitespeed.timeout'),
                global_translation)
        if 'visits' in tmp_result and tmp_result['visits'] > 0:
            for domain, domain_categories in tmp_result.items():
                if not isinstance(domain_categories, dict):
                    continue
                append_domain_entry(domain, 'transport-layers', 'TLSv1.0', tmp_result)
        result_dict = merge_dicts(
            tmp_result,
            result_dict, True, True)
    return result_dict

def check_tls_version_1_1(url, result_dict, o_domain, global_translation):
    """
    Checks if the given URL supports TLSv1.1 and updates the result dictionary.

    Args:
        url (str): The URL to test.
        result_dict (dict): A dictionary containing test results.
        o_domain (str): The original domain associated with the URL.

    Returns:
        dict: Updated result dictionary with TLSv1.1 information.
    """
    if not contains_value_for_all(result_dict, 'transport-layers', 'TLSv1.1'):
        browser = 'firefox'
        configuration = (
            ' --firefox.preference security.tls.version.min:2'
            ' --firefox.preference security.tls.version.max:2')
        url2 = change_url_to_test_url(url, 'TLSv1.1')
        print('TLSv1.1', o_domain)
        tmp_result = get_website_support_from_sitespeed(
                url2,
                o_domain,
                configuration,
                browser,
                get_config('tests.sitespeed.timeout'),
                global_translation)
        if 'visits' in tmp_result and tmp_result['visits'] > 0:
            for domain, domain_categories in tmp_result.items():
                if not isinstance(domain_categories, dict):
                    continue
                append_domain_entry(domain, 'transport-layers', 'TLSv1.1', tmp_result)
        result_dict = merge_dicts(
            tmp_result,
            result_dict, True, True)
    return result_dict

def check_tls_version_1_2(url, result_dict, o_domain, global_translation):
    """
    Checks if the given URL supports TLSv1.2 and updates the result dictionary.

    Args:
        url (str): The URL to test.
        result_dict (dict): A dictionary containing test results.
        o_domain (str): The original domain associated with the URL.

    Returns:
        dict: Updated result dictionary with TLSv1.2 information.
    """
    if not contains_value_for_all(result_dict, 'transport-layers', 'TLSv1.2'):
        browser = 'firefox'
        configuration = (
            ' --firefox.preference security.tls.version.min:3'
            ' --firefox.preference security.tls.version.max:3')
        url2 = change_url_to_test_url(url, 'TLSv1.2')
        print('TLSv1.2', o_domain)
        tmp_result = get_website_support_from_sitespeed(
                url2,
                o_domain,
                configuration,
                browser,
                get_config('tests.sitespeed.timeout'),
                global_translation)
        if 'visits' in tmp_result and tmp_result['visits'] > 0:
            for domain, domain_categories in tmp_result.items():
                if not isinstance(domain_categories, dict):
                    continue
                append_domain_entry(domain, 'transport-layers', 'TLSv1.2', tmp_result)
        result_dict = merge_dicts(
            tmp_result,
            result_dict, True, True)
    return result_dict

def check_tls_version_1_3(url, result_dict, o_domain, global_translation):
    """
    Checks if the given URL supports TLSv1.3 and updates the result dictionary.

    Args:
        url (str): The URL to test.
        result_dict (dict): A dictionary containing test results.
        o_domain (str): The original domain associated with the URL.

    Returns:
        dict: Updated result dictionary with TLSv1.3 information.
    """
    if not contains_value_for_all(result_dict, 'transport-layers', 'TLSv1.3'):
        browser = 'firefox'
        configuration = (
            ' --firefox.preference security.tls.version.min:4'
            ' --firefox.preference security.tls.version.max:4')
        url2 = change_url_to_test_url(url, 'TLSv1.3')
        print('TLSv1.3', o_domain)
        tmp_result = get_website_support_from_sitespeed(
                url2,
                o_domain,
                configuration,
                browser,
                get_config('tests.sitespeed.timeout'),
                global_translation)
        if 'visits' in tmp_result and tmp_result['visits'] > 0:
            for domain, domain_categories in tmp_result.items():
                if not isinstance(domain_categories, dict):
                    continue
                append_domain_entry(domain, 'transport-layers', 'TLSv1.3', tmp_result)
        result_dict = merge_dicts(
            tmp_result,
            result_dict, True, True)
    return result_dict

def rate(org_domain, result_dict, global_translation, local_translation):
    """
    Rates the security features of a domain.

    Parameters:
    org_domain (str): Original domain.
    result_dict (dict): Domain analysis results.
    global_translation, local_translation (function): Translation functions.

    Returns:
    rating (Rating): Rating object with overall and standards ratings.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))

    org_www_domain = f'www.{org_domain}'

    if 'visits' in result_dict and result_dict['visits'] == 0 and 'failed' in result_dict:
        error_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        error_rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return error_rating

    should_create_recommendation = get_config('general.review.details')
    for domain in result_dict.keys():
        if not isinstance(result_dict[domain], dict):
            continue

        if not get_config('tests.http.csp-only'):
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
            should_create_recommendation)
        rating += rate_sri(
            result_dict,
            global_translation,
            local_translation,
            org_domain,
            org_www_domain,
            domain)

    return rating

def rate_ip_versions(result_dict, global_translation, local_translation, domain):
    """
    Rates the IP versions (IPv4 and IPv6) supported by a domain.

    Parameters:
    result_dict (dict): Domain analysis results.
    global_translation, local_translation (function): Translation functions.
    domain (str): The domain to be rated.

    Returns:
    rating (Rating): Rating object with overall and standards ratings.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    if not isinstance(result_dict[domain], dict):
        return rating

    if 'IPv4' in result_dict[domain]['ip-versions'] or\
            'IPv4*' in result_dict[domain]['ip-versions']:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                local_translation('TEXT_REVIEW_IP_VERSION_IPV4_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
                local_translation('TEXT_REVIEW_IP_VERSION_IPV4_NO_SUPPORT').format(domain))
        rating += sub_rating

    if 'IPv6' in result_dict[domain]['ip-versions'] or\
            'IPv6*' in result_dict[domain]['ip-versions']:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                local_translation('TEXT_REVIEW_IP_VERSION_IPV6_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
                local_translation('TEXT_REVIEW_IP_VERSION_IPV6_NO_SUPPORT').format(domain))
        rating += sub_rating
    return rating


def check_hsts_features(domain, org_domain, result_dict, local_translation, global_translation):
    """
    Checks and rates the HSTS features of a domain.

    Parameters:
    domain, org_domain (str): Actual and original domain.
    result_dict (dict): Domain analysis results.
    local_translation, global_translation (function): Translation functions.

    Returns:
    sub_rating (Rating): Sub-rating object with overall,
    integrity, security, and standards ratings.
    """
    sub_rating = Rating(global_translation, get_config('general.review.improve-only'))
    sub_rating.set_overall(5.0)

    if has_domain_entry(domain, 'features', 'INVALIDATE-HSTS', result_dict):
        sub_rating.set_overall(1.5)
        sub_rating.set_integrity_and_security(1.5,
            local_translation('TEXT_REVIEW_HSTS_INVALIDATE').format(domain))
        sub_rating.set_standards(1.5,
            local_translation('TEXT_REVIEW_HSTS_INVALIDATE').format(domain))
    elif has_domain_entry(domain, 'features', 'HSTS-HEADER-PRELOAD-FOUND', result_dict) and\
            (has_domain_entry(domain, 'features', 'HSTS-PRELOAD', result_dict) or\
                has_domain_entry(domain, 'features', 'HSTS-PRELOAD*', result_dict)):
        sub_rating.set_standards(5.0)
        sub_rating.set_integrity_and_security(5.0,
            local_translation('TEXT_REVIEW_HSTS_PRELOAD_FOUND').format(domain))
    elif has_domain_entry(domain, 'features', 'HSTS-HEADER-MAXAGE-1YEAR', result_dict):
        if has_domain_entry(domain, 'features', 'HSTS-HEADER-PRELOAD-FOUND', result_dict):
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
    elif has_domain_entry(domain, 'features', 'HSTS-HEADER-MAXAGE-TOO-LOW', result_dict):
        sub_rating.set_overall(4.5)
        sub_rating.set_standards(5.0)
        sub_rating.set_integrity_and_security(4.0,
            local_translation('TEXT_REVIEW_HSTS_MAXAGE_TOO_LOW').format(domain))
    elif has_domain_entry(domain, 'features', 'HSTS-HEADER-MAXAGE-6MONTHS', result_dict):
        sub_rating.set_overall(4.0)
        sub_rating.set_standards(5.0)
        sub_rating.set_integrity_and_security(3.0,
            local_translation('TEXT_REVIEW_HSTS_MAXAGE_6MONTHS').format(domain))
    elif has_domain_entry(domain, 'features', 'HSTS-HEADER-MAXAGE-1MONTH', result_dict):
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
    return sub_rating


def rate_hsts(result_dict, global_translation, local_translation, org_domain, domain):
    """
    Rates the HSTS features of a domain.

    Parameters:
    result_dict (dict): Domain analysis results.
    global_translation, local_translation (function): Translation functions.
    org_domain, domain (str): Original and actual domain.

    Returns:
    rating (Rating): Rating object with overall, integrity, security, and standards ratings.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    if not isinstance(result_dict[domain], dict):
        return rating

    if has_domain_entry(domain, 'features', 'HSTS', result_dict):
        rating += check_hsts_features(
            domain,
            org_domain,
            result_dict,
            local_translation,
            global_translation)
    elif has_domain_entry(domain, 'features', 'HSTS-HEADER-ON-PARENTDOMAIN-FOUND', result_dict) and\
            not has_domain_entry(domain, 'features', 'INVALIDATE-HSTS', result_dict):
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(4.99,
            local_translation('TEXT_REVIEW_HSTS_USE_PARENTDOMAIN').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
            local_translation('TEXT_REVIEW_HSTS_NOT_FOUND').format(domain))
        sub_rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_HSTS_NOT_FOUND').format(domain))
        rating += sub_rating
    return rating


def rate_schemas(result_dict, global_translation, local_translation, domain):
    """
    This function rates the security schemes of a given domain based on the result dictionary.

    Parameters:
    result_dict (dict): A dictionary containing the results of the domain analysis.
    global_translation (function): A function to translate text globally.
    local_translation (function): A function to translate text locally.
    domain (str): The domain to be rated.

    Returns:
    rating (Rating): A Rating object that contains the overall rating,
    integrity and security rating, and standards rating.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    if not isinstance(result_dict[domain], dict):
        return rating

    if has_domain_entry(domain, 'schemes', 'HTTPS', result_dict):
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0,
            local_translation('TEXT_REVIEW_HTTPS_SUPPORT').format(domain))
        sub_rating.set_standards(5.0,
            local_translation('TEXT_REVIEW_HTTPS_NO_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
            local_translation('TEXT_REVIEW_HTTPS_NO_SUPPORT').format(domain))
        sub_rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_HTTPS_NO_SUPPORT').format(domain))
        rating += sub_rating

    if has_domain_entry(domain, 'schemes', 'HTTP-REDIRECT', result_dict) or\
            has_domain_entry(domain, 'schemes', 'HTTP-REDIRECT*', result_dict):
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
            local_translation('TEXT_REVIEW_HTTP_REDIRECT').format(domain))
        rating += sub_rating

    if has_domain_entry(domain, 'schemes', 'HTTPS-REDIRECT', result_dict) or\
            has_domain_entry(domain, 'schemes', 'HTTPS-REDIRECT*', result_dict):
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0,
            local_translation('TEXT_REVIEW_HTTPS_REDIRECT').format(domain))
        rating += sub_rating
    return rating

def rate_protocols(result_dict, global_translation, local_translation, domain):
    """
    This function rates the protocols used by a given domain based on the result_dict.
    It checks for the presence of HTTP/1.1, HTTP/2, and HTTP/3 protocols and
    assigns ratings accordingly. The function returns a Rating object with the overall and
    standards ratings for the domain.
    """
    rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if not isinstance(result_dict[domain], dict):
        return rating

    if has_domain_entry(domain, 'protocols', 'HTTP/1.1', result_dict):
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
            local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_1_1_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_1_1_NO_SUPPORT').format(domain))
        rating += sub_rating

    if has_domain_entry(domain, 'protocols', 'HTTP/2', result_dict):
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
            local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_2_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_2_NO_SUPPORT').format(domain))
        rating += sub_rating

    if has_domain_entry(domain, 'protocols', 'HTTP/3', result_dict):
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
            local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_3_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_HTTP_VERSION_HTTP_3_NO_SUPPORT').format(domain))
        rating += sub_rating
    return rating

def cleanup(result_dict):
    """
    This function cleans up the result_dict by removing 'urls' and
    'csp-policies' from each domain. It also ensures that each subvalue in
    the domain dictionary is a sorted list with unique elements.
    The function returns the cleaned-up dictionary.
    """
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

def check_csp(url, global_translation):
    """
    This function checks the Content Security Policy (CSP) of a given URL.
    The function returns a dictionary with the result.
    """
    o = urlparse(url)
    o_domain = o.hostname

    browser = 'chrome'
    configuration = ''
    print('CSP ONLY', o_domain)
    result_dict = get_website_support_from_sitespeed(
        url,
        o_domain,
        configuration,
        browser,
        get_config('tests.sitespeed.timeout'),
        global_translation)

    return result_dict

def check_http_to_https(url, global_translation):
    """
    Checks and updates the scheme support (HTTP to HTTPS) for a given URL and
    its associated domains. This function parses the given URL and
    determines the scheme (HTTP or HTTPS).
    It then performs a sitespeed test on the URL to get website support details.
    If the website redirects to a 'www.' domain without first redirecting to HTTPS,
    it tests the 'www.' domain as well.
    The function also checks for HSTS (HTTP Strict Transport Security) support and
    updates the result dictionary accordingly.

    Args:
        url (str): The URL to check for HTTP to HTTPS support.

    Returns:
        dict: The result dictionary with updated scheme support and
              feature details for each domain associated with the URL.
    """
    http_url = ''
    o = urlparse(url)
    o_domain = o.hostname

    if o.scheme == 'https':
        http_url = url.replace('https://', 'http://')
    else:
        http_url = url

    browser = 'chrome'
    configuration = ''
    print('HTTP', o_domain)
    result_dict = get_website_support_from_sitespeed(
        http_url,
        o_domain,
        configuration,
        browser,
        get_config('tests.sitespeed.timeout'),
        global_translation)

    # If website redirects to www. domain without first redirecting to HTTPS, make sure we test it.
    if o_domain in result_dict:
        if not has_domain_entry(o_domain, 'schemes', 'HTTPS', result_dict):
            append_domain_entry(o_domain, 'schemes', 'HTTP-REDIRECT*', result_dict)
            https_url = url.replace('http://', 'https://')
            print('HTTPS', o_domain)
            result_dict = merge_dicts(
                get_website_support_from_sitespeed(
                    https_url,
                    o_domain,
                    configuration,
                    browser,
                    get_config('tests.sitespeed.timeout'),
                    global_translation),
                result_dict, True, True)
        else:
            append_domain_entry(o_domain, 'schemes', 'HTTPS-REDIRECT*', result_dict)

        if 'HTTP' not in result_dict[o_domain]['schemes']:
            append_domain_entry(o_domain, 'features', 'HSTS-PRELOAD*', result_dict)

    # If we have www. domain, ensure we validate HTTP2HTTPS on that as well
    www_domain_key = f'www.{o_domain}'
    if www_domain_key in result_dict:
        if not has_domain_entry(www_domain_key, 'schemes', 'HTTP', result_dict):
            append_domain_entry(www_domain_key, 'schemes', 'HTTPS-REDIRECT*', result_dict)
            www_http_url = http_url.replace(o_domain, www_domain_key)
            print('HTTP', www_domain_key)
            result_dict = merge_dicts(
                get_website_support_from_sitespeed(
                    www_http_url,
                    www_domain_key,
                    configuration,
                    browser,
                    get_config('tests.sitespeed.timeout'),
                    global_translation),
                result_dict,True, True)
        else:
            append_domain_entry(www_domain_key, 'schemes', 'HTTPS-REDIRECT*', result_dict)

    handle_hsts_subdomains(result_dict)

    return result_dict

def handle_hsts_subdomains(result_dict):
    """
    This function checks for domains in the result_dict that have HSTS headers and
    subdomains found. If such domains are found,
    it appends a new entry "HSTS-HEADER-ON-PARENTDOMAIN-FOUND" to the features of all subdomains.
    """
    domains = list(result_dict.keys())
    hsts_domains = []
    for domain in domains:
        domain_dict = result_dict[domain]
        if not isinstance(domain_dict, dict):
            continue

        if has_domain_entry(domain, "features", "HSTS-HEADER-SUBDOMAINS-FOUND", result_dict) and\
                has_domain_entry(domain, "features", "HSTS", result_dict):
            hsts_domains.append(domain)

    for hsts_domain in hsts_domains:
        for domain in domains:
            if domain.endswith(f'.{hsts_domain}'):
                append_domain_entry(
                    domain,
                    "features",
                    "HSTS-HEADER-ON-PARENTDOMAIN-FOUND",
                    result_dict)

def check_ip_version(result_dict):
    """
    Checks and updates the IP versions (IPv4 and IPv6) for each domain in the result dictionary.
    This function iterates over each domain in the result dictionary.
    If a domain does not have an entry for a specific IP version (IPv4 or IPv6),
    it performs a DNS lookup for that IP version.
    If the lookup returns a result,
    it appends an entry to the domain's 'ip-versions' list in the result dictionary.

    Args:
        result_dict (dict): A dictionary where each key is a domain name and
                            the value is another dictionary with details about the domain.

    Returns:
        dict: The updated result dictionary with IP version information for each domain.
    """
    if not contains_value_for_all(result_dict, 'ip-versions', 'IPv4'):
        for domain in result_dict.keys():
            if not isinstance(result_dict[domain], dict):
                continue
            if not has_domain_entry(domain, "ip-versions", "IPv4", result_dict):
                ip4_result = dns_lookup(domain, dns.rdatatype.A)
                if len(ip4_result) > 0:
                    append_domain_entry(domain, "ip-versions", "IPv4*", result_dict)

    if not contains_value_for_all(result_dict, 'ip-versions', 'IPv6'):
        for domain in result_dict.keys():
            if not isinstance(result_dict[domain], dict):
                continue
            if not has_domain_entry(domain, "ip-versions", "IPv6", result_dict):
                ip6_result = dns_lookup(domain, dns.rdatatype.AAAA)
                if len(ip6_result) > 0:
                    append_domain_entry(domain, "ip-versions", "IPv6*", result_dict)

    return result_dict

def get_website_support_from_sitespeed(url, org_domain, configuration, browser, timeout, global_translation):
    """
    Checks the website support using SiteSpeed for a given URL and browser configuration,
    and returns the results.

    This function constructs the SiteSpeed command with the appropriate arguments based on
    the browser and configuration.
    It then runs the SiteSpeed command to generate a HAR (HTTP Archive) file.
    The HAR file is parsed to extract the website support information,
    which is returned as a dictionary.

    Parameters:
    url (str): The URL of the website to be checked.
    org_domain (str): The original domain of the website.
    configuration (str): The configuration settings for the browser.
    browser (str): The browser to be used ('firefox' or 'chrome').
    timeout (int): The maximum time to wait for the SiteSpeed command to complete.

    Returns:
    dict: A dictionary containing the website support information.
    """
    # We don't need extra iterations for what we are using it for
    sitespeed_iterations = 1
    sitespeed_arg = (
        '--plugins.remove screenshot '
        '--plugins.remove html '
        '--plugins.remove metrics '
        '--plugins.add plugin-webperf-core '
        '--browsertime.screenshot false '
        '--screenshot false '
        '--screenshotLCP false '
        '--browsertime.screenshotLCP false '
        '--videoParams.createFilmstrip false '
        '--visualMetrics false '
        '--visualMetricsPerceptual false '
        '--visualMetricsContentful false '
        '--browsertime.headless true '
        '--silent true '
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
            f'-b {get_chromium_browser()} '
            '--chrome.cdp.performance false '
            '--browsertime.chrome.timeline false '
            '--browsertime.chrome.includeResponseBodies all '
            '--browsertime.chrome.args ignore-certificate-errors '
            f'{sitespeed_arg}')

    sitespeed_arg = f'--shm-size=1g {sitespeed_arg}'

    if get_config('tests.sitespeed.xvfb'):
        sitespeed_arg += ' --xvfb'

    (result_folder_name, filename) = get_result(
        url, get_config('tests.sitespeed.docker.use'), sitespeed_arg, timeout)

    o = urlparse(url)
    url_domain = o.hostname

    browsertime_Hars = read_sites_from_directory(result_folder_name, url_domain, -1, -1)
    if len(browsertime_Hars) < 1:
        return {'failed': True }

    result = get_data_from_sitespeed(browsertime_Hars[0][0], url_domain)
    return result

def contains_value_for_all(result_dict, key, value):
    """
    Checks if a specific key-value pair exists in all dictionaries within
    a given result dictionary.

    This function iterates over the keys in the result dictionary.
    For each key, it checks if the corresponding 
    value is a dictionary and if the specified key-value pair exists in this dictionary.
    If the key-value pair does not exist in any of the dictionaries, the function returns False.
    If the key-value pair exists in all dictionaries, the function returns True.

    Parameters:
    result_dict (dict): The dictionary to be checked.
    key (str): The key to be checked.
    value (str): The value to be checked.

    Returns:
    bool: True if the key-value pair exists in all dictionaries within the result dictionary,
          False otherwise.
    """
    if result_dict is None:
        return False

    nof_values = 0
    nof_keys = 0
    for domain in result_dict.keys():
        if not isinstance(result_dict[domain], dict):
            continue

        if key in result_dict[domain]:
            nof_keys += 1
        else:
            continue

        if value in result_dict[domain][key]:
            nof_values += 1
    return nof_keys == nof_values and nof_keys != 0

def check_http_version(url, result_dict, global_translation):
    """
    Checks the HTTP version supported by a given URL and updates a result dictionary.

    This function checks the support for different HTTP versions (HTTP/1.1, HTTP/2, HTTP/3)
    by the server at the given URL.
    It uses SiteSpeed to perform the checks with different browser configurations.
    The results are then merged into the result dictionary.

    Parameters:
    url (str): The URL whose HTTP version support is to be checked.
    result_dict (dict): The dictionary to which the results should be added.

    Returns:
    dict: The result dictionary updated with the HTTP version support information.
    """

    o = urlparse(url)
    o_domain = o.hostname

    if not contains_value_for_all(result_dict, 'protocols', 'HTTP/1.1'):
        browser = 'firefox'
        configuration = (
            ' --firefox.preference network.http.http2.enabled:false'
            ' --firefox.preference network.http.http3.enable:false')
        url2 = change_url_to_test_url(url, 'HTTPv1')
        print('HTTP/1.1', o_domain)
        result_dict = merge_dicts(
            get_website_support_from_sitespeed(
                url2,
                o_domain,
                configuration,
                browser,
                get_config('tests.sitespeed.timeout'),
                global_translation),
            result_dict, True, True)

    if not contains_value_for_all(result_dict, 'protocols', 'HTTP/2'):
        browser = 'firefox'
        configuration = (
            ' --firefox.preference network.http.http2.enabled:true'
            ' --firefox.preference network.http.http3.enable:false'
            ' --firefox.preference network.http.version:2.0')
        url2 = change_url_to_test_url(url, 'HTTPv2')
        print('HTTP/2', o_domain)
        result_dict = merge_dicts(
            get_website_support_from_sitespeed(
                url2,
                o_domain,
                configuration,
                browser,
                get_config('tests.sitespeed.timeout'),
                global_translation),
            result_dict, True, True)

    if not contains_value_for_all(result_dict, 'protocols', 'HTTP/3'):
        browser = 'firefox'
        configuration = (
            ' --firefox.preference network.http.http2.enabled:false'
            ' --firefox.preference network.http.http3.enable:true'
            ' --firefox.preference network.http.version:3.0')
        url2 = change_url_to_test_url(url, 'HTTPv3')
        print('HTTP/3', o_domain)
        result_dict = merge_dicts(
            get_website_support_from_sitespeed(
                url2,
                o_domain,
                configuration,
                browser,
                get_config('tests.sitespeed.timeout'),
                global_translation),
            result_dict, True, True)

    return result_dict
