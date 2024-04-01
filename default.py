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
from utils import TEST_FUNCS, TEST_ALL, test_sites


def validate_test_type(tmp_test_types):
    """
    Validates the given test types against a list of valid tests.

    This function iterates over the input list of test types,
    checks each test type against a list of valid tests,
    and appends the valid ones to a new list.
    The new list of valid test types is then returned.

    Parameters:
    tmp_test_types (list): A list of test types to be validated.

    Returns:
    list: A list of valid test types.

    Example:
    >>> validate_test_type([6, 11, 21])
    [6, 21]
    """
    test_types = []

    valid_tests = TEST_FUNCS.keys()
    for test_type in tmp_test_types:
        if test_type in valid_tests:
            test_types.append(test_type)

    return test_types

def write_test_results(sites, output_filename, test_results):
    """
    Writes the test results to a file.

    This function takes in a list of sites, an output filename,
    and a list of test results. It determines the file type
    based on the file extension of the output filename and writes the test results to
    the file in the appropriate format.

    Parameters:
    sites (list): A list of sites for which the tests were run.
    output_filename (str): The name of the output file.
    test_results (list): A list of test results.

    Returns:
    None
    """
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
    """
    Prints out help text for various test arguments.

    This function uses the provided global translation function to
    print out help text for a variety of test arguments.
    The help text includes information about valid arguments for
    different types of tests such as Google Lighthouse, HTML, CSS,
    Sitespeed, Yellow Lab Tools, Pa11y, Webbkoll, HTTP, Energy Efficiency,
    Tracking, Email, Software, and A11Y Statement.

    Args:
        global_translation (function): A function that takes a string identifier and
        returns the corresponding translated string.

    Returns:
        None

    Raises:
        SystemExit: This function always ends the program after printing the help text.
    """
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


class CommandLineOptions: # pylint: disable=too-many-instance-attributes,missing-class-docstring
    test_types = list(TEST_ALL)
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

    read_sites = None
    add_site = None
    delete_site = None

    def __init__(self):
        self.lang_code = 'en'

    def show_help(self, _):
        """
        Prints out the command usage help text and exits the program.

        This function uses the provided language function to print out help text for command usage.
        After printing the help text, it ends the program.
        """
        print(self.language('TEXT_COMMAND_USAGE'))
        sys.exit()

    def load_language(self, lang_code):
        """
        Load the specified language for translation.

        Parameters:
        lang_code (str): The language code for the desired language.

        Returns:
        function: The translation function for the specified language.
        """
        trans = gettext.translation(
            'webperf-core', localedir='locales', languages=[lang_code])
        trans.install()
        self.language = trans.gettext
        return self.language

    def use_url(self, arg):
        """
        Uses supplied url in test(s)
        """
        self.sites.append([0, arg])

    def add_site_url(self, arg):
        """
        Adds the url to stored sites
        """
        self.add_url = arg

    def delete_site_url(self, arg):
        """
        Deletes the url from stored sites
        """
        self.delete_url = arg

    def set_input_skip(self, arg):
        """
        Sets the input skip for the instance.
        This function attempts to parse the provided argument as an integer and
        assigns it as the input skip for the instance.
        If the argument cannot be parsed into an integer,
        the function prints a usage message and exits the program.

        Args:
            arg (str): The desired input skip as a string.

        Raises:
            TypeError: If the argument cannot be parsed into an integer.

        Returns:
            None
        """
        try:
            self.input_skip = int(arg)
        except TypeError:
            print(self.language('TEXT_COMMAND_USAGE'))
            sys.exit(2)

    def set_input_take(self, arg):
        """
        Sets the input take for the instance.
        This function attempts to parse the provided argument as an integer and
        assigns it as the input take for the instance.
        If the argument cannot be parsed into an integer,
        the function prints a usage message and exits the program.

        Args:
            arg (str): The desired input take as a string.

        Raises:
            TypeError: If the argument cannot be parsed into an integer.

        Returns:
            None
        """
        try:
            self.input_take = int(arg)
        except TypeError:
            print(self.language('TEXT_COMMAND_USAGE'))
            sys.exit(2)

    def set_output_filename(self, arg):
        """
        Sets the output filename for the instance.
        This function assigns the provided argument as the output filename for the instance.

        Args:
            arg (str): The desired output filename.

        Returns:
            None
        """
        self.output_filename = arg

    def set_test_types(self, arg):
        """
        Sets the test types for the instance based on the provided argument.

        The function attempts to parse the argument as a comma-separated string of integers. 
        These integers are then validated as test types. If the parsing or validation fails, 
        the test types for the instance are set to an empty list. If no valid test types are 
        provided, the function displays a help message for tests.

        Args:
            arg (str): A comma-separated string of integers representing test types.

        Returns:
            None
        """
        try:
            tmp_test_types = list(map(int, arg.split(',')))
            self.test_types = validate_test_type(tmp_test_types)
        except (TypeError, ValueError):
            self.test_types = []

        if len(self.test_types) == 0:
            show_test_help(self.language)
            return

    def enable_reviews(self, _):
        """
        Enables the display of reviews for the instance.
        This function sets the `show_reviews` attribute of the instance to True,
        enabling the display of reviews.

        Args:
            _ (Any): This argument is not used in the function.

        Returns:
            None
        """
        self.show_reviews = True

    def set_input_handlers(self, input_filename):
        """
        Sets the appropriate input handlers based on the file type of the input file.

        This function checks the file extension of the input file and
        sets the appropriate functions to read sites, add a site, and delete a site.
        The supported file types are SQLite, CSV, XML, Result, Webprf, and JSON.
        If the file type is not recognized, it defaults to JSON.

        Args:
            input_filename (str): The name of the input file.

        Returns:
            None
        """

        self.input_filename = input_filename
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
        self.read_sites = read_sites
        self.add_site = add_site
        self.delete_site = delete_site


    def try_load_language(self, arg):
        """
        Attempts to load the specified language for translation.

        This function checks if the specified language is available in the 'locales' directory.
        If it is, it sets the language code and loads the language.
        If the specified language is not available,
        it prints out a message listing the available languages and exits the program.

        Args:
            arg (str): The language code for the desired language.

        Returns:
            None

        Raises:
            SystemExit: This function ends the program if the specified language is not available.
        """
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
                    self.lang_code = arg
                    found_lang = True

                    self.load_language(self.lang_code)

        if not found_lang:
                    # Not translateable
            print(
                        'Language not found, only the following languages are available:',
                        available_languages)
            sys.exit(2)

    def handle_option(self, opt, arg):
        """
        Handles the provided option by calling the appropriate handler function.

        This function uses a dictionary to map options to their corresponding handler functions.
        It checks if the provided option matches any of the keys in the dictionary.
        If a match is found, it calls the corresponding handler function with the provided argument.

        Args:
            opt (str): The option to handle.
            arg (str): The argument to pass to the handler function.

        Returns:
            None
        """
        option_handlers = {
            ("-h", "--help"): self.show_help,
            ("-u", "--url"): self.use_url,
            ("-A", "--addUrl"): self.add_site_url,
            ("-D", "--deleteUrl"): self.delete_site_url,
            ("-L", "--language"): self.try_load_language,
            ("-t", "--test"): self.set_test_types,
            ("-i", "--input"): self.set_input_handlers,
            ("--input-skip"): self.set_input_skip,
            ("--input-take"): self.set_input_take,
            ("-o", "--output"): self.set_output_filename,
            ("-r", "--review", "--report"): self.enable_reviews,
        }

        for option, handler in option_handlers.items():
            if opt in option:
                handler(arg)
                return


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

    options = CommandLineOptions()
    options.load_language(options.lang_code)

    try:
        opts, _ = getopt.getopt(argv, "hu:t:i:o:rA:D:L:", [
                                   "help", "url=", "test=", "input=", "output=",
                                   "review", "report", "addUrl=", "deleteUrl=",
                                   "language=", "input-skip=", "input-take="])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if len(opts) == 0:
        options.show_help(_)
        return

    for opt, arg in opts:
        options.handle_option(opt, arg)

    if options.input_filename != '':
        options.sites = options.read_sites(
            options.input_filename,
            options.input_skip,
            options.input_take)

    if options.add_url != '':
        # check if website url should be added
        options.sites = options.add_site(
            options.input_filename,
            options.add_url,
            options.input_skip,
            options.input_take)
    elif options.delete_url != '':
        # check if website url should be deleted
        options.sites = options.delete_site(
            options.input_filename,
            options.delete_url,
            options.input_skip,
            options.input_take)
    elif len(options.sites) > 0:
        # run test(s) for every website
        test_results = test_sites(options.language,
                                        options.lang_code,
                                        options.sites,
                                        test_types=options.test_types,
                                        show_reviews=options.show_reviews)

        write_test_results(options.sites, options.output_filename, test_results)
            # Cleanup exipred cache
        clean_cache_files()
    else:
        print(options.language('TEXT_COMMAND_USAGE'))



if __name__ == '__main__':
    main(sys.argv[1:])
