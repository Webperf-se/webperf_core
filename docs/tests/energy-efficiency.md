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

The rating is relative. It says how the page compares with the pages Webperf.se has measured, not whether the page is light in absolute terms. The code is in [tests/energy_efficiency.py](../../tests/energy_efficiency.py) and follows the model from [carbon-api-2-0](https://gitlab.com/wholegrain/carbon-api-2-0) by Wholegrain Digital.

1. The total transfer size of the page in bytes is taken from the sitespeed.io run.
2. The size is adjusted for returning visitors: 75 % of the bytes count in full, and 25 % count at 2 %, which gives 0.755 × bytes. The constants are `RETURNING_VISITOR_PERCENTAGE`, `FIRST_TIME_VIEWING_PERCENTAGE` and `PERCENTAGE_OF_DATA_LOADED_ON_SUBSEQUENT_LOAD`.
3. Energy is the adjusted bytes × 1.805 kWh per GiB (`KWG_PER_GB`).
4. CO2 is the energy × 475 g per kWh (`CARBON_PER_KWG_GRID`), a world average grid.
5. The CO2 value is compared with the 100 percentiles in [tests/energy_efficiency_carbon_percentiles.py](../../tests/energy_efficiency_carbon_percentiles.py). The first percentile the value is below gives a "cleaner than" figure between 0 and 99 %.
6. Rating is 5 × cleaner than / 100, rounded to two decimals. 95 % or better gives 5.0. Values below 1.0 are shown as 1.0, as for every rating.

Only `rating` is set. The review text says the CO2 in grams per page view, the percentile and the date the percentiles were generated.

Two things follow from this. A page that is cleaner than 60 % of the reference pages gets 3.0 whatever its absolute weight, and the same page gets a different rating when the reference changes. The reference shipped with webperf-core comes from Webperf.se's own lists, mostly Swedish public sector sites. If you test sites in another country or sector, generate your own reference as described below, otherwise you are comparing with Swedish municipalities.

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

