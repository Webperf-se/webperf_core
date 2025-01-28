# -*- coding: utf-8 -*-
import sys
import getopt
import json
import re

def main(argv):
    """
    WebPerf Core - Validate Sitespeed:s browsertime.har file

    Usage:
    verify_browsertime_har.py -h

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
        opts, _ = getopt.getopt(argv, "hfb:", [
                                   "help",
                                   "full",
                                   "browsertime="])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if len(opts) == 0:
        print(main.__doc__)
        sys.exit(2)

    full_validation = False
    validate = False
    browsertime_har = None
    for opt, arg in opts:
        if opt in ('-h', '--help'):  # help
            print(main.__doc__)
            sys.exit(0)
        elif opt in ('-f', '--full'): # validate also stuff that is not used by webperf_core
            full_validation = True
        elif opt in ("-b", "--browsertime"):  # validate browsertime.har for supported browsers
            browsertime_har = arg
            validate = True

    if validate:
        validate_browsertime(browsertime_har, full_validation)


    # No match for command so return error code to fail verification
    sys.exit(2)

def validate_browsertime(browsertime_har_path, full_validation):
    # http://www.softwareishard.com/blog/har-12-spec/
    is_ok = True
    with open(browsertime_har_path, encoding='utf-8') as json_input_file:
        browsertime_har = json.load(json_input_file)
        if 'log' not in browsertime_har:
            print('Error: log is missing in browsertime.har file')
            sys.exit(2)

        if full_validation:
            if 'version' not in browsertime_har['log']:
                print('Error: log.version is missing in browsertime.har file')
                is_ok = False
            is_ok = validate_creator(browsertime_har) and is_ok
            is_ok = validate_browser(browsertime_har) and is_ok

        pages_is_ok, page_refs = validate_pages(browsertime_har, full_validation)
        is_ok = pages_is_ok and is_ok
        is_ok = validate_entries(browsertime_har, page_refs, full_validation) and is_ok

    if is_ok:
        print('browsertime.har file is OK')
        sys.exit(0)
    else:
        sys.exit(2)

def validate_entries(browsertime_har, page_refs, full_validation):
    is_ok = True
    if 'entries' not in browsertime_har['log']:
        print('Error: log.entries array is missing in browsertime.har file')
        is_ok = False
    else:
        entry_index = 0
        for entry in browsertime_har['log']['entries']:
            is_ok = validate_entry(entry_index, entry, page_refs, full_validation) and is_ok
            entry_index += 1
        if entry_index < 1:
            print('Error: log.entries array has less than 1 entry in browsertime.har file')
            is_ok = False
    return is_ok

def validate_entry(entry_index, entry, page_refs, full_validation):
    is_ok = True

    is_ok = validate_entry_request(entry_index, entry, full_validation) and is_ok
    is_ok = validate_entry_response(entry_index, entry, full_validation) and is_ok

    # TODO: Add validation to "serverIPAddress" (according to modify_browsertime_content_entity)
    # TODO: Add validation to "httpVersion" (according to modify_browsertime_content_entity)

    if not full_validation:
        return is_ok

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
    else:
        if 'send' not in entry['timings']:
            print(f'Error: log.entries[{entry_index}].timings.send is missing in browsertime.har file')
            is_ok = False
        elif not isinstance(entry['timings']['send'], float) and not isinstance(entry['timings']['send'], int) and entry['timings']['send'] < 0:
            print(f'Error: log.entries[{entry_index}].timings.send property is wrong value in browsertime.har file')
            is_ok = False
        
        if 'wait' not in entry['timings']:
            print(f'Error: log.entries[{entry_index}].timings.wait is missing in browsertime.har file')
            is_ok = False
        elif not isinstance(entry['timings']['wait'], float) and not isinstance(entry['timings']['wait'], int) and entry['timings']['wait'] < 0:
            print(f'Error: log.entries[{entry_index}].timings.wait property is wrong value in browsertime.har file')
            is_ok = False

        if 'receive' not in entry['timings']:
            print(f'Error: log.entries[{entry_index}].timings.receive is missing in browsertime.har file')
            is_ok = False
        elif not isinstance(entry['timings']['receive'], float) and not isinstance(entry['timings']['receive'], int) and entry['timings']['receive'] < 0:
            print(f'Error: log.entries[{entry_index}].timings.receive property is wrong value in browsertime.har file')
            is_ok = False

    if 'pageref' not in entry:
        print(f'Error: log.entries[{entry_index}].pageref is missing in browsertime.har file')
        is_ok = False
    elif entry['pageref'] not in page_refs:
        print(f"Error: log.entries[{entry_index}].pageref has wrong value, actual value: {entry['pageref']}")
        is_ok = False

    if 'time' not in entry:
        print(f'Error: log.entries[{entry_index}].time is missing in browsertime.har file')
        is_ok = False
    elif not isinstance(entry['time'], float) and  not isinstance(entry['time'], int):
        print(f"Error: log.entries[{entry_index}].time has wrong value, actual value: {entry['time']}")
        is_ok = False

    return is_ok

def validate_entry_response(entry_index, entry, full_validation):
    is_ok = True
    if 'response' not in entry:
        print(f'Error: log.entries[{entry_index}].response is missing in browsertime.har file')
        is_ok = False

    if 'status' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.status is missing in browsertime.har file')
        is_ok = False
    elif not isinstance(entry['response']['status'], int):
        print(f"Error: log.entries[{entry_index}].response.status has wrong value, actual value: {entry['response']['status']}")
        is_ok = False
    elif entry['response']['status'] not in (
            100, 101, 102, 103,
            200, 201, 202, 203, 204, 205, 206, 207, 208, 226,
            300, 301, 302, 303, 304, 307, 308,
            400, 401, 402, 403, 404, 405, 406, 407, 408, 409,
            410, 411, 412, 413, 414, 415, 416, 417, 418,
            421, 422, 423, 424, 425, 426, 428, 429,
            431, 451,
            500, 501, 502, 503, 504, 505, 506, 507, 508, 510, 511
            ):
        print(f"Error: log.entries[{entry_index}].response.status has wrong value, actual value: {entry['response']['status']}")
        is_ok = False

    if 'content' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.content is missing in browsertime.har file')
        is_ok = False
    else:
        if 'mimeType' not in entry['response']['content']:
            print(f'Error: log.entries[{entry_index}].response.content.mimeType is missing in browsertime.har file')
            is_ok = False
        elif entry['response']['content']['mimeType'] not in ('text/html', 'text/html;charset=utf-8', 'text/html;charset=UTF-8', 'text/css', 'image/png', 'image/webp', 'text/javascript', 'font/woff2'):
            print(f"Error: log.entries[{entry_index}].response.content.mimeType has wrong value, actual value: {entry['response']['content']['mimeType']}")
            is_ok = False

        if 'size' not in entry['response']['content']:
            print(f'Error: log.entries[{entry_index}].response.content.size is missing in browsertime.har file')
            is_ok = False
        elif not isinstance(entry['response']['content']['size'], int):
            print(f"Error: log.entries[{entry_index}].response.content.size has wrong value, actual value: {entry['response']['content']['size']}")
            is_ok = False
        elif entry['response']['content']['size'] < 1 and ('status' not in entry['response'] and entry['response']['status'] != 204):
            print(f"Error: log.entries[{entry_index}].response.content.size has wrong value, actual value: {entry['response']['content']['size']}")
            is_ok = False

        if full_validation and 'compression' in entry['response']['content'] and not isinstance(entry['response']['content']['compression'], int):
            print(f"Error: log.entries[{entry_index}].response.content.compression has wrong value type, actual value type: {type(entry['response']['content']['compression'])}")
            is_ok = False

        if 'text' not in entry['response']['content']:
                if 'mimeType' in entry['response']['content'] and entry['response']['content']['mimeType'] in ('text/html;charset=utf-8', 'text/css', 'text/javascript'):
                    print(f"Error: log.entries[{entry_index}].response.content.text is missing in browsertime.har file {entry['response']['content']['mimeType']}")
                    is_ok = False
        elif 'status' in entry['response'] and entry['response']['status'] == 204:
            # ignore this
            a = 1
        elif len(entry['response']['content']['text']) < 1 and\
                ('mimeType' in entry['response']['content'] and entry['response']['content']['mimeType'] in ('text/html', 'text/html;charset=utf-8', 'text/html;charset=UTF-8', 'text/css', 'text/javascript')):
            # NOTE / WORKAROUND:
            # We would prefer to be able to use Firefox for this but currently we have a workaround
            # in place to only use chrome for when we need to read content of text based files.
            if full_validation:
                print(f"Error: log.entries[{entry_index}].response.content.text has wrong value, actual value: {entry['response']['content']['text']}, content-type: {entry['response']['content']['mimeType']}")
                is_ok = False

    if 'httpVersion' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.httpVersion is missing in browsertime.har file')
        is_ok = False
    is_ok = validate_entry_response_headers(entry_index, entry) and is_ok

    if not full_validation:
        return is_ok

    if 'redirectURL' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.redirectURL is missing in browsertime.har file')
        is_ok = False

    if 'statusText' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.statusText is missing in browsertime.har file')
        is_ok = False
    elif not isinstance(entry['response']['statusText'], str):
        print(f"Error: log.entries[{entry_index}].response.statusText has wrong value, actual value: {entry['response']['statusText']}")
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

    return is_ok

def validate_entry_response_headers(entry_index, entry):
    is_ok = True
    if 'headers' not in entry['response']:
        print(f'Error: log.entries[{entry_index}].response.headers array is missing in browsertime.har file')
        is_ok = False
    else:
        header_index = 0
        for header in entry['response']['headers']:
            if 'name' not in header:
                print(f'Error: log.entries[{entry_index}].response.headers[{header_index}].name is missing in browsertime.har file')
                is_ok = False
            elif re.match(r'[0-9a-z\-]+', header['name'], re.IGNORECASE) is None:
                print(f"Error: log.entries[{entry_index}].response.headers[{header_index}].name has wrong name, actual value: {header['name']}")
                is_ok = False

            if 'value' not in header:
                print(f'Error: log.entries[{entry_index}].response.headers[{header_index}].value is missing in browsertime.har file')
                is_ok = False
            elif re.match(r'[0-9a-z\-\.\"]+', header['value'], re.IGNORECASE) is None:
                print(f"Error: log.entries[{entry_index}].response.headers[{header_index}].value has wrong value, actual value: {header['value']}")
                is_ok = False
            header_index += 1

        if header_index < 1:
            print(f'Error: log.entries[{entry_index}].response.headers array has less than 1 header in browsertime.har file')
            is_ok = False
    return is_ok

def validate_entry_request(entry_index, entry, full_validation):
    is_ok = True
    if 'request' not in entry:
        print(f'Error: log.entries[{entry_index}].request is missing in browsertime.har file')
        is_ok = False
    else:
        if 'url' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.url is missing in browsertime.har file')
            is_ok = False
        else:
            if entry_index == 0 and entry['request']['url'] != 'https://webperf.se/':
                print(f"Error: log.entries[{entry_index}].request.url has wrong value, actual value: {entry['request']['url']}")
                is_ok = False
            if not entry['request']['url'].startswith('http://') and not entry['request']['url'].startswith('https://'):
                print(f"Error: log.entries[{entry_index}].request.url has wrong value, actual value: {entry['request']['url']}")
                is_ok = False

        if not full_validation:
            return is_ok

        if 'method' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.method is missing in browsertime.har file')
            is_ok = False
        elif entry['request']['method'] not in ('GET','POST', 'HEAD', 'PUT', 'DELETE', 'CONNECT', 'OPTIONS', 'TRACE', 'PATCH'):
            print(f"Error: log.entries[{entry_index}].request.method has wrong value, actual value: {entry['request']['method']}")
            is_ok = False

        if 'queryString' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.queryString is missing in browsertime.har file')
            is_ok = False
        elif entry_index == 0 and entry['request']['queryString'] != []:
            print(f"Error: log.entries[{entry_index}].request.queryString has wrong value, actual value: {entry['request']['queryString']}")
            is_ok = False

        if 'headersSize' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.headersSize is missing in browsertime.har file')
            is_ok = False
        elif not isinstance(entry['request']['headersSize'], int):
            print(f"Error: log.entries[{entry_index}].request.headersSize has wrong value, actual value: {entry['request']['headersSize']}")
            is_ok = False
        # NOTE: Not required by HAR specification 1.2
        # elif entry['request']['headersSize'] == -1:
        #     print(f"Warning: log.entries[{entry_index}].request.headersSize has wrong value, actual value: {entry['request']['headersSize']}")
        #     is_ok = False

        if 'bodySize' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.bodySize is missing in browsertime.har file')
            is_ok = False
        elif not isinstance(entry['request']['bodySize'], int):
            print(f"Error: log.entries[{entry_index}].request.bodySize has wrong value, actual value: {entry['request']['bodySize']}")
            is_ok = False
        # NOTE: Not required by HAR specification 1.2
        # elif entry['request']['bodySize'] != 0:
        #     print(f"Error: log.entries[{entry_index}].request.bodySize has wrong value, actual value: {entry['request']['bodySize']}")
        #     is_ok = False

        if 'cookies' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.cookies array is missing in browsertime.har file')
            is_ok = False

        if 'httpVersion' not in entry['request']:
            print(f'Error: log.entries[{entry_index}].request.httpVersion is missing in browsertime.har file')
            is_ok = False
        elif entry['request']['httpVersion'] not in ('http/1.1', 'h2','h3'):
            print(f"Error: log.entries[{entry_index}].request.httpVersion has wrong value, actual value: {entry['request']['httpVersion']}")
            is_ok = False

        is_ok = validate_entry_request_headers(entry_index, entry) and is_ok

    return is_ok

def validate_entry_request_headers(entry_index, entry):
    is_ok = True
    if 'headers' not in entry['request']:
        print(f'Error: log.entries[{entry_index}].request.headers array is missing in browsertime.har file')
        is_ok = False
    else:
        header_index = 0
        for header in entry['request']['headers']:
            if 'name' not in header:
                print(f'Error: log.entries[{entry_index}].request.headers[{header_index}].name is missing in browsertime.har file')
                is_ok = False
            elif re.match(r'[\:0-9a-z\-]+', header['name'], re.IGNORECASE) is None:
                print(f"Error: log.entries[{entry_index}].request.headers[{header_index}].name has wrong name, actual value: {header['name']}")
                is_ok = False

            if 'value' not in header:
                print(f'Error: log.entries[{entry_index}].request.headers[{header_index}].value is missing in browsertime.har file')
                is_ok = False
            elif re.match(r'[0-9a-z\-\.\"\?/\*]*', header['value'], re.IGNORECASE) is None:
                print(f"Error: log.entries[{entry_index}].request.headers[{header_index}].value has wrong value, actual value: {header['value']}")
                is_ok = False
            header_index += 1

        if header_index < 1:
            print(f'Error: log.entries[{entry_index}].request.headers array has less than 1 header in browsertime.har file')
            is_ok = False
    return is_ok

def validate_pages(browsertime_har, full_validation):
    is_ok = True
    page_refs = []
    if 'pages' not in browsertime_har['log']:
        print('Error: log.pages array is missing in browsertime.har file')
        is_ok = False
    else:
        page_index = 0
        for page in browsertime_har['log']['pages']:
            page_is_ok, page_ref = validate_page(page_index, page, full_validation)
            if page_ref is not None:
                page_refs.append(page_ref)
            is_ok = page_is_ok and is_ok
            page_index += 1
        if page_index < 1:
            print('Error: log.pages array has less than 1 page in browsertime.har file')
            is_ok = False

    return is_ok, page_refs

def validate_page(page_index, page, full_validation):
    is_ok = True
    page_ref = None
    if page['_url'] != 'https://webperf.se':
        print(f"Error: log.pages[{page_index}]._url has wrong value, actual value: {page['_url']}")
        is_ok = False

    if not full_validation:
        return is_ok, None

    if 'id' not in page:
        print(f'Error: log.pages[{page_index}].id is missing in browsertime.har file')
        is_ok = False
    elif f'page_{page_index +1 }' not in page['id']:
        print(f"Error: log.pages[{page_index}].id has wrong value, actual value: {page['id']}")
        is_ok = False
        page_ref = page['id']
    else:
        page_ref = page['id']

    if 'startedDateTime' not in page:
        print(f'Error: log.pages[{page_index}].startedDateTime is missing in browsertime.har file')
        is_ok = False
    elif re.match(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}.[0-9]{3}Z', page['startedDateTime']) is None:
        print(f'Error: log.pages[{page_index}].startedDateTime property has wrong value in browsertime.har file')
        is_ok = False

    if 'title' not in page:
        print(f'Error: log.pages[{page_index}].title is missing in browsertime.har file')
        is_ok = False

    if 'pageTimings' not in page:
        print(f'Error: log.pages[{page_index}].pageTimings is missing in browsertime.har file')
        is_ok = False
    else:
        if 'onContentLoad' not in page['pageTimings']:
            print(f'Error: log.pages[{page_index}].pageTimings.onContentLoad is missing in browsertime.har file')
            is_ok = False
        elif not isinstance(page['pageTimings']['onContentLoad'], float) and not isinstance(page['pageTimings']['onContentLoad'], int):
            print(f"Error: log.pages[{page_index}].pageTimings.onContentLoad has wrong value, actual value: {page['pageTimings']['onContentLoad']}")
            is_ok = False

        if 'onLoad' not in page['pageTimings']:
            print(f'Error: log.pages[{page_index}].pageTimings.onLoad is missing in browsertime.har file')
            is_ok = False
        elif not isinstance(page['pageTimings']['onLoad'], float) and not isinstance(page['pageTimings']['onLoad'], int):
            print(f"Error: log.pages[{page_index}].pageTimings.onLoad has wrong value, actual value: {page['pageTimings']['onLoad']}")
            is_ok = False

    if '_url' not in page:
        print(f'Error: log.pages[{page_index}]._url is missing in browsertime.har file')
        is_ok = False
    if page['_url'] != 'https://webperf.se':
        print(f"Error: log.pages[{page_index}]._url has wrong value, actual value: {page['_url']}")
        is_ok = False

    if '_meta' not in page:
        print(f'Error: log.pages[{page_index}]._meta is missing in browsertime.har file')
        is_ok = False
    return is_ok, page_ref

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
            print(f"Error: log.browser.name has wrong value, actual value: {browsertime_har['log']['browser']['name']}")
            is_ok = False

        if 'version' not in browsertime_har['log']['browser']:
            print('Error: log.browser.version is missing in browsertime.har file')
            is_ok = False
        if re.match(r'[0-9\.]+', browsertime_har['log']['browser']['version'], re.IGNORECASE) is None:
            print(f"Error: log.browser.name has wrong value, actual value: {browsertime_har['log']['browser']['version']}")
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
