# Accessibility Statement
[![Regression Test - Accessibility Statement Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-a11y-statement.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-a11y-statement.yml)

Add small description of what this test is.

## What is being tested?

This test looks for and rates your accessibility statement.
This test is currently calibrated only for swedish.

It rates on many "shall" statements from the [Swedish Agency for Digital Government](https://digg.se/kunskap-och-stod/digital-tillganglighet/skapa-en-tillganglighetsredogorelse)

## How are rating being calculated?

We are calculating rating based on:
- IF we can find an accessibility statement.
- On what link depth we find the accessibility statement.
- IF we can find "helt förenlig", "delvis förenlig" or "inte förenlig"
- IF we can find valid/correct [notification function url to DIGG](https://www.digg.se/tdosanmalan)
- IF we can find unreasonably burdensome accommodation
- IF we can find evaluation method used to validate accessibility
- IF we can find when accessibility statement was updated and WHEN

## Read more

* https://digg.se/kunskap-och-stod/digital-tillganglighet/skapa-en-tillganglighetsredogorelse

## How to setup?

This section has not been written yet.

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)

## FAQ

No frequently asked questions yet :)

