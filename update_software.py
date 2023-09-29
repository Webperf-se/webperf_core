# -*- coding: utf-8 -*-
import sys
import getopt
import config
import gettext
import utils
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import shutil
import sys
import socket
import ssl
import json
import time
import requests
import urllib  # https://docs.python.org/3/library/urllib.parse.html
import uuid
import re
from bs4 import BeautifulSoup
import dns.resolver
import config
import IP2Location
import os
from tests.utils import *
import packaging.version

try:
    github_adadvisory_database_path = config.software_github_adadvisory_database_path
except:
    # If software_github_adadvisory_database_path variable is not set in config.py this will be the default
    github_adadvisory_database_path = None


def main(argv):
    """
    WebPerf Core - Software update
    """

    update_licenses()
    update_software_info()


def update_software_info():
    collection = get_softwares()
    # print('software', collection)

    if 'aliases' not in collection:
        collection['aliases'] = {}

    if 'softwares' not in collection:
        collection['softwares'] = {}

    for key in collection['aliases'].keys():
        if collection['aliases'][key] not in collection['softwares']:
            print('alias', key, "is invalid")
        # else:
        #     print('alias', key, "=", collection['aliases'][key])


    index = 0
    for key in collection['softwares'].keys():
        # if index > 15:
        #     break
        # print('software', key)
        item = collection['softwares'][key]

        github_ower = None
        github_repo = None
        github_security = None
        github_release_source = 'tags'

        if 'github-owner' in collection['softwares'][key]:
            github_ower = collection['softwares'][key]['github-owner']
        if 'github-repo' in collection['softwares'][key]:
            github_repo = collection['softwares'][key]['github-repo']

        if 'github-security' in collection['softwares'][key]:
            github_security = collection['softwares'][key]['github-security']
        
        versions = []
        if github_ower != None:
            set_github_repository_info(item, github_ower, github_repo)
            # TODO: Git Archived status for repo and warn for it if it is.
            versions = get_github_versions(github_ower, github_repo, github_release_source, github_security)
        if key == 'iis':
            versions = get_iis_versions()
            versions = extend_versions_for_iis(versions)
        elif key == 'windows-server':
            versions = get_windows_versions()
        elif key == 'apache':
            versions = get_apache_httpd_versions()
            versions = extend_versions_for_apache_httpd(versions)
        elif key == 'nginx':
            versions = extend_versions_for_nginx(versions)
        elif key == 'php':
            versions = get_php_versions()
            versions = extend_versions_for_php(versions)
        versions = extend_versions_from_github_advisory_database(key, versions)

        # print(key, len(versions))
        if len(versions) > 0:
            collection['softwares'][key]['versions'] = versions

        set_softwares(collection)
        index += 1


def update_licenses():
    print('updates licesences used in SAMPLE-software-rules.json')

    # https://spdx.org/licenses/
    raw_data = httpRequestGetContent(
        'https://spdx.org/licenses/')

    regex = r'<code property="spdx:licenseId">(?P<licenseId>[^<]+)<\/code'
    matches = re.finditer(
        regex, raw_data, re.MULTILINE)

    licenses = list()
    for matchNum, match_vulnerable in enumerate(matches, start=1):
        license_id = match_vulnerable.group('licenseId')
        licenses.append(license_id.replace('.', '\\.').replace('-', '\\-').replace('+', '\\+'))

    rules = get_software_rules()
    if 'contents' not in rules:
        return
    
    for content_rule in rules['contents']:
        if 'match' not in content_rule:
            continue

        if '?P<license>' not in content_rule['match']:
            continue

        content = content_rule['match']
        regex = r'(?P<licenses>\?P\<license\>\([^\)]*\))'
        matches = re.finditer(
            regex, content, re.MULTILINE)
        for matchNum, match_vulnerable in enumerate(matches, start=1):
            match_content = match_vulnerable.group('licenses')
            content_rule['match'] = content_rule['match'].replace(match_content, '?P<license>({0})'.format('|'.join(licenses)))

    save_software_rules(rules)

def get_software_rules():
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep)

    file_path = '{0}{1}SAMPLE-software-rules.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        print("ERROR: No SAMPLE-software-rules.json file found!")
        return

    with open(file_path) as json_rules_file:
        rules = json.load(json_rules_file)
    return rules
    
def save_software_rules(rules):
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep)

    file_path = '{0}{1}SAMPLE-software-rules.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        print("ERROR: No software-rules.json file found!")
        return

    with open(file_path, 'w') as outfile:
        json.dump(rules, outfile, indent=4)
    return rules
    


def extend_versions_for_nginx(versions):
    for version in versions.keys():
        print('extend_versions', 'nginx', version)
        result = list()

        if version == None:
            return result

        # https://nginx.org/en/security_advisories.html
        raw_data = httpRequestGetContent(
            'https://nginx.org/en/security_advisories.html')

        regex_vulnerables = r'((?P<advisory>[^"]+)">Advisory<\/a><br>){0,1}<a href="(?P<more_info>[^"]+)">(?P<cve>CVE-[0-9]{4}\-[0-9]+)<\/a><br>Not vulnerable:(?P<safe>[ 0-9\.+,]+)<br>Vulnerable:(?P<unsafe>[ 0-9\.\-+,]+)'
        matches_vulnerables = re.finditer(
            regex_vulnerables, raw_data, re.MULTILINE)

        for matchNum, match_vulnerable in enumerate(matches_vulnerables, start=1):
            is_match = False
            cve = match_vulnerable.group('cve')
            more_info_url = match_vulnerable.group('more_info')
            safe_versions = match_vulnerable.group('safe')
            unsafe_versions = match_vulnerable.group('unsafe')
            advisory_url = match_vulnerable.group('advisory')

            # 0.6.18-1.9.9
            # 1.1.4-1.2.8, 1.3.9-1.4.0
            unsafe_sections = unsafe_versions.split(',')
            safe_sections = safe_versions.split(',')
            for section in unsafe_sections:
                ranges = section.split('-')
                if len(ranges) != 2:
                    continue
                start_version = ranges[0].strip()
                end_version = ranges[1].strip()

                lversion = packaging.version.Version(version)
                lstart_version = packaging.version.Version(start_version)
                lend_version = packaging.version.Version(end_version)

                if lversion >= lstart_version and lversion < lend_version:
                    is_match = True

            if is_match:
                # TODO: REMOVE FIXED VERSIONS
                # 1.23.2+, 1.22.1+
                for safe_section in safe_sections:
                    safe_version = safe_section.strip()
                    if '+' not in safe_section:
                        continue
                    safe_version = safe_version.strip('+')

                    lsafe_version = packaging.version.Version(safe_version)

                    if lversion == lsafe_version:
                        is_match = False

                    lversion_specificity = len(lversion.release)

                    if lversion_specificity == 3 and lversion_specificity == len(lsafe_version.release):
                        # is same branch and is equal or greater then safe (fixed) version?
                        if lversion.release[0] == lsafe_version.release[0] and lversion.release[1] == lsafe_version.release[1] and lversion.release[2] >= lsafe_version.release[2]:
                            is_match = False

            if is_match:
                versions[version].append(cve)

    return versions


def extend_versions_for_iis(versions):
    for version in versions.keys():
        print('extend_versions', 'iis', version)
        # https://www.cvedetails.com/vulnerability-list.php?vendor_id=26&product_id=3427&page=1
        raw_data = httpRequestGetContent(
            'https://www.cvedetails.com/vulnerability-list.php?vendor_id=26&product_id=3427&page=1')

        regex_vulnerables = r'href="(?P<url>[^"]+)"[^>]+>(?P<cve>CVE-[0-9]{4}\-[0-9]+)'
        matches_vulnerables = re.finditer(
            regex_vulnerables, raw_data, re.MULTILINE)

        for matchNum, match_vulnerable in enumerate(matches_vulnerables, start=1):
            is_match = False
            cve = match_vulnerable.group('cve')
            url = 'https://www.cvedetails.com{0}'.format(
                match_vulnerable.group('url'))
            raw_cve_data = httpRequestGetContent(url)
            regex_version = r'<td>[ \t\r\n]*(?P<version>[0-9]+\.[0-9]+)[ \t\r\n]*<\/td>'
            matches_version = re.finditer(
                regex_version, raw_cve_data, re.MULTILINE)
            for matchNum, match_version in enumerate(matches_version, start=1):
                cve_affected_version = match_version.group('version')
                if cve_affected_version == version:
                    is_match = True

            if is_match:
                versions[version].append(cve)
                versions[version] = sorted(versions[version], reverse=True)

    return versions

def extend_versions_for_php(versions):
    raw_data = httpRequestGetContent(
        'https://www.php.net/eol.php')
    regex = r'(?P<date>\([a-zA-Z0-9 ,]+\))<\/em>[\r\n\t]*<\/td>[\r\n\t]*<td>[\r\n\t]*<a [^>]+>[\r\n\t]*(?P<version>[0-9\.]+)'
    matches = re.finditer(
        regex, raw_data, re.MULTILINE)

    end_of_life_branches = {}
    for matchNum, match in enumerate(matches, start=1):
        is_match = False
        end_of_life_branch = None
        end_of_life_version = match.group('version')
        end_of_life_dating = match.group('date')

        if len(end_of_life_version) > 3:
            end_of_life_branch = end_of_life_version[:3]
            end_of_life_branches[end_of_life_branch] = 'END-OF-LIFE {0}'.format(end_of_life_dating)

    for version in versions.keys():
        print('extend_versions', 'php', version)
        if len(version) > 3:
            version_branch = version[:3]
            if version_branch in end_of_life_branches:
                versions[version].append(end_of_life_branches[version_branch])
                versions[version] = sorted(versions[version], reverse=True)

    return versions

def extend_versions_for_apache_httpd(versions):
    for version in versions.keys():
        print('extend_versions', 'apache', version)
        raw_data = httpRequestGetContent(
            'https://httpd.apache.org/security/vulnerabilities_24.html')

        regex_version = r"<h1 id=\"(?P<version>[0-9\.]+)\">"
        version_sections = re.split(regex_version, raw_data)

        current_version = None
        for version_section in version_sections:
            reg_version_validator = r"^(?P<version>[0-9\.]+)$"
            if re.match(reg_version_validator, version_section) == None:
                if current_version != None:
                    current_cve = None
                    regex_cve = r"<dt><h3 id=\"(?P<cve>CVE-[0-9]{4}\-[0-9]+)"
                    cve_sections = re.split(regex_cve, version_section)
                    for cve_section in cve_sections:
                        regex_cve_validator = r"^(?P<cve>CVE-[0-9]{4}\-[0-9]+)$"
                        if re.match(regex_cve_validator, cve_section) == None:
                            if current_cve != None:
                                is_match = False
                                has_rules = False
                                ranges = list()
                                regex_ranges = r'Affects<\/td><td class="cve-value">(?P<range>[0-9\., &glt;=!]+)'
                                matches_range = re.finditer(
                                    regex_ranges, cve_section, re.MULTILINE)

                                for matchNum, match_range in enumerate(matches_range, start=1):
                                    range_data = match_range.group('range')
                                    for rnge in range_data.split(','):
                                        tmp = rnge.strip()
                                        if '&' in tmp or '=' in tmp or '!' in tmp:
                                            if not has_rules:
                                                # Set is_match to true and all the rules can do is to remove it from it..
                                                is_match = True
                                                has_rules = True
                                            regex_version_expression = r'(?P<expression>[,&glt;=!]+)(?P<version>[0-9\.]+)'
                                            matches_version_expression = re.finditer(
                                                regex_version_expression, tmp, re.MULTILINE)
                                            for matchNum, match_version_expression in enumerate(matches_version_expression, start=1):
                                                tmp_expression = match_version_expression.group(
                                                    'expression')
                                                tmp_version = match_version_expression.group(
                                                    'version')
                                                # All versions below this version
                                                # <=2.4.48
                                                # Versions between 2.4.17 and 2.4.48 (including 2.4.48)
                                                # <=2.4.48, !<2.4.17
                                                # Versions between 2.4.7 and 2.4.51
                                                # >=2.4.7, <=2.4.51
                                                lversion = packaging.version.Version(version)
                                                ltmp_version = packaging.version.Version(
                                                    tmp_version)

                                                if '!&lt;=' in tmp_expression and lversion <= ltmp_version:
                                                    is_match = False
                                                elif '!&gt;=' in tmp_expression and lversion >= ltmp_version:
                                                    is_match = False
                                                elif '!&lt;' in tmp_expression and lversion < ltmp_version:
                                                    is_match = False
                                                elif '!&gt;' in tmp_expression and lversion > ltmp_version:
                                                    is_match = False
                                                elif '&lt;=' in tmp_expression and lversion > ltmp_version:
                                                    is_match = False
                                                elif '&gt;=' in tmp_expression and lversion < ltmp_version:
                                                    is_match = False
                                                elif '&lt;' in tmp_expression and lversion >= ltmp_version:
                                                    is_match = False
                                                elif '&gt;' in tmp_expression and lversion <= ltmp_version:
                                                    is_match = False

                                        else:
                                            # Exactly this version
                                            # 2.4.49
                                            # Only listed versions
                                            # 2.4.46, 2.4.43, 2.4.41, 2.4.39, 2.4.38, 2.4.37, 2.4.35, 2.4.34, 2.4.33, 2.4.29, 2.4.28, 2.4.27, 2.4.26, 2.4.25, 2.4.23, 2.4.20, 2.4.18, 2.4.17, 2.4.16, 2.4.12, 2.4.10, 2.4.9, 2.4.7, 2.4.6, 2.4.4, 2.4.3, 2.4.2, 2.4.1, 2.4.0
                                            ranges.append(tmp)

                                if version in ranges:
                                    is_match = True

                                if is_match:
                                    versions[version].append(current_cve)
                                    versions[version] = sorted(versions[version], reverse=True)

                                current_cve = None
                        else:
                            current_cve = cve_section

                    current_version = None
            else:
                current_version = version_section        
    return versions

def extend_versions_from_github_advisory_database(software_name, versions):
        print('extend_versions[github]', software_name, 'checking for matching CVE')
        # https://github.com/github/advisory-database

        if github_adadvisory_database_path == None:
            return versions

        root_path = os.path.join(
            github_adadvisory_database_path, 'advisories', 'github-reviewed')
        years = os.listdir(root_path)
        for year in years:
            year_path = os.path.join(root_path, year)
            months = os.listdir(year_path)
            for month in months:
                month_path = os.path.join(year_path, month)
                keys = os.listdir(month_path)
                for key in keys:
                    key_path = os.path.join(
                        year_path, month, key, '{0}.json'.format(key))
                    json_data = None
                    # Sanity check to make sure file exists
                    if not os.path.exists(key_path):
                        continue

                    with open(key_path, 'r', encoding='utf-8') as file:
                        json_data = json.load(file)
                    if json_data == None:
                        continue

                    if 'schema_version' not in json_data:
                        print('ERROR: NO schema version!')
                        continue
                    elif json_data['schema_version'] != '1.4.0' and json_data['schema_version'] != '1.3.0':
                        print('ERROR: Unsupported schema version! Assumed 1.3.0 or 1.4.0 but got {0}'.format(
                            json_data['schema_version']))
                        continue

                    if 'affected' not in json_data:
                        continue

                    for affected in json_data['affected']:
                        if 'package' not in affected:
                            continue
                        if 'ecosystem' not in affected['package']:
                            continue

                        ecosystem = affected['package']['ecosystem']

                        if 'npm' == ecosystem:
                            is_matching = False
                            has_cve_name = False
                            if software_name == affected['package']['name'] or '{0}.js'.format(software_name) == affected['package']['name']:
                                cve_info = {}

                                nof_aliases = len(json_data['aliases'])
                                if nof_aliases >= 1:
                                    cve_info['name'] = json_data['aliases'][0]
                                    has_cve_name = True
                                    if nof_aliases > 1:
                                        cve_info['aliases'] = json_data['aliases']
                                else:
                                    cve_info['name'] = '{0} vulnerability'.format(
                                        affected['package']['name'])

                                start_version = None
                                end_version = None
                                last_affected_version = None
                                if 'ranges' in affected:
                                    for range in affected['ranges']:
                                        if 'type' in range and range['type'] == 'ECOSYSTEM':
                                            if 'events' in range:
                                                for event in range['events']:
                                                    if 'introduced' in event:
                                                        start_version = event['introduced']
                                                    if 'fixed' in event:
                                                        end_version = event['fixed']
                                                    if 'last_affected' in event:
                                                        last_affected_version = event['last_affected']

                                        else:
                                            print('ERROR: Unknown ecosystem')

                                for version in versions.keys():
                                    print('extend_versions[github]', software_name, version)
                                    # TODO: We should handle exception better here if version(s) is not valid format
                                    if start_version != None and version != None:
                                        lversion = packaging.version.Version(version)
                                        lstart_version = packaging.version.Version(
                                            start_version)
                                        if end_version != None and end_version != '':
                                            lend_version = packaging.version.Version(end_version)
                                            if lversion >= lstart_version and lversion < lend_version:
                                                is_matching = True
                                        elif last_affected_version != None and last_affected_version != '':
                                            l_last_affected_version = packaging.version.Version(
                                                last_affected_version)
                                            if lversion >= lstart_version and lversion <= l_last_affected_version:
                                                is_matching = True
                                        # NOTE: Temporarly(?) removed until https://github.com/github/advisory-database/pull/1807
                                        # is approved and merged
                                        # elif lversion >= lstart_version:
                                        #     is_matching = True

                                    references = list()
                                    if 'references' in json_data:
                                        for reference in json_data['references']:
                                            if 'ADVISORY' in reference['type']:
                                                references.append(reference['url'])
                                                if not has_cve_name:
                                                    index = reference['url'].find(
                                                        'CVE-')
                                                    if index != -1:
                                                        cve_info['name'] = reference['url'][index:]
                                        cve_info['references'] = references
                                    if 'database_specific' in json_data and 'severity' in json_data['database_specific']:
                                        cve_info['severity'] = json_data['database_specific']['severity']

                                    if is_matching:
                                        print('extend_versions[github]', software_name, version, 'MATCHED CVE')
                                        cve_info['version'] = version
                                        if cve_info['name'] not in versions[version]:
                                            versions[version].append(cve_info['name'])
                                            versions[version] = sorted(versions[version], reverse=True)

        return versions

def set_softwares(collection):
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep)
    
    file_path = '{0}{1}data{1}software-sources.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}software-sources.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        print("ERROR: No software-sources.json file found!")

    file_path = file_path.replace('-sources.json', '-full.json')
    print('set_softwares', file_path)

    collection["loaded"] = True
    collection["updated"] = '{0}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    data = json.dumps(collection, indent=4)
    with open(file_path, 'w', encoding='utf-8', newline='') as file:
        file.write(data)
   

def get_softwares():
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep)

    file_path = '{0}{1}data{1}software-sources.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}software-sources.json'.format(dir, os.path.sep)
    if not os.path.isfile(file_path):
        print("ERROR: No software-sources.json file found!")
        return {
            'loaded': False
        }

    print('get_softwares', file_path)

    with open(file_path) as json_file:
        softwares = json.load(json_file)
    return softwares

def add_tech_if_interesting(techs, imgs, topic):
    tech = topic.lower()
    if 'js' == tech or 'javascript' == tech:
        techs.append('js')
    elif 'graphql' == tech or 'mysql' == tech: 
        techs.append(tech)
    elif 'c' == tech or 'c++' == tech or 'php' == tech or 'typescript' == tech or 'es6' == tech:
        techs.append(tech)
    elif 'sass' == tech or 'scss' == tech:
        techs.append(tech)
    elif 'markdown' == tech or 'webgl' == tech or 'font' == tech or 'woff' == tech or 'woff2' == tech or 'video' == tech or 'qrcode' == tech or 'pwa' == tech: 
        techs.append(tech)
    elif 'svg' == tech or 'png' == tech or 'jpg' == tech or 'jpeg' == tech or 'gif' == tech or 'webp' == tech or 'ico' == tech:
        techs.append(tech)
    # else:
    #     print('# TOPIC', tech)

def set_github_repository_info(item, owner, repo):
    repo_content = httpRequestGetContent(
        'https://api.github.com/repos/{0}/{1}'.format(owner, repo))

    github_info = json.loads(repo_content)

    # Get license from github repo ("license.spdx_id") info: https://api.github.com/repos/matomo-org/matomo
    # for example: MIT, GPL-3.0
    item['license'] = None
    if 'license' in github_info and github_info['license'] != None and 'spdx_id' in github_info['license']:
        license = github_info['license']['spdx_id'].lower()
        if 'noassertion' != license:
            item['license'] = license

    techs = list()
    imgs = list()
    # Get tech from github repo ("language") info: https://api.github.com/repos/matomo-org/matomo
    # for example: php, JavaScript (js), C
    if 'language' in github_info and github_info['language'] != None:
        lang = github_info['language'].lower()
        if 'javascript' in lang:
            lang = 'js'
        add_tech_if_interesting(techs, imgs, lang)

    # Get tech from github repo ("topics") info: https://api.github.com/repos/matomo-org/matomo
    # for example: php, mysql
    if 'topics' in github_info and github_info['topics'] != None:
        for topic in github_info['topics']:
            add_tech_if_interesting(techs, imgs, topic)

    techs = list(set(techs))
    if len(techs)> 0:
        techs = sorted(techs)
        item['tech'] = techs

    imgs = list(set(imgs))
    if len(imgs)> 0:
        imgs = sorted(imgs)
        item['img'] = imgs

    # someone has archived the github repo, project should not be used.
    if 'archived' in github_info and github_info['archived'] != None:
        item['archived'] = github_info['archived']

    return

def get_github_versions(owner, repo, source, security_label):
    versions_content = httpRequestGetContent(
        'https://api.github.com/repos/{0}/{1}/{2}?state=closed&per_page=100'.format(owner, repo, source))

    versions = list()
    versions_dict = {}

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
        regex = r"^([v]|release\-){0,1}(?P<name>[0-9\.\-a-zA-Z]+)([\/](?P<name2>[0-9\.\-a-zA-Z]+)){0,1}"
        matches = re.finditer(regex, version[name_key])
        for matchNum, match in enumerate(matches, start=1):
            name = match.group('name')
            name2 = match.group('name2')

        if name == None:
            continue

        try:
            name = name.strip('.')
            name_version = packaging.version.parse(name)
            # Ignore dev and pre releases, for example Matomo 5.0.0-rc3
            if not name_version.is_prerelease:
                versions.append(name)
        except:
            print('ERROR: Unable to parse version for repo: ', owner, repo, 'with value:', name)

        if name2 != None:
            try:
                name2 = name2.strip('.')
                name2_version = packaging.version.parse(name2)
                # Ignore dev and pre releases, for example Matomo 5.0.0-rc3
                if not name2_version.is_prerelease:
                    versions.append(name2)
            except:
                print('ERROR: Unable to parse version for repo: ', owner, repo, 'with value:', name2)

    versions = sorted(versions, key=packaging.version.Version, reverse=True)

    for version in versions:
        versions_dict[version] = []
        if security_label != None:
            # https://api.github.com/repos/matomo-org/matomo/milestones/163/labels
            version_label_data = httpRequestGetContent(
                'https://api.github.com/repos/{0}/{1}/{2}/{3}/labels'.format(owner, repo, source, versions_dict[version]['id']))
            labels = json.loads(version_label_data)

            fixes_security = False
            for label in labels:
                if 'name' in label and label['name'] == security_label:
                    fixes_security = True

            if fixes_security:
                versions_dict[version] = ['fixes security issues']

    return versions_dict

def get_iis_versions():
    # https://learn.microsoft.com/en-us/lifecycle/products/internet-information-services-iis
    content = httpRequestGetContent(
        'https://learn.microsoft.com/en-us/lifecycle/products/internet-information-services-iis')
    regex = r"<td>IIS (?P<version>[0-9\.]+)"
    matches = re.finditer(regex, content, re.MULTILINE)

    versions = list()
    versions_dict = {}

    for matchNum, match in enumerate(matches, start=1):
        name = match.group('version')
        # version fix because source we use are not using the trailing .0 in all cases
        if '.' not in name:
            name = '{0}.0'.format(name)
        versions.append(name)

    versions = sorted(versions, key=packaging.version.Version, reverse=True)
    for version in versions:
        if packaging.version.Version(version) < packaging.version.Version('8.5'):
            versions_dict[version] = ['END-OF-LIFE']
        else:
            versions_dict[version] = []
    return versions_dict

def get_windows_versions():
    # source: https://learn.microsoft.com/en-us/lifecycle/products/export/
    # source: https://learn.microsoft.com/en-us/lifecycle/products/?products=windows&terms=windows%20server&skip=10

    versions_dict = {
        "2016/2019/2022": [],
        "2012 r2": [],
        "2012": ['END-OF-LIFE'],
        "2008 r2": ['END-OF-LIFE'],
        "2008": ['END-OF-LIFE'],
        "2003": ['END-OF-LIFE']
    }

    return versions_dict

def get_php_versions():
    # newer_versions = []
    content = httpRequestGetContent(
        'https://www.php.net/releases/')
    regex = r"<h2>(?P<version>[0-9\.]+)<\/h2>"
    matches = re.finditer(regex, content, re.MULTILINE)

    versions = list()
    versions_dict = {}

    for matchNum, match in enumerate(matches, start=1):
        name = match.group('version')
        try:
            name_version = packaging.version.parse(name)
            # Ignore dev and pre releases, for example Matomo 5.0.0-rc3
            if not name_version.is_prerelease:
                versions.append(name)
        except:
            print('ERROR: Unable to parse version for php for version value ', name)

    versions = sorted(versions, key=packaging.version.Version, reverse=True)
    for version in versions:
        versions_dict[version] = []
    return versions_dict

def get_apache_httpd_versions():
    # newer_versions = []
    content = httpRequestGetContent(
        'https://svn.apache.org/viewvc/httpd/httpd/tags/')
    regex = r"<a name=\"(?P<version>[0-9\.]+(\-[0-9\.\-a-zA-Z]+){0,1})\""
    matches = re.finditer(regex, content, re.MULTILINE)

    versions = list()
    versions_dict = {}

    for matchNum, match in enumerate(matches, start=1):
        name = match.group('version')
        try:
            name_version = packaging.version.parse(name)
            # Ignore dev and pre releases, for example Matomo 5.0.0-rc3
            if not name_version.is_prerelease:
                versions.append(name)
        except:
            print('ERROR: Unable to parse version for apache httpd for version value ', name)

    versions = sorted(versions, key=packaging.version.Version, reverse=True)
    for version in versions:
        versions_dict[version] = []
    return versions_dict


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    main(sys.argv[1:])
