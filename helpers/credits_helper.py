# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path
import re
import urllib
import urllib.parse

from helpers.setting_helper import get_config

def update_credits_markdown(global_translation):
    creds = get_credits(global_translation)

    base_directory = os.path.join(Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent)
    credits_path = os.path.join(base_directory, 'CREDITS.md')

    with open(credits_path, 'w', encoding='utf-8', newline='') as file:
        file.write(creds)


def get_credits(global_translation):
    text = '# Credits\r\n'
    text += 'Following shows projects and contributors for webperf-core and its dependencies.\r\n'
    text += 'Many thanks to all of you! :D\r\n'

    base_directory = os.path.join(Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent)

    software_full_path = os.path.join(base_directory, 'defaults', 'software-full.json')
    softwares = None
    with open(software_full_path, encoding='utf-8') as json_input_file:
        tmp = json.load(json_input_file)
        if 'softwares' in tmp:
            softwares = tmp['softwares']

            if 'webperf_core' in softwares and len(softwares["webperf_core"]["contributors"]) > 0:
                text += '\r\n'
                text += 'Contributors:\r\n'
                for contributor in softwares["webperf_core"]["contributors"]:
                    text += f'- {contributor}\r\n'


    text += '\r\n\r\n'
    text += '## Projects we depend on:\r\n'

    package_path = os.path.join(base_directory, 'package.json')
    with open(package_path, encoding='utf-8') as json_input_file:
        data = json.load(json_input_file)
        text += '\r\n'
        for creditor_name, creditor_version in data['dependencies'].items():
            if creditor_name not in softwares:
                print(f'{creditor_name} not found in {software_full_path}.')
                continue

            software = softwares[creditor_name]
            # print(creditor_name, software)
            text += f'### [{creditor_name}](https://www.npmjs.com/package/{creditor_name})\r\n'
            if 'pa11y' in creditor_name:
                text += 'Usage: Used in Accessibility (Pa11y) Test\r\n'
            elif 'lighthouse' in creditor_name:
                text += 'Usage: Used in Google Lighthouse based Tests\r\n'
            elif 'sitespeed.io' in creditor_name:
                text += 'Usage: Used in the background in most cases where we need to visit website as browser\r\n'
            elif 'vnu-jar' in creditor_name:
                text += 'Usage: Used in HTML and CSS Validation Test\r\n'

            if 'license' in software and software["license"] != '':
                text += f'License: {software["license"].upper()}\r\n'

            text += '\r\n'

    requirements_full_path = os.path.join(base_directory, 'requirements.txt')
    with open(requirements_full_path, 'r', encoding='utf-8', newline='') as file:
        content = ''.join(file.readlines())
        regex = r"(?P<name>[^>=]+)==[0-9\\.]+"
        matches = re.finditer(regex, content, re.MULTILINE | re.IGNORECASE)
        for _, match in enumerate(matches, start=1):
            name = match.group('name').strip()
            text += f'### [{name}](https://pypi.org/project/{name}/)\r\n'
            if 'beautifulsoup4' in name:
                text += 'Usage: Used to parse HTML content\r\n'
            elif 'lxml' in name:
                text += 'Usage: Used to parse XML content\r\n'
            elif 'requests' in name:
                text += 'Usage: Used to request content not normally requested by users, like robots.txt\r\n'
            elif 'urllib3' in name:
                text += 'Usage: Used to parse url\r\n'
            elif 'pylint' in name:
                text += 'Usage: Used by our devs to ensure code quality\r\n'
            elif 'dnspython' in name:
                text += 'Usage: Used to get and parse DNS content\r\n'
            elif name in ('Pillow', 'OpenCV-Python', 'Numpy'):
                text += 'Reguired by sitespeed.io\r\n'
            elif 'IP2Location' in name:
                text += 'Usage: Used to get a proximate location related to IP/IP-range\r\n'
            elif 'packaging' in name:
                text += 'Usage: Used to understand and compare software versions\r\n'
            text += '\r\n'


    text += get_external_information_sources()
    return text

def get_external_information_sources():
    text = '## External Information Source(s):\r\n'
    # Get all contributors of repo
    # - https://api.github.com/repos/Webperf-se/webperf_core/contributors
    base_directory = os.path.join(Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent)
    py_files = get_py_files(base_directory)

    grouped_urls = get_urls(py_files)
    grouped_urls['all'] = sorted(grouped_urls['all'])

    for file_path, urls in grouped_urls.items():
        last_sep_index = file_path.rfind(os.path.sep) + 1
        file_name = file_path[last_sep_index:].lower()
        if file_name == 'all':
            continue
        elif 'update_software_helper.py' in file_name:
            text += '### Update Software Test Sources:\r\n'
            text += '- https://github.com/github/advisory-database/tree/main/advisories/github-reviewed\r\n'
        else:
            text += f'### Unspecified ({file_name}) Sources:\r\n'

        for url in urls:
            text += f'- {url}\r\n'
        text += '\r\n'

    text += '### Tracking and Privacy Test Sources:\r\n'
    text += '- https://blocklistproject.github.io/Lists/alt-version/tracking-nl.txt\r\n'
    text += '- https://blocklistproject.github.io/Lists/alt-version/ads-nl.txt\r\n'
    text += '- https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/services.json\r\n'
 
    return text

def get_urls(py_files):
    result = {
        'all': []
    }
    for py_file in py_files:
        result[py_file] = []
        with open(py_file, 'r', encoding='utf-8', newline='') as file:
            content = ''.join(file.readlines())
            regex = r"get_http_content\((?P<url>[^\)]+)[\)]"
            matches = re.finditer(regex, content, re.MULTILINE | re.IGNORECASE)
            for _, match in enumerate(matches, start=1):
                url = match.group('url').strip()
                url = sanitize_url(url)
                if url is None:
                    continue
                parsed_url = urllib.parse.urlparse(url)
                if '{' in parsed_url.hostname:
                    continue

                result['all'].append(url)
                result[py_file].append(url)

        if len(result[py_file]) == 0:
            del result[py_file]
        else:
            result[py_file] = sorted(result[py_file])
    return result

def sanitize_url(url):
    start_as_string = url.startswith('\'') or url.startswith('"')
    ends_as_string = url.endswith('\'') or url.endswith('"')
    if (start_as_string and ends_as_string):
        url = url.strip('\'').strip('"')
        return url

    if start_as_string:
        url = url.strip('\'').strip('"')
        find_1 = url.find('\'')
        if find_1 != -1:
            url = url[:find_1]
        find_2 = url.find('"')
        if find_2 != -1:
            url = url[:find_2]
        return url

    url = url.strip('(').replace('\r', '').replace('\n','')\
        .replace('\t','').replace(' ','').replace('\'\'','')
    if url.startswith('\'') or url.startswith('"'):
        url = url.replace('\'', '').replace('"', '')
        return url

    url = url.strip('f')
    if url.startswith('\'') or url.startswith('"'):
        url = url.replace('\'', '').replace('"', '')
        return url
    return None

def get_py_files(base_directory):
    py_files = []
    sub_files_or_dirs = []

    try:
        sub_files_or_dirs = os.listdir(base_directory)
    except:
        return py_files

    cache_folder = get_config('general.cache.folder')
    for sub_file_or_dir in sub_files_or_dirs:
        if sub_file_or_dir[0:1] == '.':
            continue

        if len(sub_file_or_dir) < 4:
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
                'tmp',
                'locales',
                cache_folder):
            continue
        else:
            sub_py_files = get_py_files( os.path.join(base_directory, sub_file_or_dir) )
            if len(sub_py_files) > 0:
                py_files.extend(sub_py_files)
    return py_files
