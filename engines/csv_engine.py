# -*- coding: utf-8 -*-
import csv
from helpers.models import Sites, SiteTests
from engines.utils import use_item

def write_tests(output_filename, site_tests, _, _2):
    """
    Writes site test results to a CSV formated file from a given list of site tests.

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
    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=SiteTests.fieldnames())

        writer.writeheader()
        writer.writerows(site_tests)


def add_site(input_filename, url, input_skip, input_take):
    """
    Adds a site to a list of sites in a CSV file.

    This function reads a CSV file using the `read_sites` function and
    creates a new list of sites. It then adds a new site with the specified URL to the list.
    The new site's ID is the current length of the list of sites.
    The function then writes the updated list of sites back to the CSV file using the
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
    Deletes a site from a list of sites in a CSV file.

    This function reads a CSV file using the `read_sites` function and
    creates a new list of sites excluding the site with the specified URL.
    It then writes the new list of sites back to the CSV file using the `write_sites` function.

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
    Reads a list of sites from a CSV file.

    This function reads a CSV file and creates a list of sites.
    Each site is represented as a tuple containing a site ID and a site URL.
    The function skips the first row of the CSV file (header info) and
    only includes items that pass the `use_item` function.

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

    with open(input_filename, newline='', encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        current_index = 0
        for row in csv_reader:
            number_of_fields = len(Sites.fieldnames())
            current_number_of_fields = len(row)
            if number_of_fields == current_number_of_fields:
                # ignore first row as that is our header info
                if current_index != 0 and use_item(current_index + 1, input_skip, input_take):
                    sites.append([row[0], row[1]])
            elif current_number_of_fields == 1:
                # we have no header and only one colmn, use column as website url
                if use_item(current_index, input_skip, input_take):
                    sites.append([current_index, "".join(row)])
            current_index += 1

    return sites


def write_sites(output_filename, sites):
    """
    Writes a list of sites to a CSV file.

    This function takes a list of tuples, where each tuple represents a site.
    Each tuple contains a site ID and a site URL.
    It creates a Sites object for each site, converts it to a dictionary,
    and writes the list of dictionaries to a CSV file.

    The output file is named by prepending 'output-' to the provided output_filename.

    Args:
        output_filename (str): The name of the output file (without 'output-' prepended).
        sites (list[tuple]): A list of tuples, where each tuple contains a site ID and a site URL.

    Returns:
        None

    Raises:
        IOError: If there is an issue with file I/O.
    """
    sites_output = []
    for site in sites:
        site_id = site[0]
        site_url = site[1]
        site_object = Sites(site_id, site_url).todata()
        sites_output.append(site_object)

    with open("output-" + output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=Sites.fieldnames())

        writer.writeheader()
        writer.writerows(sites_output)
