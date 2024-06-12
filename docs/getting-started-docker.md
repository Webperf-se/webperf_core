# Getting Started with Docker Desktop

You can build an image and put in your local registry that has everything installed and good to go.

It's based on the [image set up by Sitespeed.io](https://github.com/sitespeedio/sitespeed.io). Great work, thanks!

By default, [defaults/settings.json](settings-json.md), gets copied used and should have sensible defaults that work well inside container.

If you add your own [settings.json](settings-json.md) it will take precedence when building the image.

You might also want to acquire your own copy of `data/IP2LOCATION-LITE-DB1.IPV6.BIN` before building the image,
it is required for GDPR related rating.

## How to setup

- Install Docker Desktop or other software that let's you run `docker` commands.
- [Set "Use Rosetta"](https://www.sitespeed.io/documentation/sitespeed.io/docker/#running-on-mac-m1-arm) if on Mac with ARM.
- Build the image using command in [docker/build.ps1](../docker/build.ps1) or by running the ps1-script in PowerShell. This takes a while.
- _Option 1:_ Start container using command in [docker/run.ps1](../docker/run.ps1) or by running the ps1-script in PowerShell.
- _Option 2:_ Build the image using command in [docker/run-with-mounted-folder.ps1](../docker/run-with-mounted-folder.ps1) or by running the ps1-script in PowerShell - this allows for writing report files to folder on host machine.
- When container is running and you are at bash you can run `python default.py -h` and start tests according to the documentation - all dependencies are already set up in the image.

## Change settings / configuration
Easiest and fastest way is to use the `--setting` command that only change setting for current run.
You can list all available settings by writing `--setting ?`.

If you want to change your settings in a more permanent way you can do so by creating a settings.json file,
read more about it at [settings.json](settings-json.md).

## Known issues

Lighthouse tests sometimes fail reporting NO_NAVSTART - retrying usually works. Seems to be a somewhat often reported issue with Chrome/Lighthouse and Docker.

## Advanced setup

You can base your own image on `webperfse/webperf-core` or your own local version of it. It can be convenient to have your repo or folder outside of the original repo.

For example you can hold your own copies of [settings.json](settings-json.md) and `sites.json` in this separate folder.

This can makes it easier to update and sync the original GitHub repository without having to re-apply your own changes.

Put a `Dockerfile` in the new folder. Content example:

```
FROM webperfse/webperf-core:latest

COPY settings.json /usr/src/runner/settings.json
COPY sites.json /usr/src/runner/sites.json
```

Build it from your new folder:


```
docker build -t "my-own-webperf-runner:latest" .
```

Run it:

```
docker run -it --cap-add=SYS_ADMIN --cpus=".9" --shm-size=3g --rm my-own-webperf-runner:latest bash
```

Now you are at bash but with separate [settings.json](settings-json.md) and `sites.json` files _burnt into_ the image.

If you have PowerShell I recommend you also copy the _*.ps1_-files from the _./docker_ folder and adjust them to fit the custom image.