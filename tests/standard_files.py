# -*- coding: utf-8 -*-
from models import Rating
import datetime
import requests
import urllib  # https://docs.python.org/3/library/urllib.parse.html
from bs4 import BeautifulSoup
import config
from tests.utils import *
import gettext
_local = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
review_show_improvements_only = config.review_show_improvements_only


def run_test(_, langCode, url):
    """
    Looking for:
    * robots.txt
    * at least one sitemap/siteindex mentioned in robots.txt
    * a RSS feed mentioned in the page's meta
    """

    language = gettext.translation(
        'standard_files', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    o = urllib.parse.urlparse(url)
    parsed_url = '{0}://{1}/'.format(o.scheme, o.netloc)

    rating = Rating(_, review_show_improvements_only)
    return_dict = dict()

    # robots.txt
    robots_result = validate_robots(_, _local, parsed_url)
    rating += robots_result[0]
    return_dict.update(robots_result[1])
    robots_content = robots_result[2]

    # sitemap.xml
    has_robots_txt = return_dict['robots.txt'] == 'ok'
    sitemap_result = validate_sitemap(_, _local, robots_content, has_robots_txt)
    rating += sitemap_result[0]
    return_dict.update(sitemap_result[1])

    # rss feed
    feed_result = validate_feed(_, _local, url)
    rating += feed_result[0]
    return_dict.update(feed_result[1])

    # security.txt
    security_txt_result = validate_security_txt(_, _local, parsed_url)
    rating += security_txt_result[0]
    return_dict.update(security_txt_result[1])

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)


def validate_robots(_, _local, parsed_url):
    return_dict = dict()
    rating = Rating(_, review_show_improvements_only)

    robots_content = httpRequestGetContent(parsed_url + 'robots.txt', True)

    if robots_content == None or '</html>' in robots_content.lower() or ('user-agent' not in robots_content.lower() and 'disallow' not in robots_content.lower() and 'allow' not in robots_content.lower()):
        rating.set_overall(1.0, _local("TEXT_ROBOTS_MISSING"))
        rating.set_standards(1.0, _local("TEXT_ROBOTS_MISSING"))
        return_dict['robots.txt'] = 'missing content'
        robots_content = ''
    else:
        rating.set_overall(5.0, _local("TEXT_ROBOTS_OK"))
        rating.set_standards(5.0, _local("TEXT_ROBOTS_OK"))

        return_dict['robots.txt'] = 'ok'

    return (rating, return_dict, robots_content)


def validate_sitemap(_, _local, robots_content, has_robots_txt):
    rating = Rating(_, review_show_improvements_only)
    return_dict = dict()
    return_dict["num_sitemaps"] = 0

    if robots_content == None or not has_robots_txt or 'sitemap:' not in robots_content.lower():
        rating.set_overall(1.0, _local("TEXT_SITEMAP_MISSING"))
        rating.set_standards(1.0, _local("TEXT_SITEMAP_MISSING"))
        return_dict['sitemap'] = 'not in robots.txt'
    else:
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

            smap_content = httpRequestGetContent(found_smaps[0], True)

            if not is_sitemap(smap_content):
                rating.set_overall(
                    3.0, _local("TEXT_SITEMAP_FOUND") + _local("TEXT_SITEMAP_BROKEN"))
                rating.set_standards(
                    3.0, _local("TEXT_SITEMAP_FOUND") + _local("TEXT_SITEMAP_BROKEN"))
                return_dict['sitemap_check'] = '\'{0}\' seem to be broken'.format(
                    found_smaps[0])
            else:
                rating.set_overall(
                    5.0, _local("TEXT_SITEMAP_OK"))
                rating.set_standards(
                    5.0, _local("TEXT_SITEMAP_OK"))
                return_dict['sitemap_check'] = '\'{0}\' seem ok'.format(
                    found_smaps[0])
        else:
            rating.set_overall(2.0, _local("TEXT_SITEMAP_FOUND"))
            rating.set_standards(2.0, _local("TEXT_SITEMAP_FOUND"))

    return (rating, return_dict)


def is_feed(tag):

    if tag.name != 'link':
        return False

    if tag.has_attr('type'):
        tag_type = tag['type']
        if 'application/rss+xml' in tag_type:
            return True
        if 'application/atom+xml' in tag_type:
            return True
        if 'application/feed+json' in tag_type:
            return True
    return False


def validate_feed(_, _local, url):
    # TODO: validate first feed

    return_dict = dict()
    feed = list()
    rating = Rating(_, review_show_improvements_only)

    headers = {'user-agent': config.useragent}
    try:
        request = requests.get(url, allow_redirects=True,
                               headers=headers, timeout=request_timeout)
        soup = BeautifulSoup(request.text, 'lxml')
        feed = soup.find_all(is_feed)
    except:
        #print('Exception looking for feed, probably connection problems')
        pass

    if len(feed) == 0:
        rating.set_overall(4.5, _local("TEXT_RSS_FEED_MISSING"))
        #rating.set_standards(1.0, _("TEXT_RSS_FEED_MISSING"))
        return_dict['feed'] = 'not in meta'
        return_dict['num_feeds'] = len(feed)
    elif len(feed) > 0:
        rating.set_overall(5.0, _local("TEXT_RSS_FEED_FOUND"))
        #rating.set_standards(5.0, _("TEXT_RSS_FEED_FOUND"))
        return_dict['feed'] = 'found in meta'
        return_dict['num_feeds'] = len(feed)
        tmp_feed = []
        for single_feed in feed:
            tmp_feed.append(single_feed.get('href'))

        return_dict['feeds'] = tmp_feed

    return (rating, return_dict)


def validate_security_txt(_,_local, parsed_url):
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
        security_wellknown_url, True)

    # security.txt can also be placed in root if for example technical reasons prohibit use of /.well-known/
    security_root_url = parsed_url + 'security.txt'
    try:
        security_root_request = requests.get(security_root_url, allow_redirects=True,
                                             headers=headers, timeout=request_timeout)
    except:
        #print('Exception looking for security.txt, probably connection problems')
        pass
    security_root_content = httpRequestGetContent(security_root_url, True)

    #print('security_wellknown_content:', security_wellknown_content)
    #print('security_root_content:', security_root_content)

    if not security_wellknown_request and not security_root_request:
        # Can't find security.txt (not giving us 200 as status code)
        rating = Rating(_, review_show_improvements_only)
        rating.set_overall(1.0, _local("TEXT_SECURITY_MISSING"))
        rating.set_standards(1.0, _local("TEXT_SECURITY_MISSING"))
        rating.set_integrity_and_security(1.0, _local("TEXT_SECURITY_MISSING"))

        return_dict = dict()
        return_dict['security.txt'] = 'missing'
        return (rating, return_dict)
    else:
        security_wellknown_result = rate_securitytxt_content(
            security_wellknown_content, _, _local)
        security_root_result = rate_securitytxt_content(
            security_root_content, _, _local)

        #print('result1:', security_wellknown_result)
        #print('result2:', security_root_result)
        security_wellknown_rating = security_wellknown_result[0]
        security_root_rating = security_root_result[0]

        if (security_wellknown_rating.get_overall() != security_root_rating.get_overall()):
            if security_wellknown_rating.get_overall() > security_root_rating.get_overall():
                return security_wellknown_result
            else:
                return security_root_result
        else:
            return security_wellknown_result


def rate_securitytxt_content(content, _, _local):
    rating = Rating(_, review_show_improvements_only)
    return_dict = dict()
    if content == None or ('<html' in content.lower()):
        # Html (404 page?) content instead of expected content
        rating.set_overall(1.0, _local("TEXT_SECURITY_WRONG_CONTENT"))
        rating.set_standards(1.0, _local("TEXT_SECURITY_WRONG_CONTENT"))
        rating.set_integrity_and_security(
            1.0, _local("TEXT_SECURITY_WRONG_CONTENT"))
        return_dict['security.txt'] = 'wrong content'
    elif ('contact:' in content.lower() and 'expires:' in content.lower()):
        # Everything seems ok
        rating.set_overall(5.0, _local("TEXT_SECURITY_OK_CONTENT"))
        rating.set_standards(5.0, _local("TEXT_SECURITY_OK_CONTENT"))
        rating.set_integrity_and_security(5.0, _local("TEXT_SECURITY_OK_CONTENT"))
        return_dict['security.txt'] = 'ok'
    elif not ('contact:' in content.lower()):
        # Missing required Contact
        rating.set_overall(2.5, _local("TEXT_SECURITY_REQUIRED_CONTACT_MISSING"))
        rating.set_standards(2.5, _local("TEXT_SECURITY_REQUIRED_CONTACT_MISSING"))
        rating.set_integrity_and_security(
            2.5, _local("TEXT_SECURITY_REQUIRED_CONTACT_MISSING"))
        return_dict['security.txt'] = 'required contact missing'
    elif not ('expires:' in content.lower()):
        # Missing required Expires (added in version 10 of draft)
        rating.set_overall(2.5, _local("TEXT_SECURITY_REQUIRED_EXPIRES_MISSING"))
        rating.set_standards(2.5, _local("TEXT_SECURITY_REQUIRED_EXPIRES_MISSING"))
        rating.set_integrity_and_security(
            4.0, _local("TEXT_SECURITY_REQUIRED_EXPIRES_MISSING"))
        return_dict['security.txt'] = 'required expires missing'
        # print('* security.txt required content is missing')

        # print(security_wellknown_content)
        # print('* security.txt seems ok')
    else:
        rating.set_overall(1.0, _local("TEXT_SECURITY_WRONG_CONTENT"))

    return (rating, return_dict)
