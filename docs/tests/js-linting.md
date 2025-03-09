# Javascript (JS) Validation
This test is a JS linting test developed by the Webperf community.

## How are rating being calculated?
*To be documented*

As always, minimum rating are 1.0.

## How to setup?

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)
* It is highly recommended to set [general.cache.use](../settings-json.md) to `true`
* It is highly recommended to set [general.cache.max-age](../settings-json.md) to at least 12 hours (Fail to do so may result in banning of service like github).
* Depending on your preference, follow below NPM package or Docker image steps below.

#### Using NPM package

* Download and install Node.js (version 20.x)
* Download and install Google Chrome browser
* Install NPM packages ( `npm install --omit=dev` )
* Set [tests.sitespeed.docker.use](../settings-json.md) to `false` in your `settings.json`

##### Windows Specific

* Allow node to connect through Windows firewall

#### Using Docker image

* Make sure Docker command is globally accessible on your system.
* Set [tests.sitespeed.docker.use](../settings-json.md) to `true` in your `settings.json`

## FAQ

No frequently asked questions yet :)