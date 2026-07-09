# Users' privacy test (self-hosted Webbkoll backend)

This test is the successor of test 20 (Webbkoll provided by 5july.net).
Instead of scraping the hosted Webbkoll website it calls a self-hosted
[webbkoll-backend](https://codeberg.org/marcusosterberg/webbkoll-backend)
service that visits your website with a real (headless Chromium) browser and
returns raw data as JSON. The rating is then calculated locally by webperf_core.

## What is being tested?

* HTTPS by default (final URL uses HTTPS, no mixed content, no outdated TLS version)
* Referrer Policy (HTTP header or meta element)
* Cookies (third party cookies, cookies living longer than a year, cookies missing the `Secure` attribute)
* Third party requests (number of third party domains and known tracker domains, matched against `data/blocklistproject-tracking-nl.txt`)
* HTTP headers (`Strict-Transport-Security`, `X-Content-Type-Options` and protection against embedding via `X-Frame-Options` or CSP `frame-ancestors`)

Note: deep Content-Security-Policy analysis is intentionally NOT part of this
test, that is covered by test 21 (HTTP & Network).

## How are rating being calculated?

Every section above starts at 5.0 in rating and penalties are subtracted per
finding (for example: no HTTPS gives 1.0 for the HTTPS section, a missing
referrer policy gives 3.0 for that section, known tracker domains subtract
at least 2.0 from the third party section). The total rating is the average
of all five sections. Lowest rating is as always 1.0.

## Read more

* https://codeberg.org/marcusosterberg/webbkoll-backend
* https://github.com/andersju/webbkoll

## How to setup?

### Prerequirements

* Fork this repository
* Run `npm install` (webbkoll-backend is an npm dependency of webperf_core,
  just like sitespeed.io and pa11y)

That is all. When you run the test, webperf_core automatically starts
webbkoll-backend from `node_modules` on `http://localhost:8100`
(if nothing is already listening there) and stops it again when done:

```bash
python default.py -t 31 -u https://webperf.se
```

### Using a shared/remote backend

If you prefer to run webbkoll-backend as a standalone service
(for example one shared instance for several worker machines),
point the test at it:

```bash
python default.py -t 31 -u https://webperf.se --setting webbkollapiurl=http://otherhost:8100
```

or set `tests.webbkoll.api-url` in your `settings.json`.
When a backend is already responding at the configured address it is used
as-is and nothing is started or stopped by webperf_core.

Note: the service has no access control, so do NOT expose it publicly,
run it on localhost or a private network.

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)

## FAQ

No frequently asked questions yet :)
