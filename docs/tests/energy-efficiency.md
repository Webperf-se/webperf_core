# Energy Efficiency
[![Regression Test - Energy Efficiency Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-energy-efficiency.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-energy-efficiency.yml)

Aim for this test is to start discussion regarding website impact on climate and environment.
It is not perfect but hopefully a start.

## What is being tested?

We are giving websites a relative rating depending on the impact they would have _IF_ they had the same visitor count and technical solution.
We are doing this by taking the weight of the url in KiB and calculating a value from this.
We then compare that value with a reference values and gives you a rating.
The reference values represents the percentile for all urls checked by Webperf.se.
This is updated manually and you can see when it was done latet by looking at the  date in top of [/tests/energy_efficiency_carbon_percentiles.py](../../tests/energy_efficiency_carbon_percentiles.py).

If you know any other way we could automatically compare impact on climate and environment a certain url has, *PLEASE* let us know :)

## How are rating being calculated?

This section has not been written yet.

## Read more

* https://www.websitecarbon.com/
* https://www.thegreenwebfoundation.org/

## How to setup?

This test is using Sitespeed.io in the background
so please follow instructions on page about [Sitespeed.io Based Test](./sitespeed.md)

### How to update carbon percentile reference?

Below are the steps that you need to do to calculate a new carbon percentile reference file.
As you can read above, this are required if you want to have a up to date reference regarding carbon footprint.
It is also needed if you want to have your own reference to rate against, for example your own websites last year or your closes competition.

#### Create new baseline
You do this by running Energy efficiency against a list of all sites you want to compare against.
For example:
```
python default.py -i kommuner.webprf -t 22 -o data\carbon-references-kommuner.json
```

#### Calculate new percentiles
You now have a baseline to create your carbon percentiles from.
You do this by running `python default.py --update-carbon <file path>`.
We recommend running it as follows:
```
default.py --update-carbon data\carbon-references-kommuner.json
```

For webperf-core will now have updated `tests\energy_efficiency_carbon_percentiles.py` to use your new percentiles.

## FAQ

No frequently asked questions yet :)

