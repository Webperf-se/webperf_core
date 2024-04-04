# -*- coding: utf-8 -*-
import re
from engines.utils import use_item
from tests.utils import get_http_content

def read_sites(input_url, input_skip, input_take):
    """
    This function reads site data from a specific category
    on https://webperf.se and returns the sites.
    
    Parameters:
    input_url (str): The category of sites to be read.
    Possible values are:
    - 'offentlig-sektor',
    - 'kommuner',
    - 'regioner',
    - 'toplist',
    - 'digitalt',
    - 'webbyraer'.
    input_skip (int): The number of lines to skip in the input file.
    input_take (int): The number of lines to take from the input file after skipping.
    
    Returns:
    list: The list of sites read from the specified category on https://webperf.se.
    """
    sites = []

    if 'offentlig-sektor' in input_url:
        input_url = 'https://webperf.se/category/ovrig-offentlig-sektor/'
    elif 'kommuner' in input_url:
        input_url = 'https://webperf.se/category/kommuner/'
    elif 'regioner' in input_url:
        input_url = 'https://webperf.se/category/regioner/'
    elif 'toplist' in input_url:
        input_url = 'https://webperf.se/toplist/'
    elif 'digitalt' in input_url:
        input_url = 'https://webperf.se/category/digitalt-sverige/'
    elif 'webbyraer' in input_url:
        input_url = 'https://webperf.se/category/webbyraer/'
    else:
        raise NotImplementedError('input is incorrect')

    category_content = get_http_content(input_url)

    category_regex = r"<a href=\"(?P<detail_url>\/site\/[^\"]+)\""
    category_matches = re.finditer(
        category_regex, category_content, re.MULTILINE)

    detailed_urls = []
    current_index = 0
    for _, match in enumerate(category_matches, start=1):
        detail_url = match.group('detail_url')
        if detail_url.startswith('/'):
            detail_url = f'https://webperf.se{detail_url}'
        if use_item(current_index, input_skip, input_take):
            detailed_urls.append(detail_url)
        current_index += 1

    detail_regex = r"Webbplats:<\/th>[ \r\n\t]+<td><a href=\"(?P<item_url>[^\"]+)\""
    current_index = 0
    for detail_url in detailed_urls:
        detail_content = get_http_content(detail_url)
        detail_match = re.search(detail_regex, detail_content, re.MULTILINE)
        item_url = detail_match.group('item_url')

        sites.append([current_index, item_url])
        current_index += 1

    return sites


def add_site(input_url, _, input_skip, input_take):
    """
    This function reads site data from a specific category
    on https://webperf.se, prints a warning message (because it is read only),
    and returns the sites.
    
    Parameters:
    input_url (str): The category of sites to be read.
    Possible values are:
    - 'offentlig-sektor',
    - 'kommuner',
    - 'regioner',
    - 'toplist',
    - 'digitalt',
    - 'webbyraer'.
    _ : Ignored parameter.
    input_skip (int): The number of lines to skip in the input file.
    input_take (int): The number of lines to take from the input file after skipping.
    
    Returns:
    list: The list of sites read from the specified category on https://webperf.se.
    """
    print((
        "WARNING: webperf engine is a read only method for testing all"
        " pages in a category from webperf.se, NO changes will be made"))

    sites = read_sites(input_url, input_skip, input_take)

    return sites


def delete_site(input_url, _, input_skip, input_take):
    """
    This function reads site data from a specific category
    on https://webperf.se, prints a warning message (because it is read only),
    and returns the sites.
    
    Parameters:
    input_url (str): The category of sites to be read.
    Possible values are:
    - 'offentlig-sektor',
    - 'kommuner',
    - 'regioner',
    - 'toplist',
    - 'digitalt',
    - 'webbyraer'.
    _ : Ignored parameter.
    input_skip (int): The number of lines to skip in the input file.
    input_take (int): The number of lines to take from the input file after skipping.
    
    Returns:
    list: The list of sites read from the specified category on https://webperf.se.
    """
    print((
        "WARNING: webperf engine is a read only method for testing all"
        " pages in a category from webperf.se, NO changes will be made"))

    sites = read_sites(input_url, input_skip, input_take)

    return sites
