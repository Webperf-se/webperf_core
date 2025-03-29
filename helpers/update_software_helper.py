# -*- coding: utf-8 -*-
import sys
from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import os
import time
from urllib.parse import urlparse
import uuid
import packaging.version
from helpers.setting_helper import get_config, update_config
from helpers.browser_helper import get_chromium_browser
from tests.sitespeed_base import get_browsertime_har_path,\
    get_result_using_no_cache, get_sanitized_browsertime
from tests.utils import get_http_content

USE_CACHE = get_config('general.cache.use')
CACHE_TIME_DELTA = timedelta(minutes=get_config('general.cache.max-age'))
CONFIG_WARNINGS = {}

github_adadvisory_database_path = get_config(
        'tests.software.advisory.path')
# If software_github_adadvisory_database_path variable is not
# set in config.py this will be the default
if github_adadvisory_database_path == '':
    github_adadvisory_database_path = 'advisory_database'

def update_user_agent():
    sitespeed_use_docker = False
    software_browser = 'firefox'
    timeout = 300

    folder = 'tmp'
    if USE_CACHE:
        folder = get_config('general.cache.folder')

    url = "https://webperf.se/"
    o = urlparse(url)
    hostname = o.hostname

    result_folder_name = os.path.join(folder, hostname, f'{str(uuid.uuid4())}')

    sitespeed_iterations = 1
    sitespeed_arg = (
        '--plugins.remove screenshot '
        '--plugins.remove html '
        '--plugins.remove metrics '
        '--browsertime.screenshot false '
        '--screenshot false '
        '--screenshotLCP false '
        '--browsertime.screenshotLCP false '
        '--videoParams.createFilmstrip false '
        '--visualMetrics false '
        '--visualMetricsPerceptual false '
        '--visualMetricsContentful false '
        '--browsertime.headless true '
        '--utc true '
        f'-n {sitespeed_iterations}')

    if 'firefox' in software_browser:
        sitespeed_arg = (
            '-b firefox '
            '--firefox.includeResponseBodies all '
            '--firefox.preference privacy.trackingprotection.enabled:false '
            '--firefox.preference privacy.donottrackheader.enabled:false '
            '--firefox.preference browser.safebrowsing.malware.enabled:false '
            '--firefox.preference browser.safebrowsing.phishing.enabled:false '
            f'{sitespeed_arg}')
    else:
        sitespeed_arg = (
            f'-b {get_chromium_browser()} '
            '--chrome.cdp.performance false '
            '--browsertime.chrome.timeline false '
            '--browsertime.chrome.includeResponseBodies all '
            '--browsertime.chrome.args ignore-certificate-errors '
            f'{sitespeed_arg}')

    sitespeed_arg = f'--shm-size=1g {sitespeed_arg}'

    if get_config('tests.sitespeed.xvfb'):
        sitespeed_arg += ' --xvfb'
    sitespeed_arg += (f' --outputFolder {result_folder_name} {url}')

    test = get_result_using_no_cache(sitespeed_use_docker, sitespeed_arg, timeout)
    test = test.replace('\\n', '\r\n').replace('\\\\', '\\')

    filename = get_browsertime_har_path(os.path.join(result_folder_name, 'pages'))
    result = get_sanitized_browsertime(filename)
    json_result = json.loads(result)

    if 'log' not in json_result:
        print('NO log element')
        return

    if 'entries' not in json_result['log']:
        print('NO entries element')
        return

    for entry in json_result['log']['entries']:
        if 'request' not in entry:
            print('NO request element')
            return

        request = entry['request']
        if 'headers' not in request:
            print('NO headers element')
            return

        for header in request['headers']:
            header_name = header['name'].lower()
            header_value = header['value']
            if 'user-agent' != header_name:
                continue

            print(header_value)
            update_config('general.useragent', header_value, f'defaults{os.path.sep}settings.json')
            return


def update_software_info():
    collection = get_software_sources('software-sources.json')
    # print('software', collection)

    for key in collection['aliases'].keys():
        if collection['aliases'][key] not in collection['softwares']:
            print('alias', key, "is invalid")
        # else:
        #     print('alias', key, "=", collection['aliases'][key])

    plugins_to_remove = []
    for key in collection['softwares'].keys():
        # if index > 15:
        #     break
        # print('software', key)
        item = collection['softwares'][key]

        if 'note' in collection['softwares'][key]:
            print('ERROR! You are not allowed to add "software-sources.json" when it still includes "note" field.')
            raise ValueError('ERROR! You are not allowed to add "software-sources.json" when it still includes "note" field.')
        if 'url' in collection['softwares'][key]:
            print('ERROR! You are not allowed to add "software-sources.json" when it still includes "url" field.')
            raise ValueError('ERROR! You are not allowed to add "software-sources.json" when it still includes "url" field.')
        if 'urls' in collection['softwares'][key]:
            print('ERROR! You are not allowed to add "software-sources.json" when it still includes "urls" field.')
            raise ValueError('ERROR! You are not allowed to add "software-sources.json" when it still includes "urls" field.')

        versions = {}
        is_source_github = 'github-owner' in item and 'github-repo' in item
        is_source_wordpress = 'type' in item and 'wordpress-plugin' in item['type']
        if is_source_github:
            github_ower = None
            github_repo = None
            github_security = None
            github_release_source = 'tags'
            github_version_prefix = None
            github_version_key = None
            github_release_pages = 1

            if 'github-owner' in item:
                github_ower = item['github-owner']
            if 'github-repo' in item:
                github_repo = item['github-repo']
            if 'github-source' in item:
                github_release_source = item['github-source']
            if 'github-source-pages' in item:
                github_release_pages = item['github-source-pages']

            if 'github-security' in item:
                github_release_source = item['github-security']
            if 'github-prefix' in item:
                github_version_prefix = item['github-prefix']
            if 'github-key' in item:
                github_version_key = item['github-key']

            if github_ower is not None:
                set_github_repository_info(
                    item,
                    github_ower,
                    github_repo)
                versions = get_github_versions(
                    github_ower,
                    github_repo,
                    github_release_source,
                    github_release_pages,
                    github_security,
                    github_version_prefix,
                    github_version_key)

        elif is_source_wordpress:
            set_wordpress_plugin_repository_info(item, key)

        # Add custom information like end of life and cve
        if key == 'iis':
            versions = get_iis_versions()
            versions = extend_versions_for_iis(versions)
        elif key == 'apache':
            versions = extend_versions_for_apache_httpd(versions)
        elif key == 'datatables':
            versions = get_datatables_versions()
        elif key == 'epifind':
            versions = get_epifind_versions()
        elif key == 'php':
            versions = get_php_versions()
            versions = extend_versions_for_php(versions)
        elif key == 'windows-server':
            versions = get_windows_versions()
        elif key == 'nginx':
            versions = extend_versions_for_nginx(versions)
        elif key == 'openssl':
            versions = extend_versions_for_openssl(versions)
        elif key == 'drupal':
            versions = get_drupal_versions()

        versions = extend_versions_from_github_advisory_database(key, versions)

        if 'error' in item:
            plugins_to_remove.append(key)
        elif len(versions) > 0:
            collection['softwares'][key]['versions'] = versions

    print('Following wordpress plugins could not be found:')
    for key in plugins_to_remove:
        print(f'\t- {key}')
        del collection['softwares'][key]

    set_softwares('software-full.json', collection)

def update_licenses():
    print('updates licesences used in defaults/software-rules.json')

    # https://spdx.org/licenses/
    raw_data = get_http_content(
        'https://spdx.org/licenses/')

    regex = r'<code property="spdx:licenseId">(?P<licenseId>[^<]+)<\/code'
    matches = re.finditer(
        regex, raw_data, re.MULTILINE)

    licenses = []
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
            content_rule['match'] = content_rule['match'].replace(
                match_content,
                '?P<license>({0})'.format('|'.join(licenses)))

    save_software_rules(rules)

def get_software_rules():
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    file_path = '{0}{1}{2}{1}software-rules.json'.format(base_directory, os.path.sep, "defaults")
    if not os.path.isfile(file_path):
        print(f"ERROR: No {file_path} file found!")
        return

    with open(file_path) as json_rules_file:
        rules = json.load(json_rules_file)
    return rules

def save_software_rules(rules):
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    file_path = '{0}{1}{2}{1}software-rules.json'.format(base_directory, os.path.sep, "defaults")
    if not os.path.isfile(file_path):
        print(f"ERROR: No {file_path} file found!")
        return

    with open(file_path, 'w') as outfile:
        json.dump(rules, outfile, indent=4)
    return rules

def extend_versions_for_nginx(versions):
    for version in versions.keys():
        print('extend_versions', 'nginx', version)
        result = []

        if version == None:
            return result

        # https://nginx.org/en/security_advisories.html
        raw_data = get_http_content(
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

                    if lversion_specificity == 3 and\
                            lversion_specificity == len(lsafe_version.release):
                        # is same branch and is equal or greater then safe (fixed) version?
                        if lversion.release[0] == lsafe_version.release[0] and\
                                lversion.release[1] == lsafe_version.release[1] and\
                                lversion.release[2] >= lsafe_version.release[2]:
                            is_match = False

            if is_match:
                versions[version].append(cve)

    return versions


def extend_versions_for_iis(versions):
    for version in versions.keys():
        print('extend_versions', 'iis', version)
        # https://www.cvedetails.com/vulnerability-list.php?vendor_id=26&product_id=3427&page=1
        raw_data = get_http_content(
            'https://www.cvedetails.com/vulnerability-list.php?vendor_id=26&product_id=3427&page=1')

        regex_vulnerables = r'href="(?P<url>[^"]+)"[^>]+>(?P<cve>CVE-[0-9]{4}\-[0-9]+)'
        matches_vulnerables = re.finditer(
            regex_vulnerables, raw_data, re.MULTILINE)

        for matchNum, match_vulnerable in enumerate(matches_vulnerables, start=1):
            is_match = False
            cve = match_vulnerable.group('cve')
            url = 'https://www.cvedetails.com{0}'.format(
                match_vulnerable.group('url'))
            raw_cve_data = get_http_content(url)
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

def extend_versions_for_openssl(versions):
    versions = extend_versions_for_openssl_end_of_life(versions)
    versions = extend_versions_for_openssl_vulnerabilities(versions)

    return versions

def extend_versions_for_openssl_vulnerabilities(versions):
    raw_data = get_http_content(
        'https://openssl-library.org/news/vulnerabilities/')

    ver = sorted(versions.keys(), reverse=False)

    section_regex = r'<h3 id="(?P<CVE>CVE[0-9-]+)">.*?<dl>(?P<content>.*?)<\/dl>'
    section_regex_matches = re.finditer(
        section_regex, raw_data, re.MULTILINE | re.S)

    for section_matchNum, section_match in enumerate(section_regex_matches, start=1):
        cve = section_match.group('CVE')
        content = section_match.group('content')

        regex = r'from (?P<start>[0-9\.a-z]+) before (?P<fixed>[0-9\.a-z]+)'
        matches = re.finditer(
            regex, content, re.MULTILINE | re.S)

        try:
            for matchNum, match in enumerate(matches, start=1):
                first_found_in_version = packaging.version.Version(''.join(["+" + str(c) if c.isalpha() else c for c in match.group('start')]))
                fixed_in_version = packaging.version.Version(''.join(["+" + str(c) if c.isalpha() else c for c in match.group('fixed')]))

                for v in ver:
                        current_version = packaging.version.Version(v)
                        if current_version >= first_found_in_version and current_version < fixed_in_version:
                            versions[v].append(cve)
        except Exception as ex:
            a = 1

    return versions


def extend_versions_for_openssl_end_of_life(versions):
    raw_data = get_http_content(
        'https://openssl-library.org/policies/releasestrat/index.html')

    end_of_life_branches = {}

    end_of_life_regex = r'(?P<content>[^>]+) no longer supported'
    end_of_life_matches = re.finditer(
        end_of_life_regex, raw_data, re.MULTILINE)
    for end_of_life_matchNum, end_of_life_match in enumerate(end_of_life_matches, start=1):
        content = end_of_life_match.group('content')

        regex = r'(?P<version>[0-9\.]+)'
        matches = re.finditer(
            regex, content, re.MULTILINE)

        for matchNum, match in enumerate(matches, start=1):
            is_match = False
            end_of_life_branch = None
            end_of_life_version = match.group('version')

            if len(end_of_life_version) > 3:
                end_of_life_branch = end_of_life_version[:3]
                # print('end_of_life_branch', end_of_life_branch)
                end_of_life_branches[end_of_life_branch] = 'END_OF_LIFE'

    for version in versions.keys():
        if len(version) > 3:
            version_branch = version[:3]
            if version_branch in end_of_life_branches:
                versions[version].append(end_of_life_branches[version_branch])
                versions[version] = sorted(versions[version], reverse=True)

    return versions

def extend_versions_for_php(versions):
    raw_data = get_http_content(
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
            end_of_life_branches[end_of_life_branch] = 'END_OF_LIFE {0}'.format(end_of_life_dating)

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
        raw_data = get_http_content(
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
                                ranges = []
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

        if len(versions) == 0:
            print('input versions:', versions)
            return versions

        if github_adadvisory_database_path is None:
            print('github_adadvisory_database_path is None')
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
                        year_path, month, key, f'{key}.json')
                    json_data = None
                    # Sanity check to make sure file exists
                    if not os.path.exists(key_path):
                        print(f'\t\t\t- {key_path} not found')
                        continue

                    with open(key_path, 'r', encoding='utf-8') as file:
                        json_data = json.load(file)
                    if json_data is None:
                        continue

                    if 'schema_version' not in json_data:
                        print('ERROR: NO schema version!')
                        return versions
                    elif json_data['schema_version'] != '1.4.0' and json_data['schema_version'] != '1.3.0':
                        print('ERROR: Unsupported schema version! Assumed 1.3.0 or 1.4.0 but got {0}'.format(
                            json_data['schema_version']))
                        return versions

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
                            if software_name == affected['package']['name'] or f'{software_name}.js' == affected['package']['name']:
                                cve_info = {}

                                nof_aliases = len(json_data['aliases'])
                                if nof_aliases >= 1:
                                    cve_info['name'] = json_data['aliases'][0]
                                    has_cve_name = True
                                    if nof_aliases > 1:
                                        cve_info['aliases'] = json_data['aliases']
                                else:
                                    cve_info['name'] = f"{affected['package']['name']} vulnerability"

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
                                    if start_version is not None and version is not None:
                                        lversion = packaging.version.Version(version)
                                        lstart_version = packaging.version.Version(
                                            start_version)
                                        if end_version is not None and end_version != '':
                                            lend_version = packaging.version.Version(end_version)
                                            if lversion >= lstart_version and lversion < lend_version:
                                                is_matching = True
                                        elif last_affected_version is not None and last_affected_version != '':
                                            l_last_affected_version = packaging.version.Version(
                                                last_affected_version)
                                            if lversion >= lstart_version and lversion <= l_last_affected_version:
                                                is_matching = True
                                        # NOTE: Temporarly(?) removed until https://github.com/github/advisory-database/pull/1807
                                        # is approved and merged
                                        # elif lversion >= lstart_version:
                                        #     is_matching = True

                                    references = []
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

def set_softwares(filename, collection):
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    file_path = '{0}{1}data{1}{2}'.format(base_directory, os.path.sep, filename)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}defaults{1}{2}'.format(base_directory, os.path.sep, filename)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}{2}'.format(base_directory, os.path.sep, filename)
    if not os.path.isfile(file_path):
        print("ERROR: No {0} file found!".format(filename))

    print('set_software_sources', file_path)

    collection["loaded"] = True

    data = json.dumps(collection, indent=4)
    with open(file_path, 'w', encoding='utf-8', newline='') as file:
        file.write(data)

def get_software_sources(filename):
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    file_path = '{0}{1}data{1}{2}'.format(base_directory, os.path.sep, filename)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}{2}'.format(base_directory, os.path.sep, filename)
    if not os.path.isfile(file_path):
        file_path = '{0}{1}defaults{1}{2}'.format(base_directory, os.path.sep, filename)
    if not os.path.isfile(file_path):
        print("ERROR: No {0} file found!".format(filename))
        return {
            'loaded': False
        }

    print('get_software_sources', file_path)
    collection = {}
    with open(file_path) as json_file:
        collection = json.load(json_file)

    if 'aliases' not in collection:
        collection['aliases'] = {}

    if 'softwares' not in collection:
        collection['softwares'] = {}

    # sort on software names
    if len(collection['aliases'].keys())> 0:
        tmp = {}
        issue_aliases_keys = list(collection['aliases'].keys())
        issue_aliases_keys_sorted = sorted(issue_aliases_keys, reverse=False)

        for key in issue_aliases_keys_sorted:
            tmp[key] = collection['aliases'][key]

        collection['aliases'] = tmp
        if issue_aliases_keys != issue_aliases_keys_sorted:
            set_softwares(filename, collection)

    # sort on software names
    if len(collection['softwares'].keys())> 0:
        tmp = {}
        issue_keys = list(collection['softwares'].keys())
        issue_keys_sorted = sorted(issue_keys, reverse=False)

        for key in issue_keys_sorted:
            tmp[key] = collection['softwares'][key]

        collection['softwares'] = tmp
        if issue_keys != issue_keys_sorted:
            set_softwares(filename, collection)

    return collection

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

def set_wordpress_plugin_repository_info(item, name):
    print('Looking up wordpress plugin: {0}'.format(name))

    content = get_http_content(
        f'https://wordpress.org/plugins/{name}/advanced/')

    time.sleep(2.5)

    if 'note' in item:
        del item['note']
    if 'urls' in item:
        del item['urls']

    if 'https://wordpress.org/plugins/{0}'.format(name) not in content:
        item['error'] = 'no plugin found'
        return

    # Lets get an indication if the project is worked on or not
    regex_last_updated = r'<li>[\r\n\t ]*Last updated: <strong><span>(?P<years>[0-9]+) year[s]{0,1}<\/span> ago<\/strong>[\r\n\t ]*<\/li>'
    item['last_pushed_year'] = '2024'
    matches = re.finditer(regex_last_updated, content, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
        years = int(match.group('years'))
        year = datetime.now().year - years
        item['last_pushed_year'] = '{0}'.format(year)

    # Latest version:
    regex_rawversion = r'<li>[\r\n\t]+Version:(?P<rawversion>.*?)<\/li>'
    regex_version = r'(?P<version>[0-9\\.]+)'
    item['versions'] = {}
    matches = re.finditer(regex_rawversion, content, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
        latest_version = match.group('rawversion')
        matches = re.finditer(regex_version, latest_version, re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):
            latest_version = match.group('version')
            item['versions'][latest_version] = []

    # versions
    regex_versions = r'>(?P<version>[0-9\\.]+)<\/option>'
    matches = re.finditer(regex_versions, content, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
        version = match.group('version')
        item['versions'][version] = []

    # notice
    regex_notice = r'<div class=\"plugin\-notice notice notice\-(?P<type>error|warning) notice\-alt\">(?P<text>.*?)<\/div>'
    matches = re.finditer(regex_notice, content, re.MULTILINE)
    item['archived'] = False
    for matchNum, match in enumerate(matches, start=1):
        notice_type = match.group('type')
        if 'error' in notice_type:
            notice_type = 'Critical'
        else:
            notice_type = 'Warning'

        notice_text = match.group('text')
        notice_text = re.sub('<[/]{0,1}[^>]+>', '', notice_text).replace('&#146;', '\'')

        item['notice'] = '{0}! {1}'.format(notice_type, notice_text)

        if 'This plugin has been closed' in notice_text:
            item['archived'] = True

    return


def set_github_repository_info(item, owner, repo):
    repo_content = get_http_content(
        f'https://api.github.com/repos/{owner}/{repo}')

    github_info = None
    try:
        github_info = json.loads(repo_content)
    except json.decoder.JSONDecodeError:
        print(f'ERROR: unable to read repository! owner: {owner}, repo: {repo}')

    # Get license from github repo ("license.spdx_id") info: https://api.github.com/repos/matomo-org/matomo
    # for example: MIT, GPL-3.0
    item['license'] = None
    if 'license' in github_info and github_info['license'] != None and 'spdx_id' in github_info['license']:
        license = github_info['license']['spdx_id'].lower()
        if 'noassertion' != license:
            item['license'] = license

    # Lets get an indication if the project is worked on or not
    item['last_pushed_year'] = None
    if 'pushed_at' in github_info and github_info['pushed_at'] != None:
        pushed_at = github_info['pushed_at']

        # we only use year today, but who knows...
        regex = r"^(?P<date>(?P<year>[0-9]{4})\-(?P<month>[0-9]{2})\-(?P<day>[0-9]{2}))"
        match = re.match(regex, pushed_at)
        if match:
            pushed_at = match.group('year')
            item['last_pushed_year'] = pushed_at

    techs = []
    imgs = []
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

    if 'webperf_core' in repo:
        contributors_content = get_http_content(
            f'https://api.github.com/repos/{owner}/{repo}/contributors')

        contributors = []
        contributors_info = None
        try:
            contributors_info = json.loads(contributors_content)
            if 'status' in contributors_info:
                print(f"GitHub API ERROR: {contributors_info['message']}")
                sys.exit(2)
            for contributor in contributors_info:
                userinfo = f"[{contributor['login']}]({contributor['html_url']})"
                contributors.append(userinfo)

        except json.decoder.JSONDecodeError:
            print(f'ERROR: unable to read repository contributors! owner: {owner}, repo: {repo}')
        item['contributors'] = contributors

    return

def get_github_versions(owner, repo, source, number_of_pages, security_label, version_prefix, name_key):
    versions = []
    versions_dict = {}

    page_upper_limit = number_of_pages + 1

    for page_index in range(1, page_upper_limit):
        versions_content = get_http_content(
            f'https://api.github.com/repos/{owner}/{repo}/{source}?state=closed&per_page=100&page={page_index}')

        version_info = None
        try:
            version_info = json.loads(versions_content)
        except json.decoder.JSONDecodeError:
            print(f'ERROR: unable to read repository versions! owner: {owner}, repo: {repo}')
            return versions_dict

        for version in version_info:
            if source == 'milestones':
                id_key = 'number'
                if name_key is None:
                    name_key = 'title'
                date_key = 'closed_at'
            elif source == 'tags':
                id_key = None
                if name_key is None:
                    name_key = 'name'
                date_key = None
            else:
                id_key = 'id'
                # we uses tag_name instead of name as bootstrap is missing "name" for some releases
                if name_key is None:
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

            key = version[name_key]
            if key != None and version_prefix != None:
                key = key.removeprefix(version_prefix)

            # NOTE: We do this to handle jquery dual release format "1.12.4/2.2.4"
            regex = r"^([v]|release\-){0,1}(?P<name>[0-9\.\-a-zA-Z]+)([\/](?P<name2>[0-9\.\-a-zA-Z]+)){0,1}"
            matches = re.finditer(regex, key)
            for matchNum, match in enumerate(matches, start=1):
                name = match.group('name')
                name2 = match.group('name2')

            if name == None:
                continue

            try:
                name = name.strip('.')
                if owner == 'openssl':
                    name = ''.join(["+" + str(c) if c.isalpha() else c for c in name])
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
            version_label_data = get_http_content(
                f"https://api.github.com/repos/{owner}/{repo}/{source}/{versions_dict[version]['id']}/labels")
            labels = json.loads(version_label_data)

            fixes_security = False
            for label in labels:
                if 'name' in label and label['name'] == security_label:
                    fixes_security = True

            if fixes_security:
                versions_dict[version] = ['fixes security issues']

    return versions_dict
def get_drupal_versions():
    # https://www.drupal.org/about/core/policies/core-release-cycles/schedule
    # https://www.drupal.org/forum/general/news-and-announcements/2015-11-09/drupal-6-end-of-life-announcement

    versions_dict = {
        "10": [],
        "9": ['END_OF_LIFE'],
        "8": ['END_OF_LIFE'],
        "7": [],
        "6": ['END_OF_LIFE'],
        "5": ['END_OF_LIFE']
    }

    return versions_dict

def get_iis_versions():
    # https://learn.microsoft.com/en-us/lifecycle/products/internet-information-services-iis
    content = get_http_content(
        'https://learn.microsoft.com/en-us/lifecycle/products/internet-information-services-iis')
    regex = r"<td>IIS (?P<version>[0-9\.]+)"
    matches = re.finditer(regex, content, re.MULTILINE)

    versions = []
    versions_dict = {}

    for matchNum, match in enumerate(matches, start=1):
        name = match.group('version')
        # version fix because source we use are not using the trailing .0 in all cases
        if '.' not in name:
            name = '{0}.0'.format(name)
        versions.append(name)

    versions = sorted(versions, key=packaging.version.Version, reverse=True)
    for version in versions:
        if packaging.version.Version(version) < packaging.version.Version('10'):
            versions_dict[version] = ['END_OF_LIFE']
        else:
            versions_dict[version] = []
    return versions_dict

def get_windows_versions():
    # source: https://learn.microsoft.com/en-us/lifecycle/products/export/
    # source: https://learn.microsoft.com/en-us/lifecycle/products/?products=windows&terms=windows%20server&skip=10

    versions_dict = {
        "2016/2019/2022": [],
        "2012 r2": ['END_OF_LIFE'],
        "2012": ['END_OF_LIFE'],
        "2008 r2": ['END_OF_LIFE'],
        "2008": ['END_OF_LIFE'],
        "2003": ['END_OF_LIFE']
    }

    return versions_dict

def get_datatables_versions():
    # newer_versions = []
    content = get_http_content(
        'https://cdn.datatables.net/releases.html')
    regex = r">(?P<version>[0-9\.]+)<\/a>"
    matches = re.finditer(regex, content, re.MULTILINE)

    versions = []
    versions_dict = {}

    for matchNum, match in enumerate(matches, start=1):
        name = match.group('version')
        try:
            name_version = packaging.version.parse(name)
            # Ignore dev and pre releases, for example Matomo 5.0.0-rc3
            if not name_version.is_prerelease:
                versions.append(name)
        except:
            print('ERROR: Unable to parse version for datatables for version value ', name)

    versions = sorted(versions, key=packaging.version.Version, reverse=True)
    for version in versions:
        versions_dict[version] = []
    return versions_dict

def get_epifind_versions():
    # newer_versions = []
    content = get_http_content(
        'https://nuget.optimizely.com/package/?id=EPiServer.Find')
    regex = r">(?P<version>[0-9\.]+)<\/a>"
    matches = re.finditer(regex, content, re.MULTILINE)

    versions = []
    versions_dict = {}

    for matchNum, match in enumerate(matches, start=1):
        name = match.group('version')
        try:
            name_version = packaging.version.parse(name)
            # Ignore dev and pre releases, for example Matomo 5.0.0-rc3
            if not name_version.is_prerelease:
                versions.append(name)
        except:
            print('ERROR: Unable to parse version for epifind for version value ', name)

    versions = sorted(versions, key=packaging.version.Version, reverse=True)
    for version in versions:
        versions_dict[version] = []
    return versions_dict

def get_php_versions():
    # newer_versions = []
    content = get_http_content(
        'https://www.php.net/releases/')
    regex = r"<h2>(?P<version>[0-9\.]+)<\/h2>"
    matches = re.finditer(regex, content, re.MULTILINE)

    versions = []
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

def filter_unknown_sources():
    collection = get_software_sources('software-unknown-sources.json')
    known_collection = get_software_sources('software-sources.json')

    names_to_remove = []
    for key in collection.keys():
        item = collection[key]

        if len(key) < 3:
            names_to_remove.append(key)
            continue

        if isinstance(item, bool):
            continue

        if 'versions' not in item:
            names_to_remove.append(key)
            continue

        versions = item['versions']
        if 'unknown' in versions:
            del versions['unknown']

        if 'aliases' in known_collection and key in known_collection['aliases']:
            names_to_remove.append(key)

        if 'softwares' in known_collection and key in known_collection['softwares']:
            names_to_remove.append(key)

        # Change the below number to filter out how many versions should be minimum
        if len(item['versions'].keys()) < 2:
            names_to_remove.append(key)
            continue

    for key in names_to_remove:
        print(f'\t- {key}')
        if key in collection:
            del collection[key]

    set_softwares('software-unknown-sources-filtered.json', collection)
