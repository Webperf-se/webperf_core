# -*- coding: utf-8 -*-
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
except:
    # If cache_when_possible variable is not set in config.py this will be the default
    use_cache = False

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
    result_folder_name = os.path.join(
        'data', 'results-{0}'.format(str(uuid.uuid4())))
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

    data = identify_software(filename, origin_domain)
    data = enrich_data(data, origin_domain)
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
                  'analytics', 'tech', 'meta',
                  'js', 'css',
                  'lang', 'img', 'video',
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

    for category in categories:
        if category in item:

            if category == 'security':
                for key in item[category].keys():
                    category_rating = Rating(_, review_show_improvements_only)
                    if 'screaming.' in key:
                        category_rating.set_integrity_and_security(
                            2.0, _local('TEXT_USED_{0}'.format(
                                category.upper())).format(domain))
                    else:
                        category_rating.set_integrity_and_security(
                            4.0, _local('TEXT_USED_{0}'.format(
                                category.upper())).format(domain))
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
                'name': name, 'precision': precision}

        if domain_item[category][name][version]['precision'] < precision:
            obj = {}
            obj['name'] = name
            obj['precision'] = precision
            domain_item[category][name][version] = obj

        result[item['domain']] = domain_item
    return result


def enrich_data(data, orginal_domain):

    cms = None
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

    data.extend(tmp_list)

    if len(testing) > 0:
        raw_data['test'][orginal_domain] = {
            'cms': cms,
            'test': testing
        }
    # TODO: Move all additional calls into this function.
    # TODO: Make sure no additional calls are done except in this function
    # TODO: Make sure this function is ONLY called when `use_stealth = False`
    # TODO: Check if it is any idea to check matomo version, if so, do it here
    # TODO: Consider if results from additional calls can use cache
    # TODO: Check if we are missing any type and try to find this info
    # TODO: Additional check for Episerver
    # TODO: Check for Umbraco ( /umbraco )

    return data


def identify_software(filename, origin_domain):
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
            match_name = None
            match_version = None

            groups = match.groupdict()

            if 'name' in groups:
                match_name = groups['name']
            if 'version' in groups:
                match_version = groups['version']

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
                        req_url, 'content', precision, category, name, version))
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
        name = name.lower().strip()

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
