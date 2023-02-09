# -*- coding: utf-8 -*-
import sys
import getopt
import datetime
from models import Sites, SiteTests
import config
import gettext
from tests.utils import clean_cache_files
import utils


def validate_test_type(test_type):
    if test_type != utils.TEST_HTML and test_type != utils.TEST_PAGE_NOT_FOUND and test_type != utils.TEST_CSS and test_type != utils.TEST_WEBBKOLL and test_type != utils.TEST_GOOGLE_LIGHTHOUSE and test_type != utils.TEST_GOOGLE_LIGHTHOUSE_PWA and test_type != utils.TEST_GOOGLE_LIGHTHOUSE_A11Y and test_type != utils.TEST_GOOGLE_LIGHTHOUSE_SEO and test_type != utils.TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE and test_type != utils.TEST_STANDARD_FILES and test_type != utils.TEST_YELLOW_LAB_TOOLS and test_type != utils.TEST_PA11Y and test_type != utils.TEST_HTTP and test_type != utils.TEST_ENERGY_EFFICIENCY and test_type != utils.TEST_TRACKING and test_type != utils.TEST_SITESPEED and test_type != utils.TEST_EMAIL and test_type != utils.TEST_SOFTWARE and test_type != utils.TEST_A11Y_STATEMENT:
        print(_('TEXT_TEST_VALID_ARGUMENTS'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_GOOGLE_LIGHTHOUSE'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_PAGE_NOT_FOUND'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_GOOGLE_LIGHTHOUSE_SEO'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_GOOGLE_LIGHTHOUSE_BEST_PRACTICE'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_HTML'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_CSS'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_GOOGLE_LIGHTHOUSE_PWA'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_STANDARD_FILES'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_GOOGLE_LIGHTHOUSE_A11Y'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_SITESPEED'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_YELLOW_LAB_TOOLS'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_PA11Y'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_WEBBKOLL'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_HTTP'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_ENERGY_EFFICIENCY'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_TRACKING'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_EMAIL'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_SOFTWARE'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_A11Y_STATEMENT'))
        return -2
    else:
        return test_type


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

    test_type = utils.TEST_ALL
    sites = list()
    output_filename = ''
    input_filename = ''
    input_skip = 0
    input_take = -1
    show_reviews = False
    show_help = False
    add_url = ''
    delete_url = ''
    langCode = 'en'
    language = False

    # add support for default (en) language
    language = gettext.translation(
        'webperf-core', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    try:
        opts, args = getopt.getopt(argv, "hu:t:i:o:rA:D:L:", [
                                   "help", "url=", "test=", "input=", "output=", "review", "report", "addUrl=", "deleteUrl=", "language=", "input-skip=", "input-take="])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if (opts.__len__() == 0):
        show_help = True

    for opt, arg in opts:
        if opt in ('-h', '--help'):  # help
            show_help = True
        elif opt in ("-u", "--url"):  # site url
            sites.append([0, arg])
        elif opt in ("-A", "--addUrl"):  # site url
            add_url = arg
        elif opt in ("-D", "--deleteUrl"):  # site url
            delete_url = arg
        elif opt in ("-L", "--language"):  # language code
            # loop all available languages and verify language exist
            import os
            availableLanguages = list()
            localeDirs = os.listdir('locales')
            foundLang = False

            for localeName in localeDirs:
                if (localeName[0:1] == '.'):
                    continue

                languageSubDirectory = os.path.join(
                    'locales', localeName, "LC_MESSAGES")

                if (os.path.exists(languageSubDirectory)):
                    availableLanguages.append(localeName)

                    if (localeName == arg):
                        langCode = arg
                        foundLang = True

                        language = gettext.translation(
                            'webperf-core', localedir='locales', languages=[langCode])
                        language.install()
                        _ = language.gettext

            if (not foundLang):
                # Not translateable
                print(
                    'Language not found, only the following languages are available:', availableLanguages)
                sys.exit(2)
        elif opt in ("-t", "--test"):  # test type
            try:
                tmp_test_type = int(arg)
                test_type = validate_test_type(tmp_test_type)
                if test_type == -2:
                    sys.exit(2)
            except Exception:
                validate_test_type(arg)
                sys.exit()
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
            elif file_long_ending == ".result":
                from engines.sitespeed_result import read_sites, add_site, delete_site
            elif file_long_ending == ".webprf":
                from engines.webperf import read_sites, add_site, delete_site
            else:
                from engines.json import read_sites, add_site, delete_site
            pass
        elif opt in ("--input-skip"):  # specifies number of items to skip in the begining
            try:
                input_skip = int(arg)
            except Exception:
                print(_('TEXT_COMMAND_USAGE'))
                sys.exit(2)
            pass
        elif opt in ("--input-take"):  # specifies number of items to take
            try:
                input_take = int(arg)
            except Exception:
                print(_('TEXT_COMMAND_USAGE'))
                sys.exit(2)
            pass
        elif opt in ("-o", "--output"):  # output file path
            output_filename = arg
            pass
        elif opt in ("-r", "--review", "--report"):  # writes reviews directly in terminal
            show_reviews = True
            pass

    if (show_help):
        print(_('TEXT_COMMAND_USAGE'))
        sys.exit()

    if (input_filename != ''):
        sites = read_sites(input_filename, input_skip, input_take)

    if (add_url != ''):
        # check if website url should be added
        sites = add_site(input_filename, add_url, input_skip, input_take)
    elif (delete_url != ''):
        # check if website url should be deleted
        sites = delete_site(input_filename, delete_url, input_skip, input_take)
    elif (len(sites)):
        # run test(s) for every website
        test_results = utils.test_sites(_,
                                        langCode, sites, test_type=test_type, show_reviews=show_reviews)
        if (len(output_filename) > 0):
            file_ending = ""
            file_long_ending = ""
            if (len(output_filename) > 4):
                file_ending = output_filename[-4:].lower()
            if (len(output_filename) > 7):
                file_long_ending = output_filename[-7:].lower()
            if (file_ending == ".csv"):
                from engines.csv import write_tests
            elif file_ending == ".sql":
                from engines.sql import write_tests
            elif file_long_ending == ".sqlite":
                from engines.sqlite import write_tests
            else:
                from engines.json import write_tests

            # use loaded engine to write tests
            write_tests(output_filename, test_results)
            # Cleanup exipred cache
        clean_cache_files()
    else:
        print(_('TEXT_COMMAND_USAGE'))


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    main(sys.argv[1:])
