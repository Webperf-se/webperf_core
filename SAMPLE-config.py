# -*- coding: utf-8 -*-
"""
Configurations for the client lib
"""

# NOTE: Rename this file to 'config.py' and fill in the missing info below

# useragent for HTTP requests
useragent = 'Mozilla/5.0 (compatible; Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36 Edg/88.0.705.56'

# enter your API key for Google Pagespeed API
googlePageSpeedApiKey = ""

http_request_timeout = 60

# timeout between calls to website
webbkoll_sleep = 20

# if you want a more detailed review for the CSS test (Test #7), set this to False
css_review_group_errors = True

# Tells webperf-core to use "data/IP2LOCATION-LITE-DB1.IPV6.CSV"
# Go to https://pypi.org/project/IP2Location/ and download the LITE IPV6 database.
use_ip2location = False

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
