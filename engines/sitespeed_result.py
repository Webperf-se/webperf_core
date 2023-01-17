# -*- coding: utf-8 -*-
import os
from pathlib import Path
import re

sites = list()


def add_site(input_filename, url, input_skip, input_take):
    sites = list()
    return sites


def delete_site(input_filename, url, input_skip, input_take):
    tmpSites = list()
    return tmpSites


def get_url_from_file_content(input_filename):
    try:
        with open(input_filename, 'r', encoding='utf-8') as file:
            data = file.read(1024)
            regex = r"\"_url\":[ ]{0,1}\"(?P<url>[^\"]+)\""
            matches = re.finditer(regex, data, re.MULTILINE)
            for matchNum, match in enumerate(matches, start=1):
                return match.group('url')
    except:
        print('error in get_local_file_content. No such file or directory: {0}'.format(
            input_filename))
        return None

    return None


def read_sites(input_filename, input_skip, input_take):

    if len(sites) > 0:
        return sites

    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    data_dir = os.path.join(dir, 'data') + os.path.sep

    dirs = os.listdir(data_dir)

    urls = {}

    for result_dir in dirs:
        if input_take != -1 and len(urls) >= input_take:
            break

        if not result_dir.startswith('results-'):
            continue
        path = os.path.join(
            data_dir, result_dir)

        full_path = os.path.join(
            path, 'browsertime.har')

        # No need to read all content, just read the first 1024 bytes as our url will be there
        # we are doing this for performance
        url = get_url_from_file_content(full_path)
        urls[url] = full_path

    current_index = 0
    for tmp_url in urls.keys():
        sites.append([urls[tmp_url], tmp_url])
        current_index += 1

    return sites
