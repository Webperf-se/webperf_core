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
from tests.sitespeed_base import get_result
import datetime
import gettext
from distutils.version import LooseVersion

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
try:
    github_adadvisory_database_path = config.software_github_adadvisory_database_path
except:
    # If software_github_adadvisory_database_path variable is not set in config.py this will be the default
    github_adadvisory_database_path = None

cve_cache = {}

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
    data = enrich_data(data, origin_domain, result_folder_name, rules)

    rating = Rating(_, review_show_improvements_only)
    result = {}
    result = convert_item_to_domain_data(data)
    texts = sum_overall_software_used(_local, _, result, url)

    result2 = convert_item_to_software_data(data, url)
    rating += rate_software_security_result(_local, _, result2, url)

    result.update(result2)

    rating.overall_review = '{0}\r\n'.format('\r\n'.join(texts))

    if not use_cache:
        shutil.rmtree(result_folder_name)

    return (rating, result)


def create_detailed_review(msg_type, points, software_name, software_versions, sources, cve_name=None, references=None):
    # TODO: Use points from arguments into create_detailed_review and replace it in text (so it is easier to change rating)
    if msg_type == 'cve':
        msg = ['##### Software related to {0} ( #POINTS# rating )'.format(cve_name),
               '',
               '###### Introduction:',
               'Software version used is effected by vurnability described in {0}.'.format(
                   cve_name),
               'For a more detailed explanation please see references below or search for {0}.'.format(
                   cve_name),
               'In most cases you can fix a CVE related issue by updating software to latest version.',
               'In some rare cases there is no update and you need to consider not using the software affected.',
               '']
    elif msg_type == 'flagged':
        msg = ['##### Software with security flagged issues ( 1.5 rating )',
               '',
               '###### Introduction:',
               'Software used has a newer version with issues flagged with security in GITHUB_REPO.',
               'This means that one or more security related issued has been fixed in a later version then you use.',
               'You can fix this by updating software to latest version.',
               '']
    elif msg_type == 'behind100':
        msg = ['##### Software is behind >=100 versions ( #POINTS# rating )',
               '',
               '###### Introduction:',
               'Software used is behind 100 or more version compared to latests.',
               'This is a very good indicator that you need to update to lastest version.',
               'It also indicate that you don\'t have a good package routine for your software.'
               'You can fix this by updating software to latest version.',
               '']
    elif msg_type == 'behind75':
        msg = ['##### Software is behind >=75 versions ( #POINTS# rating )',
               '',
               '###### Introduction:',
               'Software used is behind 75 or more version compared to latests.',
               'This is a very good indicator that you need to update to lastest version.',
               'It also indicate that you don\'t have a good package routine for your software.'
               'You can fix this by updating software to latest version.',
               '']
    elif msg_type == 'behind50':
        msg = ['##### Software is behind >=50 versions ( #POINTS# rating )',
               '',
               '###### Introduction:',
               'Software used is behind 50 or more version compared to latests.',
               'This is a very good indicator that you need to update to lastest version.',
               'It also indicate that you don\'t have a good package routine for your software.'
               'You can fix this by updating software to latest version.',
               '']
    elif msg_type == 'behind25':
        msg = ['##### Software is behind >=25 versions ( #POINTS# rating )',
               '',
               '###### Introduction:',
               'Software used is behind 25 or more version compared to latests.',
               'This is a good indicator that you need to update to lastest version.',
               'It also indicate that you don\'t have a good package routine for your software.'
               'You can fix this by updating software to latest version.',
               '']
    elif msg_type == 'behind10':
        msg = ['##### Software is behind >=10 versions ( #POINTS# rating )',
               '',
               '###### Introduction:',
               'Software used is behind 10 or more version compared to latests.',
               'This is a semi good indicator that you need to update to lastest version.',
               'It also indicate that you don\'t have a good package routine for your software.'
               'You can fix this by updating software to latest version.',
               '']
    elif msg_type == 'latest-but-leaking-name-and-version':
        msg = ['##### Software version and name is leaked ( #POINTS# rating )',
               '',
               '###### Introduction:',
               'You seem to use latest version BUT you are leaking name and version of software used.',
               'This make it easier for someone to find vurnabilities to use against you, all from ZERO-DAY to known security issues.'
               'To fix this you need to hide name and version, please view Software documentation on how to do this.'
               '']
    elif msg_type == 'unknown-but-leaking-name-and-version':
        msg = ['##### Software version and name is leaked ( #POINTS# rating )',
               '',
               '###### Introduction:',
               'You are leaking name and version of software used.',
               'This make it easier for someone to find vurnabilities to use against you, all from ZERO-DAY to known security issues.'
               'To fix this you need to hide name and version, please view Software documentation on how to do this.'
               '']
    elif msg_type == 'leaking-name':
        msg = ['##### Software version and name is leaked ( #POINTS# rating )',
               '',
               '###### Introduction:',
               'Software used is behind 1 or more version compared to latests.',
               'This is a small indicator that you need to update to lastest version.',
               'It also indicate that you don\'t have a good package routine for your software.'
               'You can fix this by updating software to latest version.',
               '']
    elif msg_type == 'behind1':
        msg = ['##### Software is behind >=1 versions ( #POINTS# rating )',
               '',
               '###### Introduction:',
               'Software used is behind 1 or more version compared to latests.',
               'This is a small indicator that you need to update to lastest version.',
               'It also indicate that you don\'t have a good package routine for your software.'
               'You can fix this by updating software to latest version.',
               '']
    elif msg_type == 'multiple-versions':
        msg = ['##### Multiple versions of same Software ( #POINTS# rating )',
               '',
               '###### Introduction:',
               'You are using multiple version of the same software.',
               'This can be caused if you include resources from external sources or because of miss configuration.'
               'This is a small indicator that you don\'t have as much control that you probably should.',
               'It also indicate that you don\'t have a good package routine for your software.'
               'You can fix this by updating software to latest version or latest version that you use for all instances.',
               '']

    if references != None and len(references) > 0:
        msg.append('###### Reference(s):')

        for reference in references:
            msg.append('- {0}'.format(reference))
        msg.append('')

    if len(software_versions) > 0:
        msg.append('###### Detected version(s):')

        for version in software_versions:
            msg.append('- {0} {1}'.format(software_name, version))
        msg.append('')

    if len(sources) > 0:
        msg.append('###### Detected resource(s):')

        source_index = 0
        for source in sources:
            if source_index > 5:
                msg.append('- More then 5 sources, hiding rest')
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

    ratings = {}

    categories = ['cms', 'webserver', 'os',
                  'analytics',
                  'js',
                  'img', 'img.software', 'img.os', 'img.device', 'video']
    for category in categories:
        if category in result:
            for software_name in result[category]:
                info = result[category][software_name]
                if 'vulnerabilities' in info:
                    for vuln in info['vulnerabilities']:
                        points = 1.0
                        if 'severity' in vuln:
                            if 'HIGH' in vuln['severity']:
                                points = 1.2
                            elif 'MODERATE' in vuln['severity']:
                                points = 1.5
                        vuln_versions = list()
                        vuln_versions.append(vuln['version'])
                        v_sources_key = 'v-{0}-sources'.format(
                            vuln['version'])

                        if v_sources_key not in info:
                            v_sources_key = 'sources'
                        vuln_sources = info[v_sources_key]

                        text = create_detailed_review(
                            'cve', points, software_name, vuln_versions, vuln_sources, vuln['name'], vuln['references'])
                        sub_rating = Rating(_, review_show_improvements_only)
                        sub_rating.set_overall(points)
                        if use_detailed_report:
                            sub_rating.set_integrity_and_security(points, '.')
                            sub_rating.integrity_and_security_review = text
                        else:
                            sub_rating.set_integrity_and_security(points)
                        ratings = update_rating_collection(sub_rating, ratings)

                if category != 'js' and 'nof-newer-versions' in info and info['nof-newer-versions'] == 0:
                    points = 4.5
                    text = create_detailed_review(
                        'latest-but-leaking-name-and-version', points, software_name, info['versions'], info['sources'])
                    sub_rating = Rating(_, review_show_improvements_only)
                    sub_rating.set_overall(points)
                    if use_detailed_report:
                        sub_rating.set_integrity_and_security(points, '.')
                        sub_rating.integrity_and_security_review = text
                    else:
                        sub_rating.set_integrity_and_security(points)
                    ratings = update_rating_collection(sub_rating, ratings)
                elif category != 'js':
                    points = 4.0
                    text = create_detailed_review(
                        'unknown-but-leaking-name-and-version', points, software_name, info['versions'], info['sources'])
                    sub_rating = Rating(_, review_show_improvements_only)
                    sub_rating.set_overall(points)
                    if use_detailed_report:
                        sub_rating.set_integrity_and_security(points, '.')
                        sub_rating.integrity_and_security_review = text
                    else:
                        sub_rating.set_integrity_and_security(points)
                    ratings = update_rating_collection(sub_rating, ratings)

                if 'nof-newer-versions' in info and info['nof-newer-versions'] > 0:
                    for version in info['versions']:
                        v_newer_key = 'v-{0}-nof-newer-versions'.format(
                            version)
                        v_sources_key = 'v-{0}-sources'.format(version)

                        # TODO: FAIL SAFE, we have identified multiple version of same software for the same request, should not be possible...
                        if v_newer_key not in info:
                            v_newer_key = 'nof-newer-versions'

                        if info[v_newer_key] == 0:
                            continue

                        if v_sources_key not in info:
                            v_sources_key = 'sources'

                        tmp_versions = list()
                        tmp_versions.append(version)

                        points = -1
                        text = ''
                        if info[v_newer_key] >= 100:
                            points = 2.0
                            text = create_detailed_review(
                                'behind100', points, software_name, tmp_versions, info[v_sources_key])
                        elif info[v_newer_key] >= 75:
                            points = 2.25
                            text = create_detailed_review(
                                'behind75', points, software_name, tmp_versions, info[v_sources_key])
                        elif info[v_newer_key] >= 50:
                            points = 2.5
                            text = create_detailed_review(
                                'behind50', points, software_name, tmp_versions, info[v_sources_key])
                        elif info[v_newer_key] >= 25:
                            points = 2.75
                            text = create_detailed_review(
                                'behind25', points, software_name, tmp_versions, info[v_sources_key])
                        elif info[v_newer_key] >= 10:
                            points = 3.0
                            text = create_detailed_review(
                                'behind10', points, software_name, tmp_versions, info[v_sources_key])
                        elif info[v_newer_key] >= 1:
                            points = 4.9
                            text = create_detailed_review(
                                'behind1', points, software_name, tmp_versions, info[v_sources_key])

                        sub_rating = Rating(_, review_show_improvements_only)
                        sub_rating.set_overall(points)
                        if use_detailed_report:
                            sub_rating.set_integrity_and_security(points, '.')
                            sub_rating.integrity_and_security_review = text
                        else:
                            sub_rating.set_integrity_and_security(points)
                        ratings = update_rating_collection(sub_rating, ratings)

                if len(info['versions']) > 1:
                    points = 4.1
                    text = create_detailed_review(
                        'multiple-versions', points, software_name, info['versions'], info['sources'])
                    sub_rating = Rating(_, review_show_improvements_only)
                    sub_rating.set_overall(points)
                    if use_detailed_report:
                        sub_rating.set_integrity_and_security(points, '.')
                        sub_rating.integrity_and_security_review = text
                    else:
                        sub_rating.set_integrity_and_security(points)
                    ratings = update_rating_collection(sub_rating, ratings)

    sorted_keys = list()
    for points_key in ratings.keys():
        sorted_keys.append(points_key)

    sorted_keys.sort()

    for points_key in sorted_keys:
        for sub_rating in ratings[points_key]:
            rating += sub_rating

    if rating.get_overall() == -1:
        rating.set_overall(5.0)
        rating.set_integrity_and_security(5.0)
    elif not use_detailed_report:
        text = '{0}'.format(_local('UPDATE_AVAILABLE'))
        tmp_rating = Rating(_, review_show_improvements_only)
        tmp_rating.set_integrity_and_security(
            rating.get_integrity_and_security(), text)

        rating.integrity_and_security_review = tmp_rating.integrity_and_security_review

    return rating


def sum_overall_software_used(_local, _, result, url):
    texts = list()

    categories = ['cms', 'webserver', 'os',
                  'analytics', 'tech', 'license', 'meta',
                  'js', 'css',
                  'lang', 'img', 'img.software', 'img.os', 'img.device', 'video']

    has_announced_overall = False

    for category in categories:
        if category in result:
            if use_detailed_report and not has_announced_overall:
                texts.append('##### {0}'.format(url))
                has_announced_overall = True

            texts.append(_local('TEXT_USED_{0}'.format(
                category.upper())).format(', '.join(result[category].keys())))

    return texts


def convert_item_to_software_data(data, url):
    result = {
        'called_url': url
    }

    for item in data:
        category = item['category']

        if 'js' not in category and 'cms' not in category and 'webserver' not in category and 'os' not in category:
            continue

        if category not in result:
            result[category] = {}

        name = item['name']
        if name == '?':
            continue
        version = item['version']
        if 'webserver' != category and version == None:
            continue

        precision = item['precision']
        if precision < 0.3:
            continue

        if name not in result[category]:
            result[category][name] = {
                'versions': [],
                'sources': []
            }

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
        if 'latest-version' in item:
            result[category][name]['latest-version'] = item['latest-version']
        if 'nof-newer-versions' in item:
            if 'nof-newer-versions' not in result[category][name] or result[category][name]['nof-newer-versions'] < item['nof-newer-versions']:
                result[category][name]['nof-newer-versions'] = item['nof-newer-versions']
            v_newer_key = 'v-{0}-nof-newer-versions'.format(
                version)
            result[category][name][v_newer_key] = item['nof-newer-versions']

    result = cleanup_software_result(result)

    for category in result:
        if 'called_url' == category:
            continue

        for software_name in result[category]:
            software = result[category][software_name]
            for version in software['versions']:
                records = get_cve_records_for_software_and_version(
                    software_name, version, category)
                if len(records) > 0:
                    if 'vulnerabilities' not in result[category][software_name]:
                        result[category][software_name]['vulnerabilities'] = list()
                    result[category][software_name]['vulnerabilities'].extend(
                        records)

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


def get_cve_cache():
    cache_data = get_cache_file(
        'cve-cache', use_text_instead_of_content=True, time_delta=cache_time_delta)

    if cache_data == None:
        return {'loaded': True}

    return json.loads(cache_data)


def get_software_version_cves(software_name, software_version):
    if not use_cache:
        return None
    global cve_cache
    if 'loaded' not in cve_cache:
        cve_cache = get_cve_cache()
        cve_cache['loaded'] = True

    if software_name not in cve_cache:
        return None

    software_info = cve_cache[software_name]
    if software_version not in software_info:
        return None

    items = software_info[software_version]
    return items


def set_software_cves(software_name, software_version, result):
    global cve_cache
    if 'loaded' not in cve_cache:
        cve_cache = get_cve_cache()
        cve_cache['loaded'] = True

    if software_name not in cve_cache:
        cve_cache[software_name] = {}

    if software_version not in cve_cache[software_name]:
        cve_cache[software_name][software_version] = {}

    cve_cache[software_name][software_version] = result

    test = json.dumps(cve_cache, indent=4)
    set_cache_file('cve-cache',
                   test, use_text_instead_of_content=True)


def get_cve_records_for_software_and_version(software_name, version, category):
    result = get_software_version_cves(software_name, version)
    if result == None:
        result = list()
        try:
            result.extend(get_cve_records_from_github_advisory_database(
                software_name, version, category))
            result.extend(get_cve_records_from_apache(
                software_name, version, category))
            result.extend(get_cve_records_from_nginx(
                software_name, version, category))
            result.extend(get_cve_records_from_iis(
                software_name, version, category))
            # 63a0b2ce88933b5049d3393ca79850250716b0894da58cea5d0e97d32f9ad317fde14c1946f777fb7c6f0bf0d9fcdf700a2fa3f84d71b627ee29c4ef4fface29.txt.utf-8.cache
            set_software_cves(software_name, version, result)
        except:
            print('CVE Exception', software_name, version, category)
    else:
        print('Cached entry in cve cache found, using it instead.')
    return result


def get_cve_records_from_iis(software_name, version, category):
    result = list()

    if 'webserver' != category:
        return result

    if software_name != 'iis':
        return result

    if version == None:
        return result

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
            cve_info = {
                'name': cve,
                'references': [
                    url
                ],
                'version': version
            }
            result.append(cve_info)

    return result


def get_cve_records_from_nginx(software_name, version, category):
    result = list()

    if 'webserver' != category:
        return result

    if software_name != 'nginx':
        return result

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

            lversion = LooseVersion(version)
            lstart_version = LooseVersion(start_version)
            lend_version = LooseVersion(end_version)

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

                lsafe_version = LooseVersion(safe_version)

                if lversion == lsafe_version:
                    is_match = False

                lversion_specificity = len(lversion.version)

                if lversion_specificity == 3 and lversion_specificity == len(lsafe_version.version):
                    # is same branch and is equal or greater then safe (fixed) version?
                    if lversion.version[0] == lsafe_version.version[0] and lversion.version[1] == lsafe_version.version[1] and lversion.version[2] >= lsafe_version.version[2]:
                        is_match = False

        if is_match:
            cve_info = {
                'name': cve,
                'references': [
                    'https://nginx.org/en/security_advisories.html',
                    more_info_url.replace('http://', 'https://')
                ],
                'version': version
            }
            if advisory_url != None:
                cve_info['references'].append(
                    advisory_url.replace('http://', 'https://'))
            result.append(cve_info)

    return result


def get_cve_records_from_apache(software_name, version, category):
    result = list()

    if 'webserver' != category:
        return result

    if software_name != 'apache':
        return result

    if version == None:
        return result

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
                                            lversion = LooseVersion(version)
                                            ltmp_version = LooseVersion(
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
                                cve_info = {
                                    'name': current_cve,
                                    'references': [
                                        'https://httpd.apache.org/security/vulnerabilities_24.html',
                                        'https://www.cve.org/CVERecord?id={0}'.format(
                                            current_cve)
                                    ],
                                    'version': version
                                }
                                result.append(cve_info)

                            current_cve = None
                    else:
                        current_cve = cve_section

                current_version = None
        else:
            current_version = version_section
    return result


def get_cve_records_from_github_advisory_database(software_name, version, category):
    # https://github.com/github/advisory-database
    result = list()

    if category != 'js':
        return result

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

                            # TODO: We should handle exception better here if version(s) is not valid format
                            if start_version != None and version != None:
                                lversion = LooseVersion(version)
                                lstart_version = LooseVersion(
                                    start_version)
                                if end_version != None and end_version != '':
                                    lend_version = LooseVersion(end_version)
                                    if lversion >= lstart_version and lversion < lend_version:
                                        is_matching = True
                                elif last_affected_version != None and last_affected_version != '':
                                    l_last_affected_version = LooseVersion(
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
                                cve_info['version'] = version
                                result.append(cve_info)

    return result


def convert_item_to_domain_data(data):
    result = {}

    for item in data:
        category = item['category']
        name = item['name']
        if name == '?':
            continue
        version = item['version']
        if version == None:
            version = '?'
        precision = item['precision']

        if category not in result:
            result[category] = {}
        if name not in result[category]:
            result[category][name] = {}
        if version not in result[category][name]:
            result[category][name][version] = {
                'name': name, 'precision': precision
            }
            if 'github-owner' in item:
                result[category][name][version]['github-owner'] = item['github-owner']
            if 'github-repo' in item:
                result[category][name][version]['github-repo'] = item['github-repo']
            if 'latest-version' in item:
                result[category][name]['latest-version'] = item['latest-version']
            if 'is-latest-version' in item:
                result[category][name]['is-latest-version'] = item['is-latest-version']

        if result[category][name][version]['precision'] < precision:
            obj = {}
            obj['name'] = name
            obj['precision'] = precision
            if 'github-owner' in item:
                obj['github-owner'] = item['github-owner']
            if 'github-repo' in item:
                obj['github-repo'] = item['github-repo']
            result[category][name][version] = obj
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
                if 'is-latest-version' in item and item['is-latest-version']:
                    item['security.latest-but-leaking-name-and-version'] = True
                else:
                    item['security.leaking-name-and-version'] = True

                tmp_list.append(get_default_info(
                    item['url'], 'enrich', item['precision'], 'security', 'screaming.{0}'.format(item['category']), None))
            else:
                tmp_list.append(get_default_info(
                    item['url'], 'enrich', item['precision'], 'security', 'talking.{0}'.format(item['category']), None))

        # matomo = enrich_data_from_matomo(matomo, tmp_list, item)
        enrich_data_from_github_repo(tmp_list, item)
        enrich_versions(tmp_list, item)
        enrich_data_from_javascript(tmp_list, item, rules)
        enrich_data_from_videos(tmp_list, item, result_folder_name)
        enrich_data_from_images(tmp_list, item, result_folder_name)
        enrich_data_from_documents(tmp_list, item, result_folder_name)

    data.extend(tmp_list)

    if len(testing) > 0:
        raw_data['test'][orginal_domain] = {
            'cms': cms,
            'test': testing
        }

    return data


def enrich_versions(tmp_list, item):
    if item['version'] == None:
        return

    newer_versions = []
    version_verified = False

    if item['name'] == 'matomo':
        a = 1
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

    if item['name'] == 'apache':
        (version_verified, newer_versions) = get_apache_httpd_versions(
            item['version'])
    elif item['name'] == 'iis':
        (version_verified, newer_versions) = get_iis_versions(
            item['version'])
    elif 'github-owner' in item and 'github-repo' in item:
        github_ower = item['github-owner']
        github_repo = item['github-repo']
        github_release_source = item['github-repo-version-source']
        github_security_label = item['github-repo-security-label']
        (version_verified, newer_versions) = get_github_project_versions(
            github_ower, github_repo, github_release_source, github_security_label, item['version'])

    nof_newer_versions = len(newer_versions)
    has_more_then_one_newer_versions = nof_newer_versions > 0

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
        info['nof-newer-versions'] = nof_newer_versions

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

    return


def get_iis_versions(current_version):
    # https://learn.microsoft.com/en-us/lifecycle/products/internet-information-services-iis
    newer_versions = []
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
        date = None
        id = name
        versions_dict[name] = {
            'name': name,
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
            newer_versions.append(versions_dict[version])

    if not version_found:
        return (version_found, [])
    else:
        return (version_found, newer_versions)


def get_apache_httpd_versions(current_version):
    newer_versions = []
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
        date = None
        id = name
        versions_dict[name] = {
            'name': name,
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
            newer_versions.append(versions_dict[version])

    if not version_found:
        return (version_found, [])
    else:
        return (version_found, newer_versions)


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
    if 'github-repo-version-source' not in item:
        item['github-repo-version-source'] = github_release_source
    if 'github-repo-security-label' not in item:
        item['github-repo-security-label'] = github_security_label

    github_info = get_github_repository_info(
        github_ower, github_repo)

    precision = 0.8
    if github_info['license'] != None:
        info = get_default_info(
            item['url'], 'enrich', precision, item['category'], item['name'], item['version'])
        # https://spdx.org/licenses/
        tmp_list.append(get_default_info(
            item['url'], 'enrich', 0.9, 'license', github_info['license'], None))
        info['license'] = github_info['license']
        tmp_list.append(info)

    if len(github_info['tech']) > 0:
        for name in github_info['tech']:
            tmp_list.append(get_default_info(
                item['url'], 'enrich', 0.9, 'tech', name, None))

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


def enrich_data_from_documents(tmp_list, item, result_folder_name, nof_tries=0):
    if use_stealth:
        return
    # TODO: Handle: pdf, excel, word, powerpoints (and more?)


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


def identify_software(filename, origin_domain, rules):
    data = list()

    # Fix for content having unallowed chars
    with open(filename) as json_input_file:
        har_data = json.load(json_input_file)

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
    result['security'] = []

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
