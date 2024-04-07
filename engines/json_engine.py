# -*- coding: utf-8 -*-
import json
from engines.utils import use_item

def add_site(input_filename, url, input_skip, input_take):
    sites = read_sites(input_filename, input_skip, input_take)
    site_id = len(sites)
    sites.append([site_id, url])
    write_sites(input_filename, sites)

    return sites


def delete_site(input_filename, url, input_skip, input_take):
    sites = read_sites(input_filename, input_skip, input_take)
    tmp_sites = []
    for site in sites:
        site_id = site[0]
        site_url = site[1]
        if url != site_url:
            tmp_sites.append([site_id, site_url])

    write_sites(input_filename, tmp_sites)

    return tmp_sites


def read_sites(input_filename, input_skip, input_take):
    sites = []
    with open(input_filename, encoding='utf-8') as json_input_file:
        data = json.load(json_input_file)
        current_index = 0
        for site in data["sites"]:
            if use_item(current_index, input_skip, input_take):
                sites.append([site["id"], site["url"]])
            current_index += 1
    return sites


def write_sites(output_filename, sites):
    with open(output_filename, 'w', encoding='utf-8') as outfile:
        # json require us to have an object as root element
        json_sites = []
        current_siteid = 0
        for site in sites:
            json_sites.append({
                'id': site[0],
                'url': site[1]
            })
            current_siteid += 1

        container_object = {
            "sites": json_sites
        }
        json.dump(container_object, outfile)


def read_tests(input_filename, input_skip, input_take):
    result = []
    with open(input_filename, encoding='utf-8') as json_input_file:
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


def write_tests(output_filename, site_tests, _):
    with open(output_filename, 'w', encoding='utf-8') as outfile:
        # json require us to have an object as root element
        container_object = {
            "tests": site_tests
        }
        json.dump(container_object, outfile)
