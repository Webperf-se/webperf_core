# -*- coding: utf-8 -*-
from models import Sites, SiteTests
from engines.utils import use_item
import csv


def write_tests(output_filename, siteTests, sites):
    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=SiteTests.fieldnames())

        writer.writeheader()
        writer.writerows(siteTests)


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

    with open(input_filename, newline='') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(1024))
        csvfile.seek(0)
        reader = csv.reader(csvfile, dialect)

    with open(input_filename, newline='') as csvfile:
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
    sites_output = list()
    for site in sites:
        site_id = site[0]
        site_url = site[1]
        site_object = Sites(id=site_id, website=site_url).todata()
        sites_output.append(site_object)

    with open("output-" + output_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=Sites.fieldnames())

        writer.writeheader()
        writer.writerows(sites_output)
