# -*- coding: utf-8 -*-
from pathlib import Path
import os
from urllib.parse import urlparse
import config
from tests.utils import *

sitespeed_use_docker = config.sitespeed_use_docker


def get_result(url, sitespeed_use_docker, sitespeed_arg):
    folder_ending = 'tmp'
    if use_cache:
        folder_ending = 'cache'

    # TODO: CHANGE THIS IF YOU WANT TO DEBUG
    result_folder_name = os.path.join(
        'data', 'results-{0}-{1}'.format(str(uuid.uuid4()), folder_ending))
    # result_folder_name = os.path.join('data', 'results')

    sitespeed_arg += ' --outputFolder {0} {1}'.format(result_folder_name, url)

    filename = ''
    # Should we use cache when available?
    if use_cache:
        import engines.sitespeed_result as input
        sites = input.read_sites('', -1, -1)
        for site in sites:
            if url == site[1]:
                filename = site[0]
                result_folder_name = filename[:filename.rfind(os.path.sep)]

                if is_file_older_than(filename, cache_time_delta):
                    filename = ''
                    continue

                file_created_timestamp = os.path.getctime(filename)
                file_created_date = time.ctime(file_created_timestamp)
                print('Cached entry found from {0}, using it instead of calling website again.'.format(
                    file_created_date))
                break

    if filename == '':
        get_result_using_no_cache(sitespeed_use_docker, sitespeed_arg)
        website_folder_name = get_foldername_from_url(url)
        filename_old = os.path.join(result_folder_name, 'pages',
                                    website_folder_name, 'data', 'browsertime.har')
        filename = os.path.join(result_folder_name, 'browsertime.har')
        cleanup_browsertime_content(filename_old)
        cleanup_results_dir(filename_old, result_folder_name)
    return (result_folder_name, filename)


def cleanup_results_dir(browsertime_path, path):
    correct_path = os.path.join(
        path, 'browsertime.har')

    os.rename(browsertime_path, correct_path)

    sub_dirs = os.listdir(path)
    for sub_dir in sub_dirs:
        if 'browsertime.har' == sub_dir:
            continue
        else:
            tmp_path = os.path.join(
                path, sub_dir)
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)
            else:
                shutil.rmtree(tmp_path)


def get_result_using_no_cache(sitespeed_use_docker, arg):

    result = ''
    if sitespeed_use_docker:
        dir = Path(os.path.dirname(
            os.path.realpath(__file__)) + os.path.sep).parent
        data_dir = dir.resolve()

        bashCommand = "docker run --rm -v {1}:/sitespeed.io sitespeedio/sitespeed.io:latest {0}".format(
            arg, data_dir)

        import subprocess
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        result = str(output)
    else:
        import subprocess

        bashCommand = "node node_modules{1}sitespeed.io{1}bin{1}sitespeed.js {0}".format(
            arg, os.path.sep)

        process = subprocess.Popen(
            bashCommand.split(), stdout=subprocess.PIPE)

        output, error = process.communicate()
        result = str(output)

    return result


def cleanup_browsertime_content(input_filename):
    lines = list()
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

    # You can manually specify the number of replacements by changing the 4th argument
    result = re.sub(regex, subst, test_str, 0, re.MULTILINE)

    json_result = json.loads(result)
    has_minified = False
    if 'log' not in json_result:
        return ''
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
            keys_to_remove = list()
            for key in page.keys():
                if key != '_url':
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del page[key]
                has_minified = True
    if 'entries' in json_result['log']:
        has_minified = False
        for entry in json_result['log']['entries']:
            keys_to_remove = list()
            for key in entry.keys():
                if key != 'request' and key != 'response' and key != 'serverIPAddress':
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del entry[key]
                has_minified = True

            keys_to_remove = list()
            for key in entry['request'].keys():
                if key != 'url':
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del entry['request'][key]
                has_minified = True

            keys_to_remove = list()
            for key in entry['response'].keys():
                if key != 'content' and key != 'headers':
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


def get_foldername_from_url(url):
    o = urlparse(url)
    hostname = o.hostname
    relative_path = o.path

    test_str = '{0}{1}'.format(hostname, relative_path)

    regex = r"[^a-zA-Z0-9\-\/]"
    subst = "_"

    # You can manually specify the number of replacements by changing the 4th argument
    folder_result = re.sub(regex, subst, test_str, 0, re.MULTILINE)

    # NOTE: hopefully temporary fix for "index.html" and Gullspangs-kommun.html
    folder_result = folder_result.replace('_html', '.html')

    folder_result = folder_result.replace('/', os.sep)

    return folder_result
