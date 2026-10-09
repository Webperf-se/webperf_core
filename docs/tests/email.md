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

## Why is this test important?

This test main focus is to help you in the following areas for email handling: integrity, security and web standards.

For your organisation this means it will help you ensure
a stable (by making sure you have specified redundant services for email).
It will also ensure that your organisation can recieve emails independent
if the sender is using legacy (IPv4) or newer (IPv6) Information protocol.

It will also verify if your organisation allow receivers of emails to verify (By using SPF) if e-mail actually came from your organisation or if it was from someone pretending to be from your organisation.
It will also check what your organisation tell receiving email system it should do with email pretending
it is you (do nothing, mark it as spam OR block it).

It will also verify your organisations ability to receive Transport Layer Security (TLS) secure SMTP connections.
This is important because by default you can view emails as a postcard, everyone handling the email from you until it reaches the intended reciever can read all its content.
If both sending and receiving organisations support TLS (declared with MTA-STS) you have the ability to send your emails as postcards or inside a envelope with the benefit that none other then the sending and receiving email provider can view your email.
If it matches your usecases you can also force use of TLS for emails, meaning that if the sender is not supporting TLS the email will not be recieved.
One more possible benefit of using MTA-STS is that the sending party can verify if receiving party supports envelope (TLS) before sending email.
Please note that it is only encrypted (inside envelope) while in transport, as soon as it is delivered to the email provider it is open again for all eyes to see.

Final test on the security side of things it will test is if email related servers are in GDPR complaint countries or not.
If test is telling you that you are not compiant it means that
the email adress and any other potentially personal information MAY be intercepted by
other countries agencies.


## How are rating being calculated?

This test has its own logic, see [How ratings are calculated](../rating.md). It runs DNS lookups for the domain (with a leading `www.` removed) and creates one `Rating` per finding. All of them are added with `Rating.__add__`, so every category is the unweighted mean of the findings that set it. The code is in [tests/email_validator.py](../../tests/email_validator.py). `O` is overall, `S` security, `St` standards.

| Check | Condition | O | S | St |
|---|---|---|---|---|
| MX over IPv4 | 2 or more mail servers with A records | 5.0 | 5.0 | 5.0 |
| | Exactly 1 | 2.5 | 1.0 | 5.0 |
| | None | 1.0 | | 1.0 |
| MX over IPv6 | Same scale for AAAA records | | | |
| MX country | Every server IP in the EU or on the adequacy list: 5.0. Any elsewhere: 1.0 | 5.0 / 1.0 | 5.0 / 1.0 | |
| MTA-STS DNS | `_mta-sts` TXT record with `v=STSv1` present / missing | 5.0 / 1.0 | 5.0 / 1.0 | 5.0 / 1.0 |
| MTA-STS policy file | `mta-sts.txt` with version, mode, mx and max_age / present but incomplete / missing | 5.0 / 2.0 / 1.0 | 5.0 / 1.0 / 1.0 | 5.0 / 1.0 / 1.0 |
| MTA-STS mode | `enforce` adds nothing. `testing` or `none` / unknown value | 3.0 / 1.0 | 1.0 / 1.0 | 5.0 / 1.0 |
| SPF record | `v=spf1` TXT record found / missing | 5.0 / 1.0 | 5.0 / 1.0 | 5.0 / 1.0 |
| SPF `all` | `-all` / `~all` / `?all` / `+all` | 5.0 / 5.0 / 3.0 / 2.0 | 5.0 / 2.0 / 2.0 / 1.0 | 5.0 / 5.0 / 5.0 / 2.5 |
| SPF `ptr` | Used | 1.0 | | 1.0 |
| SPF syntax | Unknown term / double space | 1.0 / 1.5 | | 1.0 / 1.5 |
| SPF DNS lookups | 10 or more lookups through `include:` | 1.0 | | 1.0 |
| SPF country | `ip4:` and `ip6:` entries in the EU or adequacy list / elsewhere | 5.0 / 1.0 | 5.0 / 1.0 | |
| DMARC record | `v=DMARC1` TXT record found / missing | 5.0 / 1.0 | 5.0 / 1.0 | 5.0 / 1.0 |
| DMARC `p=` | `reject` / `quarantine` / `none` / missing or invalid | 5.0 / 4.0 / 3.0 / 1.0 | 5.0 / 4.0 / 1.0 / 1.0 | 5.0 / 5.0 / 5.0 / 1.0 |
| DMARC `sp=` | Same values as `p=`, or 3.0 when it only repeats `p=` | | | |
| DMARC `pct=` | 100 / below 100 | 5.0 / 3.0 | 5.0 / 1.0 | 5.0 |
| DMARC syntax | Per invalid tag 1.0, none 5.0. Per tag that only states a default value 3.0, none 5.0 | | | |

The SPF lookup limit is the only check that sets `rating_perf`: 10 or more lookups give performance 4.0 next to the 1.0 for overall and standards, because every `include:` costs the receiving mail server a DNS query and RFC 7208 stops evaluating at 10.

Two checks are off by default. With `tests.email.support.port25` set to `true` the test also connects to every IPv4 mail server on port 25 and rates "all servers answer" and "all servers offer STARTTLS" with 5.0 or 1.0 for overall and standards. With `tests.email.support.ipv6` as well, the same is done over IPv6. Most networks block outgoing port 25, which is why both are off.

DNS lookups go to the resolver in `general.dns.address`, 8.8.8.8 by default. A lookup that times out is treated as "no record" and rated 1.0, so run the test from a network that allows DNS to that address. A missing IP2Location database makes every country `unknown`, which counts as compliant, so the two country checks then give 5.0 for everyone. Review texts follow `general.language`; the points do not depend on language.

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


