# -*- coding: utf-8 -*-
import io
from os import path
import os.path
import sys
import getopt
import datetime
import filecmp
import json


def write_tests(output_filename, siteTests):
    with open(output_filename, 'w') as outfile:
        # json require us to have an object as root element
        testsContainerObject = {
            "tests": siteTests
        }
        json.dump(testsContainerObject, outfile)


def make_test_comparable(input_filename):
    with open(input_filename) as json_input_file:
        data = json.load(json_input_file)
        current_index = 0
        for test in data["tests"]:
            if "date" in test:
                test["date"] = "removed for comparison"

    with open(input_filename, 'w') as outfile:
        json.dump(data, outfile)


def main(argv):
    """
    WebPerf Core - Regression Test

    Usage:
    verify_result.py -h

    Options and arguments:
    -h/--help\t\t\t: Verify Help command
    -l/--list\t\t: Verify List of Tests
    -t/--test <test number>\t: Verify result of specific test
    """

    try:
        opts, args = getopt.getopt(argv, "hu:t:i:o:rA:D:L:", [
                                   "help", "url=", "test=", "input=", "output=", "review", "report", "addUrl=", "deleteUrl=", "language=", "input-skip=", "input-take="])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if (opts.__len__() == 0):
        print(main.__doc__)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):  # help
            show_help = True
            break
        elif opt in ("-l", "--list tests"):

            break
        elif opt in ("-t", "--test"):  # test id
            dir = os.path.dirname(os.path.realpath(__file__)) + '\\'
            test_id = f'{int(arg):02}'
            filename = 'testresult-' + test_id + '.json'
            predicted_filename = dir + 'predicted\\' + filename
            filename = dir + filename
            if not path.exists(filename):
                print('no file exist')
                sys.exit(2)

            if not path.exists(predicted_filename):
                print('no predicted file exist')
                sys.exit(2)

            make_test_comparable(filename)
            if filecmp.cmp(filename,
                           predicted_filename, False):
                print('files match')
                sys.exit(0)
            else:
                print('file diff')
                sys.exit(2)

    # No match for command so return error code to fail verification
    sys.exit(2)


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    main(sys.argv[1:])
