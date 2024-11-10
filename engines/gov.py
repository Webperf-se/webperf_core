# -*- coding: utf-8 -*-
import csv
from helpers.models import SiteTests

def write_tests(output_filename, site_tests, sites, _):
    """
    Writes site test results to a CSV formated file from a given list of site tests.
    Compared to csv engine it is optimized for goverment reports and is missing some fields

    Args:
        output_filename (str): The name of the output file.
        site_tests (list): A list of site tests.
        sites (list) : A list of sites.
        _ : Unused parameter.

    Returns:
        None
    """

    tmp_fieldnames = []
    lst = ['type_of_test', 'data', 'rating', 'date'
            'perf', 'sec', 'a11y', 'stand', 'perf']

    standard_fieldnames = SiteTests.fieldnames()
    for fieldname in standard_fieldnames:
        if 'site_id' == fieldname:
            tmp_fieldnames.append('url')
        elif not any(fieldname in x for x in lst):
            tmp_fieldnames.append(fieldname)
    tmp_sites = dict(sites)

    with open(output_filename.replace('.gov', '.csv'),
              'w', newline='',
              encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=tmp_fieldnames) # pylint: disable=no-member


        writer.writeheader()
        for site_test in site_tests:
            site_url = tmp_sites.get(site_test['site_id'])

            writer.writerow({
                'url': site_url,
                'report': (site_test['report'] + site_test['report_sec'])
            })
