# -*- coding: utf-8 -*-
import sys
import socket
import ssl
import json
import time
import requests
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
from bs4 import BeautifulSoup
import dns.resolver
import config
import IP2Location
import os


ip2location_db = False
try:
    ip2location_db = IP2Location.IP2Location(
        os.path.join("data", "IP2LOCATION-LITE-DB1.IPV6.BIN"))
except Exception as ex:
    print('Unable to load IP2Location Database from "data/IP2LOCATION-LITE-DB1.IPV6.BIN"', ex)


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

        # print('httpRequestGetContent', a.text)
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
        # print('httpRequestGetContent', test)

        # print('has_redirect', has_location_header, url, a.headers)

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


def dns_lookup(hostname, record_type):
    names = list()

    try:
        dns_records = dns.resolver.resolve(hostname, record_type)
    except dns.resolver.NXDOMAIN:
        # print("dns lookup error: No record found")
        # sleep so we don't get banned for to many queries on DNS servers
        time.sleep(1)
        return names
    except (dns.resolver.NoAnswer, dns.resolver.NoNameservers) as error:
        # print("dns lookup error: ", error)
        # sleep so we don't get banned for to many queries on DNS servers
        time.sleep(1)
        return names

    for dns_record in dns_records:
        if record_type == 'TXT':
            names.append(''.join(s.decode()
                                 for s in dns_record.strings))
        else:
            names.append(str(dns_record))

        # sleep so we don't get banned for to many queries on DNS servers
    time.sleep(1)
    return names


def get_eu_countries():
    eu_countrycodes = {
        'BE': 'Belgium',
        'BG': 'Bulgaria',
        'CZ': 'Czechia',
        'DK': 'Denmark',
        'DE': 'Germany',
        'EE': 'Estonia',
        'IE': 'Ireland',
        'EL': 'Greece',
        'ES': 'Spain',
        'FR': 'France',
        'HR': 'Croatia',
        'IT': 'Italy',
        'CY': 'Cyprus',
        'LV': 'Latvia',
        'LT': 'Lithuania',
        'LU': 'Luxembourg',
        'HU': 'Hungary',
        'MT': 'Malta',
        'NL': 'Netherlands',
        'AT': 'Austria',
        'PL': 'Poland',
        'PT': 'Portugal',
        'RO': 'Romania',
        'SI': 'Slovenia',
        'SK': 'Slovakia',
        'FI': 'Finland',
        'SE': 'Sweden'
    }
    return eu_countrycodes


def get_exception_countries():
    # Countries in below list comes from this page: https://ec.europa.eu/info/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en
    # Country codes for every country comes from Wikipedia when searching on country name, example: https://en.wikipedia.org/wiki/Iceland
    exception_countrycodes = {
        'NO': 'Norway',
        'LI': 'Liechtenstein',
        'IS': 'Iceland',
        'AD': 'Andorra',
        'AR': 'Argentina',
        'CA': 'Canada',
        'FO': 'Faroe Islands',
        'GG': 'Guernsey',
        'IL': 'Israel',
        'IM': 'Isle of Man',
        'JP': 'Japan',
        'JE': 'Jersey',
        'NZ': 'New Zealand',
        'CH': 'Switzerland',
        'UY': 'Uruguay',
        'KR': 'South Korea',
        'GB': 'United Kingdom',
        'AX': 'Åland Islands',
        # If we are unable to guess country, give it the benefit of the doubt.
        'unknown': 'Unknown'
    }
    return exception_countrycodes


def is_country_code_in_eu(country_code):
    country_codes = get_eu_countries()
    if country_code in country_codes:
        return True

    return False


def is_country_code_in_exception_list(country_code):
    country_codes = get_exception_countries()
    if country_code in country_codes:
        return True

    return False


def is_country_code_in_eu_or_on_exception_list(country_code):
    return is_country_code_in_eu(country_code) or is_country_code_in_exception_list(country_code)


def get_country_code_from_ip2location(ip_address):
    rec = False
    try:
        rec = ip2location_db.get_all(ip_address)
    except Exception:
        return ''
    try:
        countrycode = rec.country_short
        return countrycode
    except Exception:
        return ''


def get_best_country_code(ip_address, default_country_code):
    if is_country_code_in_eu_or_on_exception_list(default_country_code):
        return default_country_code

    country_code = get_country_code_from_ip2location(ip_address)
    if country_code == '':
        return default_country_code

    return country_code
