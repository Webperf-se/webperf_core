# -*- coding: utf-8 -*-
import os
from pathlib import Path
import shutil
from engines.utils import use_item
import json
import re

sites = list()


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


def get_url_from_file_content(input_filename):
    try:
        with open(input_filename, 'r', encoding='utf-8') as file:
            data = file.read(1024)
            regex = r"\"_url\":[ ]{0,1}\"(?P<url>[^\"]+)\""
            matches = re.finditer(regex, data, re.MULTILINE)
            for matchNum, match in enumerate(matches, start=1):
                return match.group('url')
    except:
        print('error in get_local_file_content. No such file or directory: {0}'.format(
            input_filename))
        return None

    return None


def read_sites(input_filename, input_skip, input_take):

    if len(sites) > 0:
        return sites

    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    data_dir = os.path.join(dir, 'data') + os.path.sep

    dirs = os.listdir(data_dir)

    urls = {}

    for result_dir in dirs:
        if input_take != -1 and len(urls) >= input_take:
            break

        if not result_dir.startswith('results-'):
            continue
        path = os.path.join(
            data_dir, result_dir)

        correct_path = full_path = os.path.join(
            path, 'browsertime.har')

        # cleanup
        cleanup_dirs = os.listdir(path)
        for cleanup_dir in cleanup_dirs:
            if cleanup_dir != 'browsertime.har':
                cleanup_path = os.path.join(path, cleanup_dir)
                if os.path.isfile(cleanup_path):
                    os.remove(cleanup_path)
                else:
                    shutil.rmtree(cleanup_path)

        if not os.path.exists(full_path):
            found = False
            sub_dirs = os.listdir(path)
            for sub_dir in sub_dirs:
                if 'pages' != sub_dir:
                    continue
                found = True

            if not found:
                continue

            pages_path = path = os.path.join(
                path, 'pages') + os.path.sep

            found = False
            sub_dirs = os.listdir(path)
            for sub_dir in sub_dirs:
                found = True
                path = os.path.join(
                    path, sub_dir) + os.path.sep

            if not found:
                continue

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

            if not os.path.isfile(full_path):
                continue

            os.rename(full_path, correct_path)
            shutil.rmtree(pages_path)
            full_path = correct_path

        # No need to read all content, just read the first 1024 bytes as our url will be there
        # we are doing this for performance
        url = get_url_from_file_content(full_path)
        urls[url] = full_path

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
