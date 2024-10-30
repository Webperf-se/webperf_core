# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path
import re


def get_credits(global_translation):
    text = '# Credits\r\n' # global_translation('TEXT_CREDITS')
    text += 'Following shows projects and contributors for webperf-core and its dependencies.\r\n'
    text += 'Many thanks to all of you! :D\r\n'

    folder = 'defaults'
    base_directory = os.path.join(Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent)

    credits_path = os.path.join(base_directory, folder, 'credits.json')
    if not os.path.exists(credits_path):
        os.makedirs(credits_path)

    with open(credits_path, encoding='utf-8') as json_input_file:
        data = json.load(json_input_file)
        text += '\r\n'
        for creditor in data['creditors']:
            text += f'## {creditor["name"]}\r\n'
            if 'license' in creditor and creditor["license"] != '':
                text += f'License: {creditor["license"]}\r\n'
            if 'usage' in creditor and len(creditor["usage"]) > 0:
                text += f'usage: {creditor["usage"]}\r\n'
            if 'contributors' in creditor and creditor["contributors"] != '':
                text += 'Contributors:\r\n'
                for contributor in creditor["contributors"]:
                    text += f'- {contributor}\r\n'
    return text

def set_credits():
    # Get all contributors of repo
    # - https://api.github.com/repos/Webperf-se/webperf_core/contributors
    base_directory = os.path.join(Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent)
    py_files = get_py_files(base_directory)
    nice = json.dumps(py_files, indent=3)
    # print('B', nice)

    urls = get_urls(py_files)
    urls = sorted(urls)
    nice = json.dumps(urls, indent=3)
    print('B', nice)

def get_urls(py_files):
    urls = []
    for py_file in py_files:
        with open(py_file, 'r', encoding='utf-8', newline='') as file:
            content = ''.join(file.readlines())
            regex = r"get_http_content\((?P<url>[^\)]+)[\)]"
            matches = re.finditer(regex, content, re.MULTILINE | re.IGNORECASE)
            for _, match in enumerate(matches, start=1):
                url = match.group('url').strip()
                start_as_string = url.startswith('\'') or url.startswith('"')
                ends_as_string = url.endswith('\'') or url.endswith('"')
                if (start_as_string and ends_as_string):
                    url = url.strip('\'').strip('"')
                    urls.append(url)
                elif start_as_string:
                    url = url.strip('\'').strip('"')
                    find_1 = url.find('\'')
                    if find_1 != -1:
                        url = url[:find_1]
                    find_2 = url.find('"')
                    if find_2 != -1:
                        url = url[:find_2]
                    urls.append(url)
                else:
                    url = url.strip('(').replace('\r', '').replace('\n','')\
                        .replace('\t','').replace(' ','').replace('\'\'','')
                    if url.startswith('\'') or url.startswith('"'):
                        url = url.replace('\'', '').replace('"', '')
                        urls.append(url)
                        continue
                    url = url.strip('f')
                    if url.startswith('\'') or url.startswith('"'):
                        url = url.replace('\'', '').replace('"', '')
                        urls.append(url)
                    # else:
                    #     print(f'\t-{url}')
    return urls

def get_py_files(base_directory):
    py_files = []
    sub_files_or_dirs = os.listdir(base_directory)
    for sub_file_or_dir in sub_files_or_dirs:
        if sub_file_or_dir[0:1] == '.':
            continue

        if len(sub_file_or_dir) < 4:
            print('C', sub_file_or_dir)
            continue

        if sub_file_or_dir.lower().endswith(".py"):
            py_files.append( os.path.join(base_directory, sub_file_or_dir) )
        elif '.' in sub_file_or_dir:
            continue
        elif sub_file_or_dir in (
                'data',
                'Dockerfile',
                'docker',
                'defaults',
                'docs',
                '__pycache__',
                'cache',
                'node_modules',
                'LICENSE',
                'locales'):
            continue
        else:
            sub_py_files = get_py_files( os.path.join(base_directory, sub_file_or_dir) )
            if len(sub_py_files) > 0:
                py_files.extend(sub_py_files)
    return py_files
