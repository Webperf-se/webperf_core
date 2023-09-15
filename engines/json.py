# -*- coding: utf-8 -*-
from engines.utils import use_item
import json


def add_site(input_filename, url, input_skip, input_take):
    sites = read_sites(input_filename, input_skip, input_take)
    # print(sites)
    id = len(sites)
    sites.append([id, url])
    write_sites(input_filename, sites)

    print(_('TEXT_WEBSITE_URL_ADDED').format(url))

    return sites


def delete_site(input_filename, url, input_skip, input_take):
    sites = read_sites(input_filename, input_skip, input_take)
    tmpSites = list()
    for site in sites:
        site_id = site[0]
        site_url = site[1]
        if (url != site_url):
            tmpSites.append([site_id, site_url])

    write_sites(input_filename, tmpSites)

    print(_('TEXT_WEBSITE_URL_DELETED').format(site_url))

    return tmpSites


def read_sites(input_filename, input_skip, input_take):
    sites = list()
    with open(input_filename) as json_input_file:
        data = json.load(json_input_file)
        current_index = 0
        for site in data["sites"]:
            if use_item(current_index, input_skip, input_take):
                sites.append([site["id"], site["url"]])
            current_index += 1
    return sites


def write_sites(output_filename, sites):
    with open(output_filename, 'w') as outfile:
        # json require us to have an object as root element
        jsonSites = list()
        current_siteid = 0
        for site in sites:
            jsonSites.append({
                'id': site[0],
                'url': site[1]
            })
            current_siteid += 1

        sitesContainerObject = {
            "sites": jsonSites
        }
        json.dump(sitesContainerObject, outfile)


def read_tests(input_filename, input_skip, input_take):
    result = list()
    with open(input_filename) as json_input_file:
        data = json.load(json_input_file)
        current_index = 0
        for test_result in data["tests"]:
            if use_item(current_index, input_skip, input_take):
                if "type_of_test" in test_result and test_result["type_of_test"] == 22:
                    result.append([test_result["date"], test_result["data"]])
                else:
                    print('WARNING: ARE YOU USING CORRECT FILE?!')
            current_index += 1
    print('result', result)
    return result


def write_tests(output_filename, siteTests, sites):
    with open(output_filename, 'w') as outfile:
        # json require us to have an object as root element
        testsContainerObject = {
            "tests": siteTests
        }
        json.dump(testsContainerObject, outfile)
