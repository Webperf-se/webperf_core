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
from tests.utils import *

### DEFAULTS
request_timeout = config.http_request_timeout

def run_test(langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    points = 0.0
    review = ''

    ## kollar koden
    try:
        url = 'https://validator.w3.org/nu/?doc={0}'.format(url.replace('/', '%2F').replace(':', '%3A'))
        headers = {'user-agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
        request = requests.get(url, allow_redirects=False, headers=headers, timeout=request_timeout)

        ## hämta HTML
        soup = BeautifulSoup(request.text, 'html.parser')
        errors = len(soup.find_all("li", {"class": "error"}))
        # print(len(errors))
    except requests.Timeout:
        print('Timeout!\nMessage:\n{0}'.format(sys.exc_info()[0]))
        return None

    if errors == 0:
        points = 5.0
        review = '* Inga fel i HTML-koden.\n'
    elif errors <= 5:
        points = 4.0
        review = '* Den testade sidan har {0} st fel i sin HTML-kod.\n'.format(errors)
    elif errors <= 15:
        points = 3.0
        review = '* Den testade sidan har {0} st fel i sin HTML-kod.\n'.format(errors)
    elif errors <= 30:
        points = 2.0
        review = '* Den testade sidan har {0} st fel i sin HTML-kod. Det är inte så bra.\n'.format(errors)
    elif errors > 30:
        points = 1.0
        review = '* Den testade sidan har massor med fel i sin HTML-kod. Hela {0} st. \n'.format(errors)

    return (points, review)
