# Accessibility (Pa11y)
[![Regression Test - Accessibility (Pa11y) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-pa11y.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-pa11y.yml)

Add small description of what this test is.

## What is being tested?

It test accessibility on the specified url.
Please note that automated accessibility test generally only find 20-30% of all errors.
Even if this test is not finding anything you should still do a manuall check once in a while.

## How are rating being calculated?

We are calculating rating based on:
- Number of different error types
- Number of total number of errors

we are then combining the results.

Math used are:
- `rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)`
- `rating_number_of_errors = 5.0 - ((number_of_errors / 2.0) / 5.0)`

As always, minimum rating are 1.0.

## Read more

* https://github.com/pa11y/pa11y

## How to setup?

This section has not been written yet.

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)
* Download and install Node.js (version 20.x)
* Download and install Google Chrome browser
* Install NPM packages ( `npm install --omit=dev` )

## FAQ

No frequently asked questions yet :)

