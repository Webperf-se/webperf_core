# -*- coding: utf-8 -*-
from functools import cmp_to_key
from PIL.ExifTags import TAGS, GPSTAGS
from PIL import Image
import hashlib
from pathlib import Path
import shutil
from models import Rating
import os
import json
import config
import re
# https://docs.python.org/3/library/urllib.parse.html
from urllib.parse import urlparse
from tests.utils import *
from tests.sitespeed_base import get_result
import datetime
import packaging.version
import gettext

_ = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
review_show_improvements_only = config.review_show_improvements_only
sitespeed_use_docker = config.sitespeed_use_docker
try:
    use_cache = config.cache_when_possible
    cache_time_delta = config.cache_time_delta
except:
    # If cache_when_possible variable is not set in config.py this will be the default
    use_cache = False
    cache_time_delta = timedelta(hours=1)
try:
    use_stealth = config.software_use_stealth
except:
    # If software_use_stealth variable is not set in config.py this will be the default
    use_stealth = True
try:
    use_detailed_report = config.software_use_detailed_report
except:
    # If software_use_detailed_report variable is not set in config.py this will be the default
    use_detailed_report = False

# Debug flags for every category here, this so we can print out raw values (so we can add more allowed once)
raw_data = {
    'urls': {
        'use': False
    },
    'headers': {
        'use': False
    },
    'contents': {
        'use': False
    },
    'mime-types': {
        'use': False
    },
    'css-comments': {
        'use': False
    },
    'js-comments':  {
        'use': False
    },
    'source-mapping-url':  {
        'use': False
        # unsure of this one.. it could be every single js..
        # Is this working good enough already?
    },
    'test': {
        'use': False
    }
}


def get_rating_from_sitespeed(url, _local, _):
    # We don't need extra iterations for what we are using it for
    sitespeed_iterations = 1
    sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --plugins.remove html --plugins.remove metrics --browsertime.screenshot false --screenshot false --screenshotLCP false --browsertime.screenshotLCP false --chrome.cdp.performance false --browsertime.chrome.timeline false --videoParams.createFilmstrip false --visualMetrics false --visualMetricsPerceptual false --visualMetricsContentful false --browsertime.headless true --browsertime.chrome.includeResponseBodies all --utc true --browsertime.chrome.args ignore-certificate-errors -n {0}'.format(
        sitespeed_iterations)
    if 'nt' not in os.name:
        sitespeed_arg += ' --xvfb'

    (result_folder_name, filename) = get_result(
        url, sitespeed_use_docker, sitespeed_arg)

    o = urlparse(url)
    origin_domain = o.hostname

    rules = get_rules()
    data = identify_software(filename, origin_domain, rules)
    # [
        # {
        #     "domain": "<domain>",
        #     "url": "<url>",
        #     "method": "content",
        #     "precision": <precision>,
        #     "category": "<category-name>",
        #     "name": "<item-name>",
        #     "version": <version>,
        #     "security": [],
        #     *"mime-type": "mime-type"
        # }
    # ]
    data = enrich_data(data, origin_domain, result_folder_name, rules)

    rating = Rating(_, review_show_improvements_only)
    result = {}
    result = convert_item_to_domain_data(data)

    # nice_raw = json.dumps(result, indent=2)
    # print('DEBUG 3', nice_raw)
    # result = {
    #   "<category-name>": {
    #       "<item-name>": {
    #           "<version>": {
    #               "<item-name>": "",
    #               "<precision>": <precision>
    #           }
    #       }
    #   }
    # }
    texts = ''
    texts = sum_overall_software_used(_local, _, result)

    # result2 = convert_item_to_software_data(data, url)
    rating += rate_software_security_result(_local, _, result, url)

    # result.update(result2)

    rating.overall_review = '{0}\r\n'.format('\r\n'.join(texts)).replace('GOV-IGNORE', '').strip('\r\n\t ')
    rating.integrity_and_security_review = rating.integrity_and_security_review.replace('GOV-IGNORE', '').strip('\r\n\t ')

    if not use_cache:
        shutil.rmtree(result_folder_name)

    return (rating, result)

def cleanup_domain_data(data):
    # result = {
    #   "<category-name>": {
    #       "<item-name>": {
    #           "<version>": {
    #               "<item-name>": "",
    #               "<precision>": <precision>
    #           }
    #       }
    #   }
    # }

    # removes matches with unknown version if we have a match for same software with version
    for category_name in data.keys():
        if category_name == 'issues':
            continue
        for software_name in data[category_name].keys():
            if len(data[category_name][software_name].keys()) > 1 and '?' in data[category_name][software_name]:
                del data[category_name][software_name]['?']

    if len(data['issues'])> 0:
        issues = list(set(data['issues']))
        issues = sorted(issues, key=cmp_to_key(sort_issues), reverse=True)
        data['issues'] = issues

def sort_issues(item1, item2):
    if item1.startswith('CVE-') and not item2.startswith('CVE-'):
        return 1
    elif item2.startswith('CVE-') and not item1.startswith('CVE-'):
        return -1
    
    if item1 < item2:
        return -1
    elif item1 < item2:
        return 1
    else:
        return 0

def create_detailed_review(_local, msg_type, points, software_name, software_versions, sources, cve_name=None, references=None):
    # TODO: Use points from arguments into create_detailed_review and replace it in text (so it is easier to change rating)
    # TODO: match on issue names directly
    msg = list()
    if msg_type == 'cve':
        # TODO: use startswith for 'CVE-'
        msg.append(_local('TEXT_DETAILED_REVIEW_CVE').format(cve_name))
    elif msg_type == 'behind100':
        msg.append(_local('TEXT_DETAILED_REVIEW_BEHIND100').format(cve_name))
    elif msg_type == 'behind75':
        msg.append(_local('TEXT_DETAILED_REVIEW_BEHIND075').format(cve_name))
    elif msg_type == 'behind50':
        msg.append(_local('TEXT_DETAILED_REVIEW_BEHIND050').format(cve_name))
    elif msg_type == 'behind25':
        msg.append(_local('TEXT_DETAILED_REVIEW_BEHIND025').format(cve_name))
    elif msg_type == 'behind10':
        msg.append(_local('TEXT_DETAILED_REVIEW_BEHIND010').format(cve_name))
    elif msg_type == 'latest-but-leaking-name-and-version':
        msg.append(_local('TEXT_DETAILED_REVIEW_LATEST_LEAKING_NAME_AND_VERSION').format(cve_name))
    elif msg_type == 'unknown-but-leaking-name-and-version':
        msg.append(_local('TEXT_DETAILED_REVIEW_UNKNOWN_LEAKING_NAME_AND_VERSION').format(cve_name))
    elif msg_type == 'leaking-name':
        msg.append(_local('TEXT_DETAILED_REVIEW_LEAKING_NAME').format(cve_name))
    elif msg_type == 'behind1':
        msg.append(_local('TEXT_DETAILED_REVIEW_BEHIND001').format(cve_name))
    elif msg_type == 'multiple-versions':
        msg.append(_local('TEXT_DETAILED_REVIEW_MULTIPLE_VERSIONS').format(cve_name))
    elif msg_type == 'ARCHIVED-SOURCE':
        msg.append(_local('TEXT_DETAILED_REVIEW_ARCHIVED_SOURCE').format(cve_name))
    if 'GOV-IGNORE' in msg:
        return ''
    
    if references != None and len(references) > 0:
        msg.append(_local('TEXT_DETAILED_REVIEW_REFERENCES'))

        for reference in references:
            msg.append('- {0}'.format(reference))
        msg.append('')

    if len(software_versions) > 0:
        msg.append(_local('TEXT_DETAILED_REVIEW_DETECTED_VERSIONS'))

        for version in software_versions:
            msg.append('- {0} {1}'.format(software_name, version))
        msg.append('')

    if len(sources) > 0:
        msg.append(_local('TEXT_DETAILED_REVIEW_DETECTED_RESOURCES'))

        source_index = 0
        for source in sources:
            if source_index > 5:
                msg.append(_local('TEXT_DETAILED_REVIEW_MORE_THEN_5_SOURCES'))
                break
            msg.append('- {0}'.format(source))
            source_index += 1
        msg.append('')
        msg.append('')

    return '\r\n'.join(msg).replace('#POINTS#', "{0:.2f}".format(points))


def update_rating_collection(rating, ratings):
    points_key = "key_{0:.2f}".format(rating.get_integrity_and_security())
    if points_key not in ratings:
        ratings[points_key] = list()
    ratings[points_key].append(rating)
    return ratings


def rate_software_security_result(_local, _, result, url):
    rating = Rating(_, review_show_improvements_only)


    has_cve_issues = False
    has_behind_issues = False
    has_archived_source_issues = False
    # has_multiple_versions_issues = False

    for issue_type in result['issues']:
        if issue_type.startswith('CVE-'):
            has_cve_issues = True
            points = 1.0
            sub_rating = Rating(_, review_show_improvements_only)
            sub_rating.set_overall(points)
            if use_detailed_report:
                sub_rating.set_integrity_and_security(points, '.')
                # sub_rating.integrity_and_security_review = text
            else:
                sub_rating.set_integrity_and_security(points)
            rating += sub_rating
        elif issue_type.startswith('BEHIND'):
            has_behind_issues = True
            points = 5.0
            if issue_type == 'BEHIND100':
                points = 2.0
            elif issue_type == 'BEHIND075':
                points = 2.25
            elif issue_type == 'BEHIND050':
                points = 2.5
            elif issue_type == 'BEHIND025':
                points = 2.75
            elif issue_type == 'BEHIND010':
                points = 3.0
            elif issue_type == 'BEHIND001':
                points = 4.9
            sub_rating = Rating(_, review_show_improvements_only)
            sub_rating.set_overall(points)
            if use_detailed_report:
                sub_rating.set_integrity_and_security(points, '.')
                # sub_rating.integrity_and_security_review = text
            else:
                sub_rating.set_integrity_and_security(points)
            rating += sub_rating
        elif issue_type.startswith('ARCHIVED-SOURCE'):
            has_archived_source_issues = True
        # elif issue_type.startswith('MULTIPLE-VERSIONS'):
        #     has_multiple_versions_issues = True

    if not has_cve_issues:
        points = 5.0
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(points)
        if use_detailed_report:
            sub_rating.set_integrity_and_security(points, '.')
            # sub_rating.integrity_and_security_review = text
        else:
            sub_rating.set_integrity_and_security(points)
        rating += sub_rating

    if not has_behind_issues:
        points = 5.0
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(points)
        if use_detailed_report:
            sub_rating.set_integrity_and_security(points, '.')
            # sub_rating.integrity_and_security_review = text
        else:
            sub_rating.set_integrity_and_security(points)
        rating += sub_rating

    if not has_archived_source_issues:
        points = 5.0
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(points)
        if use_detailed_report:
            sub_rating.set_integrity_and_security(points, '.')
            # sub_rating.integrity_and_security_review = text
        else:
            sub_rating.set_integrity_and_security(points)
        rating += sub_rating

    if not use_detailed_report:
        test = 1
    else:
        test = 2

    return rating

    # ratings = {}

    # categories = ['cms', 'webserver', 'os',
    #               'analytics',
    #               'js',
    #               'img', 'img.software', 'img.os', 'img.device', 'video']
    # for category in categories:
    #     if category in result:
    #         for software_name in result[category]:
    #             info = result[category][software_name]
    #             if 'issues' in info:
    #                 for issue in info['issues']:
    #                     points = 1.0
    #                     # if 'severity' in vuln:
    #                     #     if 'HIGH' in vuln['severity']:
    #                     #         points = 1.2
    #                     #     elif 'MODERATE' in vuln['severity']:
    #                     #         points = 1.5
    #                     vuln_versions = list()
    #                     # vuln_versions.append(vuln['version'])
    #                     # v_sources_key = 'v-{0}-sources'.format(
    #                     #     vuln['version'])

    #                     # if v_sources_key not in info:
    #                     #     v_sources_key = 'sources'
    #                     # vuln_sources = info[v_sources_key]
    #                     vuln_sources = list()

    #                     text = create_detailed_review(_local,
    #                         'cve', points, software_name, vuln_versions, vuln_sources, issue, list()) # vuln['references']
    #                     sub_rating = Rating(_, review_show_improvements_only)
    #                     sub_rating.set_overall(points)
    #                     if use_detailed_report:
    #                         sub_rating.set_integrity_and_security(points, '.')
    #                         sub_rating.integrity_and_security_review = text
    #                     else:
    #                         sub_rating.set_integrity_and_security(points)
    #                     ratings = update_rating_collection(sub_rating, ratings)

    #             if category != 'js' and 'nof-newer-versions' in info and info['nof-newer-versions'] == 0:
    #                 points = 4.5
    #                 text = create_detailed_review(_local,
    #                     'latest-but-leaking-name-and-version', points, software_name, info['versions'], info['sources'])
    #                 sub_rating = Rating(_, review_show_improvements_only)
    #                 sub_rating.set_overall(points)
    #                 if use_detailed_report:
    #                     sub_rating.set_integrity_and_security(points, '.')
    #                     sub_rating.integrity_and_security_review = text
    #                 else:
    #                     sub_rating.set_integrity_and_security(points)
    #                 ratings = update_rating_collection(sub_rating, ratings)
    #             elif category != 'js':
    #                 points = 4.0
    #                 text = create_detailed_review(_local,
    #                     'unknown-but-leaking-name-and-version', points, software_name, info['versions'], info['sources'])
    #                 sub_rating = Rating(_, review_show_improvements_only)
    #                 sub_rating.set_overall(points)
    #                 if use_detailed_report:
    #                     sub_rating.set_integrity_and_security(points, '.')
    #                     sub_rating.integrity_and_security_review = text
    #                 else:
    #                     sub_rating.set_integrity_and_security(points)
    #                 ratings = update_rating_collection(sub_rating, ratings)

    #             if 'nof-newer-versions' in info and info['nof-newer-versions'] > 0:
    #                 for version in info['versions']:
    #                     v_newer_key = 'v-{0}-nof-newer-versions'.format(
    #                         version)
    #                     v_sources_key = 'v-{0}-sources'.format(version)

    #                     # TODO: FAIL SAFE, we have identified multiple version of same software for the same request, should not be possible...
    #                     if v_newer_key not in info:
    #                         v_newer_key = 'nof-newer-versions'

    #                     if info[v_newer_key] == 0:
    #                         continue

    #                     if v_sources_key not in info:
    #                         v_sources_key = 'sources'

    #                     tmp_versions = list()
    #                     tmp_versions.append(version)

    #                     points = -1
    #                     text = ''
    #                     if info[v_newer_key] >= 100:
    #                         points = 2.0
    #                         text = create_detailed_review(_local,
    #                             'behind100', points, software_name, tmp_versions, info[v_sources_key])
    #                     elif info[v_newer_key] >= 75:
    #                         points = 2.25
    #                         text = create_detailed_review(_local,
    #                             'behind75', points, software_name, tmp_versions, info[v_sources_key])
    #                     elif info[v_newer_key] >= 50:
    #                         points = 2.5
    #                         text = create_detailed_review(_local,
    #                             'behind50', points, software_name, tmp_versions, info[v_sources_key])
    #                     elif info[v_newer_key] >= 25:
    #                         points = 2.75
    #                         text = create_detailed_review(_local,
    #                             'behind25', points, software_name, tmp_versions, info[v_sources_key])
    #                     elif info[v_newer_key] >= 10:
    #                         points = 3.0
    #                         text = create_detailed_review(_local,
    #                             'behind10', points, software_name, tmp_versions, info[v_sources_key])
    #                     elif info[v_newer_key] >= 1:
    #                         points = 4.9
    #                         text = create_detailed_review(_local,
    #                             'behind1', points, software_name, tmp_versions, info[v_sources_key])

    #                     sub_rating = Rating(_, review_show_improvements_only)
    #                     sub_rating.set_overall(points)
    #                     if use_detailed_report:
    #                         sub_rating.set_integrity_and_security(points, '.')
    #                         sub_rating.integrity_and_security_review = text
    #                     else:
    #                         sub_rating.set_integrity_and_security(points)
    #                     ratings = update_rating_collection(sub_rating, ratings)

    #             if len(info['versions']) > 1:
    #                 points = 4.1
    #                 text = create_detailed_review(_local,
    #                     'multiple-versions', points, software_name, info['versions'], info['sources'])
    #                 sub_rating = Rating(_, review_show_improvements_only)
    #                 sub_rating.set_overall(points)
    #                 if use_detailed_report:
    #                     sub_rating.set_integrity_and_security(points, '.')
    #                     sub_rating.integrity_and_security_review = text
    #                 else:
    #                     sub_rating.set_integrity_and_security(points)
    #                 ratings = update_rating_collection(sub_rating, ratings)

    # sorted_keys = list()
    # for points_key in ratings.keys():
    #     sorted_keys.append(points_key)

    # sorted_keys.sort()

    # for points_key in sorted_keys:
    #     for sub_rating in ratings[points_key]:
    #         rating += sub_rating

    # if rating.get_overall() == -1:
    #     rating.set_overall(5.0)
    #     rating.set_integrity_and_security(5.0)
    # elif not use_detailed_report:
    #     text = '{0}'.format(_local('UPDATE_AVAILABLE'))
    #     tmp_rating = Rating(_, review_show_improvements_only)
    #     tmp_rating.set_integrity_and_security(
    #         rating.get_integrity_and_security(), text)

    #     rating.integrity_and_security_review = tmp_rating.integrity_and_security_review

    # return rating


def sum_overall_software_used(_local, _, result):
    texts = list()

    categories = ['cms', 'webserver', 'os',
                  'analytics', 'tech', 'license', 'meta',
                  'js', 'css',
                  'lang', 'img', 'img.software', 'img.os', 'img.device', 'video']

    for category in categories:
        if category in result:
            texts.append(_local('TEXT_USED_{0}'.format(
                category.upper())).format(', '.join(result[category].keys())))

    return texts


def convert_item_to_software_data(data, url):
    result = {
        'called_url': url
    }

    for item in data:
        for match in item['matches']:
            category = match['category']

            if 'js' not in category and 'cms' not in category and 'webserver' not in category and 'os' not in category:
                continue

            if category not in result:
                result[category] = {}

            name = match['name']
            if name == '?':
                continue
            version = match['version']
            if 'webserver' != category and version == None:
                continue

            precision = match['precision']
            if precision < 0.3:
                continue

            if name not in result[category]:
                result[category][name] = {
                    'versions': [],
                    'sources': [],
                    'issues': []
                }

            if 'issues' in match and len(match['issues']) > 0:
                result[category][name]['issues'].extend(match['issues'])

            if version != None and version not in result[category][name]['versions']:
                result[category][name]['versions'].append(version)
            if 'url' in item and item['url'] not in result[category][name]['sources']:
                result[category][name]['sources'].append(item['url'])
                if version != None:
                    v_sources_key = 'v-{0}-sources'.format(
                        version)
                    if v_sources_key not in result[category][name]:
                        result[category][name][v_sources_key] = list()
                    result[category][name][v_sources_key].append(item['url'])
            if 'latest-version' in match:
                result[category][name]['latest-version'] = match['latest-version']
            if 'nof-newer-versions' in match:
                if 'nof-newer-versions' not in result[category][name] or result[category][name]['nof-newer-versions'] < match['nof-newer-versions']:
                    result[category][name]['nof-newer-versions'] = match['nof-newer-versions']
                v_newer_key = 'v-{0}-nof-newer-versions'.format(
                    version)
                result[category][name][v_newer_key] = match['nof-newer-versions']

    result = cleanup_software_result(result)

    # for category in result:
    #     if 'called_url' == category:
    #         continue

    #     for software_name in result[category]:
    #         software = result[category][software_name]
    #         for version in software['versions']:
    #             records = get_cve_records_for_software_and_version(
    #                 software_name, version, category)
    #             if len(records) > 0:
    #                 if 'vulnerabilities' not in result[category][software_name]:
    #                     result[category][software_name]['vulnerabilities'] = list()
    #                 result[category][software_name]['vulnerabilities'].extend(
    #                     records)

    return result


def cleanup_software_result(result):

    for category in result:
        if 'called_url' == category:
            continue

        for software_name in result[category]:
            software = result[category][software_name]
            versions = software['versions']
            versions_to_remove = list()

            for version in versions:
                version_sources_key = 'v-{0}-sources'.format(version)
                version_newer_key = 'v-{0}-nof-newer-versions'.format(version)
                should_remove = False
                if version_sources_key not in software:
                    should_remove = True

                if should_remove:
                    versions_to_remove.append(version)

            for version in versions_to_remove:
                version_sources_key = 'v-{0}-sources'.format(version)
                version_newer_key = 'v-{0}-nof-newer-versions'.format(version)
                software['versions'].remove(version)

                if version_sources_key in software:
                    del software[version_sources_key]

                if version_newer_key in software:
                    del software[version_newer_key]

            if len(software['versions']) == 1:
                version = software['versions'][0]
                version_sources_key = 'v-{0}-sources'.format(version)
                version_newer_key = 'v-{0}-nof-newer-versions'.format(version)

                if version_sources_key in software:
                    del software[version_sources_key]

                if version_newer_key in software:
                    del software[version_newer_key]

    return result


def convert_item_to_domain_data(data):
    result = {
        'issues': []
    }

    for item in data:
        for match in item['matches']:
            if 'issues' in match:
                result['issues'].extend(match['issues'])

            category = match['category']
            name = match['name']
            if name == '?':
                continue
            version = match['version']
            if version == None:
                version = '?'
            precision = match['precision']

            if category not in result:
                result[category] = {}
            if name not in result[category]:
                result[category][name] = {}
            if version not in result[category][name]:
                result[category][name][version] = {
                    'name': name, 'precision': precision
                }
            if 'github-owner' in match:
                result[category][name][version]['github-owner'] = match['github-owner']
            if 'github-repo' in match:
                result[category][name][version]['github-repo'] = match['github-repo']
            if 'latest-version' in match:
                result[category][name]['latest-version'] = match['latest-version']
            if 'is-latest-version' in match:
                result[category][name]['is-latest-version'] = match['is-latest-version']
            if 'tech' in match:
                # if software has info about tech, add it
                if 'tech' not in result:
                    result['tech'] = {}
                for tech in match['tech']:
                    if tech not in result['tech']:
                        result['tech'][tech] = {
                            "?": {
                                "name": tech,
                                "precision": 0.8
                            }
                        }

            if 'img' in match:
                # if software has info about tech, add it
                if 'img' not in result:
                    result['img'] = {}
                for img in match['img']:
                    if tech not in result['img']:
                        result['img'][img] = {
                            "?": {
                                "name": img,
                                "precision": 0.8
                            }
                        }

            if result[category][name][version]['precision'] < precision:
                obj = {}
                obj['name'] = name
                obj['precision'] = precision
                if 'github-owner' in match:
                    obj['github-owner'] = match['github-owner']
                if 'github-repo' in match:
                    obj['github-repo'] = match['github-repo']
                result[category][name][version] = obj

    cleanup_domain_data(result)

    return result


def enrich_data(data, orginal_domain, result_folder_name, rules):

    cms = None
    # matomo = None
    testing = {}

    tmp_list = list()

    for item in data:
        # if item['domain'] != orginal_domain:
        #     continue

        enrich_versions(item)

        # if item['category'] == 'cms':
        #     cms = item['name']

        # if item['category'] == 'test':
        #     testing[item['name']] = False

        # if item['precision'] >= 0.5 and (item['category'] == 'os' or item['category'] == 'webserver' or item['category'] == 'cms'):
        #     if item['version'] != None:
        #         if 'is-latest-version' in item and item['is-latest-version']:
        #             item['security.latest-but-leaking-name-and-version'] = True
        #         else:
        #             item['security.leaking-name-and-version'] = True

        #         tmp_list.append(get_default_info(
        #             item['url'], 'enrich', item['precision'], 'security', 'screaming.{0}'.format(item['category']), None))
        #     else:
        #         tmp_list.append(get_default_info(
        #             item['url'], 'enrich', item['precision'], 'security', 'talking.{0}'.format(item['category']), None))

        # # matomo = enrich_data_from_matomo(matomo, tmp_list, item)
        enrich_data_from_javascript(tmp_list, item, rules)
        enrich_data_from_videos(tmp_list, item, result_folder_name)
        enrich_data_from_images(tmp_list, item, result_folder_name)
        enrich_data_from_documents(tmp_list, item, result_folder_name)

        # ignore = False
        # for match in item['matches']:
        #     if match['category'] == 'img' or match['category'] == 'meta':
        #         ignore = True

        # if not ignore:
        #     nice_raw = json.dumps(item, indent=2)
        #     print('DEBUG', nice_raw)

    # data.extend(tmp_list)

    if len(testing) > 0:
        raw_data['test'][orginal_domain] = {
            'cms': cms,
            'test': testing
        }

    # nice_raw = json.dumps(tmp_list, indent=2)
    # print('DEBUG 2', nice_raw)


    return data

def get_softwares():
    # TODO: change to this version when used in webperf-core
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent
    # dir = Path(os.path.dirname(
    #     os.path.realpath(__file__)) + os.path.sep)

    file_path = '{0}{1}data{1}software-full.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}software-full.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        print("ERROR: No software-full.json file found!")
        return {
            'loaded': False
        }

    # print('get_softwares', file_path)

    with open(file_path) as json_file:
        softwares = json.load(json_file)
    return softwares


def add_github_software_source(name, github_ower, github_repo):
    # TODO: change to this version when used in webperf-core
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent
    # dir = Path(os.path.dirname(
    #     os.path.realpath(__file__)) + os.path.sep)

    file_path = '{0}{1}data{1}software-sources.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}software-sources.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        print("ERROR: No software-sources.json file found!")
        return

    print('add_github_software_source', file_path)

    collection = None
    with open(file_path) as json_file:
        collection = json.load(json_file)

    if 'softwares' not in collection:
        collection['softwares'] = {}

    if name not in collection['softwares']:
        collection['softwares'][name] = {
            'github-owner': github_ower,
            'github-repo': github_repo
        }

    data = json.dumps(collection, indent=4)
    with open(file_path, 'w', encoding='utf-8', newline='') as file:
        file.write(data)

def add_unknown_software_source(name, version, url):
    # TODO: change to this version when used in webperf-core
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent
    # dir = Path(os.path.dirname(
    #     os.path.realpath(__file__)) + os.path.sep)

    file_path = '{0}{1}data{1}software-unknown-sources.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}software-unknown-sources.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        print("Info: No software-unknown-sources.json file found!")

    # print('add_unknown_software_source', file_path)

    collection = {}
    try:
        with open(file_path) as json_file:
            collection = json.load(json_file)
    except:
        print('INFO: There was no ', file_path, 'file.')

    if name not in collection: 
        collection[name] = {
            'versions': {},
        }
    
    if version == None or version == '':
        version = 'unknown'

    if version not in collection[name]['versions']:
        collection[name]['versions'][version] = []

    if len(collection[name]['versions'][version]) < 20:
        collection[name]['versions'][version].append(url)

    data = json.dumps(collection, indent=4)
    with open(file_path, 'w', encoding='utf-8', newline='') as file:
        file.write(data)


def enrich_versions(item):
    collection = get_softwares()
    if 'softwares' not in collection:
        return
        
    if 'aliases' not in collection:
        return

    for match in item['matches']:
        if match['category'] != 'tech' and match['category'] != 'js' and match['category'] != 'cms' and match['category'] != 'os':
            continue

        newer_versions = []

        # TODO: THIS MUST BE LOOKED AT FROM A 'COMPUTER BREACH' ARGUMENT,
        # if item['name'] == 'matomo':
        #     a = 1
        # THERE IS NO REFERENCE TO THIS SO IT COULD (WRONGLY) BE ARGUED THAT YOU ARE TRYING TO HACK
        #     matomo = {}
        #     matomo['name'] = 'Matomo'
        #     matomo['url'] = item['url']
        #     matomo_version = 'Matomo'

        #     # matomo_o = urlparse(item['url'])
        #     # matomo_hostname = matomo_o.hostname
        #     # matomo_url = '{0}://{1}/CHANGELOG.md'.format(
        #     #     matomo_o.scheme, matomo_hostname)
        #     # matomo_changelog_url_regex = r"(?P<url>.*)\/(matomo|piwik).(js|php)"
        #     # matches = re.finditer(
        #     #     matomo_changelog_url_regex, item['url'], re.MULTILINE)
        #     # for matchNum, match in enumerate(matches, start=1):
        #     #     matomo_url = match.group('url') + '/CHANGELOG.md'
        #     #     matomo_content = httpRequestGetContent(matomo_url)
        #     #     matomo_regex = r"## Matomo (?P<version>[\.0-9]+)"
        #     #     matches = re.finditer(
        #     #         matomo_regex, matomo_content, re.MULTILINE)
        #     #     for matchNum, match in enumerate(matches, start=1):
        #     #         matomo_version = match.group('version')
        #     #         matomo['version'] = matomo_version
        #     #         break

    
        if match['name'] not in collection['softwares']:
            # Check aliases
            if match['name'] in collection['aliases']:
                match['name'] = collection['aliases'][match['name']]
                match['precision'] += 0.25
            else:
                has_match = False
                for alias in collection['aliases']:
                    if '*' in alias:
                        tmp_alias = alias.replace('*', '')
                        if tmp_alias in match['name']:
                            match['name'] = collection['aliases'][alias]
                            has_match = True
                            match['precision'] += 0.25
                            break
                if not has_match:
                    # If not in aliases, add to software-sources.json
                    if 'github-owner' in match and 'github-repo' in match:
                        add_github_software_source(match['name'], match['github-owner'], match['github-repo'])
                    else:
                        add_unknown_software_source(match['name'], match['version'], item['url'])
                    continue

        software_info = collection['softwares'][match['name']]
        if 'github-owner' in software_info and 'github-repo' in software_info:
            match['github-owner'] = software_info['github-owner']
            match['github-repo'] = software_info['github-repo']

        if 'license' in software_info:
            match['license'] = software_info['license']
        if 'archived' in software_info and software_info['archived']:
            # if 'issues' not in item:
            #     match['issues'] = []
            match['issues'].append('ARCHIVED-SOURCE')
        if 'tech' in software_info:
            match['tech'] = software_info['tech']

        if match['version'] == None:
            continue

        version = None

        try:
            # ensure version field uses valid format
            version = packaging.version.Version(match['version'])
        except:
            # TODO: handle matomo like software rules where version = '>=4.x'.
            # TODO: handle matomo like software rules where version = '>4.x'.
            # TODO: handle matomo like software rules where version = '<5.x'.
            # TODO: handle matomo like software rules where version = '=4.x'.
            # print('DEBUG A', match['version'])
            continue
       
        for current_version in software_info['versions'].keys():
            tmp_version = None
            try:
                tmp_version = packaging.version.Version(current_version)
            except:
                # print('DEBUG B', current_version)
                continue

            if tmp_version == version:
                match['issues'].extend(software_info['versions'][match['version']])
                break
            elif tmp_version > version:
                # handle versions that doesn't match but we know is less or greater then versions we know.
                # For example if: software_info['versions'] = [4.0, 3.0, 2.0, 1.0]. version = '1.7'. We know it is behind versions [4.0, 3.0, 2.0]
                # So we should be able to show them as newer, great for when websites use a prerelease version for example.
                newer_versions.append(current_version)

        nof_newer_versions = len(newer_versions)
        has_more_then_one_newer_versions = nof_newer_versions > 0

        if has_more_then_one_newer_versions:
            has_more_then_10_newer_versions = len(newer_versions) >= 10
            has_more_then_25_newer_versions = len(newer_versions) >= 25
            has_more_then_50_newer_versions = len(newer_versions) >= 50
            has_more_then_75_newer_versions = len(newer_versions) >= 75
            has_more_then_100_newer_versions = len(newer_versions) >= 100
            if has_more_then_100_newer_versions:
                match['issues'].append('BEHIND100')
            elif has_more_then_75_newer_versions:
                match['issues'].append('BEHIND075')
            elif has_more_then_50_newer_versions:
                match['issues'].append('BEHIND050')
            elif has_more_then_25_newer_versions:
                match['issues'].append('BEHIND025')
            elif has_more_then_10_newer_versions:
                match['issues'].append('BEHIND010')
            else:
                match['issues'].append('BEHIND001')

    # nice_raw = json.dumps(item, indent=2)
    # print('DEBUG', nice_raw)

    # return

def enrich_data_from_javascript(tmp_list, item, rules):
    if use_stealth:
        return
    for match in item['matches']:
        if match['category'] != 'js':
            return
        if 'license-txt' in item:
            content = httpRequestGetContent(
                match['license-txt'].lower(), allow_redirects=True)
            tmp = lookup_response_content(
                match['license-txt'].lower(), match['mime-type'], content, rules)
            tmp_list.extend(tmp)
        if match['version'] == None:
            return
    # TODO: We should look at wordpress plugins specifically as they are widely used and we know they are often used in attacks


def enrich_data_from_videos(tmp_list, item, result_folder_name, nof_tries=0):
    if use_stealth:
        return
    for match in item['matches']:
        if match['category'] != 'video':
            return

        if match['name'] != 'mp4':
            return

        # TODO: Consider if we should read metadata from video


def enrich_data_from_documents(tmp_list, item, result_folder_name, nof_tries=0):
    if use_stealth:
        return
    # TODO: Handle: pdf, excel, word, powerpoints (and more?)


def enrich_data_from_images(tmp_list, item, result_folder_name, nof_tries=0):
    if use_stealth:
        return
    for match in item['matches']:
        if match['category'] != 'img':
            return

        if match['name'] == 'svg':
            # NOTE: We don't get content for svg files currently, it would be better if we didn't need to request it once more
            svg_content = httpRequestGetContent(item['url'])

            # <!-- Generator: Adobe Illustrator 16.0.4, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->
            svg_regex = r"<!-- Generator: (?P<name>[a-zA-Z ]+)[ ]{0,1}(?P<version>[0-9.]*)"
            matches = re.finditer(svg_regex, svg_content, re.MULTILINE)

            tech_name = ''
            tech_version = ''
            for matchNum, match in enumerate(matches, start=1):
                tech_name = match.group('name')
                tech_version = match.group('version')

                if tech_name != None and tech_version == None:
                    tech_name = tech_name.lower().strip().replace(' ', '-')
                    tmp_list.append(get_default_info(
                        item['url'], 'enrich', 0.5, 'img.software', tech_name, None))
                    tmp_list.append(get_default_info(
                        item['url'], 'enrich', match['precision'], 'security', 'whisper.{0}.app'.format(match['category']), None))

                if tech_version != None:
                    tech_version = tech_version.lower()
                    tmp_list.append(get_default_info(
                        item['url'], 'content', 0.6, 'img.software', tech_name, tech_version))
                    tmp_list.append(get_default_info(
                        item['url'], 'enrich', 0.8, 'security', 'whisper.{0}.app'.format(match['category']), None))
        else:
            cache_key = '{0}.cache.{1}'.format(
                hashlib.sha512(item['url'].encode()).hexdigest(), match['name'])
            cache_path = os.path.join(result_folder_name, cache_key)

            image_data = None
            try:
                if use_cache and os.path.exists(cache_path) and is_file_older_than(cache_path, cache_time_delta):
                    image_data = Image.open(cache_path)
                else:
                    data = httpRequestGetContent(
                        item['url'], use_text_instead_of_content=False)
                    with open(cache_path, 'wb') as file:
                        file.write(data)
                    image_data = Image.open(cache_path)
            except:
                return

            # extract EXIF data
            exifdata = image_data.getexif()
            # if nof_tries == 0 and (exifdata == None or len(exifdata.keys()) == 0):
            # TODO: THIS MUST BE LOOKED AT FROM A 'COMPUTER BREACH' ARGUMENT,
            # THERE IS NO REFERENCE TO THIS SO IT COULD (WRONGLY) BE ARGUED THAT YOU ARE TRYING TO HACK
            # test_index = item['url'].rfind(
            #     '.{0}'.format(item['name']))
            # # test_index = item['url'].rfind(
            # #     '.{0}?'.format(item['name']))
            # if test_index > 0:
            #     test_url = '{1}.{0}'.format(
            #         item['name'], item['url'][:test_index])
            #     test = get_default_info(
            #         test_url, 'enrich', item['precision'], item['category'], item['name'], item['version'], item['domain'])

            #     enrich_data_from_images(
            #         tmp_list, test, result_folder_name, nof_tries + 1)

            device_name = None
            device_version = None

            # iterating over all EXIF data fields
            for tag_id in exifdata:
                # get the tag name, instead of human unreadable tag id
                tag = TAGS.get(tag_id, None)
                if tag == None:
                    tag = 'unknown_{0}'.format(tag_id)

                tag_name = tag.lower()
                tag_data = exifdata.get(tag_id)
                # decode bytes
                try:
                    if isinstance(tag_data, bytes):
                        tag_data = tag_data.decode()
                except:
                    a = 1
                tag_name = tag_name.lower()
                if 'software' == tag_name:
                    regex = r"(?P<debug>^(^(?P<name>([a-zA-Z ]+))) (?P<version>[0-9.]+){0,1}[ (]{0,2}(?P<osname>[a-zA-Z]+){0,1})[)]{0,1}"
                    matches = re.finditer(
                        regex, tag_data, re.MULTILINE)
                    for matchNum, match in enumerate(matches, start=1):
                        tech_name = match.group('name')
                        tech_version = match.group('version')
                        os_name = match.group('osname')
                        if tech_name != None and tech_version == None:
                            tech_name = tech_name.lower().strip().replace(' ', '-')
                            tmp_list.append(get_default_info(
                                item['url'], 'enrich', 0.5, 'img.software', tech_name, None))
                            tmp_list.append(get_default_info(
                                item['url'], 'enrich', match['precision'], 'security', 'whisper.{0}.app'.format(match['category']), None))

                        if tech_version != None:
                            tech_version = tech_version.lower()
                            tmp_list.append(get_default_info(
                                item['url'], 'content', 0.6, 'img.software', tech_name, tech_version))
                            tmp_list.append(get_default_info(
                                item['url'], 'enrich', 0.8, 'security', 'whisper.{0}.app'.format(match['category']), None))

                        if os_name != None:
                            os_name = os_name.lower()
                            tmp_list.append(get_default_info(
                                item['url'], 'content', 0.6, 'img.os', os_name, None))
                            tmp_list.append(get_default_info(
                                item['url'], 'enrich', 0.8, 'security', 'whisper.{0}.os'.format(match['category']), None))
                elif 'artist' == tag_name or 'xpauthor' == tag_name:
                    tmp_list.append(get_default_info(
                        item['url'], 'enrich', 0.8, 'security', 'info.{0}.person'.format(match['category']), None))
                elif 'make' == tag_name:
                    device_name = tag_data.lower().strip()
                    if 'nikon corporation' in device_name:
                        device_name = device_name.replace(
                            'nikon corporation', 'nikon')
                elif 'hostcomputer' == tag_name:
                    regex = r"(?P<debug>^(^(?P<name>([a-zA-Z ]+))) (?P<version>[0-9.]+){0,1}[ (]{0,2}(?P<osname>[a-zA-Z]+){0,1})[)]{0,1}"
                    matches = re.finditer(
                        regex, tag_data, re.MULTILINE)
                    for matchNum, match in enumerate(matches, start=1):
                        tech_name = match.group('name')
                        tech_version = match.group('version')
                        os_name = match.group('osname')
                        if tech_name != None and tech_version == None:
                            tech_name = tech_name.lower().strip().replace(' ', '-')
                            device_name = tech_name
                            # tmp_list.append(get_default_info(
                            #     item['url'], 'enrich', 0.5, 'img.device', tech_name, None))
                            tmp_list.append(get_default_info(
                                item['url'], 'enrich', match['precision'], 'security', 'whisper.{0}.device'.format(match['category']), None))

                        if tech_version != None:
                            tech_version = tech_version.lower()
                            device_version = tech_version
                            # tmp_list.append(get_default_info(
                            #     item['url'], 'content', 0.6, 'img.os', tech_name, tech_version))
                            tmp_list.append(get_default_info(
                                item['url'], 'enrich', 0.8, 'security', 'whisper.{0}.device'.format(match['category']), None))

                        if os_name != None:
                            os_name = os_name.lower().strip()
                            tmp_list.append(get_default_info(
                                item['url'], 'content', 0.6, 'img.os', os_name, None))
                            tmp_list.append(get_default_info(
                                item['url'], 'enrich', 0.8, 'security', 'whisper.{0}.os'.format(match['category']), None))
                elif 'model' == tag_name:
                    tmp_list.append(get_default_info(
                        item['url'], 'enrich', 0.8, 'security', 'info.{0}.model'.format(match['category']), None))
                    device_version = tag_data.lower().strip()
                elif 'gpsinfo' == tag_name:
                    tmp_list.append(get_default_info(
                        item['url'], 'enrich', 0.8, 'security', 'info.{0}.location'.format(match['category']), None))

            if device_name != None or device_version != None:
                if device_name != None:
                    device_name = device_name.lower().strip()
                if device_name != None and device_version == None:
                    tmp_list.append(get_default_info(
                        item['url'], 'enrich', 0.5, 'img.device', device_name, None))
                    tmp_list.append(get_default_info(
                        item['url'], 'enrich', match['precision'], 'security', 'whisper.{0}.device'.format(match['category']), None))

                if device_name != None and device_version != None:
                    device_version = device_version.lower()
                    if device_name != None:
                        device_version = device_version.replace(device_name, '')
                    tmp_list.append(get_default_info(
                        item['url'], 'content', 0.6, 'img.device', device_name, device_version))
                    tmp_list.append(get_default_info(
                        item['url'], 'enrich', 0.8, 'security', 'whisper.{0}.device'.format(match['category']), None))


def identify_software(filename, origin_domain, rules):
    data = list()

    # Fix for content having unallowed chars
    with open(filename) as json_input_file:
        har_data = json.load(json_input_file)

        global_software = None

        if 'log' in har_data:
            har_data = har_data['log']

        if 'software' in har_data:
            global_software = har_data['software']

            # nice_raw = json.dumps(global_software, indent=2)
            # print('DEBUG - Global Software', nice_raw)


        for entry in har_data["entries"]:
            req = entry['request']
            res = entry['response']
            req_url = req['url']

            item = {
                'url': req_url,
                'matches': []
            }

            lookup_request_url(item, rules, origin_domain)

            if 'headers' in res:
                headers = res['headers']
                lookup_response_headers(
                    item, headers, rules, origin_domain)

            if 'content' in res and 'text' in res['content']:
                response_content = res['content']['text']
                response_mimetype = res['content']['mimeType']
                lookup_response_content(
                    item, response_mimetype, response_content, rules)
            else:
                response_mimetype = res['content']['mimeType']
                lookup_response_mimetype(
                    item, response_mimetype)
            # {
            #   "domain": "boden.matomo.cloud",
            #   "method": "url",
            #   "precision": 0.4,
            #   "category": "tech",
            #   "name": "php",
            #   "version": null
            # }

            # cleanup_duplicate_matches(item)

            cleanup_used_global_software(global_software, item)
            data.append(item)

    # remove_empty_items(data)
    # nice_raw = json.dumps(data, indent=2)
    # print('DEBUG 3', nice_raw)
    # TODO: Check for https://docs.2sxc.org/index.html ?

    for software_name in global_software.keys():
        versions = global_software[software_name]
        if len(versions) == 0:
            continue
        for version in versions:
            info = get_default_info(
                req_url, 'js-objects', 0.8, 'js', software_name, version)
            item['matches'].append(info)

    # nice_raw = json.dumps(global_software, indent=2)
    # print('DEBUG - Global Software, UNRESOLVED', nice_raw)

    return data


def cleanup_used_global_software(global_software, item):
    for match in item['matches']:
        if match['name'] in global_software and match['version'] in global_software[match['name']]:
            global_software[match['name']].remove(match['version'])

def cleanup_duplicate_matches(item):
    tmp = set()
    for index, match in enumerate(item['matches']):
        for index2, match2 in enumerate(item['matches']):
            if index == index2:
                continue
            if match['category'] != match2['category']:
                continue
            if match['name'] != match2['name']:
                continue
            if match['version'] != match2['version']:
                continue

            if len(match.keys()) != len(match2.keys()):
                continue

            if match['precision'] < match2['precision']:
                tmp.add(index)
            else:
                tmp.add(index2)

    tmp = list(tmp)
    if len(tmp) > 0:
        tmp = reversed(tmp)
        for index3 in tmp:
            del item['matches'][index3]

def remove_empty_items(data):
    tmp = set()
    for index, item in enumerate(data):
        if len(item['matches']) == 0:
            tmp.add(index)

    tmp = list(tmp)
    if len(tmp) > 0:
        tmp = reversed(tmp)
        for index3 in tmp:
            del data[index3]


def lookup_response_mimetype(item, response_mimetype):

    if raw_data['mime-types']['use']:
        raw_data['mime-types'][response_mimetype] = 'svg' in response_mimetype or 'mp4' in response_mimetype or 'webp' in response_mimetype or 'png' in response_mimetype or 'jpg' in response_mimetype or 'jpeg' in response_mimetype or 'bmp' in response_mimetype

    if 'mp4' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        # look at: https://www.handinhandsweden.se/wp-content/uploads/se/2022/11/julvideo-startsida.mp4
        # that has videolan references and more interesting stuff
        item['matches'].append(get_default_info(
            item['url'], 'mimetype', 0.8, 'tech', 'mp4', None))

    if 'webp' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        item['matches'].append(get_default_info(
            item['url'], 'mimetype', 0.8, 'img', 'webp', None))
    elif 'png' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        item['matches'].append(get_default_info(
            item['url'], 'mimetype', 0.8, 'img', 'png', None))
    elif 'jpg' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        item['matches'].append(get_default_info(
            item['url'], 'mimetype', 0.8, 'img', 'jpg', None))
    elif 'jpeg' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        item['matches'].append(get_default_info(
            item['url'], 'mimetype', 0.8, 'img', 'jpeg', None))
    elif 'bmp' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        item['matches'].append(get_default_info(
            item['url'], 'mimetype', 0.8, 'img', 'bmp', None))


def lookup_response_content(item, response_mimetype, response_content, rules):
    if 'contents' not in rules:
        return

    is_found = False
    for rule in rules['contents']:
        if 'use' not in rule:
            continue
        if 'type' not in rule:
            continue
        if 'match' not in rule:
            continue
        if 'results' not in rule:
            continue

        if rule['type'] not in response_mimetype:
            continue

        req_url = item['url'].lower()

        o = urlparse(req_url)
        hostname = o.hostname

        regex = r"{0}".format(rule['match'])
        matches = re.finditer(regex, response_content, re.IGNORECASE)
        for matchNum, match in enumerate(matches, start=1):
            match_name = None
            match_version = None
            match_github_owner = None
            match_github_repo = None
            license_url = None

            groups = match.groupdict()

            if 'name' in groups:
                match_name = groups['name']
            if '?P<name>' in rule['match'] and match_name == None:
                continue
            if 'version' in groups:
                match_version = groups['version']
            if '?P<version>' in rule['match'] and match_version == None:
                continue
            if 'owner' in groups:
                match_github_owner = groups['owner']
            if '?P<owner>' in rule['match'] and match_github_owner == None:
                continue
            if 'repo' in groups:
                match_github_repo = groups['repo']
            if '?P<repo>' in rule['match'] and match_github_repo == None:
                continue

            if 'licensetxt' in groups and 'licensefile' in groups:
                source_segment = groups['licensefile']
                license_txt = groups['licensetxt']
                license_index = req_url.rfind(source_segment)
                tmp_url = req_url[:license_index]
                license_url = '{0}{1}{2}'.format(
                    tmp_url, source_segment, license_txt)

            for result in rule['results']:
                name = None
                version = None
                if 'category' not in result:
                    continue
                if 'precision' not in result:
                    continue

                category = result['category']
                precision = result['precision']

                if 'name' in result:
                    name = result['name']
                else:
                    name = match_name
                if 'version' in result:
                    version = result['version']
                else:
                    version = match_version

                if precision > 0.0:
                    info = get_default_info(
                        req_url, 'content', precision, category, name, version)
                    if match_github_owner != None:
                        info['github-owner'] = match_github_owner
                    if match_github_repo != None:
                        info['github-repo'] = match_github_repo
                    if license_url != None:
                        info['license-txt'] = license_url
                    info['mime-type'] = response_mimetype

                    item['matches'].append(info)
                    is_found = True
                elif raw_data['contents']['use'] and not is_found:
                    raw_data['contents'][match.group('debug')] = hostname


def get_default_info(url, method, precision, key, name, version, domain=None):
    result = {}

    if domain != None:
        result['domain'] = domain
    else:
        o = urlparse(url)
        hostname = o.hostname
        result['domain'] = hostname

    if name != None:
        name = name.lower().strip('.').strip('-').strip().replace(' ', '-')

    if version != None:
        version = version.lower().strip('.').strip('-').strip()

    # result['url'] = url
    result['method'] = method
    result['precision'] = precision
    result['category'] = key
    result['name'] = name
    result['version'] = version
    result['issues'] = []
    # result['security'] = []

    return result


def lookup_request_url(item, rules, origin_domain):
    data = list()

    if 'urls' not in rules:
        return data

    is_found = False
    for rule in rules['urls']:
        if 'use' not in rule:
            continue
        if 'match' not in rule:
            continue
        if 'results' not in rule:
            continue

        req_url = item['url'].lower()

        regex = r"{0}".format(rule['match'])
        matches = re.finditer(regex, req_url, re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):
            match_name = None
            match_version = None

            groups = match.groupdict()

            if 'name' in groups:
                match_name = groups['name']
            if 'version' in groups:
                match_version = groups['version']

            if '?P<name>' in rule['match'] and match_name == None:
                continue
            if '?P<version>' in rule['match'] and match_version == None:
                continue

            for result in rule['results']:
                name = None
                version = None
                if 'category' not in result:
                    continue
                if 'precision' not in result:
                    continue

                category = result['category']
                precision = result['precision']

                if 'name' in result:
                    name = result['name']
                else:
                    name = match_name
                if 'version' in result:
                    version = result['version']
                else:
                    version = match_version

                domain = None
                if 'domain' in result and result['domain'] == 'referrer':
                    domain = origin_domain

                if precision > 0.0:
                    item['matches'].append(get_default_info(
                        req_url, 'url', precision, category, name, version, domain))
                    is_found = True
                if raw_data['urls']['use'] and not is_found:
                    raw_data['urls'][req_url] = is_found
    # return item

def lookup_response_headers(item, headers, rules, origin_domain):
    data = list()

    for header in headers:
        header_name = header['name'].lower()
        header_value = header['value'].lower()

        if raw_data['headers']['use']:
            raw_data['headers'][header_name] = header_value

        lookup_response_header(
            item, header_name, header_value, rules, origin_domain)
    #     if len(tmp_data) != 0:
    #         data.extend(tmp_data)
    # return data


def lookup_response_header(item, header_name, header_value, rules, origin_domain):
    # data = list()

    if 'headers' not in rules:
        return# data

    is_found = False
    for rule in rules['headers']:
        if 'use' not in rule:
            continue
        if 'type' not in rule:
            continue
        if 'match' not in rule:
            continue
        if 'results' not in rule:
            continue

        if rule['type'] not in header_name:
            continue

        req_url = item['url'].lower()

        o = urlparse(req_url)
        hostname = o.hostname

        regex = r"{0}".format(rule['match'])
        matches = re.finditer(regex, header_value, re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):
            match_name = None
            match_version = None

            groups = match.groupdict()

            if 'name' in groups:
                match_name = groups['name']
            if 'version' in groups:
                match_version = groups['version']

            if '?P<name>' in rule['match'] and match_name == None:
                continue
            if '?P<version>' in rule['match'] and match_version == None:
                continue

            for result in rule['results']:
                name = None
                version = None
                if 'category' not in result:
                    continue
                if 'precision' not in result:
                    continue

                category = result['category']
                precision = result['precision']

                if 'name' in result:
                    name = result['name']
                else:
                    name = match_name
                if 'version' in result:
                    version = result['version']
                else:
                    version = match_version

                if precision > 0.0:
                    item['matches'].append(get_default_info(
                        req_url, 'header', precision, category, name, version))
                    is_found = True
                elif raw_data['headers']['use'] and not is_found:
                    raw_data['headers'][match.group('debug')] = hostname

    # return data


def get_rules():
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    file_path = '{0}{1}data{1}software-rules.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}SAMPLE-software-rules.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        print("ERROR: No software-rules.json file found!")

    with open(file_path) as json_rules_file:
        rules = json.load(json_rules_file)
    return rules


def run_test(_, langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    result_dict = {}
    rating = Rating(_, review_show_improvements_only)

    language = gettext.translation(
        'software', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    (rating, result_dict) = get_rating_from_sitespeed(url, _local, _)

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    raw_is_used = False
    for key in raw_data.keys():
        raw_is_used = raw_is_used or raw_data[key]['use']

    if raw_is_used:
        nice_raw = json.dumps(raw_data, indent=2)
        print(nice_raw)

    return (rating, result_dict)
