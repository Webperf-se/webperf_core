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

# Yellow Lab Tools address
# https://yellowlab.tools when using the public webservice online
# http://localhost:8383 when installed locally
ylt_server_address = 'https://yellowlab.tools'
