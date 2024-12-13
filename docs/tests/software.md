# Software
[![Regression Test - Software](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-software.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-software.yml)

As all other test in webperf-core this test main focus is to improve knowleage and to encourage small and steady improvements.
This test also has a general information section that aims to give information on software and tech usage at a overview level so you can see for example how common tech X is.

## What is being tested?

Following areas are determined from public accessible information by visting website, like:
* HTTP Headers (Including but not limited to: URL and cookies)
* HTML Markup
* SVG Markup
* Metadata in resources

Test can be set to a none stealth mode, resulting in more request to commonly used paths of CMS and other technology like Matomo.
Default is to use stealth mode (read: visting website just like a human).

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
Information found in none stealth mode (DON'T use if not approved to do so by website owners):
- img.app (used image editing software)
- img.os (used operating system when editing software)
- img.device (device used to take the image)
- app (software used by this website)

We also tell you if we find any:
- img.person (personal information, if this is by accident you should remove it)
- img.location (location information, if this is by accident you should remove it)

### Languages

This section tries to identify what languages are used for website.

### Metadata

This section tries to identify what known metadata tags are used for website.

## How are rating being calculated?

Information found in stealth mode (default mode):
- operating system
- webserver
- cms
- javascript libraries

If we can find software name, version and github reference for software being used we will look up your version against that github repository and see IF and how many versions you are behind.

If we have software name and version but not a github reference we will try match software name against a small list
of known software names and aliases. If match is found we will try to see IF and how many versions you are behind.

For javascript libraries, some webserver and operating system we will also do a CVE search to see
if we can find any publicly known vurnabilities matching your used software name and version.
Please note that we don't know if YOU are vurnable, just that the version of the software you are using has a reported vurnability.
The security implications and IF you are vurnable can be read more about in the provided links.

We consider it best practise to always use a version without CVE reported and highly recommend you to upgrade.
Generally you should always strive to have latest version as it will generally make it easier to upgrade
IF/WHEN someone has found a security issue in a software.

We will rate every occurance of:
- CVE related to a software version you use
- How many software versions you are behind latest version
- If you are simultaneously using different versions of the same software
- If you are leaking name and version of operting system, webserver or cms

## How do we find software name and version?

As you can read above we determine this from public accessible information by visting website (as any normal human would do).
We are then looking at the responses your website send.
This test have the ability to look at:
* HTML markup (read: page content and metadata)
* URLs (read: for example path and querystring used)
* HTTP Response Headers (read: for example a specific `SERVER` header commonly used to tell what webserver is used)
* SVG Markup (read: for example generator metadata)
* Metadata in images (read: for example generator metadata)

If you are not using your own `software-rules.json` file in `data` folder you will be using the `defaults/software-rules.json` file
provided with this test.
With this file you can use regular expression to look at:
* HTML markup
* URLs
* HTTP Response Headers
and tell this test how a regular expression match should be interpreted.
For every rule in the file you can specify:
* category (js/os/webserver/cms/tech) with a property called `category`
* name (either with regular expression group name or a property called `name`)
* version (either with regular expression group name or a property called `version`)
* precision (tells how precise the information is and how confident you are in the match)

## Read more

TODO: Add links to blogs and articles showing how to remove info regarding what website are using.

## How to setup?

### Prerequirements

* Fork this repository


### Setup with GitHub Actions

* Follow [general github action setup steps for this repository](../getting-started-github-actions.md).
* Currently GitHub Actions version is not searching github advisory database (Reason for this is the amount of data)

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)
* We recommend you to make use `software_use_stealth` is set to `True`, change this to `False` at your own risk.
* It is highly recommended to set `cache_when_possible` to `True` and to set `cache_time_delta` to
* It is highly recommended to set `cache_time_delta` to at least 12 hours (Fail to do so may result in banning of service like github).
* If you want to get more detailed information, please set `general.review.details` to `True`.
* Depending on your preference, follow below NPM package or Docker image steps below.

#### Using NPM package

* Download and install Node.js (version 20.x)
* Download and install Google Chrome browser
* Install NPM packages ( `npm install --omit=dev` )
* Set `sitespeed_use_docker = False` in your `config.py`

##### Windows Specific

* Allow node to connect through Windows firewall

#### Using Docker image

* Make sure Docker command is globally accessible on your system.
* Set `sitespeed_use_docker = True` in your `config.py`


## FAQ

### How to update software-full.json?

Make sure your system has access to following addresses:
* Access to https://www.cvedetails.com/*
* Access to https://nginx.org/*
* Access to https://httpd.apache.org/*
* Access to https://www.cve.org/*
* Access to https://learn.microsoft.com/*
* Access to https://svn.apache.org/*
* Access to https://api.github.com/*

Fork https://github.com/github/advisory-database and set `software_github_adadvisory_database_path` variable in `config.py` to the path of that folder.

Make sure you add a valid GitHub API key in your `config.py`.

run `update_software.py`
