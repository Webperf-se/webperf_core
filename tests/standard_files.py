# -*- coding: utf-8 -*-
import os
from urllib.parse import urlparse
from datetime import datetime
import re
from bs4 import BeautifulSoup
from helpers.models import Rating
from tests.utils import get_root_url,\
    get_translation, has_redirect,\
    get_http_content, flatten_issues_dict,\
    calculate_rating, get_domain
from engines.sitemap import read_sitemap
from helpers.setting_helper import get_config

# DEFAULTS
KNOWN_EXTENSIONS = ['bmp', 'css', 'doc', 'docx', 'dot', 'eot', 'exe', 'git',
                    'ico', 'ics', 'jpeg', 'jpg', 'js','json', 'md', 'mov', 'mp3',
                    'mp4', 'pdf', 'png', 'ppt', 'pptx', 'pub', 'svg', 'tif',
                    'txt', 'unknown-in-download', 'webp', 'wmv', 'xls', 'xlsx', 'xml', 'zip']

ALL_RULES = {
    'no-robots-txt': {
        'severity': 'error',
        'category': 'standard',
    },
    'no-sitemap-in-robots-txt': {
        'severity': 'error',
        'category': 'standard',
    },
    'no-valid-sitemap-found': {
        'severity': 'error',
        'category': 'standard',
    },
    'no-same-domain-sitemap': {
        'severity': 'warning',
        'category': 'standard',
    },
    'no-https-sitemap': {
        'severity': 'error',
        'category': 'security',
    },
    'no-duplicates-sitemap': {
        'severity': 'warning',
        'category': 'standard',
    },
    'no-unknown-types-sitemap': {
        'severity': 'warning',
        'category': 'standard',
    },
    'invalid-sitemap-too-large': {
        'severity': 'warning',
        'category': 'standard',
    },
    'no-items-sitemap': {
        'severity': 'warning',
        'category': 'standard',
    },
    'no-rss-feed': {
        'severity': 'warning',
        'category': 'standard',
    },
    'no-security-txt': {
        'severity': 'error',
        'category': 'security',
    },
    'invalid-security-txt': {
        'severity': 'error',
        'category': 'security',
    },
    'no-security-txt-contact': {
        'severity': 'warning',
        'category': 'security',
    },
    'no-security-txt-expires': {
        'severity': 'warning',
        'category': 'security',
    },
    'no-network': {
        'severity': 'warning',
        'category': 'technical',
    }
}

def run_test(global_translation, url):
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    result_dict = {
        'url': url,
        'root_url': get_root_url(url),
        'groups': {}
    }

    domain = get_domain(url)
    result_dict['groups'][domain] = {
            'issues': {}
        }

    # robots.txt
    add_robots_issues(result_dict)

    # sitemap.xml
    add_sitemaps_issues(
        result_dict)

    # rss feed
    add_feed_issues(result_dict)

    # security.txt
    add_security_txt_issues(result_dict)

    addResolvedIssues(url, domain, result_dict)

    if 'failed' in result_dict:
        error_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        error_rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        addIssue(
            result_dict,
            'no-network',
            global_translation('TEXT_SITE_UNAVAILABLE'),
            result_dict['url'])

        result_dict['groups'][domain]['issues'] = flatten_issues_dict(result_dict['groups'][domain]['issues'])

        return (error_rating, {'failed': True })

    result_dict['groups'][domain]['issues'] = flatten_issues_dict(result_dict['groups'][domain]['issues'])

    tmp = result_dict['groups']

    result_dict = {
        "groups": tmp
    }

    rating = calculate_rating(global_translation, rating, result_dict)

    return (rating, result_dict)

def addResolvedIssues(url, domain, result_dict):
    for rule_id, rule in ALL_RULES.items():
        if rule_id == 'no-network':
            continue
        if rule_id not in result_dict['groups'][domain]['issues']:
            addResolvedIssue(result_dict, rule_id, url)
            result_dict['groups'][domain]['issues'][rule_id]['severity'] = 'resolved'
            result_dict['groups'][domain]['issues'][rule_id]['category'] = rule['category']

def addIssue(result_dict, rule_id, url):
    domain = get_domain(result_dict['url'])
    if rule_id not in result_dict['groups'][domain]['issues']:
        result_dict['groups'][domain]['issues'][rule_id] = {
            'test': 'standard-files',
            'rule': rule_id,
            'category': ALL_RULES[rule_id]['category'],
            'severity': ALL_RULES[rule_id]['severity'],
            'subIssues': [
                {
                    'url': url,
                    'rule': rule_id,
                    'category': ALL_RULES[rule_id]['category'],
                    'severity': ALL_RULES[rule_id]['severity']
                }
            ]
        }
    else:
        result_dict['groups'][domain]['issues'][rule_id]['subIssues'].append({
            'url': url,
            'rule': rule_id,
            'category': ALL_RULES[rule_id]['category'],
            'severity': ALL_RULES[rule_id]['severity']
        })


def addResolvedIssue(result_dict, rule_id, url):
    domain = get_domain(result_dict['url'])
    result_dict['groups'][domain]['issues'][rule_id] = {
        'test': 'standard-files',
        'rule': rule_id,
        'category': ALL_RULES[rule_id]['category'],
        'severity': 'resolved',
        'subIssues': []
    }


def add_robots_issues(result_dict):
    robots_dict = {
        'url': result_dict['root_url'] + 'robots.txt'
    }

    (is_redirected, url_destination, _) = has_redirect(robots_dict['url'])
    if is_redirected:
        robots_dict['url'] = url_destination

    robots_dict['content'] = get_http_content(robots_dict['url'], True)

    if robots_dict['content'] is None or '</html>' in robots_dict['content'].lower() or \
          ('user-agent' not in robots_dict['content'].lower() \
           and 'disallow' not in robots_dict['content'].lower() \
           and 'allow' not in robots_dict['content'].lower()):
        robots_dict['status'] = 'missing content'
        robots_dict['content'] = None
        addIssue(
            result_dict,
            'no-robots-txt',
            robots_dict['url'])

    else:
        robots_dict['status'] = 'ok'

    result_dict['robots'] = robots_dict

def add_sitemaps_issues(result_dict):
    sitemaps_dict = {
        'nof_sitemaps': 0,
        'sitemap_urls_in_robots': [],
        'sitemaps': {},
        'use_https_only': True,
        'use_same_domain': True,
        'known_types': {},
        'has_duplicates_items': False,
        'is_duplicate': False,
        'nof_items': 0,
        'nof_items_no_duplicates': 0
    }

    if get_config('general.review.details'):
        sitemaps_dict['known_types_details'] = {}

    if result_dict['robots']['status'] != 'ok' or\
            'sitemap:' not in result_dict['robots']['content'].lower():
        sitemaps_dict['status'] = 'not in robots.txt'
        result_dict['sitemap'] = sitemaps_dict

        addIssue(
            result_dict,
            'no-sitemap-in-robots-txt',
            result_dict['url'])
        return

    regex = r"^sitemap\:(?P<url>[^\n]+)"
    matches = re.finditer(regex, result_dict['robots']['content'], re.MULTILINE | re.IGNORECASE)
    for _, match in enumerate(matches, start=1):
        sitemap_url = match.group('url').strip()
        sitemaps_dict["sitemap_urls_in_robots"].append(sitemap_url)

    sitemaps_dict["nof_sitemaps"] = len(sitemaps_dict["sitemap_urls_in_robots"])

    # NOTE: https://internetverkstan.se/ has styled sitemap

    if sitemaps_dict["nof_sitemaps"] == 0:
        result_dict['sitemap'] = sitemaps_dict
        addIssue(
            result_dict,
            'no-valid-sitemap-found',
            result_dict['url'])
        return

    robots_domain = get_domain(result_dict['robots']['url'])
    for sitemap_url in sitemaps_dict["sitemap_urls_in_robots"]:
        validate_sitemap(
            sitemap_url,
            sitemaps_dict,
            robots_domain)
    add_sitemap_issues(
        result_dict,
        sitemaps_dict)

    result_dict['sitemap'] = sitemaps_dict

def validate_sitemap(sitemap_url,
                     sitemaps_dict,
                     robots_domain):
    sitemaps = read_sitemap(sitemap_url, -1, -1, False)

    for key, items in sitemaps.items():
        if key == 'all':
            continue
        if key == 'sitemapindex':
            if "sitemapindexes" not in sitemaps_dict:
                sitemaps_dict["sitemapindexes"] = []
            if key not in sitemaps_dict["sitemapindexes"]:
                sitemaps_dict["sitemapindexes"].extend(items)

            continue

        if key not in sitemaps_dict["sitemaps"]:
            sitemap_dict = create_sitemap_dict(items, robots_domain)
            sitemaps_dict["sitemaps"][key] = sitemap_dict

            if not sitemap_dict['use_https_only']:
                sitemaps_dict['use_https_only'] = False
            if not sitemap_dict['use_same_domain']:
                sitemaps_dict['use_same_domain'] = False
            if sitemap_dict['has_duplicates_items']:
                sitemaps_dict['has_duplicates_items'] = True
            if sitemap_dict['is_duplicate']:
                sitemaps_dict['is_duplicate'] = True
            sitemaps_dict['known_types'].update(sitemap_dict['known_types'])
            if get_config('general.review.details') and 'known_types_details' in sitemap_dict:
                    sitemaps_dict['known_types_details'].update(sitemap_dict['known_types_details'])

            sitemaps_dict['nof_items'] += sitemap_dict['nof_items']
            sitemaps_dict['nof_items_no_duplicates'] += sitemap_dict['nof_items_no_duplicates']
        else:
            sitemaps_dict["sitemaps"][key]['is_duplicate'] = True
            sitemaps_dict['is_duplicate'] = True

    cleanup_sites_dict(sitemaps_dict)

def cleanup_sites_dict(sitemaps_dict):
    sitemaps_dict["sitemapindexes"] = list(set(sitemaps_dict["sitemapindexes"]))
    for sitemapindex in sitemaps_dict["sitemapindexes"]:
        if sitemapindex in sitemaps_dict["sitemaps"]:
            del sitemaps_dict["sitemaps"][sitemapindex]


def add_sitemap_issues(result_dict, sitemaps_dict):
    total_nof_items = sitemaps_dict['nof_items']
    total_nof_items_no_duplicates = sitemaps_dict['nof_items_no_duplicates']
    sitemaps = sitemaps_dict['sitemaps']

    if total_nof_items > 0:
        add_sitemap_use_https_only_issues(
            result_dict,
            sitemaps_dict)
        add_sitemap_use_same_domain_issues(
            result_dict,
            sitemaps_dict)
        add_sitemap_use_of_duplicates_issues(result_dict,
                                    total_nof_items,
                                    total_nof_items_no_duplicates)
        add_sitemap_use_known_types_issues(result_dict,
                                    sitemaps_dict,
                                    total_nof_items)

        sitemaps_is_duplicated = sitemaps_dict['is_duplicate']
        if sitemaps_is_duplicated:
            addIssue(
                result_dict,
                'no-duplicates-sitemap',
                result_dict['url'])

    # loop sitemaps and see if any single sitemap exsits amount
    for _, sitemap_info in sitemaps.items():
        nof_items = sitemap_info['nof_items']

        if nof_items > 50_000:
            addIssue(
                result_dict,
                'invalid-sitemap-too-large',
                result_dict['url'])
        elif nof_items == 0:
            addIssue(
                result_dict,
                'no-items-sitemap',
                result_dict['url'])

    add_sitemap_any_items_issues(sitemaps_dict,
                           result_dict,
                           total_nof_items)

def add_sitemap_any_items_issues(sitemaps_dict,
                           result_dict,
                           total_nof_items):
    if total_nof_items == 0:
        sitemaps_dict['status'] = "sitemap(s) seem to be broken"
        addIssue(
                result_dict,
                'no-items-sitemap',
                result_dict['url'])
        return

    sitemaps_dict['status'] = "sitemap(s) seem ok"

def add_sitemap_use_known_types_issues(result_dict,
                                 sitemaps_dict,
                                 total_nof_items):
    if total_nof_items == 0:
        return

    type_keys = sitemaps_dict['known_types'].keys()
    if len(type_keys) > 1:
        addIssue(
                result_dict,
                'no-unknown-types-sitemap',
                result_dict['url'])

def add_sitemap_use_of_duplicates_issues(result_dict,
                                   total_nof_items,
                                   total_nof_items_no_duplicates):
    if total_nof_items !=  total_nof_items_no_duplicates:
        addIssue(
                result_dict,
                'no-duplicates-sitemap',
                result_dict['url'])

def add_sitemap_use_same_domain_issues(result_dict, sitemaps_dict):
    if not sitemaps_dict['use_same_domain']:
        addIssue(
                result_dict,
                'no-same-domain-sitemap',
                result_dict['url'])

def add_sitemap_use_https_only_issues(result_dict, sitemaps_dict):
    if not sitemaps_dict['use_https_only']:
        addIssue(
                result_dict,
                'no-https-sitemap',
                result_dict['url'])

def create_sitemap_dict(sitemap_items, robots_domain):
    nof_items = len(sitemap_items)
    nof_no_duplicates = len(list(set(sitemap_items)))

    sitemap_dict = {
        'use_https_only': True,
        'use_same_domain': True,
        'known_types': {},
        'has_duplicates_items': nof_items > nof_no_duplicates,
        'is_duplicate': False,
        'nof_items': nof_items,
        'nof_items_no_duplicates': nof_no_duplicates
    }

    if get_config('general.review.details'):
        sitemap_dict['known_types_details'] = {}

    item_types = {}

    for item_url in sitemap_items:
        item_type = 'webpage'

        if not item_url.lower().startswith('https://'):
            sitemap_dict['use_https_only'] = False

        parsed_item_url = urlparse(item_url)
        if robots_domain != parsed_item_url.hostname:
            sitemap_dict['use_same_domain'] = False

        tmp = os.path.splitext(parsed_item_url.path)[1].strip('.').lower()
        ext_len = len(tmp)
        if 2 <= ext_len <= 4:
            if tmp in KNOWN_EXTENSIONS:
                item_type = tmp
        elif parsed_item_url.path.startswith('/download/'):
            item_type = 'unknown-in-download'

        if item_type not in item_types:
            item_types[item_type] = []
        item_types[item_type].append(item_url)

    keys = sorted(list(item_types.keys()))

    for key in keys:
        sitemap_dict['known_types'][key] = len(item_types[key])
        if get_config('general.review.details'):
            sitemap_dict['known_types_details'][key] = item_types[key]

    return sitemap_dict


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


def add_feed_issues(result_dict):
    feed_dict = {
        'nof_feeds': 0,
        'feeds': []
    }
    content = get_http_content(result_dict['url'], True, True)
    if content == '':
        result_dict['failed'] = True
    soup = BeautifulSoup(content, 'lxml')
    feeds = soup.find_all(is_feed)

    feed_dict['nof_feeds'] = len(feeds)
    if feed_dict['nof_feeds'] == 0:
        feed_dict['status'] = 'not in meta'
        addIssue(
                result_dict,
                'no-rss-feed',
                result_dict['url'])
    elif feed_dict['nof_feeds'] > 0:
        feed_dict['status'] = 'found in meta'
        for single_feed in feeds:
            feed_dict['feeds'].append(single_feed.get('href'))

    result_dict['feeds'] = feed_dict

def add_security_txt_issues(result_dict):
    root_url = result_dict['root_url']
    security_dict = {
        'txts': {}
    }

    # First, check .well-known/security.txt
    security_wellknown_url = root_url + '.well-known/security.txt'
    security_wellknown_content = get_http_content(security_wellknown_url, True)
    security_wellknown_result = validate_securitytxt_content(
        result_dict,
        security_wellknown_content,
        security_wellknown_url
    )
    security_dict['txts'][security_wellknown_url] = security_wellknown_result

    # Only check root location if well-known is missing or wrong content
    check_root = (security_wellknown_result['status'] == 'missing' or security_wellknown_result['status'] == 'wrong content')
    if check_root:
        security_root_url = root_url + 'security.txt'
        security_root_content = get_http_content(security_root_url, True)
        security_root_result = validate_securitytxt_content(
            result_dict,
            security_root_content,
            security_root_url
        )
        security_dict['txts'][security_root_url] = security_root_result

    # Now, pass if either location is ok
    status_ok = False
    for txt in security_dict['txts'].values():
        if txt['status'] == 'ok':
            status_ok = True
            break

    if status_ok:
        security_dict['status'] = 'ok'
        # Remove any previously added issues for security.txt for this result_dict
        domain = get_domain(result_dict['url'])
        issues = result_dict['groups'][domain]['issues']
        for rule_id in ['no-security-txt', 'invalid-security-txt', 'no-security-txt-contact', 'no-security-txt-expires', 'no-security-txt-expires']:
            if rule_id in issues:
                # Mark as resolved
                issues[rule_id]['severity'] = 'resolved'
                issues[rule_id]['subIssues'] = []                
    else:
        # Compose issues for both locations if neither is ok
        for url, txt in security_dict['txts'].items():
            if txt['status'] == 'missing':
                addIssue(result_dict, 'no-security-txt', url)
                addIssue(result_dict, 'invalid-security-txt', url)
                addIssue(result_dict, 'no-security-txt-contact', url)
                addIssue(result_dict, 'no-security-txt-expires', url)
            elif txt['status'] == 'wrong content':
                addIssue(result_dict, 'invalid-security-txt', url)
                addIssue(result_dict, 'no-security-txt-contact', url)
                addIssue(result_dict, 'no-security-txt-expires', url)
            elif txt['status'] == 'required contact missing':
                addIssue(result_dict, 'no-security-txt-contact', url)
            elif txt['status'] == 'required expires missing':
                addIssue(result_dict, 'no-security-txt-expires', url)
            elif txt['status'] == 'wrong content, no contact or expires':
                addIssue(
                        result_dict,
                        'no-security-txt-expires',
                        url)
                addIssue(
                        result_dict,
                        'no-security-txt-contact',
                        url)
    result_dict['security'] = security_dict

def validate_securitytxt_content(result_dict, content, url):
    security_dict = {}
    if content is None or content == '' or ('<html' in content.lower()):
        # Html (404 page?) content instead of expected content
        security_dict['severity'] = ALL_RULES['invalid-security-txt']['severity']
        security_dict['status'] = 'wrong content'
        addIssue(
                result_dict,
                'invalid-security-txt',
                url)
    elif ('contact:' in content.lower() and 'expires:' in content.lower()):
        # Everything seems ok
        security_dict['severity'] = 'resolved'
        security_dict['status'] = 'ok'
    elif not 'contact:' in content.lower():
        # Missing required Contact
        security_dict['severity'] = ALL_RULES['no-security-txt-contact']['severity']
        security_dict['status'] = 'required contact missing'
        addIssue(
                result_dict,
                'no-security-txt-contact',
                url)
    elif not 'expires:' in content.lower():
        # Missing required Expires (added in version 10 of draft)
        security_dict['severity'] = ALL_RULES['no-security-txt-expires']['severity']
        security_dict['status'] = 'required expires missing'
        addIssue(
                result_dict,
                'no-security-txt-expires',
                url)
    else:
        security_dict['severity'] = ALL_RULES['no-security-txt-expires']['severity']
        security_dict['status'] = 'wrong content, no contact or expires'
        addIssue(
                result_dict,
                'no-security-txt-expires',
                url)
        addIssue(
                result_dict,
                'no-security-txt-contact',
                url)

    return security_dict
