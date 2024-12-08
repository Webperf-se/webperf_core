# -*- coding: utf-8 -*-
import sys
import getopt
import json
import re

def main(argv):
    """
    WebPerf Core - Regression Test

    Usage:
    verify_result.py -h

    Options and arguments:
    -h/--help\t\t\t: Verify Help command
    -d/--docker <activate feature, True or False>\t\t:
      Updates DockerFile to use latest browsers
    -t/--test <test number>\t: Verify result of specific test

    NOTE:
    If you get this in step "Setup config [...]" you forgot to
    add repository secret for your repository.
    More info can be found here: https://github.com/Webperf-se/webperf_core/issues/81
    """

    try:
        opts, _ = getopt.getopt(argv, "hb:", [
                                   "help",
                                   "browsertime="])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if len(opts) == 0:
        print(main.__doc__)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):  # help
            print(main.__doc__)
            sys.exit(0)
        elif opt in ("-b", "--browsertime"):  # validate browsertime.har for supported browsers
            validate_browsertime(arg)

    # No match for command so return error code to fail verification
    sys.exit(2)

def validate_browsertime(browsertime_har_path):
    is_ok = True
    with open(browsertime_har_path, encoding='utf-8') as json_input_file:
        browsertime_har = json.load(json_input_file)
        if 'log' not in browsertime_har:
            print('Error: log is missing in browsertime.har file')
            sys.exit(2)

        if 'version' not in browsertime_har['log']:
            print('Error: log.version is missing in browsertime.har file')
            is_ok = False

        is_ok = validate_creator(browsertime_har) and is_ok
        is_ok = validate_browser(browsertime_har) and is_ok
        is_ok = validate_pages(browsertime_har) and is_ok
        is_ok = validate_entries(browsertime_har) and is_ok

    if is_ok:
        print('browsertime.har file is OK')
        sys.exit(0)
    else:
        sys.exit(2)

def validate_entries(browsertime_har):
    is_ok = True
    if 'entries' not in browsertime_har['log']:
        print('Error: log.entries array is missing in browsertime.har file')
        is_ok = False
    else:
        entry_index = 0
        for entry in browsertime_har['log']['entries']:
            is_ok = validate_entry(entry_index, entry) and is_ok
            entry_index += 1
        if entry_index < 1:
            print('Error: log.entries array has less than 1 entry in browsertime.har file')
            is_ok = False
    return is_ok

def validate_entry(entry_index, entry):
    is_ok = True
    if 'cache' not in entry:
        print(f'Error: log.entries[{entry_index}].id is missing in browsertime.har file')
        is_ok = False

    if 'startedDateTime' not in entry:
        print(f'Error: log.entries[{entry_index}].startedDateTime is missing in browsertime.har file')
        is_ok = False
    elif re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{3}Z', entry['startedDateTime']) is None:
        print(f'Error: log.entries[{entry_index}].startedDateTime property is wrong value in browsertime.har file')
        is_ok = False

    if 'timings' not in entry:
        print(f'Error: log.entries[{entry_index}].timings is missing in browsertime.har file')
        is_ok = False

    if 'pageref' not in entry:
        print(f'Error: log.entries[{entry_index}].pageref is missing in browsertime.har file')
        is_ok = False
    elif entry['pageref'] != 'page_1':
        print(f'Error: log.entries[{entry_index}].pageref has wrong value, actual value: {entry['pageref']}')
        is_ok = False

    if 'time' not in entry:
        print(f'Error: log.entries[{entry_index}].time is missing in browsertime.har file')
        is_ok = False
    elif not isinstance(entry['time'], float):
        print(f'Error: log.entries[{entry_index}].time has wrong value, actual value: {entry['time']}')
        is_ok = False

    is_ok = validate_entry_request(entry_index, entry) and is_ok
    is_ok = validate_entry_response(entry_index, entry) and is_ok
    return is_ok

def validate_entry_response(entry_index, entry):
    is_ok = True
    if 'response' not in entry:
        print(f'Error: log.entries[{entry_index}].response is missing in browsertime.har file')
        is_ok = False
    if 'redirectURL' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.redirectURL is missing in browsertime.har file')
        is_ok = False
    if 'status' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.status is missing in browsertime.har file')
        is_ok = False
    if 'statusText' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.statusText is missing in browsertime.har file')
        is_ok = False
    if 'content' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.content is missing in browsertime.har file')
        is_ok = False
    if 'headersSize' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.headersSize is missing in browsertime.har file')
        is_ok = False
    if 'bodySize' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.bodySize is missing in browsertime.har file')
        is_ok = False
    if 'cookies' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.cookies array is missing in browsertime.har file')
        is_ok = False
    if 'httpVersion' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.httpVersion is missing in browsertime.har file')
        is_ok = False
    if 'headers' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.headers array is missing in browsertime.har file')
        is_ok = False
    return is_ok

def validate_entry_request(entry_index, entry):
    is_ok = True
    if 'request' not in entry:
        print(f'Error: log.entries[{entry_index}].request is missing in browsertime.har file')
        is_ok = False
    else:
        if 'method' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.method is missing in browsertime.har file')
            is_ok = False
        elif entry['request']['method'] not in ('GET','POST'):
            print(f'Error: log.entries[{entry_index}].request.method has wrong value, actual value: {entry['request']['method']}')
            is_ok = False

        if 'url' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.url is missing in browsertime.har file')
            is_ok = False
        elif entry_index == 0 and entry['request']['url'] != 'https://webperf.se/':
            print(f'Error: log.entries[{entry_index}].request.url has wrong value, actual value: {entry['request']['url']}')
            is_ok = False

        if 'queryString' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.queryString is missing in browsertime.har file')
            is_ok = False
        elif entry_index == 0 and entry['request']['queryString'] != []:
            print(f'Error: log.entries[{entry_index}].request.queryString has wrong value, actual value: {entry['request']['queryString']}')
            is_ok = False

        if 'headersSize' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.headersSize is missing in browsertime.har file')
            is_ok = False
        elif not isinstance(entry['request']['headersSize'], int) or entry['request']['headersSize'] == -1:
            print(f'Error: log.entries[{entry_index}].request.headersSize has wrong value, actual value: {entry['request']['headersSize']}')
            is_ok = False

        if 'bodySize' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.bodySize is missing in browsertime.har file')
            is_ok = False
        elif not isinstance(entry['request']['bodySize'], int) or entry['request']['bodySize'] != 0:
            print(f'Error: log.entries[{entry_index}].request.bodySize has wrong value, actual value: {entry['request']['bodySize']}')
            is_ok = False

        if 'cookies' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.cookies array is missing in browsertime.har file')
            is_ok = False

        if 'httpVersion' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.httpVersion is missing in browsertime.har file')
            is_ok = False
        elif entry['request']['httpVersion'] not in ('h2','h3'):
            print(f'Error: log.entries[{entry_index}].request.httpVersion has wrong value, actual value: {entry['request']['httpVersion']}')
            is_ok = False

        if 'headers' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.headers array is missing in browsertime.har file')
            is_ok = False
    return is_ok

def validate_pages(browsertime_har):
    is_ok = True
    if 'pages' not in browsertime_har['log']:
        print('Error: log.pages array is missing in browsertime.har file')
        is_ok = False
    else:
        page_index = 0
        for page in browsertime_har['log']['pages']:
            is_ok = validate_page(page_index, page) and is_ok
            page_index += 1
        if page_index < 1:
            print('Error: log.pages array has less than 1 page in browsertime.har file')
            is_ok = False
    return is_ok

def validate_page(page_index, page):
    is_ok = True
    if 'id' not in page:
        print(f'Error: log.pages[{page_index}].id is missing in browsertime.har file')
        is_ok = False
    if f'page_{page_index +1 }' not in page['id']:
        print(f'Error: log.pages[{page_index}].id has wrong value, actual value: {page['id']}')
        is_ok = False

    if 'startedDateTime' not in page:
        print(f'Error: log.pages[{page_index}].startedDateTime is missing in browsertime.har file')
        is_ok = False
    if re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{3}Z', page['startedDateTime']) is None:
        print(f'Error: log.pages[{page_index}].startedDateTime property is wrong value in browsertime.har file')
        is_ok = False

    if 'title' not in page:
        print(f'Error: log.pages[{page_index}].title is missing in browsertime.har file')
        is_ok = False
    if 'pageTimings' not in page:
        print(f'Error: log.pages[{page_index}].pageTimings is missing in browsertime.har file')
        is_ok = False

    if '_url' not in page:
        print(f'Error: log.pages[{page_index}]._url is missing in browsertime.har file')
        is_ok = False
    if page['_url'] != 'https://webperf.se':
        print(f'Error: log.pages[{page_index}]._url has wrong value, actual value: {page['_url']}')
        is_ok = False

    if '_meta' not in page:
        print(f'Error: log.pages[{page_index}]._meta is missing in browsertime.har file')
        is_ok = False
    return is_ok

def validate_browser(browsertime_har):
    is_ok = True
    if 'browser' not in browsertime_har['log']:
        print('Error: log.browser is missing in browsertime.har file')
        is_ok = False
    else:
        if 'name' not in browsertime_har['log']['browser']:
            print('Error: log.browser.name is missing in browsertime.har file')
            is_ok = False
        if browsertime_har['log']['browser']['name'] not in ('firefox', 'Chrome'):
            print(f'Error: log.browser.name has wrong value, actual value: {browsertime_har['log']['browser']['name']}')
            is_ok = False

        if 'version' not in browsertime_har['log']['browser']:
            print('Error: log.browser.version is missing in browsertime.har file')
            is_ok = False
        if re.match(r'[0-9\.]+', browsertime_har['log']['browser']['version'], re.IGNORECASE) is None:
            print(f'Error: log.browser.name has wrong value, actual value: {browsertime_har['log']['browser']['version']}')
            is_ok = False
    return is_ok

def validate_creator(browsertime_har):
    is_ok = True
    if 'creator' not in browsertime_har['log']:
        print('Error: log.creator is missing in browsertime.har file')
        is_ok = False
    else:
        if 'name' not in browsertime_har['log']['creator']:
            print('Error: log.creator.name is missing in browsertime.har file')
            is_ok = False
        if 'version' not in browsertime_har['log']['creator']:
            print('Error: log.creator.version is missing in browsertime.har file')
            is_ok = False
    return is_ok

if __name__ == '__main__':
    main(sys.argv[1:])
