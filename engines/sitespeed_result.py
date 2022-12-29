# -*- coding: utf-8 -*-
import os
from pathlib import Path
from engines.utils import use_item
import json
import re


def add_site(input_filename, url, input_skip, input_take):
    sites = list()
#     sites = read_sites(input_filename, input_skip, input_take)
#     # print(sites)
#     id = len(sites)
#     sites.append([id, url])
#     write_sites(input_filename, sites)

#     print(_('TEXT_WEBSITE_URL_ADDED').format(url))

    return sites


def delete_site(input_filename, url, input_skip, input_take):
    tmpSites = list()
#     sites = read_sites(input_filename, input_skip, input_take)
#     tmpSites = list()
#     for site in sites:
#         site_id = site[0]
#         site_url = site[1]
#         if (url != site_url):
#             tmpSites.append([site_id, site_url])

#     write_sites(input_filename, tmpSites)

#     print(_('TEXT_WEBSITE_URL_DELETED').format(site_url))

    return tmpSites


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


def read_sites(input_filename, input_skip, input_take):
    sites = list()
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    data_dir = os.path.join(dir, 'data') + os.path.sep

    dirs = os.listdir(data_dir)

    urls = {}

    for result_dir in dirs:
        if not result_dir.startswith('results-'):
            continue
        path = os.path.join(
            data_dir, result_dir)

        found = False
        sub_dirs = os.listdir(path)
        for sub_dir in sub_dirs:
            if 'pages' != sub_dir:
                continue
            found = True

        if not found:
            continue

        path = os.path.join(
            path, 'pages') + os.path.sep

        found = False
        sub_dirs = os.listdir(path)
        for sub_dir in sub_dirs:
            found = True
            path = os.path.join(
                path, sub_dir) + os.path.sep

        if not found:
            continue

        full_path = None
        sub_dirs = os.listdir(path)
        for sub_dir in sub_dirs:
            if '1.html' == sub_dir or '2.html' == sub_dir or 'index.html' == sub_dir or 'metrics.html' == sub_dir:
                continue
            if 'data' != sub_dir:
                full_path = os.path.join(
                    path, sub_dir, 'data', 'browsertime.har')
            else:
                full_path = os.path.join(
                    path, sub_dir, 'browsertime.har')

        if full_path == None:
            continue

        # Fix for content having unallowed chars
        json_content = get_sanitized_file_content(full_path)
        if True:
            data = json.loads(json_content)
            if 'log' in data:
                data = data['log']
            if 'pages' in data:
                data = data['pages']

            for page in data:
                if '_url' in page:
                    url = page['_url']
                    urls[url] = full_path
                    break

    current_index = 0
    for tmp_url in urls.keys():
        sites.append([urls[tmp_url], tmp_url])
        current_index += 1

    return sites


# def write_sites(output_filename, sites):
#     with open(output_filename, 'w') as outfile:
#         # json require us to have an object as root element
#         jsonSites = list()
#         current_siteid = 0
#         for site in sites:
#             jsonSites.append({
#                 'id': site[0],
#                 'url': site[1]
#             })
#             current_siteid += 1

#         sitesContainerObject = {
#             "sites": jsonSites
#         }
#         json.dump(sitesContainerObject, outfile)


# def read_tests(input_filename, input_skip, input_take):
#     result = list()
#     with open(input_filename) as json_input_file:
#         data = json.load(json_input_file)
#         current_index = 0
#         for test_result in data["tests"]:
#             if use_item(current_index, input_skip, input_take):
#                 if "type_of_test" in test_result and test_result["type_of_test"] == 22:
#                     result.append([test_result["date"], test_result["data"]])
#                 else:
#                     print('WARNING: ARE YOU USING CORRECT FILE?!')
#             current_index += 1
#     print('result', result)
#     return result


# def write_tests(output_filename, siteTests):
#     with open(output_filename, 'w') as outfile:
#         # json require us to have an object as root element
#         testsContainerObject = {
#             "tests": siteTests
#         }
#         json.dump(testsContainerObject, outfile)
