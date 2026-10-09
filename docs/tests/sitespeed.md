# Website performance with Sitespeed.io
[![Regression Test - Performance (Sitespeed.io) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-sitespeed.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-sitespeed.yml)

This test measures how fast the page loads in a real browser, using [sitespeed.io](https://www.sitespeed.io/) and Browsertime, and rates the result on desktop and mobile. Every other sitespeed.io based test (2, 9, 25 to 30) shares the setup described on this page.

## What is being tested?

We will startup the URL specified with a normal browser for X iterations with different subtests.
You specify the number of iterations to use in your [settings.json file](../settings-json.md), 3 iterations or more are recommended to get most stable rating.
The subtests we use are:
* Desktop (Configured as: Laptop size, full network speed of the system)
* Mobile (Configured as: Mobile size, 3G Fast network speed)

For every subtest we are using following metrics are used:
* [SpeedIndex](https://docs.webpagetest.org/metrics/speedindex/)
* [TTFB (Time to First Byte)](https://web.dev/ttfb/)
* [TBT (Total Blocking Time)](https://web.dev/tbt/) [Alternative reference](https://developer.chrome.com/docs/lighthouse/performance/lighthouse-total-blocking-time/#how-lighthouse-determines-your-tbt-score)
* [FCP (First Contentful Paint)](https://web.dev/fcp/)
* [LCP (Largest Contentful Paint)](https://web.dev/lcp/)
* [CLS (Cumulative Layout Shift)](https://web.dev/cls/)
* FirstVisualChange
* VisualComplete85
* Load

The URL are only rated on "Desktop" and "Mobile", the others are only there to give you hints on what can improve.
We are using different values to rate the URL depending on it is for the subtest "Desktop" or "Mobile", you can read more about them below:

### Desktop rating metrics
For `SpeedIndex`, `FirstVisualChange`, `VisualComplete85` and `Load` you will get 5.0 points if you are at or below `500ms`, after that you will get penalty for every ms you are above.
For `CLS (Cumulative Layout Shift)` you will get 5.0 points if you are at or below `0.1ms`, 3.0 points if you are at or below `0.25ms`, else you will get 1.0.
For `LCP (Largest Contentful Paint)` you will get 5.0 points if you are at or below `500ms`, 3.0 points if you are at or below `1000ms`, else you will get 1.0.
For `FCP (First Contentful Paint)` you will get 5.0 points if you are at or below `1800ms`, 3.0 points if you are at or below `3000ms`, else you will get 1.0.
For `TBT (Total Blocking Time)` you will get 5.0 points if you are at or below `200ms`, 3.0 points if you are at or below `600ms`, else you will get 1.0.
For `TTFB (Time to First Byte)` you will get 5.0 points if you are at or below `250ms`, 3.0 points if you are at or below `450ms`, else you will get 1.0.

### Mobile rating metrics
For `SpeedIndex`, `FirstVisualChange`, `VisualComplete85` and `Load` you will get 5.0 points if you are at or below `1500ms`, after that you will get penalty for every ms you are above.
For `CLS (Cumulative Layout Shift)` you will get 5.0 points if you are at or below `0.1ms`, 3.0 points if you are at or below `0.25ms`, else you will get 1.0.
For `LCP (Largest Contentful Paint)` you will get 5.0 points if you are at or below `1500ms`, 3.0 points if you are at or below `2500ms`, else you will get 1.0.
For `FCP (First Contentful Paint)` you will get 5.0 points if you are at or below `1800ms`, 3.0 points if you are at or below `3000ms`, else you will get 1.0.
For `TBT (Total Blocking Time)` you will get 5.0 points if you are at or below `200ms`, 3.0 points if you are at or below `600ms`, else you will get 1.0.
For `TTFB (Time to First Byte)` you will get 5.0 points if you are at or below `800ms`, 3.0 points if you are at or below `1800ms`, else you will get 1.0.

## Read more

* https://www.sitespeed.io/documentation/sitespeed.io/


## How to setup?

sitespeed.io is installed from `package.json` and run from `node_modules`, or from its Docker image when `tests.sitespeed.docker.use` is `true`. The number of iterations is `tests.sitespeed.iterations` (default 2), the browser `tests.sitespeed.browser` (default `chrome`) and the timeout per run `tests.sitespeed.timeout` seconds. The Docker image `webperfse/webperf-core` has everything below installed.

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)

#### Using NPM package

##### On Linux:
* Update apt-get `sudo apt-get update -y` ( Not needed if you have latest version )
* Install image library `sudo apt-get install -y imagemagick libjpeg-dev xz-utils --no-install-recommends --force-yes`
* Upgrade PIP `python -m pip install --upgrade pip` ( Not needed if you have latest version )
* Install setuptools `python -m pip install --upgrade setuptools`
* Install ... `python -m pip install pyssim Pillow image`
* Install ffmpeg `sudo apt install ffmpeg`
* Download and install Node.js (version 24.x)
* Download and install Google Chrome browser
* Install NPM packages ( `npm install --omit=dev` )
* Keep `tests.sitespeed.docker.use` at `false` (the default) in your `settings.json`

(You can always see [GitHub Actions SiteSpeed](../../.github/workflows/regression-test-sitespeed.yml) for all steps required line by line)

##### On Windows:

* Upgrade PIP `python -m pip install --upgrade pip` ( Not needed if you have latest version )
* Install setuptools `python -m pip install --upgrade setuptools`
* Install ... `python -m pip install pyssim Pillow image`
* Download and Install ffmpeg `https://ffmpeg.org/download.html#build-windows`
* Download and install Node.js (version 20.x)
* Download and install Google Chrome browser
* Install NPM packages ( `npm install --omit=dev` )
* Keep `tests.sitespeed.docker.use` at `false` (the default) in your `settings.json`

#### Using Docker image

* Make sure Docker command is globally accessible on your system.
* Set `tests.sitespeed.docker.use` to `true` in your `settings.json`, or pass `-s tests.sitespeed.docker.use=true`

