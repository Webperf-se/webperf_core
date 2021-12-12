# -*- coding: utf-8 -*-
import sys
import getopt
import datetime
from models import Sites, SiteTests
import config
import gettext
import math
import csv
import datetime
import json
import gettext
from datetime import datetime

C2_INDEX = 0


def getPercentile(arr, percentile):
    percentile = min(100, max(0, percentile))
    index = (percentile / 100) * (len(arr) - 1)
    fractionPart = index - math.floor(index)
    intPart = math.floor(index)
    percentile = float(arr[intPart])

    if fractionPart > 0:
        percentile += fractionPart * \
            (float(arr[intPart + 1]) - float(arr[intPart]))
    else:
        percentile += 0

    return percentile


def fieldnames():
    result = ['c2']
    return result


def read_c2(input_filename):
    c2s = list()

    with open(input_filename, newline='') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(1024))
        csvfile.seek(0)
        reader = csv.reader(csvfile, dialect)

    with open(input_filename, newline='') as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=',', quotechar='|')
        current_index = 0
        for row in csv_reader:
            number_of_fields = len(fieldnames())
            current_number_of_fields = len(row)
            if number_of_fields == current_number_of_fields:
                # ignore first row as that is our header info
                if current_index != 0:
                    c2s.append(transform_value(row[C2_INDEX]))
            elif current_number_of_fields == 1:
                # we have no header and only one colmn, use column as website url
                c2s.append(transform_value("".join(row)))
            current_index += 1

    return c2s


def transform_value(value):
    return float("{0:.5f}".format(float(value)))


def write(output_filename, content):
    with open(output_filename, 'w') as outfile:
        outfile.write(content)


def main(argv):
    """
    WebPerf Core Carbon Percentiles


    Usage:
    1) Alter energy_efficiency.py so the review is ONLY c2 value.
    2) run webperf-core test on all websites you want to use for your percentiles (with csv as output file)
    3) alter the csv output file to only have ONE column, the report column (currently holding c2 value)
    4) run this file against your output file, for example like this: 
    carbon-rating.py -i data\c2-websitecarbon-com-2020-01-27.csv -o tests\energy_efficiency_carbon_percentiles.py

    Options and arguments:
    -h/--help\t\t\t: Help information on how to use script
    -i/--input <file path>\t: input file path (.csv)
    -o/--output <file path>\t: output file path (.py)
    """

    output_filename = ''
    input_filename = ''
    langCode = 'en'
    language = False

    # add support for default (en) language
    language = gettext.translation(
        'webperf-core', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    try:
        opts, args = getopt.getopt(
            argv, "hi:o:", ["help", "input=", "output="])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if (opts.__len__() == 0):
        print(main.__doc__)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):  # help
            print(main.__doc__)
            sys.exit(2)
        elif opt in ("-i", "--input"):  # input file path
            input_filename = arg

            file_ending = ""
            file_long_ending = ""
            if (len(input_filename) > 4):
                file_ending = input_filename[-4:].lower()
            if (len(input_filename) > 7):
                file_long_ending = input_filename[-7:].lower()

            if file_long_ending == ".sqlite":
                from engines.sqlite import read_sites, add_site, delete_site
            elif (file_ending == ".csv"):
                from engines.csv import read_sites, add_site, delete_site
            elif (file_ending == ".xml"):  # https://example.com/sitemap.xml
                from engines.sitemap import read_sites, add_site, delete_site
            else:
                from engines.json import read_sites, add_site, delete_site
            pass
        elif opt in ("-o", "--output"):  # output file path
            output_filename = arg
            pass

    c2s = read_c2(input_filename)
    c2s_sorted = sorted(c2s)

    intervals = list()

    generated_date = datetime.today().strftime('%Y-%m-%d')
    output_content = "# This array was last generated with carbon-rating.py on {0}\n".format(
        generated_date)
    output_content += "def get_generated_date():\n"
    output_content += "\treturn '{0}'\n".format(
        generated_date)
    output_content += "\n"
    output_content += "def get_percentiles():\n"
    output_content += "\treturn [\n"

    index = 1
    while (index <= 100):
        percentile = getPercentile(c2s_sorted, index)
        intervals.append(percentile)
        position = index - 1
        if index < 100:
            if position % 10 == 0 and position != 0:
                output_content += "\t\t# {0} percentile\n".format(position)

            output_content += "\t\t{0},\n".format(percentile)
        else:
            output_content += "\t\t{0}\n".format(percentile)
        index += 1

    output_content += "\t]"

    print(output_content)
    if (len(output_filename) > 0):
        write(output_filename, output_content)


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    main(sys.argv[1:])
