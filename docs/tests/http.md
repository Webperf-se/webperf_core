# HTTP & Network
[![Regression Test - HTTP & Network](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-http.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-http.yml)

This test checks how the site is served over the network: the HTTP to HTTPS redirect and HSTS, which TLS and HTTP versions the server accepts, IPv4 and IPv6, Content Security Policy and Subresource Integrity. The code is in [tests/http_validator.py](../../tests/http_validator.py) with helpers in `helpers/tls_helper.py`, `helpers/csp_helper.py`, `helpers/sri_helper.py` and `helpers/http_header_helper.py`.


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

This test has its own logic, see [How ratings are calculated](../rating.md). Every sub check creates a `Rating` with points for one or more of overall, security and standards, and all of them are added with `Rating.__add__`. The result per category is the unweighted mean of every sub check that set that category. There are no weights, so a check that sets three categories counts once in each of them.

The checks run once per domain seen in the sitespeed.io run, third party domains included. A page that loads resources from ten domains is rated on all ten, so a slow TLS setup at a CDN lowers your rating. CSP and SRI are the exceptions: they are rated for the tested domain and its `www` twin only.

| Check | Condition | Overall | Security | Standards |
|---|---|---|---|---|
| HTTPS | Served over https / only http | 5.0 / 1.0 | 5.0 / 1.0 | 5.0 / 1.0 |
| Redirect to http | Any redirect to a plain http URL | 1.0 | 1.0 | |
| Redirect to https | http request redirected to https | 5.0 | 5.0 | |
| HSTS missing | No `Strict-Transport-Security` header (parent domain with `includeSubDomains` gives 5.0 / 4.99 instead) | 1.0 | 1.0 | 1.0 |
| HSTS, `max-age` 1 year or more | With `preload` directive, or on a domain other than the tested one | 5.0 | 5.0 | 5.0 |
| | On the tested domain without `preload` | 5.0 | 4.95 | 5.0 |
| HSTS, `max-age` 6 months to 1 year | | 4.5 | 4.0 | 5.0 |
| HSTS, `max-age` 1 to 6 months | | 4.0 | 3.0 | 5.0 |
| HSTS, `max-age` under 1 month | | 3.5 | 2.0 | 5.0 |
| HSTS without readable `max-age` | | 3.0 | 1.0 | 1.0 |
| HSTS invalidated | HSTS set but the site redirects to http or to another https domain | 1.5 | 1.5 | 1.5 |
| TLS 1.3 | Supported / not | 5.0 / 1.0 | 5.0 / 1.0 | 5.0 / 1.0 |
| TLS 1.2 | Supported / not | 5.0 / 1.0 | 5.0 / 1.0 | 5.0 / 1.0 |
| TLS 1.1 | Supported / not (supporting it is the failure) | 1.0 / 5.0 | 1.0 / 5.0 | |
| TLS 1.0 | Supported / not | 1.0 / 5.0 | 1.0 / 5.0 | |
| HTTP/1.1 | Supported / not | 5.0 / 1.0 | | 5.0 / 1.0 |
| HTTP/2 | Supported / not | 5.0 / 1.0 | | 5.0 / 1.0 |
| HTTP/3 | Supported / not | 5.0 / 1.0 | | 5.0 / 1.0 |
| IPv4 | A record / none | 5.0 / 1.0 | | 5.0 / 1.0 |
| IPv6 | AAAA record / none | 5.0 / 1.0 | | 5.0 / 1.0 |
| CSP missing | HTML page without a Content Security Policy | 1.0 | 1.0 | 1.0 |
| CSP present | See below | | | |
| SRI | External scripts and stylesheets all have `integrity` / some lack it / `integrity` errors | 5.0 / 1.0 / 3.0 | 5.0 / 1.0 | 5.0 / 1.0 / 3.0 |

The `max-age` limits are 31536000 seconds for one year, 15768000 for six months and 2628000 for one month, defined in `helpers/http_header_helper.py`.

A present CSP is rated per directive in `helpers/csp_helper.py` and the pieces are averaged into one rating before it is added, so the whole CSP counts once per domain while TLS counts four times. The main deductions: `*` or a scheme wildcard, `unsafe-inline` and `unsafe-eval`, `http:`, `ws:` and `ftp:` sources, deprecated directives, a policy set in a `meta` element with directives that `meta` does not support, and more than 15 listed domains. `'self'`, `'none'`, hashes and nonces score well. Each of `default-src`, `base-uri`, `object-src`, `frame-ancestors` and `form-action` gives 5.0 when present and 1.0 when missing.

A site that cannot be reached gets no rating at all.

Settings that change what is rated: `tests.http.csp-only` skips everything except CSP and SRI and is meant for the CSP recommendation described under FAQ. The `tests.http.csp-generate-*` settings only change the recommendation text. Nothing in this test depends on language or country.

## Read more

* https://www.ssllabs.com/ssltest/
* https://http3check.net/

## How to setup?

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)
* Set `general.cache.use` to `true` and `general.cache.max-age` to at least `720` (minutes, 12 hours) in your `settings.json`. Without the cache, repeated runs can get you blocked by services like GitHub.

#### Using NPM package

* Download and install Node.js (version 24.x)
* Download and install Google Chrome browser
* Download and install Mozilla Firefox browser
* Install NPM packages ( `npm install --omit=dev` )
* Keep `tests.sitespeed.docker.use` at `false` (the default) in your `settings.json`

##### Windows Specific

* Allow node to connect through Windows firewall

#### Using Docker image

* Make sure Docker command is globally accessible on your system.
* Set `tests.sitespeed.docker.use` to `true` in your `settings.json`, or pass `-s tests.sitespeed.docker.use=true`

## FAQ

### How to get CSP recommendation for website
Did you know you can get a CSP recommendation for all/part of your website?
Do the following and webperf_core will give a CSP recommendation for more than 1 page.
* Set `tests.http.csp-only` to `true` in your `settings.json`, or pass `-s tests.http.csp-only=true`
* Point webperf_core to your sitemap or your own list pages you want to test.

Example, below will take first 25 items from sitemap:
`python default.py -r -t 21 --input-take=25 -i https://nimbleinitiatives.com/sitemap.xml`
