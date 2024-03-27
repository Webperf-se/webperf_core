# -*- coding: utf-8 -*-
import os
from urllib.parse import urlparse
from datetime import datetime
import re
import urllib  # https://docs.python.org/3/library/urllib.parse.html
from bs4 import BeautifulSoup
from models import Rating
from tests.utils import get_config_or_default, get_translation, has_redirect, get_http_content
from engines.sitemap import read_sitemap

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')
USE_DETAILED_REPORT = get_config_or_default('USE_DETAILED_REPORT')
KNOWN_EXTENSIONS = ['bmp', 'css', 'doc', 'docx', 'dot', 'eot', 'exe', 'git',
                    'ico', 'ics', 'jpeg', 'jpg', 'js','json', 'md', 'mov', 'mp3',
                    'mp4', 'pdf', 'png', 'ppt', 'pptx', 'pub', 'svg', 'tif',
                    'txt', 'unknown-in-download', 'webp', 'wmv', 'xls', 'xlsx', 'xml', 'zip']


def run_test(global_translation, lang_code, url):
    """
    Looking for:
    * robots.txt
    * at least one sitemap/siteindex mentioned in robots.txt
    * a RSS feed mentioned in the page's meta
    """

    local_translation = get_translation('standard_files', lang_code)

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    parsed_url = get_root_url(url)

    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    return_dict = {}

    # robots.txt
    robots_result = validate_robots(global_translation, local_translation, parsed_url)
    rating += robots_result[0]
    return_dict.update(robots_result[1])
    robots_content = robots_result[2]

    # sitemap.xml
    sitemap_result = validate_sitemaps(
        global_translation,
        local_translation,
        robots_content,
        return_dict)
    rating += sitemap_result[0]
    return_dict.update(sitemap_result[1])

    # rss feed
    feed_result = validate_feed(global_translation, local_translation, url)
    rating += feed_result[0]
    return_dict.update(feed_result[1])

    # security.txt
    security_txt_result = validate_security_txt(global_translation, local_translation, parsed_url)
    rating += security_txt_result[0]
    return_dict.update(security_txt_result[1])

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, return_dict)

def get_root_url(url):
    o = urllib.parse.urlparse(url)
    parsed_url = f'{o.scheme}://{o.netloc}/'
    return parsed_url

def validate_robots(global_translation, local_translation, parsed_url):
    return_dict = {}
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    return_dict['robots.txt-location'] = parsed_url + 'robots.txt'

    (is_redirected, url_destination, _) = has_redirect(return_dict['robots.txt-location'])
    if is_redirected:
        return_dict['robots.txt-location'] = url_destination

    robots_content = get_http_content(return_dict['robots.txt-location'], True)

    if robots_content is None or '</html>' in robots_content.lower() or \
          ('user-agent' not in robots_content.lower() \
           and 'disallow' not in robots_content.lower() \
           and 'allow' not in robots_content.lower()):
        rating.set_overall(1.0)
        rating.set_standards(1.0, local_translation("TEXT_ROBOTS_MISSING"))
        return_dict['robots.txt'] = 'missing content'
        robots_content = None
    else:
        rating.set_overall(5.0)
        rating.set_standards(5.0, local_translation("TEXT_ROBOTS_OK"))

        return_dict['robots.txt'] = 'ok'

    return (rating, return_dict, robots_content)


def validate_sitemaps(global_translation,
                      local_translation,
                      robots_content,
                      result_dict):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    result_dict["num_sitemaps"] = 0
    result_dict["robots_txt_sitemaps"] = []

    if not result_dict['robots.txt'] != 'ok' or 'sitemap:' not in robots_content.lower():
        rating.set_overall(1.0)
        rating.set_standards(1.0, local_translation("TEXT_SITEMAP_MISSING"))
        result_dict['sitemap'] = 'not in robots.txt'
        return (rating, result_dict)

    regex = r"^sitemap\:(?P<url>[^\n]+)"
    matches = re.finditer(regex, robots_content, re.MULTILINE | re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        sitemap_url = match.group('url').strip()
        result_dict["robots_txt_sitemaps"].append(sitemap_url)

    result_dict["num_sitemaps"] = len(result_dict["robots_txt_sitemaps"])

    # NOTE: https://internetverkstan.se/ has styled sitemap

    if result_dict["num_sitemaps"] == 0:
        rating.set_overall(2.0)
        rating.set_standards(2.0, local_translation("TEXT_SITEMAP_FOUND"))
        return (rating, result_dict)

    result_dict["sitemaps"] = []

    sitemaps_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    for sitemap_url in result_dict["robots_txt_sitemaps"]:
        sitemaps_rating += validate_sitemap(sitemap_url,
                                            result_dict,
                                            global_translation,
                                            local_translation)

    if not sitemaps_rating.is_set:
        return (rating, result_dict)

    final_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if USE_DETAILED_REPORT:
        final_rating.set_overall(sitemaps_rating.get_overall())
        final_rating.overall_review = sitemaps_rating.overall_review
        final_rating.set_standards(sitemaps_rating.get_standards())
        final_rating.standards_review = sitemaps_rating.standards_review
    else:
        review = ''
        points = sitemaps_rating.get_standards()
        if points >= 5.0:
            review = local_translation('TEXT_SITEMAP_VERY_GOOD')
        elif points >= 4.0:
            review = local_translation('TEXT_SITEMAP_IS_GOOD')
        elif points >= 3.0:
            review = local_translation('TEXT_SITEMAP_IS_OK')
        elif points > 1.0:
            review = local_translation('TEXT_SITEMAP_IS_BAD')
        elif points <= 1.0:
            review = local_translation('TEXT_SITEMAP_IS_VERY_BAD')

        final_rating.set_overall(sitemaps_rating.get_overall())
        final_rating.set_standards(
            points,
            review)
    rating += final_rating

    return (rating, result_dict)

def get_domain(url):
    parsed_url = urlparse(url)
    return parsed_url.hostname

def validate_sitemap(sitemap_url, result_dict, global_translation, local_translation):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    sitemaps = read_sitemap(sitemap_url, -1, -1, False)

    for key in sitemaps.keys():
        if key == 'all':
            continue

        if key not in result_dict["sitemaps"]:
            result_dict["sitemaps"].append(key)

    sitemap_items = sitemaps['all']

    append_sitemap_data_to_result_dict(sitemap_items, result_dict)

    # {
    #     "feed": {
    #         "status": "ok",
    #         "feeds": {
    #             "https://www.eskilstuna.se/4.47f1872e1784b0a89d021732/12.47f1872e1784b0a89d021743.portlet?state=rss&sv.contenttype=text/xml;charset=UTF-8": {
    #                 "status": "ok",
    #                 "nof-items": 1337

    #             }
    #         }

    #     },
    #     "robots": {
    #         "status": "ok",
    #         "sitemaps": []
    #     },
    #     "sitemap": {
    #         "status": "ok",
    #         "sitemaps": {
    #             "https://www.eskilstuna.se/sitemapindex.xml": {
    #                 "status": "ok",
    #                 "same-domain": true,
    #                 "https-only": true,
    #                 "has-duplicates": false,
    #                 "types": ["webpages"],
    #                 "nof-items": 1337
    #             },
    #             "https://www.eskilstuna.se/sitemap1.xml.gz": {
    #                 "status": "ok",
    #                 "same-domain": true,
    #                 "https-only": true,
    #                 "has-duplicates": false,
    #                 "types": ["webpages"],
    #                 "nof-items": 1337
    #             }
    #         }
    #     },
    #     "security": {
    #         "status": "ok"

    #     }
    # }


    # item_types = {}
    # always_starts_with_https_scheme = True
    # always_uses_same_domain = True
    # for item_url in sitemap_items:
    #     item_type = 'webpage'

    #     if not item_url.lower().startswith('https://'):
    #         always_starts_with_https_scheme = False

    #     parsed_item_url = urlparse(item_url)
    #     if robots_domain != parsed_item_url.hostname:
    #         always_uses_same_domain = False

    #     tmp = os.path.splitext(parsed_item_url.path)[1].strip('.').lower()
    #     ext_len = len(tmp)
    #     if 2 <= ext_len >= 4:
    #         if tmp in KNOWN_EXTENSIONS:
    #             item_type = tmp
    #     elif parsed_item_url.path.startswith('/download/'):
    #         item_type = 'unknown-in-download'

    #     if item_type not in item_types:
    #         item_types[item_type] = []
    #     item_types[item_type].append(item_url)

    # item_type_keys = sorted(list(item_types.keys()))
    total_nof_items = len(sitemap_items)
    sitemap_items = list(set(sitemap_items))
    total_nof_items_no_duplicates = len(sitemap_items)

    if not result_dict['sitemap_use_https_only']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    1.0)
        sub_rating.set_standards(
                    1.0, local_translation("TEXT_SITEMAP_NOT_STARTING_WITH_HTTPS_SCHEME"))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, local_translation("TEXT_SITEMAP_STARTING_WITH_HTTPS_SCHEME"))
        rating += sub_rating

    if not result_dict['sitemap_use_same_domain']:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    1.0)
        sub_rating.set_standards(
                    1.0, local_translation("TEXT_SITEMAP_NOT_SAME_DOMAIN_AS_ROBOTS_TXT"))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, local_translation("TEXT_SITEMAP_SAME_DOMAIN_AS_ROBOTS_TXT"))
        rating += sub_rating

    if total_nof_items !=  total_nof_items_no_duplicates:
        ratio = total_nof_items_no_duplicates / total_nof_items
        duplicates_points = 3.0 * ratio
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    duplicates_points)
        sub_rating.set_standards(
                    duplicates_points, local_translation("TEXT_SITEMAP_INCLUDE_DUPLICATES"))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, local_translation("TEXT_SITEMAP_NO_DUPLICATES"))
        rating += sub_rating

    type_keys = result_dict['sitemap_types'].keys()
    if len(type_keys) > 1:
        webpages_points = 1.0
        if 'webpage' in type_keys:
            nof_webpages = result_dict['sitemap_types']['webpage']
            ratio = nof_webpages / total_nof_items
            webpages_points = 5.0 * ratio

        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    webpages_points)
        sub_rating.set_standards(
                    webpages_points,  local_translation("TEXT_SITEMAP_NOT_ONLY_WEBPAGES"))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, local_translation("TEXT_SITEMAP_ONLY_WEBPAGES"))
        rating += sub_rating

    # loop sitemaps and see if any single sitemap exsits amount
    for key in sitemaps.keys():
        if key == 'all':
            continue

        nof_items = len(sitemaps[key])

        if nof_items > 50_000:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(
                        1.0)
            sub_rating.set_standards(
                        1.0,  local_translation("TEXT_SITEMAP_TOO_LARGE"))
            rating += sub_rating
        else:
            sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
            sub_rating.set_overall(
                        5.0)
            sub_rating.set_standards(
                        5.0, local_translation("TEXT_SITEMAP_NOT_TOO_LARGE"))
            rating += sub_rating

    if total_nof_items == 0:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    1.0)
        sub_rating.set_standards(
                    1.0, local_translation("TEXT_SITEMAP_BROKEN"))
        rating += sub_rating

        result_dict['sitemap_check'] = f"'{sitemap_url}' seem to be broken"
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(
                    5.0)
        sub_rating.set_standards(
                    5.0, local_translation("TEXT_SITEMAP_IS_OK"))
        rating += sub_rating

        result_dict['sitemap_check'] = f"'{sitemap_url}' seem ok"
    return rating

def append_sitemap_data_to_result_dict(sitemap_items, result_dict):
    item_types = {}

    if 'sitemap_use_https_only' not in result_dict:
        result_dict['sitemap_use_https_only'] = True

    if 'sitemap_use_same_domain' not in result_dict:
        result_dict['sitemap_use_same_domain'] = True

    if 'sitemap_types' not in result_dict:
        result_dict['sitemap_types'] = {}


    robots_domain = get_domain(result_dict['robots.txt-location'])

    for item_url in sitemap_items:
        item_type = 'webpage'

        if not item_url.lower().startswith('https://'):
            result_dict['sitemap_use_https_only'] = False

        parsed_item_url = urlparse(item_url)
        if robots_domain != parsed_item_url.hostname:
            result_dict['sitemap_use_same_domain'] = False

        tmp = os.path.splitext(parsed_item_url.path)[1].strip('.').lower()
        ext_len = len(tmp)
        if 2 <= ext_len >= 4:
            if tmp in KNOWN_EXTENSIONS:
                item_type = tmp
        elif parsed_item_url.path.startswith('/download/'):
            item_type = 'unknown-in-download'

        if item_type not in item_types:
            item_types[item_type] = []
        item_types[item_type].append(item_url)

    keys = sorted(list(item_types.keys()))

    for key in keys:
        result_dict['sitemap_types'][key] = len(item_types[key])


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


def validate_feed(global_translation, local_translation, url):
    return_dict = {}
    feed = []
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)

    content = get_http_content(url, True, True)
    soup = BeautifulSoup(content, 'lxml')
    feed = soup.find_all(is_feed)

    if len(feed) == 0:
        rating.set_overall(4.5, local_translation("TEXT_RSS_FEED_MISSING"))
        return_dict['feed'] = 'not in meta'
        return_dict['num_feeds'] = len(feed)
    elif len(feed) > 0:
        rating.set_overall(5.0, local_translation("TEXT_RSS_FEED_FOUND"))
        return_dict['feed'] = 'found in meta'
        return_dict['num_feeds'] = len(feed)
        tmp_feed = []
        for single_feed in feed:
            tmp_feed.append(single_feed.get('href'))

        return_dict['feeds'] = tmp_feed

    return (rating, return_dict)


def validate_security_txt(global_translation, local_translation, parsed_url):
    # normal location for security.txt
    security_wellknown_url = parsed_url + '.well-known/security.txt'
    security_wellknown_content = get_http_content(
        security_wellknown_url, True)

    # Note: security.txt can also be placed in root if
    # for example technical reasons prohibit use of /.well-known/
    security_root_url = parsed_url + 'security.txt'
    security_root_content = get_http_content(security_root_url, True)

    if security_wellknown_content == '' and security_root_content == '':
        # Can't find security.txt (not giving us 200 as status code)
        rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        rating.set_overall(1.0)
        rating.set_standards(1.0, local_translation("TEXT_SECURITY_MISSING"))
        rating.set_integrity_and_security(1.0, local_translation("TEXT_SECURITY_MISSING"))

        return_dict = {}
        return_dict['security.txt'] = 'missing'
        return (rating, return_dict)

    security_wellknown_result = rate_securitytxt_content(
        security_wellknown_content, global_translation, local_translation)
    security_root_result = rate_securitytxt_content(
        security_root_content, global_translation, local_translation)

    security_wellknown_rating = security_wellknown_result[0]
    security_root_rating = security_root_result[0]

    if security_wellknown_rating.get_overall() == security_root_rating.get_overall():
        return security_wellknown_result

    if security_wellknown_rating.get_overall() > security_root_rating.get_overall():
        return security_wellknown_result
    return security_root_result


def rate_securitytxt_content(content, global_translation, local_translation):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    return_dict = {}
    if content is None or ('<html' in content.lower()):
        # Html (404 page?) content instead of expected content
        rating.set_overall(1.0)
        rating.set_standards(1.0, local_translation("TEXT_SECURITY_WRONG_CONTENT"))
        rating.set_integrity_and_security(
            1.0, local_translation("TEXT_SECURITY_WRONG_CONTENT"))
        return_dict['security.txt'] = 'wrong content'
    elif ('contact:' in content.lower() and 'expires:' in content.lower()):
        # Everything seems ok
        rating.set_overall(5.0)
        rating.set_standards(5.0, local_translation("TEXT_SECURITY_OK_CONTENT"))
        rating.set_integrity_and_security(
            5.0, local_translation("TEXT_SECURITY_OK_CONTENT"))
        return_dict['security.txt'] = 'ok'
    elif not 'contact:' in content.lower():
        # Missing required Contact
        rating.set_overall(2.5)
        rating.set_standards(2.5, local_translation(
            "TEXT_SECURITY_REQUIRED_CONTACT_MISSING"))
        rating.set_integrity_and_security(
            2.5, local_translation("TEXT_SECURITY_REQUIRED_CONTACT_MISSING"))
        return_dict['security.txt'] = 'required contact missing'
    elif not 'expires:' in content.lower():
        # Missing required Expires (added in version 10 of draft)
        rating.set_overall(2.5)
        rating.set_standards(2.5, local_translation(
            "TEXT_SECURITY_REQUIRED_EXPIRES_MISSING"))
        rating.set_integrity_and_security(
            4.0, local_translation("TEXT_SECURITY_REQUIRED_EXPIRES_MISSING"))
        return_dict['security.txt'] = 'required expires missing'
    else:
        rating.set_overall(1.0, local_translation("TEXT_SECURITY_WRONG_CONTENT"))

    return (rating, return_dict)
