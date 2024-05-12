# -*- coding: utf-8 -*-
"""
Configurations for the client lib
"""

from datetime import timedelta

# NOTE: Rename this file to 'config.py' and fill in the missing info below

# useragent for HTTP requests
USERAGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0'

# enter your API key for Google Pagespeed API
GOOGLEPAGESPEEDAPIKEY = ""

HTTP_REQUEST_TIMEOUT = 60

# timeout between calls to website
WEBBKOLL_SLEEP = 20

# if you want a more detailed review for the CSS test (Test #7), set this to False
CSS_REVIEW_GROUP_ERRORS = True

# Only show reviews that you can improve, set this value to True
REVIEW_SHOW_IMPROVEMENTS_ONLY = False

# Tells Yellow Lab Tools Test to use API version or command line version
YLT_USE_API = False
YLT_SERVER_ADDRESS = 'https://yellowlab.tools'

# Tells Lighthouse based Test(s) to use API version or command line version
LIGHTHOUSE_USE_API = False

# Tells sitespeed if we should use it as a docker image or a npm package
SITESPEED_USE_DOCKER = False

# Tells sitespeed max timeout for website calls
SITESPEED_TIMEOUT = 300

# how many iterations of Sitespeed.io requests would you like? Has to be at least 2 not to fail
SITESPEED_ITERATIONS = 2

# Changing this will make webperf-core use local cache where available
CACHE_WHEN_POSSIBLE = False

# This tells webperf-core how long to use cached resources
# See https://docs.python.org/3/library/datetime.html#timedelta-objects for possible values
CACHE_TIME_DELTA = timedelta(hours=1)

# GITHUB API Token, used for calls to github API (to remove call limit)
GITHUB_API_KEY = None

# Tell tests to use detailed report (when available) for review and rating
USE_DETAILED_REPORT = False

# Tells HTTP test to ignore everything except the CSP part
# (great if you run it against sitemap to get CSP recommendation)
CSP_ONLY = False

# Tells webperf_core to use following DNS Server for dns lookups
DNS_SERVER = '8.8.8.8'

# Tell software test to use stealth mode or not, default is 'True'
SOFTWARE_USE_STEALTH = True

# Tell software test the path to where you have repo of: https://github.com/github/advisory-database
# Used to find CVE:s for npm packages
SOFTWARE_GITHUB_ADADVISORY_DATABASE_PATH = None

# Tells software test what browser to use (chrome/firefox), default = chrome
SOFTWARE_BROWSER = "chrome"

# Tells email test if it should do a operation email test (most consumer ISP don't allow this)
EMAIL_NETWORK_SUPPORT_PORT25_TRAFFIC = False

# Tells email test if it should do a operation test (GitHub Actions doesn't support it)
EMAIL_NETWORK_SUPPORT_IPV6_TRAFFIC = False
