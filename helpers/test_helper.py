# -*- coding: utf-8 -*-
import json
from datetime import datetime
import os
import traceback
from helpers.models import Rating
from helpers.setting_helper import get_config, get_used_configuration
from helpers.models import SiteTests
from tests.utils import get_translation, merge_dicts,\
    sort_testresult_issues, calculate_rating
from tests.sitespeed_base import create_webperf_json
from tests.privacy_webbkollen import run_test as run_test_privacy_webbkollen
from tests.standard_files import run_test as run_test_standard_files
from tests.performance_sitespeed_io import run_test as run_test_performance_sitespeed_io
from tests.a11y_pa11y import run_test as run_test_a11y_pa11y
from tests.http_validator import run_test as run_test_http_validator
from tests.energy_efficiency import run_test as run_test_energy_efficiency
from tests.tracking_validator import run_test as run_test_tracking_validator
from tests.email_validator import run_test as run_test_email_validator
from tests.software import run_test as run_test_software
from engines.json_engine import write_tests as json_write_tests
from engines.gov import write_tests as gov_write_tests
from engines.sql import write_tests as sql_write_tests
from engines.markdown_engine import write_tests as markdown_write_tests

def run_dummy_test(global_translation, url):
    return []

TEST_ALL = (TEST_UNKNOWN_00,
            TEST_DEPRECATED, TEST_PAGE_NOT_FOUND,
            TEST_UNKNOWN_03,
            TEST_DEPRECATED, TEST_DEPRECATED,
            TEST_DEPRECATED, TEST_DEPRECATED,
            TEST_DEPRECATED, TEST_STANDARD_FILES, TEST_DEPRECATED,
            TEST_UNKNOWN_11, TEST_UNKNOWN_12, TEST_UNKNOWN_13, TEST_UNKNOWN_14,
            TEST_SITESPEED,
            TEST_UNKNOWN_16,
            TEST_DEPRECATED, TEST_PA11Y,
            TEST_UNKNOWN_19,
            TEST_WEBBKOLL, TEST_HTTP, TEST_ENERGY_EFFICIENCY, TEST_TRACKING,
            TEST_EMAIL, TEST_SOFTWARE, TEST_A11Y_STATEMENT,
            TEST_LINT_CSS, TEST_LINT_HTML, TEST_LINT_JS,
            TEST_GOOGLE_LIGHTHOUSE
            ) = range(31)

TEST_ALL_FUNCS = {
        TEST_PAGE_NOT_FOUND: run_dummy_test,
        TEST_WEBBKOLL: run_test_privacy_webbkollen,
        TEST_STANDARD_FILES:run_test_standard_files,
        TEST_SITESPEED: run_test_performance_sitespeed_io,
        TEST_PA11Y: run_test_a11y_pa11y,
        TEST_HTTP: run_test_http_validator,
        TEST_ENERGY_EFFICIENCY: run_test_energy_efficiency,
        TEST_TRACKING: run_test_tracking_validator,
        TEST_EMAIL: run_test_email_validator,
        TEST_SOFTWARE: run_test_software,
        TEST_A11Y_STATEMENT: run_dummy_test,
        TEST_LINT_CSS: run_dummy_test,
        TEST_LINT_HTML: run_dummy_test,
        TEST_LINT_JS: run_dummy_test,
        TEST_GOOGLE_LIGHTHOUSE: run_dummy_test
    }


TEST_FUNCS = {
        TEST_WEBBKOLL: run_test_privacy_webbkollen,
        TEST_STANDARD_FILES:run_test_standard_files,
        TEST_SITESPEED: run_test_performance_sitespeed_io,
        TEST_PA11Y: run_test_a11y_pa11y,
        TEST_HTTP: run_test_http_validator,
        TEST_ENERGY_EFFICIENCY: run_test_energy_efficiency,
        TEST_TRACKING: run_test_tracking_validator,
        TEST_EMAIL: run_test_email_validator,
        TEST_SOFTWARE: run_test_software
    }

TEST_USE_SITESPEED = {
        TEST_PAGE_NOT_FOUND: 'plugin-pagenotfound',
        TEST_A11Y_STATEMENT: 'plugin-accessibility-statement',
        TEST_LINT_CSS: 'plugin-css',
        TEST_LINT_HTML: 'plugin-html',
        TEST_LINT_JS: 'plugin-javascript',
        TEST_GOOGLE_LIGHTHOUSE: '@sitespeed.io/plugin-lighthouse'
    }

TEST_USE_SITESPEED_TOMORROW = {
        TEST_STANDARD_FILES:run_test_standard_files,
        TEST_SITESPEED: run_test_performance_sitespeed_io,
        TEST_HTTP: run_test_http_validator,
        TEST_ENERGY_EFFICIENCY: run_test_energy_efficiency,
        TEST_TRACKING: run_test_tracking_validator,
        TEST_SOFTWARE: run_test_software
    }


CONFIG_WARNINGS = {}

def test(global_translation, site, test_type=None):
    """
    This function runs a specific test on a website and returns the test results.

    Parameters:
    global_translation : GNUTranslations
        An object that handles the translation of text in the context of internationalization.
    site : tuple
        A tuple containing the site ID and the website URL.
    test_type : str, optional
        The type of test to be run. If the test type is not in the predefined test functions,
        the function will return an empty list.

    Returns:
    list
        A list containing the test results. If an exception occurs during the test,
        the function will log the exception and return None.

    Raises:
    Exception
        If an exception occurs during the test, it will be caught and logged.
    """

    try:
        if test_type not in TEST_FUNCS:
            return []

        print(global_translation('TEXT_TEST_START').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        run_test = TEST_FUNCS[test_type]
        the_test_result = run_test(global_translation, site[1])

        print(global_translation('TEXT_TEST_END').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        if the_test_result is not None:
            rating = the_test_result[0]

            json_data = the_test_result[1]

            site_test = SiteTests(site_id=site[0], type_of_test=test_type,
                                  rating=rating,
                                  test_date=datetime.now(),
                                  json_check_data=json_data).todata()

            return site_test
    except Exception as ex: # pylint: disable=broad-exception-caught
        print(global_translation('TEXT_TEST_END').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        info = get_error_info(site[1], test_type, ex)
        print('\n'.join(info).replace('\n\n','\n'))

        # write error to failure.log file
        with open('failures.log', 'a', encoding='utf-8') as outfile:
            outfile.writelines(info)

    return []

def restart_failures_log():
    """
    Restart failures log by removing all content in it,
    this is so we always start fresh.
    """
    with open('failures.log', 'w', encoding='utf-8') as outfile:
        outfile.writelines('')

def get_error_info(url, test_type, ex):
    """
    Generate error information for diagnostic purposes.

    Constructs a detailed report containing relevant information such as
    date and time, URL, language code, test type, configuration settings,
    and traceback information.

    Args:
        url (str): The URL associated with the error.
        test_type (str): The type of test being performed.
        ex (Exception): The exception object.

    Returns:
        list: A list of strings containing the error information.
    """
    result = []
    result.append('###############################################')
    result.extend(get_versions())
    result.extend(['###############################################',
        '\n# Information:',
        f"\nDateTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f'\nUrl: {url}',
        f'\nTest Type(s): {test_type}',
        '\n###############################################'
        '\n# Used Configuration:'
    ])
    config = get_used_configuration()
    for name, value in config.items():
        result.append(f"\n{name}: {value}")

    result.append('\n###############################################\n')
    result.extend(traceback.format_exception(ex, ex, ex.__traceback__))
    result.append('###############################################\n\n')
    return result

def get_versions():
    """
    Retrieve version information from the 'package.json' file.

    Reads the 'package.json' file and extracts the package version and
    dependency information. It constructs a list of strings containing
    the version and dependency details.

    Returns:
        list: A list of strings with version and dependency information.
    """
    result = ['\n# Version information (from packages.json)']
    with open('package.json', encoding='utf-8') as json_input_file:
        package_info = json.load(json_input_file)

        if 'version' in package_info:
            result.append(f"\nVersion: {package_info['version']}")

        if 'dependencies' in package_info:
            result.append("\nDependencies:")
            for dependency_name, dependency_version in package_info['dependencies'].items():
                result.append(f"\n- {dependency_name} v{dependency_version}")
            result.append("\n")
    return result

def test_with_sitespeed(global_translation, site, sitespeed_plugins):
    try:
        rating = Rating(global_translation)
        result_dict = {}

        print(global_translation('TEXT_TEST_START').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        result_dict = create_webperf_json(site[1], sitespeed_plugins)
        # TODO: Handle where result_dict is None
        # TODO: Handle when unable to access website

        calculate_rating(global_translation, rating, result_dict)

        print(global_translation('TEXT_TEST_END').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        if result_dict is not None:
            reviews = rating.get_reviews()

            json_data = result_dict

            site_test = SiteTests(site_id=site[0], type_of_test=-1,
                                  rating=rating,
                                  test_date=datetime.now(),
                                  json_check_data=json_data).todata()

            return site_test
    except Exception as ex: # pylint: disable=broad-exception-caught
        print(global_translation('TEXT_TEST_END').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        info = get_error_info(site[1], -1, ex)
        print('\n'.join(info).replace('\n\n','\n'))

        # write error to failure.log file
        with open('failures.log', 'a', encoding='utf-8') as outfile:
            outfile.writelines(info)

    return []


def test_site(global_translation, site, test_types):
    """
    This function runs a series of tests on a website and returns a list of all the test results.

    Parameters:
    global_translation : GNUTranslations
        An object that handles the translation of text in the context of internationalization.
    site : tuple
        A tuple containing the site ID and the website URL.
    test_types : list
        A list of test types to be run. If not provided, all tests will be run.

    Returns:
    list
        A list containing the results of all the tests run on the website.
    """
    tests = []

    site_id = site[0]
    sitespeed_plugins = ''
    other_tests = []
    for test_id in TEST_ALL_FUNCS:
        if test_id not in test_types:
            continue
        
        if test_id in TEST_USE_SITESPEED.keys():
            sitespeed_plugins += f'--plugins.add {TEST_USE_SITESPEED[test_id]} '
        else:
            other_tests.append(test_id)

    if len(sitespeed_plugins) > 0:
        sitespeed_plugins += '--plugins.add plugin-webperf-core '
        tests.extend(test_with_sitespeed(global_translation,
            site,
            sitespeed_plugins))

    for test_id in other_tests:
        tests.extend(test(global_translation,
            site,
            test_type=test_id))

    rating = Rating(global_translation)
    site_test = None
    big_data = {}
    for test_data in tests:
        if test_data is None:
            continue
        if "data" not in test_data:
            continue

        if "groups" not in test_data["data"]:
            abc = 1
        big_data = merge_dicts(big_data, test_data['data'], False, False)

    sort_testresult_issues(big_data)
    rating = calculate_rating(global_translation, rating, big_data)

    if rating.isused():
        reviews = rating.get_reviews()
        print(global_translation('TEXT_SITE_RATING'), rating)
        if get_config('general.review.show'):
            print(
                global_translation('TEXT_SITE_REVIEW'),
                reviews)

        if get_config('general.review.data'):
            nice_json_data = json.dumps(big_data, indent=3)
            print(
                global_translation('TEXT_SITE_REVIEW_DATA'),
                f'```json\r\n{nice_json_data}\r\n```')


        site_test = SiteTests(
            site_id,
            type_of_test=-1,
            rating=rating,
            test_date=datetime.now(),
            json_check_data=big_data).todata()

        tests = []
        tests.append(site_test[0])

    return tests


def test_sites(global_translation, sites, test_types):
    """
    This function runs a series of tests on multiple websites and
    returns a list of all the test results.

    Parameters:
    global_translation : GNUTranslations
        An object that handles the translation of text in the context of internationalization.
    sites : list
        A list of tuples, each containing the site ID and the website URL.
    test_types : list
        A list of test types to be run. If not provided, all tests will be run.

    Returns:
    list
        A list containing the results of all the tests run on the websites.
    """
    results = []

    print(global_translation('TEXT_TEST_START_HEADER'))

    nof_sites = len(sites)
    has_more_then_one_site = nof_sites > 1

    if has_more_then_one_site:
        print(global_translation('TEXT_TESTING_NUMBER_OF_SITES').format(nof_sites))

    site_index = 0
    for site in sites:
        if site_index > 0:
            print(global_translation('TEXT_TEST_START_HEADER'))
        website = site[1]
        print(global_translation('TEXT_TESTING_SITE').format(website))
        if has_more_then_one_site:
            print(global_translation('TEXT_WEBSITE_X_OF_Y').format(site_index + 1, nof_sites))
        results.extend(test_site(global_translation, site,
                                 test_types))

        site_index += 1

    return results

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

    remove_tests = []
    valid_tests = TEST_ALL_FUNCS.keys()
    for test_type in tmp_test_types:
        if test_type in valid_tests:
            test_types.append(test_type)
            continue
        if test_type < 0:
            test_type = abs(test_type)
            remove_tests.append(test_type)

    if len(tmp_test_types) == 0:
        test_types = list(valid_tests)

    for test_type in remove_tests:
        if test_type in valid_tests:
            test_types.remove(test_type)

    return test_types

def write_test_results(sites, output_filename, test_results, global_translation):
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
    global_translation : GNUTranslations
        An object that handles the translation of text in the context of internationalization.

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
        elif file_long_ending.endswith(".md"):
            write_tests = markdown_write_tests
        else:
            write_tests = json_write_tests

        ensure_parent_path(output_filename)

            # use loaded engine to write tests
        write_tests(output_filename, test_results, sites, global_translation)

def ensure_parent_path(output_filename):
    """
    Ensures that the parent directory of the output file exists.
    This function takes an output filename and
    ensures that the directory structure up to the file exists.
    It handles both relative and absolute paths.
    Parameters:
        output_filename (str): The name of the output file.
    Returns: None
    """

    # Get the absolute path of the output file
    abs_path = os.path.abspath(output_filename)
    # Get the parent directory of the output file
    parent_dir = os.path.dirname(abs_path)
    # Create the parent directory if it doesn't exist
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
