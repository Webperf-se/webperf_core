# Getting Started with Docker Desktop

You can build an image and put in your local registry that has everything installed and good to go.

It's based on the [webbrowsers image set up by Sitespeed.io](https://github.com/sitespeedio/docker-browsers). Great work, thanks!

By default, `defaults/config.py`, gets copied used and should have sensible defaults that work well inside container.

If you add your own `config.py` it will take precedence when building the image.

You might also want to acquire your own copy of `data/IP2LOCATION-LITE-DB1.IPV6.BIN` before building the image,
it is required for GDPR related rating.

## How to setup

- Install Docker Desktop or other software that let's you run `docker` commands.
- [Set "Use Rosetta"](https://www.sitespeed.io/documentation/sitespeed.io/docker/#running-on-mac-m1-arm) if on Mac with ARM.
- Build the image using command in [docker/build.ps1](../docker/build.ps1) or by running the ps1-script in PowerShell. This takes a while.
- _Option 1:_ Start container using command in [docker/run.ps1](../docker/run.ps1) or by running the ps1-script in PowerShell.
- _Option 2:_ Build the image using command in [docker/run-with-mounted-folder.ps1](../docker/run-with-mounted-folder.ps1) or by running the ps1-script in PowerShell - this allows for writing report files to folder on host machine.
- When container is running and you are at bash you can run `python default.py -h` and start tests according to the documentation - all dependencies are already set up in the image.

## Regression test

The first version of the test only checks if image can build.

## Known issues

Lighthouse tests sometimes fail reporting NO_NAVSTART - retrying usually works. Seems to be a somewhat often reported issue with Chrome/Lighthouse and Docker.
