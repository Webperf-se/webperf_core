# How ratings are calculated

Every test result has five rating fields:

| Field | Category |
|---|---|
| `rating` | Overall |
| `rating_sec` | Integrity and security |
| `rating_perf` | Performance |
| `rating_a11y` | Accessibility |
| `rating_stand` | Standards |

The scale is 1.0 to 5.0. A value of `-1` means the test does not rate that category, so it is not a low rating. Values are clamped by `Rating.ensure_correct_points_range()` in [helpers/models.py](../helpers/models.py), so a score of 0 out of 100 shows as 1.0, never as 0.

Everything below describes the code on `main`. Where a number comes from a constant, the file is named so you can check it.

## Two kinds of tests

### Issue based tests

Tests 2, 9, 18 and 26 to 30 produce a list of issues per group (a group is the hostname of the tested URL). Each issue has a `rule`, a `category` and a `severity`. The score is calculated per category by `calculateScore()` in `plugin-webperf-core/lib/score.js` for the sitespeed.io plugins, and by `calculate_score()` in [tests/utils.py](../tests/utils.py) for pa11y and for combined runs. The two implementations are meant to give the same result.

1. Every category that has at least one issue starts at 100.
2. Every failing rule deducts points: 25 for `critical`, 10 for `error`, 1 for `warning`. `info` and `resolved` deduct nothing. A rule counts once per group no matter how many `subIssues` (pages or resources) it has.
3. A showstopper rule that is not `resolved` sets its category to 0. The only showstopper today is `no-a11y-statement` from test 26. The list is `showstopperRules` in `score.js` and `SHOWSTOPPER_RULES` in `tests/utils.py`.
4. Overall is the average of the categories that occur in the group. A category with no issues at all is left out of the average.
5. The rating is score / 100 × 5, clamped to 1.0 to 5.0.

Example: one `error` and two `warning` in `standard` and nothing else gives standard 88, overall 88, `rating_stand` 4.4 and `rating` 4.4.

### Tests with their own logic

Tests 15, 21 to 25, 31 and 32 are Python tests that build their rating from sub checks. Each sub check creates its own `Rating` with `set_overall()`, `set_integrity_and_security()` and so on, and the sub checks are added together with `Rating.__add__`, which averages every category over the ratings that set it.

Some tests use their own formula instead of the issue table:

- Test 22 rates the page weight against percentiles of earlier Webperf.se measurements. See [energy-efficiency.md](tests/energy-efficiency.md).
- Test 32 uses a penalty per failed Zonemaster criterion, documented at the top of [tests/zonemaster_dns.py](../tests/zonemaster_dns.py).

## Categories

Issues can have any `category`. Only four are mapped to a rating field: `security`, `performance`, `a11y` and `standard`. Every other category still counts in the overall average and its issues end up in the overall review text, but it gets no rating field of its own.

This matters for Lighthouse (test 30). `plugin-webperf-core/lib/lighthouseConverter.js` keeps the Lighthouse category names and only renames `accessibility` to `a11y`. `performance` matches the performance category by name, but `best-practices` and `seo` are separate categories that only affect `rating`. The same applies to `technical`, used by tests 9 and 26 for problems with the test itself, such as `no-network`.

Whether `best-practices` and `seo` should be mapped to a rating field is an open question. Until it is settled, do not read `rating_stand` as covering SEO or best practices.

## Which test sets which rating

Taken from the `set_*` calls in each Python test and the `category` values in each plugin. Test 20 is left out: it is replaced by test 31 and kept only for old results.

| Test | Overall | Security | Performance | A11y | Standards | Other categories |
|---|---|---|---|---|---|---|
| 2 Page not found | x | | | | x | |
| 9 Standard files | x | x | | | x | technical |
| 15 Sitespeed | x | | x | | | |
| 18 Pa11y | x | | | x | | |
| 21 HTTP | x | x | | | x | |
| 22 Energy efficiency | x | | | | | |
| 23 Tracking | x | x | | | | |
| 24 Email | x | x | x | | x | |
| 25 Software | x | x | | x | | |
| 26 A11y statement | x | | | x | | technical |
| 27 CSS | x | | | | x | unknown |
| 28 HTML | x | | | | x | |
| 29 JavaScript | x | x | | | x | |
| 30 Lighthouse | x | | x | x | | best-practices, seo |
| 31 Privacy | x | x | | | | |
| 32 DNS | x | x | | | x | |

## Where rules and severities are defined

| Test | Where |
|---|---|
| 2 | `rules` in `plugin-pagenotfound/lib/harAnalyzer.js` |
| 9 | `RULES` in `plugin-standard-files/lib/harAnalyzer.js` |
| 18 | pa11y's own `type` is used as severity (`error`, `warning`, `notice`) in [tests/a11y_pa11y.py](../tests/a11y_pa11y.py). `notice` deducts nothing. |
| 26 | `rules` in `plugin-accessibility-statement/lib/harAnalyzer.js` |
| 27 | `plugin-css/configurations/standard.json` (stylelint severities) |
| 28 | `plugin-html/configurations/standard.json`. html-validate severity 2 becomes `error`, everything else `warning`. |
| 29 | `plugin-javascript/eslint.config.js`. ESLint severity 1 becomes `warning`, 2 becomes `error`. |
| 30 | `getSeverityFromScore()` in `plugin-webperf-core/lib/lighthouseConverter.js`: audit score 90 or more is `resolved`, 50 or more is `warning`, below 50 is `error`. An audit that cannot be read is `critical`. |
| Showstoppers | `plugin-webperf-core/lib/score.js` and `SHOWSTOPPER_RULES` in [tests/utils.py](../tests/utils.py) |
| 15, 21 to 25, 31, 32 | In each test's file under [tests/](../tests/) |

## Combined runs

Running more than one test in one go, for example `-t 2,22,32`, produces one entry per test plus one entry with `type_of_test: -1` for the whole run. The combined entry is calculated by `combine_test_results()` in [helpers/test_helper.py](../helpers/test_helper.py):

1. The issues of all issue based tests are merged per group and the score is recalculated from the merged issues. Two tests that both find `a11y` problems therefore both lower the a11y rating.
2. Every test with its own logic contributes its `Rating`.
3. The merged groups and those ratings are added with `Rating.__add__`, so every category is the average of the contributors that set it.

Two consequences to keep in mind:

- The merged issue score counts as one contributor, however many plugin tests it covers.
- The sitespeed.io plugins (2, 9, 26 to 30) run in one browser session and are reported as one entry with `type_of_test: -1` when more than one of them is selected. To get a rating per plugin test, run them one at a time.

If you want ratings per test, run one test at a time and keep one output file per test. See [getting-started-docker.md](getting-started-docker.md) for a loop that does this.

Before pull request [#1615](https://github.com/Webperf-se/webperf_core/pull/1615) a combined run kept only the rating of the issue based tests, kept the first stored score per group and let the last group overwrite the others. Results from versions up to and including 2026.8.0 are affected.

## Language and country specific tests

`--language` (or `general.language`) only changes the language of the review texts. It does not change what is tested.

- Test 2 looks for phrases that a 404 page is expected to contain, in the language of the page's `lang` attribute. Only the languages with a file in `plugin-pagenotfound/locale/` are supported. See [page-not-found.md](tests/page-not-found.md).
- Test 22 is relative to percentiles from Webperf.se's own measurements, which are mostly Swedish sites. See [energy-efficiency.md](tests/energy-efficiency.md).
- Test 26 checks for a Swedish accessibility statement as required by the Swedish DOS act and described by DIGG. It gives a `no-a11y-statement` showstopper on sites that follow other countries' rules. See [a11y-statement.md](tests/a11y-statement.md).
- Tests 23 and 31 rate against the GDPR and EU adequacy decisions. They are about where data goes, not about language, so they apply to any site with visitors in the EU.
