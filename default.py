# -*- coding: utf-8 -*-
import sys
import os
import getopt
import gettext
from engines.sqlite import read_sites as sqlite_read_sites,\
    add_site as sqlite_add_site,\
    delete_site as sqlite_delete_site
from engines.csv_engine import read_sites as csv_read_sites,\
    add_site as csv_add_site,\
    delete_site as csv_delete_site
from engines.sitemap import read_sites as sitemap_read_sites
from engines.sitespeed_result import read_sites as sitespeed_read_sites
from engines.webperf import read_sites as webperf_read_sites,\
    add_site as webperf_add_site,\
    delete_site as webperf_delete_site
from engines.json_engine import read_sites as json_read_sites,\
    add_site as json_add_site,\
    delete_site as json_delete_site
from helpers.carbon_rating_helper import update_carbon_percentiles
from helpers.credits_helper import get_credits, update_credits_markdown
from helpers.dependency_helper import dependency
from helpers.release_helper import set_new_release_version_in_env, update_release_version
from helpers.setting_helper import config_mapping, get_config, set_config,\
    set_config_from_cmd, set_runtime_config_only
from helpers.test_helper import TEST_ALL,\
    restart_failures_log, test_sites, validate_test_type, write_test_results
from helpers.translation_helper import validate_translations
from helpers.update_software_helper import filter_unknown_sources,\
    update_licenses, update_software_info, update_user_agent
from tests.utils import clean_cache_files

def show_test_help(global_translation):
    """
    Prints out help text for various test arguments.

    This function uses the provided global translation function to
    print out help text for a variety of test arguments.
    The help text includes information about valid arguments for
    different types of tests such as Google Lighthouse, HTML, CSS,
    Sitespeed, Pa11y, Webbkoll, HTTP, Energy Efficiency,
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
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_PAGE_NOT_FOUND'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_STANDARD_FILES'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_SITESPEED'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_PA11Y'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_WEBBKOLL'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_HTTP'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_ENERGY_EFFICIENCY'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_TRACKING'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_EMAIL'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_SOFTWARE'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_A11Y_STATEMENT'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_CSS_LINT'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_HTML_LINT'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_JS_LINT'))
    print(global_translation('TEXT_TEST_VALID_ARGUMENTS_GOOGLE_LIGHTHOUSE'))
    sys.exit()


class CommandLineOptions: # pylint: disable=too-many-instance-attributes,missing-class-docstring
    test_types = list(TEST_ALL)
    sites = []
    output_filename = ''
    input_filename = ''
    setting_filename = ''
    input_skip = 0
    input_take = -1
    add_url = ''
    delete_url = ''
    language = False

    read_sites = None
    add_site = None
    delete_site = None

    def __init__(self):
        self.language = False

    def update_credits(self, _):
        """
        Updated credits.md and prints out the webperf_core credits and exits the program.

        This function uses the provided language function to print out webperf_core credits.
        After printing the help text, it ends the program.
        """
        update_credits_markdown(self.language)
        sys.exit()

    def update_browser(self, _):
        update_user_agent()
        sys.exit(0)

    def update_carbon_rating(self, argv):
        update_carbon_percentiles(argv)
        sys.exit(0)

    def prepare_release(self, argv):
        update_release_version(argv)
        sys.exit(0)

    def check_dependency(self, _):
        dependency()
        sys.exit(0)

    def create_release(self, argv):
        set_new_release_version_in_env(argv)
        sys.exit(0)

    def find_unknown_sources(self, _):
        filter_unknown_sources()
        sys.exit(0)

    def update_translations(self, _):
        if validate_translations():
            sys.exit(0)
        else:
            sys.exit(2)

    def update_software_definitions(self, arg):
        set_runtime_config_only("github.api.key", arg)
        update_licenses()
        update_software_info()
        sys.exit(0)

    def show_credits(self, _):
        """
        Prints out the webperf_core credits and exits the program.

        This function uses the provided language function to print out webperf_core credits.
        After printing the help text, it ends the program.
        """
        creds = get_credits(self.language)
        print(creds)
        sys.exit()

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

    def show_available_settings(self):
        """
        Display valid settings and their aliases.
        Prints the available settings along with their corresponding aliases.
        """
        print()
        print('Valid settings:')
        for aliases, value in config_mapping.items():
            value_type = value.split('|', maxsplit=1)[0]
            value_desc = 'value'
            if 'bool' in value_type:
                value_desc = 'true/false'
            elif 'int' in value_type:
                value_desc = 'number'
            elif 'string' in value_type:
                value_desc = 'string value'
            print(f"--setting {aliases[1]}=<{value_desc}> ( alias: {aliases[0]} )")
        print()

    def set_setting(self, arg):
        """
        Set configuration settings based on user input.

        Parses the input argument to determine the setting name and value.
        If the input is not in the correct format, it displays available settings.
        Otherwise, it sets the specified configuration value.

        Args:
            arg (str): Input argument in the format "<setting_name>=<value>".
        """
        if not set_config_from_cmd(arg):
            self.show_available_settings()
        else:
            self.load_language(get_config('general.language'))

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

    def save_setting(self, arg):
        """
        Specifies what filename to use when saving currently used settings to file.
        Args:
            arg (str): The setting filename to be used when saving settings.

        Returns:
            None
        """
        self.setting_filename = arg

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

    def enable_mobile(self, _):
        self.set_setting('tests.sitespeed.mobile=true')

    def enable_reviews(self, _):
        """
        Enables the display of reviews for the instance.
        This function sets the `general.review.show` to true,
        enabling the display of reviews.

        Args:
            _ (Any): This argument is not used in the function.

        Returns:
            None
        """
        self.set_setting('general.review.show=true')

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

        add_site = None
        delete_site = None
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
        elif file_long_ending == ".result":
            read_sites = sitespeed_read_sites
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
                    set_config_from_cmd(f"general.language={arg}")
                    found_lang = True

                    self.load_language(arg)

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
            ("--is", "--input-skip"): self.set_input_skip,
            ("-m", "--mobile"): self.enable_mobile,
            ("--it", "--input-take"): self.set_input_take,
            ("-o", "--output"): self.set_output_filename,
            ("-r", "--review", "--report"): self.enable_reviews,
            ("-c", "--credits", "--contributors"): self.show_credits,
            ("--uc", "--update-credits"): self.update_credits,
            ("-b", "--update-browser"): self.update_browser,
            ("-d", "--update-definitions"): self.update_software_definitions,
            ("--ucr", "--update-carbon"): self.update_carbon_rating,
            ("--ut", "--update-translations"): self.update_translations,
            ("--pr", "--prepare-release"): self.prepare_release,
            ("--cr", "--create-release"): self.create_release,
            ("--fus", "--find-unknown-sources"): self.find_unknown_sources,
            ("--dep", "--dependency", "--check-dependency"): self.check_dependency,
            ("-s", "--setting"): self.set_setting,
            ("-ss", "--save-setting"): self.save_setting
        }

        for options, handler in option_handlers.items():
            if opt in options:
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
    -o/--output <file path>\t: output file path (.json/.csv/.sql/.sqlite/.md)
    -A/--addUrl <site url>\t: website url (required in combination with -i/--input)
    -D/--deleteUrl <site url>\t: website url (required in combination with -i/--input)
    -L/--language <lang code>\t: language used for output(en = default/sv)
    -s/--setting <key>=<value>\t: override configuration for current run
                                  (use ? to list available settings)
    --save-setting <file path>\t: file path to configuration
    -c/--credits/--contributors\t: prints out credits
    --uc/--update-credits\t\t: Update credits.md file
    """

    options = CommandLineOptions()
    options.load_language(get_config('general.language'))

    try:
        opts, _ = getopt.getopt(argv, "hu:t:i:o:rA:D:L:s:cbd:m", [
                                   "help", "url=", "test=", "input=", "output=",
                                   "review", "report", "addUrl=", "deleteUrl=",
                                   "language=", "input-skip=", "input-take=",
                                   "mobile",
                                   "credits", "contributors",
                                   "uc" ,"update-credits",
                                   "update-browser", "update-definitions=",
                                   "update-translations",
                                   "pr=", "prepare-release=",
                                   "cr=", "create-release=",
                                   "dep", "dependency", "check-dependency",
                                   "fus", "find-unknown-sources",
                                   "update-carbon=",
                                   "is=", "it=", "setting=", "save-setting="])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if len(opts) == 0:
        options.show_help(_)
        return

    for opt, arg in opts:
        options.handle_option(opt, arg)

    show_help = True
    if options.input_filename != '':
        options.sites = options.read_sites(
            options.input_filename,
            options.input_skip,
            options.input_take)
        show_help = False

    if options.setting_filename != '':
        set_config(options.setting_filename)
        show_help = False

    if options.add_url != '' and options.add_site is not None:
        # check if website url should be added
        options.sites = options.add_site(
            options.input_filename,
            options.add_url,
            options.input_skip,
            options.input_take)
    elif options.delete_url != '' and options.delete_site is not None:
        # check if website url should be deleted
        options.sites = options.delete_site(
            options.input_filename,
            options.delete_url,
            options.input_skip,
            options.input_take)
    elif len(options.sites) > 0:
        restart_failures_log()
        # run test(s) for every website
        test_results = test_sites(options.language,
                                        options.sites,
                                        test_types=options.test_types)

        write_test_results(options.sites, options.output_filename, test_results, options.language)
            # Cleanup exipred cache
        clean_cache_files()
    elif show_help:
        print(options.language('TEXT_COMMAND_USAGE'))

if __name__ == '__main__':
    main(sys.argv[1:])
