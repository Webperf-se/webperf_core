# -*- coding: utf-8 -*-
"""
Offline unit tests for the Zonemaster DNS test (test 32).

These mock the Zonemaster output so no Docker/network access is needed. Run
from the repository root:

    python -m unittest unittests.test_zonemaster_dns
"""
import os
import sys
import unittest

# Make the repository root importable when run as `python -m unittest ...`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gettext  # noqa: E402  pylint: disable=wrong-import-position
from tests import zonemaster_dns  # noqa: E402  pylint: disable=wrong-import-position


def _rec(tag, testcase, level, message="msg"):
    """Build one raw Zonemaster JSON record."""
    return {"tag": tag, "testcase": testcase, "level": level, "message": message}


class ModuleAndDomainTests(unittest.TestCase):
    def test_module_from_testcase(self):
        self.assertEqual(zonemaster_dns.module_from_testcase("Basic01"), "Basic")
        self.assertEqual(zonemaster_dns.module_from_testcase("DNSSEC10"), "DNSSEC")
        self.assertEqual(zonemaster_dns.module_from_testcase("Connectivity04"), "Connectivity")
        self.assertEqual(zonemaster_dns.module_from_testcase("Unspecified"), "Unspecified")

    def test_domain_registrable_vs_hostname(self):
        self.assertEqual(
            zonemaster_dns.domain_from_url("https://www.example.com/a?b=c", True),
            "example.com")
        self.assertEqual(
            zonemaster_dns.domain_from_url("https://www.example.com/a", False),
            "www.example.com")
        self.assertEqual(zonemaster_dns.domain_from_url("", True), "")


class ParseTests(unittest.TestCase):
    def test_parse_results_wrapper(self):
        self.assertEqual(zonemaster_dns._parse_json_output('{"results": [{"a": 1}]}'),
                         [{"a": 1}])

    def test_parse_plain_array(self):
        self.assertEqual(zonemaster_dns._parse_json_output('[{"a": 1}]'), [{"a": 1}])

    def test_parse_with_leading_noise(self):
        self.assertEqual(zonemaster_dns._parse_json_output('spinner...\n[{"a": 1}]'),
                         [{"a": 1}])


class ScoreTests(unittest.TestCase):
    def test_clean_zone_is_five(self):
        entries = zonemaster_dns.normalize_entries([
            _rec("B01_CHILD_FOUND", "Basic01", "INFO"),
            _rec("ARE_AUTHORITATIVE", "Delegation01", "INFO"),
        ])
        self.assertEqual(zonemaster_dns.score(entries)["rating"], 5.0)

    def test_critical_is_one(self):
        entries = zonemaster_dns.normalize_entries([
            _rec("B02_NO_DELEGATION", "Basic02", "CRITICAL"),
            _rec("B01_CHILD_FOUND", "Basic01", "INFO"),
        ])
        self.assertEqual(zonemaster_dns.score(entries)["rating"], 1.0)

    def test_notice_does_not_lower_rating(self):
        entries = zonemaster_dns.normalize_entries(
            [_rec("SOME_NOTICE", f"Zone{i:02d}", "NOTICE") for i in range(1, 6)])
        self.assertEqual(zonemaster_dns.score(entries)["rating"], 5.0)

    def test_severity_override_downgrades_warning(self):
        # MX_NUMERIC_TLD defaults to WARNING but is re-weighted to NOTICE, so a
        # zone that only trips it must not lose any points.
        entries = zonemaster_dns.normalize_entries(
            [_rec("MX_NUMERIC_TLD", "Syntax07", "WARNING")]
            + [_rec("OK", f"Basic{i:02d}", "INFO") for i in range(1, 10)])
        scored = zonemaster_dns.score(entries)
        self.assertEqual(scored["n_warning"], 0)
        self.assertEqual(scored["n_notice"], 1)
        self.assertEqual(scored["rating"], 5.0)

    def test_absolute_deduction_per_warning(self):
        # Each warning removes a flat per-warning cost (checked explicitly so the
        # test is independent of the shipped default).
        entries = zonemaster_dns.normalize_entries(
            [_rec("IPV4_ONE_ASN", "Connectivity03", "WARNING")]
            + [_rec("OK", f"Basic{i:02d}", "INFO") for i in range(1, 20)])
        self.assertEqual(zonemaster_dns.score(entries, warning_penalty=0.5)["rating"], 4.5)

        four = zonemaster_dns.normalize_entries(
            [_rec("IPV4_ONE_ASN", f"Connectivity{i:02d}", "WARNING") for i in range(1, 5)]
            + [_rec("OK", f"Basic{i:02d}", "INFO") for i in range(1, 20)])
        self.assertEqual(zonemaster_dns.score(four, warning_penalty=0.5)["rating"], 3.0)

    def test_error_costs_twice_a_warning(self):
        one_error = zonemaster_dns.normalize_entries(
            [_rec("X", "Basic02", "ERROR")]
            + [_rec("OK", f"Basic{i:02d}", "INFO") for i in range(3, 13)])
        two_warnings = zonemaster_dns.normalize_entries(
            [_rec("W", "Zone02", "WARNING"), _rec("W", "Zone04", "WARNING")]
            + [_rec("OK", f"Basic{i:02d}", "INFO") for i in range(3, 13)])
        err = zonemaster_dns.score(one_error, warning_penalty=0.75, error_penalty=1.5)["rating"]
        warn = zonemaster_dns.score(two_warnings, warning_penalty=0.75)["rating"]
        self.assertEqual(err, warn)  # one error == two warnings == 3.5

    def test_security_subrating_uses_dnssec_and_consistency(self):
        entries = zonemaster_dns.normalize_entries([
            _rec("DS08_DNSKEY_RRSIG_EXPIRED", "DNSSEC08", "ERROR"),
            _rec("B01_CHILD_FOUND", "Basic01", "INFO"),
        ])
        scored = zonemaster_dns.score(entries)
        # The error is a DNSSEC (security) criterion: security drops, standards stays clean.
        self.assertLess(scored["rating_security"], 5.0)
        self.assertEqual(scored["rating_standards"], 5.0)

    def test_penalties_are_configurable(self):
        entries = zonemaster_dns.normalize_entries(
            [_rec("IPV4_ONE_ASN", "Connectivity03", "WARNING")]
            + [_rec("OK", f"Basic{i:02d}", "INFO") for i in range(1, 20)])
        self.assertEqual(zonemaster_dns.score(entries, warning_penalty=0.5)["rating"], 4.5)
        self.assertEqual(zonemaster_dns.score(entries, warning_penalty=1.0)["rating"], 4.0)


class RunTestTests(unittest.TestCase):
    def setUp(self):
        # Pin the language so the localized review text is deterministic
        # regardless of any cached/root settings.json.
        from helpers.setting_helper import set_runtime_config_only
        set_runtime_config_only('general.language', 'en')
        self.global_translation = gettext.translation(
            'webperf-core', localedir='locales', languages=['en']).gettext
        self._orig = zonemaster_dns.run_zonemaster

    def tearDown(self):
        zonemaster_dns.run_zonemaster = self._orig

    def test_run_test_maps_rating(self):
        raw = ([_rec("IPV4_ONE_ASN", "Connectivity03", "WARNING",
                      "Same AS")]
               + [_rec("OK", f"Basic{i:02d}", "INFO") for i in range(1, 20)])
        zonemaster_dns.run_zonemaster = lambda *a, **k: raw
        rating, data = zonemaster_dns.run_test(self.global_translation, "https://example.com")
        self.assertEqual(data["domain"], "example.com")
        self.assertGreater(rating.get_overall(), 4.0)
        self.assertLess(rating.get_overall(), 5.0)
        self.assertEqual(data["n_warning"], 1)

    def test_run_test_infra_failure_is_not_penalized(self):
        def _boom(*_a, **_k):
            raise RuntimeError("docker was not found in PATH")
        zonemaster_dns.run_zonemaster = _boom
        rating, data = zonemaster_dns.run_test(self.global_translation, "https://example.com")
        self.assertTrue(data.get("failed"))
        # No score set => overall stays unset (-1), so the run is not counted as a bad site.
        self.assertEqual(rating.get_overall(), -1)

    def test_run_test_broken_delegation_is_one(self):
        raw = [_rec("B02_NO_DELEGATION", "Basic02", "CRITICAL", "No delegation")]
        zonemaster_dns.run_zonemaster = lambda *a, **k: raw
        rating, _data = zonemaster_dns.run_test(self.global_translation, "https://example.com")
        self.assertEqual(rating.get_overall(), 1.0)

    def test_very_good_banner_reserved_for_flawless_five(self):
        local = gettext.translation(
            'zonemaster_dns', localedir='locales', languages=['en']).gettext
        very_good = local('TEXT_REVIEW_VERY_GOOD').strip()
        is_good = local('TEXT_REVIEW_IS_GOOD').strip()

        # One confirmed warning => below 5.0 => "good", never "very good".
        raw = ([_rec("IPV4_ONE_ASN", "Connectivity03", "WARNING", "Same AS")]
               + [_rec("OK", f"Basic{i:02d}", "INFO") for i in range(1, 20)])
        zonemaster_dns.run_zonemaster = lambda *a, **k: raw
        rating, _ = zonemaster_dns.run_test(self.global_translation, "https://x.example")
        self.assertLess(rating.get_overall(), 5.0)
        self.assertIn(is_good, rating.overall_review)
        self.assertNotIn(very_good, rating.overall_review)

    def test_deduction_is_denominator_independent(self):
        # One warning costs 0.5 whether it sits among 10 criteria or 40.
        small = zonemaster_dns.normalize_entries(
            [_rec("IPV4_ONE_ASN", "Connectivity03", "WARNING")]
            + [_rec("OK", f"Basic{i:02d}", "INFO") for i in range(1, 10)])
        large = zonemaster_dns.normalize_entries(
            [_rec("IPV4_ONE_ASN", "Connectivity03", "WARNING")]
            + [_rec("OK", f"Basic{i:02d}", "INFO") for i in range(1, 40)])
        self.assertEqual(zonemaster_dns.score(small, warning_penalty=0.5)["rating"], 4.5)
        self.assertEqual(zonemaster_dns.score(large, warning_penalty=0.5)["rating"], 4.5)


if __name__ == "__main__":
    unittest.main()
