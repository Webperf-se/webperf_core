#-*- coding: utf-8 -*-
from models import Sites, SiteTests
import csv

def write_tests(output_filename, siteTests):
    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=SiteTests.fieldnames())

        writer.writeheader()
        writer.writerows(siteTests)