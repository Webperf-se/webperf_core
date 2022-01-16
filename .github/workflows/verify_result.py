# -*- coding: utf-8 -*-
from math import fabs
from operator import truediv
from pathlib import Path
import os
import os.path
import sys
import getopt
import filecmp
import json
import shutil
import re
import sys
import getopt
import gettext


def prepare_config_file(sample_filename, filename):
    if not os.path.exists(sample_filename):
        print('no sample file exist')
        return False

    if os.path.exists(filename):
        print(filename + ' file already exist')
        return False

    shutil.copyfile(sample_filename, filename)

    if not os.path.exists(filename):
        print('no file exist')
        return False

    regex_ylt = r"^ylt_use_api.*"
    subst_ylt = "ylt_use_api = False"

    regex_lighthouse = r"^lighthouse_use_api.*"
    subst_lighthouse = "lighthouse_use_api = False"

    regex_sitespeed = r"^sitespeed_use_docker.*"
    subst_sitespeed = "sitespeed_use_docker = True"

    with open(filename, 'r') as file:
        data = file.readlines()
        output = list('')
        for line in data:
            tmp = re.sub(regex_ylt, subst_ylt, line, 0, re.MULTILINE)
            tmp = re.sub(regex_lighthouse, subst_lighthouse,
                         tmp, 0, re.MULTILINE)
            tmp = re.sub(regex_sitespeed, subst_sitespeed,
                         tmp, 0, re.MULTILINE)

            output.append(tmp)

    with open(filename, 'w') as outfile:
        outfile.writelines(output)

    # show resulting config in output for debug reasons
    print('config.py:\n')
    print('\n'.join(output))
    return True


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


def get_file_content(input_filename):
    # print('input_filename=' + input_filename)
    with open(input_filename, 'r', encoding='utf-8') as file:
        lines = list()
        data = file.readlines()
        for line in data:
            lines.append(line)
            # print(line)
    return '\n'.join(lines)


def validate_testresult(arg):
    dir = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
    test_id = f'{int(arg):02}'
    filename = 'testresult-' + test_id + '.json'
    filename = dir + filename
    if not os.path.exists(filename):
        print('test result doesn\'t exists')
        return False

    # for all other test it is enough that we have a file in place for now
    if '{"tests": []}' in get_file_content(filename):
        print('Test failed, empty test results only')
        print_file_content(filename)
        return False
    else:
        print('test result exists')
        print_file_content(filename)
        return True


def validate_po_file(locales_dir, localeName, languageSubDirectory, file):
    file_is_valid = True
    if file.endswith('.pot'):
        print('')
        print('')
        print('# {0} [{1}]'.format(file, localeName))
        print(
            'Unexpected .pot file found, this should probably be renamed to .po.')
        return False
    elif file.endswith('.mo'):
        # ignore this file format
        return True
    elif file.endswith('.po'):
        # print('po file found: {0}'.format(file))
        # for every .po file found, check if we have a .mo file
        print('# {0} [{1}]'.format(file, localeName))

        file_mo = os.path.join(
            languageSubDirectory, file.replace('.po', '.mo'))
        if not os.path.exists(file_mo):
            print(
                'Expected compiled translation file not found, file: "{0}"'.format(file.replace('.po', '.mo')))
            return False
        else:
            # for every .mo file found, try to load it to verify it works
            n_of_errors = 0
            try:
                language = gettext.translation(
                    file.replace('.po', ''), localedir=locales_dir, languages=[localeName])
                language.install()

                # Make sure every text in .po file is present (and equal) in .mo file
                file_po_content = get_file_content(os.path.join(
                    languageSubDirectory, file))

                regex = r"msgid \"(?P<id>[^\"]+)\"[^m]+msgstr \"(?P<text>[^\"]+)\""
                matches = re.finditer(
                    regex, file_po_content, re.MULTILINE)
                for matchNum, match in enumerate(matches, start=1):
                    if n_of_errors >= 5:
                        print(
                            'More then 5 errors, ignoring rest of errors')
                        return False

                    msg_id = match.group('id')
                    msg_txt = match.group('text')
                    lang_txt = language.gettext(msg_id).replace(
                        '\n', '\\n').replace(
                        '\r', '\\r').replace('\t', '\\t')
                    if lang_txt == msg_id:
                        print(
                            '- Could not find text for msgid "{1}" in file: {0}'.format(file_mo, msg_id))
                        n_of_errors += 1
                        continue
                    if lang_txt != msg_txt:
                        print(
                            '## Text missmatch:')
                        print('- msgid: {0}'.format(msg_id))
                        if len(msg_txt) > 15:
                            print(
                                '- expected text: "{0}[...]"'.format(msg_txt[0: 15]))
                        else:
                            print(
                                '- expected text: "{0}"'.format(msg_txt))

                        if len(lang_txt) > 15:
                            print(
                                '- recived text:  "{0}[...]"'.format(lang_txt[0:15]))
                        else:
                            print(
                                '- recived text:  "{0}"'.format(lang_txt))
                        n_of_errors += 1
                        continue
                if n_of_errors > 0:
                    file_is_valid = False
            except Exception as ex:
                print(
                    '- Unable to load "{0}" as a valid translation'.format(file_mo))
                return False

            if n_of_errors > 0:
                print('')
                print('')
            else:
                print('  - OK')

    else:
        print('')
        print('')
        print('# {0} [{1}]'.format(file, localeName))
        print(
            'Unexpected file extension found. Expected .po and .mo.')
        return False
    return file_is_valid


def validate_translations():
    is_valid = True
    # loop all available languages and verify language exist
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent.parent
    availableLanguages = list()
    locales_dir = os.path.join(dir.resolve(), 'locales') + os.sep
    localeDirs = os.listdir(locales_dir)

    number_of_valid_translations = 0

    for localeName in localeDirs:
        current_number_of_valid_translations = 0

        if (localeName[0:1] == '.'):
            continue

        languageSubDirectory = os.path.join(
            locales_dir, localeName, "LC_MESSAGES")

        if (os.path.exists(languageSubDirectory)):
            availableLanguages.append(localeName)

            files = os.listdir(languageSubDirectory)
            for file in files:
                # for every .po file found, check if we have a .mo file
                if validate_po_file(locales_dir, localeName, languageSubDirectory, file):
                    current_number_of_valid_translations += 1
                else:
                    is_valid = False

            if number_of_valid_translations == 0:
                number_of_valid_translations = current_number_of_valid_translations

            if number_of_valid_translations != current_number_of_valid_translations:
                print(
                    'Different number of translation files for languages. One or more language is missing a translation')
                is_valid = False
                continue
    if len(availableLanguages) > 0:
        print('')
        print('Available Languages: {0}'.format(', '.join(availableLanguages)))
    else:
        print('No languages found')

    return is_valid


def main(argv):
    """
    WebPerf Core - Regression Test

    Usage:
    verify_result.py -h

    Options and arguments:
    -h/--help\t\t\t: Verify Help command
    -l/--language\t\t: Verify languages
    -c/--prep-config\t\t: Uses SAMPLE-config.py to creat config.py
    -t/--test <test number>\t: Verify result of specific test

    NOTE:
    If you get this in step "Setup config [...]" you forgot to add repository secret for your repository.
    More info can be found here: https://github.com/Webperf-se/webperf_core/issues/81
    """

    try:
        opts, args = getopt.getopt(argv, "hlct:", [
                                   "help", "test=", "prep-config", "language"])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if (opts.__len__() == 0):
        print(main.__doc__)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):  # help
            print(main.__doc__)
            sys.exit(0)
            break
        elif opt in ("-c", "--prep-config"):
            if prepare_config_file('SAMPLE-config.py', 'config.py'):
                sys.exit(0)
            else:
                sys.exit(2)
            break
        elif opt in ("-l", "--language"):
            if validate_translations():
                sys.exit(0)
            else:
                sys.exit(2)
            break
        elif opt in ("-t", "--test"):  # test id
            if validate_testresult(arg):
                sys.exit(0)
            else:
                sys.exit(2)
            break

    # No match for command so return error code to fail verification
    sys.exit(2)


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    main(sys.argv[1:])
