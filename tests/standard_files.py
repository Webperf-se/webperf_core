# -*- coding: utf-8 -*-
import os
from urllib.parse import urlparse
from datetime import datetime
import re
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import gettext
import requests
from bs4 import BeautifulSoup
import config
from models import Rating
from tests.utils import has_redirect, httpRequestGetContent
from engines.sitemap import read_sitemap
_local = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
review_show_improvements_only = config.review_show_improvements_only

try:
    use_detailed_report = config.use_detailed_report
except AttributeError:
    # If use_detailed_report variable is not set in config.py this will be the default
    use_detailed_report = False


def run_test(_, lang_code, url):
    """
    Looking for:
    * robots.txt
    * at least one sitemap/siteindex mentioned in robots.txt
    * a RSS feed mentioned in the page's meta
    """

    language = gettext.translation(
        'standard_files', localedir='locales', languages=[lang_code])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    o = urllib.parse.urlparse(url)
    parsed_url = f'{o.scheme}://{o.netloc}/'

    rating = Rating(_, review_show_improvements_only)
    return_dict = {}

    # robots.txt
    robots_result = validate_robots(_, _local, parsed_url)
    rating += robots_result[0]
    return_dict.update(robots_result[1])
    robots_content = robots_result[2]

    # sitemap.xml
    has_robots_txt = return_dict['robots.txt'] == 'ok'

    robots_txt_url = parsed_url + 'robots.txt'
    test = has_redirect(robots_txt_url)
    if test[1] is not None:
        robots_txt_url = test[1]

    sitemap_result = validate_sitemaps(
        _, _local, robots_txt_url, robots_content, has_robots_txt)
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
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)


def validate_robots(_, _local, parsed_url):
    return_dict = dict()
    rating = Rating(_, review_show_improvements_only)

    robots_content = httpRequestGetContent(parsed_url + 'robots.txt', True)

    if robots_content is None or '</html>' in robots_content.lower() or \
          ('user-agent' not in robots_content.lower() \
           and 'disallow' not in robots_content.lower() \
           and 'allow' not in robots_content.lower()):
        rating.set_overall(1.0)
        rating.set_standards(1.0, _local("TEXT_ROBOTS_MISSING"))
        return_dict['robots.txt'] = 'missing content'
        robots_content = ''
    else:
        rating.set_overall(5.0)
        rating.set_standards(5.0, _local("TEXT_ROBOTS_OK"))

        return_dict['robots.txt'] = 'ok'

    return (rating, return_dict, robots_content)


def validate_sitemaps(_, _local, robots_url, robots_content, has_robots_txt):
    rating = Rating(_, review_show_improvements_only)
    return_dict = dict()
    return_dict["num_sitemaps"] = 0

    if robots_content is None or not has_robots_txt or 'sitemap:' not in robots_content.lower():
        rating.set_overall(1.0)
        rating.set_standards(1.0, _local("TEXT_SITEMAP_MISSING"))
        return_dict['sitemap'] = 'not in robots.txt'
    else:
        return_dict['sitemap'] = 'ok'

        regex = r"^sitemap\:(?P<url>[^\n]+)"
        found_smaps = []
        matches = re.finditer(regex, robots_content, re.MULTILINE | re.IGNORECASE)
        for matchNum, match in enumerate(matches, start=1):
            sitemap_url = match.group('url').strip()
            found_smaps.append(sitemap_url)

        return_dict["num_sitemaps"] = len(found_smaps)

        # NOTE: https://internetverkstan.se/ has styled sitemap

        if len(found_smaps) > 0:
            return_dict["sitemaps"] = found_smaps

            sitemaps_rating = Rating(_, review_show_improvements_only)
            for sitemap_url in found_smaps:
                sitemaps_rating += validate_sitemap(sitemap_url, robots_url, return_dict, _, _local)

            final_rating = Rating(_, review_show_improvements_only)
            if sitemaps_rating.is_set:
                if use_detailed_report:
                    final_rating.set_overall(sitemaps_rating.get_overall())
                    final_rating.overall_review = sitemaps_rating.overall_review
                    final_rating.set_standards(sitemaps_rating.get_standards())
                    final_rating.standards_review = sitemaps_rating.standards_review
                else:
                    review = ''
                    points = sitemaps_rating.get_standards()
                    if points >= 5.0:
                        review = _local('TEXT_SITEMAP_VERY_GOOD')
                    elif points >= 4.0:
                        review = _local('TEXT_SITEMAP_IS_GOOD')
                    elif points >= 3.0:
                        review = _local('TEXT_SITEMAP_IS_OK')
                    elif points > 1.0:
                        review = _local('TEXT_SITEMAP_IS_BAD')
                    elif points <= 1.0:
                        review = _local('TEXT_SITEMAP_IS_VERY_BAD')



                    final_rating.set_overall(sitemaps_rating.get_overall())
                    final_rating.set_standards(
                        points,
                        review)
            rating += final_rating
        else:
            rating.set_overall(2.0)
            rating.set_standards(2.0, _local("TEXT_SITEMAP_FOUND"))

    return (rating, return_dict)

def validate_sitemap(sitemap_url, robots_url, return_dict, _, _local):
    rating = Rating(_, review_show_improvements_only)

    known_extensions = ['bmp', 'css', 'doc', 'docx', 'dot', 'eot', 'exe', 'git',
                        'ico', 'ics', 'jpeg', 'jpg', 'js','json', 'md', 'mov', 'mp3',
                        'mp4', 'pdf', 'png', 'ppt', 'pptx', 'pub', 'svg', 'tif',
                        'txt', 'unknown-in-download', 'webp', 'wmv', 'xls', 'xlsx', 'xml', 'zip']

    parsed_robots_url = urllib.parse.urlparse(robots_url)
    robots_domain = parsed_robots_url.hostname

    sitemaps = read_sitemap(sitemap_url, -1, -1, False)
    sitemap_items = sitemaps['all']

    item_types = {}
    type_spread = {}
    always_starts_with_https_scheme = True
    always_uses_same_domain = True
    for item_url in sitemap_items:
        item_type = 'webpage'

        if not item_url.lower().startswith('https://'):
            always_starts_with_https_scheme = False

        parsed_item_url = urlparse(item_url)
        if robots_domain != parsed_item_url.hostname:
            always_uses_same_domain = False

        tmp = os.path.splitext(parsed_item_url.path)[1].strip('.').lower()
        ext_len = len(tmp)
        if ext_len <= 4 and ext_len >= 2:
            if tmp in known_extensions:
                item_type = tmp
        elif parsed_item_url.path.startswith('/download/'):
            item_type = 'unknown-in-download'

        if item_type not in item_types:
            item_types[item_type] = []
        item_types[item_type].append(item_url)

    item_type_keys = sorted(list(item_types.keys()))
    total_nof_items = len(sitemap_items)
    sitemap_items = list(set(sitemap_items))
    total_nof_items_no_duplicates = len(sitemap_items)

    if not always_starts_with_https_scheme:
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(
                    1.0)
        sub_rating.set_standards(
                    1.0, _local("TEXT_SITEMAP_NOT_STARTING_WITH_HTTPS_SCHEME"))
        rating += sub_rating
    else:
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, _local("TEXT_SITEMAP_STARTING_WITH_HTTPS_SCHEME"))
        rating += sub_rating

    if not always_uses_same_domain:
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(
                    1.0)
        sub_rating.set_standards(
                    1.0, _local("TEXT_SITEMAP_NOT_SAME_DOMAIN_AS_ROBOTS_TXT"))
        rating += sub_rating
    else:
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, _local("TEXT_SITEMAP_SAME_DOMAIN_AS_ROBOTS_TXT"))
        rating += sub_rating

    if total_nof_items !=  total_nof_items_no_duplicates:
        ratio = total_nof_items_no_duplicates / total_nof_items
        duplicates_points = 3.0 * ratio
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(
                    duplicates_points)
        sub_rating.set_standards(
                    duplicates_points, _local("TEXT_SITEMAP_INCLUDE_DUPLICATES"))
        rating += sub_rating
    else:
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, _local("TEXT_SITEMAP_NO_DUPLICATES"))
        rating += sub_rating

    if len(item_type_keys) > 1:
        webpages_points = 1.0
        if 'webpage' in item_type_keys:
            nof_webpages = len(item_types['webpage'])
            ratio = nof_webpages / total_nof_items
            webpages_points = 5.0 * ratio

        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(
                    webpages_points)
        sub_rating.set_standards(
                    webpages_points,  _local("TEXT_SITEMAP_NOT_ONLY_WEBPAGES"))
        rating += sub_rating
    else:
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, _local("TEXT_SITEMAP_ONLY_WEBPAGES"))
        rating += sub_rating

    # loop sitemaps and see if any single sitemap exsits amount
    for key in sitemaps.keys():
        if key == 'all':
            continue

        nof_items = len(sitemaps[key])

        if nof_items > 50_000:
            sub_rating = Rating(_, review_show_improvements_only)
            sub_rating.set_overall(
                        1.0)
            sub_rating.set_standards(
                        1.0,  _local("TEXT_SITEMAP_TOO_LARGE"))
            rating += sub_rating
        else:
            sub_rating = Rating(_, review_show_improvements_only)
            sub_rating.set_overall(
                        5.0)
            sub_rating.set_standards(
                        5.0, _local("TEXT_SITEMAP_NOT_TOO_LARGE"))
            rating += sub_rating

    for key in item_type_keys:
        # remove duplicates
        item_types[key] = list(set(item_types[key]))
        type_spread[key] = len(item_types[key])

    if total_nof_items == 0:
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(
                    1.0)
        sub_rating.set_standards(
                    1.0, _local("TEXT_SITEMAP_BROKEN"))
        rating += sub_rating

        return_dict['sitemap_check'] = f"'{sitemap_url}' seem to be broken"
    else:
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, _local("TEXT_SITEMAP_IS_OK"))
        rating += sub_rating

        return_dict['sitemap_check'] = f"'{sitemap_url}' seem ok"
    return rating


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
    return_dict = {}
    feed = []
    rating = Rating(_, review_show_improvements_only)

    headers = {'user-agent': config.useragent}
    try:
        request = requests.get(url, allow_redirects=True,
                               headers=headers, timeout=request_timeout)
        soup = BeautifulSoup(request.text, 'lxml')
        feed = soup.find_all(is_feed)
    except:
        pass

    if len(feed) == 0:
        rating.set_overall(4.5, _local("TEXT_RSS_FEED_MISSING"))
        return_dict['feed'] = 'not in meta'
        return_dict['num_feeds'] = len(feed)
    elif len(feed) > 0:
        rating.set_overall(5.0, _local("TEXT_RSS_FEED_FOUND"))
        return_dict['feed'] = 'found in meta'
        return_dict['num_feeds'] = len(feed)
        tmp_feed = []
        for single_feed in feed:
            tmp_feed.append(single_feed.get('href'))

        return_dict['feeds'] = tmp_feed

    return (rating, return_dict)


def validate_security_txt(_, _local, parsed_url):
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
        pass

    security_wellknown_content = httpRequestGetContent(
        security_wellknown_url, True)

    # Note: security.txt can also be placed in root if
    # for example technical reasons prohibit use of /.well-known/
    security_root_url = parsed_url + 'security.txt'
    try:
        security_root_request = requests.get(security_root_url, allow_redirects=True,
                                             headers=headers, timeout=request_timeout)
    except:
        pass
    security_root_content = httpRequestGetContent(security_root_url, True)

    if not security_wellknown_request and not security_root_request:
        # Can't find security.txt (not giving us 200 as status code)
        rating = Rating(_, review_show_improvements_only)
        rating.set_overall(1.0)
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

        security_wellknown_rating = security_wellknown_result[0]
        security_root_rating = security_root_result[0]

        if security_wellknown_rating.get_overall() == security_root_rating.get_overall():
            return security_wellknown_result

        if security_wellknown_rating.get_overall() > security_root_rating.get_overall():
            return security_wellknown_result
        else:
            return security_root_result


def rate_securitytxt_content(content, _, _local):
    rating = Rating(_, review_show_improvements_only)
    return_dict = {}
    if content is None or ('<html' in content.lower()):
        # Html (404 page?) content instead of expected content
        rating.set_overall(1.0)
        rating.set_standards(1.0, _local("TEXT_SECURITY_WRONG_CONTENT"))
        rating.set_integrity_and_security(
            1.0, _local("TEXT_SECURITY_WRONG_CONTENT"))
        return_dict['security.txt'] = 'wrong content'
    elif ('contact:' in content.lower() and 'expires:' in content.lower()):
        # Everything seems ok
        rating.set_overall(5.0)
        rating.set_standards(5.0, _local("TEXT_SECURITY_OK_CONTENT"))
        rating.set_integrity_and_security(
            5.0, _local("TEXT_SECURITY_OK_CONTENT"))
        return_dict['security.txt'] = 'ok'
    elif not 'contact:' in content.lower():
        # Missing required Contact
        rating.set_overall(2.5)
        rating.set_standards(2.5, _local(
            "TEXT_SECURITY_REQUIRED_CONTACT_MISSING"))
        rating.set_integrity_and_security(
            2.5, _local("TEXT_SECURITY_REQUIRED_CONTACT_MISSING"))
        return_dict['security.txt'] = 'required contact missing'
    elif not 'expires:' in content.lower():
        # Missing required Expires (added in version 10 of draft)
        rating.set_overall(2.5)
        rating.set_standards(2.5, _local(
            "TEXT_SECURITY_REQUIRED_EXPIRES_MISSING"))
        rating.set_integrity_and_security(
            4.0, _local("TEXT_SECURITY_REQUIRED_EXPIRES_MISSING"))
        return_dict['security.txt'] = 'required expires missing'
    else:
        rating.set_overall(1.0, _local("TEXT_SECURITY_WRONG_CONTENT"))

    return (rating, return_dict)
