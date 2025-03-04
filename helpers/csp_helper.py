# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines
import base64
import re
import urllib
import urllib.parse
from helpers.data_helper import append_domain_entry, extend_domain_entry_with_key
from helpers.hash_helper import create_sha256_hash
from helpers.setting_helper import get_config
from helpers.models import Rating
from tests.utils import get_http_content

# DEFAULTS
CSP_POLICIES_SUPPORTED_SRC = [
    'default-src','script-src','style-src','font-src',
    'connect-src','frame-src','img-src','media-src',
    'frame-ancestors','base-uri','form-action','child-src',
    'manifest-src','object-src','script-src-attr',
    'script-src-elem','style-src-attr','style-src-elem','worker-src']
CSP_POLICIES_SELF_ALLOWED = [
    'style-src-elem','style-src',
    'font-src','connect-src','frame-src','img-src','media-src',
    'frame-ancestors','base-uri','form-action','child-src','manifest-src']
CSP_POLICIES_FALLBACK_SRC = [
    'base-uri', 'object-src', 'frame-ancestors',
    'form-action', 'default-src']
# Deprecated policies (According to https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
CSP_POLICIES_DEPRECATED = [
            'block-all-mixed-content',
            'plugin-types',
            'prefetch-src',
            'referrer',
            'report-uri']

def handle_csp(content, domain, result_dict, is_from_response_header, org_domain):
    """
    Handles the Content Security Policy (CSP) from the content and updates the result dictionary.

    Parameters:
    content (str): The content containing the CSP.
    domain (str): The domain to which the CSP applies.
    result_dict (dict): The dictionary to be updated with the parsed CSP.
    is_from_response_header (bool): Flag indicating if the content is from a response header.
    org_domain (str): The original domain.
    """
    parse_csp(content, domain, result_dict, is_from_response_header)
    # Add style-src policies to all who uses it as fallback
    ensure_csp_policy_fallbacks(domain, result_dict)

    # convert polices to objects
    convert_csp_policies_2_csp_objects(domain, result_dict, org_domain)

def parse_csp(content, domain, result_dict, is_from_response_header):
    """
    Parses the Content Security Policy (CSP) from the content and updates the result dictionary.

    Parameters:
    content (str): The content containing the CSP.
    domain (str): The domain to which the CSP applies.
    result_dict (dict): The dictionary to be updated with the parsed CSP.
    is_from_response_header (bool): Flag indicating if the content is from a response header.
    """
    regex = (r'(?P<name>(default-src|script-src|style-src|font-src|connect-src|'
             r'frame-src|img-src|media-src|frame-ancestors|base-uri|form-action|'
             r'block-all-mixed-content|child-src|connect-src|fenced-frame-src|font-src|'
             r'img-src|manifest-src|media-src|object-src|plugin-types|prefetch-src|referrer|'
             r'report-to|report-uri|require-trusted-types-for|sandbox|script-src-attr|'
             r'script-src-elem|strict-dynamic|style-src-attr|style-src-elem|'
             r'trusted-types|upgrade-insecure-requests|worker-src)) '
             r'(?P<value>[^;]{5,10000})[;]{0,1}')
    matches = re.finditer(regex, content, re.MULTILINE | re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        name = match.group('name')
        value = match.group('value')

        tmp_name = name.upper()
        policy_name = name.lower()

        if not is_from_response_header and\
                policy_name in ('frame-ancestors', 'report-uri', 'sandbox'):
            append_domain_entry(
                domain,
                'features',
                'CSP-UNSUPPORTED-IN-META',
                result_dict)
            append_domain_entry(
                domain,
                'features',
                f'CSP-UNSUPPORTED-IN-META-{tmp_name}',
                result_dict)

        values = value.split(' ')
        extend_domain_entry_with_key(domain, 'csp-policies', policy_name, values, result_dict)

def ensure_csp_policy_fallbacks(domain, result_dict):
    """
    This function ensures that fallbacks are set for certain CSP policies for a given domain.

    Parameters:
    domain (str): The domain for which the CSP policies are to be ensured.
    result_dict (dict): A dictionary containing the results of the CSP checks.
    """
    if 'style-src' in result_dict[domain]['csp-policies']:
        style_items = result_dict[domain]['csp-policies']['style-src']
        append_csp_policy('style-src-attr', style_items, domain, result_dict)
        append_csp_policy('style-src-elem', style_items, domain, result_dict)

    # Add child-src policies to all who uses it as fallback
    if 'child-src' in result_dict[domain]['csp-policies']:
        child_items = result_dict[domain]['csp-policies']['child-src']
        append_csp_policy('frame-src', child_items, domain, result_dict)
        append_csp_policy('worker-src', child_items, domain, result_dict)

    # Add script-src policies to all who uses it as fallback
    if 'script-src' in result_dict[domain]['csp-policies']:
        script_items = result_dict[domain]['csp-policies']['script-src']
        append_csp_policy('script-src-attr', script_items, domain, result_dict)
        append_csp_policy('script-src-elem', script_items, domain, result_dict)
        append_csp_policy('worker-src', script_items, domain, result_dict)


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
        append_csp_policy('script-src', default_items, domain, result_dict)
        append_csp_policy('script-src-elem', default_items, domain, result_dict)
        append_csp_policy('script-src-attr', default_items, domain, result_dict)
        append_csp_policy('style-src', default_items, domain, result_dict)
        append_csp_policy('style-src-elem', default_items, domain, result_dict)
        append_csp_policy('style-src-attr', default_items, domain, result_dict)
        append_csp_policy('worker-src', default_items, domain, result_dict)

def append_csp_policy(policy_name, items, domain, result_dict):
    """
    This function appends a CSP policy to a given domain in the result dictionary.

    Parameters:
    policy_name (str): The name of the policy.
    items (list): A list of items in the policy.
    domain (str): The domain to which the policy is to be appended.
    result_dict (dict): A dictionary containing the results of the CSP checks.
    """
    if domain not in result_dict:
        result_dict[domain] = {}

    if 'csp-policies' not in result_dict[domain]:
        result_dict[domain]['csp-policies'] = {}

    if policy_name not in result_dict[domain]['csp-policies']:
        result_dict[domain]['csp-policies'][policy_name] = []

    if len(items) == 0:
        return

    if len(result_dict[domain]['csp-policies'][policy_name]) == 0:
        result_dict[domain]['csp-policies'][policy_name].extend(items)

def convert_csp_policies_2_csp_objects(domain, result_dict, org_domain):
    """
    This function converts CSP policies into CSP policy objects for a given domain.

    Parameters:
    domain (str): The domain for which the CSP policies are to be converted.
    result_dict (dict): A dictionary containing the results of the CSP checks.
    org_domain (str): The original domain.
    """
    wildcard_org_domain = f'webperf-core-wildcard.{org_domain}'
    subdomain_org_domain = f'.{org_domain}'

    for policy_name, items in result_dict[domain]['csp-policies'].items():
        policy_object = csp_policy_2_csp_object(
            policy_name,
            wildcard_org_domain,
            subdomain_org_domain,
            items)

        if 'csp-objects' not in result_dict[domain]:
            result_dict[domain]['csp-objects'] = {}
        if policy_name not in result_dict[domain]['csp-objects']:
            result_dict[domain]['csp-objects'][policy_name] = policy_object
        else:
            result_dict[domain]['csp-objects'][policy_name].update(policy_object)

def csp_policy_2_csp_object(policy_name, wildcard_org_domain, subdomain_org_domain, items):
    """
    This function converts a CSP policy into a CSP policy object.

    Parameters:
    policy_name (str): The name of the policy.
    wildcard_org_domain (str): The original domain with a wildcard.
    subdomain_org_domain (str): The original domain with a subdomain.
    items (list): A list of items in the policy.

    Returns:
    dict: A dictionary representing the CSP policy object.
    """
    policy_object = default_csp_policy_object(policy_name)
    for value in items:
        policy_object['all'].append(value)
        if value == '' or\
                (
                    value.startswith("'") and\
                    not value.endswith("'")
                ) or\
                (
                    value.endswith("'") and\
                    not value.startswith("'")
                ):
                # Malformed value, probably missing space or have two.
            policy_object['malformed'].append(value)
        elif value.startswith("'sha256-") or\
                    value.startswith("'sha384-") or\
                    value.startswith("'sha512-"):
            policy_object['hashes'].append(value)
        elif "'nonce-" in value:
            policy_object['nounces'].append(value)
        else:
            if '*' in value:
                policy_object['wildcards'].append(value)
            if '.' in value:
                host_source_url = host_source_2_url(value)
                host_source_o = urllib.parse.urlparse(host_source_url)
                host_source_hostname = host_source_o.hostname
                if host_source_hostname.endswith(wildcard_org_domain):
                    policy_object['wildcard-subdomains'].append(value)
                elif host_source_hostname.endswith(subdomain_org_domain):
                    policy_object['subdomains'].append(value)
                else:
                    policy_object['domains'].append(value)

            scheme = re.match(r'^(?P<scheme>[a-z]+)\:', value)
            if scheme is not None:
                policy_object['schemes'].append(value)

    return policy_object

def default_csp_policy_object(policy_name):
    """
    This function creates a default Content Security Policy (CSP) policy object.

    Parameters:
    policy_name (str): The name of the policy.

    Returns:
    dict: A dictionary representing the default CSP policy object.
    """
    return {
            'name': policy_name,
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

def host_source_2_url(host_source):
    """
    This function converts a host source into a URL.

    Parameters:
    host_source (str): The host source to be converted.

    Returns:
    str: The converted URL.
    """
    result = host_source
    if '*' in result:
        result = result.replace('*', 'webperf-core-wildcard')
    if '://' not in result:
        result = f'https://{result}'

    return result

# pylint: disable=too-many-arguments
def rate_csp(result_dict, global_translation, local_translation,
             org_domain, org_www_domain, domain, should_create_recommendation):
    """
    This function rates the Content Security Policy (CSP) of a given domain.

    Parameters:
    result_dict (dict): A dictionary containing the results of the CSP checks.
    global_translation (function): A function to translate text to a global language.
    local_translation (function): A function to translate text to a local language.
    org_domain (str): The original domain.
    org_www_domain (str): The original domain with 'www.' prefix.
    domain (str): The domain to be rated.
    should_create_recommendation (bool): A flag indicating whether to create a recommendation.

    Returns:
    Rating: A Rating object containing the overall rating,
            standards rating, and integrity and security rating.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    if not isinstance(result_dict[domain], dict):
        return rating

    if domain not in (org_domain, org_www_domain):
        return rating

    if 'CSP-HEADER-FOUND' in result_dict[domain]['features'] or\
            'CSP-META-FOUND' in result_dict[domain]['features']:
        total_number_of_sitespeedruns = result_dict['visits']

        if 'CSP-UNSUPPORTED-IN-META' in result_dict[domain]['features']:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(1.0)
            sub_rating.set_standards(1.0,
                                     local_translation(
                                         'TEXT_REVIEW_CSP_UNSUPPORTED_IN_META'
                                         ).format(domain))
            rating += sub_rating

        rating += rate_csp_depricated(domain, result_dict, local_translation, global_translation)

        for policy_name in CSP_POLICIES_SUPPORTED_SRC:
            policy_object = None
            if policy_name in result_dict[domain]['csp-objects']:
                policy_object = result_dict[domain]['csp-objects'][policy_name]
            else:
                continue

            rating += rate_csp_policy(
                domain,
                total_number_of_sitespeedruns,
                policy_object,
                local_translation,
                global_translation)

        rating += rate_csp_fallbacks(domain, result_dict, local_translation, global_translation)

    elif 'HTML-FOUND' in result_dict[domain]['features'] and\
            (domain in (org_domain, org_www_domain)):
        rating = Rating(global_translation, get_config('general.review.improve-only'))
        rating.set_overall(1.0)
        rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_CSP_NOT_FOUND').format(domain))
        rating.set_integrity_and_security(1.0,
            local_translation('TEXT_REVIEW_CSP_NOT_FOUND').format(domain))

    final_rating = create_final_csp_rating(global_translation, local_translation, domain, rating)

    if should_create_recommendation and 'csp-findings' in result_dict[domain]:
        rec_rating, text_recommendation = create_csp_recommendation(
            domain,
            result_dict,
            org_domain,
            org_www_domain,
            local_translation,
            global_translation)
        if rec_rating.get_integrity_and_security() > final_rating.get_integrity_and_security():
            final_rating.overall_review = text_recommendation + final_rating.overall_review

    return final_rating

def create_final_csp_rating(global_translation, local_translation, domain, rating):
    """
    Creates a final rating for a CSP (Cloud Service Provider) based on the given parameters.

    This function takes in global and local translations, domain, and a rating object.
    It then creates a final rating object and sets its attributes based on the input rating and
    whether a detailed report is to be used.

    Parameters:
    global_translation (function): A function for global translation.
    local_translation (function): A function for local translation specific to the domain.
    domain (str): The domain for which the rating is being created.
    rating (Rating): The initial rating object which contains the overall rating,
    standards rating, and integrity and security rating.

    Returns:
    final_rating (Rating): The final rating object with the overall,
                           standards, and integrity and security ratings set.
    """
    final_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if rating.is_set:
        if get_config('general.review.details'):
            final_rating.set_overall(rating.get_overall())
            final_rating.overall_review = rating.overall_review
            final_rating.set_standards(rating.get_standards())
            final_rating.standards_review = rating.standards_review
            final_rating.set_integrity_and_security(rating.get_integrity_and_security())
            final_rating.integrity_and_security_review = rating.integrity_and_security_review
        else:
            final_rating.set_overall(rating.get_overall())
            final_rating.set_standards(rating.get_standards(),
                local_translation('TEXT_REVIEW_CSP').format(domain))
            final_rating.set_integrity_and_security(
                rating.get_integrity_and_security(),
                local_translation('TEXT_REVIEW_CSP').format(domain))
    return final_rating

def create_csp_recommendation(
        domain,
        result_dict,
        org_domain,
        org_www_domain,
        local_translation,
        global_translation):
    """
    This function creates a Content Security Policy (CSP) recommendation for a given domain.

    Parameters:
    domain (str): The domain for which the CSP recommendation is being created.
    result_dict (dict): A dictionary containing the CSP details for all domains.
    org_domain (str): The original domain name.
    org_www_domain (str): The original domain name with 'www.' prefix.
    local_translation (function): A function to translate text to the local language.
    global_translation (function): A function to translate text to a global language.

    Returns:
    tuple: A tuple containing a Rating object with the overall rating of the recommended CSP and
           a string with the text recommendation.
    """
    csp_recommendation_result = False
    csp_recommendation = ''
    csp_recommendation_result = {
                'visits': 1,
                domain: default_csp_result_object(True)
            }
    csp_recommendation = create_csp(result_dict[domain]['csp-findings'], domain)

    raw_csp_recommendation = csp_recommendation.replace('- ','').replace('\r\n','')
    result_dict[domain]['csp-recommendation'] = [raw_csp_recommendation]

    handle_csp(
                raw_csp_recommendation,
                domain,
                csp_recommendation_result,
                True,
                domain)

    csp_recommendation_result[domain]['features'].append('CSP-HEADER-FOUND')
    csp_recommendation_rating = rate_csp(
                csp_recommendation_result,
                global_translation,
                local_translation,
                org_domain,
                org_www_domain,
                domain,
                False)

    csp_recommendation_rating_summary = local_translation(
                'TEXT_REVIEW_CSP_RECOMMENDED_RATING').format(csp_recommendation_rating)

    nof_pages = 1
    if 'nof_pages' in result_dict:
        nof_pages = result_dict['nof_pages']

    text_recommendation = local_translation('TEXT_REVIEW_CSP_RECOMMENDED_TEXT').format(
                nof_pages, csp_recommendation, csp_recommendation_rating_summary)
    return csp_recommendation_rating, text_recommendation

# pylint: disable=too-many-locals
def rate_csp_policy(
        domain,
        total_number_of_sitespeedruns,
        policy_object,
        local_translation,
        global_translation):
    """
    This function rates the safety of a Content Security Policy (CSP) for a
    given domain based on various aspects of the policy.

    Parameters:
    domain (str): The domain for which the CSP is being rated.
    total_number_of_sitespeedruns (int): The total number of sitespeedruns.
    policy_object (dict): A dictionary containing the CSP details.
    local_translation (function): A function to translate text to the local language.
    global_translation (function): A function to translate text to a global language.

    Returns:
    Rating: A Rating object with the overall rating based on various aspects of the CSP.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    policy_name = policy_object['name']

    any_found, wildcards_rating = rate_csp_wildcards(
                domain,
                policy_object,
                local_translation,
                global_translation)
    rating += wildcards_rating

    safe_any_found, safe_rating = rate_csp_safe(
                domain,
                policy_object,
                local_translation,
                global_translation)
    any_found = any_found or safe_any_found
    rating += safe_rating

    nonce_any_found, nonce_rating = rate_csp_nonce(
                domain,
                total_number_of_sitespeedruns,
                policy_object,
                local_translation,
                global_translation)
    any_found = any_found or nonce_any_found
    rating += nonce_rating

    self_any_found, self_rating = rate_csp_self(
                domain,
                policy_object,
                local_translation,
                global_translation)
    any_found = any_found or self_any_found
    rating += self_rating

    rating += rate_csp_subdomains(
                domain,
                policy_object,
                local_translation,
                global_translation)

    domains_any_found, domains_rating = rate_csp_domains(
                domain,
                policy_object,
                local_translation,
                global_translation)
    any_found = any_found or domains_any_found
    rating += domains_rating

    schemes_any_found, schemes_rating = rate_csp_schemes(
                domain,
                policy_object,
                local_translation,
                global_translation)
    any_found = any_found or schemes_any_found
    rating += schemes_rating

    rating += rate_csp_malformed(
                domain,
                policy_object,
                local_translation,
                global_translation)

    if not any_found:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                        policy_name,
                        "'none', 'self' nonce, sha[256/384/512], domain or scheme",
                        domain))
        rating += sub_rating

    # Handles unsafe sources
    rating += rate_csp_unsafe(domain, policy_object, local_translation, global_translation)
    return rating

def rate_csp_depricated(domain, result_dict, local_translation, global_translation):
    """
    This function rates the safety of a Content Security Policy (CSP) for a
    given domain based on the usage of deprecated policies.

    Parameters:
    domain (str): The domain for which the CSP is being rated.
    result_dict (dict): A dictionary containing the CSP details for all domains.
    local_translation (function): A function to translate text to the local language.
    global_translation (function): A function to translate text to a global language.

    Returns:
    Rating: A Rating object with the overall rating based on the usage of deprecated policies.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    is_using_deprecated_policy = False
    for policy_name in CSP_POLICIES_DEPRECATED:
        if policy_name in result_dict[domain]['csp-objects']:
            is_using_deprecated_policy = True
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(1.0)
            sub_rating.set_standards(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_DEPRECATED').format(
                        policy_name, domain))
            rating += sub_rating

    if not is_using_deprecated_policy:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_NOT_DEPRECATED').format(
                        policy_name, domain))
        rating += sub_rating
    return rating

def rate_csp_malformed(domain, policy_object, local_translation, global_translation):
    """
    This function rates the safety of a Content Security Policy (CSP) for a
    given domain based on the presence of malformed policies.

    Parameters:
    domain (str): The domain for which the CSP is being rated.
    policy_object (dict): A dictionary containing the CSP details.
    local_translation (function): A function to translate text to the local language.
    global_translation (function): A function to translate text to a global language.

    Returns:
    Rating: A Rating object with the overall rating based on the presence of malformed policies.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    policy_name = policy_object['name']
    nof_malformed = len(policy_object['malformed'])
    if nof_malformed > 0:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
                    local_translation('TEXT_REVIEW_CSP_MALFORMED').format(
                        policy_name, domain))
        rating += sub_rating
    return rating

def rate_csp_self(domain, policy_object, local_translation, global_translation):
    """
    This function rates the safety of a Content Security Policy (CSP) for
    a given domain based on the 'self' directive.

    Parameters:
    domain (str): The domain for which the CSP is being rated.
    policy_object (dict): A dictionary containing the CSP details.
    local_translation (function): A function to translate text to the local language.
    global_translation (function): A function to translate text to a global language.

    Returns:
    tuple: A tuple containing a boolean indicating if any 'self' directive was found and
           a Rating object with the overall rating.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    policy_name = policy_object['name']
    any_found = False
    if "'self'" in policy_object['all']:
        if policy_name in CSP_POLICIES_SELF_ALLOWED:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(5.0)
            sub_rating.set_standards(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, "'self'", domain))
            sub_rating.set_integrity_and_security(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, "'self'", domain))
            rating += sub_rating
        else:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(3.0)
            sub_rating.set_standards(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, "'self'", domain))
            sub_rating.set_integrity_and_security(3.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, "'self'", domain))
            rating += sub_rating
        any_found = True
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                        policy_name, "'self'", domain))
        sub_rating.set_integrity_and_security(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                        policy_name, "'self'", domain))
        rating += sub_rating
    return any_found, rating

def rate_csp_safe(domain, policy_object, local_translation, global_translation):
    """
    This function rates the safety of a Content Security Policy (CSP) for a given domain.

    Parameters:
    domain (str): The domain for which the CSP is being rated.
    policy_object (dict): A dictionary containing the CSP details.
    local_translation (function): A function to translate text to the local language.
    global_translation (function): A function to translate text to a global language.

    Returns:
    tuple: A tuple containing a boolean indicating if any policy was found and
           a Rating object with the overall rating.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    policy_name = policy_object['name']
    any_found = False
    if "'none'" in policy_object['all']:
        if len(policy_object['all']) > 1:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(1.5)
            sub_rating.set_standards(1.5,
                        local_translation('TEXT_REVIEW_CSP_POLICY_NONE_NOT_ALONE').format(
                            policy_name, "'none'", domain))
            sub_rating.set_integrity_and_security(1.5,
                        local_translation('TEXT_REVIEW_CSP_POLICY_NONE_NOT_ALONE').format(
                            policy_name, "'none'", domain))
            rating += sub_rating
        else:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(5.0)
            sub_rating.set_standards(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, "'none'", domain))
            sub_rating.set_integrity_and_security(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, "'none'", domain))
            rating += sub_rating
        any_found = True
    elif len(policy_object['hashes']) > 0:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                        policy_name, "sha[256/384/512]", domain))
        sub_rating.set_integrity_and_security(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, "sha[256/384/512]", domain))
        rating += sub_rating
        any_found = True
    elif policy_name not in CSP_POLICIES_SELF_ALLOWED:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                        policy_name, "none/sha[256/384/512]", domain))
        sub_rating.set_integrity_and_security(1.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                            policy_name, "none/sha[256/384/512]", domain))
        rating += sub_rating
    return any_found, rating

def rate_csp_fallbacks(domain, result_dict, local_translation, global_translation):
    """
    Rates the usage of fallbacks in a Content Security Policy (CSP).

    This function creates a rating based on the presence of certain fallbacks in the result_dict. 
    It checks if each fallback in CSP_POLICIES_FALLBACK_SRC is present in the 'csp-objects' of the
    result_dict for the domain. Depending on the presence of these fallbacks, it sets the overall, 
    standards, and integrity and security ratings differently.

    Args:
        domain (str): The domain for which the CSP is being rated.
        result_dict (dict): A dictionary containing the result details. 
                            It should have a key for the domain, which itself is a dictionary 
                            containing a key 'csp-objects'.
        local_translation (function): A function to translate text to the local language.
        global_translation (function): A function to translate text to a global language.

    Returns:
        Rating: A Rating object representing the rating of the usage of fallbacks in the CSP.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    for policy_name in CSP_POLICIES_FALLBACK_SRC:
        if policy_name in result_dict[domain]['csp-objects']:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(5.0)
            sub_rating.set_integrity_and_security(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_FOUND').format(
                        policy_name, domain))
            sub_rating.set_standards(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_FOUND').format(
                        policy_name, domain))
            rating += sub_rating
        else:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(1.0)
            sub_rating.set_integrity_and_security(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_NOT_FOUND').format(
                        policy_name, domain))
            sub_rating.set_standards(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_NOT_FOUND').format(
                        policy_name, domain))
            rating += sub_rating
    return rating

def rate_csp_unsafe(domain, policy_object, local_translation, global_translation):
    """
    Rates the usage of unsafe directives in a Content Security Policy (CSP).

    This function creates a rating based on the presence of certain unsafe directives 
    ('unsafe-eval', 'wasm-unsafe-eval', 'unsafe-hashes', 'unsafe-inline') in the policy_object. 
    Depending on the presence of these directives, it sets the overall and integrity and security 
    ratings differently.

    Args:
        domain (str): The domain for which the CSP is being rated.
        policy_object (dict): A dictionary containing the policy details. 
                              It should have keys 'name' and 'all'.
        local_translation (function): A function to translate text to the local language.
        global_translation (function): A function to translate text to a global language.

    Returns:
        Rating: A Rating object representing the rating of
                the usage of unsafe directives in the CSP.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    policy_name = policy_object['name']
    is_using_unsafe = False
    if "'unsafe-eval'" in policy_object['all']:
        is_using_unsafe = True
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                        policy_name, "'unsafe-eval'", domain))
        rating += sub_rating

    if "'wasm-unsafe-eval'" in policy_object['all']:
        is_using_unsafe = True
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                        policy_name, "'wasm-unsafe-eval'", domain))
        rating += sub_rating

    if "'unsafe-hashes'" in policy_object['all']:
        is_using_unsafe = True
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                        policy_name, "'unsafe-hashes'", domain))
        rating += sub_rating

    if "'unsafe-inline'" in policy_object['all']:
        is_using_unsafe = True
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                        policy_name, "'unsafe-inline'", domain))
        rating += sub_rating

    if not is_using_unsafe:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                        policy_name, "'unsafe-*'", domain))
        rating += sub_rating
    return rating

def rate_csp_schemes(domain, policy_object, local_translation, global_translation):
    """
    Rates the usage of schemes in a Content Security Policy (CSP).

    This function creates a rating based on the number of schemes found in the policy_object. 
    It checks if the schemes 'ws', 'http', or 'ftp' are present in the policy_object.
    Depending on the case, it sets the overall and integrity and security ratings differently.

    Args:
        domain (str): The domain for which the CSP is being rated.
        policy_object (dict): A dictionary containing the policy details. 
                              It should have keys 'name' and 'schemes'.
        local_translation (function): A function to translate text to the local language.
        global_translation (function): A function to translate text to a global language.

    Returns:
        tuple: A tuple containing a boolean indicating whether any schemes were found, 
               and a Rating object representing the rating.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    policy_name = policy_object['name']
    any_found = False
    nof_schemes = len(policy_object['schemes'])
    if nof_schemes > 0:
        if 'ws' in policy_object['schemes']:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(1.0)
            sub_rating.set_integrity_and_security(1.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_USE_UNSAFE_SCHEME').format(
                            policy_name, "'ws'", domain))
            rating += sub_rating
        if 'http' in policy_object['schemes']:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(1.0)
            sub_rating.set_integrity_and_security(1.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_USE_UNSAFE_SCHEME').format(
                            policy_name, "'http'", domain))
            rating += sub_rating
        if 'ftp' in policy_object['schemes']:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(1.0)
            sub_rating.set_integrity_and_security(1.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_USE_UNSAFE_SCHEME').format(
                            policy_name, "'ftp'", domain))
            rating += sub_rating
        any_found = True
    return any_found, rating

def rate_csp_domains(domain, policy_object, local_translation, global_translation):
    """
    Rates the usage of domains in a Content Security Policy (CSP).

    This function creates a rating based on the number of domains found in the policy_object. 
    It checks if the number of domains is greater than 15, less than or equal to 15, or zero. 
    Depending on the case, it sets the overall, standards, and
    integrity and security ratings differently.

    Args:
        domain (str): The domain for which the CSP is being rated.
        policy_object (dict): A dictionary containing the policy details. 
                              It should have keys 'name' and 'domains'.
        local_translation (function): A function to translate text to the local language.
        global_translation (function): A function to translate text to a global language.

    Returns:
        tuple: A tuple containing a boolean indicating whether any domains were found, 
               and a Rating object representing the rating.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    any_found = False
    policy_name = policy_object['name']
    nof_domains = len(policy_object['domains'])
    if nof_domains > 0:
        if nof_domains > 15:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(1.5)
            sub_rating.set_integrity_and_security(1.5,
                        local_translation('TEXT_REVIEW_CSP_POLICY_USE_15_OR_MORE_DOMAINS').format(
                            policy_name, local_translation('TEXT_REVIEW_CSP_DOMAIN'), domain))
            rating += sub_rating

        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(2.0)
        sub_rating.set_integrity_and_security(2.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                        policy_name, local_translation('TEXT_REVIEW_CSP_DOMAIN'), domain))
        rating += sub_rating
        any_found = True
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                        policy_name, local_translation('TEXT_REVIEW_CSP_DOMAIN'), domain))
        sub_rating.set_integrity_and_security(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                        policy_name, local_translation('TEXT_REVIEW_CSP_DOMAIN'), domain))
        rating += sub_rating
    return any_found, rating

def rate_csp_subdomains(domain, policy_object, local_translation, global_translation):
    """
    Rates the usage of subdomains in a Content Security Policy (CSP).

    This function creates a rating based on the number of subdomains found in the policy_object. 
    It checks if the policy name is in the list of policies where 'self' is allowed. Depending on 
    the case, it sets the overall, standards, and integrity and security ratings differently.

    Args:
        domain (str): The domain for which the CSP is being rated.
        policy_object (dict): A dictionary containing the policy details. 
                              It should have keys 'name' and 'subdomains'.
        local_translation (function): A function to translate text to the local language.
        global_translation (function): A function to translate text to a global language.

    Returns:
        Rating: A Rating object representing the rating of the usage of subdomains in the CSP.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    policy_name = policy_object['name']
    nof_subdomains = len(policy_object['subdomains'])
    if nof_subdomains > 0:
        if policy_name in CSP_POLICIES_SELF_ALLOWED:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(5.0)
            sub_rating.set_integrity_and_security(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, local_translation('TEXT_REVIEW_CSP_SUBDOMAIN'), domain))
            rating += sub_rating
        else:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(3.0)
            sub_rating.set_integrity_and_security(3.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, local_translation('TEXT_REVIEW_CSP_SUBDOMAIN'), domain))
            rating += sub_rating
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                        policy_name, local_translation('TEXT_REVIEW_CSP_SUBDOMAIN'), domain))
        sub_rating.set_integrity_and_security(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                        policy_name, local_translation('TEXT_REVIEW_CSP_SUBDOMAIN'), domain))
        rating += sub_rating
    return rating

def rate_csp_nonce(
        domain,
        total_number_of_sitespeedruns,
        policy_object,
        local_translation,
        global_translation):
    """
    Rates the usage of nonces in a Content Security Policy (CSP).

    This function creates a rating based on the number of nonces found in the policy_object. 
    It checks if the number of nonces is equal to 1,
    greater than the total number of site speedruns,
    or falls into any other case. Depending on the case, it sets the overall, standards, and 
    integrity and security ratings differently.

    Args:
        domain (str): The domain for which the CSP is being rated.
        total_number_of_sitespeedruns (int): The total number of site speedruns.
        policy_object (dict): A dictionary containing the policy details. 
                              It should have keys 'name' and 'nounces'.
        local_translation (function): A function to translate text to the local language.
        global_translation (function): A function to translate text to a global language.

    Returns:
        tuple: A tuple containing a boolean indicating whether any nonces were found, 
               and a Rating object representing the rating.
    """

    rating = Rating(global_translation, get_config('general.review.improve-only'))
    any_found = False
    policy_name = policy_object['name']
    nof_nonces = len(policy_object['nounces'])
    if nof_nonces > 0:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        if nof_nonces == 1 and total_number_of_sitespeedruns != nof_nonces:
            sub_rating.set_overall(1.0)
            sub_rating.set_standards(1.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_REUSE_NONCE').format(
                            policy_name, domain))
            sub_rating.set_integrity_and_security(1.0,
                            local_translation('TEXT_REVIEW_CSP_POLICY_REUSE_NONCE').format(
                                policy_name, domain))
        elif nof_nonces > total_number_of_sitespeedruns:
            sub_rating.set_overall(4.75)
            sub_rating.set_standards(4.99,
                        local_translation('TEXT_REVIEW_CSP_POLICY_MULTIUSE_NONCE').format(
                            policy_name, "'nonce's", domain))
            sub_rating.set_integrity_and_security(4.5,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, "nonce", domain))
        else:
            sub_rating.set_overall(4.5)
            sub_rating.set_standards(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, "'nonce'", domain))
            sub_rating.set_integrity_and_security(4.5,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, "'nonce'", domain))
        rating += sub_rating
        any_found = True
    return any_found, rating

def rate_csp_wildcards(domain, policy_object, local_translation, global_translation):
    """
    Rates the usage of wildcards in a Content Security Policy (CSP).

    This function iterates over the 'wildcards' in the policy_object. Each wildcard is checked 
    for certain conditions and based on these conditions, a rating is calculated. The function 
    also checks for the usage of wildcard subdomains in the policy and adjusts the rating 
    accordingly. If no wildcard is used in the policy, a perfect rating is given.

    Args:
        domain (str): The domain for which the CSP is being rated.
        policy_object (dict): A dictionary containing the policy details. 
                              It should have keys 'name', 'wildcards', and 'wildcard-subdomains'.
        local_translation (function): A function to translate text to the local language.
        global_translation (function): A function to translate text to a global language.

    Returns:
        tuple: A tuple containing a boolean indicating whether any wildcard was found and 
               a Rating object representing the calculated rating.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    is_using_wildcard_in_policy = False
    any_found = False
    policy_name = policy_object['name']
    for wildcard in policy_object['wildcards']:
        is_using_wildcard_in_policy = True
        any_found = True
        if wildcard.endswith('*'):
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(1.0)
            sub_rating.set_standards(1.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_USE_WILDCARD').format(
                            policy_name, domain))
            rating += sub_rating
        else:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(2.0)
            sub_rating.set_integrity_and_security(2.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, local_translation('TEXT_REVIEW_CSP_WILDCARDS'), domain))
            rating += sub_rating

    nof_wildcard_subdomains = len(policy_object['wildcard-subdomains'])
    if nof_wildcard_subdomains > 0:
        if policy_name in CSP_POLICIES_SELF_ALLOWED:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(5.0)
            sub_rating.set_integrity_and_security(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name,
                            local_translation('TEXT_REVIEW_CSP_WILDCARD_SUBDOMAIN'), domain))
            rating += sub_rating
        else:
            sub_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            sub_rating.set_overall(2.7)
            sub_rating.set_integrity_and_security(2.7,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name,
                            local_translation('TEXT_REVIEW_CSP_WILDCARD_SUBDOMAIN'), domain))
            rating += sub_rating

    if not is_using_wildcard_in_policy:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_NOT_USE_WILDCARD').format(
                            policy_name, domain))
        rating += sub_rating
    return any_found, rating

def default_csp_result_object(is_org_domain):
    """
    Creates a default Content Security Policy (CSP) result object.

    This function creates a dictionary with keys for protocols, schemes, ip-versions, 
    transport-layers, features, urls, and csp-policies, all of which are initialized 
    with empty lists. If the domain is the original domain, an additional key 'csp-findings' 
    is added to the dictionary, which itself is a dictionary with keys for quotes, 
    host-sources, scheme-sources, and font-sources, all initialized with empty lists.

    Args:
        is_org_domain (bool): A boolean indicating whether the domain is the original domain.

    Returns:
        dict: A dictionary representing the default CSP result object.
    """
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


def create_csp(csp_findings, org_domain): # pylint: disable=too-many-branches,too-many-statements
    """
    Creates a Content Security Policy (CSP) recommendation based on the findings.

    Args:
        csp_findings (dict): A dictionary containing CSP findings. 
                             It should have keys 'quotes', 'host-sources', and 'scheme-sources'.
        org_domain (str): The original domain for which the CSP is being created.

    Returns:
        str: A string containing the CSP recommendation.
    """
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
                default_src.append(host_source)
            else:
                default_src.append(host_source)
        else:
            if source == org_domain:
                default_src.append('\'self\'')
            else:
                default_src.append(source)

    append_schemes_to_img_srcs(csp_findings, img_src)

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

    csp_recommendation = ''
    csp_recommendation = append_if_not_empty('default-src', default_src, csp_recommendation)
    csp_recommendation = append_if_not_empty('base-uri', base_uri, csp_recommendation)
    csp_recommendation = append_if_not_empty('img-src', img_src, csp_recommendation)
    csp_recommendation = append_if_not_empty('script-src', script_src, csp_recommendation)
    csp_recommendation = append_if_not_empty('form-action', form_action, csp_recommendation)
    csp_recommendation = append_if_not_empty('style-src', style_src, csp_recommendation)
    csp_recommendation = append_if_not_empty('child-src', child_src, csp_recommendation)
    csp_recommendation = append_if_not_empty('object-src', object_src, csp_recommendation)
    csp_recommendation = append_if_not_empty('frame-ancestors', frame_ancestors, csp_recommendation)
    csp_recommendation = append_if_not_empty('connect-src', connect_src, csp_recommendation)
    csp_recommendation = append_if_not_empty('font-src', font_src, csp_recommendation)

    return csp_recommendation

def append_schemes_to_img_srcs(csp_findings, img_src):
    """
    Appends host sources to the img_src list if the element name is 'img'.

    This function iterates over the 'scheme-sources' in the csp_findings dictionary. 
    Each source is split into a host source and an element name. If the element name 
    is 'img', the host source is appended to the img_src list.

    Args:
        csp_findings (dict): A dictionary containing CSP findings. 
                             It should have a key 'scheme-sources' which
                             contains a list of sources.
        img_src (list): A list to which host sources will be appended.
    """
    for source in csp_findings['scheme-sources']:
        if '|' in source:
            pair = source.split('|')
            host_source = pair[0]
            element_name = pair[1]
            if element_name == 'img':
                img_src.append(host_source)

def append_if_not_empty(policy_name, policy_list, csp_recommendation):
    """
    Appends a policy to the CSP recommendation if the policy list is not empty.

    This function checks if the policy list is not empty.
    If it's not, it sorts the list, removes duplicates,
    joins the elements into a string, and appends it to the CSP recommendation.

    Args:
        policy_name (str): The name of the policy.
        policy_list (list): The list of policies.
        csp_recommendation (str): The existing CSP recommendation.

    Returns:
        str: The updated CSP recommendation.
    """
    policy_content = ' '.join(sorted(list(set(policy_list))))
    policy_content = policy_content.strip()
    if len(policy_content) > 0:
        csp_recommendation += f'- {policy_name} {policy_content};\r\n'
    return csp_recommendation

def append_csp_data(req_url, req_domain, res, org_domain, result):
    """
    Appends Content Security Policy (CSP) data for various types of content.

    This function checks the type of content (HTML, CSS, JavaScript, image, font) and
    calls the appropriate function to append the CSP data to the result dictionary. 
    If no match is found, it checks if the requested domain is the same as the original domain and
    appends the appropriate CSP data.

    Args:
        req_url (str): The requested URL.
        req_domain (str): The requested domain.
        res (dict): The response dictionary containing the content.
        org_domain (str): The original domain.
        result (dict): The result dictionary where the CSP data will be appended.

    Returns:
        bool: True if there is a match in the CSP findings, False otherwise.
    """
    csp_findings_match = False
    # TODO: Remove text empty check when sitespeed has fixed https://github.com/sitespeedio/sitespeed.io/issues/4295
    if 'content' in res and 'text' in res['content'] and res['content']['text'] != '':
        if 'mimeType' in res['content'] and 'text/html' in res['content']['mimeType']:
            csp_findings_match = csp_findings_match or append_csp_data_for_html(
                req_url,
                req_domain,
                res,
                org_domain,
                result)
        elif 'mimeType' in res['content'] and 'text/css' in res['content']['mimeType']:
            csp_findings_match = csp_findings_match or append_csp_data_for_css(
                req_url,
                req_domain,
                res,
                org_domain,
                result)
        elif 'mimeType' in res['content'] and\
                ('text/javascript' in res['content']['mimeType'] or\
                    'application/javascript' in res['content']['mimeType']):
            csp_findings_match = csp_findings_match or append_csp_data_for_js(
                req_url,
                req_domain,
                res,
                org_domain,
                result)
    if 'mimeType' in res['content'] and 'image/' in res['content']['mimeType']:
        csp_findings_match = csp_findings_match or append_csp_data_for_images(
            req_url,
            req_domain,
            org_domain,
            result)
    elif ('mimeType' in res['content'] and 'font/' in res['content']['mimeType']) or\
            req_url.endswith('.otf') or\
            req_url.endswith('.woff') or\
            req_url.endswith('.woff2'):
        csp_findings_match = csp_findings_match or append_csp_data_for_fonts(
            req_url,
            req_domain,
            res,
            org_domain,
            result)

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

def append_csp_data_for_fonts(req_url, req_domain, res, org_domain, result):
    """
    Appends Content Security Policy (CSP) data for font content.

    This function checks the font content for 'woff' and 'woff2' formats and
    appends the CSP data to the result dictionary. 
    It also checks if the requested domain is the same as the original domain and
    appends the appropriate CSP data.

    Args:
        req_url (str): The requested URL.
        req_domain (str): The requested domain.
        res (dict): The response dictionary containing the font content.
        org_domain (str): The original domain.
        result (dict): The result dictionary where the CSP data will be appended.

    Returns:
        bool: True if there is a match in the CSP findings, False otherwise.
    """
    csp_findings_match = False
    element_domain = req_domain
    element_name = 'font'
    # woff and woff2 support is in all browser, add hash to our csp-findings
    has_font_hash = False
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
                key2 = f"'{f'sha256-{font_hash}'}'|{element_name}"
                if key not in result[org_domain]['csp-findings']['font-sources']:
                    result[org_domain]['csp-findings']['quotes'].append(key2)
                    result[org_domain]['csp-findings']['font-sources'].append(key)
                has_font_hash = True
            elif get_config('tests.http.csp-generate-font-hashes') or\
                  get_config('tests.http.csp-generate-strict-recommended-hashes') or\
                  get_config('tests.http.csp-generate-hashes'):
                font_content = get_http_content(req_url, True, False)
                font_hash = create_sha256_hash(font_content)
                key2 = f"'{f'sha256-{font_hash}'}'|{element_name}"
                if key not in result[org_domain]['csp-findings']['font-sources']:
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

def append_csp_data_for_images(req_url, req_domain, org_domain, result):
    """
    Appends Content Security Policy (CSP) data for image content.

    This function checks if the requested domain is the same as the original domain and
    appends the appropriate CSP data for images to the result dictionary.

    Args:
        req_url (str): The requested URL.
        req_domain (str): The requested domain.
        org_domain (str): The original domain.
        result (dict): The result dictionary where the CSP data will be appended.

    Returns:
        bool: True if there is a match in the CSP findings, False otherwise.
    """
    csp_findings_match = False
    element_domain = req_domain
    element_name = 'img'
    has_img_hash = False

    if get_config('tests.http.csp-generate-img-hashes') or\
            get_config('tests.http.csp-generate-hashes'):
        font_content = get_http_content(req_url, True, False)
        font_hash = create_sha256_hash(font_content)
        key2 = f"'{f'sha256-{font_hash}'}'|{element_name}"
        if key2 not in result[org_domain]['csp-findings']['quotes']:
            result[org_domain]['csp-findings']['quotes'].append(key2)
        has_img_hash = True

    if not has_img_hash:
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

def append_csp_data_for_js(req_url, req_domain, res, org_domain, result):
    """
    Appends Content Security Policy (CSP) data for JavaScript content.

    This function checks the JavaScript content for 'eval(' and
    appends the CSP data to the result dictionary. 
    It also checks if the requested domain is the same as the original domain and
    appends the appropriate CSP data.

    Args:
        req_url (str): The requested URL.
        req_domain (str): The requested domain.
        res (dict): The response dictionary containing the JavaScript content.
        org_domain (str): The original domain.
        result (dict): The result dictionary where the CSP data will be appended.

    Returns:
        bool: True if there is a match in the CSP findings, False otherwise.
    """
    csp_findings_match = False

    if res is not None:
        content = res['content']['text']
        if 'eval(' in content:
            key = '\'unsafe-eval\'|script'
            if key not in result[org_domain]['csp-findings']['quotes']:
                result[org_domain]['csp-findings']['quotes'].append(key)
            csp_findings_match = True

    element_domain = req_domain
    element_name = 'script'
    has_js_hash = False

    if get_config('tests.http.csp-generate-js-hashes') or\
            get_config('tests.http.csp-generate-strict-recommended-hashes') or\
            get_config('tests.http.csp-generate-hashes'):
        key = f'{req_url}|{element_name}'
        font_content = get_http_content(req_url, True, False)
        font_hash = create_sha256_hash(font_content)
        key2 = f"'{f'sha256-{font_hash}'}'|{element_name}"
        if key not in result[org_domain]['csp-findings']['quotes']:
            result[org_domain]['csp-findings']['quotes'].append(key2)
        has_js_hash = True

    if not has_js_hash:
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

def append_csp_data_for_css(req_url, req_domain, res, org_domain, result):
    """
    Appends Content Security Policy (CSP) data for CSS content.

    This function checks the CSS content for 'data:image' and
    appends the CSP data to the result dictionary. 
    It also checks if the requested domain is the same as the original domain and
    appends the appropriate CSP data.

    Args:
        req_domain (str): The requested domain.
        res (dict): The response dictionary containing the CSS content.
        org_domain (str): The original domain.
        result (dict): The result dictionary where the CSP data will be appended.

    Returns:
        bool: True if there is a match in the CSP findings, False otherwise.
    """
    csp_findings_match = False
    content = res['content']['text']
    if 'data:image' in content:
        key = 'data:|img'
        if key not in result[org_domain]['csp-findings']['scheme-sources']:
            result[org_domain]['csp-findings']['scheme-sources'].append(key)
        csp_findings_match = True

    element_domain = req_domain
    element_name = 'style'
    has_css_hash = False

    if get_config('tests.http.csp-generate-css-hashes') or\
            get_config('tests.http.csp-generate-strict-recommended-hashes') or\
            get_config('tests.http.csp-generate-hashes'):
        font_content = get_http_content(req_url, True, False)
        font_hash = create_sha256_hash(font_content)
        key2 = f"'{f'sha256-{font_hash}'}'|{element_name}"
        if key2 not in result[org_domain]['csp-findings']['quotes']:
            result[org_domain]['csp-findings']['quotes'].append(key2)
        has_css_hash = True

    if not has_css_hash:
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

def append_csp_data_for_html(req_url, req_domain, res, org_domain, result):
    """
    Appends Content Security Policy (CSP) data for HTML content and linked resources.

    This function parses the HTML content and identifies the CSP from meta tags.
    It also identifies linked resources such as style, script, and form elements. 
    It then appends the CSP data for these resources to the result dictionary.

    Args:
        req_url (str): The requested URL.
        req_domain (str): The requested domain.
        res (dict): The response dictionary containing the HTML content.
        org_domain (str): The original domain.
        result (dict): The result dictionary where the CSP data will be appended.

    Returns:
        bool: True if there is a match in the CSP findings, False otherwise.
    """
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
            handle_csp(value2, req_domain, result, False, org_domain)
        elif 'x-content-security-policy' in name2:
            result[req_domain]['features'].append('CSP-META-FOUND')
            result[req_domain]['features'].append('CSP-DEPRECATED')
            handle_csp(value2, req_domain, result, False, org_domain)

    csp_findings_match = csp_findings_match or append_csp_data_for_linked_resources(
        req_url,
        req_domain,
        org_domain,
        result,
        content)

    regex = r'<(?P<type>style|script|form)>'
    matches = re.finditer(regex, content, re.DOTALL | re.IGNORECASE | re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        element_name = match.group('type').lower()
        if element_name in ('style', 'script'):
            key = f'\'unsafe-inline\'|{element_name}'
            if key not in result[org_domain]['csp-findings']['quotes']:
                result[org_domain]['csp-findings']['quotes'].append(key)
            csp_findings_match = True
        elif element_name == 'form':
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

def append_csp_data_for_linked_resources(req_url, req_domain, org_domain, result, content):
    """
    Appends Content Security Policy (CSP) data for linked resources in a given HTML content.

    This function parses the HTML content and identifies linked resources such as
    style, link, script, img, iframe, form, base, and frame elements. 
    It then appends the CSP data for these resources to the result dictionary.

    Args:
        req_domain (str): The requested domain.
        org_domain (str): The original domain.
        result (dict): The result dictionary where the CSP data will be appended.
        content (str): The HTML content to be parsed.

    Returns:
        bool: True if there is a match in the CSP findings, False otherwise.
    """
    csp_findings_match = False
    regex = (
                    r'(?P<raw><(?P<type>style|link|script|img|iframe|form|base|frame)[^>]'
                    r'*((?P<attribute>src|nonce|action|href)="(?P<value>[^"]+)"[^>]*>))'
                )

    matches = re.finditer(regex, content, re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        element_name = match.group('type').lower()
        attribute_name = match.group('attribute').lower()
        attribute_value = match.group('value')

        element_url = url_2_host_source(attribute_value, req_domain)
        o = urllib.parse.urlparse(element_url)
        element_domain = o.hostname
        if element_domain is None and element_url.lower().startswith('data:'):
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
                if element_name == 'img':
                    append_csp_data_for_images(element_url,element_domain,org_domain, result)
                    csp_findings_match = True
                elif element_name == 'script':
                    append_csp_data_for_js(element_url, element_domain, None, org_domain, result)
                    csp_findings_match = True
                else:
                    key = f'{element_domain}|{element_name}'
                    if key not in result[org_domain]['csp-findings']['host-sources']:
                        result[org_domain]['csp-findings']['host-sources'].append(key)
                    csp_findings_match = True
        elif attribute_name == 'action' and element_name == 'form':
            key = f'{element_domain}|form-action'
            if key not in result[org_domain]['csp-findings']['host-sources']:
                result[org_domain]['csp-findings']['host-sources'].append(key)
            csp_findings_match = True
    return csp_findings_match

def url_2_host_source(url, domain):
    """
    Converts a given URL to a secure (https) URL if it's not already.

    Args:
        url (str): The URL to be converted.
        domain (str): The domain to be used if the URL doesn't contain a domain.

    Returns:
        str: The converted secure URL.
    """
    if url.startswith('//'):
        return url.replace('//', 'https://')
    if 'https://' in url.lower():
        return url
    if '://' in url:
        return url
    if ':' in url:
        return url
    if url.startswith('/'):
        url = url.strip('/')
    return f'https://{domain}/{url}'
