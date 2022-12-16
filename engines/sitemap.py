# -*- coding: utf-8 -*-
from models import Sites
from engines.utils import use_item
import config
from tests.utils import *
import re


def read_sites(input_sitemap_url, input_skip, input_take):
    sites = list()

    sitemap_content = httpRequestGetContent(input_sitemap_url)

    regex = r"<loc>(?P<itemurl>[^<]+)<"
    matches = re.finditer(regex, sitemap_content, re.MULTILINE)

    current_index = 0
    for matchNum, match in enumerate(matches, start=1):

        item_url = match.group('itemurl')

        if use_item(current_index, input_skip, input_take):
            sites.append([current_index, item_url])
        current_index += 1
    return sites


def add_site(input_filename, url, input_skip, input_take):
    print("WARNING: sitemap engine is a read only method for testing all pages in a sitemap.xml, NO changes will be made")

    sites = read_sites(input_filename, input_skip, input_take)

    return sites


def delete_site(input_filename, url, input_skip, input_take):
    print("WARNING: sitemap engine is a read only method for testing all pages in a sitemap.xml, NO changes will be made")

    sites = read_sites(input_filename, input_skip, input_take)

    return sites
