# Tracking & Integrity
[![Regression Test - Tracking & Integrity](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-tracking.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-tracking.yml)

This test is aiming to improve user pricacy and integrity.


## What is being tested?

### Cookies

In this section we determin if the use of cookies are done a secure and none tracking manner.
We are doing this by:
* Check if and how many cookies that is persistant more then 1 year without revisit
* Check if and how many cookies that is persistant more then 9 months without revisit
* Check if and how many cookies that is persistant more then 6 months without revisit
* Check if and how many cookies that is persistant more then 3 months without revisit
* Check if and how many cookies that are not requiring a secure context (this make it possible to leak information)
* Check if and how many thirdpart cookies that are being set just by visiting url

All of above is considered bad behaivor and will result in a lower rating.


### GDPR and Schrems

In this section of the test we determin the use of none GDPR compliant request.
Currently this is done by guessing the origin country of every request IP.
We use IP2Location for this guessing, please note that depending on where you run this test from you may get different results.
If possible you should run this test from a EU country for the most reliable result.

Current EU countries are considered compliant by the test:
* Belgium
* Bulgaria
* Czechia
* Denmark
* Germany
* Estonia
* Ireland
* Greece
* Spain
* France
* Croatia
* Italy
* Cyprus
* Latvia
* Lithuania
* Luxembourg
* Hungary
* Malta
* Netherlands
* Austria
* Poland
* Portugal
* Romania
* Slovenia
* Slovakia
* Finland
* Sweden

In addition to above EU countries we also consider following countries complaint.
They orginally comes from: https://ec.europa.eu/info/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en

* Norway
* Liechtenstein
* Iceland
* Andorra
* Argentina
* Canada
* Faroe Islands
* Guernsey
* Israel
* Isle of Man
* Japan
* Jersey
* New Zealand
* Switzerland
* Uruguay
* South Korea
* United Kingdom
* Åland Islands


### Tracking

In this section of the test we determin the use of trackers.
We are using 2 different methods for this.
* Number of request that match the block list project list for trackers ( https://blocklistproject.github.io/Lists/alt-version/tracking-nl.txt ).
* Known javascript variablenames and filenames.

A url are allowed to use 2 tracking requests/references without impacting rating.
For all found trackers above that the rating will get lower and lower.
Please note that this section is relative to the number of none tracking request done by the url.

### Fingerprinting/Identifying technique

In this section of the test we determin the use of fingerprinting/identifying technique.
We are currently only using one method for this.
* Number of request that match the Disconnect list for fingerprinting domains ( We use `FingerprintingInvasive` and `FingerprintingGeneral` section of the file ).

### Advertising

In this section of the test we determin the use of advertising requests.
We are currently only using one method for this.
* Number of request that match the block list project list for ads ( https://blocklistproject.github.io/Lists/alt-version/ads-nl.txt ).

A url are allowed to use 2 advertising requests without impacting rating.
For all found advertising requests above that the rating will get lower and lower.
Please note that this section is relative to the number of none advertising request done by the url.

## How are rating being calculated?

This section has not been written yet.

## Read more

* https://pagexray-eu.fouanalytics.com


## How to setup?

### Prerequirements

* Fork this repository
* Download latest IP2Location Lite IPv6 database (`IP2LOCATION-LITE-DB1.IPV6.BIN`), can be found here: https://pypi.org/project/IP2Location/

### Setup with GitHub Actions

* Follow [general github action setup steps for this repository](../getting-started-github-actions.md).
* Upload `IP2LOCATION-LITE-DB1.IPV6.BIN` to a public accessable address.
* Add secret key with name `IP2LOCATION_DOWNLOAD_URL` under `Settings > Security > Secrets > Actions` with the location from previous step.

### Setup Locally

* Follow [general local setup steps for this repository](../getting-started-local.md)
* Place `IP2LOCATION-LITE-DB1.IPV6.BIN` file in a folder called "data" in the WebPerf-core folder ( data/IP2LOCATION-LITE-DB1.IPV6.BIN )
* Download https://blocklistproject.github.io/Lists/alt-version/ads-nl.txt and place it and name it to: `data/blocklistproject-ads-nl.txt`
* Download https://blocklistproject.github.io/Lists/alt-version/tracking-nl.txt and place it and name it to: `data/blocklistproject-tracking-nl.txt`
* Download https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/services.json and place it and name it to: `data/disconnect-services.json`
* Depending on your preference, follow below NPM package or Docker image steps below.

#### Using NPM package

* Download and install Node.js (v1 version 14.x)
* Download and install Google Chrome browser
* Download Geckodriver and place it in the root folder of this repo, [Geckodriver Download](https://github.com/mozilla/geckodriver/releases/):
  * [Linux x64](https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz)
  * [Windows x64](https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-win64.zip)
* Install SiteSpeed NPM package ( `npm install sitespeed.io` )
* Set `sitespeed_use_docker = False` in your `config.py`

##### Windows Specific

* Allow node to connect through Windows firewall

#### Using Docker image

* Make sure Docker command is globally accessible on your system.
* Set `sitespeed_use_docker = True` in your `config.py`


## FAQ

No frequently asked questions yet :)
