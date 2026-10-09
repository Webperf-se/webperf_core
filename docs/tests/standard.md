# Standard files
[![Regression Test - Standard files Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-standard-files.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-standard-files.yml)

This test checks the files a site is expected to serve at well known addresses: `robots.txt`, a sitemap, a subscription feed and `security.txt`. It runs as the sitespeed.io plugin [plugin-standard-files](https://github.com/Webperf-se/plugin-standard-files).

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

Each check is a rule with a fixed severity and category, defined in `RULES` in `lib/harAnalyzer.js` of the plugin. The score follows the issue based model in [How ratings are calculated](../rating.md): every category starts at 100, an `error` deducts 10 points, a `warning` 1 point, and the rating is the score divided by 20. `standard` sets `rating_stand`, `security` sets `rating_sec`, and `rating` is the average of the categories that have issues.

| Rule | Severity | Category | Fails when |
|---|---|---|---|
| `no-robots-txt` | error | standard | `/robots.txt` is missing, looks like HTML or has no `allow`, `disallow` or `user-agent` line |
| `no-sitemap-in-robots-txt` | error | standard | `robots.txt` has no `Sitemap:` line (or `robots.txt` itself failed) |
| `no-valid-sitemap-found` | error | standard | The `Sitemap:` lines point to nothing that can be read as a sitemap |
| `no-https-sitemap` | error | security | A sitemap lists `http://` URLs |
| `no-same-domain-sitemap` | warning | standard | A sitemap lists URLs on another domain |
| `no-duplicates-sitemap` | warning | standard | The same URL occurs more than once, or the same sitemap is referenced twice |
| `no-unknown-types-sitemap` | warning | standard | A sitemap mixes more than one kind of content, for example pages and images |
| `invalid-sitemap-too-large` | warning | standard | A sitemap has more than 50 000 URLs |
| `no-items-sitemap` | warning | standard | A sitemap, or all sitemaps together, has no URLs |
| `no-rss-feed` | warning | standard | The page has no `link` element of type RSS, Atom or JSON feed |
| `no-security-txt` | error | security | Neither `/.well-known/security.txt` nor `/security.txt` exists |
| `invalid-security-txt` | error | security | The file exists but is HTML or has neither `Contact:` nor `Expires:` |
| `no-security-txt-contact` | warning | security | The file has no `Contact:` line |
| `no-security-txt-expires` | warning | security | The file has no `Expires:` line |
| `no-network` | warning | technical | The site could not be fetched at all |

The `security.txt` rules are evaluated per address, so a missing file counts `no-security-txt` plus the three rules that follow from it, 13 points in `security`. If either address has a valid file, none of the four rules fail. A missing `robots.txt` costs 20 points in `standard` because `no-sitemap-in-robots-txt` follows from it, so a site with only `robots.txt` missing gets `rating_stand` 4.0.

`technical` has no rating field, so `no-network` only shows in the overall review.

## Read more

* https://securitytxt.org/
* https://well-known.dev/

## How to setup?

This test is using Sitespeed.io in the background
so please follow instructions on page about [Sitespeed.io Based Test](./sitespeed.md)

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)

