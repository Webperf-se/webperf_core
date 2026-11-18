# Getting Started on Local machine

This method is best if you want to test/verify private websites like acceptance test environments,
it is also best/fastest when wanting to contribute with new tests, translations or other stuff.

## How to setup
- [Download and install Python 3.12 (or later)](https://www.python.org/downloads/) if you don't have it installed already.
- [Fork webperf-core repository](https://github.com/Webperf-se/webperf_core/fork?fragment=1) or [download webperf-core](https://github.com/Webperf-se/webperf_core/archive/refs/heads/main.zip) to your machine.
- Open the Terminal (Macos & Linux) or Command Prompt (Windows).
- Navigate to where you downloaded (and unpacked) the source code. If you don’t know how to navigate in Terminal/CMD, read the [Windows guide](https://www.digitalcitizen.life/command-prompt-how-use-basic-commands) or [under Step 5 for Mac / Linux](https://computers.tutsplus.com/tutorials/navigating-the-terminal-a-gentle-introduction--mac-3855).
- Update Python Package manager by typing following and hit Enter: `python -m pip install --upgrade pip`
- Install required Python packages by typing following and hit Enter: `pip install -r requirements.txt`
- Download and install Node.js 24.22.1 or later. Earlier 24.x versions contain a Brotli decoder flaw that can allow remote code execution when a response from a tested website is decompressed ([CVE-2026-111497, Node.js security release October 2026](https://nodejs.org/en/blog/vulnerability/october-2026-security-releases)).
- Download and install Google Chrome browser
* Download and install Mozilla Firefox
- Install required npm packages by typing following and hit Enter: `npm install --omit=dev` (don't use `sudo`, see [Chrome or Firefox doesn't start](#chrome-or-firefox-doesnt-start-missing-browser-drivers))
- Validate that core functionality is working by typing following and hit Enter `python default.py -h`
- If the output looks something like example in [options and arguments](getting-started.md#options-and-arguments) you have successfully setup the general parts of webperf-core.
- Please look at/return to the [specific test](tests/README.md) you want to run to make sure it doesn't require more steps.

## Change settings / configuration
Easiest and fastest way is to use the `--setting` command that only change setting for current run.
You can list all available settings by writing `--setting ?`.

If you want to change your settings in a more permanent way you can do so by creating a settings.json file,
read more about it at [settings.json](settings-json.md).

## Node.js version requirement (engine-strict)
The repository contains an `.npmrc` with `engine-strict=true`, and `package.json` requires Node.js `>=24.22.1`. If your Node.js is older, `npm install` stops with an `EBADENGINE` error instead of only printing a warning. Upgrade Node.js and run the command again.

This is on purpose. webperf-core analyzes websites you don't control, and some of the tests run Node.js code on responses from those websites. Node.js before 24.22.1 has a flaw in its Brotli decoder ([CVE-2026-111497](https://nodejs.org/en/blog/vulnerability/october-2026-security-releases)) that can lead to remote code execution on your machine. On a local setup nothing separates that from your files and credentials, which is why this is checked when installing.

Things to know:
- The check only runs when you run `npm install`. If you installed before upgrading the requirement, check `node --version` yourself.
- Don't work around it with `--engine-strict=false` unless you run on a machine where it doesn't matter if it is compromised.
- The Docker image (`webperfse/webperf-core`) ships with a patched Node.js, but only from the release built after this change. Run `docker pull webperfse/webperf-core:latest` to be sure you have it.

## Chrome or Firefox doesn't start (missing browser drivers)
sitespeed.io needs a driver to control each browser. Chrome uses Chromedriver, Firefox uses Geckodriver and Edge uses Edgedriver. `npm install` doesn't download any of them. Each driver is downloaded into `node_modules` the first time a test starts that browser. If that download fails, the browser never starts and you get one of these symptoms:
- Chrome fails with `Could not start chrome with 3 tries`, followed by `No data to collect`.
- Firefox runs end after a few seconds without loading the page. Tests don't always stop with an error then. The HTTP test (21), for example, runs most of its checks in Firefox and finishes much faster than usual, and it reports that every domain lacks TLS 1.2 and TLS 1.3 support.

The most common reasons the download fails are:
- `npm install` was run with `sudo`, so `node_modules` is owned by root and can't be written to when you run the tests as yourself. Take back ownership with `sudo chown -R "$(whoami)" node_modules` (macOS & Linux), and run `npm install` without `sudo` from now on.
- The machine has no internet access when the test runs, or a firewall blocks the download hosts. Chromedriver is downloaded from `storage.googleapis.com` and Geckodriver from `github.com`.

Download the drivers yourself after every `npm install`, so you see any error directly and don't depend on internet access when testing:

```
node node_modules/sitespeed.io/node_modules/@sitespeed.io/chromedriver/install.js
node node_modules/sitespeed.io/node_modules/@sitespeed.io/geckodriver/install.js
```

Add `edgedriver` the same way if you test with Edge. If a path doesn't exist, find where npm put the driver packages with:

```
find node_modules -path "*/@sitespeed.io/*driver/install.js"
```

If nothing is found, `npm install` didn't finish. Check the end of its output for an error.

### `npm install` fails with `EACCES` in `~/.npm`
If `npm install` stops with `EACCES: permission denied` (or `EEXIST`) on a path under `~/.npm/_cacache`, an earlier `npm` command was run with `sudo` and left root-owned files in your npm cache. Take back ownership and install again:

```
sudo chown -R "$(id -u):$(id -g)" ~/.npm
npm install --omit=dev
```

When `npm install` fails like this, `node_modules` can be left half updated, for example with an older sitespeed.io that doesn't match `package.json`. Always fix the error and install again before you run tests.

The Docker image already contains all drivers, so this section doesn't apply there.

## npm warns about "install scripts not yet covered by allowScripts"
Since version 11.16, npm lists packages whose install scripts nobody has approved. On npm 11 this is only a warning and the scripts still run. From npm 12 they are skipped, and `npm install` still finishes without an error.

The only install script webperf-core needs is puppeteer's. It downloads the Chrome that pa11y and webbkoll-backend use, into `~/.cache/puppeteer`. Without it, those tests fail because puppeteer can't find Chrome. puppeteer doesn't download its browser when a test starts, unlike the sitespeed.io drivers above. That's why `package.json` approves it in `allowScripts`. If your npm still lists puppeteer, update webperf-core, or download the browser yourself with:

```
node node_modules/puppeteer/install.mjs
```

You can ignore the other packages in the list:
- `sitespeed.io` and `tldjs` only download optional data when you ask for it with an environment variable or an npm setting.
- `usb`, `node-hid` and `@serialport/bindings-cpp` are for measuring power use with a USB meter, and `ssh2` and `cpu-features` for uploading results over SFTP. webperf-core uses neither.
- Other packages in the list are usually left over from an earlier install. `npm ls <package>` shows them as `extraneous`, and `npm prune` removes them.

To see which packages are not yet approved, run `npm approve-scripts --allow-scripts-pending`. It only lists them and doesn't change anything.
