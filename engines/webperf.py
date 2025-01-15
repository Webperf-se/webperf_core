# -*- coding: utf-8 -*-
from datetime import timedelta
import json
import re
import time
from engines.utils import use_item
from helpers.setting_helper import get_config
from tests.utils import get_http_content, has_cache_file

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
    all_categories_url = 'https://webperf.se/sites/'
    categories_fallback = {
        'offentlig-sektor': '/category/ovrig-offentlig-sektor/',
        'kommuner': '/category/kommuner/',
        'regioner': '/category/regioner/',
        'toplist': '/toplist/',
        'digitalt': '/category/digitalt-sverige/',
        'webbyraer': '/category/webbyraer/'
    }

    all_categories_content = get_http_content(all_categories_url)
    if all_categories_content != '':
        categories = {}
        categories_regex = r"<th scope=\"col\">Kategori<\/th>.*?<tbody>(?P<categories>.*?)<\/tbody>"
        categories_matches = re.finditer(
            categories_regex, all_categories_content, re.MULTILINE | re.S)
        for _, match in enumerate(categories_matches, start=1):
            all_categories_subcontent = match.group('categories')
            # <a href=\"(?P<url>\/category\/(?P<name>[^\"]+)/)\">
            category_regex = r"<a href=\"(?P<url>\/category\/(?P<name>[^\"]+)/)\">"
            category_matches = re.finditer(
                category_regex, all_categories_subcontent, re.MULTILINE | re.S)
            for _, match in enumerate(category_matches, start=1):
                category_url = match.group('url')
                category_name = match.group('name')
                categories[category_name] = category_url
    else:
        categories = categories_fallback

    found = False
    for category_name, category_url in categories.items():
        if category_name in input_url:
            input_url = category_url
            found = True

    if not found and ('all' in input_url or 'alla' in input_url):
        for category_name, category_url in categories.items():
            sites.extend(get_category_sites(f'https://webperf.se{category_url}', input_skip, input_take))
        return sites

    if not found:
        for category_name, category_url in categories_fallback.items():
            if category_name in input_url:
                input_url = category_url
                found = True

    if found:
        input_url = f'https://webperf.se{input_url}'
    else:
        print('Error: No valid webperf option')
        print('')
        print('Available webperf.se input values:')
        for category_name, category_url in categories.items():
            print(f'-i {category_name}.webprf')
        return sites

    sites.extend(get_category_sites(input_url, input_skip, input_take))
    return sites

def get_category_sites(input_url, input_skip, input_take):
    print(f'Retrieving sites from {input_url}')
    sites = []
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
    use_text_instead_of_content = True
    for detail_url in detailed_urls:
        is_cached = has_cache_file(detail_url,
                                   use_text_instead_of_content,
                                   timedelta(minutes=get_config('general.cache.max-age')))
        
        detail_content = get_http_content(detail_url)
        if not is_cached:
            time.sleep(10)
        detail_match = re.search(detail_regex, detail_content, re.MULTILINE)
        item_url = detail_match.group('item_url')
        print(f'- {item_url}')

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
