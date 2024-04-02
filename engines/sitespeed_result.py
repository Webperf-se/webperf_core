# -*- coding: utf-8 -*-
import os
from pathlib import Path
from urllib.parse import urlparse
import re

def add_site(input_filename, url, input_skip, input_take):
    sites = []
    return sites


def delete_site(input_filename, url, input_skip, input_take):
    tmpSites = []
    return tmpSites


def get_url_from_file_content(input_filename):
    try:
        # No need to read all content, just read the first 1024 bytes as our url will be there
        # we are doing this for performance
        with open(input_filename, 'r', encoding='utf-8') as file:
            data = file.read(1024)
            regex = r"\"[_]{0,1}url\":[ ]{0,1}\"(?P<url>[^\"]+)\""
            matches = re.finditer(regex, data, re.MULTILINE)
            for matchNum, match in enumerate(matches, start=1):
                return match.group('url')
    except:
        print('error in get_local_file_content. No such file or directory: {0}'.format(
            input_filename))
        return None

    return None


def read_sites(hostname_or_argument, input_skip, input_take):
    sites = []
    hostname = hostname_or_argument
    if hostname_or_argument.endswith('.result'):
        tmp = hostname_or_argument[:hostname_or_argument.rfind('.result')]
        o = urlparse(tmp)
        hostname = o.hostname

    if len(sites) > 0:
        return sites

    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    data_dir = os.path.join(dir, 'cache', hostname) + os.path.sep
    if not os.path.exists(data_dir):
        return sites

    dirs = os.listdir(data_dir)

    urls = {}

    for file_name in dirs:
        if input_take != -1 and len(urls) >= input_take:
            break

        if not file_name.endswith('.har'):
            continue

        full_path = os.path.join(
            data_dir, file_name)

        url = get_url_from_file_content(full_path)
        urls[url] = full_path

    current_index = 0
    for tmp_url in urls.keys():
        sites.append([urls[tmp_url], tmp_url])
        current_index += 1

    return sites
