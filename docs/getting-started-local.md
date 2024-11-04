# Getting Started on Local machine

This method is best if you want to test/verify private websites like acceptance test environments,
it is also best/fastest when wanting to contribute with new tests, translations or other stuff.

## How to setup
- [Download and install Python 3.13 (or later)](https://www.python.org/downloads/) if you don't have it installed already.
- [Fork webperf-core repository](https://github.com/Webperf-se/webperf_core/fork?fragment=1) or [download webperf-core](https://github.com/Webperf-se/webperf_core/archive/refs/heads/main.zip) to your machine.
- Open the Terminal (Macos & Linux) or Command Prompt (Windows).
- Navigate to where you downloaded (and unpacked) the source code. If you don’t know how to navigate in Terminal/CMD, read the [Windows guide](https://www.digitalcitizen.life/command-prompt-how-use-basic-commands) or [under Step 5 for Mac / Linux](https://computers.tutsplus.com/tutorials/navigating-the-terminal-a-gentle-introduction--mac-3855).
- Update Python Package manager by typing following and hit Enter: `python -m pip install --upgrade pip`
- Install required Python packages by typing following and hit Enter: `pip install -r requirements.txt`
- Download and install Node.js (version 20.x)
- Download and install Google Chrome browser
* Download and install Mozilla Firefox
- Install required npm packages by typing following and hit Enter: `npm install --omit=dev`
- Validate that core functionality is working by typing following and hit Enter `python default.py -h`
- If the output looks something like example in [options and arguments](getting-started.md#options-and-arguments) you have successfully setup the general parts of webperf-core.
- Please look at/return to the [specific test](tests/README.md) you want to run to make sure it doesn't require more steps.

## Change settings / configuration
Easiest and fastest way is to use the `--setting` command that only change setting for current run.
You can list all available settings by writing `--setting ?`.

If you want to change your settings in a more permanent way you can do so by creating a settings.json file,
read more about it at [settings.json](settings-json.md).
