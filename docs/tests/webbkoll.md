# Users’ integrity test against Webbkoll, provided by 5july.net
[![Regression Test - Integrity & Security (Webbkoll) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-webbkoll.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-webbkoll.yml)

This test is using Webbkoll provided by 5july.net to show how you handle user security and integrity.

## What is being tested?

We are currently using below sections of Webbkoll report:

* HTTPS by default
* HTTP Strict Transport Security (HSTS)
* Content Security Policy
* Reporting (CSP, Certificate Transparency, Network Error Logging)
* Referrer Policy
* Subresource Integrity (SRI)
* HTTP headers
* Cookies

## How are rating being calculated?

We are currently giving you 5 in rating by for every section above if there is no error or warning.
We give you 1 in rating if failed the section (getting a big red X, meaning error).
We are giving you 2.5 in rating if you have warning on the section level.

In addition to above we will give you following penelty:
* for every small error we will lower the rating by 0.5
* for every small warning we will lower the rating by 0.25.

Lowest rating is as always 1.0

## Read more

* https://webbkoll.5july.net/

## How to setup?

### Prerequirements

* Fork this repository
* As we are using external service ( https://webbkoll.5july.net/ ) your site needs to be publicly available and the machine running
this test needs to be able to access external service.

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)

## FAQ

No frequently asked questions yet :)

