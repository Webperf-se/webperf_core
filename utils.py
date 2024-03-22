# -*- coding: utf-8 -*-
import json
import sys
import getopt
import datetime
import traceback
from models import Sites, SiteTests
import config
import gettext

# TEST_ALL = -1

TEST_ALL = (TEST_UNKNOWN_01, TEST_GOOGLE_LIGHTHOUSE, TEST_PAGE_NOT_FOUND, TEST_UNKNOWN_03, TEST_GOOGLE_LIGHTHOUSE_SEO, TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE, TEST_HTML, TEST_CSS, TEST_GOOGLE_LIGHTHOUSE_PWA, TEST_STANDARD_FILES,
            TEST_GOOGLE_LIGHTHOUSE_A11Y, TEST_UNKNOWN_11, TEST_UNKNOWN_12, TEST_UNKNOWN_13, TEST_UNKNOWN_14, TEST_SITESPEED, TEST_UNKNOWN_16, TEST_YELLOW_LAB_TOOLS, TEST_PA11Y, TEST_UNKNOWN_19, TEST_WEBBKOLL, TEST_HTTP, TEST_ENERGY_EFFICIENCY, TEST_TRACKING, TEST_EMAIL, TEST_SOFTWARE, TEST_A11Y_STATEMENT) = range(27)


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
        elif test_type == TEST_A11Y_STATEMENT:
            from tests.a11y_statement import run_test

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
                json_data = json.dumps(json_data)
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
        
        # write error to failure.log file
        with open('failures.log', 'a') as outfile:
            
            outfile.writelines(['###############################################',
                                '\n# Information:',
                                '\nDateTime: {0}' .format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                                '\nUrl: {0}'.format(website),
                                '\nLanguage Code: {0}'.format(langCode),
                                '\nTest Type(s): {0}'.format(test_type),
                                '\nShow Reviews: {0}'.format(show_reviews),
                                 '\n###############################################'
                                '\n# Configuration (from config.py):',
                                '\nuseragent: {0}'.format(config.useragent),
                                '\nhttp_request_timeout: {0}'.format(config.http_request_timeout),
                                '\nwebbkoll_sleep: {0}'.format(config.webbkoll_sleep),
                                '\ncss_review_group_errors: {0}'.format(config.css_review_group_errors),
                                '\nreview_show_improvements_only: {0}'.format(config.review_show_improvements_only),
                                '\nylt_use_api: {0}'.format(config.ylt_use_api),
                                '\nlighthouse_use_api: {0}'.format(config.lighthouse_use_api),
                                '\nsitespeed_use_docker: {0}'.format(config.sitespeed_use_docker),
                                '\nsitespeed_iterations: {0}'.format(config.sitespeed_iterations),
                                '\nlocales: {0}'.format(config.locales),
                                '\ncache_when_possible: {0}'.format(config.cache_when_possible),
                                '\ncache_time_delta: {0}'.format(config.cache_time_delta),
                                '\nsoftware_use_stealth: {0}'.format(config.software_use_stealth),
                                '\nuse_detailed_report: {0}'.format(config.use_detailed_report),
                                '\nsoftware_browser: {0}'.format(config.software_browser),
                                 '\n###############################################\n'
                                 ])
            
            
            outfile.writelines(traceback.format_exception(e,e, e.__traceback__))

            outfile.writelines(['###############################################\n\n'])


        pass

    return list()


def test_site(_, langCode, site, test_types=TEST_ALL, show_reviews=False):
    # print(_('TEXT_TESTING_START_HEADER').format(
    #    datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    tests = list()
    ##############
    if TEST_GOOGLE_LIGHTHOUSE in test_types:
        tests.extend(test(_,
                          langCode, site, test_type=TEST_GOOGLE_LIGHTHOUSE, show_reviews=show_reviews))
    if TEST_PAGE_NOT_FOUND in test_types:
        tests.extend(test(_, langCode, site,
                          test_type=TEST_PAGE_NOT_FOUND, show_reviews=show_reviews))
    if TEST_GOOGLE_LIGHTHOUSE_SEO in test_types:
        tests.extend(test(_,
                          langCode, site, test_type=TEST_GOOGLE_LIGHTHOUSE_SEO, show_reviews=show_reviews))
    if TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE in test_types:
        tests.extend(test(_,
                          langCode, site, test_type=TEST_GOOGLE_LIGHTHOUSE_BEST_PRACTICE, show_reviews=show_reviews))
    if TEST_HTML in test_types:
        tests.extend(test(_, langCode, site,
                          test_type=TEST_HTML, show_reviews=show_reviews))
    if TEST_CSS in test_types:
        tests.extend(test(_, langCode, site,
                          test_type=TEST_CSS, show_reviews=show_reviews))
    if TEST_GOOGLE_LIGHTHOUSE_PWA in test_types:
        tests.extend(test(_,
                          langCode, site, test_type=TEST_GOOGLE_LIGHTHOUSE_PWA, show_reviews=show_reviews))
    if TEST_STANDARD_FILES in test_types:
        tests.extend(test(_, langCode, site,
                          test_type=TEST_STANDARD_FILES, show_reviews=show_reviews))
    if TEST_GOOGLE_LIGHTHOUSE_A11Y in test_types:
        tests.extend(test(_,
                          langCode, site, test_type=TEST_GOOGLE_LIGHTHOUSE_A11Y, show_reviews=show_reviews))
    if TEST_SITESPEED in test_types:
        tests.extend(test(_, langCode, site,
                          test_type=TEST_SITESPEED, show_reviews=show_reviews))
    if TEST_YELLOW_LAB_TOOLS in test_types:
        tests.extend(test(_,
                          langCode, site, test_type=TEST_YELLOW_LAB_TOOLS, show_reviews=show_reviews))
    if TEST_PA11Y in test_types:
        tests.extend(test(_,
                          langCode, site, test_type=TEST_PA11Y, show_reviews=show_reviews))
    if TEST_WEBBKOLL in test_types:
        tests.extend(test(_, langCode, site,
                          test_type=TEST_WEBBKOLL, show_reviews=show_reviews))
    if TEST_HTTP in test_types:
        tests.extend(test(_, langCode, site,
                          test_type=TEST_HTTP, show_reviews=show_reviews))
    if TEST_ENERGY_EFFICIENCY in test_types:
        tests.extend(test(_, langCode, site,
                          test_type=TEST_ENERGY_EFFICIENCY, show_reviews=show_reviews))
    if TEST_TRACKING in test_types:
        tests.extend(test(_, langCode, site,
                          test_type=TEST_TRACKING, show_reviews=show_reviews))
    if TEST_EMAIL in test_types:
        tests.extend(test(_, langCode, site,
                          test_type=TEST_EMAIL, show_reviews=show_reviews))
    if TEST_SOFTWARE in test_types:
        tests.extend(test(_, langCode, site,
                          test_type=TEST_SOFTWARE, show_reviews=show_reviews))
    if TEST_A11Y_STATEMENT in test_types:
        tests.extend(test(_, langCode, site,
                          test_type=TEST_A11Y_STATEMENT, show_reviews=show_reviews))

    return tests


def test_sites(_, langCode, sites, test_types=TEST_ALL, show_reviews=False):
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
