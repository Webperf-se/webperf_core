# -*- coding: utf-8 -*-
from datetime import datetime
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
import dns.query
import dns.resolver
import dns.dnssec
import dns.exception
import dns.name
import gettext

def get_config_or_default(name):
    """
    Retrieves the configuration value for a given name from the configuration file.
    If the name does not exist in the configuration file,
    it attempts to retrieve it from the SAMPLE-config.py file.
    
    Parameters:
    name (str): The name of the configuration value to retrieve.

    Returns:
    The configuration value associated with the given name.

    Raises:
    ValueError: If the name does not exist in both the configuration file and
    the SAMPLE-config.py file.

    Notes:
    - If the name exists in the SAMPLE-config.py file but not in the configuration file,
      a warning message is printed.
    - If the name does not exist in both files,
      a fatal error message is printed and a ValueError is raised.
    """
    # Try get config from our configuration file
    import config # pylint: disable=import-outside-toplevel
    if hasattr(config, name):
        return getattr(config, name)

    name = name.upper()
    if hasattr(config, name):
        return getattr(config, name)

    # do we have fallback value we can use in our SAMPLE-config.py file?
    from importlib import import_module # pylint: disable=import-outside-toplevel
    SAMPLE_config = import_module('SAMPLE-config') # pylint: disable=invalid-name
    if hasattr(SAMPLE_config, name):
        print(f'Warning: "{name}" is missing in your config.py file,'
              'using value from SAMPLE-config.py')
        return getattr(SAMPLE_config, name)

    print(f'FATAL: "{name}" is missing in your config.py and SAMPLE-config.py files')
    raise ValueError(f'FATAL: "{name}" is missing in your config.py and SAMPLE-config.py files')


def get_translation(module_name, lang_code):
    """
    Retrieves the gettext translation object for a specific language.

    This function loads the appropriate language translation for
    a given module from the 'locales' directory.

    Parameters:
    module_name (str): The name of the module for which the translation is needed.
    lang_code (str): The ISO 639-1 language code (e.g., 'en' for English, 'fr' for French).

    Returns:
    function: The gettext() function for the specified language.
    """
    language = gettext.translation(
        module_name,
        localedir='locales',
        languages=[lang_code])
    return language.gettext


def change_url_to_test_url(url, test_name):
    """
    Modifies the given URL by adding or updating the 'webperf-core' query
    parameter with the provided test name.
    
    Parameters:
    url (str): The original URL to be modified.
    test_name (str): The test name to be set as the value of the 'webperf-core' query parameter.

    Returns:
    str: The modified URL with the 'webperf-core' query parameter set to the provided test name.

    Notes:
    - If the original URL does not have any query parameters,
      the 'webperf-core' query parameter is added.
    - If the original URL already has one or more query parameters,
      the 'webperf-core' query parameter is added at the beginning.
    """
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
    """
    Checks if a file is older than a given time delta.

    Parameters:
    file (str): The path to the file to check.
    delta (datetime.timedelta): The time delta to compare the file's modification time against.

    Returns:
    bool: True if the file's modification time is older than the current time minus the given delta,
          False otherwise.

    Notes:
    - The function uses the file's modification time (mtime) for the comparison.
    - The current time is determined using datetime.utcnow().
    """
    cutoff = datetime.utcnow() - delta
    mtime = datetime.utcfromtimestamp(os.path.getmtime(file))
    if mtime < cutoff:
        return True
    return False

def get_cache_path_for_rule(url, cache_key_rule):
    """
    Generates a cache path for a given URL. The cache path is based on the hostname of the URL and
    a hash of the URL itself.
    The function also ensures that the necessary directories for storing the cache file exist.

    Parameters:
    url (str): The URL for which to generate a cache path.
    cache_key_rule (str): Determines the format of the cache file/folder name.
        {0} in rule will be replaced by a sha512 hexdigest for supplied url.

    Returns:
    str: The generated cache path.
    """
    o = urlparse(url)
    hostname = o.hostname
    if hostname is None:
        hostname = 'None'

    folder = 'tmp'
    if USE_CACHE:
        folder = 'cache'

    folder_path = os.path.join(folder)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    hostname_path = os.path.join(folder, hostname)
    if not os.path.exists(hostname_path):
        os.makedirs(hostname_path)

    cache_key = cache_key_rule.format(
        hashlib.sha512(url.encode()).hexdigest())
    cache_path = os.path.join(folder, hostname, cache_key)

    return cache_path

def get_cache_path_for_folder(url):
    """
    Generates a cache path for a given URL. The cache path is based on the hostname of the URL and
    a hash of the URL itself.
    The function also ensures that the necessary directories for storing the cache file exist.

    Parameters:
    url (str): The URL for which to generate a cache path.

    Returns:
    str: The generated cache path.
    """

    cache_key_rule = '{0}'

    return get_cache_path_for_rule(url, cache_key_rule)


def get_cache_path_for_file(url, use_text_instead_of_content):
    """
    Generates a cache path for a given URL. The cache path is based on the hostname of the URL and
    a hash of the URL itself.
    The function also ensures that the necessary directories for storing the cache file exist.

    Parameters:
    url (str): The URL for which to generate a cache path.
    use_text_instead_of_content (bool): Determines the format of the cache file. 
        If True, the cache file is in '.txt.utf-8' format. 
        If False, the cache file is in '.bytes' format.

    Returns:
    str: The generated cache path.
    """

    file_ending = '.tmp'
    if USE_CACHE:
        file_ending = '.cache'

    cache_key_rule = '{0}.txt.utf-8' + file_ending
    if not use_text_instead_of_content:
        cache_key_rule = '{0}.bytes' + file_ending

    return get_cache_path_for_rule(url, cache_key_rule)


def get_cache_file(url, use_text_instead_of_content, time_delta):
    """
    Retrieves the content of a cache file for a given URL if it exists and
    is not older than a given time delta.

    Parameters:
    url (str): The URL for which to retrieve the cache file.
    use_text_instead_of_content (bool): Determines the format of the cache file.
        If True, the cache file is read as text.
        If False, the cache file is read as bytes.
    time_delta (datetime.timedelta): The maximum age of the cache file.
        If the cache file is older than this, None is returned.

    Returns:
    str or bytes or None: The content of the cache file if it exists and
    is not older than the given time delta.
    If the cache file does not exist or is too old, None is returned.

    Notes:
    - The function uses the get_cache_path_for_file function to determine the path of the cache file.
    - If USE_CACHE is False, the function always returns None.
    """
    cache_path = get_cache_path_for_file(url, use_text_instead_of_content)

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
    """
    Checks if a cache file exists for a given URL and if it's not older than a specified time delta.

    Parameters:
    url (str): The URL for which to check the cache file.
    use_text_instead_of_content (bool): Determines the type of content to be cached.
      If True, text is cached; otherwise, content is cached.
    time_delta (datetime.timedelta): The maximum age of the cache file.
      If the file is older than this, it's considered as not existing.

    Returns:
    bool: True if the cache file exists and is not older than the specified time delta,
          False otherwise.
    """
    cache_path = get_cache_path_for_file(url, use_text_instead_of_content)

    if not os.path.exists(cache_path):
        return False

    if USE_CACHE and is_file_older_than(cache_path, time_delta):
        return False

    return True


def clean_cache_files():
    """
    Cleans up cache files from the 'cache' directory and
    removes the 'tmp' directory if caching is not used.

    This function performs the following operations:
    1. If caching is not used (USE_CACHE is False), it removes the 'tmp' directory and returns.
    2. If caching is used, it goes through each file in each subdirectory of the 'cache' directory.
    3. For each file, if the file ends with '.cache',
       it checks if the file is older than CACHE_TIME_DELTA.
    4. If the file is older than CACHE_TIME_DELTA, it removes the file.

    The function also prints out the following information:
    - The number of files and folders in the 'cache' folder before cleanup.
    - The number of '.cache' files found.
    - The number of 'result' folders found.
    - The number of '.cache' files removed.
    - The number of 'result' folders removed.

    Note: The function uses the USE_CACHE and CACHE_TIME_DELTA global variables.
    """
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
    """
    Writes the given content to a cache file.

    The cache file path is determined by the given URL and the flag 
    `use_text_instead_of_content`. If the flag is True, the content is 
    written as text. Otherwise, it's written as binary.

    Args:
        url (str): The URL to determine the cache file path.
        content (str or bytes): The content to write to the cache file.
        use_text_instead_of_content (bool): Flag to determine how to write 
                                             the content.
    """
    cache_path = get_cache_path_for_file(url, use_text_instead_of_content)
    if use_text_instead_of_content:
        with open(cache_path, 'w', encoding='utf-8', newline='') as file:
            file.write(content)
    else:
        with open(cache_path, 'wb') as file:
            file.write(content)

def get_http_content(url, allow_redirects=False, use_text_instead_of_content=True):
    """
    Retrieves the content of the specified URL and caches it.

    This function first checks if the content is already cached. If it is, 
    the cached content is returned. If not, a GET request is sent to the 
    URL. The content of the response is then cached and returned.

    In case of SSL or connection errors, the function retries the request 
    using HTTPS if the original URL used HTTP. If the request times out, 
    an error message is printed.

    Args:
        url (str): The URL to retrieve the content from.
        allow_redirects (bool, optional): Whether to follow redirects. 
                                           Defaults to False.
        use_text_instead_of_content (bool, optional): Whether to retrieve 
                                                      the response content 
                                                      as text (True) or 
                                                      binary (False). 
                                                      Defaults to True.

    Returns:
        str or bytes: The content of the URL.
    """
    try:
        content = get_cache_file(
            url, use_text_instead_of_content, CACHE_TIME_DELTA)
        if content is not None:
            return content

        headers = {'user-agent': USERAGENT}

        hostname = urlparse(url).hostname

        if hostname == 'api.github.com' and GITHUB_APIKEY is not None:
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
    except TimeoutError:
        print(
            'Error! Unfortunately the request for URL'
            f'"{url}" timed out.'
            f'The timeout is set to {REQUEST_TIMEOUT} seconds.\nMessage:\n{sys.exc_info()[0]}')
    return ''

def get_content_type(url, cache_time_delta):
    """
    Retrieves the content type of the specified URL.

    This function sends a GET request to the URL and retrieves the headers. 
    If the status code is 401, it returns 401. Otherwise, it checks the 
    headers for the 'Content-Type' field (case-insensitive) and returns its 
    value. If the 'Content-Type' field is not found, it returns None.

    Args:
        url (str): The URL to retrieve the content type from.
        cache_time_delta (int): The cache time delta.

    Returns:
        str or None: The content type of the URL, or None if not found.
    """
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
    """
    Retrieves the headers of the specified URL.

    This function first checks if the headers are already cached. If they are, 
    the cached headers are returned. If not, a HEAD request is sent to the URL. 
    The headers of the response are then cached and returned.

    In case of SSL or connection errors, the function prints an error message 
    and returns an empty dictionary. If the status code is 401, it returns a 
    dictionary with 'status-code' set to 401.

    Args:
        url (str): The URL to retrieve the headers from.
        cache_time_delta (int): The cache time delta.

    Returns:
        dict: The headers of the URL.
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
    return {}

def get_root_url(url):
    """
    Extracts the root URL from a given URL.

    This function uses Python's urllib.parse.urlparse method to parse the URL and
    extract the scheme and network location (netloc). 
    It then constructs the root URL from these components.

    Args:
        url (str): The URL to extract the root from.

    Returns:
        str: The root URL, which includes the scheme and netloc, followed by a forward slash.

    Example:
        >>> get_root_url('https://www.example.com/path/to/page?query=arg')
        'https://www.example.com/'
    """
    o = urllib.parse.urlparse(url)
    parsed_url = f'{o.scheme}://{o.netloc}/'
    return parsed_url


def has_redirect(url):
    """
    Checks if a URL has a redirect.

    Args:
        url (str): The URL to check.

    Returns:
        tuple: A tuple containing:
            - bool: True if the URL has a redirect, False otherwise.
            - str or None: The redirected URL if available, None otherwise.
            - str: Error message if any (empty string if no error).
    """
    error_msg = None
    try:
        headers = {'user-agent': USERAGENT}
        response = requests.get(url, allow_redirects=True,
                         headers=headers, timeout=REQUEST_TIMEOUT*2)

        return (url != response.url, response.url, '')
    except ssl.CertificateError as error:
        print(f'Info: Certificate error. {error.reason}')
        error_msg = f'Info: Certificate error. {error.reason}'
    except requests.exceptions.SSLError:
        error_msg = 'Unable to verify: SSL error occured'
    except requests.exceptions.ConnectionError:
        error_msg = 'Unable to verify: connection error occured'
    return (False, None, error_msg)


def get_guid(length):
    """
    Generates a unique string of specified length.

    Args:
        length (int): The desired length of the generated string.

    Returns:
        str: A unique string of the specified length.
    """
    return str(uuid.uuid4())[0:length]


def convert_to_seconds(millis, return_with_seconds=True):
    """
    Converts milliseconds to seconds.

    Args:
        millis (int): The input time in milliseconds.
        return_with_seconds (bool, optional): 
            If True, returns the result with the word "sekunder" (seconds).
            Otherwise, returns the numeric value only. Defaults to True.

    Returns:
        str or float: The converted time in seconds (with "sekunder" if specified).
    """
    if return_with_seconds:
        return (millis/1000) % 60 + " sekunder"
    return (millis/1000) % 60


def dns_lookup(key, datatype):
    """
    Performs a DNS lookup for the specified key and data type.

    Args:
        key (str): The domain or hostname to look up.
        datatype (int): The DNS record type (e.g., A, AAAA, MX, CNAME).

    Returns:
        list: A list containing the DNS records found for the given key.
    """
    use_dnssec = False
    cache_key = f'dnslookup://{key}#{datatype}#{use_dnssec}'
    if has_cache_file(cache_key, True, CACHE_TIME_DELTA):
        cache_path = get_cache_path_for_file(cache_key, True)
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
            # print('\t\tERROR, RCODE is INVALID:', response.rcode())
            return []

        text_response = response.to_text()
        set_cache_file(cache_key, text_response, True)

        time.sleep(5)

        return dns_response_to_list(response)
    except dns.query.BadResponse as br:
        print('\t\tDNS Bad response', br)
    except dns.exception.Timeout:
        print('\t\tDNS Timeout')
    except dns.resolver.NoAnswer:
        # this is expected when for example no 'AAAA' record.
        return []
    except dns.resolver.NXDOMAIN:
        # this is expected when for example no MTA domain.
        return []
    except dns.dnssec.ValidationFailure as vf:
        print('\t\tDNS FAIL', vf)
    except dns.name.BadEscape as be:
        print('\t\tDNS BAD Escape for:', key, be)

    return []

def dns_response_to_list(dns_response):
    """
    Converts a DNS response to a list of names.

    Args:
        dns_response (dns.message.Message): The DNS response object.

    Returns:
        list: A list of names extracted from the DNS response.
    """
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
    """
    Returns a dictionary of European Union (EU) country codes and their corresponding full names.

    Returns:
        dict: A dictionary where keys are two-letter country codes (e.g., 'BE' for Belgium)
              and values are the full country names (e.g., 'Belgium').
    """
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
    """
    Returns a dictionary of non-European Union (EU) countries that have been granted
    data protection adequacy decisions by the European Commission.

    The country codes and their corresponding full names are sourced from official documents and
    Wikipedia.

    Returns:
        dict: A dictionary where keys are two-letter country codes (e.g., 'NO' for Norway)
              and values are the full country names (e.g., 'Norway').
    """
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
    """
    Checks if a given two-letter country code corresponds to a European Union (EU) member country.

    Args:
        country_code (str): A two-letter country code (e.g., 'SE' for Sweden).

    Returns:
        bool: True if the country code corresponds to an EU member country, False otherwise.
    """
    country_codes = get_eu_countries()
    if country_code in country_codes:
        return True

    return False


def is_country_code_in_exception_list(country_code):
    """
    Checks if a given country code is in the exception list.
    This function retrieves the list of exception countries and
    checks if the provided country code is in that list.

    Args:
        country_code (str): The country code to check.

    Returns:
        bool: True if the country code is in the exception list, False otherwise.
    """
    country_codes = get_exception_countries()
    if country_code in country_codes:
        return True

    return False


def is_country_code_in_eu_or_on_exception_list(country_code):
    """
    Checks if a given country code is in the EU or the exception list.
    This function checks if the provided country code is either in the list of EU countries or
    in the exception list.

    Args:
        country_code (str): The country code to check.

    Returns:
        bool: True if the country code is in the EU or the exception list, False otherwise.
    """
    return is_country_code_in_eu(country_code) or is_country_code_in_exception_list(country_code)


def get_country_code_from_ip2location(ip_address):
    """
    Retrieves the country code associated with an IP address using the IP2Location database.
    This function attempts to retrieve the record associated with the given IP address from
    the IP2Location database.
    If the record exists and has a 'country_short' attribute, the function returns the country code.
    If the record does not exist or an exception occurs during retrieval,
    the function returns an empty string.

    Args:
        ip_address (str): The IP address to look up.

    Returns:
        str: The country code associated with the IP address,
        or an empty string if the country code could not be retrieved.
    """
    rec = False
    try:
        rec = IP2_LOCATION_DB.get_all(ip_address)
    except Exception: # pylint: disable=broad-exception-caught
        return ''
    if hasattr(rec, 'country_short'):
        countrycode = rec.country_short
        return countrycode
    return ''


def get_best_country_code(ip_address, default_country_code):
    """
    Determines the best country code based on an IP address and a default country code.
    This function first checks if the default country code is in the EU or
    the exception list. If it is, the function returns the default country code.
    If not, the function attempts to retrieve the country code associated with
    the given IP address from the IP2Location database.
    If the country code could not be retrieved,
    the function returns the default country code.

    Args:
        ip_address (str): The IP address to look up.
        default_country_code (str):
            The default country code to use if the IP address is not
            associated with a country code in the EU or the exception list.

    Returns:
        str: The best country code, either from the IP address or the default.
    """
    if is_country_code_in_eu_or_on_exception_list(default_country_code):
        return default_country_code

    country_code = get_country_code_from_ip2location(ip_address)
    if country_code == '':
        return default_country_code

    return country_code

def get_friendly_url_name(global_translation, url, request_index):
    """
    Generates a friendly name for a given URL and request index.
    This function generates a friendly name for a given URL and request index.
    If the request index is None, it is replaced with a '?'.
    The function then attempts to parse the URL and extract the last part of the path,
    replacing any non-alphanumeric characters with '-'.
    If the length of this part is greater than 15, only the first 15 characters are used.
    If an exception occurs during this process, the function returns a default friendly name.

    Args:
        _ (function): A function for localization. This argument is not used in the function.
        url (str): The URL to generate a friendly name for.
        request_index (int or None): The index of the request.

    Returns:
        str: The friendly name for the URL.
    """

    if request_index is None:
        request_index = '?'

    request_friendly_name = global_translation(
        'TEXT_REQUEST_UNKNOWN').format(request_index)
    if request_index == 1:
        request_friendly_name = global_translation(
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
    except ValueError:
        return request_friendly_name
    return request_friendly_name

def merge_dicts(dict1, dict2, sort, make_distinct):
    """
    Merges two dictionaries into one. If the same key exists in both dictionaries, 
    the function handles the merging based on the type of the value.

    Parameters:
    dict1 (dict): The first dictionary to merge.
    dict2 (dict): The second dictionary to merge.
    sort (bool): If True, the function will sort the values if they are of type list.
    make_distinct (bool): If True, the function will remove duplicate values from lists.

    Returns:
    dict: The merged dictionary.
    """
    if dict1 is None:
        return dict2
    if dict2 is None:
        return dict1

    for domain, value in dict2.items():
        if domain not in dict1:
            dict1[domain] = value
            continue

        if isinstance(value, dict):
            merge_dict_values(dict1, dict2, domain, sort, make_distinct)
        elif isinstance(value, list):
            merge_list_values(dict1, dict2, domain, sort, make_distinct)
        elif isinstance(value, int):
            dict1[domain] += value

    return dict1

def merge_dict_values(dict1, dict2, domain, sort, make_distinct):
    """
    Merges the values of two dictionaries based on a common domain.

    Parameters:
    dict1 (dict): The first dictionary.
    dict2 (dict): The second dictionary.
    domain (str): The common domain in both dictionaries.
    sort (bool): If True, the merged list will be sorted.
    make_distinct (bool):
        If True, the merged list will only contain distinct values.

    Returns:
    None: The function modifies dict1 in-place, adding the values from dict2.

    Note:
    This function recursively merges the dictionaries and
    lists within the dictionaries.
    """
    for subkey, subvalue in dict2[domain].items():
        if subkey not in dict1[domain]:
            dict1[domain][subkey] = subvalue
            continue

        if isinstance(subvalue, dict):
            merge_dicts(dict1[domain][subkey], dict2[domain][subkey], sort, make_distinct)
        elif isinstance(subvalue, list):
            merge_list_values(dict1[domain], dict2[domain], subkey, sort, make_distinct)

def merge_list_values(dict1, dict2, key, sort, make_distinct):
    """
    Merges the values of two dictionaries based on a common key.

    Parameters:
    dict1 (dict): The first dictionary.
    dict2 (dict): The second dictionary.
    key (str): The common key in both dictionaries.
    sort (bool): If True, the merged list will be sorted.
    make_distinct (bool): 
        If True, the merged list will only contain distinct values.

    Returns:
    None: The function modifies dict1 in-place, adding the values from dict2.
    """
    dict1[key].extend(dict2[key])
    if make_distinct:
        dict1[key] = list(set(dict1[key]))
    if sort:
        dict1[key] = sorted(dict1[key])


IP2_LOCATION_DB = False
try:
    IP2_LOCATION_DB = IP2Location.IP2Location(
        os.path.join("data", "IP2LOCATION-LITE-DB1.IPV6.BIN"))
except ValueError as ex:
    print('Unable to load IP2Location Database from "data/IP2LOCATION-LITE-DB1.IPV6.BIN"', ex)

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
USE_CACHE = get_config_or_default('cache_when_possible')
CACHE_TIME_DELTA = get_config_or_default('cache_time_delta')
DNS_SERVER = get_config_or_default('DNS_SERVER')
GITHUB_APIKEY = get_config_or_default('GITHUB_API_KEY')
