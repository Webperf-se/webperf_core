# Accessibility Statement
[![Regression Test - Accessibility Statement Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-a11y-statement.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-a11y-statement.yml)

This test looks for an accessibility statement and rates it against Swedish law. It runs as the sitespeed.io plugin [plugin-accessibility-statement](https://github.com/Webperf-se/plugin-accessibility-statement).

## What is being tested?

The test is built on the Swedish act on accessibility to digital public service (lagen (2018:1937) om tillgänglighet till digital offentlig service, "DOS-lagen") and the guidance from DIGG, the Swedish Agency for Digital Government. It looks for Swedish wording such as "helt förenlig", "delvis förenlig" and "inte förenlig", and for a link to DIGG's notification form.

Because of this the test does not give meaningful results for sites outside Sweden. A site that follows another country's implementation of the EU Web Accessibility Directive has none of the Swedish markers, so the test reports `no-a11y-statement` with severity `critical`. That rule is a showstopper (see [How ratings are calculated](../rating.md)), which sets the a11y score to 0 and `rating_a11y` to 1.0 even if a correct statement exists in another language. Treat `rating_a11y` from this test as undefined for non-Swedish sites. How to avoid that false result is being discussed in the plugin's [issues](https://github.com/Webperf-se/plugin-accessibility-statement/issues).

It rates on many "shall" statements from the [Swedish Agency for Digital Government](https://digg.se/kunskap-och-stod/digital-tillganglighet/skapa-en-tillganglighetsredogorelse)

## How are rating being calculated?

Each check is a rule with a fixed severity, defined in `rules` in `lib/harAnalyzer.js` of the plugin, and the score follows the issue based model in [How ratings are calculated](../rating.md). The checks are:
- IF we can find an accessibility statement.
- On what link depth we find the accessibility statement.
- IF we can find "helt förenlig", "delvis förenlig" or "inte förenlig"
- IF we can find valid/correct [notification function url to DIGG](https://www.digg.se/tdosanmalan)
- IF we can find unreasonably burdensome accommodation
- IF we can find evaluation method used to validate accessibility
- IF we can find when accessibility statement was updated and WHEN

## Read more

* https://digg.se/kunskap-och-stod/digital-tillganglighet/skapa-en-tillganglighetsredogorelse

## How to setup?

This test is using Sitespeed.io in the background
so please follow instructions on page about [Sitespeed.io Based Test](./sitespeed.md). `tests.a11y-statement.max-nof-pages` (default 10) limits how many pages are followed when looking for the statement.

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)

