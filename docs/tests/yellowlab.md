# Frontend quality against Yellow Lab Tools
[![Regression Test - Quality on frontend (Yellow Lab Tools) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-ylt.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-ylt.yml)

We use YellowLab Tools for this test and convert their rating 1-100 to our rating 1-5.
We group every rating into:
* Overall (other)
* Integrity & Security
* Performance
* Standards

## Read more

* https://yellowlab.tools/

## How to setup?

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)

#### Using NPM package

##### On Linux:
* Download and install Node.js (version 20.x)
* Download and install node-gyp `npm install -g node-gyp`
* Setup libjpeg and fontconfig `sudo apt-get install libjpeg-dev libfontconfig`
* Install NPM packages ( `npm install --omit=dev` )

##### On Windows:
* Download and install Node.js (version 20.x)
* Install NPM packages ( `npm install --omit=dev` )

## FAQ

No frequently asked questions yet :)

