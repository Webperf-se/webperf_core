# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines
import base64
import re
import urllib
import urllib.parse
from helpers.data_helper import append_domain_entry, extend_domain_entry_with_key
from helpers.hash_helper import create_sha256_hash
from models import Rating
from tests.utils import get_config_or_default

# DEFAULTS
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
USE_DETAILED_REPORT = get_config_or_default('USE_DETAILED_REPORT')
CSP_POLICIES_SUPPORTED_SRC = [
    'default-src','script-src','style-src','font-src',
    'connect-src','frame-src','img-src','media-src',
    'frame-ancestors','base-uri','form-action','child-src',
    'manifest-src','object-src','script-src-attr',
    'script-src-elem','style-src-attr','style-src-elem','worker-src']
CSP_POLICIES_SELF_ALLOWED = [
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
    parse_csp(content, domain, result_dict, is_from_response_header)
    # Add style-src policies to all who uses it as fallback
    ensure_csp_policy_fallbacks(domain, result_dict)

    # convert polices to objects
    convert_csp_policies_2_csp_objects(domain, result_dict, org_domain)

def parse_csp(content, domain, result_dict, is_from_response_header):
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
        append_csp_policy('script-src', default_items, domain, result_dict)
        append_csp_policy('script-src-elem', default_items, domain, result_dict)
        append_csp_policy('script-src-attr', default_items, domain, result_dict)
        append_csp_policy('style-src', default_items, domain, result_dict)
        append_csp_policy('style-src-elem', default_items, domain, result_dict)
        append_csp_policy('style-src-attr', default_items, domain, result_dict)
        append_csp_policy('worker-src', default_items, domain, result_dict)

def append_csp_policy(policy_name, items, domain, result_dict):
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
    result = host_source
    if '*' in result:
        result = result.replace('*', 'webperf-core-wildcard')
    if '://' not in result:
        result = f'https://{result}'

    return result

# pylint: disable=too-many-arguments
def rate_csp(result_dict, global_translation, local_translation,
             org_domain, org_www_domain, domain, should_create_recommendation):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if not isinstance(result_dict[domain], dict):
        return rating

    if domain not in (org_domain, org_www_domain):
        return rating

    if 'CSP-HEADER-FOUND' in result_dict[domain]['features'] or\
            'CSP-META-FOUND' in result_dict[domain]['features']:
        total_number_of_sitespeedruns = result_dict['visits']

        if 'CSP-UNSUPPORTED-IN-META' in result_dict[domain]['features']:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
        rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    is_using_deprecated_policy = False
    for policy_name in CSP_POLICIES_DEPRECATED:
        if policy_name in result_dict[domain]['csp-objects']:
            is_using_deprecated_policy = True
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(1.0)
            sub_rating.set_standards(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_DEPRECATED').format(
                        policy_name, domain))
            rating += sub_rating

    if not is_using_deprecated_policy:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_NOT_DEPRECATED').format(
                        policy_name, domain))
        rating += sub_rating
    return rating

def rate_csp_malformed(domain, policy_object, local_translation, global_translation):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    policy_name = policy_object['name']
    nof_malformed = len(policy_object['malformed'])
    if nof_malformed > 0:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
                    local_translation('TEXT_REVIEW_CSP_MALFORMED').format(
                        policy_name, domain))
        rating += sub_rating
    return rating

def rate_csp_self(domain, policy_object, local_translation, global_translation):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    policy_name = policy_object['name']
    any_found = False
    if "'self'" in policy_object['all']:
        if policy_name in CSP_POLICIES_SELF_ALLOWED:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(5.0)
            sub_rating.set_standards(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, "'self'", domain))
            sub_rating.set_integrity_and_security(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, "'self'", domain))
            rating += sub_rating
        else:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    policy_name = policy_object['name']
    any_found = False
    if "'none'" in policy_object['all']:
        if len(policy_object['all']) > 1:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(1.5)
            sub_rating.set_standards(1.5,
                        local_translation('TEXT_REVIEW_CSP_POLICY_NONE_NOT_ALONE').format(
                            policy_name, "'none'", domain))
            sub_rating.set_integrity_and_security(1.5,
                        local_translation('TEXT_REVIEW_CSP_POLICY_NONE_NOT_ALONE').format(
                            policy_name, "'none'", domain))
            rating += sub_rating
        else:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    for policy_name in CSP_POLICIES_FALLBACK_SRC:
        if policy_name in result_dict[domain]['csp-objects']:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(5.0)
            sub_rating.set_integrity_and_security(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_FOUND').format(
                        policy_name, domain))
            sub_rating.set_standards(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_FOUND').format(
                        policy_name, domain))
            rating += sub_rating
        else:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    policy_name = policy_object['name']
    is_using_unsafe = False
    if "'unsafe-eval'" in policy_object['all']:
        is_using_unsafe = True
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                        policy_name, "'unsafe-eval'", domain))
        rating += sub_rating

    if "'wasm-unsafe-eval'" in policy_object['all']:
        is_using_unsafe = True
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                        policy_name, "'wasm-unsafe-eval'", domain))
        rating += sub_rating

    if "'unsafe-hashes'" in policy_object['all']:
        is_using_unsafe = True
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                        policy_name, "'unsafe-hashes'", domain))
        rating += sub_rating

    if "'unsafe-inline'" in policy_object['all']:
        is_using_unsafe = True
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                        policy_name, "'unsafe-inline'", domain))
        rating += sub_rating

    if not is_using_unsafe:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                        policy_name, "'unsafe-*'", domain))
        rating += sub_rating
    return rating

def rate_csp_schemes(domain, policy_object, local_translation, global_translation):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    policy_name = policy_object['name']
    any_found = False
    nof_schemes = len(policy_object['schemes'])
    if nof_schemes > 0:
        if 'ws' in policy_object['schemes']:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(1.0)
            sub_rating.set_integrity_and_security(1.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_USE_UNSAFE_SCHEME').format(
                            policy_name, "'ws'", domain))
            rating += sub_rating
        if 'http' in policy_object['schemes']:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(1.0)
            sub_rating.set_integrity_and_security(1.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_USE_UNSAFE_SCHEME').format(
                            policy_name, "'http'", domain))
            rating += sub_rating
        if 'ftp' in policy_object['schemes']:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(1.0)
            sub_rating.set_integrity_and_security(1.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_USE_UNSAFE_SCHEME').format(
                            policy_name, "'ftp'", domain))
            rating += sub_rating
        any_found = True
    return any_found, rating

def rate_csp_domains(domain, policy_object, local_translation, global_translation):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    any_found = False
    policy_name = policy_object['name']
    nof_domains = len(policy_object['domains'])
    if nof_domains > 0:
        if nof_domains > 15:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(1.5)
            sub_rating.set_integrity_and_security(1.5,
                        local_translation('TEXT_REVIEW_CSP_POLICY_USE_15_OR_MORE_DOMAINS').format(
                            policy_name, local_translation('TEXT_REVIEW_CSP_DOMAIN'), domain))
            rating += sub_rating

        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(2.0)
        sub_rating.set_integrity_and_security(2.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                        policy_name, local_translation('TEXT_REVIEW_CSP_DOMAIN'), domain))
        rating += sub_rating
        any_found = True
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    policy_name = policy_object['name']
    nof_subdomains = len(policy_object['subdomains'])
    if nof_subdomains > 0:
        if policy_name in CSP_POLICIES_SELF_ALLOWED:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(5.0)
            sub_rating.set_integrity_and_security(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, local_translation('TEXT_REVIEW_CSP_SUBDOMAIN'), domain))
            rating += sub_rating
        else:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(3.0)
            sub_rating.set_integrity_and_security(3.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, local_translation('TEXT_REVIEW_CSP_SUBDOMAIN'), domain))
            rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    any_found = False
    policy_name = policy_object['name']
    nof_nonces = len(policy_object['nounces'])
    if nof_nonces > 0:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
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
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    is_using_wildcard_in_policy = False
    any_found = False
    policy_name = policy_object['name']
    for wildcard in policy_object['wildcards']:
        is_using_wildcard_in_policy = True
        any_found = True
        if wildcard.endswith('*'):
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(1.0)
            sub_rating.set_standards(1.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_USE_WILDCARD').format(
                            policy_name, domain))
            rating += sub_rating
        else:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(2.0)
            sub_rating.set_integrity_and_security(2.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name, local_translation('TEXT_REVIEW_CSP_WILDCARDS'), domain))
            rating += sub_rating

    nof_wildcard_subdomains = len(policy_object['wildcard-subdomains'])
    if nof_wildcard_subdomains > 0:
        if policy_name in CSP_POLICIES_SELF_ALLOWED:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(5.0)
            sub_rating.set_integrity_and_security(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name,
                            local_translation('TEXT_REVIEW_CSP_WILDCARD_SUBDOMAIN'), domain))
            rating += sub_rating
        else:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(2.7)
            sub_rating.set_integrity_and_security(2.7,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_USING').format(
                            policy_name,
                            local_translation('TEXT_REVIEW_CSP_WILDCARD_SUBDOMAIN'), domain))
            rating += sub_rating

    if not is_using_wildcard_in_policy:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_NOT_USE_WILDCARD').format(
                            policy_name, domain))
        rating += sub_rating
    return any_found, rating

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


def create_csp(csp_findings, org_domain): # pylint: disable=too-many-branches,too-many-statements
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
    for source in csp_findings['scheme-sources']:
        if '|' in source:
            pair = source.split('|')
            host_source = pair[0]
            element_name = pair[1]
            if element_name == 'img':
                img_src.append(host_source)

def append_if_not_empty(policy_name, policy_list, csp_recommendation):
    policy_content = ' '.join(sorted(list(set(policy_list))))
    policy_content = policy_content.strip()
    if len(policy_content) > 0:
        csp_recommendation += f'- {policy_name} {policy_content};\r\n'
    return csp_recommendation

def append_csp_data(req_url, req_domain, res, org_domain, result):
    csp_findings_match = False
    if 'content' in res and 'text' in res['content']:
        if 'mimeType' in res['content'] and 'text/html' in res['content']['mimeType']:
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

        elif 'mimeType' in res['content'] and 'text/css' in res['content']['mimeType']:
            content = res['content']['text']
            if 'data:image' in content:
                key = 'data:|img'
                if key not in result[org_domain]['csp-findings']['scheme-sources']:
                    result[org_domain]['csp-findings']['scheme-sources'].append(key)
                csp_findings_match = True
            element_domain = req_domain
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
        elif 'mimeType' in res['content'] and\
                ('text/javascript' in res['content']['mimeType'] or\
                    'application/javascript' in res['content']['mimeType']):
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
                key = '{0}|{1}'.format(element_domain, element_name)
                if key not in result[org_domain]['csp-findings']['host-sources']:
                    result[org_domain]['csp-findings']['host-sources'].append(key)
                csp_findings_match = True
    if 'mimeType' in res['content'] and 'image/' in res['content']['mimeType']:
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
    elif ('mimeType' in res['content'] and 'font/' in res['content']['mimeType']) or\
            req_url.endswith('.otf') or\
            req_url.endswith('.woff') or\
            req_url.endswith('.woff2'):
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
