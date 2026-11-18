# -*- coding: utf-8 -*-
"""
Offline unit tests for how the HTTP test (21) stops when a browser it
depends on can't load the website (Webperf-se/webperf_core#1700).

No network, browsers or Docker are needed. Run from the repository root:

    python -m unittest unittests.test_http_browser_check
"""
import os
import sys
import unittest
from unittest import mock

# Make the repository root importable when run as `python -m unittest ...`.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tests import http_validator  # noqa: E402  pylint: disable=wrong-import-position

LOADED = {'visits': 1, 'example.com': {'schemes': ['HTTPS']}}
NOT_LOADED = {'failed': True}


def _global_translation(text):
    """Translation stub, returns the key unchanged."""
    return text


def _local_translation(text):
    """Translation stub that shows the placeholders, to check their order."""
    if text == 'TEXT_BROWSER_UNAVAILABLE':
        return '{0}|{1}|{2}'
    return text


def _config(name):
    """Settings stub with the defaults that matter for these tests."""
    if name == 'tests.sitespeed.timeout':
        return 60
    return None


class TestGetUnavailableBrowser(unittest.TestCase):
    """Which browser is reported as unable to run."""

    def test_both_loaded(self):
        self.assertIsNone(http_validator.get_unavailable_browser(True, True))

    def test_only_firefox_failed(self):
        self.assertEqual(http_validator.get_unavailable_browser(True, False), 'firefox')

    def test_only_chromium_failed(self):
        self.assertEqual(http_validator.get_unavailable_browser(False, True), 'chromium')

    def test_both_failed(self):
        self.assertEqual(http_validator.get_unavailable_browser(False, False), 'both')


@mock.patch.object(http_validator, 'get_config', side_effect=_config)
@mock.patch.object(http_validator, 'get_chromium_browser', return_value='chrome')
class TestCheckBrowsersCanLoad(unittest.TestCase):
    """The Firefox baseline run and the rating it returns."""

    def _check(self, chromium_result, firefox_result):
        with mock.patch.object(
                http_validator, 'get_website_support_from_sitespeed',
                return_value=firefox_result) as sitespeed:
            rating = http_validator.check_browsers_can_load(
                'https://example.com/', chromium_result,
                _global_translation, _local_translation)
        return rating, sitespeed

    def test_baseline_uses_same_url_as_chrome_run_without_restrictions(self, *_):
        _, sitespeed = self._check(LOADED, LOADED)
        args = sitespeed.call_args.args
        self.assertEqual(args[0], 'http://example.com/')
        self.assertEqual(args[2], '')
        self.assertEqual(args[3], 'firefox')

    def test_both_loaded_continues(self, *_):
        rating, _ = self._check(LOADED, LOADED)
        self.assertIsNone(rating)

    def test_firefox_failed_names_firefox_and_geckodriver(self, *_):
        rating, _ = self._check(LOADED, NOT_LOADED)
        self.assertEqual(rating.overall_review, 'Firefox|Chrome|Geckodriver')
        self.assertEqual(rating.get_overall(), -1)

    def test_chrome_failed_names_chrome_and_chromedriver(self, *_):
        rating, _ = self._check(NOT_LOADED, LOADED)
        self.assertEqual(rating.overall_review, 'Chrome|Firefox|Chromedriver')
        self.assertEqual(rating.get_overall(), -1)

    def test_edge_failed_names_edgedriver(self, chromium_browser, _):
        chromium_browser.return_value = 'edge'
        rating, _ = self._check(NOT_LOADED, LOADED)
        self.assertEqual(rating.overall_review, 'Edge|Firefox|Edgedriver')

    def test_both_failed_reports_site_unavailable(self, *_):
        rating, _ = self._check(NOT_LOADED, NOT_LOADED)
        self.assertEqual(rating.overall_review, 'TEXT_SITE_UNAVAILABLE')
        self.assertEqual(rating.get_overall(), -1)


@mock.patch.object(http_validator, 'get_config', side_effect=_config)
@mock.patch.object(http_validator, 'get_chromium_browser', return_value='chrome')
@mock.patch.object(http_validator, 'get_translation', return_value=_local_translation)
class TestRunTestStopsWithoutFirefox(unittest.TestCase):
    """run_test() must not produce findings when Firefox can't run."""

    def test_stops_before_tls_and_http_version_checks(self, *_):
        with mock.patch.object(http_validator, 'check_http_to_https',
                               return_value=dict(LOADED)), \
             mock.patch.object(http_validator, 'get_website_support_from_sitespeed',
                               return_value=NOT_LOADED), \
             mock.patch.object(http_validator, 'check_tls_versions') as tls, \
             mock.patch.object(http_validator, 'check_http_version') as http_version:
            rating, result_dict = http_validator.run_test(
                _global_translation, 'https://www.example.com/')

        tls.assert_not_called()
        http_version.assert_not_called()
        self.assertEqual(rating.get_overall(), -1)
        self.assertEqual(rating.overall_review, 'Firefox|Chrome|Geckodriver')
        self.assertEqual(result_dict.get('visits'), 0)


if __name__ == '__main__':
    unittest.main()
