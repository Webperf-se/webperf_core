#-*- coding: utf-8 -*-
import sys, getopt
import datetime
from checks import *
from models import Sites, SiteTests
import config

def testsites(sites, test_type=None, only_test_untested_last_hours=24, order_by='title ASC'):
    """
    Executing the actual tests.
    Attributes:
    * test_type=num|None to execute all available tests
    """

    # TODO: implementera test_type=None

    print("###############################################")

    i = 1

    #sites = list()
    #for row in result:
    #    site_id = row[0]
    #    website = row[1]
    #    sites.append([site_id, website])

    print('Webbadresser som testas:', len(sites))

    for site in sites:
        site_id = site[0]
        website = site[1]
        print('{}. Testar adress {}'.format(i, website))
        the_test_result = None

        try:
            if test_type == 2:
                the_test_result = check_four_o_four(website)
            elif test_type == 6:
                the_test_result = check_w3c_valid(website)
            elif test_type == 7:
                the_test_result = check_w3c_valid_css(website)
            elif test_type == 20:
                the_test_result = check_privacy_webbkollen(website)
            elif test_type == 0:
                the_test_result = check_google_pagespeed(website)

            if the_test_result != None:
                print('Rating: ', the_test_result[0])
                #print('Review: ', the_test_result[1])

                json_data = ''
                try:
                    json_data = the_test_result[2]
                except:
                    json_data = ''
                    pass

                checkreport = str(the_test_result[1]).encode('utf-8') # för att lösa encoding-probs
                jsondata = str(json_data).encode('utf-8') # --//--
                
                site_test = SiteTests(site_id=site_id, type_of_test=test_type, check_report=checkreport, rating=the_test_result[0], test_date=datetime.datetime.now(), json_check_data=jsondata)

                the_test_result = None # 190506 för att inte skriva testresultat till sajter när testet kraschat. Måste det sättas till ''?
        except Exception as e:
            print('FAIL!', website, '\n', e)
            pass

        i += 1

def testing(sites = list([[0, "https://webperf.se"]]), test_type= -1):
    print('### {0} ###'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    ##############
    if (test_type == -1 or test_type == GOOGLE_PAGESPEED):
        print('###############################\nKör test: 0 - Google Pagespeed')
        testsites(sites, test_type=GOOGLE_PAGESPEED)
    if (test_type == -1 or test_type == PAGE_NOT_FOUND):
        print('###############################\nKör test: 2 - 404-test')
        testsites(sites, test_type=PAGE_NOT_FOUND)
    if (test_type == -1 or test_type == HTML):
        print('###############################\nKör test: 6 - HTML')
        testsites(sites, test_type=HTML)
    if (test_type == -1 or test_type == CSS):
        print('###############################\nKör test: 7 - CSS')
        testsites(sites, test_type=CSS)
    if (test_type == -1 or test_type == WEBBKOLL):
        print('###############################\nKör test: 20 - Webbkoll')
        testsites(sites, test_type=WEBBKOLL)

def validate_test_type(test_type):
    if test_type != HTML and test_type != PAGE_NOT_FOUND and test_type != CSS and test_type != WEBBKOLL and test_type != GOOGLE_PAGESPEED:
        print('Valid arguments for option -t/--test:')
        print('-t 0\t: Google Pagespeed')
        print('-t 2\t: 404-test')
        print('-t 6\t: HTML')
        print('-t 7\t: CSS')
        print('-t 20\t: Webbloll')
        return -2
    else:
        return test_type

def main(argv):
    """
    WebPerf Core

    Usage:
    default.py -u https://webperf.se

    Options and arguments:
    -h/--help\t: Help information on how to use script
    -u/--url\t: website url to test against
    -t/--test\t: runs ONE specific test against website(s)
    """

    test_type = -1
    site_url = ''
    try:
        opts, args = getopt.getopt(argv,"hu:t:",["help","url","test"])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if (opts.__len__() == 0):
        print(main.__doc__)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'): # help
            print(main.__doc__)
            sys.exit()
        elif opt in ("-u", "--url"): # site url
            site_url = arg
        elif opt in ("-t", "--test"): # test type
            try:
                tmp_test_type = int(arg)
                test_type = validate_test_type(tmp_test_type)
                if test_type == -2:
                    sys.exit(2)
            except Exception:
                validate_test_type(arg)
                sys.exit(2)

    if (site_url and test_type != -1):
        testing(list([[0, site_url]]), test_type=test_type)
    elif (site_url):
        testing(list([[0, site_url]]))


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    main(sys.argv[1:])