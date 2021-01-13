# -*- coding: utf-8 -*-
import sys
import socket
import ssl
import json
import requests
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
from bs4 import BeautifulSoup
import config
from tests.utils import *
import gettext
_ = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent


def run_test(langCode, url):
    """
    Looking for:
    * robots.txt
    * at least one sitemap/siteindex mentioned in robots.txt
    * a RSS feed mentioned in the page's meta
    """

    language = gettext.translation(
        'standard_files', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

    o = urllib.parse.urlparse(url)
    parsed_url = '{0}://{1}/'.format(o.scheme, o.netloc)

    review = ''
    return_dict = dict()
    points = 5.0

    # robots.txt (up to -3)
    robots_result = validate_robots(_, parsed_url)
    points -= robots_result[0]
    review += robots_result[1]
    return_dict.update(robots_result[2])
    robots_content = robots_result[3]

    # sitemap.xml (up to -3)
    has_robots_txt = return_dict['robots.txt'] == 'ok'
    sitemap_result = validate_sitemap(_, robots_content, has_robots_txt)
    points -= sitemap_result[0]
    review += sitemap_result[1]
    return_dict.update(sitemap_result[2])

    # rss feed (up to -0.5)
    feed_result = validate_feed(_, url)
    points -= feed_result[0]
    review += feed_result[1]
    return_dict.update(feed_result[2])

    # security.txt (up to -1)
    security_txt_result = validate_security_txt(_, parsed_url)
    points -= security_txt_result[0]
    review += security_txt_result[1]
    return_dict.update(security_txt_result[2])

    # minimum score is 1, make sure we have at least 1
    if points < 1:
        points = 1

    return (points, review, return_dict)


def validate_robots(_, parsed_url):
    review = ''
    return_dict = dict()
    points = 0.0

    robots_content = httpRequestGetContent(parsed_url + 'robots.txt')

    if robots_content == None or '</html>' in robots_content.lower() or ('user-agent' not in robots_content.lower() and 'disallow' not in robots_content.lower() and 'allow' not in robots_content.lower()):
        points = 3
        review += _("TEXT_ROBOTS_MISSING")
        return_dict['robots.txt'] = 'missing content'
        robots_content = ''
    else:
        review += _("TEXT_ROBOTS_OK")
        return_dict['robots.txt'] = 'ok'

    return (points, review, return_dict, robots_content)


def validate_sitemap(_, robots_content, has_robots_txt):
    review = ''
    return_dict = dict()
    return_dict["num_sitemaps"] = 0
    points = 0.0

    if robots_content == None or not has_robots_txt or 'sitemap:' not in robots_content.lower():
        points += 2
        review += _("TEXT_SITEMAP_MISSING")
        return_dict['sitemap'] = 'not in robots.txt'
    else:
        review += _("TEXT_SITEMAP_FOUND")
        return_dict['sitemap'] = 'ok'

        smap_pos = robots_content.lower().find('sitemap')
        smaps = robots_content[smap_pos:].split('\n')
        found_smaps = []
        for line in smaps:
            if 'sitemap:' in line.lower():
                found_smaps.append(
                    line.lower().replace('sitemap:', '').strip())

        return_dict["num_sitemaps"] = len(found_smaps)

        if len(found_smaps) > 0:
            return_dict["sitemaps"] = found_smaps

            smap_content = httpRequestGetContent(found_smaps[0])

            if not is_sitemap(smap_content):
                points += 1
                review += _("TEXT_SITEMAP_BROKEN")
                return_dict['sitemap_check'] = '\'{0}\' seem to be broken'.format(
                    found_smaps[0])
            else:
                review += _("TEXT_SITEMAP_OK")
                return_dict['sitemap_check'] = '\'{0}\' seem ok'.format(
                    found_smaps[0])

    return (points, review, return_dict)


def validate_feed(_, url):
    # TODO: validate first feed

    review = ''
    return_dict = dict()
    points = 0.0
    feed = list()

    headers = {'user-agent': config.useragent}
    try:
        request = requests.get(url, allow_redirects=True,
                               headers=headers, timeout=request_timeout)
        soup = BeautifulSoup(request.text, 'lxml')
        # feed = soup.find_all(rel='alternate')
        feed = soup.find_all("link", {"type": "application/rss+xml"})

    except:
        #print('Exception looking for feed, probably connection problems')
        pass

    if len(feed) == 0:
        points = 0.5
        review += _("TEXT_RSS_FEED_MISSING")
        return_dict['feed'] = 'not in meta'
        return_dict['num_feeds'] = len(feed)
    elif len(feed) > 0:
        review += _("TEXT_RSS_FEED_FOUND")
        return_dict['feed'] = 'found in meta'
        return_dict['num_feeds'] = len(feed)
        tmp_feed = []
        for single_feed in feed:
            tmp_feed.append(single_feed.get('href'))

        return_dict['feeds'] = tmp_feed

    return (points, review, return_dict)


def validate_security_txt(_, parsed_url):
    security_wellknown_request = False
    security_root_request = False

    headers = {
        'user-agent': useragent}
    # normal location for security.txt
    security_wellknown_url = parsed_url + '.well-known/security.txt'
    try:
        security_wellknown_request = requests.get(security_wellknown_url, allow_redirects=True,
                                                  headers=headers, timeout=request_timeout)
    except:
        #print('Exception looking for security.txt, probably connection problems')
        pass

    security_wellknown_content = httpRequestGetContent(
        security_wellknown_url)

    # security.txt can also be placed in root if for example technical reasons prohibit use of /.well-known/
    security_root_url = parsed_url + 'security.txt'
    try:
        security_root_request = requests.get(security_root_url, allow_redirects=True,
                                             headers=headers, timeout=request_timeout)
    except:
        #print('Exception looking for security.txt, probably connection problems')
        pass
    security_root_content = httpRequestGetContent(security_root_url)

    print('security_wellknown_content:', security_wellknown_content)
    print('security_root_content:', security_root_content)

    if not security_wellknown_request and not security_root_request:
        # Can't find security.txt (not giving us 200 as status code)
        points = 1.0
        review = ''
        return_dict = dict()
        review = _("TEXT_SECURITY_MISSING")
        return_dict['security.txt'] = 'missing'
        return (points, review, return_dict)
    else:
        security_wellknown_result = rate_securitytxt_content(
            security_wellknown_content, _)
        security_root_result = rate_securitytxt_content(
            security_root_content, _)

        print('result1:', security_wellknown_result)
        print('result2:', security_root_result)
        security_wellknown_points = security_wellknown_result[0]
        security_root_points = security_root_result[0]

        if (security_wellknown_points != security_root_points):
            if security_wellknown_points < security_root_points:
                return security_wellknown_result
            else:
                return security_root_result
        else:
            return security_wellknown_result


def rate_securitytxt_content(content, _):
    review = ''
    return_dict = dict()
    points = -10.0
    if content == None or ('<html' in content.lower()):
        # Html (404 page?) content instead of expected content
        points = 1.0
        review += _("TEXT_SECURITY_WRONG_CONTENT")
        return_dict['security.txt'] = 'wrong content'
    elif ('contact:' in content.lower() and 'expires:' in content.lower()):
        # Everything seems ok
        points = 0.0
        review += _("TEXT_SECURITY_OK_CONTENT")
        return_dict['security.txt'] = 'ok'
    elif not ('contact:' in content.lower()):
        # Missing required Contact
        points = 0.5
        review += _("TEXT_SECURITY_REQUIRED_CONTACT_MISSING")
        return_dict['security.txt'] = 'required contact missing'
    elif not ('expires:' in content.lower()):
        # Missing required Expires (added in version 10 of draft)
        points = 0.25
        review += _("TEXT_SECURITY_REQUIRED_EXPIRES_MISSING")
        return_dict['security.txt'] = 'required expires missing'
        # print('* security.txt required content is missing')

        # print(security_wellknown_content)
        # print('* security.txt seems ok')

    return (points, review, return_dict)
