# -*- coding: utf-8 -*-
import os
from urllib.parse import urlparse
import gzip
import io
from bs4 import BeautifulSoup
from engines.utils import use_item
from tests.utils import get_content_type, httpRequestGetContent, cache_time_delta
from utils import merge_dicts

def read_sites(input_sitemap_url, input_skip, input_take):
    ignore_none_html = True
    sitemaps = read_sitemap(input_sitemap_url, input_skip, input_take, ignore_none_html)

    sites = []
    for index, address in enumerate(sitemaps['all']):
        sites.append((index, address))

    return sites

def read_sitemap(input_sitemap_url, input_skip, input_take, ignore_none_html):
    result = {
        'all': [],
        input_sitemap_url: []
    }

    if input_sitemap_url.endswith('.xml.gz'):
        # unpack gzip:ed sitemap
        sitemap_content = httpRequestGetContent(input_sitemap_url, True, False)
        gzip_io = io.BytesIO(sitemap_content)
        with gzip.GzipFile(fileobj=gzip_io, mode='rb') as gzip_file:
            gzip_content = gzip_file.read()
            sitemap_content = gzip_content.decode('utf-8', 'ignore')
            result = merge_dicts(read_sitemap_xml(
                input_sitemap_url,
                sitemap_content,
                input_skip,
                input_take,
                ignore_none_html), result, True, False)
    else:
        sitemap_content = httpRequestGetContent(input_sitemap_url, True, True)
        result = merge_dicts(read_sitemap_xml(input_sitemap_url,
            sitemap_content,
            input_skip,
            input_take,
            ignore_none_html), result, True, False)
        
    return result

def read_sitemap_xml(key, sitemap_content, input_skip, input_take, ignore_none_html):
    result = {
        'all': [],
        key: []
    }

    soup = BeautifulSoup(sitemap_content, 'xml')

    root_element = None
    is_sitemap_index = False
    for element in soup.contents:
        if element.name is None:
            continue
        low_name = element.name.lower()
        if 'sitemapindex' == low_name:
            root_element = element
            is_sitemap_index = True
            break
        elif 'urlset' == low_name:
            root_element = element
            break

    if root_element is None:
        return result

    # Get the direct children of the root element
    children = [child for child in root_element.children \
                if child.name == 'url' or child.name == 'sitemap']


    nof_children = len(children)
    print('\tnof_children =', nof_children)

    # https://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd
    current_index = 0
    for child in children:
        loc_children = [child for child in child.children \
                    if child.name == 'loc']
        if len(loc_children) == 0:
            continue

        item_url = loc_children[0].text

        if not use_item(current_index, input_skip, input_take):
            current_index += 1
            continue

        if is_sitemap_index:
            print('\tsitemap =', item_url)

            result = merge_dicts(read_sitemap(
                item_url,
                input_skip,
                input_take,
                ignore_none_html), result, True, False)
            current_index += len(result['all'])
        else:
            if ignore_none_html:
                item_type = 'html'
                parsed_item_url = urlparse(item_url)
                tmp = os.path.splitext(parsed_item_url.path)[1].strip('.').lower()
                ext_len = len(tmp)
                if ext_len <= 11 and ext_len >= 2:
                    item_type = tmp

                if 'html' != item_type and 'htm' != item_type:
                    print(f'- skipping because it is of type: {item_type}')
                    continue

                item_content_type = get_content_type(item_url, cache_time_delta)
                print('content-type', item_content_type)
                if item_content_type == 401:
                    print(f'- skipping because it is of status-code: {item_content_type}')
                    continue
                elif item_content_type is not None and 'html' not in item_content_type:
                    print(f'- skipping because it is of content-type: {item_content_type}')
                    continue
            result['all'].append(item_url)
            result[key].append(item_url)
        current_index += 1
    return result


def add_site(input_filename, _, input_skip, input_take):
    print("WARNING: sitemap engine is a read only method for testing all pages in a sitemap.xml,"
          ,"NO changes will be made")

    sites = read_sites(input_filename, input_skip, input_take)

    return sites


def delete_site(input_filename, _, input_skip, input_take):
    print("WARNING: sitemap engine is a read only method for testing all pages in a sitemap.xml,"
          ,"NO changes will be made")

    sites = read_sites(input_filename, input_skip, input_take)

    return sites
