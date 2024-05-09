# -*- coding: utf-8 -*-
import re
import urllib
import urllib.parse
import hashlib
import base64
from models import Rating
from tests.utils import get_config_or_default


# DEFAULTS
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
USE_DETAILED_REPORT = get_config_or_default('USE_DETAILED_REPORT')

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
    if len(default_src) > 0:
        csp_recommendation += f'- default-src {default_src};\r\n'
    if len(base_uri) > 0:
        csp_recommendation += f'- base-uri {base_uri};\r\n'
    if len(img_src) > 0:
        csp_recommendation += f'- img-src {img_src};\r\n'
    if len(script_src) > 0:
        csp_recommendation += f'- script-src {script_src};\r\n'
    if len(form_action) > 0:
        csp_recommendation += f'- form-action {form_action};\r\n'
    if len(style_src) > 0:
        csp_recommendation += f'- style-src {style_src};\r\n'
    if len(child_src) > 0:
        csp_recommendation += f'- child-src {child_src};\r\n'

    if len(object_src) > 0:
        csp_recommendation += f'- object-src {object_src};\r\n'
    if len(frame_ancestors) > 0:
        csp_recommendation += f'- frame-ancestors {frame_ancestors};\r\n'
    if len(connect_src) > 0:
        csp_recommendation += f'- connect-src {connect_src};\r\n'
    if len(font_src) > 0:
        csp_recommendation += f'- font-src {font_src};\r\n'

    return csp_recommendation

def rate_csp(result_dict, global_translation, local_translation,
             org_domain, org_www_domain, domain, create_recommendation):
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

        # default-src|script-src|style-src|font-src|connect-src|
        # frame-src|img-src|media-src|frame-ancestors|base-uri|
        # form-action|block-all-mixed-content|child-src|connect-src|
        # fenced-frame-src|font-src|img-src|manifest-src|media-src|
        # object-src|plugin-types|prefetch-src|referrer|report-to|
        # report-uri|require-trusted-types-for|sandbox|script-src-attr|
        # script-src-elem|strict-dynamic|style-src-attr|style-src-elem|
        # trusted-types|unsafe-hashes|upgrade-insecure-requests|worker-src
        supported_src_policies = [
            'default-src','script-src','style-src','font-src',
            'connect-src','frame-src','img-src','media-src',
            'frame-ancestors','base-uri','form-action','child-src',
            'manifest-src','object-src','script-src-attr',
            'script-src-elem','style-src-attr','style-src-elem','worker-src']
        self_allowed_policies = [
            'font-src','connect-src','frame-src','img-src','media-src',
            'frame-ancestors','base-uri','form-action','child-src','manifest-src']
        other_supported_polices = ['report-to','sandbox','upgrade-insecure-requests']
        fallback_src_policies = [
            'base-uri', 'object-src', 'frame-ancestors',
            'form-action', 'default-src']
        experimental_policies = [
            'fenced-frame-src',
            'require-trusted-types-for',
            'inline-speculation-rules',
            'trusted-types']
        # Deprecated policies (According to https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
        deprecated_policies = [
            'block-all-mixed-content',
            'plugin-types',
            'prefetch-src',
            'referrer',
            'report-uri']
        is_using_deprecated_policy = False
        for policy_name in deprecated_policies:
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
                if policy_name in self_allowed_policies:
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
            elif policy_name not in self_allowed_policies:
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(1.0)
                sub_rating.set_standards(5.0,
                    local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                        policy_name, "none/sha[256/384/512]", domain))
                sub_rating.set_integrity_and_security(1.0,
                        local_translation('TEXT_REVIEW_CSP_POLICY_IS_NOT_USING').format(
                            policy_name, "none/sha[256/384/512]", domain))
                rating += sub_rating


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

            if "'self'" in policy_object['all']:
                if policy_name in self_allowed_policies:
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


            nof_subdomains = len(policy_object['subdomains'])
            if nof_subdomains > 0:
                if policy_name in self_allowed_policies:
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

            nof_malformed = len(policy_object['malformed'])
            if nof_malformed > 0:
                sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
                sub_rating.set_overall(1.0)
                sub_rating.set_standards(1.0,
                    local_translation('TEXT_REVIEW_CSP_MALFORMED').format(
                        policy_name, domain))
                rating += sub_rating

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

        for policy_name in fallback_src_policies:
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

    elif 'HTML-FOUND' in result_dict[domain]['features'] and\
            (domain in (org_domain, org_www_domain)):
        rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        rating.set_overall(1.0)
        rating.set_standards(1.0,
            local_translation('TEXT_REVIEW_CSP_NOT_FOUND').format(domain))
        rating.set_integrity_and_security(1.0,
            local_translation('TEXT_REVIEW_CSP_NOT_FOUND').format(domain))

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

            csp_recommendation_result = handle_csp_data(
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
            score = csp_recommendation_rating.get_integrity_and_security()
            if score > final_rating.get_integrity_and_security():
                final_rating.overall_review = text_recommendation + final_rating.overall_review

    return final_rating


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

def create_sha256_hash(data):
    sha_signature = hashlib.sha256(data).digest()
    base64_encoded_sha_signature = base64.b64encode(sha_signature).decode()
    return base64_encoded_sha_signature

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
    wildcard_org_domain = f'webperf-core-wildcard.{org_domain}'
    subdomain_org_domain = f'.{org_domain}'

    for policy_name, items in result_dict[domain]['csp-policies'].items():
        policy_object = default_csp_policy_object()
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

        if policy_name not in result_dict[domain]['csp-policies']:
            result_dict[domain]['csp-policies'][policy_name] = []

        if not is_from_response_header and\
                policy_name in ('frame-ancestors', 'report-uri', 'sandbox'):
            result_dict[domain]['features'].append('CSP-UNSUPPORTED-IN-META')
            result_dict[domain]['features'].append(f'CSP-UNSUPPORTED-IN-META-{tmp_name}')

        values = value.split(' ')

        result_dict[domain]['csp-policies'][policy_name].extend(values)
        result_dict[domain]['csp-policies'][policy_name] = sorted(list(set(
            result_dict[domain]['csp-policies'][policy_name])))

def append_csp_policy(policy_name, items, domain, result_dict):
    if policy_name not in result_dict[domain]['csp-policies']:
        result_dict[domain]['csp-policies'][policy_name] = []

    if len(items) == 0:
        return

    if len(result_dict[domain]['csp-policies'][policy_name]) == 0:
        result_dict[domain]['csp-policies'][policy_name].extend(items)
