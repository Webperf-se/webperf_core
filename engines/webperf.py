# -*- coding: utf-8 -*-
from models import Sites
from engines.utils import use_item
import config
from tests.utils import *
import re


def read_sites(input_url, input_skip, input_take):
    sites = list()

    if 'offentlig-sektor' in input_url:
        input_url = 'https://webperf.se/category/ovrig-offentlig-sektor/'
    elif 'kommuner' in input_url:
        input_url = 'https://webperf.se/category/kommuner/'
    elif 'regioner' in input_url:
        input_url = 'https://webperf.se/category/regioner/'
    elif 'toplist' in input_url:
        input_url = 'https://webperf.se/toplist/'
    else:
        raise NotImplementedError('input is incorrect')

    category_content = httpRequestGetContent(input_url)

    category_regex = r"<a href=\"(?P<detail_url>\/site\/[^\"]+)\""
    category_matches = re.finditer(
        category_regex, category_content, re.MULTILINE)

    detailed_urls = list()
    current_index = 0
    for matchNum, match in enumerate(category_matches, start=1):
        detail_url = match.group('detail_url')
        if detail_url.startswith('/'):
            detail_url = 'https://webperf.se{0}'.format(detail_url)
        if use_item(current_index, input_skip, input_take):
            detailed_urls.append(detail_url)
        current_index += 1

    detail_regex = r"Webbplats:<\/th>[ \r\n\t]+<td><a href=\"(?P<item_url>[^\"]+)\""
    current_index = 0
    for detail_url in detailed_urls:
        detail_content = httpRequestGetContent(detail_url)
        detail_match = re.search(detail_regex, detail_content, re.MULTILINE)
        item_url = detail_match.group('item_url')

        sites.append([current_index, item_url])
        current_index += 1

    return sites


def add_site(input_filename, url, input_skip, input_take):
    print("WARNING: webperf engine is a read only method for testing all pages in a category from webperf.se, NO changes will be made")

    sites = read_sites(input_filename, input_skip, input_take)

    return sites


def delete_site(input_filename, url, input_skip, input_take):
    print("WARNING: webperf engine is a read only method for testing all pages in a category from webperf.se, NO changes will be made")

    sites = read_sites(input_filename, input_skip, input_take)

    return sites
