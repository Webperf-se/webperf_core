# Working in webperf_core

This file is for anyone, human or agent, who needs to get productive in this repository quickly. It says what the code does, where things live, how to run and check it, and which conventions a pull request has to follow. The user facing documentation is under [docs/](docs/README.md).

## What this is

webperf_core is a command line tool that runs a set of tests against a website and rates it 1 to 5 in five fields: overall, security, performance, accessibility and standards. It is the engine behind [webperf.se](https://webperf.se) and webperf.cloud, and it is used by other organisations for their own sites. The JSON and SQL output is a contract: webperf.se, webperf.cloud, api.webperf.se and third parties import it. Do not change the output fields, their meaning or the number of entries per run without a discussion first.

## Repository map

| Path | What it is |
|---|---|
| `default.py` | The CLI. Parses arguments, reads the site list, runs tests, writes results. Run `python3 default.py -h`. |
| `helpers/test_helper.py` | The test registry (`TEST_ALL_FUNCS`, `TEST_USE_SITESPEED`), `test_site()` and `combine_test_results()`, and the failures log. |
| `helpers/models.py` | `Rating` (the 1 to 5 rating with review texts, combined with `__add__`) and `SiteTests` (one output entry). |
| `helpers/setting_helper.py` | Settings: `get_config('section.key')`, the alias table for old setting names, `--setting`. Defaults in `defaults/settings.json`, overrides in `settings.json` (gitignored). |
| `tests/*.py` | One file per Python test. Each exposes `run_test(global_translation, url)` and returns `(Rating, dict)`. |
| `tests/utils.py` | Shared helpers: `calculate_score()` and `calculate_rating()` for issue based tests, DNS lookups, HTTP cache, the EU and adequacy country lists, IP2Location. |
| `tests/sitespeed_base.py` | Runs sitespeed.io (local `node_modules` or Docker) and reads the JSON the plugins write. |
| `engines/` | Input and output formats: `json_engine.py`, `csv_engine.py`, `sqlite.py`, `sql.py`, `markdown_engine.py`, `sitemap.py`, `sitespeed_result.py`. |
| `locales/<lang>/LC_MESSAGES/*.po` | gettext translations of review texts, one file per test. Compiled `.mo` files are committed. See [docs/translation.md](docs/translation.md). |
| `defaults/` | `settings.json` and the rule data some tests read (`analytics-rules.json`, `software-rules.json`, `software-sources.json`, `a11y-overlays.json`). |
| `data/` | Downloaded data that is not committed: IP2Location database, blocklists, Disconnect list. Tests degrade without them, see each test's doc. |
| `unittests/` | Offline unit tests, `python3 -m unittest unittests.<module>`. |
| `.github/workflows/` | `pylint.yml`, one `regression-test-*.yml` per test (they run real sites, need network), release and Docker image workflows. `verify_result.py` checks the JSON a regression run produced. |
| `docs/` | User documentation. [docs/rating.md](docs/rating.md) explains how ratings are calculated. |
| `Dockerfile` | Image based on `sitespeedio/sitespeed.io`, published as `webperfse/webperf-core`. Runs as user `sitespeedio` with `WORKDIR /usr/src/runner`. |

## The tests

Tests are selected by number. Numbers that are not listed are deprecated and kept as `TEST_DEPRECATED` in `helpers/test_helper.py`.

| Number | Test | Runs as |
|---|---|---|
| 2 | Page not found | sitespeed.io plugin `plugin-pagenotfound` |
| 9 | Standard files | sitespeed.io plugin `plugin-standard-files` |
| 15 | Performance | `tests/performance_sitespeed_io.py` |
| 18 | Accessibility, pa11y | `tests/a11y_pa11y.py`, runs `node_modules/pa11y` |
| 20 | Webbkoll (legacy, replaced by 31) | `tests/privacy_webbkollen.py` |
| 21 | HTTP and network | `tests/http_validator.py` |
| 22 | Energy efficiency | `tests/energy_efficiency.py` |
| 23 | Tracking and integrity | `tests/tracking_validator.py` |
| 24 | Email | `tests/email_validator.py` |
| 25 | Software | `tests/software.py` |
| 26 | Accessibility statement | sitespeed.io plugin `plugin-accessibility-statement` |
| 27 | CSS | sitespeed.io plugin `plugin-css` |
| 28 | HTML | sitespeed.io plugin `plugin-html` |
| 29 | JavaScript | sitespeed.io plugin `plugin-javascript` |
| 30 | Lighthouse | `@sitespeed.io/plugin-lighthouse` through `plugin-webperf-core` |
| 31 | Privacy | `tests/privacy.py`, starts `webbkoll-backend` from `node_modules` |
| 32 | DNS | `tests/zonemaster_dns.py`, runs the `zonemaster/cli` Docker image |

The sitespeed.io plugins live in their own repositories under [github.com/Webperf-se](https://github.com/Webperf-se): `plugin-pagenotfound`, `plugin-standard-files`, `plugin-accessibility-statement`, `plugin-css`, `plugin-html`, `plugin-javascript` and `plugin-webperf-core`. The last one collects the others' issues, converts Lighthouse audits to issues and calculates the score in `lib/score.js`. Their versions are pinned in `package.json`. A change in a plugin reaches webperf_core only through a release of the plugin and a version bump here, in its own pull request.

## How a run works

1. `default.py` reads the site list (`-u` for one URL, `-i` for a file, see [docs/getting-started.md](docs/getting-started.md#input-formats)) and the test numbers (`-t 2,22`, comma separated).
2. `test_sites()` in `helpers/test_helper.py` loops over sites. For each site, `test_site()` runs all selected plugin tests in one sitespeed.io session and every Python test on its own.
3. A Python test returns `(Rating, dict)`. A plugin run returns a dict with `groups` of issues; `calculate_rating()` in `tests/utils.py` turns that into a `Rating`.
4. Each result becomes one `SiteTests` entry with `type_of_test`, the five rating fields, the five review texts and `data`. When more than one test ran, `combine_test_results()` adds an entry with `type_of_test -1` for the whole run.
5. The engine chosen by the `-o` file ending writes the entries.

Ratings: issue based tests deduct 25, 10 and 1 points per critical, error and warning from 100 per category; `no-a11y-statement` zeroes its category. Python tests build their rating from sub checks added with `Rating.__add__`, which averages per category. All of it is in [docs/rating.md](docs/rating.md).

## Commands

```
pip install -r requirements.txt
npm install --omit=dev
python3 default.py -t ?                      # list tests
python3 default.py -s ?                      # list settings
python3 default.py -u https://example.com -t 21 -r -o reports/t21.json
python3 -m unittest discover -s unittests -t .   # offline unit tests
pylint $(git ls-files '*.py') --generated-members json,ssl,datetime --disable C0114 --errors-only
```

The pylint line is what CI runs; it must pass. The regression workflows need network and a browser and are run by GitHub Actions, not locally. The Docker image is the simplest way to get all dependencies, see [docs/getting-started-docker.md](docs/getting-started-docker.md).

## Conventions

- Code, comments, docstrings, documentation, commit messages and pull request texts are in English. Swedish appears only in `locales/sv` and in the Swedish specific tests.
- One branch and one pull request per topic. Code and documentation for the same change go together; unrelated fixes do not.
- A change to how a rating is calculated starts with a unit test in `unittests/` that fails before the change. Describe the effect with before and after ratings in the pull request.
- Settings are read with `get_config('section.key')`. Add new keys to `defaults/settings.json`, to the alias table in `helpers/setting_helper.py` and to [docs/settings-json.md](docs/settings-json.md).
- Review texts are translation keys. Add the key to the test's `.po` file for every language in `locales/` and compile the `.mo`, see [docs/translation.md](docs/translation.md). A missing key is reported at runtime and appended to the `.po` file.
- Every test has a page under `docs/tests/`, listed in [docs/tests/README.md](docs/tests/README.md). Start from `docs/tests/test-template.md`.
- No attribution lines in commits or pull requests.

## Do not

- Do not fetch anything from webperf.se at runtime. The site is not an API, and every user of this tool would be hitting it.
- Do not add external services a test depends on without a setting to point elsewhere and a note in the test's doc.
- Do not commit anything under `data/`, `settings.json`, `failures.log` or `reports/`.
- Do not bump plugin versions in `package.json` as part of another change.
