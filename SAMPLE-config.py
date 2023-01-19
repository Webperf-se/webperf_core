# -*- coding: utf-8 -*-
"""
Configurations for the client lib
"""

from datetime import timedelta

# NOTE: Rename this file to 'config.py' and fill in the missing info below

# useragent for HTTP requests
useragent = 'Mozilla/5.0 (compatible; Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36 Edg/88.0.705.56'

# enter your API key for Google Pagespeed API
googlePageSpeedApiKey = ""

http_request_timeout = 60

# timeout between calls to website
webbkoll_sleep = 20

# Tells CSS/HTML test to use public website or local version
w3c_use_website = True

# if you want a more detailed review for the CSS test (Test #7), set this to False
css_review_group_errors = True

# Only show reviews that you can improve, set this value to True
review_show_improvements_only = False

# Tells Yellow Lab Tools Test to use API version or command line version
ylt_use_api = True

# Tells Lighthouse based Test(s) to use API version or command line version
lighthouse_use_api = True

# Tells sitespeed if we should use it as a docker image or a npm package
sitespeed_use_docker = True

# TO BE IMPLEMENTED:
# locales - where are the lang files located?
# at services like PythonAnywhere.com you might have to state a path like '/home/your-username/your-webperf-core-folder/locales'
locales = 'locales'

# how many iterations of Sitespeed.io requests would you like? Has to be at least 2 not to fail
sitespeed_iterations = 2

# Changing this will make webperf-core use local cache where available
cache_when_possible = False

# This tells webperf-core how long to use cached resources
# See https://docs.python.org/3/library/datetime.html#timedelta-objects for possible values
cache_time_delta = timedelta(hours=1)

# Tell software test to use stealth mode or not, default is 'True'
software_use_stealth = True

# Tell software test to use detailed report for review and rating
software_use_detailed_report = False

# Tell software test the path to where you have repo of: https://github.com/github/advisory-database
# Used to find CVE:s for npm packages
software_github_adadvisory_database_path = None
