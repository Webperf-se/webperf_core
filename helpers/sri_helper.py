# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines
import json
import re
import urllib
import urllib.parse
from helpers.data_helper import append_domain_entry
from helpers.setting_helper import get_config
from models import Rating

# pylint: disable=too-many-arguments
def rate_sri(result_dict, global_translation, local_translation,
             org_domain, org_www_domain, domain):
    """
    This function rates the Subresource Integrity (SRI) of a given domain.

    Parameters:
    result_dict (dict): A dictionary containing the results of the SRI checks.
    global_translation (function): A function to translate text to a global language.
    local_translation (function): A function to translate text to a local language.
    org_domain (str): The original domain.
    org_www_domain (str): The original domain with 'www.' prefix.
    domain (str): The domain to be rated.

    Returns:
    Rating: A Rating object containing the overall rating,
            standards rating, and integrity and security rating.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    if not isinstance(result_dict[domain], dict):
        return rating

    if domain not in (org_domain, org_www_domain):
        return rating

    if 'SRI-WITH-ERRORS' in result_dict[domain]['features']:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(3.0)
        sub_rating.set_standards(3.0,
                local_translation(
                'TEXT_REVIEW_SRI_WITH_ERRORS'
            ).format(domain))
        sub_rating.set_integrity_and_security(3.0,
                local_translation(
                'TEXT_REVIEW_SRI_WITH_ERRORS'
            ).format(domain))
        rating += sub_rating
    elif 'SRI-COMPLIANT' in result_dict[domain]['features']:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                local_translation(
                'TEXT_REVIEW_SRI_COMPLIANT'
            ).format(domain))
        sub_rating.set_integrity_and_security(5.0,
                local_translation(
                'TEXT_REVIEW_SRI_COMPLIANT'
            ).format(domain))
        rating += sub_rating
    elif 'HTML-FOUND' in result_dict[domain]['features'] and\
            (domain in (org_domain, org_www_domain)):
        rating = Rating(global_translation, get_config('general.review.improve-only'))
        rating.set_overall(1.0)
        rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_SRI_NONE_COMPLIANT').format(domain))
        rating.set_integrity_and_security(1.0,
            local_translation('TEXT_REVIEW_SRI_NONE_COMPLIANT').format(domain))

    return rating

def append_sri_data(req_url, req_domain, res, org_domain, result):
    """
    Appends Subresource Integrity (SRI) data for various types of content.

    This function checks the type of content (HTML) and
    calls the appropriate function to append the SRI data to the result dictionary. 

    Args:
        req_url (str): The requested URL.
        req_domain (str): The requested domain.
        res (dict): The response dictionary containing the content.
        org_domain (str): The original domain.
        result (dict): The result dictionary where the CSP data will be appended.
    """
    if 'content' in res and 'text' in res['content']:
        if 'mimeType' in res['content'] and 'text/html' in res['content']['mimeType']:
            append_sri_data_for_html(
                req_url,
                req_domain,
                res,
                org_domain,
                result)

def append_sri_data_for_html(req_url, req_domain, res, org_domain, result):
    """
    Appends Subresource Integrity (SRI) data for HTML content and linked resources.

    This function parses the HTML content and identifies the SRI from attributes.
    It also identifies linked resources such as style, and script.
    It then appends the SRI data for these resources to the result dictionary.

    Args:
        req_url (str): The requested URL.
        req_domain (str): The requested domain.
        res (dict): The response dictionary containing the HTML content.
        org_domain (str): The original domain.
        result (dict): The result dictionary where the SRI data will be appended.
    """
    # Reference: https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity
    # https://www.srihash.org/
    content = res['content']['text']

    candidates = get_sri_candidates(req_domain, content)
    # nice_candidates = json.dumps(candidates, indent=3)
    # print('Candidates', nice_candidates)

    sri_list = get_sris(req_domain, content)
    nice_sri_list = json.dumps(sri_list, indent=3)
    print('SRI', nice_sri_list)

    sri_errors = []

    for sri in sri_list:
        found_candidate = None

        if 'error' in sri:
            sri_errors.append(sri['error'])

        for candidate in candidates:
            if candidate['raw'] == sri['raw']:
                found_candidate = candidate
                break

        if found_candidate is not None:
            candidates.remove(found_candidate)

    # nice_candidates = json.dumps(candidates, indent=3)
    # print('Candidates', nice_candidates)

    if len(sri_errors) > 0:
        append_domain_entry(
            req_domain,
            'features',
            'SRI-WITH-ERRORS',
            result)
    elif len(candidates) == 0:
        append_domain_entry(
            req_domain,
            'features',
            'SRI-COMPLIANT',
            result)

def get_sris(req_domain, content):
    sri_list = []
    regex = (
        r'(?P<raw><(?P<name>[a-z]+)[^<]*? integrity=["\'](?P<integrity>[^"\']+)["\'][^>]*?>)'
        )
    matches = re.finditer(regex, content, re.MULTILINE | re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        raw = match.group('raw')
        name = match.group('name').lower()
        integrity = match.group('integrity')

        sri = {
            'raw': raw,
            'tag-name': name,
            'integrity': integrity
        }

        src = None
        regex_src = r'(href|src)="(?P<src>[^"\']+)["\']'
        group_src = re.search(regex_src, raw, re.IGNORECASE)
        if group_src is not None:
            src = group_src.group('src')
            sri['src'] = src
            sri['src-same-origin'] = is_same_domain(src, req_domain)

        src_type = None
        if name == 'script':
            src_type = 'script'
        else:
            regex_type = r'(as)="(?P<as>[^"\']+)["\']'
            group_type = re.search(regex_type, raw, re.IGNORECASE)
            if group_type is not None:
                tmp = group_type.group('as').lower()
                if tmp in ('style', 'font', 'img', 'script'):
                    src_type = tmp

        link_rel = None
        regex_rel = r'(rel)="(?P<rel>[^"\']+)["\']'
        group_rel = re.search(regex_rel, raw, re.IGNORECASE)
        if group_rel is not None:
            link_rel = group_rel.group('rel').lower()
            if src_type is None and link_rel in ('stylesheet'):
                src_type = 'style'

        sri['type'] = src_type
        sri['rel'] = link_rel

        if name in ('link'):
            if link_rel not in ('stylesheet', 'preload', 'modulepreload'):
                # TODO: Do something when using it incorrectly
                sri['error'] = 'Using integrity attribute in combination with unallowed rel attribute value.'
                print('WEBSITE WARNING: USING integrity incorrectly!')
        elif name not in ('link', 'script'):
            # TODO: Do something when using it incorrectly
            sri['error'] = 'Using integrity attribute on wrong element type.'
            print('WEBSITE WARNING: USING integrity incorrectly!')

        sri_list.append(sri)

    return sri_list

def get_sri_candidates(req_domain, content):
    candidates = []
    regex = (
        r'(?P<raw><(?P<name>link|script) [^>]*?>)'
        )

    matches = re.finditer(regex, content, re.MULTILINE | re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        raw = match.group('raw')
        name = match.group('name').lower()

        src = None
        src_same_origin = False
        regex_src = r'(href|src)="(?P<src>[^"\']+)["\']'
        group_src = re.search(regex_src, raw, re.IGNORECASE)
        if group_src is not None:
            src = group_src.group('src')
            src_same_origin = is_same_domain(src, req_domain)

        link_rel = None
        regex_rel = r'(rel)="(?P<rel>[^"\']+)["\']'
        group_rel = re.search(regex_rel, raw, re.IGNORECASE)
        if group_rel is not None:
            link_rel = group_rel.group('rel').lower()

        should_have_integrity = False
        if name in ('link'):
            if link_rel in ('stylesheet', 'preload', 'modulepreload'):
                should_have_integrity = True
        elif name in ('script') and src is not None:
            should_have_integrity = True

        # NOTE: Remove same domain resources
        if should_have_integrity and src_same_origin:
            should_have_integrity = False

        if should_have_integrity:
            candidates.append({
                'raw': raw,
                'tag-name': name,
                'src': src,
                'src-same-origin': src_same_origin
            })

    return candidates

def is_same_domain(url, domain):
    if url.startswith('//'):
        url = url.replace('//', 'https://')
    elif url.startswith('https://'):
        url = url
    elif '://' in url:
        url = url
    elif ':' in url:
        url = url
    elif url.startswith('/'):
        url = url.strip('/')
        url = f'https://{domain}/{url}'

    o = urllib.parse.urlparse(url)
    resource_domain = o.hostname

    return domain == resource_domain
