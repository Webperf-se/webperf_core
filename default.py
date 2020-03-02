#-*- coding: utf-8 -*-
import sys, getopt
import json
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

    result = list()

    # TODO: implementera test_type=None

    print("###############################################")

    i = 1

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
                
                site_test = SiteTests(site_id=site_id, type_of_test=test_type, check_report=checkreport, rating=the_test_result[0], test_date=datetime.datetime.now(), json_check_data=jsondata).todata()

                result.append(site_test)

                the_test_result = None # 190506 för att inte skriva testresultat till sajter när testet kraschat. Måste det sättas till ''?
        except Exception as e:
            print('FAIL!', website, '\n', e)
            pass

        i += 1
    
    return result

def testing(sites, test_type= ALL_TESTS):
    print('### {0} ###'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    tests = {}
    ##############
    if (test_type == ALL_TESTS or test_type == GOOGLE_PAGESPEED):
        print('###############################\nKör test: 0 - Google Pagespeed')
        tests['google_pagespeed'] = testsites(sites, test_type=GOOGLE_PAGESPEED)
    if (test_type == ALL_TESTS or test_type == PAGE_NOT_FOUND):
        print('###############################\nKör test: 2 - 404-test')
        tests['404'] = testsites(sites, test_type=PAGE_NOT_FOUND)
    if (test_type == ALL_TESTS or test_type == HTML):
        print('###############################\nKör test: 6 - HTML')
        tests['html'] = testsites(sites, test_type=HTML)
    if (test_type == ALL_TESTS or test_type == CSS):
        print('###############################\nKör test: 7 - CSS')
        tests['css'] = testsites(sites, test_type=CSS)
    if (test_type == ALL_TESTS or test_type == WEBBKOLL):
        print('###############################\nKör test: 20 - Webbkoll')
        tests['webbkoll'] = testsites(sites, test_type=WEBBKOLL)
    return tests

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
    -h/--help\t\t\t: Help information on how to use script
    -u/--url <site url>\t\t: website url to test against
    -t/--test <0/2/6/7/20>\t: runs ONE specific test against website(s)
    -i/--input <file path>\t: input file path (JSON)
    -o/--output <file path>\t: output file path (JSON)
    """

    test_type = ALL_TESTS
    sites = list()
    output_filename = ''

    try:
        opts, args = getopt.getopt(argv,"hu:t:i:o:",["help","url","test", "input", "output"])
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
            sites.append([0, arg])
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
            with open(arg) as json_input_file:
                data = json.load(json_input_file)
                for site in data["sites"]:
                    sites.append([site["id"], site["url"]])
            pass
        elif opt in ("-o", "--output"): # output file path
            output_filename = arg
            pass


    if (len(sites)):
        siteTests = testing(sites, test_type=test_type)
        if (len(output_filename) > 0):
            with open(output_filename, 'w') as outfile:
                json.dump(siteTests, outfile)
    else:
        print(main.__doc__)


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    main(sys.argv[1:])