# -*- coding: utf-8 -*-
import json
from datetime import datetime
import traceback
from helpers.setting_helper import get_used_configuration
from models import SiteTests
from tests.page_not_found import run_test as run_test_page_not_found
from tests.html_validator_w3c import run_test as run_test_html_validator_w3c
from tests.css_validator_w3c import run_test as run_test_css_validator_w3c
from tests.privacy_webbkollen import run_test as run_test_privacy_webbkollen
from tests.performance_lighthouse import run_test as run_test_performance_lighthouse
from tests.seo_lighthouse import run_test as run_test_seo_lighthouse
from tests.best_practice_lighthouse import run_test as run_test_best_practice_lighthouse
from tests.standard_files import run_test as run_test_standard_files
from tests.a11y_lighthouse import run_test as run_test_a11y_lighthouse
from tests.performance_sitespeed_io import run_test as run_test_performance_sitespeed_io
from tests.frontend_quality_yellow_lab_tools import \
     run_test as run_test_frontend_quality_yellow_lab_tools
from tests.a11y_pa11y import run_test as run_test_a11y_pa11y
from tests.http_validator import run_test as run_test_http_validator
from tests.energy_efficiency import run_test as run_test_energy_efficiency
from tests.tracking_validator import run_test as run_test_tracking_validator
from tests.email_validator import run_test as run_test_email_validator
from tests.software import run_test as run_test_software
from tests.a11y_statement import run_test as run_test_a11y_statement


TEST_ALL = (TEST_UNKNOWN_01,
            TEST_GOOGLE_LIGHTHOUSE, TEST_PAGE_NOT_FOUND,
            TEST_UNKNOWN_03,
            TEST_GOOGLE_LIGHTHOUSE_SEO, TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE, TEST_HTML, TEST_CSS,
            TEST_DEPRECATED, TEST_STANDARD_FILES, TEST_GOOGLE_LIGHTHOUSE_A11Y,
            TEST_UNKNOWN_11, TEST_UNKNOWN_12, TEST_UNKNOWN_13, TEST_UNKNOWN_14,
            TEST_SITESPEED,
            TEST_UNKNOWN_16,
            TEST_YELLOW_LAB_TOOLS, TEST_PA11Y,
            TEST_UNKNOWN_19,
            TEST_WEBBKOLL, TEST_HTTP, TEST_ENERGY_EFFICIENCY, TEST_TRACKING,
            TEST_EMAIL, TEST_SOFTWARE, TEST_A11Y_STATEMENT) = range(27)

TEST_FUNCS = {
        TEST_PAGE_NOT_FOUND: run_test_page_not_found,
        TEST_HTML: run_test_html_validator_w3c,
        TEST_CSS: run_test_css_validator_w3c,
        TEST_WEBBKOLL: run_test_privacy_webbkollen,
        TEST_GOOGLE_LIGHTHOUSE: run_test_performance_lighthouse,
        TEST_GOOGLE_LIGHTHOUSE_SEO: run_test_seo_lighthouse,
        TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE: run_test_best_practice_lighthouse,
        TEST_STANDARD_FILES:run_test_standard_files,
        TEST_GOOGLE_LIGHTHOUSE_A11Y: run_test_a11y_lighthouse,
        TEST_SITESPEED: run_test_performance_sitespeed_io,
        TEST_YELLOW_LAB_TOOLS: run_test_frontend_quality_yellow_lab_tools,
        TEST_PA11Y: run_test_a11y_pa11y,
        TEST_HTTP: run_test_http_validator,
        TEST_ENERGY_EFFICIENCY: run_test_energy_efficiency,
        TEST_TRACKING: run_test_tracking_validator,
        TEST_EMAIL: run_test_email_validator,
        TEST_SOFTWARE: run_test_software,
        TEST_A11Y_STATEMENT: run_test_a11y_statement
    }

CONFIG_WARNINGS = {}

def test(global_translation, lang_code, site, test_type=None, show_reviews=False):
    """
    This function runs a specific test on a website and returns the test results.

    Parameters:
    global_translation : GNUTranslations
        An object that handles the translation of text in the context of internationalization.
    lang_code : str
        The language code for the website to be tested.
    site : tuple
        A tuple containing the site ID and the website URL.
    test_type : str, optional
        The type of test to be run. If the test type is not in the predefined test functions,
        the function will return an empty list.
    show_reviews : bool, optional
        A flag indicating whether to print the reviews of the website. The default is False.

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

        run_test = TEST_FUNCS[test_type]
        the_test_result = run_test(global_translation, lang_code, site[1])

        if the_test_result is not None:
            rating = the_test_result[0]
            reviews = rating.get_reviews()
            print(global_translation('TEXT_SITE_RATING'), rating)
            if show_reviews:
                print(global_translation('TEXT_SITE_REVIEW'),
                      reviews)

            json_data = ''
            try:
                json_data = the_test_result[1]
                json_data = json.dumps(json_data)
            except json.decoder.JSONDecodeError:
                json_data = ''
            except TypeError:
                json_data = ''
            except RecursionError:
                json_data = ''

            jsondata = str(json_data).encode('utf-8')  # --//--

            site_test = SiteTests(site_id=site[0], type_of_test=test_type,
                                  rating=rating,
                                  test_date=datetime.now(),
                                  json_check_data=jsondata).todata()

            return site_test
    except Exception as ex: # pylint: disable=broad-exception-caught
        print(global_translation('TEXT_TEST_END').format(
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        info = get_error_info(site[1], lang_code, test_type, show_reviews, ex)
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

def get_error_info(url, lang_code, test_type, show_reviews, ex):
    """
    Generate error information for diagnostic purposes.

    Constructs a detailed report containing relevant information such as
    date and time, URL, language code, test type, configuration settings,
    and traceback information.

    Args:
        url (str): The URL associated with the error.
        lang_code (str): The language code.
        test_type (str): The type of test being performed.
        show_reviews (bool): Whether to display reviews.
        ex (Exception): The exception object.

    Returns:
        list: A list of strings containing the error information.
    """
    result = []
    result.append('###############################################')
    result.extend(get_versions())
    result.extend(['###############################################',
        '\n# Information:',
        f"\nDateTime: { \
            datetime.now().strftime('%Y-%m-%d %H:%M:%S') \
        }",
        f'\nUrl: {url}',
        f'\nLanguage Code: {lang_code}',
        f'\nTest Type(s): {test_type}',
        f'\nShow Reviews: {show_reviews}',
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

def get_version():
    """
    Retrieve the version information from the 'package.json' file.

    Reads the 'package.json' file and extracts the version information.
    If the version is found, it returns the version string; otherwise,
    it returns a placeholder '?'.

    Returns:
        str: The version string or '?' if not found.
    """
    with open('package.json', encoding='utf-8') as json_input_file:
        package_info = json.load(json_input_file)
        if 'version' in package_info:
            return package_info['version']
    return '?'


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

def test_site(global_translation, lang_code, site, test_types=TEST_ALL, show_reviews=False):
    """
    This function runs a series of tests on a website and returns a list of all the test results.

    Parameters:
    global_translation : GNUTranslations
        An object that handles the translation of text in the context of internationalization.
    lang_code : str
        The language code for the website to be tested.
    site : tuple
        A tuple containing the site ID and the website URL.
    test_types : list, optional
        A list of test types to be run. If not provided, all tests will be run.
    show_reviews : bool, optional
        A flag indicating whether to print the reviews of the website. The default is False.

    Returns:
    list
        A list containing the results of all the tests run on the website.
    """
    tests = []

    for test_id in TEST_ALL:
        if test_id in test_types:
            tests.extend(test(global_translation,
                            lang_code,
                            site,
                            test_type=test_id,
                            show_reviews=show_reviews))

    return tests


def test_sites(global_translation, lang_code, sites, test_types=TEST_ALL, show_reviews=False):
    """
    This function runs a series of tests on multiple websites and
    returns a list of all the test results.

    Parameters:
    global_translation : GNUTranslations
        An object that handles the translation of text in the context of internationalization.
    lang_code : str
        The language code for the websites to be tested.
    sites : list
        A list of tuples, each containing the site ID and the website URL.
    test_types : list, optional
        A list of test types to be run. If not provided, all tests will be run.
    show_reviews : bool, optional
        A flag indicating whether to print the reviews of the websites. The default is False.

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
        results.extend(test_site(global_translation, lang_code, site,
                                 test_types, show_reviews))

        site_index += 1

    return results
