# -*- coding: utf-8 -*-
"""
Offline unit tests for Sitespeed scoring and for the rating text.

No network or Docker access is needed. Run from the repository root:

    python -m unittest unittests.test_sitespeed_points
"""
# pylint: disable=missing-function-docstring
import os
import sys
import unittest

# Make the repository root importable when run as `python -m unittest ...`.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from helpers.models import Rating  # noqa: E402  pylint: disable=wrong-import-position
from tests.performance_sitespeed_io import (  # noqa: E402  pylint: disable=wrong-import-position
    LINEAR_SCORED_METRICS, get_data_for_entry, get_points)


def _translation(text):
    """Translation stub, formats the rating item like the Swedish text."""
    if text == 'TEXT_TEST_REVIEW_RATING_ITEM':
        return '{0} ( {1:.2f} betyg )\r\n'
    return text


class RatingTextTests(unittest.TestCase):
    """The review text must show the clamped value that is stored."""

    def test_performance_below_range_is_clamped_in_text(self):
        rating = Rating(_translation)
        rating.set_performance(-180.51, 'Load')
        self.assertEqual(rating.performance, 1.0)
        self.assertIn('( 1.00 betyg )', rating.performance_review)
        self.assertNotIn('-180', rating.performance_review)

    def test_overall_above_range_is_clamped_in_text(self):
        rating = Rating(_translation)
        rating.set_overall(7.3, 'x')
        self.assertIn('( 5.00 betyg )', rating.overall_review)


class SitespeedPointsTests(unittest.TestCase):
    """Metric keys are matched exactly and medians are real medians."""

    def test_no_substring_matching(self):
        self.assertEqual(get_points('desktop', 'pageLoadTime', 90000, 90000), -1)

    def test_dom_content_loaded_is_still_scored(self):
        self.assertIn('DOMContentLoaded', LINEAR_SCORED_METRICS)
        self.assertEqual(get_points('desktop', 'DOMContentLoaded', 400, 400), 5.0)

    def test_single_value_is_scored(self):
        entry = get_data_for_entry('mobile', 'LCP', ['9000ms'])
        self.assertEqual(entry['median'], 9000)
        self.assertEqual(entry['points'], 1.0)

    def test_outlier_does_not_move_median(self):
        entry = get_data_for_entry(
            'desktop', 'SpeedIndex', ['400ms', '420ms', '36000ms'])
        self.assertEqual(entry['median'], 420)
        self.assertEqual(entry['points'], 5.0)

    def test_seconds_are_converted(self):
        entry = get_data_for_entry('desktop', 'LCP', ['1.2s', '1.4s', '1.3s'])
        self.assertAlmostEqual(entry['median'], 1300)


if __name__ == '__main__':
    unittest.main()
