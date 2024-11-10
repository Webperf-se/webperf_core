# -*- coding: utf-8 -*-
import re
import urllib
import urllib.parse
from helpers.data_helper import append_domain_entry,\
    append_domain_entry_with_key, has_domain_entry
from helpers.setting_helper import get_config
from helpers.models import Rating

# pylint: disable=too-many-arguments,too-many-positional-arguments
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

        if get_config('general.review.details') and \
                has_domain_entry(domain, 'sri-findings', 'sri-errors', result_dict):
            errors_str_list = ''
            errors = result_dict[domain]['sri-findings']['sri-errors']
            for error in errors:
                errors_str_list += f"  - {error}\r\n"

            sub_rating.set_standards(3.0,
                    local_translation(
                    'TEXT_REVIEW_SRI_WITH_ERRORS_DETAILS'
                ).format(domain))

            sub_rating.standards_review = sub_rating.standards_review +\
                errors_str_list
        else:
            sub_rating.set_standards(3.0,
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

        sub_rating = Rating(global_translation, get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)

        if get_config('general.review.details') and \
                has_domain_entry(domain, 'sri-findings', 'sri-candidates', result_dict):
            candidates_str_list = ''
            candidates = result_dict[domain]['sri-findings']['sri-candidates']
            for candidate in candidates:
                candidates_str_list += f"  - `{candidate}`\r\n"

            sub_rating.set_standards(1.0,
                local_translation(
                    'TEXT_REVIEW_SRI_NONE_COMPLIANT'
                    ).format(domain))
            sub_rating.set_integrity_and_security(1.0,
                local_translation(
                    'TEXT_REVIEW_SRI_NONE_COMPLIANT_DETAILS'
                    ).format(domain))
            sub_rating.integrity_and_security_review = sub_rating.integrity_and_security_review +\
                candidates_str_list
        else:
            sub_rating.set_standards(1.0,
                local_translation('TEXT_REVIEW_SRI_NONE_COMPLIANT').format(domain))
            sub_rating.set_integrity_and_security(1.0,
                local_translation('TEXT_REVIEW_SRI_NONE_COMPLIANT').format(domain))
        rating += sub_rating

    return rating

def append_sri_data(req_domain, res, result):
    """
    Appends Subresource Integrity (SRI) data for various types of content.

    This function checks the type of content (HTML) and
    calls the appropriate function to append the SRI data to the result dictionary. 

    Args:
        req_domain (str): The requested domain.
        res (dict): The response dictionary containing the content.
        result (dict): The result dictionary where the CSP data will be appended.
    """

    # TODO: Remove text empty check when sitespeed has fixed https://github.com/sitespeedio/sitespeed.io/issues/4295
    if 'content' in res and 'text' in res['content'] and res['content']['text'] != '':
        if 'mimeType' in res['content'] and 'text/html' in res['content']['mimeType']:
            append_sri_data_for_html(
                req_domain,
                res,
                result)

def append_sri_data_for_html(req_domain, res, result):
    """
    Appends Subresource Integrity (SRI) data for HTML content and linked resources.

    This function parses the HTML content and identifies the SRI from attributes.
    It also identifies linked resources such as style, and script.
    It then appends the SRI data for these resources to the result dictionary.

    Args:
        req_domain (str): The requested domain.
        res (dict): The response dictionary containing the HTML content.
        result (dict): The result dictionary where the SRI data will be appended.
    """
    # Reference: https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity
    # https://www.srihash.org/
    content = res['content']['text']

    candidates = get_sri_candidates(req_domain, content)
    sri_list = get_sris(req_domain, content)

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

    is_sri_compliant = not has_domain_entry(req_domain,
            'features',
            'SRI-NONE-COMPLIANT',
                result)

    if len(sri_errors) > 0:
        is_sri_compliant = False
        append_domain_entry(
            req_domain,
            'features',
            'SRI-WITH-ERRORS',
            result)
        for sri_error in sri_errors:
            append_domain_entry_with_key(
                req_domain,
                'sri-findings',
                'sri-errors',
                sri_error,
                result)
    elif len(candidates) == 0:
        is_sri_compliant = is_sri_compliant and True
    else:
        is_sri_compliant = False
        for candidate in candidates:
            append_domain_entry_with_key(
                req_domain,
                'sri-findings',
                'sri-candidates',
                candidate['raw'],
                result)

    if is_sri_compliant:
        append_domain_entry(
            req_domain,
            'features',
            'SRI-COMPLIANT',
            result)
    else:
        append_domain_entry(
            req_domain,
            'features',
            'SRI-NONE-COMPLIANT',
            result)


def get_sris(req_domain, content):
    """
    Extracts Subresource Integrity (SRI) information from HTML content.

    This function searches for HTML tags with 'integrity' attributes within the provided content,
    extracts relevant SRI details, and processes them using helper functions to append additional
    information. The results are returned as a list of dictionaries.

    Args:
        req_domain (str): The domain from which the request originated.
        content (str): The HTML content to be parsed.

    Returns:
        list: A list of dictionaries,
              each containing SRI information and additional processed data.
    """
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

        append_with_src(req_domain, raw, sri)
        src_type = append_with_src_type(raw, name)
        link_rel = append_with_rel(raw, sri, src_type)
        append_sri_errors(name, sri, link_rel)

        sri_list.append(sri)

    return sri_list

def append_with_src_type(raw, name):
    """
    Determines the source type of an HTML tag based on its attributes.

    This function checks the tag name and
    its attributes to identify the type of resource it represents.
    If the tag is a 'script', it directly assigns 'script' as the source type.
    For other tags, it searches for the 'as' attribute and
    assigns the corresponding type if it matches known resource types.

    Args:
        raw (str): The raw HTML tag string.
        name (str): The name of the HTML tag.

    Returns:
        str or None: The determined source type ('script', 'style', 'font', 'img')
                     or None if not identified.
    """
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
    return src_type

def append_with_rel(raw, sri, src_type):
    """
    Extracts and processes the 'rel' attribute from an HTML tag.

    This function searches for the 'rel' attribute within the provided HTML tag string.
    It assigns the corresponding source type if the 'rel' attribute indicates a stylesheet and
    updates the SRI dictionary with the determined type and 'rel' attribute.

    Args:
        raw (str): The raw HTML tag string.
        sri (dict): The dictionary containing SRI information to be updated.
        src_type (str or None): The current source type,
                                which may be updated based on the 'rel' attribute.

    Returns:
        str or None: The value of the 'rel' attribute if found, otherwise None.
    """
    link_rel = None
    regex_rel = r'(rel)="(?P<rel>[^"\']+)["\']'
    group_rel = re.search(regex_rel, raw, re.IGNORECASE)
    if group_rel is not None:
        link_rel = group_rel.group('rel').lower()
        if src_type is None and link_rel in ('stylesheet'):
            src_type = 'style'

    sri['type'] = src_type
    sri['rel'] = link_rel
    return link_rel

def append_sri_errors(name, sri, link_rel):
    """
    Validates the use of the integrity attribute in HTML tags and logs errors.

    This function checks if the integrity attribute is used correctly based on the tag name and
    its 'rel' attribute.
    It updates the SRI dictionary with error messages if the integrity attribute is
    used incorrectly and logs warnings.

    Args:
        name (str): The name of the HTML tag.
        sri (dict): The dictionary containing SRI information to be updated.
        link_rel (str or None): The value of the 'rel' attribute of the HTML tag.

    Returns:
        None
    """
    if name in ('link'):
        if link_rel not in ('stylesheet', 'preload', 'modulepreload'):
            sri['error'] = (
                    'Using integrity attribute in combination '
                    'with unallowed rel attribute value.')
    elif name not in ('link', 'script'):
        sri['error'] = 'Using integrity attribute on wrong element type.'

def append_with_src(req_domain, raw, obj):
    """
    Extracts the source URL from an HTML tag and updates the SRI object.

    This function searches for 'href' or 'src' attributes within the provided HTML tag string,
    extracts the URL, and updates the SRI dictionary with the source URL and
    a flag indicating if the source is from the same domain.

    Args:
        req_domain (str): The domain from which the request originated.
        raw (str): The raw HTML tag string.
        obj (dict): The dictionary containing SRI information to be updated.

    Returns:
        None
    """
    src = None
    regex_src = r'(href|src)="(?P<src>[^"\']+)["\']'
    group_src = re.search(regex_src, raw, re.IGNORECASE)
    if group_src is not None:
        src = group_src.group('src')
        obj['src'] = src
        obj['src-same-origin'] = is_same_domain(src, req_domain)

def get_sri_candidates(req_domain, content):
    """
    Identifies HTML tags that should have Subresource Integrity (SRI) attributes.

    This function searches for 'link' and 'script' tags within the provided HTML content,
    determines if they should have SRI attributes based on their attributes and origin,
    and returns a list of candidate tags.

    Args:
        req_domain (str): The domain from which the request originated.
        content (str): The HTML content to be parsed.

    Returns:
        list: A list of dictionaries,
              each representing a candidate tag that should have an SRI attribute.
    """
    candidates = []
    regex = (
        r'(?P<raw><(?P<name>link|script) [^>]*?>)'
        )

    matches = re.finditer(regex, content, re.MULTILINE | re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        raw = match.group('raw')
        name = match.group('name').lower()

        candidate = {
            'raw': raw,
            'tag-name': name
        }
        append_with_src(req_domain, raw, candidate)
        link_rel = append_with_rel(raw, candidate, None)

        should_have_integrity = False
        if name in ('link'):
            if link_rel in ('stylesheet', 'preload', 'modulepreload'):
                should_have_integrity = True
        elif name in ('script') and ('src' in candidate and candidate['src'] is not None):
            should_have_integrity = True

        # NOTE: Remove same domain resources
        if should_have_integrity and candidate['src-same-origin']:
            should_have_integrity = False

        if should_have_integrity:
            candidates.append(candidate)

    return candidates

def is_same_domain(url, domain):
    """
    Check if given url is using same domain.

    Args:
        url (str): URL to check.
        domain (str): Domain to compare with.

    Returns:
        bool: True if URL uses same domain, otherwise False.
    """
    if url.startswith('//'):
        url = url.replace('//', 'https://')
    elif url.startswith('/'):
        url = url.strip('/')
        url = f'https://{domain}/{url}'

    parsed_url = urllib.parse.urlparse(url)
    return parsed_url.hostname == domain
