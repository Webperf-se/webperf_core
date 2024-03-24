# -*- coding: utf-8 -*-
import time
import json
from pathlib import Path
import os
import re
import shutil
from subprocess import TimeoutExpired
import urllib
from urllib.parse import ParseResult, urlparse, urlunparse
import uuid
from tests.utils import get_config_or_default, is_file_older_than

REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
sitespeed_use_docker = get_config_or_default('sitespeed_use_docker')
USE_CACHE = get_config_or_default('CACHE_WHEN_POSSIBLE')
CACHE_TIME_DELTA = get_config_or_default('CACHE_TIME_DELTA')

def to_firefox_url_format(url):

    o = urllib.parse.urlparse(url)
    path = o.path
    if '' == o.path:
        path = '/'

    o2 = ParseResult(scheme=o.scheme, netloc=o.netloc, path=path, params=o.params, query=o.query, fragment=o.fragment)
    url2 = urlunparse(o2)
    return url2

def get_result(url, sitespeed_use_docker, sitespeed_arg, timeout):
    folder = 'tmp'
    if USE_CACHE:
        folder = 'cache'

    o = urlparse(url)
    hostname = o.hostname

    # TODO: CHANGE THIS IF YOU WANT TO DEBUG
    result_folder_name = os.path.join(folder, hostname, '{0}'.format(str(uuid.uuid4())))
    # result_folder_name = os.path.join('data', 'results')

    #sitespeed_arg += ' --outputFolder {0} {1}'.format(result_folder_name, url)
    sitespeed_arg += ' --postScript chrome-cookies.cjs --postScript chrome-versions.cjs --outputFolder {0} {1}'.format(result_folder_name, url)
    # sitespeed_arg += ' --outputFolder {0} {1}'.format(result_folder_name, url)

    filename = ''
    # Should we use cache when available?
    if USE_CACHE:
        # added for firefox support
        url2 = to_firefox_url_format(url)

        import engines.sitespeed_result as input
        sites = input.read_sites(hostname, -1, -1)
        for site in sites:
            if url == site[1] or url2 == site[1]:
                filename = site[0]

                if is_file_older_than(filename, CACHE_TIME_DELTA):
                    filename = ''
                    continue

                result_folder_name = filename[:filename.rfind(os.path.sep)]

                file_created_timestamp = os.path.getctime(filename)
                file_created_date = time.ctime(file_created_timestamp)
                print('Cached entry found from {0}, using it instead of calling website again.'.format(
                    file_created_date))
                break
    if filename != '':
        return (result_folder_name, filename)
    else:
        test = get_result_using_no_cache(sitespeed_use_docker, sitespeed_arg, timeout)
        test = test.replace('\\n', '\r\n').replace('\\\\', '\\')

        regex = r"COOKIES:START: {\"cookies\":(?P<COOKIES>.+)} COOKIES:END"
        cookies = '{}'
        matches = re.finditer(
            regex, test, re.MULTILINE)
        for _, match in enumerate(matches, start=1):
            cookies = match.group('COOKIES')

        regex = r"VERSIONS:START: (?P<VERSIONS>[^V]+) VERSIONS:END"
        versions = '{}'
        matches = re.finditer(
            regex, test, re.MULTILINE)
        for _, match in enumerate(matches, start=1):
            versions = match.group('VERSIONS')

        # print('DEBUG VERSIONS:', versions)

        filename_old = get_browsertime_har_path(os.path.join(result_folder_name, 'pages'))

        filename = '{0}{1}'.format(result_folder_name, '.har')
        cookies_json = json.loads(cookies)
        versions_json = json.loads(versions)

        if (os.path.exists(filename_old)):
            modify_browsertime_content(filename_old, cookies_json, versions_json)
            cleanup_results_dir(filename_old, result_folder_name)
            return (result_folder_name, filename)
        else:
            shutil.rmtree(result_folder_name)
            return (result_folder_name, '')


def cleanup_results_dir(browsertime_path, path):
    correct_path = '{0}{1}'.format(path, '.har')
    os.rename(browsertime_path, correct_path)
    shutil.rmtree(path)

def get_result_using_no_cache(sitespeed_use_docker, arg, timeout):

    result = ''
    process = None
    process_failsafe_timeout = timeout * 10
    try:
        if sitespeed_use_docker:
            base_directory = Path(os.path.dirname(
                os.path.realpath(__file__)) + os.path.sep).parent
            data_dir = base_directory.resolve()

            # print('DEBUG get_result_using_no_cache(data_dir)', data_dir)

            command = "docker run --rm -v {1}:/sitespeed.io sitespeedio/sitespeed.io:latest --maxLoadTime {2} {0}".format(
                arg, data_dir, timeout * 1000)

            import subprocess
            process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
            output, error = process.communicate(timeout=process_failsafe_timeout)

            if error != None:
                print('DEBUG get_result_using_no_cache(error)', error)

            result = str(output)

            if 'Could not locate Firefox on the current system' in result:
                print('ERROR! Could not locate Firefox on the current system.')
            #else:
            # print('DEBUG get_result_using_no_cache(result)', '\n\t', result.replace('\\n', '\n\t'))
        else:
            import subprocess

            command = "node node_modules{1}sitespeed.io{1}bin{1}sitespeed.js --maxLoadTime {2} {0}".format(
                arg, os.path.sep, timeout * 1000)

            process = subprocess.Popen(
                command.split(), stdout=subprocess.PIPE)

            output, error = process.communicate(timeout=process_failsafe_timeout)
            
            if error is not None:
                print('DEBUG get_result_using_no_cache(error)', error)

            result = str(output)

            if 'Could not locate Firefox on the current system' in result:
                print('ERROR! Could not locate Firefox on the current system.')
            #else:
            # print('DEBUG get_result_using_no_cache(result)', '\n\t', result.replace('\\n', '\n\t'))
    except TimeoutExpired:
        if process is not None:
            process.terminate()
            process.kill()
        print('TIMEOUT!')
        return result
    return result

def get_sanitized_browsertime(input_filename):
    lines = []
    try:
        with open(input_filename, 'r', encoding='utf-8') as file:
            data = file.readlines()
            for line in data:
                lines.append(line)
    except:
        print('error in get_local_file_content. No such file or directory: {0}'.format(
            input_filename))
        return '\n'.join(lines)

    test_str = '\n'.join(lines)
    regex = r"[^a-zåäöA-ZÅÄÖ0-9\{\}\"\:;.,#*\<\>%'&$?!`=@\-\–\+\~\^\\\/| \(\)\[\]_]"
    subst = ""

    result = re.sub(regex, subst, test_str, 0, re.MULTILINE)
    return result


def modify_browsertime_content(input_filename, cookies, versions):
    result = get_sanitized_browsertime(input_filename)
    json_result = json.loads(result)
    has_minified = False
    if 'log' not in json_result:
        return ''

    # add cookies
    json_result['log']['cookies'] = cookies
    # add software name and versions
    json_result['log']['software'] = versions

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
        has_minified = False
        for page in json_result['log']['pages']:
            keys_to_remove = []
            for key in page.keys():
                if key != '_url':
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del page[key]
                has_minified = True
    if 'entries' in json_result['log']:
        has_minified = False
        for entry in json_result['log']['entries']:
            keys_to_remove = []
            for key in entry.keys():
                if key != 'request' and key != 'response' and key != 'serverIPAddress' and key != 'httpVersion':
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
                if key != 'content' and key != 'headers' and key != 'httpVersion':
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del entry['response'][key]
                has_minified = True

    if has_minified:
        write_json(input_filename, json_result)

    return result


def write_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as outfile:
        json.dump(data, outfile)

def get_browsertime_har_path(parent_path):
    if not os.path.exists(parent_path):
        return None

    sub_dirs = os.listdir(parent_path)
    if 'browsertime.har' in sub_dirs:
        return os.path.join(parent_path, 'browsertime.har')

    for sub_dir in sub_dirs:
        tmp = get_browsertime_har_path(os.path.join(parent_path, sub_dir))
        if tmp:
            return tmp

    return None
