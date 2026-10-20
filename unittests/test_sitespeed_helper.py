# -*- coding: utf-8 -*-
"""
Offline unit tests for get_first_page_entries.

No network or Docker access is needed. Run from the repository root:

    python -m unittest unittests.test_sitespeed_helper
"""
# pylint: disable=missing-function-docstring,missing-class-docstring
import os
import sys
import unittest

# Make the repository root importable when run as `python -m unittest ...`.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from helpers.sitespeed_helper import get_first_page_entries  # noqa: E402  pylint: disable=wrong-import-position


def _entry(url, **extra):
    entry = {'pageref': 'page_1', 'request': {'url': url}, 'response': {'status': 200}}
    entry.update(extra)
    return entry


def _navigation(url, **extra):
    return _entry(url, _resourceType='document', _initiator_type='other', **extra)


def _iframe(url):
    return _entry(url, _resourceType='document', _initiator_type='parser')


def _har(entries):
    return {'log': {'pages': [{'id': 'page_1'}], 'entries': entries}}


def _urls(entries):
    return [e['request']['url'] for e in entries]


class FirstPageEntriesTest(unittest.TestCase):
    def test_drops_requests_after_crossed_in_navigation(self):
        har = _har([
            _navigation('https://www.mucf.se/'),
            _entry('https://www.mucf.se/style.css'),
            _navigation('https://gambiagrupperna.org/'),
            _entry('https://gambiagrupperna.org/style.css'),
            _entry('https://cdnjs.cloudflare.com/owl.css')])
        result = get_first_page_entries(har, 'www.mucf.se')
        self.assertEqual(_urls(result),
                         ['https://www.mucf.se/', 'https://www.mucf.se/style.css'])

    def test_keeps_site_after_redirect_to_other_host(self):
        har = _har([
            _navigation('https://mucf.se/', response={
                'status': 301, 'redirectURL': 'https://www.mucf.se/'}),
            _navigation('https://www.mucf.se/'),
            _entry('https://www.mucf.se/style.css')])
        self.assertEqual(len(get_first_page_entries(har, 'mucf.se')), 3)

    def test_keeps_third_party_iframes_and_subresources(self):
        har = _har([
            _navigation('https://www.mucf.se/'),
            _iframe('https://www.google.com/recaptcha/anchor'),
            _entry('https://www.gstatic.com/recaptcha/styles.css')])
        self.assertEqual(len(get_first_page_entries(har, 'www.mucf.se')), 3)

    def test_existing_guards_still_apply(self):
        mixed = _har([
            _navigation('https://www.mucf.se/'),
            _entry('https://gambiagrupperna.org/a.css', pageref='page_2')])
        self.assertEqual(len(get_first_page_entries(mixed, 'www.mucf.se')), 1)
        wrong_start = _har([_navigation('https://gambiagrupperna.org/')])
        self.assertIsNone(get_first_page_entries(wrong_start, 'www.mucf.se'))

    def test_without_initiator_information_nothing_is_dropped(self):
        har = _har([_entry('https://www.mucf.se/'),
                    _entry('https://gambiagrupperna.org/x.css')])
        self.assertEqual(len(get_first_page_entries(har, 'www.mucf.se')), 2)

    def test_without_origin_domain_nothing_is_cut(self):
        har = _har([_navigation('https://www.mucf.se/'),
                    _navigation('https://gambiagrupperna.org/')])
        self.assertEqual(len(get_first_page_entries(har)), 2)


if __name__ == '__main__':
    unittest.main()
