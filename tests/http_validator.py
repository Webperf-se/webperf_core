# -*- coding: utf-8 -*-
import os
import datetime
import urllib.parse
import datetime
import sys
import ssl
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from requests.packages.urllib3.util import ssl_
# https://docs.python.org/3/library/urllib.parse.html
import urllib
import config
from models import Rating
from tests.utils import dns_lookup
from tests.utils import *
from tests.sitespeed_base import get_result
import dns.name
import dns.query
import dns.dnssec
import dns.message
import dns.resolver
import dns.rdatatype
import datetime
import gettext
_local = gettext.gettext


# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
review_show_improvements_only = config.review_show_improvements_only
sitespeed_use_docker = config.sitespeed_use_docker
try:
    software_browser = config.software_browser
except:
    # If browser is not set in config.py this will be the default
    software_browser = 'chrome'
try:
    use_cache = config.cache_when_possible
    cache_time_delta = config.cache_time_delta
except:
    # If cache_when_possible variable is not set in config.py this will be the default
    use_cache = False
    cache_time_delta = timedelta(hours=1)


def run_test(_, langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    # TODO: Check if we can use sitespeed instead (to make it more accurate), https://addons.mozilla.org/en-US/firefox/addon/http2-indicator/

    rating = Rating(_, review_show_improvements_only)
    result_dict = {}

    language = gettext.translation(
        'http_validator', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    # We must take in consideration "www." subdomains...

    orginal_url = url
    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    if hostname.startswith('www.'):
        url = url.replace(hostname, hostname[4:])

    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    result_dict = check_http_to_https(url)

    result_dict = check_tls_version(result_dict)

    result_dict = check_ip_version(result_dict)

    result_dict = check_http_version(url, result_dict)

    # result_dict = check_dnssec(result_dict)

    result_dict = cleanup(result_dict)

    nice_result = json.dumps(result_dict, indent=3)
    print('DEBUG TOTAL', nice_result)

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)


def cleanup(result_dict):
    for domain in result_dict.keys():
        del result_dict[domain]['urls']
    return result_dict

def merge_dicts(dict1, dict2):
    if dict1 == None:
        return dict2
    if dict2 == None:
        return dict1

    for key, value in dict2.items():
        if key in dict1:
            for subkey, subvalue in value.items():
                dict1[key][subkey].extend(subvalue)
                dict1[key][subkey] = sorted(list(set(dict1[key][subkey])))
        else:
            dict1[key] = value
    return dict1

def rate_url(filename, origin_domain):

    result = {}

    if filename == '':
        return result
    
    # Fix for content having unallowed chars
    with open(filename) as json_input_file:
        har_data = json.load(json_input_file)

        if 'log' in har_data:
            har_data = har_data['log']

        for entry in har_data["entries"]:
            req = entry['request']
            res = entry['response']
            req_url = req['url']

            o = urllib.parse.urlparse(req_url)
            req_domain = o.hostname

            if req_domain not in result:
                result[req_domain] = {
                    'protocols': [],
                    'schemes': [],
                    'ip-versions': [],
                    'transport-layers': [],
                    'urls': []
                }

            result[req_domain]['schemes'].append(o.scheme.upper())
            result[req_domain]['urls'].append(req_url)

            if 'httpVersion' in req and req['httpVersion'] != '':
                result[req_domain]['protocols'].append(req['httpVersion'].replace('h2', 'HTTP/2').replace('h3', 'HTTP/3').upper())

            if 'httpVersion' in res and res['httpVersion'] != '':
                result[req_domain]['protocols'].append(res['httpVersion'].replace('h2', 'HTTP/2').replace('h3', 'HTTP/3').upper())

            if 'serverIPAddress' in entry:
                if ':' in entry['serverIPAddress']:
                    result[req_domain]['ip-versions'].append('IPv6')
                else:
                    result[req_domain]['ip-versions'].append('IPv4')


            result[req_domain]['protocols'] = list(set(result[req_domain]['protocols']))
            result[req_domain]['schemes'] = list(set(result[req_domain]['schemes']))
            result[req_domain]['ip-versions'] = list(set(result[req_domain]['ip-versions']))

    return result

def check_dnssec(result_dict):
    # To facilitate signature validation, DNSSEC adds a few new DNS record types4:

    # RRSIG - Contains a cryptographic signature
    # DNSKEY - Contains a public signing key
    # DS - Contains the hash of a DNSKEY record
    # NSEC and NSEC3 - For explicit denial-of-existence of a DNS record
    # CDNSKEY and CDS - For a child zone requesting updates to DS record(s) in the parent zone
    # get nameservers for target domain

    for domain in result_dict.keys():
        try:
            response = dns.resolver.query('{0}.'.format(domain), dns.rdatatype.NS)

            # we'll use the first nameserver in this example
            nsname = response.rrset[0].to_text()  # name
            #nsname = response.rrset[1].to_text()  # name

            # get DNSKEY for zone
            request = dns.message.make_query('{0}.'.format(domain), dns.rdatatype.DNSKEY, want_dnssec=True)
            name = dns.name.from_text('{0}.'.format(domain))

            if 'IPv4' in result_dict[domain]['ip-versions'] or 'IPv4*' in result_dict[domain]['ip-versions']:
                response = dns.resolver.query(nsname, dns.rdatatype.A)
                nsaddr = response.rrset[0].to_text()  # IPv4

                # send the query
                response = dns.query.udp(request, nsaddr)

                if response.rcode() != 0:
                    # HANDLE QUERY FAILED (SERVER ERROR OR NO DNSKEY RECORD)
                    a = 1
                    # print('D.1', response.rcode())
                    continue
                else:
                    a = 2
                    # print('D.2', response.rcode())

                # answer should contain two RRSET: DNSKEY and RRSIG (DNSKEY)
                answer = response.answer
                # print('E', answer)
                if len(answer) != 2:
                    # SOMETHING WENT WRONG
                    # print('E.1', answer, response)
                    continue
                else:
                    # print('E.2', answer)
                    a = 1

                # the DNSKEY should be self-signed, validate it
                try:
                    # print('F')
                    dns.dnssec.validate(answer[0], answer[1], {name: answer[0]})
                except dns.dnssec.ValidationFailure:
                    # BE SUSPICIOUS
                    a = False
                    # print('G VALIDATION FAIL')
                else:
                    # WE'RE GOOD, THERE'S A VALID DNSSEC SELF-SIGNED KEY FOR example.com
                    # print('G VALIDATION SUCCESS')
                    result_dict[domain]['protocols'].append('DNSSEC')
                    # a = True

            # if 'IPv6' in result_dict[domain]['ip-versions'] or 'IPv6*' in result_dict[domain]['ip-versions']:
            #     b = 1
            #     print('B IPv6')
        except Exception:
            c = 1
                
    return result_dict

def check_dnssec_for_domain(domain, result_dict):
    # To facilitate signature validation, DNSSEC adds a few new DNS record types4:

    # RRSIG - Contains a cryptographic signature
    # DNSKEY - Contains a public signing key
    # DS - Contains the hash of a DNSKEY record
    # NSEC and NSEC3 - For explicit denial-of-existence of a DNS record
    # CDNSKEY and CDS - For a child zone requesting updates to DS record(s) in the parent zone
    # get nameservers for target domain

    for domain in result_dict.keys():
        response = dns.resolver.query('{0}.'.format(domain), dns.rdatatype.NS)

        # we'll use the first nameserver in this example
        nsname = response.rrset[0].to_text()  # name
        print('A', nsname)

        # get DNSKEY for zone
        request = dns.message.make_query('{0}.'.format(domain), dns.rdatatype.DNSKEY, want_dnssec=True)
        name = dns.name.from_text('{0}.'.format(domain))

        if 'IPv4' in result_dict[domain]['ip-versions'] or 'IPv4*' in result_dict[domain]['ip-versions']:
            print('B IPv4')
            response = dns.resolver.query(nsname, dns.rdatatype.A)
            nsaddr = response.rrset[0].to_text()  # IPv4

            print('C', nsaddr)
            # send the query
            response = dns.query.udp(request, nsaddr)

            if response.rcode() != 0:
                # HANDLE QUERY FAILED (SERVER ERROR OR NO DNSKEY RECORD)
                print('D.1', response.rcode())
            else:
                print('D.2', response.rcode())

            # answer should contain two RRSET: DNSKEY and RRSIG (DNSKEY)
            answer = response.answer
            print('E', answer)
            if len(answer) != 2:
                # SOMETHING WENT WRONG
                print('E.1', answer, response)
            else:
                print('E.2', answer)

            # the DNSKEY should be self-signed, validate it
            try:
                print('F')
                dns.dnssec.validate(answer[0], answer[1], {name: answer[0]})
            except dns.dnssec.ValidationFailure:
                # BE SUSPICIOUS
                a = False
                print('G VALIDATION FAIL')
            else:
                # WE'RE GOOD, THERE'S A VALID DNSSEC SELF-SIGNED KEY FOR example.com
                print('G VALIDATION SUCCESS')
                a = True



def check_http_to_https(url):
    # Firefox
    # dom.security.https_only_mode

    http_url = ''

    o = urllib.parse.urlparse(url)
    o_domain = o.hostname

    if (o.scheme == 'https'):
        http_url = url.replace('https://', 'http://')
    else:
        http_url = url

    browser = 'firefox'
    configuration = ''
    print('HTTP2HTTPS')
    result_dict = get_website_support_from_sitespeed(http_url, configuration, browser, request_timeout)

    # If website redirects to www. domain without first redirecting to HTTPS, make sure we test it.
    if o_domain in result_dict:
        if 'HTTPS' not in result_dict[o_domain]['schemes']:
            result_dict[o_domain]['schemes'].append('HTTP-REDIRECT')
            https_url = url.replace('http://', 'https://')
            result_dict = merge_dicts(get_website_support_from_sitespeed(https_url, configuration, browser, request_timeout), result_dict)
        else:
            result_dict[o_domain]['schemes'].append('HTTPS-REDIRECT')

        # TODO: Should we add check for HSTS and if website is in preload list (example: start.stockholm)
        # being in preload list means http:// requests will be converted to https:// request before leaving browser.
        # preload list source can be collected here: https://source.chromium.org/chromium/chromium/src/+/main:net/http/transport_security_state_static.json
        # or is below good enough?
        if 'HTTP' not in result_dict[o_domain]['schemes']:
            result_dict[o_domain]['schemes'].append('HSTS-PRELOAD*')

    # If we have www. domain, ensure we validate HTTP2HTTPS on that as well
    www_domain_key = 'www.{0}'.format(o_domain)
    if www_domain_key in result_dict:
        if 'HTTP' not in result_dict[www_domain_key]['schemes']:
            result_dict[www_domain_key]['schemes'].append('HTTPS-REDIRECT')
            www_http_url = http_url.replace(o_domain, www_domain_key)
            result_dict = merge_dicts(get_website_support_from_sitespeed(www_http_url, configuration, browser, request_timeout), result_dict)
        else:
            result_dict[www_domain_key]['schemes'].append('HTTP-REDIRECT')

    return result_dict


def check_ip_version(result_dict):
    # network.dns.ipv4OnlyDomains
    # network.dns.disableIPv6

    if not contains_value_for_all(result_dict, 'ip-versions', 'IPv4'):
        for domain in result_dict.keys():
            if 'IPv4' not in result_dict[domain]['ip-versions']:
                ip4_result = dns_lookup(domain, "A")
                if len(ip4_result) > 0:
                    result_dict[domain]['ip-versions'].append('IPv4*')

    if not contains_value_for_all(result_dict, 'ip-versions', 'IPv6'):
        for domain in result_dict.keys():
            if 'IPv6' not in result_dict[domain]['ip-versions']:
                ip4_result = dns_lookup(domain, "AAAA")
                if len(ip4_result) > 0:
                    result_dict[domain]['ip-versions'].append('IPv6*')

    return result_dict


def protocol_version_score(url, domain, protocol_version, result_dict):
    result_not_validated = (False, '')
    result_validated = (False, '')

    protocol_rule = False
    protocol_name = ''

    try:
        if protocol_version == ssl.PROTOCOL_TLS:
            protocol_name = 'TLSv1.3'
            assert ssl.HAS_TLSv1_3
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2
        elif protocol_version == ssl.PROTOCOL_TLSv1_2:
            protocol_name = 'TLSv1.2'
            assert ssl.HAS_TLSv1_2
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_3
        elif protocol_version == ssl.PROTOCOL_TLSv1_1:
            protocol_name = 'TLSv1.1'
            assert ssl.HAS_TLSv1_1
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
        elif protocol_version == ssl.PROTOCOL_TLSv1:
            protocol_name = 'TLSv1.0'
            assert ssl.HAS_TLSv1
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
        elif protocol_version == ssl.PROTOCOL_SSLv3:
            protocol_name = 'SSLv3'
            assert ssl.HAS_SSLv3
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
        elif protocol_version == ssl.PROTOCOL_SSLv2:
            protocol_name = 'SSLv2'
            protocol_rule = ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
            assert ssl.HAS_SSLv2

        if has_protocol_version(
            url, True, protocol_rule)[0]:
            result_dict[domain]['transport-layers'].append(protocol_name)
        elif has_protocol_version(
            url, False, protocol_rule)[0]:
            result_dict[domain]['transport-layers'].append('{0}-'.format(protocol_name))

    except ssl.SSLError as sslex:
        print('error 0.0s', sslex)
        pass
    except AssertionError:
        print('### No {0} support on your machine, unable to test ###'.format(
            protocol_name))
        pass
    except:
        print('error protocol_version_score: {0}'.format(sys.exc_info()[0]))
        pass

    return result_dict


def check_tls_version(result_dict):
    for domain in result_dict.keys():
        # TODO: Make sure to find https:// based url instead of creating one.
        https_url = result_dict[domain]['urls'][0].replace('http://', 'https://')
        result_dict = protocol_version_score(https_url, domain, ssl.PROTOCOL_TLS, result_dict)
        result_dict = protocol_version_score(https_url, domain, ssl.PROTOCOL_TLSv1_2, result_dict)
        result_dict = protocol_version_score(https_url, domain, ssl.PROTOCOL_TLSv1_1, result_dict)
        result_dict = protocol_version_score(https_url, domain, ssl.PROTOCOL_TLSv1, result_dict)

    # Firefox:
    # security.tls.version.min
    # security.tls.version.max

    # 1 = TLS 1.0
    # 2 = TLS 1.1
    # 3 = TLS 1.2
    # 4 = TLS 1.3

    # o = urllib.parse.urlparse(url)
    # domain = o.hostname

    # url = url.replace('http://', 'https://')

    # browser = 'firefox'
    # # configuration = ' --firefox.preference network.http.http2.enabled:false --firefox.preference network.http.http3.enable:false --firefox.preference network.http.version:1.1'
    # configuration = ' --firefox.preference security.tls.version.min:4 --firefox.preference security.tls.version.max:4'
    # url2 = change_url_to_test_url(url, 'TLS1_3')
    # print('TLS/1.3')
    # tls1_3_result = get_website_support_from_sitespeed(url2, configuration, browser, 2 * 60)
    # for domain in tls1_3_result.keys():
    #     result_dict[domain]['transport-layers'].append('TLSv1.3')

    # configuration = ' --firefox.preference security.tls.version.min:3 --firefox.preference security.tls.version.max:3'
    # url2 = change_url_to_test_url(url, 'TLS1_2')
    # print('TLS/1.2')
    # tls1_2_result = get_website_support_from_sitespeed(url2, configuration, browser, 2 * 60)
    # for domain in tls1_2_result.keys():
    #     result_dict[domain]['transport-layers'].append('TLSv1.2')

    # configuration = ' --firefox.preference security.tls.version.min:2 --firefox.preference security.tls.version.max:2'
    # url2 = change_url_to_test_url(url, 'TLS1_1')
    # print('TLS/1.1')
    # tls1_1_result = get_website_support_from_sitespeed(url2, configuration, browser, 2 * 60)
    # for domain in tls1_1_result.keys():
    #     result_dict[domain]['transport-layers'].append('TLSv1.1')

    # configuration = ' --firefox.preference security.tls.version.min:1 --firefox.preference security.tls.version.max:1'
    # url2 = change_url_to_test_url(url, 'TLS1_0')
    # print('TLS/1.0')
    # tls1_0_result = get_website_support_from_sitespeed(url2, configuration, browser, 2 * 60)
    # for domain in tls1_0_result.keys():
    #     result_dict[domain]['transport-layers'].append('TLSv1.0')

    # TODO: check cipher security
    # TODO: re add support for identify wrong certificate

    return result_dict

def get_website_support_from_sitespeed(url, configuration, browser, timeout):
    # We don't need extra iterations for what we are using it for
    sitespeed_iterations = 1
    sitespeed_arg = '--plugins.remove screenshot --plugins.remove html --plugins.remove metrics --browsertime.screenshot false --screenshot false --screenshotLCP false --browsertime.screenshotLCP false --videoParams.createFilmstrip false --visualMetrics false --visualMetricsPerceptual false --visualMetricsContentful false --browsertime.headless true --utc true -n {0}'.format(
        1)

    if 'firefox' in browser:
        sitespeed_arg = '-b firefox --firefox.includeResponseBodies all --firefox.preference privacy.trackingprotection.enabled:false --firefox.preference privacy.donottrackheader.enabled:false --firefox.preference browser.safebrowsing.malware.enabled:false --firefox.preference browser.safebrowsing.phishing.enabled:false{1} {0}'.format(
            sitespeed_arg, configuration)
    else:
        sitespeed_arg = '-b chrome --chrome.cdp.performance false --browsertime.chrome.timeline false --browsertime.chrome.includeResponseBodies all --browsertime.chrome.args ignore-certificate-errors {0}'.format(
            sitespeed_arg)

    sitespeed_arg = '--shm-size=1g {0}'.format(
        sitespeed_arg)

    if 'nt' not in os.name:
        sitespeed_arg += ' --xvfb'

    (result_folder_name, filename) = get_result(
        url, sitespeed_use_docker, sitespeed_arg, timeout)
    
    o = urllib.parse.urlparse(url)
    origin_domain = o.hostname
    result = rate_url(filename, origin_domain)

    nice_result = json.dumps(result, indent=3)
    print('DEBUG', nice_result)

    return result

def contains_value_for_all(result_dict, key, value):
    if result_dict == None:
        return False

    has_value = True    
    for domain in result_dict.keys():
        if key not in result_dict[domain] or value not in result_dict[domain][key]:
            has_value = False
    return has_value

def check_http_version(url, result_dict):

    # SiteSpeed (firefox):
    # "httpVersion": "HTTP/1"
    # "httpVersion": "HTTP/1.1"
    # "httpVersion": "HTTP/2"
    # "httpVersion": "HTTP/3"

    # SiteSpeed (chrome):
    # "httpVersion": "http/1.1"
    # "httpVersion": "h2"
    # "httpVersion": "h3"

    # Chrome:
    # https://www.chromium.org/for-testers/providing-network-details/


    # Firefox:
    # about:networking
    # network.http.http2.enabled
    # network.http.http3.enable
    # network.http.version

    # network.http.version and their effects1:
    # - 0.9
    # - 1.0
    # - 1.1 (Default)
    # - 2.0
    # - 3.02

    # Response Header: alt-svc
    # h3=\":443\"; ma=2592000, h3-29=\":443\"; ma=2592000, h3-Q050=\":443\"; ma=2592000, h3-Q046=\":443\"; ma=2592000, h3-Q043=\":443\"; ma=2592000, quic=\":443\"; ma=2592000; v=\"43,46\"
    # h3=":443";
    # ma=2592000, h3-29=":443";
    # ma=2592000, h3-Q050=":443";
    # ma=2592000, h3-Q046=":443";
    # ma=2592000, h3-Q043=":443";
    # ma=2592000, quic=":443";
    # ma=2592000; v="43,46"

    # https://www.http3check.net/?host=https%3A%2F%2Fwebperf.se
    # 0-RTT
    # H3
    # H3-29
    # H3-Q050
    # H3-Q046
    # H3-Q043
    # Q043
    # Q046

    if not contains_value_for_all(result_dict, 'protocols', 'HTTP/1.1'):
        browser = 'firefox'
        # configuration = ' --firefox.preference network.http.http2.enabled:false --firefox.preference network.http.http3.enable:false --firefox.preference network.http.version:1.1'
        configuration = ' --firefox.preference network.http.http2.enabled:false --firefox.preference network.http.http3.enable:false'
        url2 = change_url_to_test_url(url, 'HTTPv1')
        print('HTTP/1.1')
        result_dict = merge_dicts(get_website_support_from_sitespeed(url2, configuration, browser, request_timeout), result_dict)

    if not contains_value_for_all(result_dict, 'protocols', 'HTTP/2'):
        browser = 'firefox'
        configuration = ' --firefox.preference network.http.http2.enabled:true --firefox.preference network.http.http3.enable:false --firefox.preference network.http.version:3.0'
        url2 = change_url_to_test_url(url, 'HTTPv2')
        print('HTTP/2')
        result_dict = merge_dicts(get_website_support_from_sitespeed(url2, configuration, browser, request_timeout), result_dict)

    if not contains_value_for_all(result_dict, 'protocols', 'HTTP/3'):
        browser = 'firefox'
        configuration = ' --firefox.preference network.http.http2.enabled:false --firefox.preference network.http.http3.enable:true --firefox.preference network.http.version:3.0'
        url2 = change_url_to_test_url(url, 'HTTPv3')
        print('HTTP/3')
        result_dict = merge_dicts(get_website_support_from_sitespeed(url2, configuration, browser, request_timeout), result_dict)

    return result_dict

# Read post at: https://hussainaliakbar.github.io/restricting-tls-version-and-cipher-suites-in-python-requests-and-testing-wireshark/
WEAK_CIPHERS = (
    'ECDHE+AES128+CBC+SHA:'
    'ECDHE+AES256+CBC+SHA:'
    'ECDHE+RSA+3DES+EDE+CBC+SHA:'
    'ECDHE+RSA+AES256+GCM+SHA383:'
    'RSA+AES128+CBC+SHA:'
    'RSA+AES256+CBC+SHA:'
    'RSA+AES128+GCM+SHA256:'
    'RSA+AES256+GCM+SHA:'
    'RSA+AES256+GCM+SHA383:'
    'RSA+CAMELLIA128+CBC+SHA:'
    'RSA+CAMELLIA256+CBC+SHA:'
    'RSA+IDEA+CBC+SHA:'
    'RSA+AES256+GCM+SHA:'
    'RSA+3DES+EDE+CBC+SHA:'
    'RSA+SEED+CBC+SHA:'
    'DHE+RSA+3DES+EDE+CBC+SHA:'
    'DHE+RSA+AES128+CBC+SHA:'
    'DHE+RSA+AES256+CBC+SHA:'
    'DHE+RSA+CAMELLIA128+CBC+SHA:'
    'DHE+RSA+CAMELLIA256+CBC+SHA:'
    'DHE+RSA+SEED+CBC+SHA:'
)


class TlsAdapterWeakCiphers(HTTPAdapter):

    def __init__(self, ssl_options=0, **kwargs):
        self.ssl_options = ssl_options
        super(TlsAdapterWeakCiphers, self).__init__(**kwargs)

    def init_poolmanager(self, *pool_args, **pool_kwargs):
        ctx = ssl_.create_urllib3_context(
            ciphers=WEAK_CIPHERS,
            cert_reqs=ssl.CERT_REQUIRED, options=self.ssl_options)

        self.poolmanager = PoolManager(*pool_args,
                                       ssl_context=ctx,
                                       **pool_kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = ssl_.create_urllib3_context(ciphers=WEAK_CIPHERS)
        kwargs['ssl_context'] = context
        return super(TlsAdapterWeakCiphers, self).proxy_manager_for(*args, **kwargs)


def has_weak_cipher(url, protocol_version):
    session = False

    try:
        # print('ssl._DEFAULT_CIPHERS', ssl._DEFAULT_CIPHERS)

        session = requests.session()
        adapter = TlsAdapterWeakCiphers(protocol_version)

        session.mount(url, adapter)

    except ssl.SSLError as sslex:
        # print('### No weak cipher support on your machine, unable to test: {0} ###'.format(
        #    WEAK_CIPHERS))
        return (False, 'weak_cipher SSLError {0}'.format(sslex))

    try:
        allow_redirects = False

        headers = {'user-agent': useragent}
        a = session.get(url, verify=False, allow_redirects=allow_redirects,
                        headers=headers, timeout=request_timeout)

        if a.status_code == 200 or a.status_code == 301 or a.status_code == 302 or a.status_code == 404:
            # print('is ok')
            return (True, 'is ok')

        resulted_in_html = '<html' in a.text

        # if resulted_in_html:
        #    print('has html')
        # else:
        #    print('no html')
        return (resulted_in_html, 'has <html tag in result')
    except ssl.SSLCertVerificationError as sslcertex:
        # print('weak_cipher SSLCertVerificationError', sslcertex)
        return (True, 'weak_cipher SSLCertVerificationError: {0}'.format(sslcertex))
    except ssl.SSLError as sslex:
        # print('error has_weak_cipher SSLError1', sslex)
        return (False, 'weak_cipher SSLError {0}'.format(sslex))
    except ConnectionResetError as resetex:
        # print('error ConnectionResetError', resetex)
        return (False, 'weak_cipher ConnectionResetError {0}'.format(resetex))
    except requests.exceptions.SSLError as sslerror:
        # print('error weak_cipher SSLError2', sslerror)
        return (False, 'Unable to verify: SSL error occured')
    except requests.exceptions.ConnectionError as conex:
        # print('error weak_cipher ConnectionError', conex)
        return (False, 'Unable to verify: connection error occured')
    except Exception as exception:
        # print('weak_cipher test', exception)
        return (False, 'weak_cipher Exception {0}'.format(exception))


# Read post at: https://hussainaliakbar.github.io/restricting-tls-version-and-cipher-suites-in-python-requests-and-testing-wireshark/
INSECURE_CIPHERS = (
    'RSA+RC4+MD5:'
    'RSA+RC4128+MD5:'
    'RSA+RC4+SHA:'
    'RSA+RC4128+SHA:'
    'ECDHE+RSA+RC4+SHA:'
    'ECDHE+RSA+RC4+SHA:'
    'ECDHE+RSA+RC4128+MD5:'
    'ECDHE+RSA+RC4128+MD5:'
)


class TlsAdapterInsecureCiphers(HTTPAdapter):

    def __init__(self, ssl_options=0, **kwargs):
        self.ssl_options = ssl_options
        super(TlsAdapterInsecureCiphers, self).__init__(**kwargs)

    def init_poolmanager(self, *pool_args, **pool_kwargs):
        ctx = ssl_.create_urllib3_context(
            ciphers=INSECURE_CIPHERS,
            cert_reqs=ssl.CERT_REQUIRED, options=self.ssl_options)

        self.poolmanager = PoolManager(*pool_args,
                                       ssl_context=ctx,
                                       **pool_kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = ssl_.create_urllib3_context(ciphers=INSECURE_CIPHERS)
        kwargs['ssl_context'] = context
        return super(TlsAdapterInsecureCiphers, self).proxy_manager_for(*args, **kwargs)


def has_insecure_cipher(url, protocol_version):
    session = False

    try:
        # print('ssl._DEFAULT_CIPHERS', ssl._DEFAULT_CIPHERS)

        session = requests.session()
        adapter = TlsAdapterInsecureCiphers(protocol_version)

        session.mount(url, adapter)

    except ssl.SSLError as sslex:
        # print('### No weak cipher support on your machine, unable to test: {0} ###'.format(
        #    WEAK_CIPHERS))
        return (False, 'insecure_cipher SSLError {0}'.format(sslex))

    try:
        allow_redirects = False

        headers = {'user-agent': useragent}
        a = session.get(url, verify=False, allow_redirects=allow_redirects,
                        headers=headers, timeout=request_timeout)

        if a.status_code == 200 or a.status_code == 301 or a.status_code == 302 or a.status_code == 404:
            # print('is ok')
            return (True, 'is ok')

        resulted_in_html = '<html' in a.text

        # if resulted_in_html:
        #    print('has html')
        # else:
        #    print('no html')
        return (resulted_in_html, 'has <html tag in result')
    except ssl.SSLCertVerificationError as sslcertex:
        # print('weak_cipher SSLCertVerificationError', sslcertex)
        return (True, 'insecure_cipher SSLCertVerificationError: {0}'.format(sslcertex))
    except ssl.SSLError as sslex:
        # print('error has_weak_cipher SSLError1', sslex)
        return (False, 'insecure_cipher SSLError {0}'.format(sslex))
    except ConnectionResetError as resetex:
        # print('error ConnectionResetError', resetex)
        return (False, 'insecure_cipher ConnectionResetError {0}'.format(resetex))
    except requests.exceptions.SSLError as sslerror:
        # print('error weak_cipher SSLError2', sslerror)
        return (False, 'Unable to verify: SSL error occured')
    except requests.exceptions.ConnectionError as conex:
        # print('error weak_cipher ConnectionError', conex)
        return (False, 'Unable to verify: connection error occured')
    except Exception as exception:
        # print('weak_cipher test', exception)
        return (False, 'insecure_cipher Exception {0}'.format(exception))


class TlsAdapterCertRequired(HTTPAdapter):

    def __init__(self, ssl_options=0, **kwargs):
        self.ssl_options = ssl_options
        super(TlsAdapterCertRequired, self).__init__(**kwargs)

    def init_poolmanager(self, *pool_args, **pool_kwargs):
        ctx = ssl_.create_urllib3_context(
            cert_reqs=ssl.CERT_REQUIRED, options=self.ssl_options)

        self.poolmanager = PoolManager(*pool_args,
                                       ssl_context=ctx,
                                       **pool_kwargs)


class TlsAdapterNoCert(HTTPAdapter):

    def __init__(self, ssl_options=0, **kwargs):
        self.ssl_options = ssl_options
        super(TlsAdapterNoCert, self).__init__(**kwargs)

    def init_poolmanager(self, *pool_args, **pool_kwargs):
        ctx = ssl_.create_urllib3_context(
            cert_reqs=ssl.CERT_NONE,
            options=self.ssl_options)

        self.poolmanager = PoolManager(*pool_args,
                                       ssl_context=ctx,
                                       **pool_kwargs)


def has_protocol_version(url, validate_hostname, protocol_version):
    session = requests.session()
    if validate_hostname:
        adapter = TlsAdapterCertRequired(protocol_version)
    else:
        adapter = TlsAdapterNoCert(protocol_version)

    session.mount("https://", adapter)

    try:
        allow_redirects = False

        headers = {'user-agent': useragent}
        session.get(url, verify=validate_hostname, allow_redirects=allow_redirects,
                        headers=headers, timeout=request_timeout)

        return (True, 'is ok')

    except ssl.SSLCertVerificationError as sslcertex:
        # print('protocol version SSLCertVerificationError', sslcertex)
        if validate_hostname:
            return (True, 'protocol version SSLCertVerificationError: {0}'.format(sslcertex))
        else:
            return (False, 'protocol version SSLCertVerificationError: {0}'.format(sslcertex))
    except ssl.SSLError as sslex:
        # print('protocol version SSLError', sslex)
        return (False, 'protocol version SSLError: {0}'.format(sslex))
    except ssl.SSLCertVerificationError as sslcertex:
        # print('protocol version SSLCertVerificationError', sslcertex)
        return (True, 'protocol version SSLCertVerificationError: {0}'.format(sslcertex))
    except ssl.SSLError as sslex:
        # print('error protocol version ', sslex)
        return (False, 'protocol version SSLError {0}'.format(sslex))
    except ConnectionResetError as resetex:
        # print('error protocol version  ConnectionResetError', resetex)
        return (False, 'protocol version  ConnectionResetError {0}'.format(resetex))
    except requests.exceptions.SSLError as sslerror:
        # print('error protocol version  SSLError', sslerror)
        return (False, 'Unable to verify: SSL error occured')
    except requests.exceptions.ConnectionError as conex:
        # print('error protocol version  ConnectionError', conex)
        return (False, 'Unable to verify: connection error occured')
    except Exception as exception:
        # print('protocol version  test', exception)
        return (False, 'protocol version  Exception {0}'.format(exception))
