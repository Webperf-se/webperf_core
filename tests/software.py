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
    'cookies': {
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
    # sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --plugins.remove html --plugins.remove metrics --browsertime.screenshot false --screenshot false --screenshotLCP false --browsertime.screenshotLCP false --chrome.cdp.performance false --browsertime.chrome.timeline false --videoParams.createFilmstrip false --visualMetrics false --visualMetricsPerceptual false --visualMetricsContentful false --browsertime.headless true --browsertime.chrome.includeResponseBodies all --utc true --browsertime.chrome.args ignore-certificate-errors -n {0}'.format(
    #     sitespeed_iterations)
    # sitespeed_arg = '--shm-size=1g -b firefox --plugins.remove screenshot --plugins.remove html --plugins.remove metrics --browsertime.screenshot false --screenshot false --screenshotLCP false --browsertime.screenshotLCP false --chrome.cdp.performance false --browsertime.chrome.timeline false --videoParams.createFilmstrip false --visualMetrics false --visualMetricsPerceptual false --visualMetricsContentful false --browsertime.headless true --browsertime.chrome.includeResponseBodies all --utc true --browsertime.chrome.args ignore-certificate-errors -n {0}'.format(
    #     sitespeed_iterations)
    sitespeed_arg = '--shm-size=1g -b firefox --firefox.includeResponseBodies all --firefox.preference privacy.trackingprotection.enabled:false --firefox.preference privacy.donottrackheader.enabled:false --firefox.preference browser.safebrowsing.malware.enabled:false --firefox.preference browser.safebrowsing.phishing.enabled:false --plugins.remove screenshot --plugins.remove html --plugins.remove metrics --browsertime.screenshot false --screenshot false --screenshotLCP false --browsertime.screenshotLCP false --chrome.cdp.performance false --browsertime.chrome.timeline false --videoParams.createFilmstrip false --visualMetrics false --visualMetricsPerceptual false --visualMetricsContentful false --browsertime.headless true --browsertime.chrome.includeResponseBodies all --utc true --browsertime.chrome.args ignore-certificate-errors -n {0}'.format(
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

    # nice_raw = json.dumps(data, indent=2)
    # print('DEBUG 2', nice_raw)

    rating = Rating(_, review_show_improvements_only)
    result = convert_item_to_domain_data(data)

    # if 'issues' in result:
    #     nice_raw2 = json.dumps(result['issues'], indent=2)
    #     print('DEBUG 3a', nice_raw2)
    # else:
    #     nice_raw2 = json.dumps(result, indent=2)
    #     print('DEBUG 3b', nice_raw2)
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

    rating += rate_software_security_result(_local, _, result, url)

    rating.overall_review = '{0}\r\n'.format('\r\n'.join(texts))
    if len(rating.overall_review.strip('\r\n\t ')) == 0:
        rating.overall_review = ''
    rating.integrity_and_security_review = rating.integrity_and_security_review.replace('GOV-IGNORE', '').strip('\r\n\t ')

    if not use_cache:
        os.remove(filename)

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

    if len(data['issues'].keys())> 0:
        tmp = {}
        issue_keys = list(data['issues'].keys())
        issue_keys = sorted(issue_keys, key=cmp_to_key(sort_issues), reverse=True)

        for key in issue_keys:
            tmp[key] = data['issues'][key]

        data['issues'] = tmp

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


def rate_software_security_result(_local, _, result, url):
    rating = Rating(_, review_show_improvements_only)

    has_cve_issues = False
    has_behind_issues = False
    has_archived_source_issues = False
    # has_multiple_versions_issues = False
    has_end_of_life_issues = False

    for issue_type in result['issues']:
        text = ''
        if issue_type.startswith('CVE'):
            has_cve_issues = True
            points = 1.0
            cve_ratings = Rating(_, review_show_improvements_only)
            for sub_issue in result['issues'][issue_type]['sub-issues']:
                sub_rating = Rating(_, review_show_improvements_only)
                sub_rating.set_overall(points)
                sub_rating.set_integrity_and_security(points)
                cve_ratings += sub_rating
            if use_detailed_report:
                text = _local('TEXT_DETAILED_REVIEW_CVE').replace('#POINTS#', str(cve_ratings.get_integrity_and_security()))

                text += _local('TEXT_DETAILED_REVIEW_CVES')
                text += '\r\n'
                for cve in result['issues'][issue_type]['sub-issues']:
                    text += '- {0}\r\n'.format(cve)
                text += '\r\n'
                text += _local('TEXT_DETAILED_REVIEW_DETECTED_SOFTWARE')
                text += '\r\n'
                for software in result['issues'][issue_type]['softwares']:
                    text += '- {0}\r\n'.format(software)
                text += '\r\n'
                text += _local('TEXT_DETAILED_REVIEW_AFFECTED_RESOURCES')
                text += '\r\n'
                for resource in result['issues'][issue_type]['resources']:
                    text += '- {0}\r\n'.format(resource)

                cve_ratings.integrity_and_security_review = text
            rating += cve_ratings
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
            sub_rating.set_integrity_and_security(points)

            if use_detailed_report:
                text = _local('TEXT_DETAILED_REVIEW_{0}'.format(issue_type)).replace('#POINTS#', str(sub_rating.get_integrity_and_security()))
                text += '\r\n'
                text += _local('TEXT_DETAILED_REVIEW_DETECTED_SOFTWARE')
                text += '\r\n'
                for software in result['issues'][issue_type]['softwares']:
                    text += '- {0}\r\n'.format(software)

                text += '\r\n'
                text += _local('TEXT_DETAILED_REVIEW_AFFECTED_RESOURCES')
                text += '\r\n'
                for resource in result['issues'][issue_type]['resources']:
                    text += '- {0}\r\n'.format(resource)
                sub_rating.integrity_and_security_review = text

            rating += sub_rating
        elif issue_type.startswith('ARCHIVED_SOURCE'):
            has_archived_source_issues = True
            points = 1.75
            sub_rating = Rating(_, review_show_improvements_only)
            sub_rating.set_overall(points)
            sub_rating.set_integrity_and_security(points)
            if use_detailed_report:
                text = _local('TEXT_DETAILED_REVIEW_{0}'.format(issue_type)).replace('#POINTS#', str(sub_rating.get_integrity_and_security()))
                text += '\r\n'
                text += _local('TEXT_DETAILED_REVIEW_DETECTED_SOFTWARE')
                text += '\r\n'
                for software in result['issues'][issue_type]['softwares']:
                    text += '- {0}\r\n'.format(software)

                text += '\r\n'
                text += _local('TEXT_DETAILED_REVIEW_AFFECTED_RESOURCES')
                text += '\r\n'
                for resource in result['issues'][issue_type]['resources']:
                    text += '- {0}\r\n'.format(resource)
                sub_rating.integrity_and_security_review = text
            rating += sub_rating

        elif issue_type.startswith('END_OF_LIFE'):
            has_end_of_life_issues = True
            points = 1.75
            sub_rating = Rating(_, review_show_improvements_only)
            sub_rating.set_overall(points)
            sub_rating.set_integrity_and_security(points)

            if use_detailed_report:
                text = _local('TEXT_DETAILED_REVIEW_{0}'.format(issue_type)).replace('#POINTS#', str(sub_rating.get_integrity_and_security()))
                text += '\r\n'
                text += _local('TEXT_DETAILED_REVIEW_DETECTED_SOFTWARE')
                text += '\r\n'
                for software in result['issues'][issue_type]['softwares']:
                    text += '- {0}\r\n'.format(software)

                text += '\r\n'
                text += _local('TEXT_DETAILED_REVIEW_AFFECTED_RESOURCES')
                text += '\r\n'
                for resource in result['issues'][issue_type]['resources']:
                    text += '- {0}\r\n'.format(resource)
                sub_rating.integrity_and_security_review = text
            rating += sub_rating

        # elif issue_type.startswith('MULTIPLE-VERSIONS'):
        #     has_multiple_versions_issues = True

    if not has_cve_issues:
        points = 5.0
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(points)
        if use_detailed_report:
            sub_rating.set_integrity_and_security(points, _local('TEXT_DETAILED_REVIEW_NO_CVE'))
        else:
            sub_rating.set_integrity_and_security(points)
        rating += sub_rating

    if not has_behind_issues:
        points = 5.0
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(points)
        if use_detailed_report:
            sub_rating.set_integrity_and_security(points, _local('TEXT_DETAILED_REVIEW_NO_BEHIND'))
        else:
            sub_rating.set_integrity_and_security(points)
        rating += sub_rating

    if not has_archived_source_issues:
        points = 5.0
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(points)
        if use_detailed_report:
            sub_rating.set_integrity_and_security(points, _local('TEXT_DETAILED_REVIEW_NO_ARCHIVES'))
        else:
            sub_rating.set_integrity_and_security(points)
        rating += sub_rating

    if not has_end_of_life_issues:
        points = 5.0
        sub_rating = Rating(_, review_show_improvements_only)
        sub_rating.set_overall(points)
        if use_detailed_report:
            sub_rating.set_integrity_and_security(points, _local('TEXT_DETAILED_REVIEW_NO_END_OF_LIFE'))
        else:
            sub_rating.set_integrity_and_security(points)
        rating += sub_rating

    return rating


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


def convert_item_to_domain_data(data):
    result = {
        'issues': {}
    }

    for item in data:
        for match in item['matches']:
            if 'issues' in match:
                for issue_name in match['issues']:
                    issue_key = issue_name
                    if issue_key.startswith('CVE-'):
                        issue_key = 'CVE'
                    elif issue_key.startswith('END_OF_LIFE'):
                        issue_key = 'END_OF_LIFE'

                    if issue_key not in result['issues']:
                        result['issues'][issue_key] = {
                            'softwares': [],
                            'resources': [],
                            'sub-issues': []
                        }

                    if issue_key != issue_name:
                        if issue_name not in result['issues'][issue_key]['sub-issues']:
                            result['issues'][issue_key]['sub-issues'].append(issue_name)

                    if len(result['issues'][issue_key]['softwares']) < 15:
                        tmp = ''
                        if match['version'] != None:
                            tmp = ' {0}'.format(match['version'])
                        software_key = '{0}{1}'.format(match['name'], tmp)
                        if software_key not in result['issues'][issue_key]['softwares']:
                            result['issues'][issue_key]['softwares'].append(software_key)

                    if len(result['issues'][issue_key]['resources']) < 15:
                        if item['url'] not in result['issues'][issue_key]['resources']:
                            result['issues'][issue_key]['resources'].append(item['url'])
                    
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
        enrich_versions(item)

        enrich_data_from_javascript(tmp_list, item, rules)
        enrich_data_from_videos(tmp_list, item, result_folder_name)
        enrich_data_from_images(tmp_list, item, result_folder_name)
        enrich_data_from_documents(tmp_list, item, result_folder_name)

    if len(testing) > 0:
        raw_data['test'][orginal_domain] = {
            'cms': cms,
            'test': testing
        }

    # nice_raw = json.dumps(tmp_list, indent=2)
    # print('DEBUG 2', nice_raw)

    return data

def get_softwares():
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    file_path = '{0}{1}data{1}software-full.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}software-full.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        print("ERROR: No software-full.json file found!")
        return {
            'loaded': False
        }

    with open(file_path) as json_file:
        softwares = json.load(json_file)
    return softwares


def add_github_software_source(name, github_ower, github_repo):
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

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
            'note': 'BEFORE COMMIT, VERIFY THAT REPO EXIST, IS NOT REDIRECTED TO OTHER REPO AND HAVE TAGS/RELEASE VERSIONS IN SEMVERSION FORMAT (1.2.3). Remove this note if all is OK.',
            'github-owner': github_ower,
            'github-repo': github_repo
        }

    data = json.dumps(collection, indent=4)
    with open(file_path, 'w', encoding='utf-8', newline='') as file:
        file.write(data)

def add_unknown_software_source(name, version, url):
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    file_path = '{0}{1}data{1}software-unknown-sources.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}software-unknown-sources.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        print("Info: No software-unknown-sources.json file found!")

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
        if match['category'] != 'tech' and match['category'] != 'js' and match['category'] != 'cms' and match['category'] != 'os' and match['category'] != 'webserver':
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
            match['issues'].append('ARCHIVED_SOURCE')
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

        if 'versions' not in software_info:
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

    global_software = None
    global_cookies = None
    
    # Fix for content having unallowed chars
    with open(filename) as json_input_file:
        har_data = json.load(json_input_file)

        if 'log' in har_data:
            har_data = har_data['log']

        if 'software' in har_data:
            global_software = har_data['software']
        if 'cookies' in har_data:
            global_cookies = har_data['cookies']

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

                response_mimetype = None
                if 'mimeType' in res['content']:
                    response_mimetype = res['content']['mimeType']
                else:
                    print('ERROR! No mimeType', res['content'])

                lookup_response_content(
                    item, response_mimetype, response_content, rules)
            elif 'mimeType' in res['content']:
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

            cleanup_used_global_software(global_software, item)
            data.append(item)

    # remove_empty_items(data)
    # nice_raw = json.dumps(data, indent=2)
    # print('DEBUG 3', nice_raw)
    # TODO: Check for https://docs.2sxc.org/index.html ?

    if global_cookies != None:
        lookup_cookies(
            data[0], global_cookies, rules, origin_domain)

    for software_name in global_software.keys():
        versions = global_software[software_name]
        if len(versions) == 0:
            continue
        for version in versions:
            info = get_default_info(
                data[0]['url'], 'js-objects', 0.8, 'js', software_name, version)
            data[0]['matches'].append(info)
    # nice_raw = json.dumps(global_software, indent=2)
    # print('DEBUG - Global Software, UNRESOLVED', nice_raw)

    return data


def cleanup_used_global_software(global_software, item):
    for match in item['matches']:
        if match['name'] in global_software and match['version'] in global_software[match['name']]:
            global_software[match['name']].remove(match['version'])


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
        if not rule['use']:
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

    result['method'] = method
    result['precision'] = precision
    result['category'] = key
    result['name'] = name
    result['version'] = version
    result['issues'] = []

    return result


def lookup_request_url(item, rules, origin_domain):
    if 'urls' not in rules:
        return

    is_found = False
    for rule in rules['urls']:
        if 'use' not in rule:
            continue
        if not rule['use']:
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

def lookup_cookies(item, cookies, rules, origin_domain):
    for cookie in cookies:
        cookie_name = cookie['name'].lower()
        cookie_value = cookie['value'].lower()

        lookup_cookie(
            item, cookie_name, cookie_value, rules, origin_domain)

def lookup_cookie(item, cookie_name, cookie_value, rules, origin_domain):

    if 'cookies' not in rules:
        return

    is_found = False
    for rule in rules['cookies']:
        if 'use' not in rule:
            continue
        if not rule['use']:
            continue
        if 'type' not in rule:
            continue
        if 'match' not in rule:
            continue
        if 'results' not in rule:
            continue

        value = ''
        if 'name' == rule['type']:
            value = cookie_name
        elif 'value' == rule['type']:
            value = cookie_value

        req_url = item['url'].lower()

        o = urlparse(req_url)
        hostname = o.hostname


        regex = r"{0}".format(rule['match'])
        matches = re.finditer(regex, value, re.MULTILINE)
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
                        req_url, 'cookies', precision, category, name, version))
                    is_found = True
                elif raw_data['cookies']['use'] and not is_found:
                    raw_data['cookies'][match.group('debug')] = hostname

    if raw_data['cookies']['use'] and not is_found:
        if cookie_name not in raw_data['cookies']:
            raw_data['cookies'][cookie_name] = []
        raw_data['cookies'][cookie_name].append(cookie_value)



def lookup_response_headers(item, headers, rules, origin_domain):
    for header in headers:
        header_name = header['name'].lower()
        header_value = header['value'].lower()

        lookup_response_header(
            item, header_name, header_value, rules, origin_domain)

def lookup_response_header(item, header_name, header_value, rules, origin_domain):

    if 'headers' not in rules:
        return

    is_found = False
    for rule in rules['headers']:
        if 'use' not in rule:
            continue
        if not rule['use']:
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

    if raw_data['headers']['use'] and not is_found:
        if header_name not in raw_data['headers']:
            raw_data['headers'][header_name] = []
        raw_data['headers'][header_name].append(header_value)



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

        with open('debug.json', 'w', encoding='utf-8', newline='') as file:
            file.write(nice_raw)


    return (rating, result_dict)
