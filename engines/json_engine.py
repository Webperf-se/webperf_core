# -*- coding: utf-8 -*-
import json
from engines.utils import use_item

def add_site(input_filename, url, input_skip, input_take):
    """
    Adds a site to a list of sites in a JSON file.

    This function reads a JSON file using the `read_sites` function and
    creates a new list of sites. It then adds a new site with the specified URL to the list.
    The new site's ID is the current length of the list of sites.
    The function then writes the updated list of sites back to the JSON file using the
    `write_sites` function.

    Args:
        input_filename (str): The name of the input file.
        url (str): The URL of the site to be added.
        input_skip (int): The number of items to skip at the beginning when reading the file.
        input_take (int): The number of items to take after skipping when reading the file.

    Returns:
        sites (list[tuple]): A list of tuples, where each tuple contains a site ID and
                             a site URL, including the newly added site.

    Raises:
        IOError: If there is an issue with file I/O.
    """
    sites = read_sites(input_filename, input_skip, input_take)
    site_id = len(sites)
    sites.append([site_id, url])
    write_sites(input_filename, sites)

    return sites


def delete_site(input_filename, url, input_skip, input_take):
    """
    Deletes a site from a list of sites in a JSON file.

    This function reads a JSON file using the `read_sites` function and
    creates a new list of sites excluding the site with the specified URL.
    It then writes the new list of sites back to the JSON file using the `write_sites` function.

    Args:
        input_filename (str): The name of the input file.
        url (str): The URL of the site to be deleted.
        input_skip (int): The number of items to skip at the beginning when reading the file.
        input_take (int): The number of items to take after skipping when reading the file.

    Returns:
        tmp_sites (list[tuple]): A list of tuples, where each tuple contains a site ID and
        a site URL, excluding the site with the specified URL.

    Raises:
        IOError: If there is an issue with file I/O.
    """
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
    """
    Reads a list of sites from a JSON file.

    This function reads a JSON file and creates a list of sites.
    Each site is represented as a tuple containing a site ID and a site URL.
    The function only includes items that pass the `use_item` function.

    Args:
        input_filename (str): The name of the input file.
        input_skip (int): The number of items to skip at the beginning.
        input_take (int): The number of items to take after skipping.

    Returns:
        sites (list[tuple]): A list of tuples,
        where each tuple contains a site ID and a site URL.

    Raises:
        IOError: If there is an issue with file I/O.
    """
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
    """
    Writes a list of sites to a JSON file.

    This function takes a list of tuples, where each tuple represents a site.
    Each tuple contains a site ID and a site URL.
    It creates a Sites object for each site, converts it to a dictionary,
    and writes the list of dictionaries to a JSON file.

    Args:
        output_filename (str): The name of the output file.
        sites (list[tuple]): A list of tuples, where each tuple contains a site ID and a site URL.

    Returns:
        None

    Raises:
        IOError: If there is an issue with file I/O.
    """
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
    """
    Reads a list of test results from a JSON file.

    This function reads a JSON file and creates a list of test results.
    Each test result is represented as a tuple containing a date and data.
    The function only includes items that pass the `use_item` function and
    have a `type_of_test` field equal to 22.

    Args:
        input_filename (str): The name of the input file.
        input_skip (int): The number of items to skip at the beginning.
        input_take (int): The number of items to take after skipping.

    Returns:
        result (list[tuple]): A list of tuples, where each tuple contains a date and
                              data from the test result.

    Raises:
        IOError: If there is an issue with file I/O.
        ValueError: If the JSON file does not have the expected structure.
    """
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
    return result


def write_tests(output_filename, site_tests, _, _2):
    """
    Writes site test results to a JSON formated file from a given list of site tests.

    Args:
        output_filename (str): The name of the output file.
        site_tests (list): A list of site tests.
        input_skip (int): The number of tests to skip before starting to take.
        input_take (int): The number of tests to take after skipping.
        _ : Unused parameter.
        _2 : Unused parameter.

    Returns:
        None
    """
    with open(output_filename, 'w', encoding='utf-8') as outfile:
        # json require us to have an object as root element
        container_object = {
            "tests": site_tests
        }
        json.dump(container_object, outfile)
