# Getting started, other

PLEASE NOTE: Content in this section are obsolete and/or incomplete.

## Hosting webperf_core in the cloud
* [Get an account on PythonAnywhere and run the code in the cloud](https://www.pythonanywhere.com/?affiliate_id=0007e5c6) - through their “Tasks” function you can automatically run the code for example every day

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