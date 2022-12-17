# Website performance with Sitespeed.io
[![Regression Test - Performance (Sitespeed.io) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-sitespeed.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-sitespeed.yml)

Add small description of what this test is.

## What is being tested?

Currently we are only using the SpeedIndex metric from SiteSpeed.io (Expressed in ms).
You can read more about SpeedIndex at: https://www.sitespeed.io/documentation/sitespeed.io/metrics/#speed-index

After we get this value from SiteSpeed.io we remove 500 from it and do the following calculation:

`Rating = 5.0 - (speedindex_adjusted / 1000)`

## Read more

* https://www.sitespeed.io/documentation/sitespeed.io/


## How to setup?

This section has not been written yet.

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)

#### Using NPM package

On Linux:
* Update apt-get `sudo apt-get update -y` ( Not needed if you have latest version )
* Install image library `sudo apt-get install -y imagemagick libjpeg-dev xz-utils --no-install-recommends --force-yes`
* Upgrade PIP `python -m pip install --upgrade pip` ( Not needed if you have latest version )
* Install setuptools `python -m pip install --upgrade setuptools`
* Install ... `python -m pip install pyssim Pillow image`
* Install ffmpeg `sudo apt install ffmpeg`
* Download and install Node.js (v1 version 14.x)
* Download and install Google Chrome browser
* Install SiteSpeed NPM package ( `npm install sitespeed.io` )
* Set `sitespeed_use_docker = False` in your `config.py`

(You can always see [GitHub Actions SiteSpeed](../../.github/workflows/regression-test-sitespeed.yml) for all steps required line by line)

#### Using Docker image

* Make sure Docker command is globally accessible on your system.
* Set `sitespeed_use_docker = True` in your `config.py`

## FAQ

No frequently asked questions yet :)

