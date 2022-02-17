# Energy Efficiency
[![Regression Test - Google Lighthouse Based Test(s)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-google-lighthouse-based.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-google-lighthouse-based.yml)

Aim for this test is to start discussion regarding website impact on climate and environment.
It is not perfect but hopefully a start.

## What is being tested?

We are giving websites a relative rating depending on the impact they would have _IF_ they had the same visitor count and technical solution.
We are doing this by taking the weight of the url in KiB and calculating a value from this.
We then compare that value with a reference values and gives you a rating.
The reference values represents the percentile for all urls checked by Webperf.se.
This is updated manually and you can see when it was done latet by looking at the  date in top of [/tests/energy_efficiency_carbon_percentiles.py](../../tests/energy_efficiency_carbon_percentiles.py)).

If you know any other way we could automatically compare impact on climate and environment a certain url has, *PLEASE* let us know :)

## How are rating being calculated?

This section has not been written yet.

## Read more

* https://www.websitecarbon.com/
* https://www.thegreenwebfoundation.org/

## How to setup?

This test is using Google LightHouse in the background
so please follow instructions on page about [Google Lighthouse Based Test](./google-lighthouse-based.md)

## FAQ

No frequently asked questions yet :)

