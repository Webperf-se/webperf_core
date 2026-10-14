# -*- coding: utf-8 -*-
"""
Offline unit tests for how ratings are calculated and combined.

No network or Docker access is needed. Run from the repository root:

    python -m unittest unittests.test_rating
"""
import os
import re
import sys
import unittest
from datetime import datetime
from unittest import mock

# Make the repository root importable when run as `python -m unittest ...`.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from helpers import test_helper  # noqa: E402  pylint: disable=wrong-import-position
from helpers.models import Rating, SiteTests  # noqa: E402  pylint: disable=wrong-import-position
from tests import utils  # noqa: E402  pylint: disable=wrong-import-position

SCORE_JS = os.path.join(
    REPO_ROOT, 'node_modules', 'plugin-webperf-core', 'lib', 'score.js')


def _translation(text):
    """Translation stub, returns the key unchanged."""
    return text


def _issue(rule, category='a11y', severity='critical'):
    """Build one issue in the shape pa11y and the plugins produce."""
    return {
        "test": "pa11y",
        "text": f"{rule} ({severity})",
        "rule": rule,
        "category": category,
        "severity": severity,
        "subIssues": []
    }


def _group(issues, with_score=True):
    """Build one group, with the score stored as the plugins do."""
    group = {"issues": issues, "pages": {}}
    if with_score:
        group["score"] = utils.calculate_score(issues)
    return group


def _entry(type_of_test, rating, data):
    """Build a result entry as test() and test_with_sitespeed() return it."""
    return SiteTests(site_id=0, type_of_test=type_of_test, rating=rating,
                     test_date=datetime.now(), json_check_data=data).todata()[0]


def _groups_result(type_of_test, groups):
    """(Rating, entry) for an issue based test with the given groups."""
    data = {"groups": groups}
    rating = utils.calculate_rating(_translation, Rating(_translation), data)
    return (rating, _entry(type_of_test, rating, data))


def _plain_result(type_of_test, overall, security):
    """(Rating, entry) for a test with its own rating logic, like DNS."""
    rating = Rating(_translation)
    rating.set_overall(overall)
    rating.set_integrity_and_security(security)
    return (rating, _entry(type_of_test, rating, {"dns": {"checked": True}}))


class ScoreTests(unittest.TestCase):
    def test_severity_deductions(self):
        issues = [_issue("a", "a11y", "critical"), _issue("b", "a11y", "error"),
                  _issue("c", "standard", "warning")]
        score = utils.calculate_score(issues)
        self.assertEqual(score["a11y"], 65)
        self.assertEqual(score["standard"], 99)
        self.assertEqual(score["overall"], 82)

    def test_showstopper_zeroes_its_category_only(self):
        issues = [_issue("no-a11y-statement", "a11y", "critical"),
                  _issue("b", "a11y", "warning"),
                  _issue("c", "standard", "warning")]
        score = utils.calculate_score(issues)
        self.assertEqual(score["a11y"], 0)
        self.assertEqual(score["standard"], 99)
        self.assertEqual(score["overall"], 49.5)

    def test_resolved_showstopper_does_not_zero(self):
        issues = [_issue("no-a11y-statement", "a11y", "resolved")]
        self.assertEqual(utils.calculate_score(issues)["a11y"], 100)

    @unittest.skipUnless(os.path.exists(SCORE_JS), "plugin-webperf-core is not installed")
    def test_showstopper_rules_match_plugin_webperf_core(self):
        with open(SCORE_JS, encoding='utf-8') as score_js:
            source = score_js.read()
        match = re.search(r"showstopperRules\s*=\s*new Set\(\[(.*?)\]\)", source, re.DOTALL)
        self.assertIsNotNone(match, "showstopperRules not found in score.js")
        js_rules = set(re.findall(r"'([^']+)'", match.group(1)))
        self.assertEqual(js_rules, set(utils.SHOWSTOPPER_RULES))


class GroupTests(unittest.TestCase):
    """A run with more than one group must not let the last group win."""

    def _rating_for(self, group_names):
        groups = {
            "uni.de": _group([_issue("a"), _issue("b"), _issue("c")], False),  # a11y 25
            "www.uni.de": _group([_issue("w", severity="warning")], False),    # a11y 99
        }
        ordered = {name: groups[name] for name in group_names}
        return utils.calculate_rating(_translation, Rating(_translation), {"groups": ordered})

    def test_groups_are_averaged_regardless_of_order(self):
        first = self._rating_for(["uni.de", "www.uni.de"])
        second = self._rating_for(["www.uni.de", "uni.de"])
        expected = (1.25 + 4.95) / 2
        self.assertAlmostEqual(first.get_a11y(), expected, places=2)
        self.assertAlmostEqual(second.get_a11y(), expected, places=2)
        self.assertAlmostEqual(first.get_overall(), expected, places=2)

    def test_review_contains_every_group(self):
        rating = self._rating_for(["uni.de", "www.uni.de"])
        self.assertEqual(rating.a11y_review.count("\n- "), 3)
        self.assertEqual(rating.a11y_review.count("- "), 4)

    def test_score_is_calculated_when_missing(self):
        data = {"groups": {"uni.de": _group([_issue("a")], False)}}
        utils.calculate_rating(_translation, Rating(_translation), data)
        self.assertEqual(data["groups"]["uni.de"]["score"]["a11y"], 75)


class CombineTests(unittest.TestCase):
    """Combining the results of several tests on one site."""

    def test_score_is_recalculated_from_all_issues(self):
        # sitespeed (lighthouse) already stored an a11y score of 90,
        # pa11y adds three critical a11y issues for the same domain.
        sitespeed = _groups_result(30, {
            "uni.de": _group([_issue("lh", severity="error")])})
        pa11y = _groups_result(18, {
            "uni.de": _group([_issue("a"), _issue("b"), _issue("c")])})
        self.assertEqual(sitespeed[0].get_a11y(), 4.5)

        rating, big_data = test_helper.combine_test_results(
            _translation, [sitespeed, pa11y])

        self.assertEqual(big_data["groups"]["uni.de"]["score"]["a11y"], 15)
        self.assertEqual(len(big_data["groups"]["uni.de"]["issues"]), 4)
        self.assertEqual(rating.get_a11y(), 1.0)  # 0.75 clamped to the 1-5 scale

    def test_individual_entries_are_not_modified_by_the_merge(self):
        sitespeed = _groups_result(30, {
            "uni.de": _group([_issue("lh", severity="error")])})
        pa11y = _groups_result(18, {
            "uni.de": _group([_issue("a")])})
        test_helper.combine_test_results(_translation, [sitespeed, pa11y])
        group = sitespeed[1]["data"]["groups"]["uni.de"]
        self.assertEqual(group["score"]["a11y"], 90)
        self.assertEqual(len(group["issues"]), 1)

    def test_ratings_of_tests_without_groups_are_kept(self):
        sitespeed = _groups_result(28, {
            "uni.de": _group([_issue("h", "standard", "warning")])})  # 4.95
        dns = _plain_result(32, overall=3.0, security=3.0)

        rating, big_data = test_helper.combine_test_results(
            _translation, [sitespeed, dns])

        self.assertEqual(rating.get_integrity_and_security(), 3.0)
        self.assertAlmostEqual(rating.get_standards(), 4.95, places=2)
        self.assertAlmostEqual(rating.get_overall(), (4.95 + 3.0) / 2, places=2)
        self.assertIn("dns", big_data)
        self.assertIn("groups", big_data)


class TestSiteTests(unittest.TestCase):
    """test_site() keeps every test's entry and adds one for the whole run."""

    def test_single_test_returns_its_own_entry(self):
        dns = _plain_result(32, overall=3.0, security=3.0)
        with mock.patch.object(test_helper, 'test', return_value=[dns]):
            tests = test_helper.test_site(_translation, (0, "https://uni.de"), [32])
        self.assertEqual([entry["type_of_test"] for entry in tests], [32])
        self.assertEqual(tests[0]["rating_sec"], 3.0)

    def test_combined_run_adds_a_combined_entry(self):
        sitespeed = _groups_result(28, {
            "uni.de": _group([_issue("h", "standard", "warning")])})
        dns = _plain_result(32, overall=3.0, security=3.0)
        with mock.patch.object(test_helper, 'test_with_sitespeed', return_value=[sitespeed]), \
             mock.patch.object(test_helper, 'test', return_value=[dns]):
            tests = test_helper.test_site(_translation, (0, "https://uni.de"), [28, 32])

        self.assertEqual([entry["type_of_test"] for entry in tests], [28, 32, -1])
        self.assertEqual(tests[0]["rating_sec"], -1)
        self.assertEqual(tests[1]["rating_sec"], 3.0)
        combined = tests[2]
        self.assertEqual(combined["rating_sec"], 3.0)
        self.assertAlmostEqual(combined["rating_stand"], 4.95, places=2)
        self.assertAlmostEqual(combined["rating"], (4.95 + 3.0) / 2, places=2)
        self.assertIn("groups", combined["data"])
        self.assertIn("dns", combined["data"])


if __name__ == '__main__':
    unittest.main()
