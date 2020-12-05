#-*- coding: utf-8 -*-
import sys
import socket
import ssl
import json
import requests
import urllib # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
from bs4 import BeautifulSoup
import config

### DEFAULTS
request_timeout = config.http_request_timeout
googlePageSpeedApiKey = config.googlePageSpeedApiKey

def httpRequestGetContent(url):
    """Trying to fetch the response content
    Attributes: url, as for the URL to fetch
    """

    try:
        a = requests.get(url)

        return a.text
    except requests.exceptions.SSLError:
        if 'http://' in url: # trying the same URL over SSL/TLS
            print('Info: Trying SSL before giving up.')
            return httpRequestGetContent(url.replace('http://', 'https://'))
    except requests.exceptions.ConnectionError:
        print(
            'Connection error! Unfortunately the request for URL "{0}" failed.\nMessage:\n{1}'.format(url, sys.exc_info()[0]))
        pass
    except:
        print(
            'Error! Unfortunately the request for URL "{0}" either timed out or failed for other reason(s). The timeout is set to {1} seconds.\nMessage:\n{2}'.format(url, timeout_in_seconds, sys.exc_info()[0]))
        pass

def get_guid(length):
    """
    Generates a unique string in specified length
    """
    return str(uuid.uuid4())[0:length]

def convert_to_seconds(millis, return_with_seconds=True):
    """
    Converts milliseconds to seconds.
    Arg: 'return_with_seconds' defaults to True and returns string ' sekunder' after the seconds
    """
    if return_with_seconds:
        return (millis/1000)%60 + " sekunder"
    else:
        return (millis/1000)%60

def is_sitemap(content):
	"""Check a string to see if its content is a sitemap or siteindex.

	Attributes: content (string)
	"""
	try:
		if 'www.sitemaps.org/schemas/sitemap/' in content or '<sitemapindex' in content:
			return True
	except:
		return False

	return False
