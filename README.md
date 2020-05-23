# Webperf Core
Minimalistic client mainly running on PythonAnywhere.com, accessing different websites, or web-APIs, and scraping them.

The tests included in the first version are:
* Google Pagespeed Insights API
* Testing the 404 page and status code
* Validating the HTML code against W3C
* Validating the CSS code against W3C
* Users’ integrity test against Webbkoll, provided by Dataskydd.net

## psst. third party extensions...
* [webperf-leaderboard](https://github.com/krompaco/webperf-leaderboard) by [Johan Kronberg](https://github.com/krompaco/)

## Get started with webperf_core
Here are some suggestions on how to get started with the tests on your own computer. Actually, it is even easier to run the tests on a cloud environment such as [PythonAnywhere - $ 5 / month](https://www.pythonanywhere.com/?affiliate_id=0007e5c6) - then the technical environment is ready to just upload the files.

You download the code itself from [GitHub - webperf_core](https://github.com/Webperf-se/webperf_core) and place it in a good place on your computer.
### Adjust the source code
There are two files that you need to adjust:
* *SAMPLE-config.py* needs to be renamed to *config.py*
The reason for this is because if you download a new version of the code, your settings or data should not be overwritten by accident.

Another thing you need to do is to open the *config.py* file and change one thing. The line that looks like the following is incomplete:  
*googlePageSpeedApiKey = “”*  
Between the quotation marks, enter your Google Pagespeed API key. See the following header for how to do this.

### Google Pagespeed API key
You can choose to ignore the Google Pagespeed API. In this case, put a hashtag *#* in front of the following line in *default.py*:  
*testsites(test_type=0)*  
So it looks like this:  
*# testsites(test_type=0)*

Google Pagespeed requires an API key. You can get one like this:
1. Go to [Google Cloud Platform](https://console.cloud.google.com/apis).
2. Search for *Pagespeed Insights API*.
3. Click on *Credentials* (you may need to create a project first, if you do not already have one).
4. Click *+ Create Credentials*, then *API key*
5. In the dialog the key now appears below *Your API key*, it can look like this *AIzaXyCjEXTvAq7zAU_RV_vA7slvDO9p1weRfgW*

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
*python default.py*

Now it will begin testing.

### Are you getting error messages?
It is often worthwhile to google the error messages you get. If you give up the search then you can always [check if someone on our Slack channel](https://webperf.se/articles/webperf-pa-slack/) have time to help you, but don’t forget to paste your error message directly in the first post. Or, if you think your error are common for more people than yourself, post an issue here at Github.

## What you are allowed to do with this code / repo
The license used is the [MIT license](https://en.wikipedia.org/wiki/MIT_License). This means that you can do whatever you want with the source code, including using it in commercial software and contexts. However, there is no guarantee or liability for the code.

## Do you want to contribute?
You can contribute here at Github. By checking the code, trying the documentation, suggesting new tests, among other things.

## Hosting webperf_core in the cloud
* [Get an account on PythonAnywhere and run the code in the cloud](https://www.pythonanywhere.com/?affiliate_id=0007e5c6) - through their “Tasks” function you can automatically run the code for example every day
