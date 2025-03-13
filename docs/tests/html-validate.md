# HTML

This test is validating all used HTML on the url specified. Making use of the [html-validate](https://html-validate.org/)

## Differences compared to vanilla html-validate
We are using  
* the built-in preset: ``--preset standard``
* sitespeed to visit the website
* sitespeed's HAR file to identify HTML files used during the visit
* all files whose mimetype contains 'html'

## How are rating being calculated?

We are calculating rating based on:
- Number of different error types
- Number of total number of errors

we are then combining the results.

Math used are:
- `rating_number_of_error_types = 5.0 - (number_of_error_types / 5.0)`
- `rating_number_of_errors = 5.0 - ((number_of_errors / 2.0) / 5.0)`

As always, minimum rating are 1.0.

## Read more

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

##### Windows Specific

* Allow node to connect through Windows firewall

#### Using Docker image

* Make sure Docker command is globally accessible on your system.
* Set [tests.sitespeed.docker.use](../settings-json.md) to `true` in your `settings.json`

## FAQ

No frequently asked questions yet :)
