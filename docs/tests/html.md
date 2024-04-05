# HTML Validation
[![Regression Test - HTML Validation Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-html.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-html.yml)

This test is validating all used HTML on the url specified.
We are currently using local version of [W3C HTML Validation](https://validator.w3.org/nu/) for validation.

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

## How to setup?

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)
* It is highly recommended to set `cache_when_possible` to `True` and to set `cache_time_delta` to
* It is highly recommended to set `cache_time_delta` to at least 12 hours (Fail to do so may result in banning of service like github).
* Depending on your preference, follow below NPM package or Docker image steps below.

* Download and install Java (JDK 8 or above)
* [Download latest vnu.jar](https://github.com/validator/validator/releases/download/latest/vnu.jar) and place it in your webperf-core directory

#### Using NPM package

* Download and install Node.js (version 20.x)
* Download and install Google Chrome browser
* Install NPM packages ( `npm install` )
* Set `sitespeed_use_docker = False` in your `config.py`

##### Windows Specific

* Allow node to connect through Windows firewall

#### Using Docker image

* Make sure Docker command is globally accessible on your system.
* Set `sitespeed_use_docker = True` in your `config.py`

## FAQ

No frequently asked questions yet :)
