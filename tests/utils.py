# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import shutil
import sys
import ssl
import json
import time
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
import os
from urllib.parse import ParseResult, urlparse, urlunparse
import requests
import IP2Location
import dns
import dns.resolver
import dns.dnssec
import config

IP2_LOCATION_DB = False
try:
    IP2_LOCATION_DB = IP2Location.IP2Location(
        os.path.join("data", "IP2LOCATION-LITE-DB1.IPV6.BIN"))
except ValueError as ex:
    print('Unable to load IP2Location Database from "data/IP2LOCATION-LITE-DB1.IPV6.BIN"', ex)


# DEFAULTS
REQUEST_TIMEOUT = config.http_request_timeout
USERAGENT = config.useragent

USE_CACHE = False
CACHE_TIME_DELTA = timedelta(hours=1)
try:
    USE_CACHE = config.cache_when_possible
    CACHE_TIME_DELTA = config.cache_time_delta
except:
    # If cache_when_possible variable is not set in config.py this will be the default
    USE_CACHE = False
    CACHE_TIME_DELTA = timedelta(hours=1)

DNS_SERVER = '8.8.8.8'
try:
    DNS_SERVER = config.dns_server
except:
    # If cache_when_possible variable is not set in config.py this will be the default
    DNS_SERVER = '8.8.8.8'


GITHUB_APIKEY = None
try:
    GITHUB_APIKEY=config.github_api_key
except:
    GITHUB_APIKEY=None

def change_url_to_test_url(url, test_name):

    o = urllib.parse.urlparse(url)
    if '' == o.query:
        new_query = f'webperf-core={test_name}'
    else:
        new_query = f'webperf-core={test_name}&' + o.query
    o2 = ParseResult(
        scheme=o.scheme,
        netloc=o.netloc,
        path=o.path,
        params=o.params,
        query=new_query,
        fragment=o.fragment)
    url2 = urlunparse(o2)
    return url2


def is_file_older_than(file, delta):
    cutoff = datetime.utcnow() - delta
    mtime = datetime.utcfromtimestamp(os.path.getmtime(file))
    if mtime < cutoff:
        return True
    return False


def get_cache_path(url, use_text_instead_of_content):
    o = urlparse(url)
    hostname = o.hostname

    file_ending = '.tmp'
    folder = 'tmp'
    if USE_CACHE:
        file_ending = '.cache'
        folder = 'cache'

    folder_path = os.path.join(folder)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    hostname_path = os.path.join(folder, hostname)
    if not os.path.exists(hostname_path):
        os.makedirs(hostname_path)

    cache_key_rule = '{0}.txt.utf-8{1}'
    if not use_text_instead_of_content:
        cache_key_rule = '{0}.bytes{1}'

    cache_key = cache_key_rule.format(
        hashlib.sha512(url.encode()).hexdigest(), file_ending)
    cache_path = os.path.join(folder, hostname, cache_key)

    return cache_path


def get_cache_file(url, use_text_instead_of_content, time_delta):
    cache_path = get_cache_path(url, use_text_instead_of_content)

    if not os.path.exists(cache_path):
        return None

    if USE_CACHE and is_file_older_than(cache_path, time_delta):
        return None

    if use_text_instead_of_content:
        with open(cache_path, 'r', encoding='utf-8', newline='') as file:
            return '\n'.join(file.readlines())
    else:
        with open(cache_path, 'rb') as file:
            return file.read()

def has_cache_file(url, use_text_instead_of_content, time_delta):
    cache_path = get_cache_path(url, use_text_instead_of_content)

    if not os.path.exists(cache_path):
        return False

    if USE_CACHE and is_file_older_than(cache_path, time_delta):
        return False

    return True


def clean_cache_files():
    if not USE_CACHE:
        # If we don't want to cache stuff, why complicate stuff, just empy tmp folder when done
        folder = 'tmp'
        base_directory = os.path.join(Path(os.path.dirname(
            os.path.realpath(__file__)) + os.path.sep).parent, folder)
        if os.path.exists(base_directory):
            shutil.rmtree(base_directory)
        return

    file_ending = '.cache'
    folder = 'cache'

    base_directory = os.path.join(Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent, folder)

    if not os.path.exists(base_directory):
        return

    print(f'Cleaning {file_ending[1:]} files...')

    subdirs = os.listdir(base_directory)
    print(len(subdirs), f'file and folders in {folder} folder.')
    cache_files = 0
    results_folders = 0
    cache_files_removed = 0
    results_folders_removed = 0
    for subdir in subdirs:
        files_or_subdirs = os.listdir(os.path.join(base_directory, subdir))
        for file_or_dir in files_or_subdirs:
            if file_or_dir.endswith(file_ending):
                cache_files += 1
                path = os.path.join(base_directory, subdir, file_or_dir)
                if not USE_CACHE or is_file_older_than(path, CACHE_TIME_DELTA):
                    os.remove(path)
                    cache_files_removed += 1

    print(cache_files, f'{file_ending[1:]} file(s) found.')
    print(results_folders, 'result folder(s) found.')
    print(cache_files_removed,
          f'{file_ending[1:]} file(s) removed.')
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

def get_http_content(url, allow_redirects=False, use_text_instead_of_content=True):
    """Trying to fetch the response content
    Attributes: url, as for the URL to fetch
    """

    try:
        content = get_cache_file(
            url, use_text_instead_of_content, CACHE_TIME_DELTA)
        if content is not None:
            return content

        headers = {'user-agent': USERAGENT}
        if url.startswith('https://api.github.com') and GITHUB_APIKEY is not None:
            headers['authorization'] = f'Bearer {GITHUB_APIKEY}'
        a = requests.get(url, allow_redirects=allow_redirects,
                         headers=headers, timeout=REQUEST_TIMEOUT*2)

        if use_text_instead_of_content:
            content = a.text
        else:
            content = a.content

        set_cache_file(url, content, use_text_instead_of_content)
        return content
    except ssl.CertificateError as error:
        print(f'Info: Certificate error. {error.reason}')
    except requests.exceptions.SSLError as error:
        if 'http://' in url:  # trying the same URL over SSL/TLS
            print('Info: Trying SSL before giving up.')
            return get_http_content(url.replace('http://', 'https://'))
        print(f'Info: SSLError. {error}')
    except requests.exceptions.ConnectionError as error:
        if 'http://' in url:  # trying the same URL over SSL/TLS
            print('Connection error! Info: Trying SSL before giving up.')
            return get_http_content(url.replace('http://', 'https://'))
        print(
            'Connection error! Unfortunately the request for URL'
            f'"{url}" failed.\nMessage:\n{sys.exc_info()[0]}')
    except:
        print(
            'Error! Unfortunately the request for URL'
            f'"{url}" either timed out or failed for other reason(s).'
            f'The timeout is set to {REQUEST_TIMEOUT} seconds.\nMessage:\n{sys.exc_info()[0]}')
    return ''

def get_content_type(url, cache_time_delta):
    headers = get_url_headers(url, cache_time_delta)

    if headers['status-code'] == 401:
        return 401

    print('\t- headers =', headers)

    if 'Content-Type' in headers:
        return headers['Content-Type']
    if 'content-type' in headers:
        return headers['content-type']

    return None

def get_url_headers(url, cache_time_delta):
    """Trying to fetch the response content
    Attributes: url, as for the URL to fetch
    """

    try:
        key = url.replace('https://', 'heads://').replace('http://', 'head://')

        content = get_cache_file(
            key, True, cache_time_delta)
        if content is not None:
            headers = json.loads(content)
            return headers

        headers = {'user-agent': USERAGENT}
        a = requests.head(url, allow_redirects=True,
                         headers=headers, timeout=REQUEST_TIMEOUT*2)

        print('\t- status =', a.status_code)

        if a.status_code == 401:
            return {
                'status-code': a.status_code
            }

        time.sleep(5)

        headers = dict(a.headers)
        headers['status-code'] = a.status_code
        nice_headers = json.dumps(headers, indent=3)
        set_cache_file(key, nice_headers, True)
        return headers
    except ssl.CertificateError as error:
        print(f'get_url_headers, Info using: Certificate error. {error.reason}')
    except requests.exceptions.SSLError:
        print('get_url_headers, Info using: SSL error occured')
    except requests.exceptions.ConnectionError:
        print('get_url_headers, Info using: connection error occured')
    except Exception:
        print('get_url_headers, Info using: unknown connection error occured')
    return {}

def has_redirect(url):
    """Trying to fetch the response content
    Attributes: url, as for the URL to fetch
    """

    error_msg = None
    try:
        headers = {'user-agent': USERAGENT}
        a = requests.get(url, allow_redirects=False,
                         headers=headers, timeout=REQUEST_TIMEOUT*2)

        has_location_header = 'Location' in a.headers

        if has_location_header:
            location_header = a.headers['Location']
            if len(location_header) > 1 and location_header[0:1] == '/':
                return (True, url + a.headers['Location'], '')
            return (True, a.headers['Location'], '')
        return (False, url, '')
    except ssl.CertificateError as error:
        print(f'Info: Certificate error. {error.reason}')
        error_msg = f'Info: Certificate error. {error.reason}'
    except requests.exceptions.SSLError:
        error_msg = 'Unable to verify: SSL error occured'
    except requests.exceptions.ConnectionError:
        error_msg = 'Unable to verify: connection error occured'
    except:
        error_msg = 'Unable to verify: unknown connection error occured'
    return (False, None, error_msg)


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
    return (millis/1000) % 60


def dns_lookup(key, datatype):
    use_dnssec = False
    cache_key = f'dnslookup://{key}#{datatype}#{use_dnssec}'
    if has_cache_file(cache_key, True, CACHE_TIME_DELTA):
        cache_path = get_cache_path(cache_key, True)
        response = dns.message.from_file(cache_path)
        return dns_response_to_list(response)

    try:
        query = None
        # Create a query for the 'www.example.com' domain
        if use_dnssec:
            query = dns.message.make_query(key, datatype, want_dnssec=True)
        else:
            query = dns.message.make_query(key, datatype, want_dnssec=False)

        # Send the query and get the response
        response = dns.query.udp(query, DNS_SERVER)

        if response.rcode() != 0:
            # HANDLE QUERY FAILED (SERVER ERROR OR NO DNSKEY RECORD)
            print('\t\tERROR, RCODE is INVALID:', response.rcode())
            return []

        text_response = response.to_text()
        set_cache_file(cache_key, text_response, True)

        time.sleep(5)

        return dns_response_to_list(response)

    except dns.dnssec.ValidationFailure as vf:
        print('\t\tDNS FAIL', vf)
    except Exception as ex2:
        print('\t\tDNS GENERAL FAIL', ex2)

    return []

def dns_response_to_list(dns_response):
    names = []
    for rrset in dns_response.answer:
        for rr in rrset:
            if rr.rdtype == dns.rdatatype.TXT:
                names.append(''.join(s.decode()
                                    for s in rr.strings))
            else:
                names.append(str(rr))

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
    # Countries in below list comes from this page:
    # https://ec.europa.eu/info/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en
    # Country codes for every country comes from Wikipedia when searching on country name,
    # example: https://en.wikipedia.org/wiki/Iceland
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
        rec = IP2_LOCATION_DB.get_all(ip_address)
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

def get_friendly_url_name(_, url, request_index):

    if request_index is None:
        request_index = '?'

    request_friendly_name = _(
        'TEXT_REQUEST_UNKNOWN').format(request_index)
    if request_index == 1:
        request_friendly_name = _(
            'TEXT_REQUEST_WEBPAGE').format(request_index)

    try:
        o = urlparse(url)
        tmp = o.path.strip('/').split('/')
        length = len(tmp)
        tmp = tmp[length - 1]

        regex = r"[^a-zA-Z0-9.]"
        subst = "-"

        tmp = re.sub(regex, subst, tmp, 0, re.MULTILINE)
        length = len(tmp)
        if length > 15:
            request_friendly_name = f'#{request_index}: {tmp[:15]}'
        elif length > 1:
            request_friendly_name = f'#{request_index}: {tmp}'
    except:
        return request_friendly_name
    return request_friendly_name

def merge_dicts(dict1, dict2, sort, make_distinct):
    if dict1 is None:
        return dict2
    if dict2 is None:
        return dict1

    for domain, value in dict2.items():
        if domain in dict1:
            type_of_value = type(value)
            if type_of_value is dict:
                for subkey, subvalue in value.items():
                    if subkey in dict1[domain]:
                        if isinstance(subvalue, dict):
                            merge_dicts(
                                dict1[domain][subkey],
                                dict2[domain][subkey],
                                sort,
                                make_distinct)
                        elif isinstance(subvalue, list):
                            dict1[domain][subkey].extend(subvalue)
                            if make_distinct:
                                dict1[domain][subkey] = list(set(dict1[domain][subkey]))
                            if sort:
                                dict1[domain][subkey] = sorted(dict1[domain][subkey])
                    else:
                        dict1[domain][subkey] = dict2[domain][subkey]
            elif type_of_value == list:
                dict1[domain].extend(value)
                if make_distinct:
                    dict1[domain] = list(set(dict1[domain]))
                if sort:
                    dict1[domain] = sorted(dict1[domain])
            elif type_of_value == int:
                dict1[domain] = dict1[domain] + value
        else:
            dict1[domain] = value
    return dict1
