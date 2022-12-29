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
    rating = Rating(_, review_show_improvements_only)

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

    data = list()

    import json
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

            url_data = lookup_request_url(req_url)
            if url_data != None or len(url_data) > 0:
                data.extend(url_data)

            if 'content' in res and 'text' in res['content']:
                response_content = res['content']['text']
                response_mimetype = res['content']['mimeType']
                content_data = lookup_response_content(
                    req_url, response_mimetype, response_content)
                if content_data != None or len(content_data) > 0:
                    data.extend(content_data)

            # TODO: Check for https://docs.2sxc.org/index.html ?

            # if 'matomo.php' in req_url or 'matomo.js' in req_url or 'piwik.php' in req_url or 'piwik.js' in req_url:
            #     analytics_dict = {}
            #     analytics_dict['name'] = 'Matomo'
            #     analytics_dict['url'] = req_url
            #     matomo_version = 'Matomo'

            #     check_matomo_version = 'matomo' not in result['analytics']
            #     if check_matomo_version and not use_stealth:
            #         matomo_o = urlparse(req_url)
            #         matomo_hostname = matomo_o.hostname
            #         matomo_url = '{0}://{1}/CHANGELOG.md'.format(
            #             matomo_o.scheme, matomo_hostname)

            #         matomo_changelog_url_regex = r"(?P<url>.*)\/(matomo|piwik).(js|php)"
            #         matches = re.finditer(
            #             matomo_changelog_url_regex, req_url, re.MULTILINE)
            #         for matchNum, match in enumerate(matches, start=1):
            #             matomo_url = match.group('url') + '/CHANGELOG.md'

            #         # print('matomo_url', matomo_url)

            #         matomo_content = httpRequestGetContent(matomo_url)
            #         matomo_regex = r"## Matomo (?P<version>[\.0-9]+)"

            #         matches = re.finditer(
            #             matomo_regex, matomo_content, re.MULTILINE)
            #         for matchNum, match in enumerate(matches, start=1):
            #             matomo_version = match.group('version')
            #             analytics_dict['version'] = matomo_version
            #             break

            #         if 'version' in analytics_dict:
            #             analytics_dict['versions-behind'] = -1
            #             analytics_dict['latest-version'] = ''

            #             matomo_version_index = 0

            #             # TODO: Change this request
            #             # matomo_changelog_feed = httpRequestGetContent(
            #             #     'https://matomo.org/changelog/feed/')
            #             matomo_changelog_feed = get_sanitized_file_content(
            #                 'data\\matomo-org-changelog-feed.txt')

            #             matomo_changelog_regex = r"<title>Matomo (?P<version>[\.0-9]+)<\/title>"
            #             matches = re.finditer(
            #                 matomo_changelog_regex, matomo_changelog_feed, re.MULTILINE)
            #             for matchNum, match in enumerate(matches, start=1):
            #                 matomo_changelog_version = match.group('version')
            #                 if analytics_dict['latest-version'] == '':
            #                     analytics_dict['latest-version'] = matomo_changelog_version
            #                 # print('changelog version:', matomo_changelog_version)
            #                 if matomo_changelog_version in matomo_version:
            #                     analytics_dict['versions-behind'] = matomo_version_index
            #                     break
            #                 matomo_version_index = matomo_version_index + 1
            #     if check_matomo_version:
            #         result['analytics']['matomo'] = analytics_dict

            if 'headers' in res:
                headers = res['headers']
                header_data = lookup_response_headers(req_url, headers)
                if header_data != None or len(header_data) > 0:
                    data.extend(header_data)

            # TODO: Add logic to look in markup and text based resources
            # <meta name=generator content="Hugo 0.108.0">

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

    result = {}

    for item in data:
        domain_item = None
        if item['domain'] not in result:
            domain_item = {}
        else:
            domain_item = result[item['domain']]

        key = None
        if 'tech' in item:
            key = 'tech'
        elif 'webserver' in item:
            key = 'webserver'
        elif 'cms' in item:
            key = 'cms'
        elif 'os' in item:
            key = 'os'
        elif 'analytics' in item:
            key = 'analytics'
        elif 'cdn' in item:
            key = 'cdn'
        elif 'js' in item:
            key = 'js'
        elif 'css' in item:
            key = 'css'
        else:
            key = 'unknown'

        value = item[key]
        pos = value.find(' ')
        key2 = value
        if pos > 0:
            key2 = value[:pos]

        if key not in domain_item:
            domain_item[key] = {}
        if key2 not in domain_item[key]:
            domain_item[key][key2] = {
                'name': value, 'precision': 0.0}

        if domain_item[key][key2]['precision'] < item['precision']:
            obj = {}
            obj['name'] = value
            obj['precision'] = item['precision']
            domain_item[key][key2] = obj

        result[item['domain']] = domain_item

    # pretty_result = json.dumps(result, indent=4)
    # print('result', pretty_result)

    found_cms = False
    for domain in result.keys():
        if found_cms:
            break
        if 'cms' in result[domain]:
            for cms_name in result[domain]['cms']:
                cms_rating = Rating(_, review_show_improvements_only)
                cms_rating.set_overall(
                    5.0, '- CMS used: {0}'.format(cms_name.capitalize()))
                rating += cms_rating
                found_cms = True
                break

    if not found_cms:
        no_cms_rating = Rating(_, review_show_improvements_only)
        no_cms_rating.set_overall(1.0, _local('NO_CMS'))
        rating += no_cms_rating

    return (rating, result)


def lookup_response_content(req_url, response_mimetype, response_content):
    data = list()

    if 'html' in response_mimetype:
        generator_regex = r"<meta name=['|\"]{0,1}generator['|\"]{0,1} content=['|\"]{0,1}(?P<cmsname>[a-zA-Z]+)[ ]{0,1}(?P<cmsversion>[0-9.]*)"
        matches = re.finditer(generator_regex, response_content, re.MULTILINE)

        cms_name = ''
        cms_version = ''
        for matchNum, match in enumerate(matches, start=1):
            cms_name = match.group('cmsname')
            if cms_name != None:
                cms_name = cms_name.lower()
                data.append(get_default_info(
                    req_url, 'content', 0.4, 'cms', cms_name))

            cms_version = match.group('cmsversion')
            if cms_version != None:
                cms_version = cms_version.lower()
                data.append(get_default_info(
                    req_url, 'content', 0.6, 'cms', "{0} {1}".format(cms_name, cms_version)))

    elif 'css' in response_mimetype:
        css_regex = r"\/\*![ \t\n\r*]+(?P<name>[a-zA-Z.]+)[ ]{0,1}[v]{0,1}(?P<version>[.0-9]+){0,1}"
        matches = re.finditer(css_regex, response_content, re.MULTILINE)

        tech_name = ''
        tech_version = ''
        for matchNum, match in enumerate(matches, start=1):
            tech_name = match.group('name')
            if tech_name != None:
                tech_name = tech_name.lower().replace(' ', '-')
                data.append(get_default_info(
                    req_url, 'content', 0.5, 'css', tech_name))

            tech_version = match.group('version')
            if tech_version != None:
                tech_version = tech_version.lower()
                data.append(get_default_info(
                    req_url, 'content', 0.6, 'css', "{0} {1}".format(tech_name, tech_version)))
    elif 'javascript' in response_mimetype:
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
                js_simple_comment_regex = r" (?P<name>[a-zA-Z.\-]+)(?P<license>.LICENSE.txt)"
                simple_matches = re.finditer(
                    js_simple_comment_regex, comment)
                for matchNum, simple_match in enumerate(simple_matches, start=1):
                    tech_name = simple_match.group('name')
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
                tech_name = tech_name.lower().replace(' ', '-').strip('-')
                data.append(get_default_info(
                    req_url, 'content', precision, 'js', tech_name))

            if tech_version != None and tech_version != '-':
                tech_version = tech_version.lower()
                data.append(get_default_info(
                    req_url, 'content', precision + 0.3, 'js', "{0} {1}".format(tech_name, tech_version)))

        if not use_stealth and '//# sourceMappingURL=' in response_content:
            map_url = req_url + '.map'
            map_content = httpRequestGetContent(map_url)

            js_map_regex = r"node_modules\/(?P<module>[^\/]+)"
            matches = re.finditer(js_map_regex, map_content, re.MULTILINE)

            for matchNum, match in enumerate(matches, start=1):
                module_name = match.group('module')
                if module_name != None:
                    module_name = module_name.lower()
                    data.append(get_default_info(
                        req_url, 'content', 0.5, 'js', module_name))

    elif 'svg' in response_mimetype:
        # TODO: We don't get content for svg files currently, can we change that?
        svg_regex = r"<!-- Generator: (?P<name>[a-zA-Z ]+)[ ]{0,1}(?P<version>[0-9.]*)"
        matches = re.finditer(svg_regex, response_content, re.MULTILINE)

        tech_name = ''
        tech_version = ''
        for matchNum, match in enumerate(matches, start=1):
            tech_name = match.group('name')
            if tech_name != None:
                tech_name = tech_name.lower().replace(' ', '-')
                data.append(get_default_info(
                    req_url, 'content', 0.5, 'tech', tech_name))

            tech_version = match.group('version')
            if tech_version != None:
                tech_version = tech_version.lower()
                data.append(get_default_info(
                    req_url, 'content', 0.6, 'tech', "{0} {1}".format(tech_name, tech_version)))

    return data


def get_default_info(url, method, precision, key, value):
    result = {}

    o = urlparse(url)
    hostname = o.hostname
    result['domain'] = hostname

    result['url'] = url
    result['method'] = method
    result['precision'] = precision
    result[key] = value

    return result


def lookup_request_url(req_url):
    data = list()

    # print('# ', req_url)
    if '.aspx' in req_url or '.ashx' in req_url:
        data.append(get_default_info(req_url, 'url', 0.5, 'tech', 'asp.net'))

    if '/contentassets/' in req_url or '/globalassets/' in req_url or 'epi-util/find.js' in req_url or 'dl.episerver.net' in req_url:
        data.append(get_default_info(req_url, 'url', 0.1, 'tech', 'asp.net'))
        data.append(get_default_info(req_url, 'url', 0.5, 'cms', 'episerver'))
        data.append(get_default_info(req_url, 'url', 0.5, 'tech', 'csharp'))
    elif '/sitevision/' in req_url:
        data.append(get_default_info(req_url, 'url', 0.1, 'tech', 'java'))
        data.append(get_default_info(req_url, 'url', 0.5, 'cms', 'sitevision'))
        data.append(get_default_info(
            req_url, 'url', 0.5, 'webserver', 'tomcat'))
    elif '/wp-content/' in req_url or '/wp-content/' in req_url:
        # https://wordpress.org/support/article/upgrading-wordpress-extended-instructions/
        data.append(get_default_info(req_url, 'url', 0.1, 'tech', 'php'))
        data.append(get_default_info(req_url, 'url', 0.5, 'cms', 'wordpress'))
    elif '/typo3temp/' in req_url or '/typo3conf/' in req_url or '/t3olayout/' in req_url:
        # https://typo3.org/
        data.append(get_default_info(req_url, 'url', 0.1, 'tech', 'php'))
        data.append(get_default_info(req_url, 'url', 0.5, 'cms', 'typo3'))

        # TODO: Check for https://docs.2sxc.org/index.html ?

    if 'matomo.php' in req_url or 'matomo.js' in req_url or 'piwik.php' in req_url or 'piwik.js' in req_url:
        data.append(get_default_info(req_url, 'url', 0.5, 'tech', 'matomo'))
    if '.php' in req_url:
        data.append(get_default_info(req_url, 'url', 0.5, 'tech', 'php'))
    if '.webp' in req_url:
        data.append(get_default_info(req_url, 'url', 0.5, 'tech', 'webp'))
    if '.webm' in req_url:
        data.append(get_default_info(req_url, 'url', 0.5, 'tech', 'webm'))
    if '.js' in req_url:
        # TODO: check framework name and version in comment
        # TODO: check if ".map" is mentioned in file, if so, check it for above framework name and version
        # TODO: check use of node_modules
        # https://www.tranemo.se/wp-includes/js/jquery/jquery.min.js?ver=3.6.1
        # https://www.tranemo.se/wp-includes/js/dist/vendor/regenerator-runtime.min.js?ver=0.13.9
        data.append(get_default_info(req_url, 'url', 0.5, 'tech', 'js'))
    if '.svg' in req_url:
        # TODO: Check Generator comment
        # https://www.pajala.se/static/gfx/pajala-kommunvapen.svg
        # <!-- Generator: Adobe Illustrator 24.0.2, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->
        # https://start.stockholm/ui/assets/img/logotype.svg
        # <!-- Generator: Adobe Illustrator 19.2.1, SVG Export Plug-In . SVG Version: 6.00 Build 0)  -->
        data.append(get_default_info(
            req_url, 'url', 0.5, 'tech', 'svg'))
    if '/imagevault/' in req_url:
        data.append(get_default_info(
            req_url, 'url', 0.5, 'tech', 'imagevault'))

    return data


def lookup_response_headers(req_url, headers):
    data = list()

    for header in headers:
        header_name = header['name'].upper()
        header_value = header['value'].upper()

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
                req_url, 'cookie', 0.5, 'webserver', 'iis'))
            data.append(get_default_info(
                req_url, 'cookie', 0.5, 'tech', 'asp.net'))
            if 'SAMESITE=LAX' in header_value:
                # https://learn.microsoft.com/en-us/aspnet/samesite/system-web-samesite
                data.append(get_default_info(req_url, 'header',
                            0.7, 'tech', 'asp.net >=4.7.2'))

            if 'JSESSIONID' in header_value:
                data.append(get_default_info(
                    req_url, 'cookie', 0.3, 'webserver', 'tomcat'))
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'tech', 'java'))
            if 'SITEVISION' in header_value:
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'cms', 'sitevision'))
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'tech', 'java'))
                data.append(get_default_info(
                    req_url, 'cookie', 0.3, 'webserver', 'tomcat'))
            if 'SITEVISIONLTM' in header_value:
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'cms', 'sitevision'))
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'tech', 'java'))
                data.append(get_default_info(
                    req_url, 'cookie', 0.3, 'webserver', 'tomcat'))
                data.append(get_default_info(
                    req_url, 'cookie', 0.5, 'cms', 'sitevision-cloud'))
    if 'CONTENT-TYPE' in header_name:
        if 'image/vnd.microsoft.icon' in header_value:
            data.append(get_default_info(
                req_url, 'header', 0.3, 'os', 'windows'))
    if 'X-OPNET-TRANSACTION-TRACE' in header_name:
        data.append(get_default_info(
            req_url, 'header', 0.8, 'tech', 'riverbed-steelcentral-transaction-analyzer'))
        # https://en.wikipedia.org/wiki/OPNET
        # https://support.riverbed.com/content/support/software/opnet-performance/apptransaction-xpert.html
    if 'X-POWERED-BY' in header_name:
        if 'ASP.NET' in header_value:
            data.append(get_default_info(
                req_url, 'header', 0.5, 'webserver', 'iis'))
            data.append(get_default_info(
                req_url, 'header', 0.5, 'tech', 'asp.net'))
        if 'SERVLET/' in header_value:
            data.append(get_default_info(
                req_url, 'header', 0.5, 'webserver', 'websphere'))
            data.append(get_default_info(
                req_url, 'header', 0.5, 'tech', 'java'))
            data.append(get_default_info(
                req_url, 'header', 0.5, 'tech', 'servlet'))
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
                    req_url, 'header', 0.7, 'webserver', 'iis'))
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'os', 'windows'))

                if '10.0' in webserver_version:
                    data.append(get_default_info(
                        req_url, 'header', 0.8, 'os', 'windows server 2016/2019'))
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'webserver', 'iis 10'))
                elif '8.5' in webserver_version or '8.0' in webserver_version:
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'os', 'windows server 2012'))
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'webserver', 'iis 8.x'))
                elif '7.5' in webserver_version or '7.0' in webserver_version:
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'os', 'windows server 2008'))
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'webserver', 'iis 7.x'))
                elif '6.0' in webserver_version:
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'os', 'windows server 2003'))
                    data.append(get_default_info(
                        req_url, 'header', 0.9, 'webserver', 'iis 6.x'))
                elif None != webserver_version:
                    data.append(get_default_info(
                        req_url, 'header', 0.6, 'webserver', 'iis {0}'.format(
                            webserver_version)))
            elif 'APACHE' in webserver_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'webserver', 'apache'))
                if webserver_version != None:
                    data.append(get_default_info(
                        req_url, 'header', 0.5, 'webserver', 'apache {0}'.format(
                            webserver_version)))
            elif 'NGINX' in webserver_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'webserver', 'nginx'))
            elif 'CLOUDFLARE' in webserver_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'cdn', 'cloudflare'))
            elif 'BUNNYCDN' in webserver_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'cdn', 'bunnycdn'))
            elif 'LITESPEED' in webserver_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'webserver', 'litespeed'))
            elif 'RESIN' in webserver_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'webserver', 'resin'))
                if webserver_version != None:
                    data.append(get_default_info(
                        req_url, 'header', 0.5, 'webserver', 'resin {0}'.format(
                            webserver_version)))

            if 'UBUNTU' in os_name:
                data.append(get_default_info(
                    req_url, 'header', 0.5, 'os', 'ubuntu'))
            elif None == os_name or '' == os_name:
                ignore = 1
            else:
                print('UNHANDLED OS:', os_name)

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
                    req_url, 'header', 0.4, 'cms', cms_name))

            cms_version = match.group('cmsversion')
            if cms_version != None:
                cms_version = cms_version.lower()
                data.append(get_default_info(
                    req_url, 'header', 0.8, 'cms', "{0} {1}".format(cms_name, cms_version)))

        data.append(get_default_info(
            req_url, 'header', 0.4, 'webserver', 'nginx'))
    if 'X-NGINX-' in header_name:
        data.append(get_default_info(
            req_url, 'header', 0.4, 'webserver', 'nginx'))
    if 'X-VARNISH' in header_name:
        # TODO: Check what they mean
        # X-Varnish: 1079078756 1077313267
        data.append(get_default_info(
            req_url, 'header', 0.5, 'tech', 'varnish'))
    if 'VIA' in header_name and 'VARNISH' in header_value:
        # TODO: Check if it contains version number and if we can check for it
        # Via: 1.1 varnish
        data.append(get_default_info(
            req_url, 'header', 0.5, 'tech', 'varnish'))
    if 'X-ASPNET-VERSION' in header_name:
        data.append(get_default_info(
            req_url, 'header', 0.5, 'webserver', 'iis'))
        data.append(get_default_info(
            req_url, 'header', 0.5, 'tech', 'asp.net'))
        # TODO: Fix validation of header_value, it can now include infected data
        data.append(get_default_info(
            req_url, 'header', 0.8, 'tech', 'asp.net {0}'.format(
                header_value)))
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
                    req_url, 'header', 0.7, 'cms', 'episerver'))
                data.append(get_default_info(
                    req_url, 'header', 0.4, 'tech', 'asp.net'))
                data.append(get_default_info(
                    req_url, 'header', 0.4, 'tech', 'tech'))

    return data


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

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)
