# -*- coding: utf-8 -*-
import sys
import getopt
import datetime
import gettext
import math
import datetime
import json
import gettext
from datetime import datetime

FIELD_INDEX_DATE = 0
FIELD_INDEX_DATA = 1


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


def write(output_filename, content):
    with open(output_filename, 'w') as outfile:
        outfile.write(content)


def main(argv):
    """
    WebPerf Core Carbon Percentiles


    Usage:
    * run webperf-core test on all websites you want to use for your percentiles (with json as output file)
    * run this file against your output file, for example like this: carbon-rating.py -i data\carbon-references-2022.json -o tests\energy_efficiency_carbon_percentiles.py

    Options and arguments:
    -h/--help\t\t\t: Help information on how to use script
    -i/--input <file path>\t: input file path (.json)
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
                from engines.json import read_tests, read_sites, add_site, delete_site
            pass
        elif opt in ("-o", "--output"):  # output file path
            output_filename = arg
            pass

    tests = read_tests(input_filename, 0, -1)
    generated_date = False
    co2s = list()

    for test in tests:
        if not generated_date:
            generated_date = datetime.fromisoformat(
                test[FIELD_INDEX_DATE]).strftime('%Y-%m-%d')

        str_data = test[FIELD_INDEX_DATA].replace('\'', '"')
        data = json.loads(str_data)
        print(str_data)
        co2s.append(data['co2'])

    if not generated_date:
        generated_date = datetime.today().strftime('%Y-%m-%d')

    output_content = "# This array was last generated with carbon-rating.py on {0}\n".format(
        generated_date)
    output_content += "def get_generated_date():\n"
    output_content += "\treturn '{0}'\n".format(
        generated_date)
    output_content += "\n"
    output_content += "def get_percentiles():\n"
    output_content += "\treturn [\n"

    co2s_sorted = sorted(co2s)

    intervals = list()

    index = 1
    while (index <= 100):
        percentile = getPercentile(co2s_sorted, index)
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
