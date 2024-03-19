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
import gettext
import subprocess
import requests

def prepare_config_file(sample_filename, filename, arguments):
    """
    Prepares a configuration file based on a sample file and a set of arguments.

    This function performs the following steps:
    1. Checks if the sample file exists. If not, it returns False.
    2. If the target file already exists, it removes it.
    3. Copies the sample file to the target file location.
    4. Opens the new file and reads its contents.
    5. Iterates over each line in the file and each argument in the arguments list.
    6. For each argument, it finds the name and value and constructs a new line with these values.
    7. Writes the modified lines back to the file.
    8. Prints the contents of the new file for debugging purposes.

    Args:
        sample_filename (str): The path to the sample configuration file.
        filename (str): The path where the new configuration file should be created.
        arguments (list): A list of strings where each string is
          an argument in the format 'name=value'.

    Returns:
        bool: True if the operation was successful, False otherwise.
    """

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

    with open(filename, 'r', encoding="utf-8") as file:
        data = file.readlines()
        output = list('')
        for line in data:
            tmp = line
            for argument in arguments:
                index = argument.find('=')
                name = argument[:index]
                value = argument[(index + 1):]

                regex_argument = f'^{name}.*'
                if value == 'True' or value == 'False' or value == 'None':
                    result_argument = f'{name} = {value}'
                else:
                    result_argument = f"{name} = '{value}'"


                tmp = re.sub(regex_argument, result_argument,
                             tmp, 0, re.MULTILINE)
            output.append(tmp)

    with open(filename, 'w', encoding="utf-8") as outfile:
        outfile.writelines(output)

    # show resulting config in output for debug reasons
    print('config.py:\n')
    print('\n'.join(output))
    return True


def make_test_comparable(input_filename):
    """
    Modifies a JSON test file to make it comparable by removing date information.

    This function performs the following steps:
    1. Opens the input file and loads the JSON data.
    2. Iterates over each test in the data. If a test contains a "date" field,
      it replaces the date with the string "removed for comparison".
    3. Writes the modified data back to the input file.

    Args:
        input_filename (str): The path to the JSON file to be modified.

    Note: This function modifies the input file in-place.
      Make sure to create a backup if you need to preserve the original data.
    """

    with open(input_filename, encoding="utf-8") as json_input_file:
        data = json.load(json_input_file)
        for test in data["tests"]:
            if "date" in test:
                test["date"] = "removed for comparison"

    with open(input_filename, 'w', encoding="utf-8") as outfile:
        json.dump(data, outfile)


def print_file_content(input_filename):
    """
    Prints the content of a file line by line.

    This function performs the following steps:
    1. Prints the name of the input file.
    2. Opens the input file in read mode.
    3. Reads the file line by line.
    4. Prints each line.

    Args:
        input_filename (str): The path to the file to be read.

    Note: This function assumes that the file exists and can be opened.
      If the file does not exist or cannot be opened, an error will occur.
    """

    print('input_filename=' + input_filename)
    with open(input_filename, 'r', encoding="utf-8") as file:
        data = file.readlines()
        for line in data:
            print(line)


def get_file_content(input_filename):
    """
    Reads the content of a file and returns it as a string.

    This function performs the following steps:
    1. Opens the input file in read mode.
    2. Reads the file line by line and stores each line in a list.
    3. Joins the list of lines into a single string with newline characters between each line.

    Args:
        input_filename (str): The path to the file to be read.

    Returns:
        str: The content of the file as a string.

    Note: This function assumes that the file exists and can be opened.
      If the file does not exist or cannot be opened, an error will occur.
    """

    with open(input_filename, 'r', encoding='utf-8') as file:
        lines = list()
        data = file.readlines()
        for line in data:
            lines.append(line)
    return '\n'.join(lines)


def validate_testresult(arg):
    """
    Validates the test result by checking the existence and content of a specific JSON file.

    This function checks if a JSON file named 'testresult-{test_id}.json' exists
      in the same directory as this script.
    If the file exists, it checks if the file contains '{"tests": []}',
      which indicates an empty test result.
    The function prints the content of the file and 
      returns a boolean value indicating the validity of the test result.

    Parameters:
    arg (str): The test_id used to identify the test result file.

    Returns:
    bool: True if the test result file exists and contains valid test results, False otherwise.
    """

    base_directory = os.path.dirname(os.path.realpath(__file__)) + os.path.sep
    test_id = arg
    filename = f'testresult-{test_id}.json'
    filename = os.path.join(base_directory, filename)
    if not os.path.exists(filename):
        print('test result doesn\'t exists')
        return False

    # for all other test it is enough that we have a file in place for now
    if '{"tests": []}' in get_file_content(filename):
        print('Test failed, empty test results only')
        print_file_content(filename)
        return False

    print('test result exists')
    print_file_content(filename)
    return True


def validate_po_file(locales_dir, locale_name, language_sub_directory, file, msg_ids):
    """
    Validates the .po and .mo files in a given directory for a specific locale.

    This function checks the existence and content of .po and .mo files in a given directory.
    It validates the .po file by checking if the corresponding .mo file exists and
      if it can be loaded.
    It also checks if the text in the .po file is present and equal in the .mo file.
    The function prints the content of the file and returns a boolean value
      indicating the validity of the file.

    Parameters:
    locales_dir (str): The directory where the locale files are located.
    locale_name (str): The name of the locale to validate.
    language_sub_directory (str): The subdirectory where the language files are located.
    file (str): The name of the file to validate.
    msg_ids (dict): A dictionary to store the message IDs and their corresponding texts.

    Returns:
    bool: True if the file is valid, False otherwise.
    """

    file_is_valid = True
    if file.endswith('.pot'):
        print('')
        print('')
        print(f'# {0} [{1}]'.format(file, locale_name))
        print(
            '  Unexpected .pot file found, this should probably be renamed to .po.')
        return False

    if file.endswith('.mo'):
        # ignore this file format
        return True

    if file.endswith('.po'):
        # for every .po file found, check if we have a .mo file
        print(f'  # {file} [{locale_name}]')

        file_mo = os.path.join(
            language_sub_directory, file.replace('.po', '.mo'))
        if not os.path.exists(file_mo):
            print(
                f'  Expected compiled translation file not found, file: "{file.replace('.po', '.mo')}"')
            return False
        else:
            # for every .mo file found, try to load it to verify it works
            n_of_errors = 0
            try:
                # NOTE: gettext is internally caching all mo files, we need to clear this variable to readd the newly generated .mo file.
                gettext._translations = {} # pylint: disable=protected-access

                language = gettext.translation(
                    file.replace('.po', ''), localedir=locales_dir, languages=[locale_name])
                language.install()

                # Make sure every text in .po file is present (and equal) in .mo file
                file_po_content = get_file_content(os.path.join(
                    language_sub_directory, file))

                regex = r"msgid \"(?P<id>[^\"]+)\"[^m]+msgstr \"(?P<text>[^\"]+)\""
                matches = re.finditer(
                    regex, file_po_content, re.MULTILINE)
                for _, match in enumerate(matches, start=1):
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
                            f'  - Could not find text for msgid "{msg_id}" in file: {file_mo}')
                        n_of_errors += 1
                        continue
                    if lang_txt != msg_txt:
                        print(
                            '  ## Text missmatch:')
                        print(f'  - msgid: {msg_id}')
                        if len(msg_txt) > 15:
                            print(
                                f'    - expected text: "{msg_txt[0: 15]}[...]"')
                        else:
                            print(
                                f'    - expected text: "{msg_txt}"')

                        if len(lang_txt) > 15:
                            print(
                                f'    - recived text:  "{lang_txt[0:15]}[...]"')
                        else:
                            print(
                                f'    - recived text:  "{lang_txt}"')
                        n_of_errors += 1
                        continue
                if n_of_errors > 0:
                    file_is_valid = False
            except Exception:
                print(
                    f'  - Unable to load "{file_mo}" as a valid translation')
                return False

            if n_of_errors > 0:
                print('')
                print('')
            else:
                print('    - OK')

    else:
        print('')
        print('')
        print(f'  # {file} [{locale_name}]')
        print(
            '  Unexpected file extension found. Expected .po and .mo.')
        return False
    return file_is_valid


def validate_translations():
    """
    Validates the translation files and usage in the project.

    This function performs two main validation steps:
    1. Validates the existence and correctness of .po and .mo files in the project.
    2. Validates the usage of _() and _local() in .py files in the project.

    The function uses the `validate_locales` function to validate .po and .mo files,
    and the `validate_python_files` function to validate _() and _local() usage.

    Returns:
        bool: True if all validations pass, False otherwise.
    """

    msg_ids = {}
    # loop all available languages and verify language exist
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent.parent

    print('Validate .po and .mo files')
    is_valid = validate_locales(base_directory, msg_ids)

    root_folder = base_directory.resolve()

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
    except Exception:
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
    for _, match in enumerate(matches, start=1):
        if n_of_errors >= 5:
            print(
                '    - More then 5 errors, ignoring rest of errors')
            return False

        msg_id = match.group('msgid')
        if msg_id not in msg_ids:
            file_is_valid = False
            print('    - Missing msg_id:', msg_id)

    if file_is_valid:
        print('    - OK')
    return file_is_valid


def validate_locales(base_directory, msg_ids):
    is_valid = True

    available_languages = list()
    locales_dir = os.path.join(base_directory.resolve(), 'locales') + os.sep
    locale_directories = os.listdir(locales_dir)

    number_of_valid_translations = 0

    for locale_name in locale_directories:
        current_number_of_valid_translations = 0

        if locale_name[0:1] == '.':
            continue

        lang_sub_directory = os.path.join(
            locales_dir, locale_name, "LC_MESSAGES")

        if os.path.exists(lang_sub_directory):
            available_languages.append(locale_name)

            files = os.listdir(lang_sub_directory)
            for file in files:
                # for every .po file found, check if we have a .mo file
                if validate_po_file(locales_dir, locale_name, lang_sub_directory, file, msg_ids):
                    current_number_of_valid_translations += 1
                elif file.endswith('.po'):
                    # po file had errors, try generate new mo file and try again.
                    msgfmt_path = ensure_msgfmt_py()
                    if msgfmt_path is not None:
                        print(
                            '  - Trying to generate .mo file so it matches .po file')
                        bash_command = f"python {msgfmt_path} -o {os.path.join(lang_sub_directory, file.replace(
                                '.po', '.mo'))} {os.path.join(lang_sub_directory, file)}"

                        process = subprocess.Popen(
                            bash_command.split(),
                            stdout=subprocess.PIPE)
                        process.communicate()

                        if validate_po_file(locales_dir,
                                            locale_name,
                                            lang_sub_directory,
                                            file,
                                            msg_ids):
                            current_number_of_valid_translations += 1
                        else:
                            is_valid = False
                    else:
                        print(
                            '  - Unable to generate .mo file because'
                             'we could not find msgfmt.py in python installation')
                else:
                    is_valid = False

            if number_of_valid_translations == 0:
                number_of_valid_translations = current_number_of_valid_translations

            if number_of_valid_translations != current_number_of_valid_translations:
                print(
                    '  Different number of translation files for languages.'
                     'One or more language is missing a translation')
                is_valid = False
                continue
    if len(available_languages) > 0:
        print('')
        print(f'  Available Languages: {', '.join(available_languages)}')
    else:
        print('  No languages found')
    return is_valid

def get_content(url, allow_redirects=False, use_text_instead_of_content=True):
    """Trying to fetch the response content
    Attributes: url, as for the URL to fetch
    """

    try:
        headers = {
            'user-agent': (
                'Mozilla/5.0 (compatible; Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 '
                'Safari/537.36 Edg/88.0.705.56'
            )
        }

        a = requests.get(url, allow_redirects=allow_redirects,
                         headers=headers, timeout=120)

        if use_text_instead_of_content:
            content = a.text
        else:
            content = a.content
        return content
    except ssl.CertificateError as error:
        print(f'Info: Certificate error. {error.reason}')
    except requests.exceptions.SSLError as error:
        if 'http://' in url:  # trying the same URL over SSL/TLS
            print('Info: Trying SSL before giving up.')
            return get_content(url.replace('http://', 'https://'))
        print(f'Info: SSLError. {error}')
        return ''
    except requests.exceptions.ConnectionError as error:
        if 'http://' in url:  # trying the same URL over SSL/TLS
            print('Connection error! Info: Trying SSL before giving up.')
            return get_content(url.replace('http://', 'https://'))
        print(
            f'Connection error! Unfortunately the request for URL "{url}" failed.'
            f'\nMessage:\n{sys.exc_info()[0]}')
        return ''
    except Exception:
        print(
            f'Error! Unfortunately the request for URL "{url}" either timed out or '
            f'failed for other reason(s). The timeout is set to {120} seconds.\n'
            f'Message:\n{sys.exc_info()[0]}')
    return ''

def set_file(file_path, content, use_text_instead_of_content):
    """
    Writes the provided content to a file at the specified path.

    If 'use_text_instead_of_content' is True,
        the function opens the file in text mode and writes the content as a string.
    If 'use_text_instead_of_content' is False,
        the function opens the file in binary mode and writes the content as bytes.

    Args:
        file_path (str): The path to the file where the content will be written.
        content (str or bytes): The content to be written to the file.
        use_text_instead_of_content (bool): 
            Determines whether the file is opened in text or binary mode.

    Returns:
        None
    """
    if use_text_instead_of_content:
        with open(file_path, 'w', encoding='utf-8', newline='') as file:
            file.write(content)
    else:
        with open(file_path, 'wb') as file:
            file.write(content)

def ensure_msgfmt_py():
    """
    This function ensures the availability of the 'msgfmt.py' file in the system path.

    The function iterates over the system path, ignoring zip files.
    If 'msgfmt.py' is found in a directory, the path to 'msgfmt.py' is returned.
    If not found, the function checks a specific 'data' directory
    in the base directory of the script.
    If 'msgfmt.py' does not exist in the 'data' directory, the file is
    downloaded from the Python repository and saved in the 'data' directory.

    Returns:
        str: The path to 'msgfmt.py' if it exists in 
          the system path or the 'data' directory, else None.
    """
    for python_path in sys.path:
        a = python_path

        if a.endswith('.zip'):
            # Ignore zip files
            continue

        msgfmt_path = has_dir_msgfmt_py(a, 0)
        if msgfmt_path is not None:
            return msgfmt_path

        base_directory = Path(os.path.dirname(
            os.path.realpath(__file__)) + os.path.sep).parent.parent
        data_dir = os.path.join(base_directory.resolve(), 'data') + os.sep
        filename = 'msgfmt.py'
        file_path = os.path.join(data_dir,filename)

        if not os.path.exists(file_path):
            content = get_content(
                'https://raw.githubusercontent.com/python/cpython/main/Tools/i18n/msgfmt.py',
                 True,
                 True)
            set_file(file_path, content, True)
        return file_path
    return None


def has_dir_msgfmt_py(base_directory, depth):
    """
    Searches for the 'msgfmt.py' file within the specified directory and its subdirectories.

    Args:
        base_directory (str): The starting directory to search.
        depth (int): Current recursion depth (used for tracking).

    Returns:
        str or None: The path to 'msgfmt.py' if found, else None.

    Raises:
        FileNotFoundError: If the specified directory does not exist.
        PermissionError: If access to the directory is denied.
        NotADirectoryError: If the provided path is not a directory.
        RecursionError: If maximum recursion depth is exceeded.
    """

    try:
        files = os.listdir(base_directory)

        if 'msgfmt.py' in files:
            return os.path.join(base_directory, 'msgfmt.py')
        elif 'i18n' in files:
            return os.path.join(base_directory, 'i18n', 'msgfmt.py')
        elif 'Tools' in files:
            return os.path.join(base_directory, 'Tools', 'i18n', 'msgfmt.py')
        elif 'io.py' in files or \
            'base64.py' in files or \
            'calendar.py' in files or \
            'site-packages' in files:
            parent_dir = Path(os.path.dirname(
                os.path.realpath(base_directory)) + os.path.sep).parent
            return has_dir_msgfmt_py(parent_dir, depth + 1)

    except FileNotFoundError as ex:
        print('\t   Exception: Directory not found', ex)
    except PermissionError as ex:
        print('\t   Exception: Permission denied', ex)
    except NotADirectoryError as ex:
        print('\t   Exception: Not a directory', ex)
    except RecursionError as ex:
        print('\t   Exception: Maximum recursion depth exceeded', ex)

    return None


def main(argv):
    """
    WebPerf Core - Regression Test

    Usage:
    verify_result.py -h

    Options and arguments:
    -h/--help\t\t\t: Verify Help command
    -l/--language\t\t: Verify languages
    -c/--prep-config <activate feature, True or False>\t\t:
      Uses SAMPLE-config.py to creat config.py
    -t/--test <test number>\t: Verify result of specific test

    NOTE:
    If you get this in step "Setup config [...]" you forgot to
    add repository secret for your repository.
    More info can be found here: https://github.com/Webperf-se/webperf_core/issues/81
    """

    try:
        opts, _ = getopt.getopt(argv, "hlc:t:", [
                                   "help", "test=", "prep-config=", "language"])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if len(opts) == 0:
        print(main.__doc__)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):  # help
            print(main.__doc__)
            sys.exit(0)
        elif opt in ("-c", "--prep-config"):
            handle_pre_config(arg)
        elif opt in ("-l", "--language"):
            handle_language()
        elif opt in ("-t", "--test"):  # test id
            handle_test_result(arg)

    # No match for command so return error code to fail verification
    sys.exit(2)

def handle_test_result(arg):
    """ Terminate the programme with an error if our test contains unexpected content  """
    if validate_testresult(arg):
        sys.exit(0)
    else:
        sys.exit(2)

def handle_language():
    """ Terminate the programme with an error if we're unable to
      generate translations for all the modified language files """
    if validate_translations():
        sys.exit(0)
    else:
        sys.exit(2)

def handle_pre_config(arg):
    """ Terminate the programme with an error if we're unable to
      generate a config.py file from SAMPLE-config with a few alterations """
    if 'true' == arg.lower() or 'false' == arg.lower() or '1' == arg or '0' == arg:
        raise ValueError(
                    'c/prep-config argument has changed format,'
                    ' it doesn\'t support previous format')
    arguments = arg.split(',')

    if prepare_config_file('SAMPLE-config.py', 'config.py', arguments):
        sys.exit(0)
    else:
        sys.exit(2)


if __name__ == '__main__':
    main(sys.argv[1:])
