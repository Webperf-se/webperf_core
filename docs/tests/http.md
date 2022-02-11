# HTTP & Network
[![Regression Test - HTTP & Network](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-http.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-http.yml)

Add small description of what this test is.


## What is being tested?

### HTTP to HTTPS redirect

Checks if HTTP requests are redirected to HTTPS.
A common misstake is to forget to force this redirect for root domain if www. subdomain is used.

### TLS and SSL support

Checks for Secure encryption support
* Checks for TLS 1.3 support
* Checks for TLS 1.2 support

Checks for Insecure encryption support
* Checks for TLS 1.1 support
* Checks for TLS 1.0 support
* Checks for SSL 3.0 support (Require host modification)
* Checks for SSL 2.0 support (Require host modification)
* Checks if certificate used match website domain

### HTTP protocol support

* Checks for HTTP/1.1 support
* Checks for HTTP/2 support
* Checks for HTTP/3 support
* Checks for Quick support

### IPv6 and IPv4 support

* Checks for IPv4 support
* Checks for IPv6 support

## How are rating being calculated?

This section has not been written yet.

## Read more

Links to other sources where you can test or read more

## FAQ

No frequently asked questions yet :)

## How to setup?

### Prerequirements

Is the website required to be public because we use external service?

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

#### Using NPM package

#### Using Docker image

#### Using service?



