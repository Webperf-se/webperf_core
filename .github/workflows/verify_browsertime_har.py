# -*- coding: utf-8 -*-
from pathlib import Path
import os
import os.path
import ssl
import sys
import getopt
import json
import shutil
import re
import requests

# DEFAULTS
REQUEST_TIMEOUT = 60
USERAGENT = 'Mozilla/5.0 (compatible; Windows NT 10.0; Win64; x64) ' \
     'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36 Edg/88.0.705.56'

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
        headers = {'user-agent': USERAGENT}
        response = requests.get(url, allow_redirects=allow_redirects,
                         headers=headers, timeout=REQUEST_TIMEOUT*2)

        if use_text_instead_of_content:
            content = response.text
        else:
            content = response.content

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
            f'The timeout is set to {REQUEST_TIMEOUT} seconds.\nMessage:\n{sys.exc_info()[0]}')
    return ''

def print_file_content(input_filename):
    """
    Prints the content of a file line by line.

    This function performs the following steps:
    1. Prints the name of the input file.
    2. Opens the input file in read mode.
    3. Reads the file line by line.
    4. Prints each line.

    Args:
        input_filename (str): The path to the file to be read.

    Note: This function assumes that the file exists and can be opened.
      If the file does not exist or cannot be opened, an error will occur.
    """

    print('input_filename=' + input_filename)
    with open(input_filename, 'r', encoding="utf-8") as file:
        data = file.readlines()
        for line in data:
            print(line)

def get_file_content(input_filename):
    """
    Reads the content of a file and returns it as a string.

    This function performs the following steps:
    1. Opens the input file in read mode.
    2. Reads the file line by line and stores each line in a list.
    3. Joins the list of lines into a single string with newline characters between each line.

    Args:
        input_filename (str): The path to the file to be read.

    Returns:
        str: The content of the file as a string.

    Note: This function assumes that the file exists and can be opened.
      If the file does not exist or cannot be opened, an error will occur.
    """

    with open(input_filename, 'r', encoding='utf-8', newline='') as file:
        data = file.read()
        return data

def get_content(url, allow_redirects=False, use_text_instead_of_content=True):
    """Trying to fetch the response content
    Attributes: url, as for the URL to fetch
    """

    try:
        headers = {
            'user-agent': (
                'Mozilla/5.0 (compatible; Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 '
                'Safari/537.36 Edg/88.0.705.56'
            )
        }

        a = requests.get(url, allow_redirects=allow_redirects,
                         headers=headers, timeout=120)

        if use_text_instead_of_content:
            content = a.text
        else:
            content = a.content
        return content
    except ssl.CertificateError as error:
        print(f'Info: Certificate error. {error.reason}')
    except requests.exceptions.SSLError as error:
        if 'http://' in url:  # trying the same URL over SSL/TLS
            print('Info: Trying SSL before giving up.')
            return get_content(url.replace('http://', 'https://'))
        print(f'Info: SSLError. {error}')
        return ''
    except requests.exceptions.ConnectionError as error:
        if 'http://' in url:  # trying the same URL over SSL/TLS
            print('Connection error! Info: Trying SSL before giving up.')
            return get_content(url.replace('http://', 'https://'))
        print(
            f'Connection error! Unfortunately the request for URL "{url}" failed.'
            f'\nMessage:\n{sys.exc_info()[0]}')
        return ''
    except requests.exceptions.Timeout:
        print(
            f'Timeout error! Unfortunately the request for URL "{url}" timed out. '
            f'The timeout is set to {120} seconds.\n'
            f'Message:\n{sys.exc_info()[0]}')
    except requests.exceptions.RequestException as error:
        print(
            f'Error! Unfortunately the request for URL "{url}" failed for other reason(s).\n'
            f'Message:\n{error}')
    return ''

def set_file(file_path, content, use_text_instead_of_content):
    """
    Writes the provided content to a file at the specified path.

    If 'use_text_instead_of_content' is True,
        the function opens the file in text mode and writes the content as a string.
    If 'use_text_instead_of_content' is False,
        the function opens the file in binary mode and writes the content as bytes.

    Args:
        file_path (str): The path to the file where the content will be written.
        content (str or bytes): The content to be written to the file.
        use_text_instead_of_content (bool): 
            Determines whether the file is opened in text or binary mode.

    Returns:
        None
    """
    if use_text_instead_of_content:
        with open(file_path, 'w', encoding='utf-8', newline='') as file:
            file.write(content)
    else:
        with open(file_path, 'wb') as file:
            file.write(content)

def main(argv):
    """
    WebPerf Core - Regression Test

    Usage:
    verify_result.py -h

    Options and arguments:
    -h/--help\t\t\t: Verify Help command
    -d/--docker <activate feature, True or False>\t\t:
      Updates DockerFile to use latest browsers
    -t/--test <test number>\t: Verify result of specific test

    NOTE:
    If you get this in step "Setup config [...]" you forgot to
    add repository secret for your repository.
    More info can be found here: https://github.com/Webperf-se/webperf_core/issues/81
    """

    try:
        opts, _ = getopt.getopt(argv, "hlt:d:s:b:", [
                                   "help", "test=", "sample-config=",
                                   "browsertime=",
                                   "language", "docker="])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if len(opts) == 0:
        print(main.__doc__)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):  # help
            print(main.__doc__)
            sys.exit(0)
        elif opt in ("-b", "--browsertime"):  # validate browsertime.har for supported browsers
            handle_validate_browsertime(arg)

    # No match for command so return error code to fail verification
    sys.exit(2)

def set_file_content(file_path, content):
    """
    Writes the given content to a file at the specified path.

    This function checks if the file exists at the given path.
    If the file does not exist, it prints an error message and returns.
    If the file does exist, it opens the file in write mode with UTF-8 encoding and
    writes the provided content to the file.

    Args:
        file_path (str): The path to the file.
        content (str): The content to be written to the file.

    Returns:
        None
    """
    if not os.path.isfile(file_path):
        print(f"ERROR: No {file_path} file found!")
        return

    with open(file_path, 'w', encoding='utf-8', newline='') as file:
        file.write(content)

def handle_validate_browsertime(browsertime_har_path):
    is_ok = True
    with open(browsertime_har_path, encoding='utf-8') as json_input_file:
        browsertime_har = json.load(json_input_file)
        if 'log' not in browsertime_har:
            print('Error: log is missing in browsertime.har file')
            sys.exit(2)

        if 'version' not in browsertime_har['log']:
            print('Error: log.version is missing in browsertime.har file')
            is_ok = False

        if 'creator' not in browsertime_har['log']:
            print('Error: log.creator is missing in browsertime.har file')
            is_ok = False
        else:
            if 'name' not in browsertime_har['log']['creator']:
                print('Error: log.creator.name is missing in browsertime.har file')
                is_ok = False
            if 'version' not in browsertime_har['log']['creator']:
                print('Error: log.creator.version is missing in browsertime.har file')
                is_ok = False

        if 'browser' not in browsertime_har['log']:
            print('Error: log.browser is missing in browsertime.har file')
            is_ok = False
        else:
            if 'name' not in browsertime_har['log']['browser']:
                print('Error: log.browser.name is missing in browsertime.har file')
                is_ok = False
            if browsertime_har['log']['browser']['name'] not in ('firefox', 'Chrome'):
                print(f'Error: log.browser.name has wrong value, actual value: {browsertime_har['log']['browser']['name']}')
                is_ok = False

            if 'version' not in browsertime_har['log']['browser']:
                print('Error: log.browser.version is missing in browsertime.har file')
                is_ok = False
            if re.match(r'[0-9\.]+', browsertime_har['log']['browser']['version'], re.IGNORECASE) is None:
                print(f'Error: log.browser.name has wrong value, actual value: {browsertime_har['log']['browser']['version']}')
                is_ok = False

        if 'pages' not in browsertime_har['log']:
            print('Error: log.pages array is missing in browsertime.har file')
            is_ok = False
        else:
            page_index = 0
            for page in browsertime_har['log']['pages']:
                if 'id' not in page:
                    print(f'Error: log.pages[{page_index}].id is missing in browsertime.har file')
                    is_ok = False
                if f'page_{page_index +1 }' not in page['id']:
                    print(f'Error: log.pages[{page_index}].id has wrong value, actual value: {page['id']}')
                    is_ok = False

                if 'startedDateTime' not in page:
                    print(f'Error: log.pages[{page_index}].startedDateTime is missing in browsertime.har file')
                    is_ok = False
                if re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{3}Z', page['startedDateTime']) is None:
                    print(f'Error: log.pages[{page_index}].startedDateTime property is wrong value in browsertime.har file')
                    is_ok = False

                if 'title' not in page:
                    print(f'Error: log.pages[{page_index}].title is missing in browsertime.har file')
                    is_ok = False
                if 'pageTimings' not in page:
                    print(f'Error: log.pages[{page_index}].pageTimings is missing in browsertime.har file')
                    is_ok = False

                if '_url' not in page:
                    print(f'Error: log.pages[{page_index}]._url is missing in browsertime.har file')
                    is_ok = False
                if page['_url'] != 'https://webperf.se':
                    print(f'Error: log.pages[{page_index}]._url has wrong value, actual value: {page['_url']}')
                    is_ok = False

                if '_meta' not in page:
                    print(f'Error: log.pages[{page_index}]._meta is missing in browsertime.har file')
                    is_ok = False
                page_index += 1
            if page_index < 1:
                print('Error: log.pages array has less than 1 page in browsertime.har file')
                is_ok = False

        if 'entries' not in browsertime_har['log']:
            print('Error: log.entries array is missing in browsertime.har file')
            is_ok = False
        else:
            entity_index = 0
            for entity in browsertime_har['log']['entries']:
                if 'cache' not in entity:
                    print(f'Error: log.entries[{entity_index}].id is missing in browsertime.har file')
                    is_ok = False

                if 'startedDateTime' not in entity:
                    print(f'Error: log.entries[{entity_index}].startedDateTime is missing in browsertime.har file')
                    is_ok = False
                elif re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{3}Z', entity['startedDateTime']) is None:
                    print(f'Error: log.entries[{entity_index}].startedDateTime property is wrong value in browsertime.har file')
                    is_ok = False

                if 'timings' not in entity:
                    print(f'Error: log.entries[{entity_index}].timings is missing in browsertime.har file')
                    is_ok = False

                if 'pageref' not in entity:
                    print(f'Error: log.entries[{entity_index}].pageref is missing in browsertime.har file')
                    is_ok = False
                elif entity['pageref'] != 'page_1':
                    print(f'Error: log.entries[{entity_index}].pageref has wrong value, actual value: {entity['pageref']}')
                    is_ok = False

                if 'time' not in entity:
                    print(f'Error: log.entries[{entity_index}].time is missing in browsertime.har file')
                    is_ok = False
                elif not isinstance(entity['time'], float):
                    print(f'Error: log.entries[{entity_index}].time has wrong value, actual value: {entity['time']}')
                    is_ok = False

                if 'request' not in entity:
                    print(f'Error: log.entries[{entity_index}].request is missing in browsertime.har file')
                    is_ok = False
                else:
                    if 'method' not in entity['request']:
                        print(f'Error: log.entries[{entity_index}].request.method is missing in browsertime.har file')
                        is_ok = False
                    elif entity['request']['method'] not in ('GET','POST'):
                        print(f'Error: log.entries[{entity_index}].request.method has wrong value, actual value: {entity['request']['method']}')
                        is_ok = False

                    if 'url' not in entity['request']:
                        print(f'Error: log.entries[{entity_index}].request.url is missing in browsertime.har file')
                        is_ok = False
                    elif entity_index == 0 and entity['request']['url'] != 'https://webperf.se/':
                        print(f'Error: log.entries[{entity_index}].request.url has wrong value, actual value: {entity['request']['url']}')
                        is_ok = False

                    if 'queryString' not in entity['request']:
                        print(f'Error: log.entries[{entity_index}].request.queryString is missing in browsertime.har file')
                        is_ok = False
                    elif entity_index == 0 and entity['request']['queryString'] != []:
                        print(f'Error: log.entries[{entity_index}].request.queryString has wrong value, actual value: {entity['request']['queryString']}')
                        is_ok = False

                    if 'headersSize' not in entity['request']:
                        print(f'Error: log.entries[{entity_index}].request.headersSize is missing in browsertime.har file')
                        is_ok = False
                    elif not isinstance(entity['request']['headersSize'], int) or entity['request']['headersSize'] == -1:
                        print(f'Error: log.entries[{entity_index}].request.headersSize has wrong value, actual value: {entity['request']['headersSize']}')
                        is_ok = False

                    if 'bodySize' not in entity['request']:
                        print(f'Error: log.entries[{entity_index}].request.bodySize is missing in browsertime.har file')
                        is_ok = False
                    elif not isinstance(entity['request']['bodySize'], int) or entity['request']['bodySize'] != 0:
                        print(f'Error: log.entries[{entity_index}].request.bodySize has wrong value, actual value: {entity['request']['bodySize']}')
                        is_ok = False

                    if 'cookies' not in entity['request']:
                        print(f'Error: log.entries[{entity_index}].request.cookies array is missing in browsertime.har file')
                        is_ok = False

                    if 'httpVersion' not in entity['request']:
                        print(f'Error: log.entries[{entity_index}].request.httpVersion is missing in browsertime.har file')
                        is_ok = False
                    elif entity['request']['httpVersion'] not in ('h2','h3'):
                        print(f'Error: log.entries[{entity_index}].request.httpVersion has wrong value, actual value: {entity['request']['httpVersion']}')
                        is_ok = False

                    if 'headers' not in entity['request']:
                        print(f'Error: log.entries[{entity_index}].request.headers array is missing in browsertime.har file')
                        is_ok = False

                if 'response' not in entity:
                    print(f'Error: log.entries[{entity_index}].response is missing in browsertime.har file')
                    is_ok = False
                if 'redirectURL' not in entity['response']:
                    print(f'Error: log.entries[{entity_index}].response.redirectURL is missing in browsertime.har file')
                    is_ok = False
                if 'status' not in entity['response']:
                    print(f'Error: log.entries[{entity_index}].response.status is missing in browsertime.har file')
                    is_ok = False
                if 'statusText' not in entity['response']:
                    print(f'Error: log.entries[{entity_index}].response.statusText is missing in browsertime.har file')
                    is_ok = False
                if 'content' not in entity['response']:
                    print(f'Error: log.entries[{entity_index}].response.content is missing in browsertime.har file')
                    is_ok = False
                if 'headersSize' not in entity['response']:
                    print(f'Error: log.entries[{entity_index}].response.headersSize is missing in browsertime.har file')
                    is_ok = False
                if 'bodySize' not in entity['response']:
                    print(f'Error: log.entries[{entity_index}].response.bodySize is missing in browsertime.har file')
                    is_ok = False
                if 'cookies' not in entity['response']:
                    print(f'Error: log.entries[{entity_index}].response.cookies array is missing in browsertime.har file')
                    is_ok = False
                if 'httpVersion' not in entity['response']:
                    print(f'Error: log.entries[{entity_index}].response.httpVersion is missing in browsertime.har file')
                    is_ok = False
                if 'headers' not in entity['response']:
                    print(f'Error: log.entries[{entity_index}].response.headers array is missing in browsertime.har file')
                    is_ok = False

                entity_index += 1
            if entity_index < 1:
                print('Error: log.entries array has less than 1 entry in browsertime.har file')
                is_ok = False

    if is_ok:
        print('browsertime.har file is OK')
        sys.exit(0)
    else:
        sys.exit(2)

if __name__ == '__main__':
    main(sys.argv[1:])
