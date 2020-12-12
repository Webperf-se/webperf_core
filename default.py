#-*- coding: utf-8 -*-
import sys, getopt
import datetime
from models import Sites, SiteTests
import config
import gettext
_ = gettext.gettext

TEST_ALL = -1

(TEST_UNKNOWN_01, TEST_GOOGLE_LIGHTHOUSE, TEST_PAGE_NOT_FOUND, TEST_UNKNOWN_03, TEST_GOOGLE_LIGHTHOUSE_SEO, TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE, TEST_HTML, TEST_CSS, TEST_GOOGLE_LIGHTHOUSE_PWA, TEST_STANDARD_FILES, TEST_GOOGLE_LIGHTHOUSE_A11Y, TEST_UNKNOWN_11, TEST_UNKNOWN_12, TEST_UNKNOWN_13, TEST_UNKNOWN_14, TEST_UNKNOWN_15, TEST_UNKNOWN_16, TEST_YELLOW_LAB_TOOLS, TEST_UNKNOWN_18, TEST_UNKNOWN_19, TEST_WEBBKOLL) = range(21)

def testsites(langCode, sites, test_type=None, show_reviews=False, only_test_untested_last_hours=24, order_by='title ASC'):
    """
    Executing the actual tests.
    Attributes:
    * test_type=num|None to execute all available tests
    """

    result = list()

    # TODO: implementera test_type=None

    print(_('TEXT_TEST_START_HEADER'))

    i = 1

    print(_('TEXT_TESTING_NUMBER_OF_SITES').format(len(sites)))

    for site in sites:
        site_id = site[0]
        website = site[1]
        print(_('TEXT_TESTING_SITE').format(i, website))
        the_test_result = None

        try:
            if test_type == TEST_PAGE_NOT_FOUND:
                from tests.page_not_found import run_test
            elif test_type == TEST_HTML:
                from tests.html_validator_w3c import run_test
            elif test_type == TEST_CSS:
                from tests.css_validator_w3c import run_test
            elif test_type == TEST_WEBBKOLL:
                from tests.privacy_webbkollen import run_test
            elif test_type == TEST_GOOGLE_LIGHTHOUSE:
                from tests.performance_lighthouse import run_test
            elif test_type == TEST_GOOGLE_LIGHTHOUSE_SEO:
                from tests.seo_lighthouse import run_test
            elif test_type == TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE:
                from tests.best_practice_lighthouse import run_test
            elif test_type == TEST_GOOGLE_LIGHTHOUSE_PWA:
                from tests.pwa_lighthouse import run_test
            elif test_type == TEST_STANDARD_FILES:
                from tests.standard_files import run_test
            elif test_type == TEST_GOOGLE_LIGHTHOUSE_A11Y:
                from tests.a11y_lighthouse import run_test
            elif test_type == TEST_YELLOW_LAB_TOOLS:
                from tests.frontend_quality_yellow_lab_tools import run_test

            the_test_result = run_test(langCode, website)

            if the_test_result != None:
                print(_('TEXT_SITE_RATING'), the_test_result[0])
                if show_reviews:
                    print(_('TEXT_SITE_REVIEW'), the_test_result[1])

                json_data = ''
                try:
                    json_data = the_test_result[2]
                except:
                    json_data = ''
                    pass

                checkreport = str(the_test_result[1]).encode('utf-8') # för att lösa encoding-probs
                jsondata = str(json_data).encode('utf-8') # --//--

                site_test = SiteTests(site_id=site_id, type_of_test=test_type, check_report=checkreport, rating=the_test_result[0], test_date=datetime.datetime.now(), json_check_data=jsondata).todata()

                result.append(site_test)

                the_test_result = None # 190506 för att inte skriva testresultat till sajter när testet kraschat. Måste det sättas till ''?
        except Exception as e:
            print(_('TEXT_EXCEPTION'), website, '\n', e)
            pass

        i += 1
    
    return result

def testing(langCode, sites, test_type= TEST_ALL, show_reviews= False):
    print(_('TEXT_TESTING_START_HEADER').format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    tests = list()
    ##############
    if (test_type == TEST_ALL or test_type == TEST_GOOGLE_LIGHTHOUSE):
        print(_('TEXT_TEST_GOOGLE_LIGHTHOUSE'))
        tests.extend(testsites(langCode, sites, test_type=TEST_GOOGLE_LIGHTHOUSE, show_reviews=show_reviews))
    if (test_type == TEST_ALL or test_type == TEST_GOOGLE_LIGHTHOUSE_A11Y):
        print(_('TEXT_TEST_GOOGLE_LIGHTHOUSE_A11Y'))
        tests.extend(testsites(langCode, sites, test_type=TEST_GOOGLE_LIGHTHOUSE_A11Y, show_reviews=show_reviews))
    if (test_type == TEST_ALL or test_type == TEST_GOOGLE_LIGHTHOUSE_SEO):
        print(_('TEXT_TEST_GOOGLE_LIGHTHOUSE_SEO'))
        tests.extend(testsites(langCode, sites, test_type=TEST_GOOGLE_LIGHTHOUSE_SEO, show_reviews=show_reviews))
    if (test_type == TEST_ALL or test_type == TEST_GOOGLE_LIGHTHOUSE_PWA):
        print(_('TEXT_TEST_GOOGLE_LIGHTHOUSE_PWA'))
        tests.extend(testsites(langCode, sites, test_type=TEST_GOOGLE_LIGHTHOUSE_PWA, show_reviews=show_reviews))
    if (test_type == TEST_ALL or test_type == TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE):
        print(_('TEXT_TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE'))
        tests.extend(testsites(langCode, sites, test_type=TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE, show_reviews=show_reviews))
    if (test_type == TEST_ALL or test_type == TEST_PAGE_NOT_FOUND):
        tests.extend(testsites(langCode, sites, test_type=TEST_PAGE_NOT_FOUND, show_reviews=show_reviews))
    if (test_type == TEST_ALL or test_type == TEST_HTML):
        tests.extend(testsites(langCode, sites, test_type=TEST_HTML, show_reviews=show_reviews))
    if (test_type == TEST_ALL or test_type == TEST_CSS):
        tests.extend(testsites(langCode, sites, test_type=TEST_CSS, show_reviews=show_reviews))
    if (test_type == TEST_ALL or test_type == TEST_WEBBKOLL):
        tests.extend(testsites(langCode, sites, test_type=TEST_WEBBKOLL, show_reviews=show_reviews))
    if (test_type == TEST_ALL or test_type == TEST_STANDARD_FILES):
        tests.extend(testsites(langCode, sites, test_type=TEST_STANDARD_FILES, show_reviews=show_reviews))
    if (test_type == TEST_ALL or test_type == TEST_YELLOW_LAB_TOOLS):
        tests.extend(testsites(langCode, sites, test_type=TEST_YELLOW_LAB_TOOLS, show_reviews=show_reviews))
    
    return tests

def validate_test_type(test_type):
    if test_type != TEST_HTML and test_type != TEST_PAGE_NOT_FOUND and test_type != TEST_CSS and test_type != TEST_WEBBKOLL and test_type != TEST_GOOGLE_LIGHTHOUSE and test_type != TEST_GOOGLE_LIGHTHOUSE_PWA and test_type != TEST_GOOGLE_LIGHTHOUSE_A11Y and test_type != TEST_GOOGLE_LIGHTHOUSE_SEO and test_type != TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE and test_type != TEST_STANDARD_FILES and test_type != TEST_YELLOW_LAB_TOOLS:
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
        print(_('TEXT_TEST_VALID_ARGUMENTS_YELLOW_LAB_TOOLS'))
        print(_('TEXT_TEST_VALID_ARGUMENTS_WEBBKOLL'))
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
    -t/--test <1/2/4/5/6/7/8/9/10/20>\t: runs ONE specific test against website(s)
    -r/--review\t\t\t: show reviews in terminal
    -i/--input <file path>\t: input file path (.json/.sqlite)
    -o/--output <file path>\t: output file path (.json/.csv/.sql/.sqlite)
    -A/--addUrl <site url>\t: website url (required in compination with -i/--input)
    -D/--deleteUrl <site url>\t: website url (required in compination with -i/--input)
    -L/--language <lang code>\t: language used for output(en = default/sv)
    """

    test_type = TEST_ALL
    sites = list()
    output_filename = ''
    input_filename = ''
    show_reviews = False
    show_help = False
    add_url = ''
    delete_url = ''
    langCode = 'en'
    language = False
    global _

    # add support for default (en) language
    language = gettext.translation('webperf-core', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext


    try:
        opts, args = getopt.getopt(argv,"hu:t:i:o:rA:D:L:",["help","url","test", "input", "output", "review", "report", "addUrl", "deleteUrl", "language"])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if (opts.__len__() == 0):
        show_help = True

    for opt, arg in opts:
        if opt in ('-h', '--help'): # help
            show_help = True
        elif opt in ("-u", "--url"): # site url
            sites.append([0, arg])
        elif opt in ("-A", "--addUrl"): # site url
            add_url = arg
        elif opt in ("-D", "--deleteUrl"): # site url
            delete_url = arg
        elif opt in ("-L", "--language"): # language code
            # loop all available languages and verify language exist
            import os 
            availableLanguages = list()
            localeDirs = os.listdir('locales')
            foundLang = False

            for localeName in localeDirs:
                if (localeName[0:1] == '.'):
                    continue

                languageSubDirectory = os.path.join('locales', localeName, "LC_MESSAGES")

                if (os.path.exists(languageSubDirectory)):
                    availableLanguages.append(localeName)

                    if (localeName == arg):
                        langCode = arg
                        foundLang = True

                        language = gettext.translation('webperf-core', localedir='locales', languages=[langCode])
                        language.install()
                        _ = language.gettext

            if (not foundLang):
                # Not translateable
                print('Language not found, only the following languages are available:', availableLanguages)
                sys.exit(2)
        elif opt in ("-t", "--test"): # test type
            try:
                tmp_test_type = int(arg)
                test_type = validate_test_type(tmp_test_type)
                if test_type == -2:
                    sys.exit(2)
            except Exception:
                validate_test_type(arg)
                sys.exit(2)
        elif opt in ("-i", "--input"): # input file path
            input_filename = arg
            file_long_ending = ""
            if (len(input_filename) > 7):
                file_long_ending = input_filename[-7:].lower()

            if file_long_ending == ".sqlite":                
                from engines.sqlite import read_sites, add_site, delete_site
            else:
                from engines.json import read_sites, add_site, delete_site
            sites = read_sites(input_filename)
            pass
        elif opt in ("-o", "--output"): # output file path
            output_filename = arg
            pass
        elif opt in ("-r", "--review", "--report"): # writes reviews directly in terminal
            show_reviews = True
            pass

    if (show_help):
        print(_('TEXT_COMMAND_USAGE'))
        sys.exit(2)

    if (add_url != ''):
        # check if website url should be added
        sites = add_site(input_filename, add_url)
    elif (delete_url != ''):
        # check if website url should be deleted
        sites = delete_site(input_filename, delete_url)
    elif (len(sites)):
        # run test(s) for every website
        siteTests = testing(langCode, sites, test_type=test_type, show_reviews=show_reviews)
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
            write_tests(output_filename, siteTests)
    else:
        print(_('TEXT_COMMAND_USAGE'))


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    main(sys.argv[1:])