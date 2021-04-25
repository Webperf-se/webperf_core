# -*- coding: utf-8 -*-
import sys
import socket
import ssl
import json
import requests
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
from bs4 import BeautifulSoup
import config

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
googlePageSpeedApiKey = config.googlePageSpeedApiKey


def httpRequestGetContent(url, allow_redirects=False):
    """Trying to fetch the response content
    Attributes: url, as for the URL to fetch
    """

    try:
        headers = {'user-agent': useragent}
        a = requests.get(url, allow_redirects=allow_redirects,
                         headers=headers, timeout=request_timeout*2)

        #print('httpRequestGetContent', a.text)
        return a.text
    except ssl.CertificateError as error:
        print('Info: Certificate error. {0}'.format(error.reason))
        pass
    except requests.exceptions.SSLError as error:
        if 'http://' in url:  # trying the same URL over SSL/TLS
            print('Info: Trying SSL before giving up.')
            return httpRequestGetContent(url.replace('http://', 'https://'))
        else:
            print('Info: SSLError. {0}'.format(error))
            return ''
        pass
    except requests.exceptions.ConnectionError as error:
        if 'http://' in url:  # trying the same URL over SSL/TLS
            print('Connection error! Info: Trying SSL before giving up.')
            return httpRequestGetContent(url.replace('http://', 'https://'))
        else:
            print(
                'Connection error! Unfortunately the request for URL "{0}" failed.\nMessage:\n{1}'.format(url, sys.exc_info()[0]))
            return ''
        pass
    except:
        print(
            'Error! Unfortunately the request for URL "{0}" either timed out or failed for other reason(s). The timeout is set to {1} seconds.\nMessage:\n{2}'.format(url, request_timeout, sys.exc_info()[0]))
        pass
    return ''


def has_redirect(url):
    """Trying to fetch the response content
    Attributes: url, as for the URL to fetch
    """

    try:
        headers = {'user-agent': useragent}
        a = requests.get(url, allow_redirects=False,
                         headers=headers, timeout=request_timeout*2)

        has_location_header = 'Location' in a.headers
        #print('httpRequestGetContent', test)

        #print('has_redirect', has_location_header, url, a.headers)

        if has_location_header:
            location_header = a.headers['Location']
            if len(location_header) > 1 and location_header[0:1] == '/':
                return (True, url + a.headers['Location'], '')
            else:
                return (True, a.headers['Location'], '')
        else:
            return (False, url, '')
        return a.text
    except ssl.CertificateError as error:
        print('Info: Certificate error. {0}'.format(error.reason))
        pass
    except requests.exceptions.SSLError:
        return (False, None, 'Unable to verify: SSL error occured')
    except requests.exceptions.ConnectionError:
        return (False, None, 'Unable to verify: connection error occured')
    except:
        return (False, None, 'Unable to verify: unknown connection error occured')


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
        return (millis/1000) % 60 + " sekunder"
    else:
        return (millis/1000) % 60


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
