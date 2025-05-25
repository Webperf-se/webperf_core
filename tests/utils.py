# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import shutil
import sys
import ssl
import json
import time
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import urllib.parse
import uuid
import re
import os
from urllib.parse import ParseResult, urlparse, urlunparse
import gettext
import requests
import IP2Location
import dns
import dns.query
import dns.resolver
import dns.dnssec
import dns.exception
import dns.name

from helpers.setting_helper import get_config

CONFIG_WARNINGS = {}
IP2_LOCATION_DB = {
    'loaded': False,
    'database': None
}

def get_domain(url):
    """
    Extracts the domain name from a given URL.
    """
    parsed_url = urlparse(url)
    return parsed_url.hostname

def get_dependency_version(dependency_name):
    """
    Retrieves the version of a specified dependency from the 'package.json' file.

    Args:
        dependency_name (str): The name of the dependency.

    Returns:
        str: The version of the specified dependency, or 'latest' if not found.
    """
    with open('package.json', encoding='utf-8') as json_input_file:
        package_info = json.load(json_input_file)

        if 'dependencies' not in package_info:
            return 'latest'

        if dependency_name not in package_info['dependencies']:
            return 'latest'

        return package_info['dependencies'][dependency_name]


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
    language = gettext.translation(module_name,
        localedir='locales', languages=[lang_code])
    return language.gettext

def create_or_append_translation(module_name, lang_code, text_key):
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent
    locales_dir = os.path.join(base_directory.resolve(), 'locales') + os.sep
    lang_dir = os.path.join(locales_dir, lang_code, 'LC_MESSAGES') + os.sep
    if not os.path.exists(lang_dir):
        os.makedirs(lang_dir)

    module_filepath = os.path.join(lang_dir, f'{module_name}.po')

    content = None
    if os.path.exists(module_filepath):
        with open(module_filepath, 'r', encoding='utf-8', newline='') as file:
            content = ''.join(file.readlines())
    else:
        this_year = datetime.now().year
        today = datetime.now().strftime("%Y-%m-%d %H:%M%z")
        content = (
            f'# Copyright (C) {this_year} WebPerf\n'
            f'# FIRST AUTHOR <your-email-here@webperf.se>, {this_year}.\n'
            '#\n'
            'msgid ""\n'
            'msgstr ""\n'
            '"Project-Id-Version: PACKAGE VERSION\\n"\n'
            f'"POT-Creation-Date: {today}\\n"\n'
            f'"PO-Revision-Date: {today}\\n"\n'
            '"Last-Translator: Your-Name-Here <your-email-here@webperf.se>\\n"\n'
            '"Language-Team: English <team@webperf.se>\\n"\n'
            '"MIME-Version: 1.0\\n"\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
            '"Content-Transfer-Encoding: 8bit\\n"\n'
            '"Generated-By: pygettext.py 1.5\\n"\n'
            '#\n'
            '# Example(s):\n'
            '# Please note that msgid has to be unique in each file.\n'
            '# {0} in msgstr will add the severity, one of (critical, error, warning, resolved).\n'
            '\n'
            f'msgid "rule-id (unresolved)"\n'
            f'msgstr "Text to show instead of msgid, showed for severity levels (critical, error and warning)"\n'
            '\n'
            f'msgid "rule-id (resolved)"\n'
            f'msgstr "Text to show instead of msgid, here unique on severity level resolved"\n'
            '\n'
            f'msgid "rule-id"\n'
            f'msgstr "Text to show instead of msgid, here independent of severity level"\n'
            '\n'
            '# End of Examples\n\n'
            )

    if f'msgid "{text_key} (unresolved)"' not in content:
        content_to_append = (
                '\n'
                f'msgid "{text_key} (unresolved)"\n'
                f'msgstr "{text_key} ({{0}})"\n'
            )
        content += content_to_append

    if f'msgid "{text_key} (resolved)"' not in content:
        content_to_append = (
                '\n'
                f'msgid "{text_key} (resolved)"\n'
                f'msgstr "{text_key} (resolved)"\n'
            )
        content += content_to_append

    with open(module_filepath, 'w', encoding='utf-8', newline='') as file:
        file.write(content)

def standardize_url(url):
    o = urllib.parse.urlparse(url)

    path = o.path
    if path == '':
        path = '/'
    o2 = ParseResult(
        scheme=o.scheme, netloc=o.netloc, path=path,
        params=o.params, query=o.query, fragment=o.fragment)
    return urlunparse(o2)

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
        scheme=o.scheme, netloc=o.netloc, path=o.path,
        params=o.params, query=new_query, fragment=o.fragment)
    return standardize_url(urlunparse(o2))


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

    # Parse the URL into components 
    tmp_parsed_url = urllib.parse.urlparse(url)
    if tmp_parsed_url.query is not None and tmp_parsed_url.query != '':
        if tmp_parsed_url.query.find('%') != -1:
            unencoded_query = urllib.parse.unquote(tmp_parsed_url.query)
            url = f"{tmp_parsed_url.scheme}://{tmp_parsed_url.netloc}{tmp_parsed_url.path}?{unencoded_query}"

    o = urlparse(url)
    hostname = o.hostname
    if hostname is None:
        hostname = 'None'

    folder = 'tmp'
    if get_config('general.cache.use'):
        folder = get_config('general.cache.folder')

    folder_path = os.path.join(folder)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    hostname_path = os.path.join(folder, hostname)
    if not os.path.exists(hostname_path):
        os.makedirs(hostname_path)

    cache_key = cache_key_rule.format(hashlib.sha512(url.encode()).hexdigest())
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
    if get_config('general.cache.use'):
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
    - The function uses the get_cache_path_for_file function
      to determine the path of the cache file.
    - If get_config('general.cache.use') is False, the function always returns None.
    """
    cache_path = get_cache_path_for_file(url, use_text_instead_of_content)
    if not os.path.exists(cache_path):
        return None
    if get_config('general.cache.use') and is_file_older_than(cache_path, time_delta):
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
    if get_config('general.cache.use') and is_file_older_than(cache_path, time_delta):
        return False
    return True


def clean_cache_files():
    """
    Cleans up cache files from the 'cache' directory and
    removes the 'tmp' directory if caching is not used.

    This function performs the following operations:
    1. If caching is not used (get_config('general.cache.use') is False),
       it removes the 'tmp' directory and returns.
    2. If caching is used, it goes through each file in each subdirectory of the 'cache' directory.
    3. For each file, if the file ends with '.cache',
       it checks if the file is older than get_config('general.cache.max-age').
    4. If the file is older than get_config('general.cache.max-age'), it removes the file.

    The function also prints out the following information:
    - The number of files and folders in the 'cache' folder before cleanup.
    - The number of '.cache' files found.
    - The number of 'result' folders found.
    - The number of '.cache' files removed.
    - The number of 'result' folders removed.

    Note: The function uses the get_config('general.cache.use') and
          get_config('general.cache.max-age') global variables.
    """
    if not get_config('general.cache.use'):
        # If we don't want to cache stuff, why complicate stuff, just empy tmp folder when done
        folder = 'tmp'
        base_directory = os.path.join(Path(os.path.dirname(
            os.path.realpath(__file__)) + os.path.sep).parent, folder)
        if os.path.exists(base_directory):
            shutil.rmtree(base_directory)
        return
    file_ending = '.cache'
    folder = get_config('general.cache.folder')
    base_directory = os.path.join(Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent, folder)

    clean_folder(folder, base_directory, file_ending)

def clean_folder(folder, base_directory, file_ending):
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
                if not get_config('general.cache.use') or\
                        is_file_older_than(
                            path,
                            timedelta(minutes=get_config('general.cache.max-age'))):
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

def get_http_content(url, allow_redirects=False, use_text_instead_of_content=True): # pylint: disable=too-many-branches
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
            url,
            use_text_instead_of_content,
            timedelta(minutes=get_config('general.cache.max-age')))
        if content is not None:
            return content

        headers = {'user-agent': get_config('useragent')}
        hostname = urlparse(url).hostname
        if hostname == 'api.github.com' and get_config('github.api.key') is not None:
            headers['authorization'] = f"Bearer {get_config('github.api.key')}"
        response = requests.get(url, allow_redirects=allow_redirects,
                         headers=headers, timeout=get_config('general.request.timeout')*2)

        if use_text_instead_of_content:
            content = response.text
        else:
            content = response.content

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
            'Connection error! Unfortunately the request for URL '
            f'"{url}" failed.\nMessage:\n{sys.exc_info()[0]}')
    except requests.exceptions.MissingSchema as error:
        print(
            'Connection error! Missing Schema for '
            f'"{url}"')
    except requests.exceptions.TooManyRedirects as error:
        print(
            'Connection error! Too many redirects for '
            f'"{url}"')
    except requests.exceptions.InvalidURL:
        print(
            'Connection error! Invalid url '
            f'"{url}"')
    except TimeoutError:
        print(
            'Error! Unfortunately the request for URL '
            f'"{url}" timed out.'
            f"The timeout is set to {get_config('general.request.timeout')} seconds."
            f"\nMessage:\n{sys.exc_info()[0]}")
    return ''

def get_content_type(url):
    """
    Retrieves the content type of the specified URL.

    This function sends a GET request to the URL and retrieves the headers. 
    If the status code is 401, it returns 401. Otherwise, it checks the 
    headers for the 'Content-Type' field (case-insensitive) and returns its 
    value. If the 'Content-Type' field is not found, it returns None.

    Args:
        url (str): The URL to retrieve the content type from.
        get_config('general.cache.max-age') (int): The cache time delta.

    Returns:
        str or None: The content type of the URL, or None if not found.
    """
    headers = get_url_headers(url, timedelta(minutes=get_config('general.cache.max-age')))

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

        headers = {'user-agent': get_config('useragent')}
        a = requests.head(url, allow_redirects=True,
                         headers=headers, timeout=get_config('general.request.timeout')*2)

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
        headers = {'user-agent': get_config('useragent')}
        response = requests.get(url, allow_redirects=True,
                         headers=headers, timeout=get_config('general.request.timeout')*2)

        return (url != response.url, response.url, '')
    except ssl.CertificateError as error:
        print(f'Info: Certificate error. {error.reason}')
        error_msg = f'Info: Certificate error. {error.reason}'
    except requests.exceptions.SSLError:
        error_msg = 'Unable to verify: SSL error occured'
    except requests.exceptions.ConnectionError:
        error_msg = 'Unable to verify: connection error occured'
    except requests.exceptions.TooManyRedirects:
        error_msg = 'Unable to verify: Too many redirects'
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
    if has_cache_file(cache_key, True, timedelta(minutes=get_config('general.cache.max-age'))):
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
        response = dns.query.udp(query, get_config('general.dns.address'))

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
        ensure_ip2_location_db()
        rec = IP2_LOCATION_DB['database'].get_all(ip_address)
    except Exception: # pylint: disable=broad-exception-caught
        return ''
    if hasattr(rec, 'country_short'):
        return rec.country_short
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

def calculate_score(issues):
    category_scores = {'overall': 100}

    for issue in issues:
        if issue['category'] not in category_scores:
            category_scores[issue['category']] = 100

        if issue['severity'] == 'critical':
            category_scores[issue['category']] -= 25
        elif issue['severity'] == 'error':
            category_scores[issue['category']] -= 10
        elif issue['severity'] == 'warning':
            category_scores[issue['category']] -= 1

    scores = [value for key, value in category_scores.items() if key != 'overall']  # Exclude 'overall' from calculation
    total = sum(scores)
    category_scores['overall'] = total / len(scores) if scores else 100  # Use average

    return category_scores

def calculate_rating(global_translation, rating, result_dict):
    issues_other = []
    issues_standard =[]
    issues_security = []
    issues_a11y = []
    issues_performance = []

    if "groups" not in result_dict:
        return rating

    for group_name, info in result_dict["groups"].items():
        for issue in info["issues"]:
            if get_config('general.review.improve-only') and issue["severity"] == "resolved":
                continue

            severity_text = global_translation(f"TEXT_SEVERITY_{issue['severity'].upper()}")
            text = None
            if 'test' not in issue:
                text = f"{issue['rule']} ({severity_text})"
            elif 'text' in issue:
                text = issue['text']
            else:
                severity_key = None
                if issue['severity'] in ('resolved'):
                    severity_key = 'resolved'
                elif issue['severity'] in ('critical', 'error', 'warning'):
                    severity_key = 'unresolved'
                elif issue['severity'] in ('info'):
                    severity_key = 'info'
                else:
                    severity_key = 'unknown'
                text_primarykey = f"{issue['rule']} ({severity_key})"
                text_secondarykey = f"{issue['rule']}"
                try:
                    local_translation = get_translation(
                            issue['test'],
                            get_config('general.language')
                        )
                    text = local_translation(text_primarykey)
                    if '{0}' in text:
                            text = local_translation(text_primarykey).format(severity_text)
                    if text == text_primarykey:
                        print(f"no translation found for: {issue['test']}, and language: {get_config('general.language')}. Adding it so you can translate it.")
                        create_or_append_translation(issue['test'], get_config('general.language'), text_secondarykey)
                except FileNotFoundError:
                    text = text_primarykey
                    print(f"no translation found for: {issue['test']}, adding file for language: {get_config('general.language')} so you can translate it.")
                    create_or_append_translation(issue['test'], get_config('general.language'), text_secondarykey)

            if get_config('general.review.details'):
                if 'resources' in issue:
                    a1 ="\n  - ".join([f"{item}" for item in issue['resources']])
                    more_info = global_translation('TEXT_DETAILS_MORE_INFO')
                    # More info
                    text = f"{text}\n  {more_info}:\n  - {a1}\n"
                if 'subIssues' in issue and len(issue['subIssues']) > 0:
                    unique_urls = set(subItem['url'] for subItem in issue['subIssues'])
                    a2 = "\n  - ".join(unique_urls)
                    urls_with_issues  = global_translation('TEXT_DETAILS_URLS_WITH_ISSUES')
                    # Url(s) with issues
                    text = f"{text}\n  {urls_with_issues}:\n  - {a2}\n"

            if issue['category'] == 'standard':
                issues_standard.append(text)
            elif issue['category'] == 'security':
                issues_security.append(text)
            elif issue['category'] == 'a11y':
                issues_a11y.append(text)
            elif issue['category'] == 'performance':
                issues_performance.append(text)
            else:
                issues_other.append(text)

        if "score" not in info:
            # Calculate Score (for python packages who has not calculated this yet)
            info["score"] = calculate_score(info["issues"])

        if 'overall' in info["score"]:
            overall = (info["score"]["overall"] / 100) * 5
            rating.set_overall(overall)
            if len(issues_other) > 0:
                rating.overall_review = "\n".join([f"- {item}" for item in issues_other]) + "\n"
        if 'standard' in info["score"]:
            standard = (info["score"]["standard"] / 100) * 5
            rating.set_standards(standard)
            if len(issues_standard) > 0:
                rating.standards_review = "\n".join([f"- {item}" for item in issues_standard]) + "\n"
        if 'security' in info["score"]:
            security = (info["score"]["security"] / 100) * 5
            rating.set_integrity_and_security(security)
            if len(issues_security) > 0:
                rating.integrity_and_security_review = "\n".join([f"- {item}" for item in issues_security]) + "\n"
        if 'a11y' in info["score"]:
            a11y = (info["score"]["a11y"] / 100) * 5
            rating.set_a11y(a11y)
            if len(issues_a11y) > 0:
                rating.a11y_review = "\n".join([f"- {item}" for item in issues_a11y]) + "\n"
        if 'performance' in info["score"]:
            performance = (info["score"]["performance"] / 100) * 5
            rating.set_performance(performance)
            if len(issues_performance) > 0:
                rating.performance_review = "\n".join([f"- {item}" for item in issues_performance]) + "\n"
    return rating


def sort_testresult_issues(data):
    # Define the severity ranking
    severity_order = {
        "critical": 1,
        "error": 2,
        "warning": 3,
        "info": 4,
        "resolved": 5
    }

    if "groups" not in data:
        return

    # Access all groups in the JSON
    groups = data["groups"]

    # Iterate over each group and sort its issues
    for group_name, group_data in groups.items():
        issues = group_data.get("issues", [])
        
        # Sort issues by severity (primary) and number of subIssues (secondary)
        sorted_issues = sorted(
            issues,
            key=lambda x: (severity_order.get(x["severity"], float('inf')), -len(x.get("subIssues", [])))
        )
        # Update the group's issues with the sorted list
        group_data["issues"] = sorted_issues

def flatten_issues_dict(data):
    flattened = []

    for issue_key, issue_value in data.items():
        base_info = {k: v for k, v in issue_value.items()}
        flattened.append(base_info)

    return flattened

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

def ensure_ip2_location_db():
    """
    Ensures that the IP2Location database is loaded.

    If the database is already loaded, this function does nothing.
    Otherwise, it attempts to load the IP2Location database from the specified file path.

    Raises:
        ValueError: If loading the database fails.
    """
    if IP2_LOCATION_DB['loaded']:
        return
    try:
        IP2_LOCATION_DB['database'] = IP2Location.IP2Location(
            os.path.join("data", "IP2LOCATION-LITE-DB1.IPV6.BIN"))
        IP2_LOCATION_DB['loaded'] = True
    except ValueError as ex:
        print('Unable to load IP2Location Database from "data/IP2LOCATION-LITE-DB1.IPV6.BIN"', ex)
