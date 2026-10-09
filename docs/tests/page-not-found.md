# 404 (Page not Found)
[![Regression Test - 404 (Page not Found) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-404.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-404.yml)

This test checks that your 404 (page not found) page is set up correctly. It requests a random URL on your domain and looks at the response. The test runs as the sitespeed.io plugin [plugin-pagenotfound](https://github.com/Webperf-se/plugin-pagenotfound).

## What is being tested?

Each check is a rule with a fixed severity. The rules and their severities are defined in `rules` in `lib/harAnalyzer.js` of the plugin.

| Rule | Severity | Fails when |
|---|---|---|
| `no-valid-response-status-code` | error | The random URL does not answer with HTTP status 404 |
| `no-valid-text-found` | error | The response has no readable body text |
| `invalid-text-found` | warning | The body text is shorter than 150 characters |
| `no-valid-title-found` | warning | The HTML has no `title` element with text |
| `no-valid-h1-found` | warning | The HTML has no `h1` element with text |
| `no-valid-not-found-text-in-body` | warning | None of the expected phrases for the page's language is found in the body text |
| `no-unsupported-locale-use` | warning | The page's language has no phrase list in the plugin |
| `has-unexpected-404-response` | warning | Other resources on the page (images, scripts) answered with 404 |
| `no-network` | warning | The URL could not be fetched at all |

All rules use the category `standard`, so this test sets `rating_stand` and `rating`.

### Phrases per language

The phrases that a 404 page is expected to contain live in `locale/<lang>.json` in the plugin, one file per language, under the key `valid-not-found-texts`. The language is taken from the `lang` attribute of the page's `html` element.

Supported languages today:

- `sv` (Swedish)
- `en` (English)

A page in any other language cannot pass `no-valid-not-found-text-in-body`. If your language is missing, add a locale file to the plugin and open a pull request there.

## How are rating being calculated?

The rating follows the issue based model described in [How ratings are calculated](../rating.md): the `standard` category starts at 100, every failing rule deducts 10 points for `error` and 1 point for `warning`, and the rating is the score divided by 20. A page that returns 404 with a title, an `h1` and a long enough text but without a recognised phrase gets 99 points, which is a rating of 4.95. A page that returns 200 instead of 404 loses 10 points for that alone.

## Read more

## How to setup?

### Prerequirements

* Fork this repository
* As we are using external service ( https://validator.w3.org/nu/ ) your site needs to be publicly available and the machine running
this test needs to be able to access external service.

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)

