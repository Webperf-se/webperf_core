# Accessibility (Pa11y)
[![Regression Test - Accessibility (Pa11y) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-pa11y.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-pa11y.yml)

Add small description of what this test is.

## What is being tested?

It test accessibility on the specified url.
Please note that automated accessibility test generally only find 20-30% of all errors.
Even if this test is not finding anything you should still do a manuall check once in a while.

## How are rating being calculated?

We are rating the url based on:
- If Pa11y finds 0 errors you get 5.0 in rating
- If Pa11y finds just 1 error you get 4.0 in rating
- If Pa11y finds 2-3 errors you get 3.0 in rating
- If Pa11y finds 4-7 errors you get 2.0 in rating
- Else you will get 1.0 in rating

## Read more

* https://github.com/pa11y/pa11y-ci
* https://github.com/pa11y/pa11y

## How to setup?

This section has not been written yet.

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)
* Download and install Node.js
* Install Pa11y CI npm package ( `npm install -g pa11y-ci` )

## FAQ

No frequently asked questions yet :)

