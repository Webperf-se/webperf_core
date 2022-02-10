# Tracking & Integrity

This test is aiming to improve user pricacy and integrity.


## What is being tested?

### Cookies

### GDPR and Schrems

### Tracking

### Fingerprinting/Identifying technique

### Advertising

## How are rating being calculated?

## Read more

Links to other sources where you can test or read more

## FAQ

No frequently asked questions yet :)

## How to setup?

### Prerequirements

* Fork this repository
* Download latest IP2Location Lite IPv6 database (`IP2LOCATION-LITE-DB1.IPV6.BIN`), can be found here: https://pypi.org/project/IP2Location/

### Setup with GitHub Actions

* Follow [general github action setup steps for this repository](../getting-started-github-actions.md).
* Package `IP2LOCATION-LITE-DB1.IPV6.BIN` into a tar file `IP2LOCATION-LITE-DB1.IPV6.BIN.tar` and upload it to a public accessable address.
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
* Download Geckodriver and place it in the root folder of this repo ( for linux x64 you can use: https://github.com/mozilla/geckodriver/releases/download/v0.30.0/geckodriver-v0.30.0-linux64.tar.gz)
* Install SiteSpeed NPM package ( `npm install -g sitespeed.io` )
* Set `sitespeed_use_docker = False` in your `config.py`

#### Using Docker image

* Make sure Docker command is globally accessible on your system.
* Set `sitespeed_use_docker = True` in your `config.py`


