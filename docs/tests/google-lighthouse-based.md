# Google Lighthouse based Tests
[![Regression Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-google-lighthouse-based.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-google-lighthouse-based.yml)

This is a general page for the lighthouse test that are using Google Lighthouse in the background.

## How to setup?

This section has not been written yet.

### Prerequirements

* Fork this repository

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

This section has not been written yet.
* Follow [general local setup steps for this repository](../getting-started-local.md)

You can run this test by letting webperf-core call Google API:s (googleapis.com) or install a local version on your system.
Follow the instructions below depending on what you choose.

#### Using NPM package

Benefit of this option is that you can use it to test pre production urls like your AcceptanceTest environment.

* Download and install Node.js (version 24.x)
* Install NPM packages ( `npm install --omit=dev` )

## Lighthouse version

Lighthouse is not a direct dependency. It comes with `@sitespeed.io/plugin-lighthouse`, which pins it to an exact version (13.0.1 in plugin version 13.0.1, the latest release as of November 2026).

To run a newer Lighthouse than the plugin ships with, `package.json` has an npm override:

```json
"overrides": {
  "lighthouse": "13.5.0"
}
```

This is the only override in the repository and an exception to how dependencies are otherwise handled (exact versions of direct dependencies, updated through Dependabot). Keep the following in mind:

* `npm ls lighthouse` shows the version in use, marked `overridden`.
* Do not count on Dependabot to update the override. Raise it by hand.
* When `@sitespeed.io/plugin-lighthouse` ships a Lighthouse version equal to or newer than the override, remove the `overrides` block. Left in place it silently forces the older version.
* The plugin imports `lighthouse/core/config/lr-desktop-config.js` and `lr-mobile-config.js`, which are not part of Lighthouse's public API. Run the Lighthouse regression tests after changing the override.
* Overrides are an npm feature (npm 8.3 or later). Docker, the GitHub Actions workflows and the documented local setup all use npm. yarn and pnpm ignore the field and give you the plugin's own Lighthouse version.

## Read more

Links to other sources where you can test or read more
* https://web.dev/
* https://pagespeed.web.dev/


## FAQ

No frequently asked questions yet :)
