# -*- coding: utf-8 -*-
from datetime import timedelta
import subprocess
import time
import json
from pathlib import Path
import os
import re
import shutil
import urllib
from urllib.parse import ParseResult, urlparse, urlunparse
import uuid
from tests.utils import change_url_to_test_url,\
    get_dependency_version, is_file_older_than,\
    get_translation, create_or_append_translation,\
    flatten_issues_dict
import engines.sitespeed_result as sitespeed_cache
from helpers.setting_helper import get_config
from helpers.browser_helper import get_chromium_browser



def get_webperf_json(filename):
    if not os.path.exists(filename):
        return None

    data_str = get_sanitized_browsertime(filename)
    return json.loads(data_str)

def create_webperf_json(url, sitespeed_plugins):
    # We don't need extra iterations for what we are using it for
    sitespeed_iterations = 1
    sitespeed_arg = (
            f'--shm-size=1g -b {get_chromium_browser()} '
            f'{sitespeed_plugins}'
            # '--plugins.remove screenshot --plugins.remove html --plugins.remove metrics '
            '--plugins.remove screenshot --plugins.remove metrics '
            '--browsertime.screenshot false --screenshot false --screenshotLCP false '
            '--browsertime.screenshotLCP false --chrome.cdp.performance false '
            '--browsertime.chrome.timeline false --videoParams.createFilmstrip false '
            '--visualMetrics false --visualMetricsPerceptual false '
            '--visualMetricsContentful false --browsertime.headless true '
            '--utc true '
            '--browsertime.chrome.args ignore-certificate-errors '
            f'-n {sitespeed_iterations}')
    if get_config('tests.sitespeed.xvfb'):
        sitespeed_arg += ' --xvfb'

    (folder, filename) = get_result(url,
        get_config('tests.sitespeed.docker.use'),
        sitespeed_arg,
        get_config('tests.sitespeed.timeout'))

    data = get_webperf_json(filename)
    return data

def to_firefox_url_format(url):
    """
    Converts a given URL to Firefox URL format.

    Args:
        url (str): The URL to be converted.

    Returns:
        str: The URL in Firefox format.
    """
    o = urllib.parse.urlparse(url)
    path = o.path
    if '' == o.path:
        path = '/'

    o2 = ParseResult(scheme=o.scheme,
                     netloc=o.netloc,
                     path=path,
                     params=o.params,
                     query=o.query,
                     fragment=o.fragment)
    url2 = urlunparse(o2)
    return url2

def get_result(url, sitespeed_use_docker, sitespeed_arg, timeout):
    """
    Retrieves the result of a site speed test for a given URL.

    Args:
        url (str): The URL to be tested.
        sitespeed_use_docker (bool): Whether to use Docker for the site speed test.
        sitespeed_arg (str): The arguments for the site speed test.
        timeout (int): The maximum time to wait for the test to complete.

    Returns:
        tuple: The name of the result folder and the filename of the HAR file.
    """
    folder = 'tmp'
    o = urlparse(url)
    hostname = o.hostname

    result_folder_name = os.path.join(folder, hostname, f'{str(uuid.uuid4())}')

    if get_config('tests.sitespeed.mobile'):
        url = change_url_to_test_url(url, 'mobile')
        sitespeed_arg += (' --mobile')

    sitespeed_arg += (' --postScript chrome-cookies.cjs --postScript chrome-versions.cjs '
                      f'--outputFolder {result_folder_name} {url}')

    filename = ''

    test = get_result_using_no_cache(sitespeed_use_docker, sitespeed_arg, timeout)
    test = test.replace('\\n', '\r\n').replace('\\\\', '\\')

    cookies_json = get_cookies(test)
    versions_json = get_versions(test)

    folder = os.path.join(result_folder_name, 'data')
    filename = os.path.join(result_folder_name, 'data', 'webperf-core.json')

    return (folder, filename)

def get_versions(test):
    """
    Extracts the versions from the test results.

    Args:
        test (str): The test results as a string.

    Returns:
        dict: A dictionary containing the versions.
    """
    regex = r"VERSIONS:START: (?P<VERSIONS>[^V]+) VERSIONS:END"
    versions = '{}'
    matches = re.finditer(
        regex, test, re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        versions = match.group('VERSIONS')
    versions_json = json.loads(versions)
    return versions_json

def get_cookies(test):
    """
    Extracts the cookies from the test results.

    Args:
        test (str): The test results as a string.

    Returns:
        dict: A dictionary containing the cookies.
    """
    regex = r"COOKIES:START: {\"cookies\":(?P<COOKIES>.+)} COOKIES:END"
    raw = '{}'
    matches = re.finditer(
        regex, test, re.MULTILINE)
    for _, match in enumerate(matches, start=1):
        raw = match.group('COOKIES')
    json_data = json.loads(raw)

    cookies = []
    for item_json in json_data:
        cookie = {}
        for key, value in item_json.items():
            if key in ('name', 'value', 'domain', 'path', 'httpOnly', 'secure'):
                cookie[key] = value
            elif key in ('expires'):
                if value != -1:
                    cookie[key] = value
            else:
                cookie[f'_{key}'] = value
        cookies.append(cookie)

    return cookies


def cleanup_results_dir(browsertime_path, path):
    """
    Cleans up the results directory by renaming the browsertime file and
    removing the directory.

    Args:
        browsertime_path (str): The path to the browsertime file.
        path (str): The path to the directory to be removed.
    """
    correct_path = f'{path}.har'
    coach_path = browsertime_path.replace('browsertime.har', 'coach.json')
    correct_coach_path = f'{path}-coach.json'
    sustainable_path = browsertime_path.replace('browsertime.har', 'sustainable.json')
    correct_sustainable_path = f'{path}-sustainable.json'
    lighthouse_path = browsertime_path.replace('browsertime.har', 'lighthouse-lhr.json')
    correct_lighthouse_path = f'{path}-lighthouse-lhr.json'

    if os.path.exists(browsertime_path):
        os.rename(browsertime_path, correct_path)
    if os.path.exists(coach_path):
        os.rename(coach_path, correct_coach_path)
    if os.path.exists(sustainable_path):
        os.rename(sustainable_path, correct_sustainable_path)
    if os.path.exists(lighthouse_path):
        os.rename(lighthouse_path, correct_lighthouse_path)
    shutil.rmtree(path)

def get_result_using_no_cache(sitespeed_use_docker, arg, timeout):
    """
    Executes a command using subprocess.Popen and returns the result.

    If `sitespeed_use_docker` is True, the command is run in a Docker container.
    Otherwise, it is run on the host system. The command is constructed using
    the provided `arg` and `timeout` parameters.

    If the command execution exceeds the `timeout` multiplied by 10, a 
    subprocess.TimeoutExpired exception is raised, and the process is terminated.

    Parameters:
    sitespeed_use_docker (bool): Flag to determine if command should be run in Docker.
    arg (str): Argument to be passed to the command.
    timeout (int): Time limit for the command execution.

    Returns:
    str: Output of the command execution.
    """
    result = ''
    process = None
    process_failsafe_timeout = timeout * 10
    try:
        if sitespeed_use_docker:
            base_directory = Path(os.path.dirname(
                os.path.realpath(__file__)) + os.path.sep).parent
            data_dir = base_directory.resolve()

            sitespeedio_version = get_dependency_version('sitespeed.io')
            command = (
                f"docker run --rm -v {data_dir}:/sitespeed.io "
                f"sitespeedio/sitespeed.io:{sitespeedio_version} "
                f"--maxLoadTime {(timeout * 1000)} {arg}"
                )

            with subprocess.Popen(command.split(), stdout=subprocess.PIPE) as process:
                output, error = process.communicate(timeout=process_failsafe_timeout)

                if error is not None:
                    print('DEBUG get_result_using_no_cache(error)', error)

                result = str(output)

            if 'Could not locate Firefox on the current system' in result:
                print('ERROR! Could not locate Firefox on the current system.')
        else:
            command = (f"node node_modules{os.path.sep}sitespeed.io{os.path.sep}"
                       f"bin{os.path.sep}sitespeed.js --maxLoadTime {(timeout * 1000)} {arg}")

            with subprocess.Popen(
                command.split(), stdout=subprocess.PIPE) as process:
                output, error = process.communicate(timeout=process_failsafe_timeout)

                if error is not None:
                    print('DEBUG get_result_using_no_cache(error)', error)

                result = str(output)

            if 'Could not locate Firefox on the current system' in result:
                print('ERROR! Could not locate Firefox on the current system.')
    except subprocess.TimeoutExpired:
        if process is not None:
            process.terminate()
            process.kill()
        print('TIMEOUT!')
        return result
    return result

def get_sanitized_browsertime(input_filename):
    """
    Reads a file and returns its content after removing any character
    that doesn't match a specific regex pattern.

    The function opens the file with the given `input_filename`,
    reads its lines, and appends them to a list. 
    It then joins the lines into a single string and
    applies a regex substitution to remove any character 
    that doesn't match the specified pattern.
    If the file cannot be opened, an error message is printed and 
    an empty string is returned.

    Parameters:
    input_filename (str): The name of the file to be read and sanitized.

    Returns:
    str: The sanitized content of the file.
    """
    lines = []
    try:
        with open(input_filename, 'r', encoding='utf-8') as file:
            data = file.readlines()
            for line in data:
                lines.append(line)
    except: # pylint: disable=bare-except
        print(f'error in get_local_file_content. No such file or directory: {input_filename}')
        return '\n'.join(lines)

    test_str = '\n'.join(lines)
    regex = r"[^a-zåäöA-ZÅÄÖ0-9\{\}\"\:;.,#*\<\>%'&$?!`=@\-\–\+\~\^\\\/| \(\)\[\]_]"
    subst = ""

    result = re.sub(regex, subst, test_str, 0, re.MULTILINE)
    return result


def modify_browsertime_content(input_filename, cookies, versions):
    """
    Modifies the content of a browsertime JSON file by adding cookies and software versions, 
    and removing unnecessary information.

    The function reads the file, sanitizes its content, and loads it as a JSON object. 
    It then adds cookies and software versions to the 'log' section of the JSON object. 
    Unnecessary information such as 'version', 'browser', 'creator', and some parts of 'pages'
    and 'entries' are removed. If any modification is made,
    the JSON object is written back to the file.

    Parameters:
    input_filename (str): The name of the file to be modified.
    cookies (dict): The cookies to be added to the 'log' section.
    versions (dict): The software versions to be added to the 'log' section.

    Returns:
    str: The sanitized content of the file before modification.
    """
    result = get_sanitized_browsertime(input_filename)
    json_result = json.loads(result)
    has_minified = False
    if 'log' not in json_result:
        return ''

    # add cookies
    json_result['log']['cookies'] = cookies
    # add software name and versions
    json_result['log']['_software'] = versions

    if 'version' in json_result['log']:
        del json_result['log']['version']
        has_minified = True
    if 'browser' in json_result['log']:
        del json_result['log']['browser']
        has_minified = True
    if 'creator' in json_result['log']:
        del json_result['log']['creator']
        has_minified = True
    if 'pages' in json_result['log']:
        for page in json_result['log']['pages']:
            keys_to_remove = []

            # NOTE: Fix for inconsistancy in sitespeed handling of not being able to access webpage
            # For some reason it will sometime not add _url field but add url in title field (See TLSv1.0 and TLSv1.1 testing)
            if 'id' in page and 'failing_page' == page['id'] and '_url' not in page and 'title' in page:
                page['_url'] = page['title']
                has_minified = True

            for key in page.keys():
                if key != '_url':
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del page[key]
                has_minified = True
    if 'entries' in json_result['log']:
        for entry in json_result['log']['entries']:
            has_minified = modify_browertime_content_entity(entry) or has_minified

    if has_minified:
        write_json(input_filename, json_result)

    return json_result

def modify_browertime_content_entity(entry):
    """
    Modifies a browsertime entry by removing unnecessary keys.

    The function iterates over the keys of the entry and its 'request'
    and 'response' sub-entries. 
    It removes any key that is not necessary,
    leaving only 'request', 'response', 'serverIPAddress', 
    'httpVersion' in the main entry, 'url' in the
    'request' sub-entry, and 'content', 'headers', 
    'httpVersion' in the 'response' sub-entry.

    Parameters:
    entry (dict): The browsertime entry to be modified.

    Returns:
    bool: True if any modification is made, False otherwise.
    """
    keys_to_remove = []
    for key in entry.keys():
        if key not in ('request', 'response', 'serverIPAddress','httpVersion'):
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del entry[key]
        has_minified = True

    keys_to_remove = []
    for key in entry['request'].keys():
        if key != 'url':
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del entry['request'][key]
        has_minified = True

    keys_to_remove = []
    for key in entry['response'].keys():
        if key not in ('content', 'headers', 'httpVersion', 'status'):
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del entry['response'][key]
        has_minified = True
    return has_minified


def write_json(filename, data):
    """
    Writes a Python object to a JSON file.

    The function opens the file with the given `filename` in write mode and 
    uses the json.dump() function to write the `data` to the file.

    Parameters:
    filename (str): The name of the file to be written.
    data (dict): The Python object to be written to the file.
    """
    with open(filename, 'w', encoding='utf-8') as outfile:
        json.dump(data, outfile)

def get_browsertime_har_path(parent_path):
    """
    Recursively searches for a file named 'browsertime.har' in a directory structure.

    Args:
        parent_path (str): The path of the directory to start the search from.

    Returns:
        str: The path of the 'browsertime.har' file if found, else None.
    """
    if not os.path.exists(parent_path):
        return ''

    if not os.path.isdir(parent_path):
        return ''

    sub_dirs = os.listdir(parent_path)
    if 'browsertime.har' in sub_dirs:
        return os.path.join(parent_path, 'browsertime.har')

    for sub_dir in sub_dirs:
        tmp = get_browsertime_har_path(os.path.join(parent_path, sub_dir))
        if tmp:
            return tmp

    return ''
