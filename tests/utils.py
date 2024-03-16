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
from urllib.parse import ParseResult, urlparse, urlunparse


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
gitHubApiKey = None

try:
    use_cache = config.cache_when_possible
    cache_time_delta = config.cache_time_delta
except:
    # If cache_when_possible variable is not set in config.py this will be the default
    use_cache = False
    cache_time_delta = timedelta(hours=1)

try:
    gitHubApiKey=config.github_api_key
except:
    gitHubApiKey=None

def change_url_to_test_url(url, test_name):

    o = urllib.parse.urlparse(url)
    if '' == o.query:
        new_query = 'webperf-core={0}'.format(test_name)
    else:
        new_query = 'webperf-core={0}&'.format(test_name) + o.query
    o2 = ParseResult(scheme=o.scheme, netloc=o.netloc, path=o.path, params=o.params, query=new_query, fragment=o.fragment)
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
    if use_cache:
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

    if use_cache and is_file_older_than(cache_path, time_delta):
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

    if use_cache and is_file_older_than(cache_path, time_delta):
        return False
    
    return True


def clean_cache_files():
    if not use_cache:
        # If we don't want to cache stuff, why complicate stuff, just empy tmp folder when done
        folder = 'tmp'
        dir = os.path.join(Path(os.path.dirname(
            os.path.realpath(__file__)) + os.path.sep).parent, folder)
        if os.path.exists(dir):
            shutil.rmtree(dir)
        return
    
    file_ending = '.cache'
    folder = 'cache'


    dir = os.path.join(Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent, folder)
    
    if not os.path.exists(dir):
        return

    print('Cleaning {0} files...'.format(file_ending[1:]))

    subdirs = os.listdir(dir)
    print(len(subdirs), 'file and folders in {0} folder.'.format(folder))
    cache_files = 0
    results_folders = 0
    cache_files_removed = 0
    results_folders_removed = 0
    for subdir in subdirs:
        files_or_subdirs = os.listdir(os.path.join(dir, subdir))
        for file_or_dir in files_or_subdirs:
            if file_or_dir.endswith(file_ending):
                cache_files += 1
                path = os.path.join(dir, subdir, file_or_dir)
                if not use_cache or is_file_older_than(path, cache_time_delta):
                    os.remove(path)
                    cache_files_removed += 1

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
        if url.startswith('https://api.github.com') and gitHubApiKey != None:
            headers['authorization'] = 'Bearer {0}'.format(gitHubApiKey)
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

def get_content_type(url, cache_time_delta):
    headers = get_url_headers(url, cache_time_delta)

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
        if content != None:
            headers = json.loads(content)
            return headers
        
        headers = {'user-agent': useragent}
        a = requests.head(url, allow_redirects=True,
                         headers=headers, timeout=request_timeout*2)

        time.sleep(5)

        headers = dict(a.headers)
        nice_headers = json.dumps(headers, indent=3)
        set_cache_file(key, nice_headers, True)
        return headers
    except ssl.CertificateError as error:
        print('Info: Certificate error. {0}'.format(error.reason))
        return dict()
    except requests.exceptions.SSLError:
        return dict()
    except requests.exceptions.ConnectionError:
        return dict()
    except Exception as ex:
        return dict()

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

    import dns.rdataclass
    import dns.rdatatype
    import dns.rrset

    cache_key = 'dnslookup://{0}#{1}'.format(hostname, record_type)
    content = get_cache_file(
        cache_key, True, cache_time_delta)

    # TODO: make this cachable again
    if content != None:
        tmps = json.loads(content)
        # for tmp in tmps:
        #     # names.append(dns.rdataclass.from_text(tmp))
        #     names.append(dns.rdataclass.from_text(tmp))
        return tmps

    try:
        dns_records = dns.resolver.resolve(hostname, record_type)
    except dns.resolver.NXDOMAIN:
        print("dns lookup info: No record found")
        # sleep so we don't get banned for to many queries on DNS servers
        time.sleep(1)
        nice_raw = json.dumps(names, indent=2)
        set_cache_file(cache_key, nice_raw, True)
        return names
    except (dns.resolver.NoAnswer, dns.resolver.NoNameservers) as error:
        print("dns lookup info: ", error)
        # sleep so we don't get banned for to many queries on DNS servers
        time.sleep(5)
        nice_raw = json.dumps(names, indent=2)
        set_cache_file(cache_key, nice_raw, True)
        return names
    except Exception as ex:
        time.sleep(10)
        nice_raw = json.dumps(names, indent=2)
        set_cache_file(cache_key, nice_raw, True)
        return names

    # data = list()
    for dns_record in dns_records:
        if record_type == 'TXT':
            names.append(''.join(s.decode()
                                 for s in dns_record.strings))
        else:
            # names.append(dns_record.to_text())
            # data.append(dns_record)
            names.append(str(dns_record))

        # sleep so we don't get banned for to many queries on DNS servers
    time.sleep(1)

    nice_raw = json.dumps(names, indent=2)
    set_cache_file(cache_key, nice_raw, True)

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

def get_friendly_url_name(_, url, request_index):

    if request_index == None:
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
            request_friendly_name = '#{0}: {1}'.format(request_index, tmp[:15])
        elif length > 1:
            request_friendly_name = '#{0}: {1}'.format(request_index, tmp)
    except:
        return request_friendly_name
    return request_friendly_name
