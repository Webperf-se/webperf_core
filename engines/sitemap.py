# -*- coding: utf-8 -*-
from models import Sites
from engines.utils import use_item
import config
from tests.utils import *
import re
import gzip
import io

def read_sites(input_sitemap_url, input_skip, input_take):
    ignore_none_html = True
    return read_sitemap(input_sitemap_url, input_skip, input_take, ignore_none_html)

def read_sitemap(input_sitemap_url, input_skip, input_take, ignore_none_html):
    # TODO, handle this?: <loc><![CDATA[https://melanomforeningen.se/post-sitemap.xml]]></loc>
    
    # TODO: CDATA everything: https://melanomforeningen.se/post-sitemap.xml
	# <url>
	# 	<loc><![CDATA[https://melanomforeningen.se/nyheter/]]></loc>
	# 	<lastmod><![CDATA[2024-01-26T11:22:43+00:00]]></lastmod>
	# 	<changefreq><![CDATA[weekly]]></changefreq>
	# 	<priority><![CDATA[0.7]]></priority>
	# 	<image:image>
	# 		<image:loc><![CDATA[https://melanomforeningen.se/wp-content/uploads/newspapers-444447_1280.jpg]]></image:loc>
	# 	</image:image>
	# </url>    

    if input_sitemap_url.endswith('.xml.gz'):
        # unpack gzip:ed sitemap
        sitemap_content = httpRequestGetContent(input_sitemap_url, True, False)
        gzip_io = io.BytesIO(sitemap_content)
        with gzip.GzipFile(fileobj=gzip_io, mode='rb') as gzip_file:
            gzip_content = gzip_file.read()
            sitemap_content = gzip_content.decode('utf-8', 'ignore')
            return read_sitemap_xml(sitemap_content, input_skip, input_take, ignore_none_html)
    else:
        sitemap_content = httpRequestGetContent(input_sitemap_url, True, True)
        return read_sitemap_xml(sitemap_content, input_skip, input_take, ignore_none_html)

def read_sitemap_xml(sitemap_content, input_skip, input_take, ignore_none_html):
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
        # TODO: validate url encoding ( Example: https://www.gotene.se/webdav/files/Centrumhuset/Kultur, turism & fritid/Biblioteket/hemsidefilm/loss_teckensprak.html )
        item_url = item_url.replace(' ', '%20')

        if is_recursive:
            tmp_sites = read_sitemap(item_url, input_skip, input_take, ignore_none_html)
            current_index += len(tmp_sites)
            sites.extend(tmp_sites)
        else:
            if ignore_none_html:
                item_type = 'html'
                parsed_item_url = urlparse(item_url)
                tmp = os.path.splitext(parsed_item_url.path)[1].strip('.').lower()
                ext_len = len(tmp)
                if ext_len <= 11 and ext_len >= 2:
                    item_type = tmp

                if 'html' != item_type and 'htm' != item_type:
                    print('- skipping because it is of type: {0}'.format(item_type))
                    # current_index += 1
                    continue

                item_content_type = get_content_type(item_url, cache_time_delta)
                print('content-type', item_content_type)
                if item_content_type == 401:
                    print('- skipping because it is of status-code: {0}'.format(item_content_type))
                    continue
                elif item_content_type != None and 'html' not in item_content_type:
                    print('- skipping because it is of content-type: {0}'.format(item_content_type))
                    # current_index += 1
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
