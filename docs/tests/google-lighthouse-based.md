# Google Lighthouse based Tests
[![Regression Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-google-lighthouse-based.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-google-lighthouse-based.yml)

This is test 30. It runs [Google Lighthouse](https://developer.chrome.com/docs/lighthouse) through sitespeed.io's `@sitespeed.io/plugin-lighthouse` and turns the audits into issues.

## What is being tested?

Every Lighthouse audit in the categories performance, accessibility, best practices and SEO. Lighthouse runs once per page in the same browser session as the other sitespeed.io based tests.

## How are rating being calculated?

`plugin-webperf-core/lib/lighthouseConverter.js` converts each audit to an issue. The audit's score decides the severity: 90 or more is `resolved`, 50 to 89 is `warning`, below 50 is `error`. An audit that cannot be read is `critical`. The issue keeps Lighthouse's category name, except that `accessibility` becomes `a11y`.

The score then follows the issue based model in [How ratings are calculated](../rating.md). `performance` sets `rating_perf` and `a11y` sets `rating_a11y`. `best-practices` and `seo` have no rating field of their own: they count in `rating` and their issues show in the overall review text.

## How to setup?

This test is using Sitespeed.io in the background
so please follow instructions on page about [Sitespeed.io Based Test](./sitespeed.md). Nothing is sent to Google; Lighthouse runs locally in Chrome.

## Read more

* https://web.dev/
* https://pagespeed.web.dev/


