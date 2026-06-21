# -*- coding: utf-8 -*-
"""
Standard files test (robots.txt, sitemap.xml, RSS/Atom feed, security.txt).

The actual checks now live in the sitespeed.io plugin ``plugin-standard-files``
(https://github.com/Webperf-se/plugin-standard-files), a real-browser port of
the previous ``requests``-based implementation. Using a real browser resolves
the certificate / bot-detection problems that made the old Python version fail
on sites with e.g. self-signed or otherwise unverifiable certificates.

In normal runs ``helpers.test_helper`` routes test id 9 through the shared
sitespeed pass via ``TEST_USE_SITESPEED`` (alongside ``plugin-webperf-core``,
which aggregates the result into ``webperf-core.json``) and this module is not
called.

This thin shim keeps test id 9 working as a standalone, ``requests``-free
fallback: it runs sitespeed with the plugin and reads the ``standard-files``
issues out of the resulting ``webperf-core.json``. The rule ids, severities and
categories are owned by the plugin and kept identical to the old Python test so
that scores stay continuous.
"""
from helpers.models import Rating
from helpers.setting_helper import get_config
from tests.utils import get_domain, calculate_rating
from tests.sitespeed_base import create_webperf_json

TEST_NAME = 'standard-files'


def run_test(global_translation, url):
    """
    Run the standard files test for ``url`` via the sitespeed.io plugin.

    Parameters:
    global_translation (function): Function to translate text to a global language.
    url (str): The URL to test.

    Returns:
    tuple: ``(rating, result_dict)`` where ``rating`` is a ``Rating`` and
        ``result_dict`` holds the per-domain ``standard-files`` issues. On a
        failure to reach the site ``({rating}, {'failed': True})`` is returned.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))

    sitespeed_plugins = (
        '--plugins.add plugin-standard-files '
        '--plugins.add plugin-webperf-core ')
    data = create_webperf_json(url, sitespeed_plugins)

    result_dict = build_result_dict(url, data)
    if result_dict is None:
        error_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        error_rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (error_rating, {'failed': True})

    rating = calculate_rating(global_translation, rating, result_dict)
    return (rating, result_dict)


def build_result_dict(url, data):
    """
    Extract the ``standard-files`` issues from a ``webperf-core.json`` payload.

    Parameters:
    url (str): The tested URL.
    data (dict): The parsed ``webperf-core.json`` produced by the sitespeed run.

    Returns:
    dict | None: A ``{'url', 'groups': {domain: {'issues': [...]}}}`` dict, or
        ``None`` when the site could not be reached / produced no result.
    """
    if not isinstance(data, dict) or 'groups' not in data:
        return None

    domain = get_domain(url)
    issues = []
    for group_info in data['groups'].values():
        if not isinstance(group_info, dict):
            continue
        for issue in group_info.get('issues', []):
            if issue.get('test') == TEST_NAME:
                issues.append(issue)

    if len(issues) == 0:
        return None

    # An unresolved no-network result means the plugin could not read the page
    # (mirrors the old "site unavailable" behaviour).
    for issue in issues:
        if issue.get('rule') == 'no-network' and issue.get('severity') != 'resolved':
            return None

    return {
        'url': url,
        'groups': {
            domain: {
                'issues': issues
            }
        }
    }
