# -*- coding: utf-8 -*-
# https://docs.python.org/3/library/urllib.parse.html
from helpers.data_helper import has_domain_entry
from helpers.setting_helper import get_config
from helpers.models import Rating

def rate_transfer_layers(result_dict, global_translation, local_translation, domain):
    """
    Rates the transport layers of a given domain based on its TLS version support.

    Args:
        result_dict (dict): The result dictionary where each key is a domain name and
                            the value is another dictionary with details about the domain.
        global_translation (function): A function to translate text to a global language.
        local_translation (function): A function to translate text to a local language.
        domain (str): The domain to rate.

    Returns:
        Rating: A Rating object that represents the rating of the domain's transport layers.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    if not isinstance(result_dict[domain], dict):
        return rating

    if has_domain_entry(domain, 'transport-layers', 'TLSv1.3', result_dict):
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                                local_translation('TEXT_REVIEW_TLS1_3_SUPPORT').format(domain))
        sub_rating.set_integrity_and_security(5.0,
                                local_translation('TEXT_REVIEW_TLS1_3_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
                                local_translation('TEXT_REVIEW_TLS1_3_NO_SUPPORT').format(domain))
        sub_rating.set_integrity_and_security(1.0,
                                local_translation('TEXT_REVIEW_TLS1_3_NO_SUPPORT').format(domain))
        rating += sub_rating

    if has_domain_entry(domain, 'transport-layers', 'TLSv1.2', result_dict):
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                                local_translation('TEXT_REVIEW_TLS1_2_SUPPORT').format(domain))
        sub_rating.set_integrity_and_security(5.0,
                                local_translation('TEXT_REVIEW_TLS1_2_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
                                local_translation('TEXT_REVIEW_TLS1_2_NO_SUPPORT').format(domain))
        sub_rating.set_integrity_and_security(1.0,
                                local_translation('TEXT_REVIEW_TLS1_2_NO_SUPPORT').format(domain))
        rating += sub_rating

    if has_domain_entry(domain, 'transport-layers', 'TLSv1.1', result_dict):
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                                local_translation('TEXT_REVIEW_TLS1_1_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0,
                                local_translation('TEXT_REVIEW_TLS1_1_NO_SUPPORT').format(domain))
        rating += sub_rating

    if has_domain_entry(domain, 'transport-layers', 'TLSv1.0', result_dict):
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                                local_translation('TEXT_REVIEW_TLS1_0_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0,
                                local_translation('TEXT_REVIEW_TLS1_0_NO_SUPPORT').format(domain))
        rating += sub_rating
    return rating
