# -*- coding: utf-8 -*-
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
import datetime
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


def get_foldername_from_url(url):
    o = urlparse(url)
    hostname = o.hostname
    relative_path = o.path

    test_str = '{0}{1}'.format(hostname, relative_path)

    regex = r"[^a-zA-Z0-9\-\/]"
    subst = "_"

    # You can manually specify the number of replacements by changing the 4th argument
    folder_result = re.sub(regex, subst, test_str, 0, re.MULTILINE)

    # NOTE: hopefully temporary fix for "index.html" and Gullspangs-kommun.html
    folder_result = folder_result.replace('_html', '.html')

    folder_result = folder_result.replace('/', os.sep)

    return folder_result


def get_sanitized_file_content(input_filename):
    # print('input_filename=' + input_filename)
    lines = list()
    try:
        with open(input_filename, 'r', encoding='utf-8') as file:
            data = file.readlines()
            for line in data:
                lines.append(line)
                # print(line)
    except:
        print('error in get_local_file_content. No such file or directory: {0}'.format(
            input_filename))
        return '\n'.join(lines)

    test_str = '\n'.join(lines)
    regex = r"[^a-zåäöA-ZÅÄÖ0-9\{\}\"\:;.,#*\<\>%'&$?!`=@\-\–\+\~\^\\\/| \(\)\[\]_]"
    subst = ""

    # You can manually specify the number of replacements by changing the 4th argument
    result = re.sub(regex, subst, test_str, 0, re.MULTILINE)

    json_result = json.loads(result)
    has_minified = False
    if 'log' not in json_result:
        return ''
    if 'version' in json_result['log']:
        del json_result['log']['version']
        has_minified = True
    if 'browser' in json_result['log']:
        del json_result['log']['browser']
        has_minified = True
    if 'creator' in json_result['log']:
        del json_result['log']['creator']
        has_minified = True
    if 'pages' in json_result['log']:
        has_minified = False
        for page in json_result['log']['pages']:
            keys_to_remove = list()
            for key in page.keys():
                if key != '_url':
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del page[key]
                has_minified = True
    if 'entries' in json_result['log']:
        has_minified = False
        for entry in json_result['log']['entries']:
            keys_to_remove = list()
            for key in entry.keys():
                if key != 'request' and key != 'response':
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del entry[key]
                has_minified = True

            keys_to_remove = list()
            for key in entry['request'].keys():
                if key != 'url':
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del entry['request'][key]
                has_minified = True

            keys_to_remove = list()
            for key in entry['response'].keys():
                if key != 'content' and key != 'headers':
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                del entry['response'][key]
                has_minified = True

    if has_minified:
        write_json(input_filename, json_result)

    return result


def write_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as outfile:
        json.dump(data, outfile)


def get_rating_from_sitespeed(url, _local, _):
    # TODO: CHANGE THIS IF YOU WANT TO DEBUG
    folder_ending = 'tmp'
    if use_cache:
        folder_ending = 'cache'

    result_folder_name = os.path.join(
        'data', 'results-{0}-{1}'.format(str(uuid.uuid4()), folder_ending))
    # result_folder_name = os.path.join('data', 'results')

    from tests.performance_sitespeed_io import get_result as sitespeed_run_test

    sitespeed_iterations = 1

    sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --plugins.remove html --plugins.remove metrics --browsertime.screenshot false --screenshot false --screenshotLCP false --browsertime.screenshotLCP false --chrome.cdp.performance false --browsertime.chrome.timeline false --videoParams.createFilmstrip false --visualMetrics false --visualMetricsPerceptual false --visualMetricsContentful false --browsertime.headless true --browsertime.chrome.includeResponseBodies all --outputFolder {2} --utc true --xvfb --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        sitespeed_iterations, url, result_folder_name)
    if 'nt' in os.name:
        sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --plugins.remove html --plugins.remove metrics --browsertime.screenshot false --screenshot false --screenshotLCP false --browsertime.screenshotLCP false --chrome.cdp.performance false --browsertime.chrome.timeline false --videoParams.createFilmstrip false --visualMetrics false --visualMetricsPerceptual false --visualMetricsContentful false --browsertime.headless true --browsertime.chrome.includeResponseBodies all --outputFolder {2} --utc true --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
            sitespeed_iterations, url, result_folder_name)
        # sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --browsertime.chrome.includeResponseBodies all --outputFolder {2} --utc true --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        #     sitespeed_iterations, url, result_folder_name)

    filename = ''
    # Should we use cache when available?
    if use_cache:
        import engines.sitespeed_result as input
        sites = input.read_sites('', -1, -1)
        for site in sites:
            if url == site[1]:
                filename = site[0]
                result_folder_name = filename[:filename.rfind(os.path.sep)]

                if is_file_older_than(filename, cache_time_delta):
                    filename = ''
                    continue

                file_created_timestamp = os.path.getctime(filename)
                file_created_date = time.ctime(file_created_timestamp)
                print('Cached entry found from {0}, using it instead of calling website again.'.format(
                    file_created_date))
                break

    if filename == '':
        sitespeed_run_test(sitespeed_use_docker, sitespeed_arg)

        website_folder_name = get_foldername_from_url(url)

        filename_old = os.path.join(result_folder_name, 'pages',
                                    website_folder_name, 'data', 'browsertime.har')

        filename = os.path.join(result_folder_name, 'browsertime.har')

        if os.path.exists(filename_old):
            os.rename(filename_old, filename)
            dir_old = os.path.join(result_folder_name, 'pages')
            shutil.rmtree(dir_old)

    o = urlparse(url)
    origin_domain = o.hostname

    rules = get_rules()
    data = identify_software(filename, origin_domain, rules)
    data = enrich_data(data, origin_domain, result_folder_name, rules)
    result = convert_item_to_domain_data(data)
    rating = rate_result(_local, _, result, url)

    if not use_cache:
        shutil.rmtree(result_folder_name)

    return (rating, result)


def rate_result(_local, _, result, url):
    rating = Rating(_, review_show_improvements_only)

    url_info = urlparse(url)
    orginal_domain = url_info.hostname

    categories = ['cms', 'webserver', 'os',
                  'analytics', 'tech', 'license', 'meta',
                  'js', 'css',
                  'lang', 'img', 'img.software', 'img.os', 'img.device', 'video',
                  'test', 'security']

    for domain in result.keys():
        if domain not in orginal_domain:
            continue
        item = result[domain]

        (found_cms, rating) = rate_domain(
            _local, _, rating, categories, domain, item)

        if not found_cms and domain in orginal_domain:
            no_cms_rating = Rating(_, review_show_improvements_only)
            no_cms_rating.set_overall(5.0, _local('TEXT_NO_CMS'))
            rating += no_cms_rating

    for domain in result.keys():
        if domain in orginal_domain:
            continue
        item = result[domain]

        (found_cms, rating) = rate_domain(
            _local, _, rating, categories, domain, item)

    return rating


def rate_domain(_local, _, rating, categories, domain, item):
    found_cms = False
    has_announced_overall = False
    has_security = False

    for category in categories:
        if category in item:
            if category == 'security':
                has_security = True
                security_sub_categories = ['os', 'webserver', 'cms', 'img.app',
                                           'img.os', 'img.device', 'img.location']
                for key in item[category].keys():
                    points = 5.0
                    if 'screaming.' in key:
                        item_type = key[10:]
                        points = 1.0
                    elif 'talking.' in key:
                        item_type = key[8:]
                        points = 2.0
                    elif 'whisper.' in key:
                        item_type = key[8:]
                        points = 3.0
                    elif 'guide.' in key:
                        item_type = key[6:]
                        points = 4.0
                    elif 'info.' in key:
                        item_type = key[5:]
                        points = 5.0

                    sub_key_index = key.find('.') + 1
                    sub_key = key[sub_key_index:]
                    if sub_key in security_sub_categories:
                        security_sub_categories.remove(sub_key)
                    category_rating = Rating(_, review_show_improvements_only)
                    if 'not-latest' in key:
                        category_rating.set_overall(points)
                        category_rating.set_integrity_and_security(
                            points, _local('UPDATE_AVAILABLE').format(domain))
                    elif 'security-issues' in key:
                        category_rating.set_overall(points)
                        category_rating.set_integrity_and_security(
                            points, _local('KNOWN_SECURITY_ISSUES').format(domain))
                    else:
                        category_rating.set_overall(points)
                        category_rating.set_integrity_and_security(
                            points, _local('TEXT_USED_{0}'.format(
                                category.upper())).format('{0}'.format(domain)))
                        # category_rating.set_integrity_and_security(
                        #     points, _local('TEXT_USED_{0}'.format(
                        #         category.upper())).format('{0} - {1}'.format(item_type, domain)))

                    rating += category_rating
            else:
                category_rating = Rating(_, review_show_improvements_only)
                if not has_announced_overall:
                    domain_header_rating = Rating(
                        _, review_show_improvements_only)
                    domain_header_rating.set_overall(
                        5.0, '##### {0}'.format(domain))
                    rating += domain_header_rating
                    has_announced_overall = True

                category_rating.set_overall(
                    5.0, _local('TEXT_USED_{0}'.format(
                        category.upper())).format(', '.join(item[category].keys())))
                rating += category_rating
        if category == 'cms' and category in item:
            found_cms = True

    if not has_security:
        category_rating = Rating(
            _, review_show_improvements_only)
        category_rating.set_overall(5.0)
        category_rating.set_integrity_and_security(5.0)
        rating += category_rating

    return (found_cms, rating)


def convert_item_to_domain_data(data):
    result = {}

    for item in data:
        domain_item = None
        if item['domain'] not in result:
            domain_item = {}
        else:
            domain_item = result[item['domain']]

        category = item['category']
        name = item['name']
        if name == '?':
            continue
        version = item['version']
        if version == None:
            version = '?'
        precision = item['precision']

        if category not in domain_item:
            domain_item[category] = {}
        if name not in domain_item[category]:
            domain_item[category][name] = {}
        if version not in domain_item[category][name]:
            domain_item[category][name][version] = {
                'name': name, 'precision': precision
            }
            if 'github-owner' in item:
                domain_item[category][name][version]['github-owner'] = item['github-owner']
            if 'github-repo' in item:
                domain_item[category][name][version]['github-repo'] = item['github-repo']
            if 'latest-version' in item:
                domain_item[category][name]['latest-version'] = item['latest-version']
            if 'is-latest-version' in item:
                domain_item[category][name]['is-latest-version'] = item['is-latest-version']

        if domain_item[category][name][version]['precision'] < precision:
            obj = {}
            obj['name'] = name
            obj['precision'] = precision
            if 'github-owner' in item:
                obj['github-owner'] = item['github-owner']
            if 'github-repo' in item:
                obj['github-repo'] = item['github-repo']
            if 'latest-version' in item:
                domain_item[category][name]['latest-version'] = item['latest-version']
            if 'is-latest-version' in item:
                domain_item[category][name]['is-latest-version'] = item['is-latest-version']
            domain_item[category][name][version] = obj

        result[item['domain']] = domain_item
    return result


def enrich_data(data, orginal_domain, result_folder_name, rules):

    cms = None
    # matomo = None
    testing = {}

    tmp_list = list()

    for item in data:
        # if item['domain'] != orginal_domain:
        #     continue
        if item['category'] == 'cms':
            cms = item['name']

        if item['category'] == 'test':
            testing[item['name']] = False

        if item['precision'] >= 0.5 and (item['category'] == 'os' or item['category'] == 'webserver' or item['category'] == 'cms'):
            if item['version'] != None:
                tmp_list.append(get_default_info(
                    item['url'], 'enrich', item['precision'], 'security', 'screaming.{0}'.format(item['category']), None))
            else:
                tmp_list.append(get_default_info(
                    item['url'], 'enrich', item['precision'], 'security', 'talking.{0}'.format(item['category']), None))

        # matomo = enrich_data_from_matomo(matomo, tmp_list, item)
        enrich_data_from_github_repo(tmp_list, item)
        enrich_data_from_javascript(tmp_list, item, rules)
        enrich_data_from_videos(tmp_list, item, result_folder_name)
        enrich_data_from_images(tmp_list, item, result_folder_name)
        enrich_data_from_github_advisory_database(
            tmp_list, item, result_folder_name)

    data.extend(tmp_list)

    if len(testing) > 0:
        raw_data['test'][orginal_domain] = {
            'cms': cms,
            'test': testing
        }

    return data


def enrich_data_from_github_advisory_database(tmp_list, item, result_folder_name):
    # https://github.com/github/advisory-database
    return


def enrich_data_from_github_repo(tmp_list, item):
    # replace 'name' that maches if-cases below and replace them with new.
    # we are doing this both for more correct name but also consolidating names
    if item['name'] == 'jquery-javascript-library':
        item['name'] = 'jquery'
    elif item['name'] == 'jquery-ui-core' or item['name'] == 'query-ui-widget' or item['name'] == 'jquery-ui-position' or item['name'] == 'jquery-ui-menu' or item['name'] == 'jquery-ui-autocomplete' or item['name'].startswith('jquery-ui-'):
        item['name'] = 'jquery-ui'
    elif item['name'] == 'jquery migrate' or item['name'] == 'jquery.migrate':
        item['name'] = 'jquery-migrate'
    elif item['name'] == 'sizzle-css-selector-engine':
        item['name'] = 'sizzle'
    elif item['name'] == 'javascript cookie' or item['name'] == 'javascript.cookie' or item['name'] == 'javascript-cookie':
        item['name'] = 'js-cookie'

    github_ower = None
    github_repo = None
    github_security_label = None
    github_release_source = 'tags'

    if item['name'] == 'jquery':
        github_ower = 'jquery'
        github_repo = 'jquery'
    elif item['name'] == 'jquery-ui':
        github_ower = 'jquery'
        github_repo = 'jquery-ui'
    elif item['name'] == 'jquery-migrate':
        github_ower = 'jquery'
        github_repo = 'jquery-migrate'
    elif item['name'] == 'sizzle':
        github_ower = 'jquery'
        github_repo = 'sizzle'
    elif item['name'] == 'js-cookie':
        github_ower = 'js-cookie'
        github_repo = 'js-cookie'
    elif item['name'] == 'requirejs':
        github_ower = 'requirejs'
        github_repo = 'requirejs'
    elif item['name'] == 'vue-devtools':
        github_ower = 'vuejs'
        github_repo = 'devtools'
    elif item['name'] == 'eslint':
        github_ower = 'eslint'
        github_repo = 'eslint'
    elif item['name'] == 'uuid':
        github_ower = 'uuidjs'
        github_repo = 'uuid'
    elif item['name'] == 'chart':
        github_ower = 'chartjs'
        github_repo = 'Chart.js'
    elif item['name'] == 'chartjs-plugin-datalabels':
        github_ower = 'chartjs'
        github_repo = 'chartjs-plugin-datalabels'
    elif item['name'] == 'chartjs-plugin-deferred':
        github_ower = 'chartjs'
        github_repo = 'chartjs-plugin-deferred'
    elif item['name'] == 'css-element-queries':
        github_ower = 'marcj'
        github_repo = 'css-element-queries'
    elif item['name'] == 'modernizr':
        github_ower = 'Modernizr'
        github_repo = 'Modernizr'
    elif item['name'] == 'core-js':
        github_ower = 'zloirock'
        github_repo = 'core-js'
    elif item['name'] == 'vue':
        github_ower = 'vuejs'
        github_repo = 'vue'
    elif item['name'] == 'vuex':
        github_ower = 'vuejs'
        github_repo = 'vuex'
    elif item['name'] == 'vue-router':
        github_ower = 'vuejs'
        github_repo = 'vue-router'
    elif item['name'] == 'react':
        github_ower = 'facebook'
        github_repo = 'react'
    elif item['name'] == 'choices':
        github_ower = 'jshjohnson'
        github_repo = 'Choices'
    elif item['name'] == 'nginx':
        github_ower = 'nginx'
        github_repo = 'nginx'
    elif item['name'] == 'matomo':
        github_ower = 'matomo-org'
        github_repo = 'matomo'
        github_security_label = 'c: Security'
    elif item['name'] == 'bootstrap':
        github_ower = 'twbs'
        github_repo = 'bootstrap'
        github_release_source = 'releases'
    elif 'github-owner' in item and 'github-repo' in item:
        github_ower = item['github-owner']
        github_repo = item['github-repo']

    if github_ower == None:
        return
    if github_repo == None:
        return

    if 'github-owner' not in item:
        item['github-owner'] = github_ower
    if 'github-repo' not in item:
        item['github-repo'] = github_repo

    github_info = get_github_repository_info(
        github_ower, github_repo)

    # TODO: THIS MUST BE LOOKED AT FROM A 'COMPUTER BREACH' ARGUMENT,
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

    newer_versions = []
    version_verified = False
    if item['version'] is not None:
        (version_verified, newer_versions) = get_github_project_versions(
            github_ower, github_repo, github_release_source, github_security_label, item['version'])

    has_more_then_one_newer_versions = len(newer_versions) > 0

    precision = 0.8
    info = get_default_info(
        item['url'], 'enrich', precision, item['category'], item['name'], item['version'])

    if version_verified:
        info['precision'] = precision = 0.9
        if has_more_then_one_newer_versions:
            info['latest-version'] = newer_versions[0]['name']
            info['is-latest-version'] = False
        else:
            info['is-latest-version'] = True
            info['latest-version'] = item['version']

    if github_info['license'] != None:
        # https://spdx.org/licenses/
        tmp_list.append(get_default_info(
            item['url'], 'enrich', 0.9, 'license', github_info['license'], None))
        info['license'] = github_info['license']

    if len(github_info['tech']) > 0:
        for name in github_info['tech']:
            tmp_list.append(get_default_info(
                item['url'], 'enrich', 0.9, 'tech', name, None))

    tmp_list.append(info)

    if has_more_then_one_newer_versions:
        has_more_then_10_newer_versions = len(newer_versions) > 10
        has_more_then_25_newer_versions = len(newer_versions) > 25
        has_more_then_50_newer_versions = len(newer_versions) > 50
        if has_more_then_50_newer_versions:
            tmp_list.append(get_default_info(
                item['url'], 'enrich', precision, 'security', 'screaming.js.not-latest', None))
        elif has_more_then_25_newer_versions:
            tmp_list.append(get_default_info(
                item['url'], 'enrich', precision, 'security', 'talking.js.not-latest', None))
        elif has_more_then_10_newer_versions:
            tmp_list.append(get_default_info(
                item['url'], 'enrich', precision, 'security', 'whisper.js.not-latest', None))
        else:
            tmp_list.append(get_default_info(
                item['url'], 'enrich', precision, 'security', 'guide.js.not-latest', None))
        # is_security_related = False
        # for version_info in newer_versions:
        #     if 'fixes-security' in version_info:
        #         is_security_related = is_security_related or version_info['fixes-security']

        # if is_security_related:
        #     tmp_list.append(get_default_info(
        #         item['url'], 'enrich', precision, 'security', 'screaming.js.security-issues', None))
        #     tmp_list.append(get_default_info(
        #         item['url'], 'enrich', precision, 'security', 'screaming.js.not-latest', None))
        # else:
        #     tmp_list.append(get_default_info(
        #         item['url'], 'enrich', precision, 'security', 'guide.js.not-latest', None))

    return


def get_github_repository_info(owner, repo):
    repo_content = httpRequestGetContent(
        'https://api.github.com/repos/{0}/{1}'.format(owner, repo))

    info_dict = {}

    from distutils.version import LooseVersion

    github_info = json.loads(repo_content)

    # Get license from github repo ("license.spdx_id") info: https://api.github.com/repos/matomo-org/matomo
    # for example: MIT, GPL-3.0
    info_dict['license'] = None
    if 'license' in github_info and github_info['license'] != None and 'spdx_id' in github_info['license']:
        license = github_info['license']['spdx_id'].lower()
        if 'noassertion' != license:
            info_dict['license'] = license

    techs = list()
    # Get tech from github repo ("language") info: https://api.github.com/repos/matomo-org/matomo
    # for example: php, JavaScript (js), C
    if 'language' in github_info and github_info['language'] != None:
        lang = github_info['language'].lower()
        if 'javascript' in lang:
            lang = 'js'
        add_tech_if_interesting(techs, lang)
        # info_dict['language'] = lang
    # else:
    #     info_dict['language'] = None

    # TODO: Get tech from github repo ("topics") info: https://api.github.com/repos/matomo-org/matomo
    # for example: php, mysql
    if 'topics' in github_info and github_info['topics'] != None:
        for topic in github_info['topics']:
            add_tech_if_interesting(techs, topic)

    info_dict['tech'] = techs

    # print('repo:', info_dict)
    return info_dict


def add_tech_if_interesting(techs, topic):
    tech = topic.lower()
    if 'js' == tech or 'javascript' == tech:
        techs.append('js')
    elif 'c' == tech or 'php' == tech or 'mysql' == tech or 'typescript' == tech:
        techs.append(tech)
    elif 'sass' == tech or 'scss' == tech:
        techs.append(tech)
    # else:
    #     print('# TOPIC', tech)


def get_github_project_versions(owner, repo, source, security_label, current_version):
    versions_content = httpRequestGetContent(
        'https://api.github.com/repos/{0}/{1}/{2}?state=closed&per_page=100'.format(owner, repo, source))

    versions = list()
    versions_dict = {}

    from distutils.version import LooseVersion

    version_info = json.loads(versions_content)
    for version in version_info:
        if source == 'milestones':
            id_key = 'number'
            name_key = 'title'
            date_key = 'closed_at'
        elif source == 'tags':
            id_key = None
            name_key = 'name'
            date_key = None
        else:
            id_key = 'id'
            # we uses tag_name instead of name as bootstrap is missing "name" for some releases
            name_key = 'tag_name'
            date_key = 'published_at'

        if name_key not in version:
            continue

        id = None
        name = None
        name2 = None
        date = None

        if id_key in version:
            id = '{0}'.format(version[id_key])

        if date_key in version:
            date = version[date_key]

        # NOTE: We do this to handle jquery dual release format "1.12.4/2.2.4"
        regex = r"^([v]|release\-){0,1}(?P<name>[0-9\\.]+)([\\\/](?P<name2>[0-9\\.]+)){0,1}"
        matches = re.finditer(regex, version[name_key])
        for matchNum, match in enumerate(matches, start=1):
            name = match.group('name')
            name2 = match.group('name2')

        if name == None:
            continue

        versions.append(name)
        versions_dict[name] = {
            'name': name,
            'date': date,
            'id': id
        }

        if name2 != None:
            versions.append(name2)
            versions_dict[name2] = {
                'name': name2,
                'date': date,
                'id': id
            }

    versions = sorted(versions, key=LooseVersion, reverse=True)

    newer_versions = list()
    version_found = False
    for version in versions:
        if current_version == version:
            version_found = True
            break
        else:
            if security_label != None:
                # https://api.github.com/repos/matomo-org/matomo/milestones/163/labels
                version_label_data = httpRequestGetContent(
                    'https://api.github.com/repos/{0}/{1}/{2}/{3}/labels'.format(owner, repo, source, versions_dict[version]['id']))
                labels = json.loads(version_label_data)

                fixes_security = False
                for label in labels:
                    if 'name' in label and label['name'] == security_label:
                        fixes_security = True

                versions_dict[version]['fixes-security'] = fixes_security
            newer_versions.append(versions_dict[version])

    if not version_found:
        return (version_found, [])
    else:
        return (version_found, newer_versions)


def enrich_data_from_javascript(tmp_list, item, rules):
    if use_stealth:
        return
    if item['category'] != 'js':
        return
    if 'license-txt' in item:
        content = httpRequestGetContent(
            item['license-txt'].lower(), allow_redirects=True)
        tmp = lookup_response_content(
            item['license-txt'].lower(), item['mime-type'], content, rules)
        tmp_list.extend(tmp)
    if item['version'] == None:
        return

    # TODO: Check if we can run custom javascript in sitespeed.io to add below tests
    # jQuery.fn.jquery = '1.9.1'
    # Modernizr._version = '3.4.0'
    # window['__core-js_shared__'].versions

    # TODO: We should look at wordpress plugins specifically as they are widely used and we know they are often used in attacks


def enrich_data_from_videos(tmp_list, item, result_folder_name, nof_tries=0):
    if use_stealth:
        return
    if item['category'] != 'video':
        return

    if item['name'] != 'mp4':
        return

    # TODO: Consider if we should read metadata from video


def enrich_data_from_images(tmp_list, item, result_folder_name, nof_tries=0):
    if use_stealth:
        return
    if item['category'] != 'img':
        return

    if item['name'] == 'svg':
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
                    item['url'], 'enrich', item['precision'], 'security', 'whisper.{0}.app'.format(item['category']), None))

            if tech_version != None:
                tech_version = tech_version.lower()
                tmp_list.append(get_default_info(
                    item['url'], 'content', 0.6, 'img.software', tech_name, tech_version))
                tmp_list.append(get_default_info(
                    item['url'], 'enrich', 0.8, 'security', 'whisper.{0}.app'.format(item['category']), None))
    else:
        # print('url', item['url'])
        cache_key = '{0}.cache.{1}'.format(
            hashlib.sha512(item['url'].encode()).hexdigest(), item['name'])
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
                            item['url'], 'enrich', item['precision'], 'security', 'whisper.{0}.app'.format(item['category']), None))

                    if tech_version != None:
                        tech_version = tech_version.lower()
                        tmp_list.append(get_default_info(
                            item['url'], 'content', 0.6, 'img.software', tech_name, tech_version))
                        tmp_list.append(get_default_info(
                            item['url'], 'enrich', 0.8, 'security', 'whisper.{0}.app'.format(item['category']), None))

                    if os_name != None:
                        os_name = os_name.lower()
                        tmp_list.append(get_default_info(
                            item['url'], 'content', 0.6, 'img.os', os_name, None))
                        tmp_list.append(get_default_info(
                            item['url'], 'enrich', 0.8, 'security', 'whisper.{0}.os'.format(item['category']), None))
            elif 'artist' == tag_name or 'xpauthor' == tag_name:
                tmp_list.append(get_default_info(
                    item['url'], 'enrich', 0.8, 'security', 'info.{0}.person'.format(item['category']), None))
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
                            item['url'], 'enrich', item['precision'], 'security', 'whisper.{0}.device'.format(item['category']), None))

                    if tech_version != None:
                        tech_version = tech_version.lower()
                        device_version = tech_version
                        # tmp_list.append(get_default_info(
                        #     item['url'], 'content', 0.6, 'img.os', tech_name, tech_version))
                        tmp_list.append(get_default_info(
                            item['url'], 'enrich', 0.8, 'security', 'whisper.{0}.device'.format(item['category']), None))

                    if os_name != None:
                        os_name = os_name.lower().strip()
                        tmp_list.append(get_default_info(
                            item['url'], 'content', 0.6, 'img.os', os_name, None))
                        tmp_list.append(get_default_info(
                            item['url'], 'enrich', 0.8, 'security', 'whisper.{0}.os'.format(item['category']), None))
            elif 'model' == tag_name:
                tmp_list.append(get_default_info(
                    item['url'], 'enrich', 0.8, 'security', 'info.{0}.model'.format(item['category']), None))
                device_version = tag_data.lower().strip()
            elif 'gpsinfo' == tag_name:
                tmp_list.append(get_default_info(
                    item['url'], 'enrich', 0.8, 'security', 'info.{0}.location'.format(item['category']), None))
            # elif 'resolutionunit' == tag_name or 'exifoffset' == tag_name or 'xresolution' == tag_name or 'yresolution' == tag_name or 'orientation' == tag_name or 'imagewidth' == tag_name or 'imagelength' == tag_name or 'bitspersample' == tag_name or 'samplesperpixel' == tag_name or 'compression' == tag_name or 'datetime' == tag_name or 'copyright' == tag_name or 'photometricinterpretation' == tag_name or 'unknown_59932' == tag_name:
            #     a = 1
            # else:
            #     print(f"\t{tag_name:25}: {tag_data}")

        if device_name != None or device_version != None:
            if device_name != None:
                device_name = device_name.lower().strip()
            if device_name != None and device_version == None:
                tmp_list.append(get_default_info(
                    item['url'], 'enrich', 0.5, 'img.device', device_name, None))
                tmp_list.append(get_default_info(
                    item['url'], 'enrich', item['precision'], 'security', 'whisper.{0}.device'.format(item['category']), None))

            if device_name != None and device_version != None:
                device_version = device_version.lower()
                if device_name != None:
                    device_version = device_version.replace(device_name, '')
                tmp_list.append(get_default_info(
                    item['url'], 'content', 0.6, 'img.device', device_name, device_version))
                tmp_list.append(get_default_info(
                    item['url'], 'enrich', 0.8, 'security', 'whisper.{0}.device'.format(item['category']), None))
            # print('device', device_name, device_version)


def identify_software(filename, origin_domain, rules):
    data = list()

    # Fix for content having unallowed chars
    json_content = get_sanitized_file_content(filename)
    if True:
        har_data = json.loads(json_content)
        if 'log' in har_data:
            har_data = har_data['log']
        for entry in har_data["entries"]:
            req = entry['request']
            res = entry['response']
            req_url = req['url']

            url_data = lookup_request_url(req_url, rules, origin_domain)
            if url_data != None or len(url_data) > 0:
                data.extend(url_data)

            if 'headers' in res:
                headers = res['headers']
                header_data = lookup_response_headers(
                    req_url, headers, rules, origin_domain)
                if header_data != None or len(header_data) > 0:
                    data.extend(header_data)

            if 'content' in res and 'text' in res['content']:
                response_content = res['content']['text']
                response_mimetype = res['content']['mimeType']
                content_data = lookup_response_content(
                    req_url, response_mimetype, response_content, rules)
                if content_data != None or len(content_data) > 0:
                    data.extend(content_data)
            else:
                response_mimetype = res['content']['mimeType']
                mimetype_data = lookup_response_mimetype(
                    req_url, response_mimetype)
                if mimetype_data != None or len(mimetype_data) > 0:
                    data.extend(mimetype_data)

            # TODO: Check for https://docs.2sxc.org/index.html ?
    return data


def lookup_response_mimetype(req_url, response_mimetype):
    data = list()

    if raw_data['mime-types']['use']:
        raw_data['mime-types'][response_mimetype] = 'svg' in response_mimetype or 'mp4' in response_mimetype or 'webp' in response_mimetype or 'png' in response_mimetype or 'jpg' in response_mimetype or 'jpeg' in response_mimetype or 'bmp' in response_mimetype

    if 'mp4' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        # look at: https://www.handinhandsweden.se/wp-content/uploads/se/2022/11/julvideo-startsida.mp4
        # that has videolan references and more interesting stuff
        data.append(get_default_info(
            req_url, 'mimetype', 0.8, 'video', 'mp4', None))

    if 'webp' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        data.append(get_default_info(
            req_url, 'mimetype', 0.8, 'img', 'webp', None))
    elif 'png' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        data.append(get_default_info(
            req_url, 'mimetype', 0.8, 'img', 'png', None))
    elif 'jpg' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        data.append(get_default_info(
            req_url, 'mimetype', 0.8, 'img', 'jpg', None))
    elif 'jpeg' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        data.append(get_default_info(
            req_url, 'mimetype', 0.8, 'img', 'jpeg', None))
    elif 'bmp' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        data.append(get_default_info(
            req_url, 'mimetype', 0.8, 'img', 'bmp', None))

    return data


def lookup_response_content(req_url, response_mimetype, response_content, rules):
    data = list()

    if 'contents' not in rules:
        return data

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

        req_url = req_url.lower()

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

                    data.append(info)
                    is_found = True
                elif raw_data['contents']['use'] and not is_found:
                    raw_data['contents'][match.group('debug')] = hostname

    return data


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

    result['url'] = url
    result['method'] = method
    result['precision'] = precision
    result['category'] = key
    result['name'] = name
    result['version'] = version

    return result


def lookup_request_url(req_url, rules, origin_domain):
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

        req_url = req_url.lower()

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
                    data.append(get_default_info(
                        req_url, 'url', precision, category, name, version, domain))
                    is_found = True
                if raw_data['urls']['use'] and not is_found:
                    raw_data['urls'][req_url] = is_found

    return data


def lookup_response_headers(req_url, headers, rules, origin_domain):
    data = list()

    for header in headers:
        header_name = header['name'].lower()
        header_value = header['value'].lower()

        if raw_data['headers']['use']:
            raw_data['headers'][header_name] = header_value

        # print('header', header_name, header_value)
        tmp_data = lookup_response_header(
            req_url, header_name, header_value, rules, origin_domain)
        if len(tmp_data) != 0:
            data.extend(tmp_data)
    return data


def lookup_response_header(req_url, header_name, header_value, rules, origin_domain):
    data = list()

    if 'headers' not in rules:
        return data

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

        req_url = req_url.lower()

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
                    data.append(get_default_info(
                        req_url, 'header', precision, category, name, version))
                    is_found = True
                elif raw_data['headers']['use'] and not is_found:
                    raw_data['headers'][match.group('debug')] = hostname

    return data


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
