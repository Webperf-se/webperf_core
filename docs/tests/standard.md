# Standard files
[![Regression Test - Standard files Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-standard-files.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-standard-files.yml)

Add small description of what this test is.

## What is being tested?

### Robots.txt

* Ensure /robots.txt has no `</html>` element
* Ensure /robots.txt has one or more of the following content:
  * `allow`
  * `disallow`
  * `user-agent`

### Sitemap

* Checks if sitemap are referenced in robots.txt and seem to have correct formating.
* Ensure sitemaps has one or more of the following content:
  * `www.sitemaps.org/schemas/sitemap/`
  * `<sitemapindex`

### Subscription Feed(s)

* Checks if there are one or more link element with any of the following types:
  * `application/rss+xml`
  * `application/atom+xml`
  * `application/feed+json`

Please note that you should probably not have a feed on every single page,
it is more logical to have on startpages or pages that list content of some sort.

### Security.txt

* Checks following urls:
  * `/.well-known/security.txt`
  * `/security.txt`
* Checks if any of the urls match:
  * Has no `html` in content
  * Has `contact:` in content
  * Has `expires:` in content


## How are rating being calculated?

This section has not been written yet.

## Read more

* https://securitytxt.org/
* https://well-known.dev/

## How to setup?

This section has not been written yet.

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)

## FAQ

No frequently asked questions yet :)

