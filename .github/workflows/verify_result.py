# -*- coding: utf-8 -*-
from os import path
import os.path
import sys
import getopt
import filecmp
import json
import shutil
import re


def prepare_config_file(sample_filename, filename, secret_key):
    if not path.exists(sample_filename):
        print('no sample file exist')
        sys.exit(2)

    if path.exists(filename):
        print(filename + ' file already exist')
        sys.exit(2)

    shutil.copyfile(sample_filename, filename)

    if not path.exists(filename):
        print('no file exist')
        sys.exit(2)

    regex = r"^googlePageSpeedApiKey.*"
    subst = "googlePageSpeedApiKey = \"" + secret_key + "\""
    with open(filename, 'r') as file:
        data = file.readlines()
        output = list('')
        for line in data:
            output.append(re.sub(regex, subst, line, 0, re.MULTILINE))

    with open(filename, 'w') as outfile:
        outfile.writelines(output)


def make_test_comparable(input_filename):
    with open(input_filename) as json_input_file:
        data = json.load(json_input_file)
        for test in data["tests"]:
            if "date" in test:
                test["date"] = "removed for comparison"

    with open(input_filename, 'w') as outfile:
        json.dump(data, outfile)


def print_file_content(input_filename):
    print('input_filename=' + input_filename)
    with open(input_filename, 'r') as file:
        data = file.readlines()
        for line in data:
            print(line)


def validate_testresult(arg):
    dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
    test_id = f'{int(arg):02}'
    filename = 'testresult-' + test_id + '.json'
    predicted_filename = dir + 'predicted' + os.path.sep + filename
    filename = dir + filename
    if not path.exists(filename):
        print('test result doesn\'t exists')
        sys.exit(2)

    # We only have 3 tests that are predictable enough with output to try to match content
    if test_id == '02' or test_id == '09' or test_id == '21':
        if not path.exists(predicted_filename):
            print('no predicted file exist')
            sys.exit(2)

        make_test_comparable(filename)
        if filecmp.cmp(filename,
                       predicted_filename, False):
            print('test result mached expected content')
            sys.exit(0)
        else:
            print('test result is _NOT_ maching expected content')
            print_file_content(filename)
            print_file_content(predicted_filename)
            sys.exit(2)
    else:
        # for all other test it is enough that we have a file in place for now
        print('test result exists')
        sys.exit(0)


def main(argv):
    """
    WebPerf Core - Regression Test

    Usage:
    verify_result.py -h

    Options and arguments:
    -h/--help\t\t\t: Verify Help command
    -l/--list\t\t: Verify List of Tests
    -c/--prep-config\t\t: Uses SAMPLE-config.py to creat config.py
    -t/--test <test number>\t: Verify result of specific test
    """

    try:
        opts, args = getopt.getopt(argv, "ht:l:c:", [
                                   "help", "test=", "prep-config=", "list="])
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
        elif opt in ("-c", "--prep-config"):
            prepare_config_file('SAMPLE-config.py', 'config.py', arg)
            sys.exit(0)
        elif opt in ("-l", "--list tests"):

            break
        elif opt in ("-t", "--test"):  # test id
            validate_testresult(arg)

    # No match for command so return error code to fail verification
    sys.exit(2)


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    main(sys.argv[1:])
