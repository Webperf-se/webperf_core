# -*- coding: utf-8 -*-
from models import Sites, SiteTests
import config
from tests.utils import *
import re


def read_sites(input_sitemap_url):
    sites = list()

    sitemap_content = httpRequestGetContent(input_sitemap_url)

    regex = r"<loc>(?P<itemurl>[^<]+)<"
    matches = re.finditer(regex, sitemap_content, re.MULTILINE)

    current_siteid = 0
    for matchNum, match in enumerate(matches, start=1):

        item_url = match.group('itemurl')

        sites.append([current_siteid, item_url])
        current_siteid += 1
    return sites


def add_site(input_filename, url):
    print("WARNING: sitemap engine is a read only method for testing all pages in a sitemap.xml, NO changes will be made")

    sites = read_sites(input_filename)

    return sites


def delete_site(input_filename, url):
    print("WARNING: sitemap engine is a read only method for testing all pages in a sitemap.xml, NO changes will be made")

    sites = read_sites(input_filename)

    return sites
