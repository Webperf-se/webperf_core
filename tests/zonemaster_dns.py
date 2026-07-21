#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zonemaster DNS test for webperf_core (test 32).

Runs Zonemaster (via the Docker image `zonemaster/cli`) against the domain in a
URL, parses the JSON output and translates it into a 1.0-5.0 rating using a
quota based model with a floor:

    - The rating is set per *test case* (criterion) but reported per *module*.
    - A CRITICAL => 1.0 (broken delegation).
    - penalty = (ERROR_WEIGHT*errors + WARNING_WEIGHT*warnings) / criteria_that_ran
      rating  = 5 - 4 * min(1, penalty / THRESHOLD)
    - Calibration: THRESHOLD=0.5 => "half of the criteria warn" hits the floor 1.0.
      min()/max() give the ceiling/floor for free (no free fall).

This module is runnable stand-alone (for trial runs and calibration on a batch
of sites) AND exposes the `run_test(global_translation, url)` seam that hooks
into webperf_core, mirroring the other external-tool tests.

Requires: Docker + the image `zonemaster/cli` (pulled automatically on first
use). Pure standard-library Python; `tldextract` is used if present but is not
required.

Examples (stand-alone / calibration):
    python tests/zonemaster_dns.py https://example.com https://iis.se
    python tests/zonemaster_dns.py -f urls.txt --workers 4 --save-dir raw/
    python tests/zonemaster_dns.py --from-dir raw/ --threshold 0.4   # rescore, no DNS
"""

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# --- Calibration knobs (defaults; overridable via settings/CLI) ---------------

# Absolute per-deficiency deduction (same style as the Webbkoll test): start at
# 5.0, subtract a fixed cost per confirmed deficiency, floor at 1.0. This is
# denominator-independent (a warning always costs the same, regardless of how
# many criteria ran) which keeps results predictable, and it spreads the scale:
# a flawless zone stays 5.0 while an ordinary one with a handful of warnings
# lands around 3. NOTICE-level hygiene never affects the rating.
ERROR_PENALTY = 1.0     # points removed per confirmed error
WARNING_PENALTY = 0.5   # points removed per confirmed warning
NOTICE_PENALTY = 0.0    # notices never affect the rating

# --- Zonemaster severity ------------------------------------------------------

LEVEL_RANK = {
    "DEBUG3": 0, "DEBUG2": 0, "DEBUG": 0,
    "INFO": 1, "NOTICE": 2, "WARNING": 3, "ERROR": 4, "CRITICAL": 5,
}
RANK_NOTICE = LEVEL_RANK["NOTICE"]
RANK_WARNING = LEVEL_RANK["WARNING"]
RANK_ERROR = LEVEL_RANK["ERROR"]
RANK_CRITICAL = LEVEL_RANK["CRITICAL"]

DOCKER_IMAGE = "zonemaster/cli"
PROFILE_FILENAME = "webperf-dns.profile.json"

# Zonemaster modules whose criteria we map to the integrity & security
# sub-rating (steering the visitor to the right, consistent server). Everything
# else maps to the standards sub-rating. Derived from the test case name, e.g.
# "DNSSEC10" -> "dnssec", "Consistency06" -> "consistency".
SECURITY_MODULES = ("dnssec", "consistency")

# Visitor-impact re-weighting, applied in-code by message tag. We only lower
# severity (never remove a test case), so the criterion still counts towards the
# "X of Y" denominator but a NOTICE (weight 0) no longer lowers the rating.
#
# We reweight here rather than in a Zonemaster --profile because Zonemaster
# *replaces* the whole `test_levels` map when given a profile (it does not merge
# per tag), so a partial profile would silently suppress every unlisted tag
# (including CRITICAL delegation failures). Doing it in-code keeps every default
# severity intact, lets new Zonemaster tags flow through, and lets `--from-dir`
# recalibrate offline from raw JSON. The same weights are mirrored, as a
# complete pinned map, in defaults/webperf-dns.profile.json for callers who
# explicitly opt into engine-side weighting (tests.dns.profile.use).
#
# Tags verified against `zonemaster-cli --dump-profile` (engine v9.0.0).
SEVERITY_OVERRIDES = {
    # Address02/03 - reverse DNS for the name servers (no visitor impact).
    "NAMESERVER_IP_WITHOUT_REVERSE": "NOTICE",
    "NO_RESPONSE_PTR_QUERY": "NOTICE",
    # Zone - SOA expire timer inside/outside the RFC recommendation.
    "EXPIRE_LOWER_THAN_REFRESH": "NOTICE",
    "EXPIRE_MINIMUM_VALUE_LOWER": "NOTICE",
    # Syntax - discouraged-but-legal forms without resolver impact. Structurally
    # invalid names (leading/terminal hyphen, disallowed chars) keep their ERROR.
    "DISCOURAGED_DOUBLE_DASH": "NOTICE",
    "MNAME_DISCOURAGED_DOUBLE_DASH": "NOTICE",
    "MNAME_NON_ALLOWED_CHARS": "NOTICE",
    "MNAME_NUMERIC_TLD": "NOTICE",
    "MX_DISCOURAGED_DOUBLE_DASH": "NOTICE",
    "MX_NON_ALLOWED_CHARS": "NOTICE",
    "MX_NUMERIC_TLD": "NOTICE",
    "NAMESERVER_DISCOURAGED_DOUBLE_DASH": "NOTICE",
    "RNAME_MISUSED_AT_SIGN": "NOTICE",
    "RNAME_RFC822_INVALID": "NOTICE",
}


# --- Domain from URL ----------------------------------------------------------

def module_from_testcase(testcase):
    """Derive the Zonemaster module name from a test case name.

    The JSON output has no explicit module field; the module is the alphabetic
    prefix of the test case, e.g. "Basic01" -> "Basic", "DNSSEC10" -> "DNSSEC".
    """
    return re.sub(r'\d+$', '', testcase)


def domain_from_url(url, use_registrable_domain=True):
    """Pick the zone to test out of a URL.

    Zonemaster tests a delegation, i.e. the registrable domain. We use
    tldextract if it is available (correct public-suffix handling), otherwise we
    strip a leading 'www.'. When ``use_registrable_domain`` is False the exact
    hostname is returned instead (configurable via ``tests.dns.registrable``).
    """
    if "://" not in url:
        url = "http://" + url
    host = (urlparse(url).hostname or "").strip(".").lower()
    if not host:
        return ""
    if not use_registrable_domain:
        return host
    try:
        import tldextract  # optional dependency
        ext = tldextract.extract(host)
        if ext.domain and ext.suffix:
            return f"{ext.domain}.{ext.suffix}"
    except ImportError:
        pass
    if host.startswith("www.") and host.count(".") >= 2:
        return host[4:]
    return host


# --- Run Zonemaster -----------------------------------------------------------

def run_zonemaster(domain, image=DOCKER_IMAGE, timeout=180, use_ipv6=False,
                   locale=None, profile_path=None):
    """Run zonemaster-cli in Docker and return the list of raw records (dict).

    Raises RuntimeError on failure so the batch run can catch it per domain.
    """
    cmd = ["docker", "run", "--rm"]
    profile_name = None
    if profile_path:
        # Mount the folder containing the profile read-only and reference it inside.
        profile_dir = os.path.dirname(os.path.abspath(profile_path))
        profile_name = os.path.basename(profile_path)
        cmd += ["-v", f"{profile_dir}:/webperf-profiles:ro"]
    cmd += [image, "--json", "--level=INFO", "--show_testcase"]
    if profile_name:
        cmd += ["--profile", f"/webperf-profiles/{profile_name}"]
    if not use_ipv6:
        # Docker often lacks IPv6 => meaningless errors. Enable --ipv6 if the network supports it.
        cmd.append("--no-ipv6")
    if locale:
        cmd += ["--locale", locale]
    cmd.append(domain)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("docker was not found in PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"timeout after {timeout}s") from exc

    if proc.returncode != 0 and not proc.stdout.strip():
        raise RuntimeError((proc.stderr or "unknown error").strip().splitlines()[-1])

    return _parse_json_output(proc.stdout)


def _parse_json_output(stdout):
    """Tolerant against small format differences between versions."""
    text = stdout.strip()
    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        brace = text.find("{")
        if start == -1 or (brace != -1 and brace < start):
            start = brace
        if start != -1:
            data = json.loads(text[start:])
    if data is None:
        raise RuntimeError("could not parse JSON from zonemaster-cli")
    if isinstance(data, dict):        # some versions wrap it in {"results": [...]}
        data = data.get("results", [])
    return data


# --- Normalization ------------------------------------------------------------

def normalize_entries(raw, apply_overrides=True):
    """Extract (level, testcase, module, message) regardless of key variants.

    When ``apply_overrides`` is True the visitor-impact SEVERITY_OVERRIDES are
    applied per message tag, lowering (never raising) the severity.
    """
    out = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        low = {k.lower(): v for k, v in entry.items()}
        level = str(low.get("level", "")).upper()
        tag = str(low.get("tag", ""))
        testcase = str(low.get("testcase") or low.get("test_case") or tag or "")
        message = str(low.get("message", "")).strip()
        module = str(low.get("module", "")) or module_from_testcase(testcase)
        if apply_overrides and tag in SEVERITY_OVERRIDES:
            override = SEVERITY_OVERRIDES[tag]
            # Only lower severity, so an engine-side profile can never be undone.
            if LEVEL_RANK.get(override, 0) < LEVEL_RANK.get(level, 0):
                level = override
        out.append({"level": level, "module": module,
                    "testcase": testcase, "message": message})
    return out


# --- Rating -------------------------------------------------------------------

def _rating_from_counts(total, n_crit, n_err, n_warn, n_notice, # pylint: disable=too-many-arguments
                        error_penalty, warning_penalty, notice_penalty):
    """Turn severity counts into a 1.0-5.0 rating via absolute deduction."""
    if total == 0:
        return -1.0
    if n_crit:
        return 1.0
    deduction = (error_penalty * n_err + warning_penalty * n_warn
                 + notice_penalty * n_notice)
    return round(max(1.0, 5.0 - deduction), 2)


def score(entries, error_penalty=ERROR_PENALTY, warning_penalty=WARNING_PENALTY,
          notice_penalty=NOTICE_PENALTY):
    """Aggregate the worst level per criterion and compute rating + evidence.

    Returns the overall rating plus integrity/security and standards
    sub-ratings (computed over the module subsets), the severity counts and the
    issues grouped by module.
    """
    worst = {}   # testcase -> {"rank", "message", "module"}
    for entry in entries:
        module, testcase = entry["module"], entry["testcase"]
        if module.lower() == "system":
            continue
        if testcase.lower() in ("", "unspecified"):
            continue
        rank = LEVEL_RANK.get(entry["level"], 0)
        if testcase not in worst or rank > worst[testcase]["rank"]:
            worst[testcase] = {"rank": rank, "message": entry["message"], "module": module}

    def counts(items):
        return (
            len(items),
            sum(1 for v in items if v["rank"] == RANK_CRITICAL),
            sum(1 for v in items if v["rank"] == RANK_ERROR),
            sum(1 for v in items if v["rank"] == RANK_WARNING),
            sum(1 for v in items if v["rank"] == RANK_NOTICE),
        )

    all_items = list(worst.values())
    sec_items = [v for v in all_items if v["module"].lower() in SECURITY_MODULES]
    std_items = [v for v in all_items if v["module"].lower() not in SECURITY_MODULES]

    total, n_crit, n_err, n_warn, n_notice = counts(all_items)

    def rate(items):
        return _rating_from_counts(*counts(items),
                                   error_penalty, warning_penalty, notice_penalty)

    # Evidence per module (only criteria with a warning or worse).
    issues = {}
    for testcase, value in worst.items():
        if value["rank"] >= RANK_WARNING:
            issues.setdefault(value["module"], []).append(
                {"testcase": testcase, "rank": value["rank"], "message": value["message"]})

    return {
        "rating": rate(all_items),
        "rating_security": rate(sec_items),
        "rating_standards": rate(std_items),
        "total": total,
        "n_critical": n_crit, "n_error": n_err,
        "n_warning": n_warn, "n_notice": n_notice,
        "issues_by_module": issues,
    }


# --- Report (stand-alone CLI) -------------------------------------------------

_RANK_LABEL = {RANK_CRITICAL: "critical", RANK_ERROR: "error", RANK_WARNING: "warning"}


def format_report(domain, scored, max_per_module=3):
    """Plain-text report used by the stand-alone/calibration CLI."""
    r = scored
    ok = r["total"] - (r["n_critical"] + r["n_error"] + r["n_warning"])
    lines = [f"DNS (Zonemaster) for {domain}: {r['rating']}"]

    if r["total"] == 0:
        lines.append("- No test cases ran (check domain/network).")
        return "\n".join(lines)

    lines.append(f"- {ok} of {r['total']} criteria without remark.")
    if r["n_notice"]:
        lines.append(f"- {r['n_notice']} notice(s) (no rating impact).")

    for module in sorted(r["issues_by_module"]):
        items = sorted(r["issues_by_module"][module], key=lambda x: -x["rank"])
        for item in items[:max_per_module]:
            msg = item["message"].replace("\n", " ")
            if len(msg) > 100:
                msg = msg[:97] + "..."
            label = _RANK_LABEL.get(item["rank"], "?")
            lines.append(f"- {module} [{label}] {item['testcase']}: {msg}")
        if len(items) > max_per_module:
            lines.append(f"- {module}: (+{len(items) - max_per_module} more)")
    return "\n".join(lines)


# --- webperf_core adapter -----------------------------------------------------

def _profile_path():
    """Absolute path to the bundled severity profile, or None if missing."""
    base_directory = Path(os.path.dirname(os.path.realpath(__file__))).parent
    path = os.path.join(base_directory.resolve(), 'defaults', PROFILE_FILENAME)
    return path if os.path.exists(path) else None


def build_review(scored, local_translation, max_per_module=3):
    """Build the localized review text from a scored result."""
    r = scored
    lines = []
    if r["total"] == 0:
        return local_translation('TEXT_REVIEW_NO_TESTCASES')

    if r["n_critical"]:
        lines.append(local_translation('TEXT_REVIEW_BROKEN_DELEGATION'))

    ok = r["total"] - (r["n_critical"] + r["n_error"] + r["n_warning"])
    lines.append(local_translation('TEXT_REVIEW_CRITERIA_SUMMARY').format(ok, r["total"]))
    if r["n_notice"]:
        lines.append(local_translation('TEXT_REVIEW_NOTICES').format(r["n_notice"]))

    severity_key = {
        RANK_CRITICAL: 'TEXT_SEVERITY_CRITICAL',
        RANK_ERROR: 'TEXT_SEVERITY_ERROR',
        RANK_WARNING: 'TEXT_SEVERITY_WARNING',
    }
    for module in sorted(r["issues_by_module"]):
        items = sorted(r["issues_by_module"][module], key=lambda x: -x["rank"])
        for item in items[:max_per_module]:
            msg = item["message"].replace("\n", " ")
            if len(msg) > 100:
                msg = msg[:97] + "..."
            label = local_translation(severity_key.get(item["rank"], 'TEXT_SEVERITY_WARNING'))
            lines.append(local_translation('TEXT_REVIEW_ISSUE').format(
                module, label, item["testcase"], msg))
        if len(items) > max_per_module:
            lines.append(local_translation('TEXT_REVIEW_MORE').format(
                module, len(items) - max_per_module))
    return ''.join(lines)


def run_test(global_translation, url):
    """Run the Zonemaster DNS test on ``url`` and return (Rating, dict).

    Mirrors the other external-tool tests: the language comes from config, the
    review text is localized, and the 1.0-5.0 rating is mapped onto the overall,
    standards and integrity/security parts of the Rating model.
    """
    # Imported here so the module stays importable / runnable stand-alone
    # without the webperf_core package being on the path.
    from helpers.models import Rating
    from helpers.setting_helper import get_config
    from tests.utils import get_translation

    rating = Rating(global_translation, get_config('general.review.improve-only'))
    local_translation = get_translation('zonemaster_dns', get_config('general.language'))

    print(local_translation('TEXT_RUNNING_TEST'))
    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    domain = domain_from_url(url, get_config('tests.dns.registrable'))
    if not domain:
        rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (rating, {'failed': True, 'url': url})

    # Make the tested zone visible (the registrable-domain stripping is otherwise
    # invisible, which makes results hard to predict against Zonemaster's site).
    original_host = (urlparse(url if '://' in url else 'http://' + url).hostname
                     or '').strip('.').lower()
    if original_host and original_host != domain:
        print(local_translation('TEXT_TESTED_ZONE_FROM').format(domain, original_host))
    else:
        print(local_translation('TEXT_TESTED_ZONE').format(domain))

    try:
        raw = run_zonemaster(
            domain,
            image=get_config('tests.dns.image') or DOCKER_IMAGE,
            timeout=get_config('tests.dns.timeout'),
            use_ipv6=get_config('tests.dns.ipv6'),
            profile_path=_profile_path() if get_config('tests.dns.profile.use') else None)
    except RuntimeError as exc:
        rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (rating, {'failed': True, 'url': url, 'domain': domain, 'error': str(exc)})

    entries = normalize_entries(raw)
    scored = score(
        entries,
        error_penalty=float(get_config('tests.dns.error-penalty')),
        warning_penalty=float(get_config('tests.dns.warning-penalty')))

    points = scored["rating"]
    if points == -1.0:
        rating.overall_review = local_translation('TEXT_REVIEW_NO_TESTCASES')
        return (rating, {'failed': True, 'url': url, 'domain': domain})

    review = build_review(scored, local_translation)
    if points >= 5.0:
        # "Very good" is reserved for a flawless 5.0 (no confirmed deficiencies).
        review = local_translation('TEXT_REVIEW_VERY_GOOD') + review
    elif points >= 3.5:
        review = local_translation('TEXT_REVIEW_IS_GOOD') + review
    elif points >= 2.5:
        review = local_translation('TEXT_REVIEW_IS_OK') + review
    elif points >= 1.5:
        review = local_translation('TEXT_REVIEW_IS_BAD') + review
    else:
        review = local_translation('TEXT_REVIEW_IS_VERY_BAD') + review

    rating.set_overall(points, review)
    if scored["rating_standards"] != -1.0:
        rating.set_standards(scored["rating_standards"],
                             local_translation('TEXT_REVIEW_STANDARDS'))
    if scored["rating_security"] != -1.0:
        rating.set_integrity_and_security(scored["rating_security"],
                                          local_translation('TEXT_REVIEW_INTEGRITY_SECURITY'))

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    print(global_translation('TEXT_SITE_RATING'), rating)
    if get_config('general.review.show'):
        print(global_translation('TEXT_SITE_REVIEW'), rating.get_reviews())

    return_dict = {k: v for k, v in scored.items() if k != 'issues_by_module'}
    return_dict.update({'url': url, 'domain': domain})
    return (rating, return_dict)


# --- Batch orchestration (stand-alone / calibration) --------------------------

def evaluate_url(url, **run_kwargs):
    """URL -> domain -> Zonemaster -> rating. Returns a result dict."""
    registrable = run_kwargs.pop('use_registrable_domain', True)
    domain = domain_from_url(url, registrable)
    if not domain:
        return {"url": url, "domain": None, "error": "could not parse domain"}
    try:
        raw = run_zonemaster(domain, **run_kwargs)
    except RuntimeError as exc:
        return {"url": url, "domain": domain, "error": str(exc)}
    entries = normalize_entries(raw)
    result = score(entries)
    result.update({"url": url, "domain": domain, "raw": raw})
    return result


def _load_urls(args):
    urls = list(args.urls)
    if args.file:
        with open(args.file, encoding="utf-8") as file_handle:
            urls += [ln.strip() for ln in file_handle
                     if ln.strip() and not ln.startswith("#")]
    return urls


def _run_batch(urls, args):
    run_kwargs = {"image": args.image, "timeout": args.timeout, "use_ipv6": args.ipv6,
                  "use_registrable_domain": not args.hostname}
    if not args.no_profile:
        profile = _profile_path()
        if profile:
            run_kwargs["profile_path"] = profile
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(evaluate_url, u, **run_kwargs): u for u in urls}
        for fut in concurrent.futures.as_completed(futs):
            results.append(fut.result())
    order = {u: i for i, u in enumerate(urls)}
    results.sort(key=lambda r: order.get(r["url"], 0))
    if args.save_dir:
        os.makedirs(args.save_dir, exist_ok=True)
        for result in results:
            if result.get("domain") and "raw" in result:
                path = os.path.join(args.save_dir, f"{result['domain']}.json")
                with open(path, "w", encoding="utf-8") as file_handle:
                    json.dump(result["raw"], file_handle, ensure_ascii=False, indent=2)
    return results


def _rescore_dir(directory, args):
    """Rescore from saved raw JSON (for calibration without new DNS traffic)."""
    results = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as file_handle:
            raw = json.load(file_handle)
        entries = normalize_entries(raw)
        result = score(entries, error_penalty=args.error_penalty,
                       warning_penalty=args.warning_penalty)
        result.update({"url": name, "domain": name[:-5]})
        results.append(result)
    return results


def _build_arg_parser():
    parser = argparse.ArgumentParser(description="Zonemaster DNS test for webperf_core")
    parser.add_argument("urls", nargs="*", help="one or more URLs/domains")
    parser.add_argument("-f", "--file", help="file with one URL per line")
    parser.add_argument("--workers", type=int, default=2, help="parallel runs")
    parser.add_argument("--timeout", type=int, default=180, help="seconds per domain")
    parser.add_argument("--image", default=DOCKER_IMAGE, help="docker image (pin version here)")
    parser.add_argument("--ipv6", action="store_true", help="enable IPv6 (needs IPv6 in Docker)")
    parser.add_argument("--hostname", action="store_true",
                        help="test the exact hostname instead of the registrable domain")
    parser.add_argument("--no-profile", action="store_true",
                        help="do not pass the bundled severity profile")
    parser.add_argument("--save-dir", help="save raw JSON per domain here")
    parser.add_argument("--from-dir", help="rescore from saved raw JSON (no DNS)")
    parser.add_argument("--warning-penalty", type=float, default=WARNING_PENALTY,
                        help="points removed per warning (calibration, from-dir)")
    parser.add_argument("--error-penalty", type=float, default=ERROR_PENALTY,
                        help="points removed per error (calibration, from-dir)")
    parser.add_argument("--json-out", action="store_true", help="machine-readable summary")
    return parser


def main(argv=None):
    """Stand-alone entry point for trial runs and calibration."""
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if args.from_dir:
        results = _rescore_dir(args.from_dir, args)
    else:
        urls = _load_urls(args)
        if not urls:
            parser.error("provide at least one URL or --file")
        results = _run_batch(urls, args)

    if args.json_out:
        slim = [{k: v for k, v in r.items() if k != "raw"} for r in results]
        print(json.dumps(slim, ensure_ascii=False, indent=2))
    else:
        for result in results:
            if result.get("error"):
                print(f"DNS (Zonemaster) for {result.get('domain') or result['url']}: "
                      f"ERROR - {result['error']}\n")
            else:
                print(format_report(result["domain"], result) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
