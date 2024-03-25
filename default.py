# -*- coding: utf-8 -*-
import sys
import os
import getopt
import gettext
from engines.sqlite import read_sites as sqlite_read_sites,\
    add_site as sqlite_add_site,\
    delete_site as sqlite_delete_site,\
    write_tests as sqlite_write_tests
from engines.csv import read_sites as csv_read_sites,\
    add_site as csv_add_site,\
    delete_site as csv_delete_site,\
    write_tests as csv_write_tests
from engines.sitemap import read_sites as sitemap_read_sites,\
    add_site as sitemap_add_site,\
    delete_site as sitemap_delete_site
from engines.sitespeed_result import read_sites as sitespeed_read_sites,\
    add_site as sitespeed_add_site,\
    delete_site as sitespeed_delete_site
from engines.webperf import read_sites as webperf_read_sites,\
    add_site as webperf_add_site,\
    delete_site as webperf_delete_site
from engines.json import read_sites as json_read_sites,\
    add_site as json_add_site,\
    delete_site as json_delete_site,\
    write_tests as json_write_tests
from engines.gov import write_tests as gov_write_tests
from engines.sql import write_tests as sql_write_tests
from tests.utils import clean_cache_files
import utils


def validate_test_type(test_types):
    if utils.TEST_HTML in test_types and \
          utils.TEST_PAGE_NOT_FOUND in test_types and \
          utils.TEST_CSS in test_types and \
          utils.TEST_WEBBKOLL in test_types and \
          utils.TEST_GOOGLE_LIGHTHOUSE in test_types and \
          utils.TEST_GOOGLE_LIGHTHOUSE_PWA in test_types and \
          utils.TEST_GOOGLE_LIGHTHOUSE_A11Y in test_types and \
          utils.TEST_GOOGLE_LIGHTHOUSE_SEO in test_types and \
          utils.TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE in test_types and \
          utils.TEST_STANDARD_FILES in test_types and \
          utils.TEST_YELLOW_LAB_TOOLS in test_types and \
          utils.TEST_PA11Y in test_types and \
          utils.TEST_HTTP in test_types and \
          utils.TEST_ENERGY_EFFICIENCY in test_types and \
          utils.TEST_TRACKING in test_types and \
          utils.TEST_SITESPEED in test_types and \
          utils.TEST_EMAIL in test_types and \
          utils.TEST_SOFTWARE in test_types and \
          utils.TEST_A11Y_STATEMENT in test_types:
        return []
    return test_types

def show_help(global_translation):
    print(global_translation('TEXT_COMMAND_USAGE'))
    sys.exit()

def write_test_results(sites, output_filename, test_results):
    if len(output_filename) > 0:
        file_ending = ""
        file_long_ending = ""
        if len(output_filename) > 4:
            file_ending = output_filename[-4:].lower()
        if len(output_filename) > 7:
            file_long_ending = output_filename[-7:].lower()
        if file_ending == ".csv":
            write_tests = csv_write_tests
        elif file_ending == ".gov":
            write_tests = gov_write_tests
        elif file_ending == ".sql":
            write_tests = sql_write_tests
        elif file_long_ending == ".sqlite":
            write_tests = sqlite_write_tests
        else:
            write_tests = json_write_tests

            # use loaded engine to write tests
        write_tests(output_filename, test_results, sites)

def show_test_help(global_translation):
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_GOOGLE_LIGHTHOUSE'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_PAGE_NOT_FOUND'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_GOOGLE_LIGHTHOUSE_SEO'))
    print(global_translation(
                'TEXT_TEST_VALID_ARGUMENTS_GOOGLE_LIGHTHOUSE_BEST_PRACTICE'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_HTML'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_CSS'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_GOOGLE_LIGHTHOUSE_PWA'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_STANDARD_FILES'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_GOOGLE_LIGHTHOUSE_A11Y'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_SITESPEED'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_YELLOW_LAB_TOOLS'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_PA11Y'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_WEBBKOLL'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_HTTP'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_ENERGY_EFFICIENCY'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_TRACKING'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_EMAIL'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_SOFTWARE'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_A11Y_STATEMENT'))
    sys.exit()

def try_load_language(arg):
    lang_code = 'en'
    available_languages = []
    locale_dirs = os.listdir('locales')
    found_lang = False

    for locale_name in locale_dirs:
        if locale_name[0:1] == '.':
            continue

        language_sub_directory = os.path.join(
                    'locales', locale_name, "LC_MESSAGES")

        if os.path.exists(language_sub_directory):
            available_languages.append(locale_name)

            if locale_name == arg:
                lang_code = arg
                found_lang = True

                language = gettext.translation(
                            'webperf-core', localedir='locales', languages=[lang_code])
                language.install()
                _ = language.gettext

    if not found_lang:
                # Not translateable
        print(
                    'Language not found, only the following languages are available:',
                    available_languages)
        sys.exit(2)
    return lang_code


def get_site_input_handlers(input_filename):
    file_ending = ""
    file_long_ending = ""
    if len(input_filename) > 4:
        file_ending = input_filename[-4:].lower()
    if len(input_filename) > 7:
        file_long_ending = input_filename[-7:].lower()

    if file_long_ending == ".sqlite":
        read_sites = sqlite_read_sites
        add_site = sqlite_add_site
        delete_site = sqlite_delete_site
    elif file_ending == ".csv":
        read_sites = csv_read_sites
        add_site = csv_add_site
        delete_site = csv_delete_site
    elif file_ending == ".xml" or file_long_ending == ".xml.gz":
                # https://example.com/sitemap.xml
                # https://example.com/sitemap.xml.gz
        read_sites = sitemap_read_sites
        add_site = sitemap_add_site
        delete_site = sitemap_delete_site
    elif file_long_ending == ".result":
        read_sites = sitespeed_read_sites
        add_site = sitespeed_add_site
        delete_site = sitespeed_delete_site
    elif file_long_ending == ".webprf":
        read_sites = webperf_read_sites
        add_site = webperf_add_site
        delete_site = webperf_delete_site
    else:
        read_sites = json_read_sites
        add_site = json_add_site
        delete_site = json_delete_site
    return read_sites,add_site,delete_site



def main(argv):
    """
    WebPerf Core

    Usage:
    default.py -u https://webperf.se

    Options and arguments:
    -h/--help\t\t\t: Help information on how to use script
    -u/--url <site url>\t\t: website url to test against
    -t/--test <test number>\t: run ONE test (use ? to list available tests)
    -r/--review\t\t\t: show reviews in terminal
    -i/--input <file path>\t: input file path (.json/.sqlite)
    -o/--output <file path>\t: output file path (.json/.csv/.sql/.sqlite)
    -A/--addUrl <site url>\t: website url (required in combination with -i/--input)
    -D/--deleteUrl <site url>\t: website url (required in combination with -i/--input)
    -L/--language <lang code>\t: language used for output(en = default/sv)
    """

    test_types = list(utils.TEST_ALL)
    sites = []
    output_filename = ''
    input_filename = ''
    input_skip = 0
    input_take = -1
    show_reviews = False
    add_url = ''
    delete_url = ''
    lang_code = 'en'
    language = False

    # add support for default (en) language
    language = gettext.translation(
        'webperf-core', localedir='locales', languages=[lang_code])
    language.install()
    global_translation = language.gettext

    try:
        opts, _ = getopt.getopt(argv, "hu:t:i:o:rA:D:L:", [
                                   "help", "url=", "test=", "input=", "output=",
                                   "review", "report", "addUrl=", "deleteUrl=",
                                   "language=", "input-skip=", "input-take="])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if len(opts) == 0:
        show_help(global_translation)
        return

    for opt, arg in opts:
        if opt in ('-h', '--help'):  # help
            show_help(global_translation)
            return
        if opt in ("-u", "--url"):  # site url
            sites.append([0, arg])
        elif opt in ("-A", "--addUrl"):  # site url
            add_url = arg
        elif opt in ("-D", "--deleteUrl"):  # site url
            delete_url = arg
        elif opt in ("-L", "--language"):  # language code
            # loop all available languages and verify language exist
            lang_code = try_load_language(arg)
        elif opt in ("-t", "--test"):  # test type
            try:
                tmp_test_types = list(map(int, arg.split(',')))
                test_types = validate_test_type(tmp_test_types)
            except (TypeError, ValueError):
                test_types = []

            if len(test_types) == 0:
                show_test_help(global_translation)
                return
        elif opt in ("-i", "--input"):  # input file path
            input_filename = arg

            read_sites, add_site, delete_site = get_site_input_handlers(input_filename)
        elif opt in ("--input-skip"):  # specifies number of items to skip in the begining
            try:
                input_skip = int(arg)
            except TypeError:
                print(global_translation('TEXT_COMMAND_USAGE'))
                sys.exit(2)
        elif opt in ("--input-take"):  # specifies number of items to take
            try:
                input_take = int(arg)
            except TypeError:
                print(global_translation('TEXT_COMMAND_USAGE'))
                sys.exit(2)
        elif opt in ("-o", "--output"):  # output file path
            output_filename = arg
        elif opt in ("-r", "--review", "--report"):  # writes reviews directly in terminal
            show_reviews = True

    if input_filename != '':
        sites = read_sites(input_filename, input_skip, input_take)

    if add_url != '':
        # check if website url should be added
        sites = add_site(input_filename, add_url, input_skip, input_take)
    elif delete_url != '':
        # check if website url should be deleted
        sites = delete_site(input_filename, delete_url, input_skip, input_take)
    elif len(sites) > 0:
        # run test(s) for every website
        test_results = utils.test_sites(global_translation,
                                        lang_code,
                                        sites,
                                        test_types=test_types,
                                        show_reviews=show_reviews)

        write_test_results(sites, output_filename, test_results)
            # Cleanup exipred cache
        clean_cache_files()
    else:
        print(global_translation('TEXT_COMMAND_USAGE'))



if __name__ == '__main__':
    main(sys.argv[1:])
