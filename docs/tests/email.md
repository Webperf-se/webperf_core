# Email (Beta)
[![Regression Test - Email (Beta)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-email.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-email.yml)

This test is aiming to improve stability, security pricacy for email handling.


## What is being tested?

### MX Support
In this section we determin support for receiving email over IPv4 and IPv6.
We also check if there are redundance setup so MX support is less vurnable to single point failure.
Today all of this is done by checking only DNS records.

### MTA-STS Support

In this section of the test we determin use of MTA-STS and how well the specification is followed.
We also test how the use is impacted on security.
Today all of this is done by checking DNS records and MTA-STS.txt file hosted by webserver.

### SPF Support

In this section of the test we determin use of SPF and how well the specification is followed.
We also test how the use is impacted on security and privacy.
Today all of this is done by checking only DNS records.

### GDPR and Schrems

In this section of the test we determin the use of none GDPR compliant server locations.
Currently this is done by guessing the server country of every server IP.
We use IP2Location for this guessing, please note that depending on where you run this test from you may get different results.
If possible you should run this test from a EU country for the most reliable result.

We currently check IP-addresses of MX and SPF (For SPF we also check IP-network if specified).
For IP-network we use only first and last IP-address of a IP-network, this is done because of performance reasons as IPv6 IP-networks can contain over 1000 IP-addresses.

Please view [GDPR and Schrems section under Tracking & Integrity](./tracking.md#gdpr-and-schrems) documentation for
current list of countries.

## How are rating being calculated?

This section has not been written yet.

## Read more

* https://pagexray-eu.fouanalytics.com

* [SMTP MTA Strict Transport Security (MTA-STS) RFC](https://www.rfc-editor.org/rfc/rfc8461)
* [Sender Policy Framework (SPF) RFC](https://www.rfc-editor.org/rfc/rfc7208)
* [Mail Routing and the domain system](https://www.rfc-editor.org/rfc/rfc974.html)
* [CRLF - MDN Web Docs Glossary](https://developer.mozilla.org/en-US/docs/Glossary/CRLF)

## How to setup?

### Prerequirements

* Fork this repository
* Download latest IP2Location Lite IPv6 database (`IP2LOCATION-LITE-DB1.IPV6.BIN`), can be found here: https://pypi.org/project/IP2Location/
* You are able to make DNS requests for the domains you test against

### Setup with GitHub Actions

* Follow [general github action setup steps for this repository](../getting-started-github-actions.md).
* Upload `IP2LOCATION-LITE-DB1.IPV6.BIN` to a public accessable address.
* Add secret key with name `IP2LOCATION_DOWNLOAD_URL` under `Settings > Security > Secrets > Actions` with the location from previous step.

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)
* Place `IP2LOCATION-LITE-DB1.IPV6.BIN` file in a folder called "data" in the WebPerf-core folder ( data/IP2LOCATION-LITE-DB1.IPV6.BIN )


## FAQ

No frequently asked questions yet :)
