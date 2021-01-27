# -*- coding: utf-8 -*-
"""
Configurations for the client lib
"""

# NOTE: Rename this file to 'config.py' and fill in the missing info below

# useragent for HTTP requests
#useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0'
useragent = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'

# enter your API key for Google Pagespeed API
googlePageSpeedApiKey = ""

http_request_timeout = 60

# timeout between calls to website
webbkoll_sleep = 20

# if you want a more detailed review for the CSS test (Test #7), set this to False
css_review_group_errors = True

# scoring method used for CSS test (Test #7), possible values are: 'average', 'median', 'lowest' (default)
css_scoring_method = 'lowest'
