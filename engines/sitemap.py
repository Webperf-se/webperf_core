# -*- coding: utf-8 -*-
from models import Sites
from engines.utils import use_item
import config
from tests.utils import *
import re
import gzip
import io


def read_sites(input_sitemap_url, input_skip, input_take):
    if input_sitemap_url.endswith('.xml'):
        sitemap_content = httpRequestGetContent(input_sitemap_url, True, True)
        return read_sites_from_xml(sitemap_content, input_skip, input_take)
    elif input_sitemap_url.endswith('.xml.gz'):
        # unpack gzip:ed sitemap
        sitemap_content = httpRequestGetContent(input_sitemap_url, True, False)
        gzip_io = io.BytesIO(sitemap_content)
        with gzip.GzipFile(fileobj=gzip_io, mode='rb') as gzip_file:
            gzip_content = gzip_file.read()
            sitemap_content = gzip_content.decode('utf-8')
            return read_sites_from_xml(sitemap_content, input_skip, input_take)
    else:
        sites = list()
        return sites

def read_sites_from_xml(sitemap_content, input_skip, input_take):
    sites = list()

    # do we have sitemaps in our sitemap?...
    is_recursive = '<sitemap>' in sitemap_content

    regex = r"<loc>(?P<itemurl>[^<]+)<"
    matches = re.finditer(regex, sitemap_content, re.MULTILINE)

    current_index = 0
    for matchNum, match in enumerate(matches, start=1):

        if not use_item(current_index, input_skip, input_take):
            current_index += 1
            continue

        item_url = match.group('itemurl')

        if is_recursive:
            tmp_sites = read_sites(item_url, input_skip, input_take)
            current_index += len(tmp_sites)
            sites.extend(tmp_sites)
        else:
            content_type = get_content_type(item_url, config.cache_time_delta)
            if 'html' not in content_type:
                print('- skipping index {0} because it is of type: {1}'.format(current_index, content_type))
                current_index += 1
                continue
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
