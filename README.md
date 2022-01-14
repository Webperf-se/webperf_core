# Webperf Core
Minimalistic client mainly running on PythonAnywhere.com, accessing different websites, or web-APIs, and scraping them.

The tests included in 3.x are:
* Google Lighthouse accessibility with Axe
* Google Lighthouse performance
* Google Lighthouse best practice
* Google Lighthouse progressive web apps
* Google Lighthouse SEO
* Testing the 404 page and status code (by default checks for Swedish text, though)
* Validating the HTML code against W3C
* Validating the CSS code against W3C
* Users’ integrity test against Webbkoll, provided by Dataskydd.net
* *Frontend quality against Yellow Lab Tools (preferably with [local instance of YLT](https://hub.docker.com/r/jguyomard/yellowlabtools))*
* *Website performance with Sitespeed.io (requires [local instance of Sitespeed.io](https://hub.docker.com/r/sitespeedio/sitespeed.io))*
* Carbon dioxide checked against Website Carbon Calculator API
* Standard files (checks for robots.txt, security.txt and more)
* HTTP and Network test (checks HTTP version, TLS version and more)
* Tracking & Integrity test (provided by Pagexray, checks GDPR compliance, tracking and more)

## Code Tests
* [![CodeQL (Security and Code Quality)](https://github.com/Webperf-se/webperf_core/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/codeql-analysis.yml)
* [![Regression Test - Google Lighthouse Based Test(s)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-google-lighthouse-based.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-google-lighthouse-based.yml)
* [![Regression Test - 404 (Page not Found) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-404.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-404.yml)
* [![Regression Test - HTML Validation Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-html.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-html.yml)
* [![Regression Test - CSS Validation Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-css.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-css.yml)
* [![Regression Test - Integrity & Security (Webbkoll) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-webbkoll.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-webbkoll.yml)
* [![Regression Test - Quality on frontend (Yellow Lab Tools) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-ylt.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-ylt.yml)
* [![Regression Test - Performance (Sitespeed.io) Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-sitespeed.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-sitespeed.yml)
* [![Regression Test - Standard files Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-standard-files.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-standard-files.yml)
* [![Regression Test - HTTP & Network Test](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-http.yml/badge.svg)](https://github.com/Webperf-se/webperf_core/actions/workflows/regression-test-http.yml)

## psst. third party extensions...
* [webperf-leaderboard](https://github.com/krompaco/webperf-leaderboard) by [Johan Kronberg](https://github.com/krompaco/)

## Get started with webperf_core
Here are some suggestions on how to get started with the tests on your own computer. Actually, it is even easier to run the tests on a cloud environment such as [PythonAnywhere - $ 5 / month](https://www.pythonanywhere.com/?affiliate_id=0007e5c6) - then the technical environment is ready to just upload the files.

You download the code itself from [GitHub - webperf_core](https://github.com/Webperf-se/webperf_core) and place it in a good location on your computer.
### Adjust the source code
There are two files that you need to adjust:
* *SAMPLE-config.py* needs to be renamed to *config.py*
The reason for this is because if you download a new version of the code, your settings or data should not be overwritten by accident.

Another thing you need to do is to open the *config.py* file and change one thing. The line that looks like the following is incomplete:  
*googlePageSpeedApiKey = “”*  
Between the quotation marks, enter your Google Pagespeed API key. See the following header for how to do this.

### Google Lighthouse API key
Google Lighthouse API requires an API key. You can get one like this:
1. Go to [Google Cloud Platform](https://console.cloud.google.com/apis).
2. Search for *Pagespeed Insights API*.
3. Click the button labelled *Manage*.
4. Click on *Credentials* (you may need to create a project first, if you do not already have one).
5. Click *+ Create Credentials*, then *API key*
6. In the dialogue box the key now appears below *Your API key*, it can look like this *AIzaXyCjEXTvAq7zAU_RV_vA7slvDO9p1weRfgW*

That code is your API key, that you should put in the *config.py* file in the source code, between the quotation marks on the line where you find *googlePageSpeedApiKey*.

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

### Are you receiving error messages? 

It is often worthwhile to google the error messages you get. If you give up the search then you can always [check if someone on our Slack channel](https://webperf.se/articles/webperf-pa-slack/) have time to help you, but don’t forget to paste your error message directly in the first post. Or, if you think your error are common for more people than yourself, post an issue here at Github.

### Want to add another language? 

The multiple language support is built on `gettext` in Python.

#### How to support new language
You could either follow the more technical suggestions below, or you perhaps would like an application such as [Poedit](https://poedit.net) (available on Macos, Linux and Windows).

To create a new language source file:  
```python3 <your path to pygettext.py > -d webperf-core -o locales/webperf-core.pot default.py checks.py```

Copy the file to your locale, for Swedish it would be:  
```locales/sv/LC_MESSAGES/webperf-core.pot```

Rename the file extension from `.pot` to `.po`

After you have translated everything you should run the following command from the LC_MESSAGES folder:  
```python3 <your path to msgfmt.py> -o webperf-core.mo webperf-core.po```

You now have support for a new language, please send it to the official repository using a pull request :)

#### How to find pygettext.py

Locate your pygettext.py file:  
```locate pygettext.py```

It might be as follows:  
```/Library/Frameworks/Python.framework/Versions/3.8/share/doc/python3.8/examples/Tools/i18n/pygettext.py```

#### How to find msgfmt.py

Locate your msgfmt.py file:  
```locate msgfmt.py```

It might be as follows:  
```/Library/Frameworks/Python.framework/Versions/3.8/share/doc/python3.8/examples/Tools/i18n/msgfmt.py```

The command can be:
```python3 /Library/Frameworks/Python.framework/Versions/3.8/share/doc/python3.8/examples/Tools/i18n/pygettext.py -d webperf-core -o locales/webperf-core.pot default.py```

### References

- https://phrase.com/blog/posts/translate-python-gnu-gettext/
- https://docs.python.org/3/library/gettext.html

## What you are allowed to do with this code / repo
The license used is the [MIT license](https://en.wikipedia.org/wiki/MIT_License). This means that you can do whatever you want with the source code, including using it in commercial software and contexts. However, there is no guarantee or liability for the code.

## Do you want to contribute?
You can contribute here at Github. By checking the code, trying the documentation, suggesting new tests, among other things.

## Hosting webperf_core in the cloud
* [Get an account on PythonAnywhere and run the code in the cloud](https://www.pythonanywhere.com/?affiliate_id=0007e5c6) - through their “Tasks” function you can automatically run the code for example every day
