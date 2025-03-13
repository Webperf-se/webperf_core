# -*- coding: utf-8 -*-
from pathlib import Path
import os
import os.path
import ssl
import sys
import re
import gettext
import subprocess
import requests

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
        lines = []
        data = file.readlines()
        for line in data:
            lines.append(line)
    return '\n'.join(lines)


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
                (f'  Expected compiled translation file not found, '
                  f"file: \"{file.replace('.po', '.mo')}\""))
            return False

        clear_cache = True
        language_module = file.replace('.po', '')
        language = get_language(locales_dir, locale_name, language_module, clear_cache)

        file_is_valid = diff_mo_and_po_file(
            locale_name,
            language,
            file_mo,
            msg_ids)

    else:
        print('')
        print('')
        print(f'  # {file} [{locale_name}]')
        print(
            '  Unexpected file extension found. Expected .po and .mo.')
        return False
    return file_is_valid

def get_language(locales_dir, locale_name, language_module, clear_cache):
    """
    This function retrieves the specified language translation module.

    Parameters:
    locales_dir (str): The directory path where locale files are stored.
    locale_name (str): The name of the locale for which the translation is needed.
    language_module (str): The name of the language module to be used for translation.
    clear_cache (bool): If set to True, the internal cache of gettext is cleared.

    Returns:
    gettext.GNUTranslations: A translation object for the specified language.

    Note:
    The gettext module internally caches all .mo files. If clear_cache is set to True,
    this function clears the cache to ensure that the newly generated .mo file is read.
    """

    if clear_cache:
        # NOTE: gettext is internally caching all mo files,
        #       we need to clear this variable to readd the newly generated .mo file.
        gettext._translations = {} # pylint: disable=protected-access

    language = gettext.translation(
        language_module, localedir=locales_dir, languages=[locale_name])
    language.install()

    return language

def diff_mo_and_po_file(locale_name, language, file_mo, msg_ids):
    """
    This function compares the content of .mo and .po files to ensure they match.

    Parameters:
    locale_name (str): The name of the specified language.
    language (gettext.GNUTranslations): The gettext translation object for the specified language.
    file_mo (str): The name of the .mo file.
    msg_ids (dict): A dictionary to store the msgid and corresponding text from the .po file.

    Returns:
    bool: True if the .mo and .po files match, False otherwise.

    Note:
    The function iterates through the .po file and
      checks if each text is present and equal in the .mo file.
    If there are more than 5 mismatches, it stops checking and returns False.
    If an IOError occurs (e.g., the .mo file cannot be loaded), it also returns False.
    """

    file_is_valid = True
    # for every .mo file found, try to load it to verify it works
    n_of_errors = 0
    file_po = file_mo.replace('.mo', '.po')
    try:

        # Make sure every text in .po file is present (and equal) in .mo file
        file_po_content = get_file_content(file_po)

        regex = r"^msgid \"(?P<id>.+)\"[^m]+^msgstr \"(?P<text>.+)\"$"
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
            if msg_id not in msg_ids:
                msg_ids[msg_id] = []

            tmp = file_po.split('\\')

            msg_ids[msg_id].append({
                    'text': msg_txt,
                    'locale_name': locale_name,
                    'location': tmp[len(tmp) - 1]
                })

            if lang_txt == msg_id and msg_id != msg_txt:
                print(
                    f'  - Could not find text for msgid "{msg_id}" in file: {file_mo}')
                print(f'  - msgid: {msg_id}')
                print_limited_message('expected text', msg_txt, 135)
                print_limited_message('recived text', lang_txt, 135)
                n_of_errors += 1
                continue
            if lang_txt != msg_txt:
                print(
                    '  ## Text missmatch:')
                print(f'  - msgid: {msg_id}')
                print_limited_message('expected text', msg_txt, 135)
                print_limited_message('recived text', lang_txt, 135)

                n_of_errors += 1
                continue
        if n_of_errors > 0:
            file_is_valid = False
    except IOError:
        print(
            f'  - Unable to load "{file_mo}" as a valid translation')
        return False

    if n_of_errors > 0:
        print('')
        print('')
    else:
        print('    - OK')

    return file_is_valid

def print_limited_message(pre_text, msg_txt, limit):
    """
    Prints a limited portion of a message, truncating it if necessary.

    Args:
        pre_text (str): A prefix or label for the message.
        msg_txt (str): The full message text.
        limit (int): The maximum length of the message to display.

    Returns:
        None
    """
    if len(msg_txt) > limit:
        print(
            f'    - {pre_text}: "{msg_txt[0: limit]}[...]"')
    else:
        print(
            f'    - {pre_text}: "{msg_txt}"')

def validate_translations():
    """
    Validates the translation files and usage in the project.

    This function performs two main validation steps:
    1. Validates the existence and correctness of .po and .mo files in the project.
    2. Validates the usage of global_translation() and
       local_translation() in .py files in the project.

    The function uses the `validate_locales` function to validate .po and .mo files,
    and the `validate_python_files` function to validate global_translation() and
       local_translation() usage.

    Returns:
        bool: True if all validations pass, False otherwise.
    """

    msg_ids = {}
    # loop all available languages and verify language exist
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    print('Validate .po and .mo files')
    is_valid = validate_locales(base_directory, msg_ids)

    root_folder = base_directory.resolve()

    print('')
    print('')
    print('Validate global_translation() and local_translation() uses in .py files')
    file_is_valid = validate_python_files(root_folder, msg_ids)

    is_valid = is_valid and file_is_valid

    return is_valid

def validate_msg_ids(available_languages, msg_ids):
    """
    Validates that all msg_ids exist in all available languages.

    Parameters:
    available_languages (list): A list of locales codes that indicates found languages.
    msg_ids (list): A list of valid message IDs.

    Returns:
    bool: True if all msg_ids exist in every available language, False otherwise.
    """
    is_valid = True
    msg_ids_with_missing_language = {}
    nof_languages = len(available_languages)
    for msg_id, msg_list in msg_ids.items():
        grouped_by_file = {}
        for obj in msg_list:
            location = obj['location']
            if location not in grouped_by_file:
                grouped_by_file[location] = []
            grouped_by_file[location].append(obj)

        for location, obj_list in grouped_by_file.items():
            if len(obj_list) != nof_languages:
                msg_ids_with_missing_language[msg_id] = msg_list
                break

    print('')
    print('')
    print('Validate that translations has the same msg_id:s')
    for msg_id, msg_list in msg_ids_with_missing_language.items():
        msg_langs = []
        for msg in msg_list:
            msg_langs.append(msg['locale_name'])
        nof_langs = len(msg_langs)
        tmp_str = '","'.join(msg_langs)
        if nof_langs < nof_languages:
            print(f"  # msgid \"{msg_id}\" only in \"{tmp_str}\"")
        else:
            print(f"  # msgid \"{msg_id}\" occur multiple times \"{tmp_str}\"")

    if len(msg_ids_with_missing_language) > 0:
        is_valid = False
    else:
        print('  - OK')
    return is_valid

def validate_python_files(folder, msg_ids):
    """
    Validates all Python files in a given directory and its subdirectories.

    This function recursively traverses through the given directory and its subdirectories,
    and validates each Python file it encounters using the `validate_python_file` function.
    A Python file is considered valid if it passes all the checks in
    the `validate_python_file` function.

    Parameters:
    folder (str): The path to the directory that contains the Python files to be validated.
    msg_ids (list): A list of message IDs to be used for validation.

    Returns:
    bool: True if all Python files in the directory and its subdirectories are valid,
    False otherwise.

    Raises:
    OSError: If the given directory cannot be read. The function will return True in this case, 
             as it assumes that there are no Python files in an unreadable directory.
    """

    files_are_valid = True
    listing = False
    try:
        listing = os.listdir(folder)
    except OSError:
        # Ignore: is not a directory or has some read problem..
        return files_are_valid
    for item in listing:
        if '.' in item:
            if len(item) < 3 or not item.endswith('.py'):
                continue
            current_file = os.path.join(
                folder, item)

            file_is_valid = validate_python_file(current_file, msg_ids)
            files_are_valid = files_are_valid and file_is_valid
        else:
            current_dir = os.path.join(
                folder, item) + os.path.sep
            dir_is_valid = validate_python_files(current_dir, msg_ids)
            files_are_valid = files_are_valid and dir_is_valid

    return files_are_valid


def validate_python_file(current_file, msg_ids):
    """
    Validates a Python file by checking for missing message IDs.

    This function reads the content of the given Python file and
    searches for message IDs using a regular expression.
    It then checks if each found message ID is present in the provided list of message IDs.
    If a message ID is not found in the list, it's considered a validation error.
    The function stops checking after encountering 5 errors.

    Parameters:
    current_file (str): The path to the Python file to be validated.
    msg_ids (list): A list of valid message IDs.

    Returns:
    bool: True if the Python file is valid
      (i.e., all found message IDs are in the list of valid IDs),
      False otherwise.

    Note:
    The function prints the name of the file being validated,
    and any missing message IDs it encounters. If the file is valid, it prints 'OK'.
    """

    file_name = current_file[current_file.rindex(os.sep) + 1:]
    print('  #', file_name)
    file_is_valid = True
    # for every .mo file found, try to load it to verify it works
    n_of_errors = 0

    file_py_content = get_file_content(current_file)
    regex = r"(global|local)_translation\(['\"](?P<msgid>[^\"']+)[\"']\)"
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

def get_locales(base_directory):
    available_languages = []
    locales_dir = os.path.join(base_directory.resolve(), 'locales') + os.sep
    locale_directories = os.listdir(locales_dir)

    for locale_name in locale_directories:
        current_number_of_valid_translations = 0

        if locale_name[0:1] == '.':
            continue

        lang_sub_directory = os.path.join(
            locales_dir, locale_name, "LC_MESSAGES")

        if os.path.exists(lang_sub_directory):
            available_languages.append(locale_name)

    return available_languages

def validate_locales(base_directory, msg_ids):
    """
    Validates all locale directories in a given base directory.

    This function traverses through the given base directory and
    validates each locale directory it encounters using the `validate_po_file` function.
    A locale directory is considered valid if all its .po files pass the validation checks in
    the `validate_po_file` function.

    Parameters:
    base_directory (str):
      The path to the base directory that contains the locale directories to be validated.
    msg_ids (list): A list of valid message IDs.

    Returns:
    bool: True if all locale directories in the base directory are valid
      (i.e., all .po files in each directory are valid), False otherwise.

    Note:
    The function prints the name of each locale directory being validated,
    and any validation errors it encounters. 
    If a .po file fails validation, the function tries to generate a new .mo file and
    validate it again. If all locale directories are valid, it prints the available languages.
    """

    is_valid = True

    available_languages = get_locales(base_directory)
    locales_dir = os.path.join(base_directory.resolve(), 'locales') + os.sep

    number_of_valid_translations = 0

    for locale_name in available_languages:
        current_number_of_valid_translations = 0

        lang_sub_directory = os.path.join(
            locales_dir, locale_name, "LC_MESSAGES")

        if not validate_locale(msg_ids,
                                locales_dir,
                                locale_name,
                                current_number_of_valid_translations,
                                lang_sub_directory):
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
        print(f"  Available Languages: {', '.join(available_languages)}")
    else:
        print('  No languages found')

    is_valid = is_valid and validate_msg_ids(available_languages, msg_ids)

    return is_valid

def validate_locale(msg_ids, locales_dir,
                    locale_name,
                    current_number_of_valid_translations,
                    lang_sub_directory):
    """
    This function validates the locale by comparing the .po and .mo files
      in the given language sub-directory.

    Parameters:
    msg_ids (dict): A dictionary to store the msgid and corresponding text from the .po file.
    locales_dir (str): The directory path where locale files are stored.
    locale_name (str): The name of the locale for which the validation is needed.
    current_number_of_valid_translations (int): The current number of valid translations.
    lang_sub_directory (str): The directory path where the
      language files for the specific locale are stored.

    Returns:
    bool: True if the locale is valid, False otherwise.

    Note:
    The function iterates through all the files in the language sub-directory.
      For each .po file, it checks if a corresponding .mo file exists and validates it.
      If the .po file has errors, it tries to generate a new .mo file and validates it again.
      If the .mo file cannot be generated or if the validation fails, the function returns False.
    """

    is_valid = True
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
                bash_command = (f"python {msgfmt_path} -o ",
                                        f"{os.path.join(lang_sub_directory, file.replace('.po', '.mo'))} ",
                                        f"{os.path.join(lang_sub_directory, file)}")
                # Konvertera tuple till sträng
                bash_command = "".join(bash_command)

                with subprocess.Popen(
                            bash_command.split(),
                            stdout=subprocess.PIPE) as process:
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
    except requests.exceptions.Timeout:
        print(
            f'Timeout error! Unfortunately the request for URL "{url}" timed out. '
            f'The timeout is set to {120} seconds.\n'
            f'Message:\n{sys.exc_info()[0]}')
    except requests.exceptions.RequestException as error:
        print(
            f'Error! Unfortunately the request for URL "{url}" failed for other reason(s).\n'
            f'Message:\n{error}')
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
            os.path.realpath(__file__)) + os.path.sep).parent
        data_dir = os.path.join(base_directory.resolve(), 'data') + os.sep
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

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
        if 'i18n' in files:
            return os.path.join(base_directory, 'i18n', 'msgfmt.py')
        if 'Tools' in files:
            return os.path.join(base_directory, 'Tools', 'i18n', 'msgfmt.py')
        if 'io.py' in files or \
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
