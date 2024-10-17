# HTTP & Network
[![Regression Test - HTTP & Network](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-http.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-http.yml)

Add small description of what this test is.


## What is being tested?

### HTTP to HTTPS redirect

Checks if HTTP requests are redirected to HTTPS.
A common misstake is to forget to force this redirect for root domain if www. subdomain is used.
Also checks for HSTS support.

### TLS support

Checks for Secure encryption support
* Checks for TLS 1.3 support
* Checks for TLS 1.2 support

Checks for Insecure encryption support
* Checks for TLS 1.1 support
* Checks for TLS 1.0 support
* Checks if certificate used match website domain

### HTTP protocol support

* Checks for HTTP/1.1 support
* Checks for HTTP/2 support
* Checks for HTTP/3 support

### IPv6 and IPv4 support

* Checks for IPv4 support
* Checks for IPv6 support

### Content Security Policy (CSP) support

* Checks for CSP support
* Gives CSP recommendation if it could improve 0.75 or more in rating

## How are rating being calculated?

This section has not been written yet.

## Read more

Links to other sources where you can test or read more

* https://www.ssllabs.com/ssltest/
* https://http3check.net/

## How to setup?

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)
* It is highly recommended to set `cache_when_possible` to `True` and to set `cache_time_delta` to
* It is highly recommended to set `cache_time_delta` to at least 12 hours (Fail to do so may result in banning of service like github).

#### Using NPM package

* Download and install Node.js (version 20.x)
* Download and install Google Chrome browser
* Download and install Mozilla Firefox browser
* Install NPM packages ( `npm install --omit=dev` )
* Set `sitespeed_use_docker = False` in your `config.py`

##### Windows Specific

* Allow node to connect through Windows firewall

#### Using Docker image

* Make sure Docker command is globally accessible on your system.
* Set `sitespeed_use_docker = True` in your `config.py`

## FAQ

### How to get CSP recommendation for website
Did you know you can get a CSP recommendation for all/part of your website?
Do the following and webperf_core will give a CSP recommendation for more than 1 page.
* Set `csp_only = True` in your `config.py`
* Point webperf_core to your sitemap or your own list pages you want to test.

Example, below will take first 25 items from sitemap:
`python default.py -r -t 21 --input-take=25 -i https://nimbleinitiatives.com/sitemap.xml`
