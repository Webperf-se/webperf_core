# -*- coding: utf-8 -*-
import json
import datetime
import traceback
from models import SiteTests
import config
from tests.page_not_found import run_test as run_test_page_not_found
from tests.html_validator_w3c import run_test as run_test_html_validator_w3c
from tests.css_validator_w3c import run_test as run_test_css_validator_w3c
from tests.privacy_webbkollen import run_test as run_test_privacy_webbkollen
from tests.performance_lighthouse import run_test as run_test_performance_lighthouse
from tests.seo_lighthouse import run_test as run_test_seo_lighthouse
from tests.best_practice_lighthouse import run_test as run_test_best_practice_lighthouse
from tests.pwa_lighthouse import run_test as run_test_pwa_lighthouse
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
            TEST_GOOGLE_LIGHTHOUSE_PWA, TEST_STANDARD_FILES, TEST_GOOGLE_LIGHTHOUSE_A11Y,
            TEST_UNKNOWN_11, TEST_UNKNOWN_12, TEST_UNKNOWN_13, TEST_UNKNOWN_14,
            TEST_SITESPEED,
            TEST_UNKNOWN_16,
            TEST_YELLOW_LAB_TOOLS, TEST_PA11Y,
            TEST_UNKNOWN_19,
            TEST_WEBBKOLL, TEST_HTTP, TEST_ENERGY_EFFICIENCY, TEST_TRACKING,
            TEST_EMAIL, TEST_SOFTWARE, TEST_A11Y_STATEMENT) = range(27)


def test(_, lang_code, site, test_type=None, show_reviews=False):
    """
    Executing the actual tests.
    Attributes:
    * test_type=num|None to execute all available tests
    """

    site_id = site[0]
    website = site[1]

    try:
        the_test_result = None
        if test_type == TEST_PAGE_NOT_FOUND:
            the_test_result = run_test_page_not_found(_, lang_code, website)
        elif test_type == TEST_HTML:
            the_test_result = run_test_html_validator_w3c(_, lang_code, website)
        elif test_type == TEST_CSS:
            the_test_result = run_test_css_validator_w3c(_, lang_code, website)
        elif test_type == TEST_WEBBKOLL:
            the_test_result = run_test_privacy_webbkollen(_, lang_code, website)
        elif test_type == TEST_GOOGLE_LIGHTHOUSE:
            the_test_result = run_test_performance_lighthouse(_, lang_code, website)
        elif test_type == TEST_GOOGLE_LIGHTHOUSE_SEO:
            the_test_result = run_test_seo_lighthouse(_, lang_code, website)
        elif test_type == TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE:
            the_test_result = run_test_best_practice_lighthouse(_, lang_code, website)
        elif test_type == TEST_GOOGLE_LIGHTHOUSE_PWA:
            the_test_result = run_test_pwa_lighthouse(_, lang_code, website)
        elif test_type == TEST_STANDARD_FILES:
            the_test_result = run_test_standard_files(_, lang_code, website)
        elif test_type == TEST_GOOGLE_LIGHTHOUSE_A11Y:
            the_test_result = run_test_a11y_lighthouse(_, lang_code, website)
        elif test_type == TEST_SITESPEED:
            the_test_result = run_test_performance_sitespeed_io(_, lang_code, website)
        elif test_type == TEST_YELLOW_LAB_TOOLS:
            the_test_result = run_test_frontend_quality_yellow_lab_tools(_, lang_code, website)
        elif test_type == TEST_PA11Y:
            the_test_result = run_test_a11y_pa11y(_, lang_code, website)
        elif test_type == TEST_HTTP:
            the_test_result = run_test_http_validator(_, lang_code, website)
        elif test_type == TEST_ENERGY_EFFICIENCY:
            the_test_result = run_test_energy_efficiency(_, lang_code, website)
        elif test_type == TEST_TRACKING:
            the_test_result = run_test_tracking_validator(_, lang_code, website)
        elif test_type == TEST_EMAIL:
            the_test_result = run_test_email_validator(_, lang_code, website)
        elif test_type == TEST_SOFTWARE:
            the_test_result = run_test_software(_, lang_code, website)
        elif test_type == TEST_A11Y_STATEMENT:
            the_test_result = run_test_a11y_statement(_, lang_code, website)

        if the_test_result is not None:
            rating = the_test_result[0]
            reviews = rating.get_reviews()
            print(_('TEXT_SITE_RATING'), rating)
            if show_reviews:
                print(_('TEXT_SITE_REVIEW'),
                      reviews)

            json_data = ''
            try:
                json_data = the_test_result[1]
                json_data = json.dumps(json_data)
            except:
                json_data = ''

            jsondata = str(json_data).encode('utf-8')  # --//--

            site_test = SiteTests(site_id=site_id, type_of_test=test_type,
                                  rating=rating,
                                  test_date=datetime.datetime.now(),
                                  json_check_data=jsondata).todata()

            return site_test
    except Exception as e:
        print(_('TEXT_TEST_END').format(
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        print(_('TEXT_EXCEPTION'), website, '\n', e)

        date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # write error to failure.log file
        with open('failures.log', 'a', encoding='utf-8') as outfile:
            outfile.writelines(['###############################################',
                                '\n# Information:',
                                f'\nDateTime: {date}',
                                f'\nUrl: {website}',
                                f'\nLanguage Code: {lang_code}',
                                f'\nTest Type(s): {test_type}',
                                f'\nShow Reviews: {show_reviews}',
                                 '\n###############################################'
                                '\n# Configuration (from config.py):',
                                f'\nuseragent: {config.useragent}',
                                f'\nhttp_request_timeout: {config.http_request_timeout}',
                                f'\nwebbkoll_sleep: {config.webbkoll_sleep}',
                                f'\ncss_review_group_errors: {config.css_review_group_errors}',
                                f'\nreview_show_improvements_only: {
                                    config.review_show_improvements_only}',
                                f'\nylt_use_api: {config.ylt_use_api}',
                                f'\nlighthouse_use_api: {config.lighthouse_use_api}',
                                f'\nsitespeed_use_docker: {config.sitespeed_use_docker}',
                                f'\nsitespeed_iterations: {config.sitespeed_iterations}',
                                f'\nlocales: {config.locales}',
                                f'\ncache_when_possible: {config.cache_when_possible}',
                                f'\ncache_time_delta: {config.cache_time_delta}',
                                f'\nsoftware_use_stealth: {config.software_use_stealth}',
                                f'\nuse_detailed_report: {config.use_detailed_report}',
                                f'\nsoftware_browser: {config.software_browser}',
                                 '\n###############################################\n'
                                 ])


            outfile.writelines(traceback.format_exception(e,e, e.__traceback__))

            outfile.writelines(['###############################################\n\n'])

    return []


def test_site(_, lang_code, site, test_types=TEST_ALL, show_reviews=False):
    tests = []
    ##############
    if TEST_GOOGLE_LIGHTHOUSE in test_types:
        tests.extend(test(_,
                          lang_code,
                          site,
                          test_type=TEST_GOOGLE_LIGHTHOUSE,
                          show_reviews=show_reviews))
    if TEST_PAGE_NOT_FOUND in test_types:
        tests.extend(test(_, lang_code, site,
                          test_type=TEST_PAGE_NOT_FOUND,
                          show_reviews=show_reviews))
    if TEST_GOOGLE_LIGHTHOUSE_SEO in test_types:
        tests.extend(test(_,
                          lang_code,
                          site,
                          test_type=TEST_GOOGLE_LIGHTHOUSE_SEO,
                          show_reviews=show_reviews))
    if TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE in test_types:
        tests.extend(test(_,
                          lang_code,
                          site,
                          test_type=TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE,
                          show_reviews=show_reviews))
    if TEST_HTML in test_types:
        tests.extend(test(_, lang_code, site,
                          test_type=TEST_HTML,
                          show_reviews=show_reviews))
    if TEST_CSS in test_types:
        tests.extend(test(_, lang_code, site,
                          test_type=TEST_CSS,
                          show_reviews=show_reviews))
    if TEST_GOOGLE_LIGHTHOUSE_PWA in test_types:
        tests.extend(test(_,
                          lang_code,
                          site,
                          test_type=TEST_GOOGLE_LIGHTHOUSE_PWA,
                          show_reviews=show_reviews))
    if TEST_STANDARD_FILES in test_types:
        tests.extend(test(_, lang_code, site,
                          test_type=TEST_STANDARD_FILES,
                          show_reviews=show_reviews))
    if TEST_GOOGLE_LIGHTHOUSE_A11Y in test_types:
        tests.extend(test(_,
                          lang_code,
                          site,
                          test_type=TEST_GOOGLE_LIGHTHOUSE_A11Y,
                          show_reviews=show_reviews))
    if TEST_SITESPEED in test_types:
        tests.extend(test(_, lang_code, site,
                          test_type=TEST_SITESPEED,
                          show_reviews=show_reviews))
    if TEST_YELLOW_LAB_TOOLS in test_types:
        tests.extend(test(_,
                          lang_code,
                          site,
                          test_type=TEST_YELLOW_LAB_TOOLS,
                          show_reviews=show_reviews))
    if TEST_PA11Y in test_types:
        tests.extend(test(_,
                          lang_code,
                          site,
                          test_type=TEST_PA11Y,
                          show_reviews=show_reviews))
    if TEST_WEBBKOLL in test_types:
        tests.extend(test(_, lang_code, site,
                          test_type=TEST_WEBBKOLL,
                          show_reviews=show_reviews))
    if TEST_HTTP in test_types:
        tests.extend(test(_, lang_code, site,
                          test_type=TEST_HTTP,
                          show_reviews=show_reviews))
    if TEST_ENERGY_EFFICIENCY in test_types:
        tests.extend(test(_, lang_code, site,
                          test_type=TEST_ENERGY_EFFICIENCY,
                          show_reviews=show_reviews))
    if TEST_TRACKING in test_types:
        tests.extend(test(_, lang_code, site,
                          test_type=TEST_TRACKING,
                          show_reviews=show_reviews))
    if TEST_EMAIL in test_types:
        tests.extend(test(_, lang_code, site,
                          test_type=TEST_EMAIL, show_reviews=show_reviews))
    if TEST_SOFTWARE in test_types:
        tests.extend(test(_, lang_code, site,
                          test_type=TEST_SOFTWARE,
                          show_reviews=show_reviews))
    if TEST_A11Y_STATEMENT in test_types:
        tests.extend(test(_, lang_code, site,
                          test_type=TEST_A11Y_STATEMENT,
                          show_reviews=show_reviews))

    return tests


def test_sites(_, lang_code, sites, test_types=TEST_ALL, show_reviews=False):
    results = []

    print(_('TEXT_TEST_START_HEADER'))

    nof_sites = len(sites)
    has_more_then_one_site = nof_sites > 1

    if has_more_then_one_site:
        print(_('TEXT_TESTING_NUMBER_OF_SITES').format(nof_sites))

    site_index = 0
    for site in sites:
        if site_index > 0:
            print(_('TEXT_TEST_START_HEADER'))
        website = site[1]
        print(_('TEXT_TESTING_SITE').format(website))
        if has_more_then_one_site:
            print(_('TEXT_WEBSITE_X_OF_Y').format(site_index + 1, nof_sites))
        results.extend(test_site(_, lang_code, site,
                                 test_types, show_reviews))

        site_index += 1

    return results

def merge_dicts(dict1, dict2, sort, make_distinct):
    if dict1 is None:
        return dict2
    if dict2 is None:
        return dict1

    for domain, value in dict2.items():
        if domain in dict1:
            type_of_value = type(value)
            if type_of_value is dict:
                for subkey, subvalue in value.items():
                    if subkey in dict1[domain]:
                        if isinstance(subvalue, dict):
                            merge_dicts(
                                dict1[domain][subkey],
                                dict2[domain][subkey],
                                sort,
                                make_distinct)
                        elif isinstance(subvalue, list):
                            dict1[domain][subkey].extend(subvalue)
                            if make_distinct:
                                dict1[domain][subkey] = list(set(dict1[domain][subkey]))
                            if sort:
                                dict1[domain][subkey] = sorted(dict1[domain][subkey])
                    else:
                        dict1[domain][subkey] = dict2[domain][subkey]
            elif type_of_value == list:
                dict1[domain].extend(value)
                if make_distinct:
                    dict1[domain] = list(set(dict1[domain]))
                if sort:
                    dict1[domain] = sorted(dict1[domain])
            elif type_of_value == int:
                dict1[domain] = dict1[domain] + value
        else:
            dict1[domain] = value
    return dict1
