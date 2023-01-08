# Software (Alpha)
[![Regression Test - Software (Alpha)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-software.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-software.yml)

This test is aiming to follow software usage and improve software required for website.


## What is being tested?

Following areas are determined from public accessible information by visting website, like:
* HTTP Headers (Including but not limited to: URL and cookies)
* HTML Markup
* SVG Markup
* Metadata in resources

Test can be set to a none stealth mode, resulting in more request to commonly used paths of CMS and other technology like Matomo.

### CMS
This section tries to identify what CMS (if any) is used for website.

### WebServer
This section tries to identify what webserver is used for website.

### Operating System
This section tries to identify what webserver is used for website.

### Analytics
This section tries to identify analytics (if any) is used for website.
Currently this only look a Matomo as that is most commonly used analytics that can be installed on-premise.
Analytics that are only provided by ONE provider are not interesting to follow in this test.

### Technology
This section tries to identify what technology is used for website, like PHP, Java and more.

### JS Libraries
This section tries to identify what javascript libraries are used for website.

### CSS Libraries
This section tries to identify what CSS libraries are used for website.

### Image formats

This section tries to identify what image formats used for website.

### Languages

This section tries to identify what languages are used for website.

### Metadata

This section tries to identify what known metadata tags are used for website.

## How are rating being calculated?

Information found in stealth mode (default mode):
- operating system
- webserver
- cms

If name and version is leaked a security rating of 2.0 is given.
If only name is leaked a security rating of 4.0 is given.

Information found in none stealth mode:
- img.app (used image editing software)
- img.os (used operating system when editing software)
- img.device (device used to take the image)
- app (software used by this website)
- app.not-latest (software used by this website is found to not use latest version)
- app.security-issues (software used by this website has known security issues)

If name or version is leaked a security rating of 4.0 is given.
If we can determin you are not using latest version of app and it is not known for security issue a security rating of 4.0 is given.
If we can determin you are using a version with known security issues a security rating of 1.0 is given.

We also tell you if we find any:
- img.person (personal information, if this is by accident you should remove it)
- img.location (location information, if this is by accident you should remove it)

## Read more

TODO: Add links to blogs and articles showing how to remove info regarding what website are using.

## How to setup?

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

* Follow [general github action setup steps for this repository](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)
* Depending on your preference, follow below NPM package or Docker image steps below.

#### Using NPM package

* Download and install Node.js (v1 version 14.x)
* Download and install Google Chrome browser
* Install SiteSpeed NPM package ( `npm install sitespeed.io` )
* Set `sitespeed_use_docker = False` in your `config.py`

##### Windows Specific

* Allow node to connect through Windows firewall

#### Using Docker image

* Make sure Docker command is globally accessible on your system.
* Set `sitespeed_use_docker = True` in your `config.py`


## FAQ

No frequently asked questions yet :)
