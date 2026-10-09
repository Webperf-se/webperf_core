# Accessibility (Pa11y)
[![Regression Test - Accessibility (Pa11y) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-pa11y.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-pa11y.yml)

This test runs [pa11y](https://github.com/pa11y/pa11y) against the page and reports the accessibility problems it finds. pa11y is installed from `package.json` and runs with the Chrome on the machine.

## What is being tested?

It test accessibility on the specified url.
Please note that automated accessibility test generally only find 20-30% of all errors.
Even if this test is not finding anything you should still do a manuall check once in a while.

## How are rating being calculated?

pa11y runs first with its default HTML_CodeSniffer runner. If that finds nothing, it runs again with the axe runner. Every distinct message becomes one issue in the category `a11y` with pa11y's own `type` as severity: `error`, `warning` or `notice`. The same message on several elements counts once, with the elements as sub issues.

The score then follows the issue based model in [How ratings are calculated](../rating.md): `a11y` starts at 100, every `error` deducts 10 points and every `warning` 1 point. `notice` deducts nothing. The rating is the score divided by 20, so a page with three distinct errors gets `rating_a11y` 3.5. Only `rating_a11y` and `rating` are set. The code is in [tests/a11y_pa11y.py](../../tests/a11y_pa11y.py).

## Read more

* https://github.com/pa11y/pa11y

## How to setup?

pa11y comes with the npm packages of this repository, so the general setup is enough. It needs a Chrome or Chromium on the machine. The Docker image has everything.

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)
* Download and install Node.js (version 24.x)
* Download and install Google Chrome browser
* Install NPM packages ( `npm install --omit=dev` )

