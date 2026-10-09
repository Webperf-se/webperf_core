# Getting Started with Docker Desktop

You can build an image and put in your local registry or use `webperfse/webperf-core`, both have all runtime dependencies installed and are good to go.

Image is based on the [image set up by Sitespeed.io](https://github.com/sitespeedio/sitespeed.io). Great work, thanks!

By default, [defaults/settings.json](settings-json.md), gets copied and used and should have sensible defaults that work well inside the container.

If you add your own [settings.json](settings-json.md) it will take precedence when building the image.

You might also want to acquire your own copy of `data/IP2LOCATION-LITE-DB1.IPV6.BIN` before building your image, it is required for the GDPR-related ratings.

## Use the public image with your custom files

You can base your own image on `webperfse/webperf-core` or your own local version of it. It can be convenient to have your repo or folder outside of the original repo.

For example you can hold your own copies of [settings.json](settings-json.md) and `defaults/sites.json` in this separate folder.

This can make it easier to update image tag, or sync the original GitHub repository without having to re-apply your own changes.

Put a `Dockerfile` in the new folder. Content example:

```
FROM webperfse/webperf-core:latest

COPY settings.json /usr/src/runner/settings.json
COPY defaults/sites.json /usr/src/runner/sites.json
```

Build it from your new folder:


```
docker build -t "my-own-webperf-runner:latest" .
```

When running, the `--shm-size` and `--cpus` parameters adjusts available resources for the container. The environment variable MAX_OLD_SPACE_SIZE is picked up by Node.js and should be set to give that runtime more memory to work with.

What to set is dependent on the host machine's resources and the complexity of the web sites you test. MAX_OLD_SPACE_SIZE should in all situations be set lower than `--shm-size`.

All mentioned parameters are standard Docker and Node.js settings. For the GitHub Action runner we use `--shm-size=4g -e MAX_OLD_SPACE_SIZE=3000` when regression testing the image.

This starts the container:

```
docker run -it --cpus="0.9" --shm-size=4g -e MAX_OLD_SPACE_SIZE=3000 --rm my-own-webperf-runner:latest bash
```

Now you are at bash but with separate [settings.json](settings-json.md) and `defaults/sites.json` files _burnt into_ the image.

If you have PowerShell we recommend you also copy the _*.ps1_-files from the _./docker_ folder and adjust them to fit the custom image.

## How to setup for building image locally

- Install Docker Desktop or other software that let's you run `docker` commands.
- [Set "Use Rosetta"](https://www.sitespeed.io/documentation/sitespeed.io/docker/#running-on-mac-m1-arm) if on Mac with ARM.
- Build the image using command in [docker/build.ps1](../docker/build.ps1) or by running the ps1-script in PowerShell. This takes a while.
- _Option 1:_ Start container using command in [docker/run.ps1](../docker/run.ps1) or by running the ps1-script in PowerShell.
- _Option 2:_ Build the image using command in [docker/run-with-mounted-folder.ps1](../docker/run-with-mounted-folder.ps1) or by running the ps1-script in PowerShell - this allows for writing report files to folder on host machine.
- When container is running and you are at bash you can run `python default.py -h` and start tests according to the documentation - all dependencies are already set up in the image.

## Run tests from the host without entering the container

You do not have to open a shell in the container. Mount a folder for input and output and pass the command on the command line. The image runs as the user `sitespeedio`, so the mounted folder must be writable for that user:

```
mkdir -p reports
chmod a+rwx reports
```

Put your sites in `reports/sites.csv`. The format is a header row followed by one site per row:

```
id,website
1,https://www.uni-bielefeld.de
2,https://www.uni-koeln.de
```

A file with one URL per line and no header also works; the row number is then used as id.

Run one test and write the result to the mounted folder:

```
docker run --rm --shm-size=4g -e MAX_OLD_SPACE_SIZE=3000 \
  -v "$PWD/reports:/usr/src/runner/reports" \
  webperfse/webperf-core:latest \
  python3 default.py -i reports/sites.csv -t 28 -o reports/test-28.json
```

Test numbers are comma separated, so `-t 2,28` runs both. Repeating `-t` only keeps the last one. A run with more than one test adds a combined entry with `type_of_test: -1` to the output, see [How ratings are calculated](rating.md). To get one file per test, loop over the tests instead:

```
for t in 2 9 18 21 22 23 24 25 26 27 28 29 30; do
  docker run --rm --shm-size=4g -e MAX_OLD_SPACE_SIZE=3000 \
    -v "$PWD/reports:/usr/src/runner/reports" \
    webperfse/webperf-core:latest \
    python3 default.py -i reports/sites.csv -t $t -o reports/test-$t.json \
    2>&1 | tee reports/test-$t.log
done
```

`tee` keeps the console output in a file next to the result. When a test fails for a site, the reason is printed there, and unhandled errors go to `failures.log`. That file is written to the working directory inside the container, `/usr/src/runner`, unless you point `general.failures-log` at the mounted folder: `-s general.failures-log=reports/failures.log`.

For long lists, `--is <n>` (input skip) and `--it <n>` (input take) select a slice of the input file, so you can run in batches and restart where you left off:

```
python3 default.py -i reports/sites.csv --is 100 --it 50 -t 28 -o reports/test-28-batch3.json
```

### What is in the output

The JSON output always contains the full `data` of every test, including every issue with its rule, severity and the pages it was found on. The settings `general.review.details` and `general.review.improve-only` only change the review texts in `report`, `report_sec` and the other report fields. You do not need to change them to get complete data.

### Tests with requirements outside the container

- Test 32 (DNS) starts the `zonemaster/cli` Docker image itself, so it needs a Docker daemon. It cannot run inside the container without mounting the Docker socket. Run it from the host instead, see [dns-zonemaster.md](tests/dns-zonemaster.md).
- Test 20 (Webbkoll) calls the public service at webbkoll.5july.net.
- Test 24 (Email) needs the IP2Location database file `data/IP2LOCATION-LITE-DB1.IPV6.BIN` for the GDPR part of its rating, see above.
- Test 31 (Privacy) needs a self-hosted Webbkoll backend, see [privacy.md](tests/privacy.md).

## Change settings / configuration

Easiest and fastest way is to use the `--setting` command that only change the setting for current run.
You can list all available settings by writing `--setting ?`.

If you want to change your settings in a more permanent way you can do so by creating a settings.json file. 
Read more about it at [settings.json](settings-json.md).

## Known issues

Lighthouse tests sometimes fail reporting NO_NAVSTART - retrying usually works. Seems to be a somewhat often reported issue with Chrome/Lighthouse and Docker.