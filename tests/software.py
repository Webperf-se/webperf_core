# -*- coding: utf-8 -*-
from pathlib import Path
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

use_stealth = True

raw_data = {
    'urls': {
        'use': False
    },
    'headers': {
        'use': False
    },
    'contents': {
        'use': True
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
    }
}
# TODO: Add debug flags for every category here, this so we can print out raw values (so we can add more allowed once)
# TODO: Consider if it is better to use hardcoded lists to match against or not, this would make it more stable but would require maintaining lists


def get_urls_from_har(content):
    urls = dict()

    entries = list()
    json_content = list()
    try:
        json_content = json.loads(content)

        json_content = json_content['log']

        if 'entries' in json_content:
            entries = json_content['entries']

        for entry in entries:
            url = False
            if 'request' in entry:
                request = entry['request']
                if 'url' in request:
                    url = request['url']
                    urls[url] = ''

            content_text = False
            if 'response' in entry:
                response = entry['response']
                if 'content' in response:
                    content = response['content']
                    if 'text' in content:
                        content_text = content['text']
                        urls[url] = content_text

    except Exception as ex:  # might crash if checked resource is not a webpage
        print('crash get_urls_from_har', ex)
        return urls

    return urls


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

    return result


def get_rating_from_sitespeed(url, _local, _):
    # TODO: CHANGE THIS IF YOU WANT TO DEBUG
    result_folder_name = os.path.join(
        'data', 'results-{0}'.format(str(uuid.uuid4())))
    # result_folder_name = os.path.join('data', 'results')

    from tests.performance_sitespeed_io import get_result as sitespeed_run_test

    sitespeed_iterations = 1

    sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --browsertime.chrome.collectPerfLog --browsertime.chrome.includeResponseBodies "all" --html.fetchHARFiles true --outputFolder {2} --firstParty --utc true --xvfb --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        sitespeed_iterations, url, result_folder_name)
    if 'nt' in os.name:
        sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --browsertime.chrome.includeResponseBodies all --outputFolder {2} --utc true --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
            sitespeed_iterations, url, result_folder_name)
        # sitespeed_arg = '--shm-size=1g -b chrome --plugins.remove screenshot --browsertime.chrome.collectPerfLog --browsertime.chrome.includeResponseBodies "all" --html.fetchHARFiles true --outputFolder {2} --firstParty --utc true --browsertime.chrome.args ignore-certificate-errors -n {0} {1}'.format(
        #     sitespeed_iterations, url, result_folder_name)

    filename = ''

    # TODO: Remove cache when done
    import engines.sitespeed_result as input
    sites = input.read_sites('', -1, -1)
    for site in sites:
        if url == site[1]:
            filename = site[0]

            file_created_timestamp = os.path.getctime(filename)
            file_created_date = time.ctime(file_created_timestamp)
            print('Cached entry found from {0}, using it instead of calling website again.'.format(
                file_created_date))

    if filename == '':
        sitespeed_run_test(sitespeed_use_docker, sitespeed_arg)

        website_folder_name = get_foldername_from_url(url)

        filename = os.path.join(result_folder_name, 'pages',
                                website_folder_name, 'data', 'browsertime.har')

    data = identify_software(filename)
    data = enrich_data(data)
    result = convert_item_to_domain_data(data)

    rating = rate_result(_local, _, result, url)

    return (rating, result)


def rate_result(_local, _, result, url):
    rating = Rating(_, review_show_improvements_only)

    url_info = urlparse(url)
    orginal_domain = url_info.hostname

    categories = {'cms': 'CMS', 'webserver': 'WebServer', 'os': 'Operating System',
                  'analytics': 'Analytics', 'tech': 'Technology', 'js': 'JS Libraries', 'css': 'CSS Libraries'}
    # TODO: add 'img': 'Image formats' for used image formats
    # TODO: add 'video': 'Video formats' for used video formats

    for domain in result.keys():
        found_cms = False
        if len(result[domain]) > 0:
            cms_rating = Rating(_, review_show_improvements_only)
            cms_rating.set_overall(
                5.0, '##### {0}'.format(domain))
            rating += cms_rating

        for category in categories.keys():
            if category in result[domain]:
                category_rating = Rating(_, review_show_improvements_only)

                category_rating.set_overall(
                    5.0, '- {1} used: {0}'.format(', '.join(result[domain][category].keys()), categories[category]))
                rating += category_rating
            if category == 'cms' and category in result[domain]:
                found_cms = True

        if not found_cms and domain in orginal_domain:
            no_cms_rating = Rating(_, review_show_improvements_only)
            no_cms_rating.set_overall(1.0, _local('NO_CMS'))
            rating += no_cms_rating
    return rating


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
        version = item['version']
        precision = item['precision']

        if category not in domain_item:
            domain_item[category] = {}
        if name not in domain_item[category]:
            domain_item[category][name] = {}
        if version not in domain_item[category][name]:
            domain_item[category][name][version] = {
                'name': name, 'precision': precision}

        if domain_item[category][name][version]['precision'] < precision:
            obj = {}
            obj['name'] = name
            obj['precision'] = precision
            domain_item[category][version] = obj

        result[item['domain']] = domain_item
    return result


def enrich_data(data):
    # TODO: Move all additional calls into this function.
    # TODO: Make sure no additional calls are done except in this function
    # TODO: Make sure this function is ONLY called when `use_stealth = False`
    # if True:
    #     if 'matomo.php' in req_url or 'matomo.js' in req_url or 'piwik.php' in req_url or 'piwik.js' in req_url:
    #         analytics_dict = {}
    #         analytics_dict['name'] = 'Matomo'
    #         analytics_dict['url'] = req_url
    #         matomo_version = 'Matomo'

    #         check_matomo_version = 'matomo' not in result['analytics']
    #         if check_matomo_version and not use_stealth:
    #             matomo_o = urlparse(req_url)
    #             matomo_hostname = matomo_o.hostname
    #             matomo_url = '{0}://{1}/CHANGELOG.md'.format(
    #                 matomo_o.scheme, matomo_hostname)

    #             matomo_changelog_url_regex = r"(?P<url>.*)\/(matomo|piwik).(js|php)"
    #             matches = re.finditer(
    #                 matomo_changelog_url_regex, req_url, re.MULTILINE)
    #             for matchNum, match in enumerate(matches, start=1):
    #                 matomo_url = match.group('url') + '/CHANGELOG.md'

    #             # print('matomo_url', matomo_url)

    #             matomo_content = httpRequestGetContent(matomo_url)
    #             matomo_regex = r"## Matomo (?P<version>[\.0-9]+)"

    #             matches = re.finditer(
    #                 matomo_regex, matomo_content, re.MULTILINE)
    #             for matchNum, match in enumerate(matches, start=1):
    #                 matomo_version = match.group('version')
    #                 analytics_dict['version'] = matomo_version
    #                 break

    #             if 'version' in analytics_dict:
    #                 analytics_dict['versions-behind'] = -1
    #                 analytics_dict['latest-version'] = ''

    #                 matomo_version_index = 0

    #                 # TODO: Change this request
    #                 # matomo_changelog_feed = httpRequestGetContent(
    #                 #     'https://matomo.org/changelog/feed/')
    #                 matomo_changelog_feed = get_sanitized_file_content(
    #                     'data\\matomo-org-changelog-feed.txt')

    #                 matomo_changelog_regex = r"<title>Matomo (?P<version>[\.0-9]+)<\/title>"
    #                 matches = re.finditer(
    #                     matomo_changelog_regex, matomo_changelog_feed, re.MULTILINE)
    #                 for matchNum, match in enumerate(matches, start=1):
    #                     matomo_changelog_version = match.group('version')
    #                     if analytics_dict['latest-version'] == '':
    #                         analytics_dict['latest-version'] = matomo_changelog_version
    #                     # print('changelog version:', matomo_changelog_version)
    #                     if matomo_changelog_version in matomo_version:
    #                         analytics_dict['versions-behind'] = matomo_version_index
    #                         break
    #                     matomo_version_index = matomo_version_index + 1
    #         if check_matomo_version:
    #             result['analytics']['matomo'] = analytics_dict

    # if not use_stealth:
    #     # TODO: Check if we are missing any type and try to find this info
    #     if len(result['cms']) == 0:
    #         o = urlparse(url)
    #         hostname = o.hostname
    #         episerver_url = '{0}://{1}/App_Themes/Default/Styles/system.css'.format(
    #             o.scheme, hostname)
    #         content = httpRequestGetContent(episerver_url)
    #         if 'EPiServer' in content:
    #             data.append(get_default_info(
    #                 req_url, 'url', 0.5, 'cms', 'episerver'))
    #             data.append(get_default_info(
    #                 req_url, 'url', 0.5, 'tech', 'asp.net'))
    #             data.append(get_default_info(
    #                 req_url, 'url', 0.5, 'tech', 'csharp'))
    #         else:
    #             episerver_url = '{0}://{1}/util/login.aspx'.format(
    #                 o.scheme, hostname)
    #             content = httpRequestGetContent(episerver_url)
    #             if 'episerver-white.svg' in content or "__epiXSRF" in content:
    #                 data.append(get_default_info(
    #                     req_url, 'url', 0.5, 'cms', 'episerver'))
    #                 data.append(get_default_info(
    #                     req_url, 'url', 0.5, 'tech', 'asp.net'))
    #                 data.append(get_default_info(
    #                     req_url, 'url', 0.5, 'tech', 'csharp'))
    #     if len(result['cms']) == 0:
    #         # https://wordpress.org/support/article/upgrading-wordpress-extended-instructions/
    #         o = urlparse(url)
    #         hostname = o.hostname
    #         wordpress_url = '{0}://{1}/wp-includes/css/dashicons.min.css'.format(
    #             o.scheme, hostname)
    #         content = httpRequestGetContent(wordpress_url)
    #         if 'dashicons-wordpress' in content:
    #             data.append(get_default_info(
    #                 req_url, 'url', 0.5, 'cms', 'wordpress'))
    #             data.append(get_default_info(
    #                 req_url, 'url', 0.5, 'tech', 'php'))
    #         else:
    #             o = urlparse(url)
    #             hostname = o.hostname
    #             wordpress_url = '{0}://{1}/wp-login.php'.format(
    #                 o.scheme, hostname)
    #             content = httpRequestGetContent(wordpress_url)
    #             if '/wp-admin/' in content or '/wp-includes/' in content:
    #                 data.append(get_default_info(
    #                     req_url, 'url', 0.5, 'cms', 'wordpress'))
    #                 data.append(get_default_info(
    #                     req_url, 'url', 0.5, 'tech', 'php'))

    # if len(result['cms']) == 0:
    # https://typo3.org/
    # <meta name="generator" content="TYPO3 CMS" />

    return data


def identify_software(filename):
    data = list()
    rules = get_rules()

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

            url_data = lookup_request_url(req_url, rules)
            if url_data != None or len(url_data) > 0:
                data.extend(url_data)

            if 'headers' in res:
                headers = res['headers']
                header_data = lookup_response_headers(req_url, headers)
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
    # TODO: Move all this to `enrich_data` method
    data = list()

    if use_stealth:
        return data

    if raw_data['mime-types']['use']:
        raw_data['mime-types'][response_mimetype] = 'svg' in response_mimetype or 'mp4' in response_mimetype or 'webp' in response_mimetype or 'png' in response_mimetype or 'jpg' in response_mimetype or 'jpeg' in response_mimetype

    if 'svg' in response_mimetype:
        # NOTE: We don't get content for svg files currently, it would be better if we didn't need to request it once more
        svg_content = httpRequestGetContent(req_url)

        # <!-- Generator: Adobe Illustrator 16.0.4, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->
        svg_regex = r"<!-- Generator: (?P<name>[a-zA-Z ]+)[ ]{0,1}(?P<version>[0-9.]*)"
        matches = re.finditer(svg_regex, svg_content, re.MULTILINE)

        tech_name = ''
        tech_version = ''
        for matchNum, match in enumerate(matches, start=1):
            tech_name = match.group('name')
            if tech_name != None:
                tech_name = tech_name.lower().strip().replace(' ', '-')
                data.append(get_default_info(
                    req_url, 'content', 0.5, 'tech', tech_name, None))

            tech_version = match.group('version')
            if tech_version != None:
                tech_version = tech_version.lower()
                data.append(get_default_info(
                    req_url, 'content', 0.6, 'tech', tech_name, tech_version))
    if 'mp4' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        # look at: https://www.handinhandsweden.se/wp-content/uploads/se/2022/11/julvideo-startsida.mp4
        # that has videolan references and more interesting stuff
        a = 1
    if 'webp' in response_mimetype or 'png' in response_mimetype or 'jpg' in response_mimetype or 'jpeg' in response_mimetype:
        # Extract metadata to see if we can get produced application and more,
        # look at: https://skatteverket.se/images/18.1df9c71e181083ce6f6cbd/1655378197989/mobil-externwebb.jpg
        # that has adobe photoshop 21.2 (Windows) information
        a = 1

    return data


def lookup_response_content(req_url, response_mimetype, response_content, rules):
    data = list()

    if 'contents' not in rules:
        return data

    is_found = False
    for rule in rules['contents']:
        if is_found:
            break

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
        matches = re.finditer(regex, response_content, re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):
            if is_found:
                break
            match_name = None
            match_version = None

            groups = match.groupdict()

            if 'name' in groups:
                match_name = groups['name']
            if 'version' in groups:
                match_version = groups['version']

            for result in rule['results']:
                if is_found:
                    break

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
                        req_url, 'content', precision, category, name, version))
                    is_found = True
                    break
                elif raw_data['contents']['use']:
                    raw_data['contents'][match.group('debug')] = hostname

    return data


def lookup_response_content_old(req_url, response_mimetype, response_content):
    data = list()

    if 'css' in response_mimetype:
        if raw_data['css-comments']['use']:
            # (?P<comment>\/\*[^*]*\*+([^\/*][^*]*\*+)*\/)
            raw_regex = r"(?P<comment>\/\*[^*]*\*+([^\/*][^*]*\*+)*\/)"
            matches = re.finditer(raw_regex, response_content, re.MULTILINE)

            for matchNum, match in enumerate(matches, start=1):
                raw_data['css-comments'][match.group('comment')] = False
        # TODO: Handle "this" in "- CSS Libraries used: this ( 5.00 rating )", example: www.handinhandsweden.se
        # TODO: handle "this" and "the" in "- CSS Libraries used: this, animate, normalize, the ( 5.00 rating )", example: hundstallet.se
        css_regex = r"\/\*![ \t\n\r*]+(?P<name>[a-zA-Z.]+)[ ]{0,1}[v]{0,1}(?P<version>[.0-9]+){0,1}"
        matches = re.finditer(css_regex, response_content, re.MULTILINE)

        tech_name = ''
        tech_version = ''
        for matchNum, match in enumerate(matches, start=1):
            tech_name = match.group('name')
            if tech_name != None:
                tech_name = tech_name.lower().replace(' ', '-').replace('.css', '')
                data.append(get_default_info(
                    req_url, 'content', 0.5, 'css', tech_name, None))

            tech_version = match.group('version')
            if tech_version != None:
                tech_version = tech_version.lower()
                data.append(get_default_info(
                    req_url, 'content', 0.6, 'css', tech_name, tech_version))
    elif 'javascript' in response_mimetype:
        if raw_data['js-comments']['use']:
            raw_regex = r"(?P<comment>\/\*[^*]*\*+([^\/*][^*]*\*+)*\/)"
            matches = re.finditer(raw_regex, response_content, re.MULTILINE)

            for matchNum, match in enumerate(matches, start=1):
                raw_data['js-comments'][match.group('comment')] = False
        # TODO: Look at @link in comments to see if we can identify more libraries
        # TODO: Look at @source in comments to see if we can identify more libraries
        # TODO: Look at @license in comments to see if we can identify license type (add a new "Licenses" category?)
        # TODO: Add support for comments not having ! in begining ( Example: https://www.gislaved.se/sitevision/system-resource/bc115c0e1f6ff62fce025281bf04f9f70a93a23090933bb3f70b067494dfd5e6/js/webAppExternals/react_17_0.js )
        # TODO: Add support for when @license looks like this:
        # /** @ license React v17.0.2
        # * react.production.min.js
        # *
        # * Copyright (c) Facebook, Inc. and its affiliates.
        # *
        # * This source code is licensed under the MIT license found in the
        # * LICENSE file in the root directory of this source tree.
        # */
        # TODO: "for-license-information-please-see" in "JS Libraries used: for-license-information-please-see" (Example: https://www.helptohelp.se)

        js_comment_regex = r"\/\*!(?P<comment>[ \t\n\r*@a-zåäöA-ZÅÄÖ0-9\-\/\+.,:'\(\)]+)\*\/"
        matches = re.finditer(js_comment_regex, response_content, re.MULTILINE)

        for matchNum, match in enumerate(matches, start=1):
            # print('# JS', req_url, matchNum)
            tech_name = None
            tech_version = None
            precision = 0.0
            comment = match.group('comment')
            if comment == None:
                continue

            js_comment_overview_regex = r"@overview[ \t]+(?P<name>[a-zA-Z0-9\-]+)"
            overview_matches = re.finditer(
                js_comment_overview_regex, comment, re.MULTILINE)
            for matchNum, overview_match in enumerate(overview_matches, start=1):
                tech_name = overview_match.group('name')
                precision = 0.6

            js_comment_version_regex = r"@version[ \t]+[a-zA-Z]+(?P<version>[0-9\-.]+)"
            version_matches = re.finditer(
                js_comment_version_regex, comment, re.MULTILINE)
            for matchNum, version_match in enumerate(version_matches, start=1):
                tech_version = version_match.group('version')
                precision = 0.6

            if tech_name == None and tech_version == None:
                js_simple_comment_regex = r"^[*\n\r \t]+(?P<name>[a-zA-Z.\- ]+) [v]{0,1}(?P<version>[0-9\-\.]+)"
                simple_matches = re.finditer(
                    js_simple_comment_regex, comment)
                for matchNum, simple_match in enumerate(simple_matches, start=1):
                    tech_name = simple_match.group('name')
                    tech_version = simple_match.group('version')
                    precision = 0.5

            if tech_name == None and tech_version == None:
                js_simple_comment_regex = r" (?P<name>[a-zA-Z\.\-]+)(?P<version>[0-9\.\-]*)[a-zA-Z.\-]*(?P<license>.LICENSE.txt)"
                simple_matches = re.finditer(
                    js_simple_comment_regex, comment)
                for matchNum, simple_match in enumerate(simple_matches, start=1):
                    tech_name = simple_match.group('name')
                    tech_version = simple_match.group('version')
                    license_path = simple_match.group('license')
                    precision = 0.3

                    if not use_stealth and license_path != None:
                        license_url = req_url + license_path
                        license_content = httpRequestGetContent(license_url)
                        js_license_regex = r"@version[ \t]+(?P<version>[0-9\-.]+)"
                        license_matches = re.finditer(
                            js_license_regex, license_content)
                        for matchNum, license_match in enumerate(license_matches, start=1):
                            tech_version = license_match.group('version')
                            precision = 0.6

            if tech_name != None:
                tech_name = tech_name.lower().replace(
                    ' ', '-').strip('-').replace('.min.js', '').replace('.js', '')
                data.append(get_default_info(
                    req_url, 'content', precision, 'js', tech_name, None))

            if tech_version != None and tech_version != '' and tech_version != '-':
                tech_version = tech_version.lower().strip('.')
                data.append(get_default_info(
                    req_url, 'content', precision + 0.3, 'js', tech_name, tech_version))

        if raw_data['source-mapping-url']['use']:
            raw_regex = r"(?P<mapping>.*sourceMappingURL.*)"
            matches = re.finditer(raw_regex, response_content, re.MULTILINE)

            for matchNum, match in enumerate(matches, start=1):
                raw_data['source-mapping-url'][match.group('mapping')] = False

        if not use_stealth and '//# sourceMappingURL=' in response_content:
            map_url = req_url + '.map'
            map_content = httpRequestGetContent(map_url)

            js_map_regex = r"node_modules\/(?P<module>[^\/]+)"
            matches = re.finditer(js_map_regex, map_content, re.MULTILINE)

            for matchNum, match in enumerate(matches, start=1):
                module_name = match.group('module')
                if module_name != None:
                    module_name = module_name.lower().replace('.min.js', '').replace('.js', '')
                    data.append(get_default_info(
                        req_url, 'content', 0.2, 'js', module_name, None))
    return data


def get_default_info(url, method, precision, key, name, version):
    result = {}

    o = urlparse(url)
    hostname = o.hostname
    result['domain'] = hostname

    result['url'] = url
    result['method'] = method
    result['precision'] = precision
    result['category'] = key
    result['name'] = name
    result['version'] = version

    return result


def lookup_request_url(req_url, rules):
    data = list()

    if 'urls' not in rules:
        return data

    is_found = False
    for rule in rules['urls']:
        if is_found:
            break
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
            if is_found:
                break
            match_name = None
            match_version = None

            groups = match.groupdict()

            if 'name' in groups:
                match_name = groups['name']
            if 'version' in groups:
                match_version = groups['version']

            for result in rule['results']:
                if is_found:
                    break
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
                        req_url, 'url', precision, category, name, version))
                    is_found = True
                    break
                elif raw_data['urls']['use']:
                    raw_data['urls'][req_url] = False

    return data


def lookup_response_headers(req_url, headers):
    data = list()

    for header in headers:
        header_name = header['name'].upper()
        header_value = header['value'].upper()

        if raw_data['headers']['use']:
            raw_data['headers'][header_name] = header_value

        # print('header', header_name, header_value)
        tmp_data = lookup_response_header(req_url, header_name, header_value)
        if len(tmp_data) != 0:
            data.extend(tmp_data)
    return data


def lookup_response_header(req_url, header_name, header_value):
    data = list()

    if 'SET-COOKIE' in header_name:
        if 'ASP.NET_SESSIONID' in header_value:
            data.append(get_default_info(
                req_url, 'cookie', 0.5, 'webserver', 'iis', None))
            data.append(get_default_info(
                req_url, 'cookie', 0.5, 'tech', 'asp.net', None))
            if 'SAMESITE=LAX' in header_value:
                # https://learn.microsoft.com/en-us/aspnet/samesite/system-web-samesite
                data.append(get_default_info(req_url, 'header',
                            0.7, 'tech', 'asp.net', '>=4.7.2'))

            if 'JSESSIONID' in header_value:
                data.append(get_default_info(
                    req_url, 'cookie', 0.3, 'webserver', 'tomcat', None))
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'tech', 'java', None))
            if 'SITEVISION' in header_value:
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'cms', 'sitevision', None))
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'tech', 'java', None))
                data.append(get_default_info(
                    req_url, 'cookie', 0.3, 'webserver', 'tomcat', None))
            if 'SITEVISIONLTM' in header_value:
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'cms', 'sitevision', None))
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'tech', 'java', None))
                data.append(get_default_info(
                    req_url, 'cookie', 0.3, 'webserver', 'tomcat', None))
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'cms', 'sitevision-cloud', None))
    # ImageProcessedBy: ImageProcessor/2.9.0.207 - ImageProcessor.Web/4.12.0.206
    if 'IMAGEPROCESSEDBY' in header_name:
        regex = r"(?P<name>[a-zA-Z.]+)\/(?P<version>[0-9.]+)"
        matches = re.finditer(regex, header_value, re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):
            tech_name = match.group('name')
            tech_version = match.group('version')
            if tech_name != None and tech_version != None:
                tech_name = tech_name.lower()
                data.append(get_default_info(
                    req_url, 'header', 0.9, 'tech', tech_name, tech_version))
                if 'imageprocessor' in tech_name or 'imageprocessor.web' in tech_name:
                    # https://www.nuget.org/packages/ImageProcessor.Web/4.12.1#readme-body-tab
                    data.append(get_default_info(
                        req_url, 'header', 0.7, 'tech', 'asp.net', '>=4.5.2'))
                    # https://github.com/JimBobSquarePants/ImageProcessor
                    data.append(get_default_info(
                        req_url, 'header', 0.5, 'os', 'windows', None))

    if 'CONTENT-TYPE' in header_name:
        if 'image/vnd.microsoft.icon' in header_value:
            data.append(get_default_info(
                req_url, 'header', 0.3, 'os', 'windows', None))
        if 'image/webp' in header_value:
            data.append(get_default_info(
                req_url, 'header', 0.9, 'tech', 'webp', None))
    if 'X-OPNET-TRANSACTION-TRACE' in header_name:
        data.append(get_default_info(
            req_url, 'header', 0.8, 'tech', 'riverbed-steelcentral-transaction-analyzer', None))
        # https://en.wikipedia.org/wiki/OPNET
        # https://support.riverbed.com/content/support/software/opnet-performance/apptransaction-xpert.html
    if 'X-POWERED-BY' in header_name:
        if 'ASP.NET' in header_value:
            data.append(get_default_info(
                req_url, 'header', 0.5, 'webserver', 'iis', None))
            data.append(get_default_info(
                req_url, 'header', 0.5, 'tech', 'asp.net', None))
        elif 'SERVLET/' in header_value:
            data.append(get_default_info(
                req_url, 'header', 0.5, 'webserver', 'websphere', None))
            data.append(get_default_info(
                req_url, 'header', 0.5, 'tech', 'java', None))
            data.append(get_default_info(
                req_url, 'header', 0.5, 'tech', 'servlet', None))
        elif 'NEXT.JS' in header_value:
            data.append(get_default_info(
                req_url, 'header', 0.5, 'tech', 'next.js', None))

    if 'SERVER' in header_name:
        server_regex = r"^(?P<webservername>[a-zA-Z\-]+)\/{0,1}(?P<webserverversion>[0-9.]+){0,1}[ ]{0,1}\({0,1}(?P<osname>[a-zA-Z]*)\){0,1}"
        matches = re.finditer(
            server_regex, header_value, re.MULTILINE)
        webserver_name = ''
        webserver_version = ''
        os_name = ''
        for matchNum, match in enumerate(matches, start=1):
            webserver_name = match.group('webservername')
            if webserver_name != None:
                webserver_name = webserver_name.upper()

            webserver_version = match.group('webserverversion')
            if webserver_version != None:
                webserver_version = webserver_version.upper()
            os_name = match.group('osname')
            if os_name != None:
                os_name = os_name.upper()

            if 'MICROSOFT-IIS' in webserver_name:
                data.append(get_default_info(
                    req_url, 'header', 0.7, 'webserver', 'iis', None))
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'os', 'windows', None))

                if '10.0' in webserver_version:
                    data.append(get_default_info(
                        req_url, 'header', 0.8, 'os', 'windows server', '2016/2019'))
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'webserver', 'iis', '10'))
                elif '8.5' in webserver_version or '8.0' in webserver_version:
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'os', 'windows server', '2012'))
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'webserver', 'iis', '8.x'))
                elif '7.5' in webserver_version or '7.0' in webserver_version:
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'os', 'windows server', '2008'))
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'webserver', 'iis', '7.x'))
                elif '6.0' in webserver_version:
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'os', 'windows server', '2003'))
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'webserver', 'iis', '6.x'))
                elif None != webserver_version:
                    data.append(get_default_info(
                        req_url, 'header', 0.6, 'webserver', 'iis', webserver_version))
            elif 'APACHE' in webserver_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'webserver', 'apache', None))
                if webserver_version != None:
                    data.append(get_default_info(
                        req_url, 'header', 0.5, 'webserver', 'apache', webserver_version))
            elif 'NGINX' in webserver_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'webserver', 'nginx', None))
            # elif 'CLOUDFLARE' in webserver_name:
            #     data.append(get_default_info(
            #         req_url, 'header', 0.5, 'cdn', 'cloudflare'))
            # elif 'BUNNYCDN' in webserver_name:
            #     data.append(get_default_info(
            #         req_url, 'header', 0.5, 'cdn', 'bunnycdn'))
            elif 'LITESPEED' in webserver_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'webserver', 'litespeed', None))
            elif 'RESIN' in webserver_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'webserver', 'resin', None))
                if webserver_version != None:
                    data.append(get_default_info(
                        req_url, 'header', 0.5, 'webserver', 'resin', webserver_version))

            if 'UBUNTU' in os_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'os', 'ubuntu', None))
            elif 'DEBIAN' in os_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'os', 'debian', None))
            # elif None == os_name or '' == os_name:
            #     ignore = 1
            # else:
            #     print('UNHANDLED OS:', os_name)

    # x-generator
    if 'X-GENERATOR' in header_name:
        generator_regex = r"^(?P<cmsname>[a-zA-Z\-]+) {0,1}(?P<cmsversion>[0-9.]+)"
        matches = re.finditer(
            generator_regex, header_value, re.MULTILINE)
        cms_name = ''
        cms_version = ''
        for matchNum, match in enumerate(matches, start=1):
            cms_name = match.group('cmsname')
            if cms_name != None:
                cms_name = cms_name.lower()
                data.append(get_default_info(
                    req_url, 'header', 0.4, 'cms', cms_name, None))

            cms_version = match.group('cmsversion')
            if cms_version != None:
                cms_version = cms_version.lower()
                data.append(get_default_info(
                    req_url, 'header', 0.8, 'cms', cms_name, cms_version))

        data.append(get_default_info(
            req_url, 'header', 0.4, 'webserver', 'nginx', None))
    if 'X-NGINX-' in header_name:
        data.append(get_default_info(
            req_url, 'header', 0.4, 'webserver', 'nginx', None))
    if 'X-NEXTJS-' in header_name:
        data.append(get_default_info(
            req_url, 'header', 0.4, 'tech', 'next.js', None))
    if 'X-VARNISH' in header_name:
        # TODO: Check what they mean
        # X-Varnish: 1079078756 1077313267
        data.append(get_default_info(
            req_url, 'header', 0.5, 'tech', 'varnish', None))
    if 'VIA' in header_name and 'VARNISH' in header_value:
        # TODO: Check if it contains version number and if we can check for it
        # Via: 1.1 varnish
        data.append(get_default_info(
            req_url, 'header', 0.5, 'tech', 'varnish', None))
    if 'X-ASPNET-VERSION' in header_name:
        data.append(get_default_info(
            req_url, 'header', 0.5, 'webserver', 'iis', None))
        data.append(get_default_info(
            req_url, 'header', 0.5, 'tech', 'asp.net', None))
        # TODO: Fix validation of header_value, it can now include infected data
        data.append(get_default_info(
            req_url, 'header', 0.8, 'tech', 'asp.net', header_value))
    if 'CONTENT-SECURITY-POLICY' in header_name:
        regex = r"(?P<name>[a-zA-Z\-]+) (?P<value>[^;]+);*[ ]*"
        matches = re.finditer(
            regex, header_value, re.MULTILINE)
        for matchNum, match in enumerate(matches, start=1):
            # TODO: look at more values and uses in CSP
            csp_rule_name = match.group('name').upper()
            csp_rule_value = match.group('value').upper()
            if 'DL.EPISERVER.NET' in csp_rule_value:
                data.append(get_default_info(
                    req_url, 'header', 0.7, 'cms', 'episerver', None))
                data.append(get_default_info(
                    req_url, 'header', 0.4, 'tech', 'asp.net', None))
                data.append(get_default_info(
                    req_url, 'header', 0.4, 'tech', 'tech', None))

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
        'tracking_validator', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    # TODO: Change this to normal logic for texts
    # print(_local('TEXT_RUNNING_TEST'))
    print('## Test: 25 - Software (Alpha)')

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    (rating, result_dict) = get_rating_from_sitespeed(url, _local, _)

    print('raw_data', raw_data)

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)
