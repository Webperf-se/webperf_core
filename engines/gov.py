# -*- coding: utf-8 -*-
from models import Sites, SiteTests
from engines.utils import use_item
import csv


def write_tests(output_filename, siteTests, sites):

    tmp_fieldnames = list()
    standard_fieldnames = SiteTests.fieldnames()
    for fieldname in standard_fieldnames:
        if 'site_id' == fieldname:
            tmp_fieldnames.append('url')
        elif 'type_of_test' != fieldname and 'data' not in fieldname and 'rating' not in fieldname and 'date' not in fieldname and 'perf' not in fieldname and 'sec' not in fieldname and 'a11y' not in fieldname and 'stand' not in fieldname and 'perf' not in fieldname:
            tmp_fieldnames.append(fieldname)

    tmp_sites = dict(sites)

    with open(output_filename.replace('.gov', '.csv'), 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=tmp_fieldnames)


        writer.writeheader()
        for siteTest in siteTests:
            site_url = tmp_sites.get(siteTest['site_id'])
            
            writer.writerow({
                'url': site_url,
                'report': (siteTest['report'] + siteTest['report_sec'])
            })