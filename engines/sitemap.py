# -*- coding: utf-8 -*-
import os
from urllib.parse import urlparse
import gzip
import io
from bs4 import BeautifulSoup
from engines.utils import use_item
from tests.utils import get_http_content, merge_dicts

def read_sites(input_sitemap_url, input_skip, input_take):
    """
    This function reads site data from a specific sitemap.
    
    Parameters:
    input_url (str): Absolute url to sitemap, .xml and .xml.bz fileendings are supported.
    input_skip (int): The number of lines to skip in the input file.
    input_take (int): The number of lines to take from the input file after skipping.
    
    Returns:
    list: The list of sites read from the specified sitemap.
    """
    ignore_none_html = True
    sitemaps = read_sitemap(input_sitemap_url, input_skip, input_take, ignore_none_html)

    sites = []
    for index, address in enumerate(sitemaps['all']):
        sites.append((index, address))

    return sites

def read_sitemap(input_sitemap_url, input_skip, input_take, ignore_none_html):
    """
    This function reads a sitemap from a given URL,
    which can be in XML or gzipped XML format.
    It then parses the sitemap content, filters the URLs based on certain conditions,
    and returns a dictionary of URLs.
    
    Parameters:
    input_sitemap_url (str): The URL of the sitemap.
    input_skip (int): The number of URLs to skip.
    input_take (int): The number of URLs to take after skipping.
    ignore_none_html (bool): If True, non-HTML URLs are ignored.
    
    Returns:
    dict: A dictionary containing all URLs and filtered URLs from the sitemap.
    """
    result = {
        'all': [],
        input_sitemap_url: []
    }

    if input_sitemap_url.endswith('.xml.gz'):
        # unpack gzip:ed sitemap
        sitemap_content = get_http_content(input_sitemap_url, True, False)
        try:
            if isinstance(sitemap_content, str):
                return result
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
        except gzip.BadGzipFile:
            return result
    else:
        sitemap_content = get_http_content(input_sitemap_url, True, True)
        result = merge_dicts(read_sitemap_xml(input_sitemap_url,
            sitemap_content,
            input_skip,
            input_take,
            ignore_none_html), result, True, False)

    return result

def read_sitemap_xml(input_url, sitemap_content, input_skip, input_take, ignore_none_html):
    """
    This function parses the XML content of a sitemap,
    filters the URLs based on certain conditions, and returns a dictionary of URLs.
    
    Parameters:
    input_url (str): The url to be used in the result dictionary for storing filtered URLs.
    sitemap_content (str): The XML content of the sitemap.
    input_skip (int): The number of URLs to skip.
    input_take (int): The number of URLs to take after skipping.
    ignore_none_html (bool): If True, non-HTML URLs are ignored.
    
    Returns:
    dict: A dictionary containing all URLs and filtered URLs.
    """
    result = {
        'all': [],
        input_url: []
    }

    root_element = get_root_element(sitemap_content)
    if root_element is None:
        return result

    # Get the direct children of the root element
    children = [child for child in root_element.children \
                if child.name in ('url', 'sitemap')]

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

        if root_element.name.lower() == 'sitemapindex':
            result = merge_dicts(read_sitemap(
                item_url,
                input_skip,
                input_take,
                ignore_none_html), result, True, False)
            current_index += len(result['all'])
        else:
            if ignore_none_html:
                item_type = 'html'
                tmp = os.path.splitext(urlparse(item_url).path)[1].strip('.').lower()
                ext_len = len(tmp)
                if 2 <= ext_len <= 11:
                    item_type = tmp

                if item_type not in ('html', 'htm'):
                    print(f'- skipping because it is of type: {item_type}')
                    continue
            result['all'].append(item_url)
            result[input_url].append(item_url)
        current_index += 1
    return result

def get_root_element(sitemap_content):
    """
    This function parses the XML content of a sitemap and returns the root element.
    
    Parameters:
    sitemap_content (str): The XML content of the sitemap.
    
    Returns:
    bs4.element.Tag: The root element of the sitemap. It could be either 'sitemapindex' or 'urlset'.
    """
    xml = BeautifulSoup(sitemap_content, 'xml')
    root_element = None
    for element in xml.contents:
        if element.name is None:
            continue
        low_name = element.name.lower()
        if 'sitemapindex' == low_name:
            root_element = element
            break
        if 'urlset' == low_name:
            root_element = element
            break
    return root_element


def add_site(input_url, _, input_skip, input_take):
    """
    This function reads site data from a specific sitemap,
    prints a warning message (because it is read only),
    
    Parameters:
    input_url (str): Absolute url to sitemap, .xml and .xml.bz fileendings are supported.
    input_skip (int): The number of lines to skip in the input file.
    input_take (int): The number of lines to take from the input file after skipping.
    
    Returns:
    list: The list of sites read from the specified sitemap.
    """

    print("WARNING: sitemap engine is a read only method for testing all pages in a sitemap.xml,"
          ,"NO changes will be made")

    sites = read_sites(input_url, input_skip, input_take)

    return sites


def delete_site(input_url, _, input_skip, input_take):
    """
    This function reads site data from a specific sitemap,
    prints a warning message (because it is read only),
    
    Parameters:
    input_url (str): Absolute url to sitemap, .xml and .xml.bz fileendings are supported.
    input_skip (int): The number of lines to skip in the input file.
    input_take (int): The number of lines to take from the input file after skipping.
    
    Returns:
    list: The list of sites read from the specified sitemap.
    """
    print("WARNING: sitemap engine is a read only method for testing all pages in a sitemap.xml,"
          ,"NO changes will be made")

    sites = read_sites(input_url, input_skip, input_take)

    return sites
