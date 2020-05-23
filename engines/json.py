#-*- coding: utf-8 -*-
import json

def add_site(input_filename, url):
    sites = read_sites(input_filename)
    print(sites)
    id = len(sites)
    sites.append([id, url])
    write_sites(input_filename, sites)

    print("website with url: " + url + " has been added\n")

    return sites

def delete_site(input_filename, url):
    sites = read_sites(input_filename)
    tmpSites = list()
    for site in sites:
        site_id = site[0]
        site_url = site[1]
        if (url != site_url):
            tmpSites.append([site_id, site_url])
    
    write_sites(input_filename, tmpSites)

    print("website with url: " + url + " has been deleted\n")
    
    return tmpSites

def read_sites(input_filename):
    sites = list()
    with open(input_filename) as json_input_file:
        data = json.load(json_input_file)
        for site in data["sites"]:
            sites.append([site["id"], site["url"]])
    return sites

def write_tests(output_filename, siteTests):
    with open(output_filename, 'w') as outfile:
        # json require us to have an object as root element
        testsContainerObject = {
            "tests": siteTests
        }
        json.dump(testsContainerObject, outfile)

def write_sites(output_filename, sites):
    with open(output_filename, 'w') as outfile:
        # json require us to have an object as root element
        jsonSites = list()
        for site in sites:
            jsonSites.append({
            'id': site[0],
            'url': site[1]
        })

        sitesContainerObject = {
            "sites": jsonSites
        }
        json.dump(sitesContainerObject, outfile)
        
