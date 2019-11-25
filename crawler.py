#-*- coding: utf-8 -*-
"""
Crawling websites for URLs
"""
#from urllib.request import urlopen, Request
import urllib
import requests
from bs4 import BeautifulSoup
import datetime
import random
import re
import time

sec_timeout = 60*1   # 1 minute from now
while_timeout = time.time() + sec_timeout
random.seed(datetime.datetime.now())

def get_links(site, pageUrl):
    try:
        html = urllib.request.urlopen(Request('{0}{1}'.format(site, pageUrl), headers={'User-Agent': 'Webperf.se Crawler'}))
        bs = BeautifulSoup(html, 'html.parser')

        return bs.find_all('a', href=re.compile('^/')) # only URLs starting with /
    except Exception as e:
        print(site, pageUrl, '\n', e)
        return None

def check_for_redirect(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout = 5)
        return r.url, r.history, r.status_code, r.headers['Content-Type']
    except:
        return None

def harvest_links(site = 'https://www.vgregion.se', initial_page = '/', max_pages = 50, print_progress=False, timeout=while_timeout):
    """
    Returns URL found on a website
    """
    links = get_links(site, initial_page)
    i = 0
    urls = []

    if print_progress:
        print('Looking for at most {} URLs at {} for {} seconds'.format(max_pages, site, sec_timeout))

    while len(links) > 0 and i < max_pages:
        newPage = links[random.randint(0, len(links)-1)].attrs['href']

        if site + newPage not in urls and 'mailto' not in newPage and '#' not in newPage and newPage != None and 'http' not in newPage and '.pdf' not in newPage and '.docx' not in newPage and '.pptx' not in newPage:

            check_redir = check_for_redirect(site + newPage)
            if(check_redir is not None and site in check_redir[0] and check_redir[2] == 200 and 'text/html' in check_redir[3]):
                i += 1
                if print_progress:
                    print(i, newPage)
                urls.append(site + newPage)

                new_links = get_links(site, newPage)
                if new_links is not None:
                    links = new_links
            elif print_progress:
                # check_redir[0] do not work for all content-types
                print('Redirection, content-type or status code error detected. URL skipped.\n', check_redir)

        if time.time() > while_timeout:
            break

    return urls

"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    urls = harvest_links(site='http://intra.vgregion.se', initial_page='/sv/Insidan/amnesomraden/', max_pages=100, print_progress=True)
    print(urls)
    file = open('urls.txt','w')

    file.write(str(urls))
    file.close()