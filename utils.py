# -*- coding: utf-8 -*-
import sys
import getopt
import datetime
from models import Sites, SiteTests
import config
import gettext

TEST_ALL = -1

(TEST_UNKNOWN_01, TEST_GOOGLE_LIGHTHOUSE, TEST_PAGE_NOT_FOUND, TEST_UNKNOWN_03, TEST_GOOGLE_LIGHTHOUSE_SEO, TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE, TEST_HTML, TEST_CSS, TEST_GOOGLE_LIGHTHOUSE_PWA, TEST_STANDARD_FILES,
 TEST_GOOGLE_LIGHTHOUSE_A11Y, TEST_UNKNOWN_11, TEST_UNKNOWN_12, TEST_UNKNOWN_13, TEST_UNKNOWN_14, TEST_SITESPEED, TEST_UNKNOWN_16, TEST_YELLOW_LAB_TOOLS, TEST_PA11Y, TEST_UNKNOWN_19, TEST_WEBBKOLL, TEST_HTTP, TEST_ENERGY_EFFICIENCY, TEST_TRACKING, TEST_EMAIL, TEST_SOFTWARE) = range(26)


def test(_, langCode, site, test_type=None, show_reviews=False,):
    """
    Executing the actual tests.
    Attributes:
    * test_type=num|None to execute all available tests
    """

    site_id = site[0]
    website = site[1]

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
        elif test_type == TEST_SITESPEED:
            from tests.performance_sitespeed_io import run_test
        elif test_type == TEST_YELLOW_LAB_TOOLS:
            from tests.frontend_quality_yellow_lab_tools import run_test
        elif test_type == TEST_PA11Y:
            from tests.a11y_pa11y import run_test
        elif test_type == TEST_HTTP:
            from tests.http_validator import run_test
        elif test_type == TEST_ENERGY_EFFICIENCY:
            #from tests.energy_efficiency_websitecarbon import run_test
            from tests.energy_efficiency import run_test
        elif test_type == TEST_TRACKING:
            from tests.tracking_validator import run_test
        elif test_type == TEST_EMAIL:
            from tests.email_validator import run_test
        elif test_type == TEST_SOFTWARE:
            from tests.software import run_test

        the_test_result = run_test(_, langCode, website)

        if the_test_result != None:
            rating = the_test_result[0]
            reviews = rating.get_reviews()
            print(_('TEXT_SITE_RATING'), rating)
            if show_reviews:
                print(_('TEXT_SITE_REVIEW'),
                      reviews)

            json_data = ''
            try:
                json_data = the_test_result[1]
            except:
                json_data = ''
                pass

            jsondata = str(json_data).encode('utf-8')  # --//--

            site_test = SiteTests(site_id=site_id, type_of_test=test_type,
                                  rating=rating,
                                  test_date=datetime.datetime.now(), json_check_data=jsondata).todata()

            return site_test
    except Exception as e:
        print(_('TEXT_TEST_END').format(
            datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        print(_('TEXT_EXCEPTION'), website, '\n', e)
        pass

    return list()


def test_site(_, langCode, site, test_type=TEST_ALL, show_reviews=False):
    # print(_('TEXT_TESTING_START_HEADER').format(
    #    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    tests = list()
    run_all_tests = test_type == TEST_ALL
    ##############
    if (run_all_tests or test_type == TEST_GOOGLE_LIGHTHOUSE):
        tests.extend(test(_,
                          langCode, site, test_type=TEST_GOOGLE_LIGHTHOUSE, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_PAGE_NOT_FOUND):
        tests.extend(test(_, langCode, site,
                          test_type=TEST_PAGE_NOT_FOUND, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_GOOGLE_LIGHTHOUSE_SEO):
        tests.extend(test(_,
                          langCode, site, test_type=TEST_GOOGLE_LIGHTHOUSE_SEO, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE):
        tests.extend(test(_,
                          langCode, site, test_type=TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_HTML):
        tests.extend(test(_, langCode, site,
                          test_type=TEST_HTML, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_CSS):
        tests.extend(test(_, langCode, site,
                          test_type=TEST_CSS, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_GOOGLE_LIGHTHOUSE_PWA):
        tests.extend(test(_,
                          langCode, site, test_type=TEST_GOOGLE_LIGHTHOUSE_PWA, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_STANDARD_FILES):
        tests.extend(test(_, langCode, site,
                          test_type=TEST_STANDARD_FILES, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_GOOGLE_LIGHTHOUSE_A11Y):
        tests.extend(test(_,
                          langCode, site, test_type=TEST_GOOGLE_LIGHTHOUSE_A11Y, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_SITESPEED):
        tests.extend(test(_, langCode, site,
                          test_type=TEST_SITESPEED, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_YELLOW_LAB_TOOLS):
        tests.extend(test(_,
                          langCode, site, test_type=TEST_YELLOW_LAB_TOOLS, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_PA11Y):
        tests.extend(test(_,
                          langCode, site, test_type=TEST_PA11Y, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_WEBBKOLL):
        tests.extend(test(_, langCode, site,
                          test_type=TEST_WEBBKOLL, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_HTTP):
        tests.extend(test(_, langCode, site,
                          test_type=TEST_HTTP, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_ENERGY_EFFICIENCY):
        tests.extend(test(_, langCode, site,
                          test_type=TEST_ENERGY_EFFICIENCY, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_TRACKING):
        tests.extend(test(_, langCode, site,
                          test_type=TEST_TRACKING, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_EMAIL):
        tests.extend(test(_, langCode, site,
                          test_type=TEST_EMAIL, show_reviews=show_reviews))
    if (run_all_tests or test_type == TEST_SOFTWARE):
        tests.extend(test(_, langCode, site,
                          test_type=TEST_SOFTWARE, show_reviews=show_reviews))

    return tests


def test_sites(_, langCode, sites, test_type=TEST_ALL, show_reviews=False):
    results = list()

    print(_('TEXT_TEST_START_HEADER'))

    nOfSites = len(sites)
    has_more_then_one_site = nOfSites > 1

    if has_more_then_one_site:
        print(_('TEXT_TESTING_NUMBER_OF_SITES').format(nOfSites))

    site_index = 0
    for site in sites:
        if site_index > 0:
            print(_('TEXT_TEST_START_HEADER'))
        website = site[1]
        print(_('TEXT_TESTING_SITE').format(website))
        if has_more_then_one_site:
            print(_('TEXT_WEBSITE_X_OF_Y').format(site_index + 1, nOfSites))
        results.extend(test_site(_, langCode, site,
                                 test_type, show_reviews))

        site_index += 1

    return results
