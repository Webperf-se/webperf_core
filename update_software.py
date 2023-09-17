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
    WebPerf Core

    Usage:
    test.py -u https://webperf.se

    Options and arguments:
    -h/--help\t\t\t: Help information on how to use script
    -u/--url <site url>\t\t: website url to test against
    -t/--test <test number>\t: run ONE test (use ? to list available tests)
    -r/--review\t\t\t: show reviews in terminal
    -i/--input <file path>\t: input file path (.json/.sqlite)
    -o/--output <file path>\t: output file path (.json/.csv/.sql/.sqlite)
    -A/--addUrl <site url>\t: website url (required in combination with -i/--input)
    -D/--deleteUrl <site url>\t: website url (required in combination with -i/--input)
    -L/--language <lang code>\t: language used for output(en = default/sv)
    """

    collection = get_softwares()
    # print('software', collection)

    del collection['loaded']

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
            versions = get_github_versions(github_ower, github_repo, github_release_source, github_security)
        if key == 'iis':
            versions = get_iis_versions()
            versions = extend_versions_for_iis(versions)
        elif key == 'apache':
            versions = get_apache_httpd_versions()
            versions = extend_versions_for_apache_httpd(versions)
        elif key == 'nginx':
            versions = extend_versions_for_nginx(versions)
        versions = extend_versions_from_github_advisory_database(key, versions)

        # print(key, len(versions))
        if len(versions) > 0:
            collection['softwares'][key]['versions'] = versions

        set_softwares(collection)
        index += 1


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
                # cve_info = {
                #     'name': cve,
                #     'references': [
                #         'https://nginx.org/en/security_advisories.html',
                #         more_info_url.replace('http://', 'https://')
                #     ],
                #     'version': version
                # }
                # if advisory_url != None:
                #     cve_info['references'].append(
                #         advisory_url.replace('http://', 'https://'))
                # result.append(cve_info)
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
                # versions[version].append({
                #     'name': cve,
                #     'references': [
                #         url
                #     ],
                #     'version': version
                # })
                versions[version].append(cve)

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
                                    # versions[version].append({
                                    #     'name': current_cve,
                                    #     'references': [
                                    #         'https://httpd.apache.org/security/vulnerabilities_24.html',
                                    #         'https://www.cve.org/CVERecord?id={0}'.format(
                                    #             current_cve)
                                    #     ]
                                    # })
                                    # versions[version].append({
                                    #     'name': current_cve
                                    # })
                                    versions[version].append(current_cve)

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
        result = list()

        if github_adadvisory_database_path == None:
            return result

        root_path = os.path.join(
            github_adadvisory_database_path, 'advisories', 'github-reviewed')
        #root_path = os.path.join(input_folder, 'advisories', 'unreviewed')
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
                        # nice_json_data = json.dumps(json_data, indent=4)
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

                        # if software_name in affected['package']['name']:
                        #     print('DEBUG:', affected['package']['name'])

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
                                        versions[version].append(cve_info['name'])
                                        result.append(cve_info)

        return versions

def set_softwares(collection):
    # TODO: change to this version when used in webperf-core
    # dir = Path(os.path.dirname(
    #     os.path.realpath(__file__)) + os.path.sep).parent
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep)
    
    file_path = '{0}{1}data{1}software-sources.json'.format(dir, os.path.sep)
    print('file_path', file_path)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}software-sources.json'.format(dir, os.path.sep)
        print('file_path', file_path)
    if not os.path.isfile(file_path):
        print("ERROR: No software-sources.json file found!")

    file_path = file_path.replace('-sources.json', '-full.json')

    collection["loaded"] = True
    collection["updated"] = '{0}'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    data = json.dumps(collection, indent=4)
    with open(file_path, 'w', encoding='utf-8', newline='') as file:
        file.write(data)
   

def get_softwares():
    # TODO: change to this version when used in webperf-core
    # dir = Path(os.path.dirname(
    #     os.path.realpath(__file__)) + os.path.sep).parent
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep)

    file_path = '{0}{1}data{1}software-sources.json'.format(dir, os.path.sep)
    print('file_path', file_path)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}software-sources.json'.format(dir, os.path.sep)
        print('file_path', file_path)
    if not os.path.isfile(file_path):
        print("ERROR: No software-sources.json file found!")
        return {
            'loaded': False
        }

    with open(file_path) as json_file:
        softwares = json.load(json_file)
    return softwares

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
        regex = r"^([v]|release\-){0,1}(?P<name>[0-9\\.]+)([\\\/](?P<name2>[0-9\\.]+)){0,1}"
        matches = re.finditer(regex, version[name_key])
        for matchNum, match in enumerate(matches, start=1):
            name = match.group('name')
            name2 = match.group('name2')

        if name == None:
            continue

        versions.append(name)

        if name2 != None:
            versions.append(name2)

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
                versions_dict[version] = {
                    'name': 'fixes security issues'
                }

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
            versions_dict[version] = [{
                'name': 'END-OF-LIFE'
            }]
        else:
            versions_dict[version] = []
    return versions_dict


def get_apache_httpd_versions():
    # newer_versions = []
    content = httpRequestGetContent(
        'https://svn.apache.org/viewvc/httpd/httpd/tags/')
    regex = r"<a name=\"(?P<version>[0-9\.]+)\""
    matches = re.finditer(regex, content, re.MULTILINE)

    versions = list()
    versions_dict = {}
    from distutils.version import LooseVersion

    for matchNum, match in enumerate(matches, start=1):
        name = match.group('version')
        versions.append(name)

    versions = sorted(versions, key=packaging.version.Version, reverse=True)
    for version in versions:
        versions_dict[version] = []
    return versions_dict


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    main(sys.argv[1:])