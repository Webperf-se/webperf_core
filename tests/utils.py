# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import shutil
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

try:
    use_cache = config.cache_when_possible
    cache_time_delta = config.cache_time_delta
except:
    # If cache_when_possible variable is not set in config.py this will be the default
    use_cache = False
    cache_time_delta = timedelta(hours=1)


def is_file_older_than(file, delta):
    cutoff = datetime.utcnow() - delta
    mtime = datetime.utcfromtimestamp(os.path.getmtime(file))
    if mtime < cutoff:
        return True
    return False


def get_cache_path(url, use_text_instead_of_content):
    file_ending = '.tmp'
    if use_cache:
        file_ending = '.cache'

    cache_key_rule = '{0}.txt.utf-8{1}'
    if not use_text_instead_of_content:
        cache_key_rule = '{0}.bytes{1}'

    cache_key = cache_key_rule.format(
        hashlib.sha512(url.encode()).hexdigest(), file_ending)
    cache_path = os.path.join('data', cache_key)
    return cache_path


def get_cache_file(url, use_text_instead_of_content, time_delta):
    cache_path = get_cache_path(url, use_text_instead_of_content)

    if not os.path.exists(cache_path):
        return None

    if use_cache and is_file_older_than(cache_path, time_delta):
        return None

    if use_text_instead_of_content:
        with open(cache_path, 'r', encoding='utf-8', newline='') as file:
            return '\n'.join(file.readlines())
    else:
        with open(cache_path, 'rb') as file:
            return file.read()


def clean_cache_files():
    file_ending = '.tmp'
    if use_cache:
        file_ending = '.cache'

    print('Cleaning {0} files...'.format(file_ending[1:]))

    dir = os.path.join(Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent, 'data')

    files_or_subdirs = os.listdir(dir)
    print(len(files_or_subdirs), 'file and folders in data folder.')
    cache_files = 0
    results_folders = 0
    cache_files_removed = 0
    results_folders_removed = 0
    for file_or_dir in files_or_subdirs:
        if file_or_dir.endswith(file_ending):
            cache_files += 1
            path = os.path.join(dir, file_or_dir)
            if not use_cache or is_file_older_than(path, cache_time_delta):
                os.remove(path)
                cache_files_removed += 1
        if file_or_dir.startswith('results-'):
            results_folders += 1
            path = os.path.join(dir, file_or_dir)
            if not use_cache or is_file_older_than(path, cache_time_delta):
                shutil.rmtree(path)
                results_folders_removed += 1

    print(cache_files, '{0} file(s) found.'.format(file_ending[1:]))
    print(results_folders, 'result folder(s) found.')
    print(cache_files_removed,
          '{0} file(s) removed.'.format(file_ending[1:]))
    print(results_folders_removed,
          'result folder(s) removed.')


def set_cache_file(url, content, use_text_instead_of_content):
    cache_path = get_cache_path(url, use_text_instead_of_content)
    if use_text_instead_of_content:
        with open(cache_path, 'w', encoding='utf-8', newline='') as file:
            file.write(content)
    else:
        with open(cache_path, 'wb') as file:
            file.write(content)


def httpRequestGetContent(url, allow_redirects=False, use_text_instead_of_content=True):
    """Trying to fetch the response content
    Attributes: url, as for the URL to fetch
    """

    try:
        content = get_cache_file(
            url, use_text_instead_of_content, cache_time_delta)
        if content != None:
            return content

        headers = {'user-agent': useragent}
        a = requests.get(url, allow_redirects=allow_redirects,
                         headers=headers, timeout=request_timeout*2)

        if use_text_instead_of_content:
            content = a.text
        else:
            content = a.content

        set_cache_file(url, content, use_text_instead_of_content)
        return content
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
        time.sleep(5)
        return names
    except Exception as ex:
        time.sleep(10)
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
