# -*- coding: utf-8 -*-
from pathlib import Path
import os
import os.path
import ssl
import sys
import getopt
import json
import shutil
import re
import sys
import getopt
import gettext

import requests


def prepare_config_file(sample_filename, filename, arguments):
    print('A', arguments)

    if not os.path.exists(sample_filename):
        print('no sample file exist')
        return False

    if os.path.exists(filename):
        print(filename + ' file already exist, removing it')
        os.remove(filename)

    shutil.copyfile(sample_filename, filename)

    if not os.path.exists(filename):
        print('no file exist')
        return False

    with open(filename, 'r') as file:
        data = file.readlines()
        output = list('')
        for line in data:
            tmp = line
            for argument in arguments:
                index = argument.find('=')
                pair = argument.split('=')
                name = argument[:index]
                value = argument[(index + 1):]

                regex_argument = r'^{0}.*'.format(name)
                if value == 'True' or value == 'False' or value == 'None':
                    result_argument = r'{0} = {1}'.format(name, value)
                else:
                    result_argument = r"{0} = '{1}'".format(name, value)


                tmp = re.sub(regex_argument, result_argument,
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
    test_id = arg
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


def validate_po_file(locales_dir, localeName, languageSubDirectory, file, msg_ids):
    file_is_valid = True
    if file.endswith('.pot'):
        print('')
        print('')
        print('# {0} [{1}]'.format(file, localeName))
        print(
            '  Unexpected .pot file found, this should probably be renamed to .po.')
        return False
    elif file.endswith('.mo'):
        # ignore this file format
        return True
    elif file.endswith('.po'):
        # print('po file found: {0}'.format(file))
        # for every .po file found, check if we have a .mo file
        print('  # {0} [{1}]'.format(file, localeName))

        file_mo = os.path.join(
            languageSubDirectory, file.replace('.po', '.mo'))
        if not os.path.exists(file_mo):
            print(
                '  Expected compiled translation file not found, file: "{0}"'.format(file.replace('.po', '.mo')))
            return False
        else:
            # for every .mo file found, try to load it to verify it works
            n_of_errors = 0
            try:
                # NOTE: gettext is internally caching all mo files, we need to clear this variable to readd the newly generated .mo file.
                gettext._translations = {}

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
                            '  More then 5 errors, ignoring rest of errors')
                        return False

                    msg_id = match.group('id')
                    msg_txt = match.group('text')
                    lang_txt = language.gettext(msg_id).replace(
                        '\n', '\\n').replace(
                        '\r', '\\r').replace('\t', '\\t')
                    msg_ids[msg_id] = msg_txt

                    if lang_txt == msg_id:
                        print(
                            '  - Could not find text for msgid "{1}" in file: {0}'.format(file_mo, msg_id))
                        n_of_errors += 1
                        continue
                    if lang_txt != msg_txt:
                        print(
                            '  ## Text missmatch:')
                        print('  - msgid: {0}'.format(msg_id))
                        if len(msg_txt) > 15:
                            print(
                                '    - expected text: "{0}[...]"'.format(msg_txt[0: 15]))
                        else:
                            print(
                                '    - expected text: "{0}"'.format(msg_txt))

                        if len(lang_txt) > 15:
                            print(
                                '    - recived text:  "{0}[...]"'.format(lang_txt[0:15]))
                        else:
                            print(
                                '    - recived text:  "{0}"'.format(lang_txt))
                        n_of_errors += 1
                        continue
                if n_of_errors > 0:
                    file_is_valid = False
            except Exception as ex:
                print(
                    '  - Unable to load "{0}" as a valid translation'.format(file_mo))
                return False

            if n_of_errors > 0:
                print('')
                print('')
            else:
                print('    - OK')

    else:
        print('')
        print('')
        print('  # {0} [{1}]'.format(file, localeName))
        print(
            '  Unexpected file extension found. Expected .po and .mo.')
        return False
    return file_is_valid


def validate_translations():
    msg_ids = {}
    # loop all available languages and verify language exist
    dir = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent.parent

    print('Validate .po and .mo files')
    is_valid = validate_locales(dir, msg_ids)

    root_folder = dir.resolve()

    print('')
    print('')
    print('Validate _() and _local() uses in .py files')
    file_is_valid = validate_python_files(root_folder, msg_ids)

    is_valid = is_valid and file_is_valid

    return is_valid


def validate_python_files(folder, msg_ids):
    files_are_valid = True
    listing = False
    try:
        listing = os.listdir(folder)
    except:
        # Ignore: is not a directory or has some read problem..
        return files_are_valid
    for item in listing:
        if '.' in item:
            if len(item) < 3 or not item.endswith('.py'):
                continue
            #print('python file:', item)
            current_file = os.path.join(
                folder, item)

            file_is_valid = validate_python_file(current_file, msg_ids)
            files_are_valid = files_are_valid and file_is_valid
        else:
            current_dir = os.path.join(
                folder, item) + os.path.sep
            dir_is_valid = validate_python_files(current_dir, msg_ids)
            files_are_valid = files_are_valid and dir_is_valid
            # print('dir:', current_dir)

    return files_are_valid


def validate_python_file(current_file, msg_ids):
    file_name = current_file[current_file.rindex(os.sep) + 1:]
    print('  #', file_name)
    file_is_valid = True
    # for every .mo file found, try to load it to verify it works
    n_of_errors = 0

    file_py_content = get_file_content(current_file)
    regex = r"[^_]_(local){0,1}\(['\"](?P<msgid>[^\"']+)[\"']\)"
    matches = re.finditer(
        regex, file_py_content, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
        if n_of_errors >= 5:
            print(
                '    - More then 5 errors, ignoring rest of errors')
            return False

        msg_id = match.group('msgid')
        if msg_id not in msg_ids:
            file_is_valid = False
            print('    - Missing msg_id:', msg_id)
        # else:
        #     print('  - msg_id', msg_id, 'OK')

    if file_is_valid:
        print('    - OK')
    # else:
    #     print('  - FAIL')
    return file_is_valid


def validate_locales(dir, msg_ids):
    is_valid = True

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
                if validate_po_file(locales_dir, localeName, languageSubDirectory, file, msg_ids):
                    current_number_of_valid_translations += 1
                elif file.endswith('.po'):
                    # po file had errors, try generate new mo file and try again.
                    msgfmt_path = ensure_msgfmt_py()
                    if msgfmt_path != None:
                        print(
                            '  - Trying to generate .mo file so it matches .po file')
                        bashCommand = "python {0} -o {1} {2}".format(
                            msgfmt_path, os.path.join(languageSubDirectory, file.replace(
                                '.po', '.mo')), os.path.join(languageSubDirectory, file))
                        import subprocess
                        process = subprocess.Popen(
                            bashCommand.split(), stdout=subprocess.PIPE)
                        output, error = process.communicate()
                        result = str(output)
                        if validate_po_file(locales_dir, localeName, languageSubDirectory, file, msg_ids):
                            current_number_of_valid_translations += 1
                        else:
                            is_valid = False
                    else:
                        print(
                            '  - Unable to generate .mo file because we could not find msgfmt.py in python installation')
                else:
                    is_valid = False

            if number_of_valid_translations == 0:
                number_of_valid_translations = current_number_of_valid_translations

            if number_of_valid_translations != current_number_of_valid_translations:
                print(
                    '  Different number of translation files for languages. One or more language is missing a translation')
                is_valid = False
                continue
    if len(availableLanguages) > 0:
        print('')
        print('  Available Languages: {0}'.format(
            ', '.join(availableLanguages)))
    else:
        print('  No languages found')
    return is_valid

def httpRequestGetContent(url, allow_redirects=False, use_text_instead_of_content=True):
    """Trying to fetch the response content
    Attributes: url, as for the URL to fetch
    """

    try:
        headers = {'user-agent': 'Mozilla/5.0 (compatible; Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36 Edg/88.0.705.56'}
        a = requests.get(url, allow_redirects=allow_redirects,
                         headers=headers, timeout=120)

        if use_text_instead_of_content:
            content = a.text
        else:
            content = a.content
        return content
    except ssl.CertificateError as error:
        print('Info: Certificate error. {0}'.format(error.reason))
        pass
    except requests.exceptions.SSLError as error:
        if 'http://' in url:  # trying the same URL over SSL/TLS
            print('Info: Trying SSL before giving up.')
            return httpRequestGetContent(url.replace('http://', 'https://'))
        else:
            print('Info: SSLError. {0}'.format(error))
            return ''
        pass
    except requests.exceptions.ConnectionError as error:
        if 'http://' in url:  # trying the same URL over SSL/TLS
            print('Connection error! Info: Trying SSL before giving up.')
            return httpRequestGetContent(url.replace('http://', 'https://'))
        else:
            print(
                'Connection error! Unfortunately the request for URL "{0}" failed.\nMessage:\n{1}'.format(url, sys.exc_info()[0]))
            return ''
        pass
    except:
        print(
            'Error! Unfortunately the request for URL "{0}" either timed out or failed for other reason(s). The timeout is set to {1} seconds.\nMessage:\n{2}'.format(url, 120, sys.exc_info()[0]))
        pass
    return ''

def set_file(file_path, content, use_text_instead_of_content):
    if use_text_instead_of_content:
        with open(file_path, 'w', encoding='utf-8', newline='') as file:
            file.write(content)
    else:
        with open(file_path, 'wb') as file:
            file.write(content)

def ensure_msgfmt_py():
    import sys
    for python_path in sys.path:
        a = python_path

        if a.endswith('.zip'):
            # Ignore zip files
            continue

        msgfmt_path = has_dir_msgfmt_py(a, 0)
        if msgfmt_path != None:
            return msgfmt_path
        else:
            dir = Path(os.path.dirname(
                os.path.realpath(__file__)) + os.path.sep).parent.parent
            data_dir = os.path.join(dir.resolve(), 'data') + os.sep
            filename = 'msgfmt.py'
            file_path = os.path.join(data_dir,filename)

            if not os.path.exists(file_path):
                content = httpRequestGetContent('https://raw.githubusercontent.com/python/cpython/main/Tools/i18n/msgfmt.py', True, True)
                set_file(file_path, content, True)
            return file_path
    return None


def has_dir_msgfmt_py(dir, depth):
    try:
        files = os.listdir(dir)

        if 'msgfmt.py' in files:
            return os.path.join(dir, 'msgfmt.py')
        elif 'i18n' in files:
            return os.path.join(dir, 'i18n' 'msgfmt.py')
        elif 'Tools' in files:
            return os.path.join(dir, 'Tools', 'i18n', 'msgfmt.py')
        elif 'io.py' in files or 'base64.py' in files or 'calendar.py' in files or 'site-packages' in files:
            parent_dir = Path(os.path.dirname(
                os.path.realpath(dir)) + os.path.sep).parent
            return has_dir_msgfmt_py(parent_dir, depth + 1)

    except Exception as ex:
        print('\t   Exception', ex)
    return None


def main(argv):
    """
    WebPerf Core - Regression Test

    Usage:
    verify_result.py -h

    Options and arguments:
    -h/--help\t\t\t: Verify Help command
    -l/--language\t\t: Verify languages
    -c/--prep-config <activate feature, True or False>\t\t: Uses SAMPLE-config.py to creat config.py
    -t/--test <test number>\t: Verify result of specific test

    NOTE:
    If you get this in step "Setup config [...]" you forgot to add repository secret for your repository.
    More info can be found here: https://github.com/Webperf-se/webperf_core/issues/81
    """

    try:
        opts, args = getopt.getopt(argv, "hlc:t:", [
                                   "help", "test=", "prep-config=", "language"])
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
            if 'true' == arg.lower() or 'false' == arg.lower() or '1' == arg or '0' == arg:
                raise ValueError(
                    'c/prep-config argument has changed format, it doesn\'t support previous format')
            arguments = arg.split(',')

            if prepare_config_file('SAMPLE-config.py', 'config.py', arguments):
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
