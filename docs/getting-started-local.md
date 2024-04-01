# Getting Started on Local machine / Virtual Machine

This method is best if you want to test/verify private websites like acceptance test environments,
it is also best/fastest when wanting to contribute with new tests, translations or other stuff.

## How to setup
- [Download and install Python 3.10 (or later)](https://www.python.org/downloads/) if you don't have it installed already.
- [Fork webperf-core repository](https://github.com/Webperf-se/webperf_core/fork?fragment=1) or [download webperf-core](https://github.com/Webperf-se/webperf_core/archive/refs/heads/main.zip) to your machine.
- Copy `SAMPLE-config.py` to new file named `config.py`, [read more about config.py here](config-py.md)
- Open the Terminal (Macos & Linux) or Command Prompt (Windows).
- Navigate to where you downloaded (and unpacked) the source code. If you don’t know how to navigate in Terminal/CMD, read the [Windows guide](https://www.digitalcitizen.life/command-prompt-how-use-basic-commands) or [under Step 5 for Mac / Linux](https://computers.tutsplus.com/tutorials/navigating-the-terminal-a-gentle-introduction--mac-3855).
- Update Python Package manager by typing following and hit Enter: `python -m pip install --upgrade pip`
- Install required Python packages by typing following and hit Enter: `pip install -r requirements.txt`
- Validate that core functionality is working by typing following and hit Enter `python default.py -h`
- If the output looks something like example in [options and arguments](getting-started.md#options-and-arguments) you have successfully setup the general parts of webperf-core.
- Please look at/return to the [specific test](tests/README.md) you want to run to make sure it doesn't require more steps.


