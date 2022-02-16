# Getting Started on Local machine / Virtual Machine

This method is best if you want to test/verify private websites like acceptance test environments,
it is also best/fastest when wanting to contribute with new tests, translations or other stuff.

## How to setup
- [Download and install Python 3.8 (or later)](https://www.python.org/downloads/) if you don't have it installed already.
- [Fork webperf-core repository](https://github.com/Webperf-se/webperf_core/fork?fragment=1) or [download webperf-core](https://github.com/Webperf-se/webperf_core/archive/refs/heads/main.zip) to your machine.
- Open the Terminal (Macos & Linux) or Command Prompt (Windows).
- Navigate to where you downloaded (and unpacked) the source code. If you don’t know how to navigate in Terminal/CMD, read the [Windows guide](https://www.digitalcitizen.life/command-prompt-how-use-basic-commands) or [under Step 5 for Mac / Linux](https://computers.tutsplus.com/tutorials/navigating-the-terminal-a-gentle-introduction--mac-3855).
- Update Python Package manager by typing following and hit Enter: `python -m pip install --upgrade pip`
- Install required Python packages by typing following and hit Enter: `pip install -r requirements.txt`
- Validate that core functionality is working by typing following and hit Enter `python default -h`
- If the output looks something like example in [options and arguments](getting-started.md#options-and-arguments) you have successfully setup the general parts of webperf-core.
- Please look at/return to the [specific test](tests/README.md) you want to run to make sure it doesn't require more steps.


## Get started with webperf_core
Here are some suggestions on how to get started with the tests on your own computer. Actually, it is even easier to run the tests on a cloud environment such as [PythonAnywhere - $ 5 / month](https://www.pythonanywhere.com/?affiliate_id=0007e5c6) - then the technical environment is ready to just upload the files.

You download the code itself from [GitHub - webperf_core](https://github.com/Webperf-se/webperf_core) and place it in a good location on your computer.
### Adjust the source code
There are two files that you need to adjust:
* *SAMPLE-config.py* needs to be renamed to *config.py*
The reason for this is because if you download a new version of the code, your settings or data should not be overwritten by accident.

## Where to run?
Read of the many ways to run webperf-core by following one of the links below.

* [Locally](./getting-started-local.md)
* [GitHub Actions](./getting-started-github-actions.md)
* [PythonAnywhere.com](./getting-started-others.md)





## Running the code
You need to go through the following steps before you run the code:
1. If you do not have Python 3.8 or above installed, start with [downloading Python](https://www.python.org/downloads/) (which you can ignore if you run on [PythonAnywhere](https://www.pythonanywhere.com/?affiliate_id=0007e5c6)).
2. Open the Terminal (Macos & Linux) or Command Prompt (Windows).
3. Navigate to where you downloaded (and unpacked) the source code. If you don’t know how to navigate in Terminal/CMD, read the [Windows guide](https://www.digitalcitizen.life/command-prompt-how-use-basic-commands) or [under Step 5 for Mac / Linux](https://computers.tutsplus.com/tutorials/navigating-the-terminal-a-gentle-introduction--mac-3855).
4. Type the following command and hit Enter:  
*pip install -r requirements.txt*  
Then some Python extensions will be installed.
5. Start the program with the following command and press Enter:  
*python default.py -u https://webperf.se*

If that command results in errors, you can try addressing **Python3** instead:  
*python3 default.py -u https://webperf.se*

Now it will begin testing.

### Options and arguments
|Argument|What happens|
|---|---|
| -h/--help | Help information on how to use script |
| -u/--url <site url> | website url to test against |
| -t/--test <test number> | run ONE test (use ? to list available tests) |
| -r/--review | show reviews in terminal |
| -i/--input <file path> | input file path (.json/.sqlite) |
| --input-skip <number> | number of items to skip |
| --input-take <number> | number of items to take |
| -o/--output <file path> | output file path (.json/.csv/.sql/.sqlite) |
| -a/--addUrl <site url> | website url (required in compination with -i/--input) |
| -d/--deleteUrl <site url> | website url (required in compination with -i/--input) |
| -L/--language <lang code> | language used for output(en = default/sv) |

For instance, if you'd like to test *https://yourwebsite.com*, get the output as a JSON-file named *my-report.json* and also see the reviews in the prompt the statement is as follows:  
```python default.py -u https://yourwebsite.com -o my-report.json -r```

If you want to test multiple URL:s and get the results as a CSV-file, then edit the file *sites.json* and run the following in your terminal to get the result in a file of your chosing, for instance *results.csv* in the application root:  
```python default.py -i sites.json -o results.csv```

The file *sites.json* already exists in the repository's root. If you'd like to check multiple websites or URL:s you've to add them inside the square brackets, separated by commas. For instance:  
```
{ "sites": [
    {
        "id": 0,
        "url": "https://webperf.se/"
    },
    {
        "id": 1,
        "url": "https://surfalugnt.se/"
    }
]
}
```