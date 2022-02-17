# Google Lighthouse based Tests
[![Regression Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-google-lighthouse-based.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-google-lighthouse-based.yml)

This is a general page for all tests that are using Google Lighthouse in the background.

Following tests are using Google Lighthouse in the background:
* [Google Lighthouse accessibility with Axe](google-lighthouse-a11y.md)
* [Google Lighthouse performance](google-lighthouse-performance.md)
* [Google Lighthouse best practice](google-lighthouse-best-practice.md)
* [Google Lighthouse progressive web apps](google-lighthouse-pwa.md)
* [Google Lighthouse SEO](google-lighthouse-seo.md)
* [Energy efficiency](energy-efficiency.md)

## How to setup?

This section has not been written yet.

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

This section has not been written yet.
* Follow [general local setup steps for this repository](../getting-started-local.md)

You can run this test by letting webperf-core call Google API:s (googleapis.com) or install a local version on your system.
Follow the instructions below depending on what you choose.

#### Using NPM package

Benefit of this option is that you can use it to test pre production urls like your AcceptanceTest environment.

* Download and install Node.js (v2)
* Installl lighthouse NPM Package ( `npm install -g lighthouse` )
* Set `lighthouse_use_api = False` in your `config.py`

#### Using service?

Using this option limits you to test urls that are publically available (Accessible from Internet).
You will also need to ccreate a Google Account and request a API KEY.

Get your API key by:
1. Go to [Google Cloud Platform](https://console.cloud.google.com/apis).
2. Search for *Pagespeed Insights API*.
3. Click the button labelled *Manage*.
4. Click on *Credentials* (you may need to create a project first, if you do not already have one).
5. Click *+ Create Credentials*, then *API key*
6. In the dialogue box the key now appears below *Your API key*, it can look like this *AIzaXyCjEXTvAq7zAU_RV_vA7slvDO9p1weRfgW*
7. Set `googlePageSpeedApiKey = "<YOUR API KEY>"` in your `config.py`
8. Set `lighthouse_use_api = True` in your `config.py`

## Read more

Links to other sources where you can test or read more
* https://web.dev/
* https://pagespeed.web.dev/


## FAQ

No frequently asked questions yet :)
