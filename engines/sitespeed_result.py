# -*- coding: utf-8 -*-
import os
from pathlib import Path
from urllib.parse import urlparse
import re
from engines.utils import use_item
from helpers.setting_helper import get_config

def get_url_from_file_content(input_filename):
    """
    Extracts the URL from the content of a HAR file.

    The function opens the file and reads the first 1024 bytes.
    It then uses a regular expression to find the URL in the read data.
    If the file does not exist, it prints an error message and returns None.

    Parameters:
    input_filename (str): The path of the HAR file from which to extract the URL.

    Returns:
    str: The extracted URL. Returns None if the file does not exist or no URL is found.

    """
    try:
        # No need to read all content, just read the first 1024 bytes as our url will be there
        # we are doing this for performance
        with open(input_filename, 'r', encoding='utf-8') as file:
            data = file.read(1024)
            regex = r"\"[_]{0,1}url\":[ ]{0,1}\"(?P<url>[^\"]+)\""
            matches = re.finditer(regex, data, re.MULTILINE)
            for _, match in enumerate(matches, start=1):
                return match.group('url')
    except OSError:
        print(f'Error. No such file or directory: {input_filename}')
        return None

    return None

def read_sites_from_directory(directory, hostname_or_argument, input_skip, input_take):
    sites = []

    hostname = hostname_or_argument
    if hostname_or_argument.endswith('.result'):
        tmp_url = hostname_or_argument[:hostname_or_argument.rfind('.result')]
        hostname = urlparse(tmp_url).hostname

    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    # host_path = os.path.join(base_directory, directory, hostname) + os.path.sep
    host_path = directory

    if not os.path.exists(host_path):
        return sites

    dirs = os.listdir(host_path)

    urls = {}

    for file_name in dirs:
        if input_take != -1 and len(urls) >= input_take:
            break

        if not file_name.endswith('.har'):
            continue

        full_path = os.path.join(
            host_path, file_name)

        url = get_url_from_file_content(full_path)
        urls[url] = full_path

    current_index = 0
    for url, har_path in urls.items():
        if use_item(current_index, input_skip, input_take):
            sites.append([har_path, url])
        current_index += 1

    return sites

def read_sites(hostname_or_argument, input_skip, input_take):
    """
    Reads the sites from the cache directory based on the hostname or
    the argument that ends with '.result'.

    Parameters:
    hostname_or_argument (str): The hostname or the argument that ends with '.result'.
    input_skip (int): The number of items to skip from the start.
    input_take (int): The number of items to take after skipping. If -1, takes all items.

    Returns:
    list: A list of sites where each site is represented as a
          list containing the path to the HAR file and the URL.
    """
    cache_folder = get_config('general.cache.folder')
    return read_sites_from_directory(cache_folder, hostname_or_argument, input_skip, input_take)
