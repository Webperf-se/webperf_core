# -*- coding: utf-8 -*-
import re
from bs4 import BeautifulSoup
import smtplib
import datetime
import socket
import ipaddress
import sys
import urllib.parse
import datetime
import time
# https://docs.python.org/3/library/urllib.parse.html
import urllib
import config
from models import Rating
from tests.utils import dns_lookup, get_best_country_code, httpRequestGetContent, is_country_code_in_eu_or_on_exception_list
import gettext
_local = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
review_show_improvements_only = config.review_show_improvements_only

checked_urls = {}

# We are doing this to support IPv6


class SMTP_WEBPERF(smtplib.SMTP):
    def __init__(self, host='', port=0, local_hostname=None,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
                 source_address=None):
        """Initialize a new instance.

        If specified, `host` is the name of the remote host to which to
        connect.  If specified, `port` specifies the port to which to connect.
        By default, smtplib.SMTP_PORT is used.  If a host is specified the
        connect method is called, and if it returns anything other than a
        success code an SMTPConnectError is raised.  If specified,
        `local_hostname` is used as the FQDN of the local host in the HELO/EHLO
        command.  Otherwise, the local hostname is found using
        socket.getfqdn(). The `source_address` parameter takes a 2-tuple (host,
        port) for the socket to bind to as its source address before
        connecting. If the host is '' and port is 0, the OS default behavior
        will be used.

        """
        self._host = host
        self.timeout = timeout
        self.esmtp_features = {}
        self.command_encoding = 'ascii'
        self.source_address = source_address
        self._auth_challenge_count = 0
        self.local_hostname = local_hostname

        if host:
            (code, msg) = self.connect(host, port)
            if code != 220:
                self.close()
                raise smtplib.SMTPConnectError(code, msg)

    def connect(self, host='localhost', port=0, source_address=None):
        """Connect to a host on a given port.

        If the hostname ends with a colon (`:') followed by a number, and
        there is no port specified, that suffix will be stripped off and the
        number interpreted as the port number to use. When using an IPv6 literal
        address, the port must be passed as a seperate parameter.

        Note: This method is automatically invoked by __init__, if a host is
        specified during instantiation.

        """

        if source_address:
            self.source_address = source_address

        if not port and (host.find(':') == host.rfind(':')):
            i = host.rfind(':')
            if i >= 0:
                host, port = host[:i], host[i + 1:]
                try:
                    port = int(port)
                except ValueError:
                    raise OSError("nonnumeric port")
        if not port:
            port = self.default_port
        sys.audit("smtplib.connect", self, host, port)

        print("_GET_SOCKET:", host, port)

        self.sock = self._get_socket(host, port, self.timeout)
        self.file = None

        print("GETREPLY")

        (code, msg) = self.getreply()

        print("DEBUGLEVEL", self.debuglevel)

        if self.debuglevel > 0:
            self._print_debug('connect:', repr(msg))

        print("LOCAL_HOSTNAME", self.local_hostname)

        if self.local_hostname is None:
            # RFC 2821 says we should use the fqdn in the EHLO/HELO verb, and
            # if that can't be calculated, that we should use a domain literal
            # instead (essentially an encoded IP address like [A.B.C.D]) or
            # [IPv6:XXXX:XXXX:XXXX:XXXX:XXXX:XXXX:XXXX:XXXX].
            try:
                name = socket.getnameinfo(self.sock.getsockname(), 0)
                if self.sock.family == socket.AF_INET:
                    self.local_hostname = '[%s]' % name[0]
                elif self.sock_family == socket.AF_INET6:
                    self.local_hostname = '[IPv6:%s]' % name[0]
                else:
                    if self.debuglevel > 0:
                        print>>sys.stderr, "Unknown address family in SMTP socket"
            except socket.gaierror as e:
                if self.debuglevel > 0:
                    print>>sys.stderr, "Error while resolving hostname: ", e.string()
                pass
        return (code, msg)


def run_test(_, langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    # rating = Rating(_, review_show_improvements_only)
    result_dict = {}

    language = gettext.translation(
        'email_validator', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    rating, result_dict = validate_email_domain(
        hostname, result_dict, _, _local)
    if rating.get_overall() == -1.0:
        # NO MX record found for domain, look for e-mail on website for alternative e-mail domain.
        content = httpRequestGetContent(url, True)
        time.sleep(1)
        result = search_for_email_domain(content)
        if result == None:
            interesting_urls = get_interesting_urls(content, url, 0)
            for interesting_url in interesting_urls:
                content = httpRequestGetContent(interesting_url, True)
                result = search_for_email_domain(content)
                if result != None:
                    break
                time.sleep(1)

        if result != None:
            rating, result_dict = validate_email_domain(
                result, result_dict, _, _local)
            rating.overall_review = _local('TEXT_REVIEW_MX_ALTERATIVE').format(
                result, rating.overall_review)

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)


def search_for_email_domain(content):
    content_match = re.search(
        r"[\"']mailto:(?P<email>[^\"']+)\"", content)

    if content_match == None:
        return None

    email = content_match.group('email')
    domain_match = re.search(r'@(?P<domain>.*)', email)
    if domain_match == None:
        return None

    domain = domain_match.group('domain')
    if domain == None:
        return None

    domain = domain.lower().strip()

    # Ignore imy.se in text as it can be related to GDPR texts
    if 'imy.se' == domain:
        return None
    # Ignore digg.se in text as it can be related to WCAG texts
    if 'digg.se' == domain:
        return None

    return domain


def get_interesting_urls(content, org_url_start, depth):
    urls = {}

    soup = BeautifulSoup(content, 'lxml')
    links = soup.find_all("a")

    for link in links:
        if not link.find(string=re.compile(
                r"(kontakt(a [a-z]+){0,1}|om [a-z]+|personuppgifter|(tillg(.{1,6}|ä|&auml;|&#228;)nglighet(sredog(.{1,6}|ö|&ouml;|&#246;)relse){0,1}))", flags=re.MULTILINE | re.IGNORECASE)):
            continue

        url = '{0}'.format(link.get('href'))

        if url == None:
            continue
        elif url.endswith('.pdf'):
            continue
        elif url.startswith('//'):
            continue
        elif url.startswith('/'):
            url = '{0}{1}'.format(org_url_start, url)
        elif url.startswith('#'):
            continue

        if not url.startswith(org_url_start):
            continue

        text = link.get_text().strip()

        precision = 0.0
        if re.match(r'^[ \t\r\n]*kontakt', text, flags=re.MULTILINE | re.IGNORECASE) != None:
            precision = 0.66
        if re.match(r'^[ \t\r\n]*kontakta oss', text, flags=re.MULTILINE | re.IGNORECASE) != None:
            precision = 0.65
        if re.match(r'^[ \t\r\n]*kontakta [a-z]+', text, flags=re.MULTILINE | re.IGNORECASE) != None:
            precision = 0.60
        if re.match(r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse$', text, flags=re.MULTILINE | re.IGNORECASE) != None:
            precision = 0.55
        elif re.match(r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog(.{1,6}|ö|&ouml;|&#246;)relse', text, flags=re.MULTILINE | re.IGNORECASE) != None:
            precision = 0.5
        elif re.match(r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighet$', text, flags=re.MULTILINE | re.IGNORECASE) != None:
            precision = 0.4
        elif re.match(r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighet', text, flags=re.MULTILINE | re.IGNORECASE) != None:
            precision = 0.35
        if re.match(r'^[ \t\r\n]*personuppgifter', text, flags=re.MULTILINE | re.IGNORECASE) != None:
            precision = 0.32
        elif re.match(r'tillg(.{1,6}|ä|&auml;|&#228;)nglighet', text, flags=re.MULTILINE | re.IGNORECASE) != None:
            precision = 0.3
        elif re.search(r'om webbplats', text, flags=re.MULTILINE | re.IGNORECASE) != None:
            precision = 0.29
        elif re.match(r'^[ \t\r\n]*om [a-z]+$', text, flags=re.MULTILINE | re.IGNORECASE) != None:
            precision = 0.25
        elif re.match(r'^[ \t\r\n]*om [a-z]+', text, flags=re.MULTILINE | re.IGNORECASE) != None:
            precision = 0.2
        else:
            precision = 0.1

        info = get_default_info(
            url, text, 'url.text', precision, depth)
        if url not in checked_urls:
            urls[url] = info

    if len(urls) > 0:
        tmp = sorted(urls.items(), key=get_sort_on_precision)
        # Take top 10
        tmp = tmp[:10]
        urls = dict(tmp)

        return urls
    return urls


def get_sort_on_precision(item):
    return item[1]["precision"]


def get_default_info(url, text, method, precision, depth):
    result = {}

    if text != None:
        text = text.lower().strip('.').strip('-').strip()

    result['url'] = url
    result['method'] = method
    result['precision'] = precision
    result['text'] = text
    result['depth'] = depth

    return result


def validate_email_domain(hostname, result_dict, _, _local):
    rating = Rating(_, review_show_improvements_only)
    result_dict = {}
    # We must take in consideration "www." subdomains...
    if hostname.startswith('www.'):
        hostname = hostname[4:]

    # 0.0 - Preflight (Will probably resolve 98% of questions from people trying this test themself)
    # 0.1 - Check for allowed connection over port 25 (most consumer ISP don't allow this)
    support_port25 = False
    # 0.2 - Check for allowed IPv6 support (GitHub Actions doesn't support it on network lever on the time of writing this)
    support_IPv6 = False

    # 1 - Get Email servers
    # dns_lookup
    rating, ipv4_servers, ipv6_servers = Validate_MX_Records(
        _, rating, result_dict, _local, hostname)

    # If we have -1.0 in rating, we have no MX records, ignore test.
    if rating.get_overall() != -1.0:
        # 1.2 - Check operational
        if support_port25 and len(ipv4_servers) > 0:
            rating = Validate_IPv4_Operation_Status(
                _, rating, _local, ipv4_servers)

        # 1.2 - Check operational
        if support_port25 and support_IPv6 and len(ipv6_servers) > 0:
            rating = Validate_IPv6_Operation_Status(
                _, rating, _local, ipv6_servers)

        # 1.4 - Check TLS
        # 1.5 - Check PKI
        # 1.6 - Check DNSSEC
        # 1.7 - Check DANE
        # 1.8 - Check MTA-STS policy
        rating = Validate_MTA_STS_Policy(_, rating, _local, hostname)
        # 1.9 - Check SPF policy
        rating = Validate_SPF_Policies(
            _, rating, result_dict, _local, hostname)

    return rating, result_dict


def Validate_MTA_STS_Policy(_, rating, _local, hostname):
    has_mta_sts_policy = False
    # https://www.rfc-editor.org/rfc/rfc8461#section-3.1
    mta_sts_results = dns_lookup('_mta-sts.' + hostname, 'TXT')
    for result in mta_sts_results:
        if 'v=STSv1;' in result:
            has_mta_sts_policy = True

    has_mta_sts_records_rating = Rating(_, review_show_improvements_only)
    if has_mta_sts_policy:
        has_mta_sts_records_rating.set_overall(5.0)
        has_mta_sts_records_rating.set_integrity_and_security(
            5.0, _local('TEXT_REVIEW_MTA_STS_DNS_RECORD_SUPPORT'))
        has_mta_sts_records_rating.set_standards(
            5.0, _local('TEXT_REVIEW_MTA_STS_DNS_RECORD_SUPPORT'))
    else:
        has_mta_sts_records_rating.set_overall(1.0)
        has_mta_sts_records_rating.set_integrity_and_security(
            1.0, _local('TEXT_REVIEW_MTA_STS_DNS_RECORD_NO_SUPPORT'))
        has_mta_sts_records_rating.set_standards(
            1.0, _local('TEXT_REVIEW_MTA_STS_DNS_RECORD_NO_SUPPORT'))
    rating += has_mta_sts_records_rating

    # https://mta-sts.example.com/.well-known/mta-sts.txt
    content = httpRequestGetContent(
        "https://mta-sts.{0}/.well-known/mta-sts.txt".format(hostname))

    has_mta_sts_txt_rating = Rating(_, review_show_improvements_only)
    # https://www.rfc-editor.org/rfc/rfc8461#section-3.2
    if 'STSv1' in content:

        # version: STSv1
        # mode: enforce
        # mx: mail1.polisen.se
        # mx: mail2.polisen.se
        # max_age: 604800

        is_valid = True
        has_version = False
        has_mode = False
        has_mx = False
        has_max_age = False

        # print('content:', content.replace(
        #     '\r\n', '\\r\\n\r\n').replace('\n', '\\n\r\n'))

        rows = content.split('\r\n')
        if len(rows) == 1:
            rows = content.split('\n')
            if len(rows) > 1:
                # https://www.rfc-editor.org/rfc/rfc8461#section-3.2
                mta_sts_records_wrong_linebreak_rating = Rating(
                    _, review_show_improvements_only)
                mta_sts_records_wrong_linebreak_rating.set_overall(1.0)
                mta_sts_records_wrong_linebreak_rating.set_integrity_and_security(
                    2.5, _local('TEXT_REVIEW_MTA_STS_DNS_RECORD_WRONG_LINEBREAK'))
                mta_sts_records_wrong_linebreak_rating.set_standards(
                    1.0, _local('TEXT_REVIEW_MTA_STS_DNS_RECORD_WRONG_LINEBREAK'))
                rating += mta_sts_records_wrong_linebreak_rating

        for row in rows:
            if row == '':
                continue
            key_value_pair = row.split(':')
            if len(key_value_pair) != 2:
                print('invalid pair:', key_value_pair)
                is_valid = False
                continue

            key = key_value_pair[0].strip(' ')
            value = key_value_pair[1].strip(' ')

            if 'version' in key:
                has_version = True
            elif 'mode' in key:
                if value == 'enforce':
                    a = 1
                elif value == 'testing' or value == 'none':
                    mta_sts_records_not_enforced_rating = Rating(
                        _, review_show_improvements_only)
                    mta_sts_records_not_enforced_rating.set_overall(3.0)
                    mta_sts_records_not_enforced_rating.set_integrity_and_security(
                        1.0, _local('TEXT_REVIEW_MTA_STS_DNS_RECORD_NOT_ENFORCED'))
                    mta_sts_records_not_enforced_rating.set_standards(
                        5.0, _local('TEXT_REVIEW_MTA_STS_DNS_RECORD_VALID_MODE'))
                    rating += mta_sts_records_not_enforced_rating
                else:
                    mta_sts_records_invalid_mode_rating = Rating(
                        _, review_show_improvements_only)
                    mta_sts_records_invalid_mode_rating.set_overall(1.0)
                    mta_sts_records_invalid_mode_rating.set_integrity_and_security(
                        1.0, _local('TEXT_REVIEW_MTA_STS_DNS_RECORD_INVALID_MODE'))
                    mta_sts_records_invalid_mode_rating.set_standards(
                        1.0, _local('TEXT_REVIEW_MTA_STS_DNS_RECORD_INVALID_MODE'))
                    rating += mta_sts_records_invalid_mode_rating

                has_mode = True
            elif 'mx' in key:
                has_mx = True
            elif 'max_age' in key:
                has_max_age = True
            else:
                print('invalid key:', key)
                is_valid = False

        is_valid = is_valid and has_version and has_mode and has_mx and has_max_age

        if is_valid:
            has_mta_sts_txt_rating.set_overall(5.0)
            has_mta_sts_txt_rating.set_integrity_and_security(
                5.0, _local('TEXT_REVIEW_MTA_STS_TXT_SUPPORT'))
            has_mta_sts_txt_rating.set_standards(
                5.0, _local('TEXT_REVIEW_MTA_STS_TXT_SUPPORT'))
        else:
            has_mta_sts_txt_rating.set_overall(2.0)
            has_mta_sts_txt_rating.set_integrity_and_security(
                1.0, _local('TEXT_REVIEW_MTA_STS_TXT_INVALID_FORMAT'))
            has_mta_sts_txt_rating.set_standards(
                1.0, _local('TEXT_REVIEW_MTA_STS_TXT_INVALID_FORMAT'))

    else:
        has_mta_sts_txt_rating.set_overall(1.0)
        has_mta_sts_txt_rating.set_integrity_and_security(
            1.0, _local('TEXT_REVIEW_MTA_STS_TXT_NO_SUPPORT'))
        has_mta_sts_txt_rating.set_standards(
            1.0, _local('TEXT_REVIEW_MTA_STS_TXT_NO_SUPPORT'))
    rating += has_mta_sts_txt_rating
    return rating


def Validate_SPF_Policies(_, rating, result_dict, _local, hostname):
    spf_result_dict = Validate_SPF_Policy(_, _local, hostname, result_dict)
    result_dict.update(spf_result_dict)

    rating = Rate_has_SPF_Policies(_, rating, result_dict, _local)
    rating = Rate_Invalid_format_SPF_Policies(_, rating, result_dict, _local)
    rating = Rate_Too_many_DNS_lookup_for_SPF_Policies(
        _, rating, result_dict, _local)
    rating = Rate_Use_of_PTR_for_SPF_Policies(_, rating, result_dict, _local)

    rating = Rate_Fail_Configuration_for_SPF_Policies(
        _, rating, result_dict, _local)

    rating = Rate_GDPR_for_SPF_Policies(_, rating, result_dict, _local)

    return rating


def Rate_Use_of_PTR_for_SPF_Policies(_, rating, result_dict, _local):
    if 'spf-uses-ptr' in result_dict:
        has_spf_record_ptr_being_used_rating = Rating(
            _, review_show_improvements_only)
        has_spf_record_ptr_being_used_rating.set_overall(1.0)
        has_spf_record_ptr_being_used_rating.set_standards(
            1.0, _local('TEXT_REVIEW_SPF_DNS_RECORD_PTR_USED'))
        rating += has_spf_record_ptr_being_used_rating

    return rating


def Rate_Fail_Configuration_for_SPF_Policies(_, rating, result_dict, _local):
    if 'spf-uses-ignorefail' in result_dict:
        has_spf_ignore_records_rating = Rating(
            _, review_show_improvements_only)
        has_spf_ignore_records_rating.set_overall(2.0)
        has_spf_ignore_records_rating.set_integrity_and_security(
            1.0, _local('TEXT_REVIEW_SPF_DNS_IGNORE_RECORD_NO_SUPPORT'))
        has_spf_ignore_records_rating.set_standards(
            2.5, _local('TEXT_REVIEW_SPF_DNS_IGNORE_RECORD_NO_SUPPORT'))
        rating += has_spf_ignore_records_rating

    if 'spf-uses-neutralfail' in result_dict:
        has_spf_dns_record_neutralfail_records_rating = Rating(
            _, review_show_improvements_only)
        has_spf_dns_record_neutralfail_records_rating.set_overall(
            3.0)
        has_spf_dns_record_neutralfail_records_rating.set_integrity_and_security(
            2.0, _local('TEXT_REVIEW_SPF_DNS_NEUTRALFAIL_RECORD'))
        has_spf_dns_record_neutralfail_records_rating.set_standards(
            5.0, _local('TEXT_REVIEW_SPF_DNS_NEUTRALFAIL_RECORD'))
        rating += has_spf_dns_record_neutralfail_records_rating

    if 'spf-uses-softfail' in result_dict:
        has_spf_dns_record_softfail_records_rating = Rating(
            _, review_show_improvements_only)
        has_spf_dns_record_softfail_records_rating.set_overall(5.0)
        has_spf_dns_record_softfail_records_rating.set_integrity_and_security(
            2.0, _local('TEXT_REVIEW_SPF_DNS_SOFTFAIL_RECORD'))
        has_spf_dns_record_softfail_records_rating.set_standards(
            5.0, _local('TEXT_REVIEW_SPF_DNS_SOFTFAIL_RECORD'))
        rating += has_spf_dns_record_softfail_records_rating

    if 'spf-uses-hardfail' in result_dict:
        has_spf_dns_record_hardfail_records_rating = Rating(
            _, review_show_improvements_only)
        has_spf_dns_record_hardfail_records_rating.set_overall(5.0)
        has_spf_dns_record_hardfail_records_rating.set_integrity_and_security(
            5.0, _local('TEXT_REVIEW_SPF_DNS_HARDFAIL_RECORD'))
        has_spf_dns_record_hardfail_records_rating.set_standards(
            5.0, _local('TEXT_REVIEW_SPF_DNS_HARDFAIL_RECORD'))
        rating += has_spf_dns_record_hardfail_records_rating
    return rating


def Rate_Invalid_format_SPF_Policies(_, rating, result_dict, _local):
    if 'spf-uses-none-standard' in result_dict:
        has_spf_unknown_section_rating = Rating(
            _, review_show_improvements_only)
        has_spf_unknown_section_rating.set_overall(1.0)
        has_spf_unknown_section_rating.set_standards(
            1.0, _local('TEXT_REVIEW_SPF_UNKNOWN_SECTION'))
        rating += has_spf_unknown_section_rating

    if 'spf-error-double-space' in result_dict:
        has_spf_dns_record_double_space_rating = Rating(
            _, review_show_improvements_only)
        has_spf_dns_record_double_space_rating.set_overall(
            1.5)
        has_spf_dns_record_double_space_rating.set_standards(
            1.5, _local('TEXT_REVIEW_SPF_DNS_DOUBLE_SPACE_RECORD'))
        rating += has_spf_dns_record_double_space_rating
    return rating


def Rate_has_SPF_Policies(_, rating, result_dict, _local):
    has_spf_records_rating = Rating(_, review_show_improvements_only)
    if 'spf-has-policy' in result_dict:
        txt = _local('TEXT_REVIEW_SPF_DNS_RECORD_SUPPORT')
        has_spf_records_rating.set_overall(5.0)
        has_spf_records_rating.set_integrity_and_security(
            5.0, txt)
        has_spf_records_rating.set_standards(
            5.0, txt)
    else:
        txt = _local('TEXT_REVIEW_SPF_DNS_RECORD_NO_SUPPORT')
        has_spf_records_rating.set_overall(1.0)
        has_spf_records_rating.set_integrity_and_security(
            1.0, txt)
        has_spf_records_rating.set_standards(
            1.0, txt)
    rating += has_spf_records_rating
    return rating


def Rate_Too_many_DNS_lookup_for_SPF_Policies(_, rating, result_dict, _local):
    if 'spf-error-to-many-dns-lookups' in result_dict:
        to_many_spf_dns_lookups_rating = Rating(
            _, review_show_improvements_only)
        to_many_spf_dns_lookups_rating.set_overall(1.0)
        to_many_spf_dns_lookups_rating.set_standards(
            1.0, _local('TEXT_REVIEW_SPF_TO_MANY_DNS_LOOKUPS'))
        to_many_spf_dns_lookups_rating.set_performance(
            4.0, _local('TEXT_REVIEW_SPF_TO_MANY_DNS_LOOKUPS'))
        rating += to_many_spf_dns_lookups_rating
    return rating


def Rate_GDPR_for_SPF_Policies(_, rating, result_dict, _local):
    spf_addresses = list()
    if 'spf-ipv4' not in result_dict:
        result_dict['spf-ipv4'] = list()
    if 'spf-ipv6' not in result_dict:
        result_dict['spf-ipv6'] = list()
    spf_addresses.extend(result_dict['spf-ipv4'])
    spf_addresses.extend(result_dict['spf-ipv6'])

    # 2.0 - Check GDPR for all IP-adresses
    replace_network_with_first_and_last_ipaddress(spf_addresses)

    countries_others = {}
    countries_eu_or_exception_list = {}

    for ip_address in spf_addresses:
        country_code = ''
        country_code = get_best_country_code(
            ip_address, country_code)
        if country_code == '' or country_code == '-':
            country_code = 'unknown'

        if is_country_code_in_eu_or_on_exception_list(country_code):
            if country_code in countries_eu_or_exception_list:
                countries_eu_or_exception_list[
                    country_code] = countries_eu_or_exception_list[country_code] + 1
            else:
                countries_eu_or_exception_list[country_code] = 1
        else:
            if country_code in countries_others:
                countries_others[country_code] = countries_others[country_code] + 1
            else:
                countries_others[country_code] = 1

    nof_gdpr_countries = len(countries_eu_or_exception_list)
    nof_none_gdpr_countries = len(countries_others)
    if nof_gdpr_countries > 0:
        gdpr_rating = Rating(_, review_show_improvements_only)
        gdpr_rating.set_overall(5.0)
        gdpr_rating.set_integrity_and_security(
            5.0, _local('TEXT_REVIEW_SPF_GDPR').format(', '.join(countries_eu_or_exception_list.keys())))
        rating += gdpr_rating
    if nof_none_gdpr_countries > 0:
        none_gdpr_rating = Rating(_, review_show_improvements_only)
        none_gdpr_rating.set_overall(1.0)
        none_gdpr_rating.set_integrity_and_security(
            1.0, _local('TEXT_REVIEW_SPF_NONE_GDPR').format(', '.join(countries_others.keys())))
        rating += none_gdpr_rating
    return rating


def Validate_SPF_Policy(_, _local, hostname, result_dict):
    # https://proton.me/support/anti-spoofing-custom-domain

    if 'spf-dns-lookup-count' in result_dict and result_dict['spf-dns-lookup-count'] >= 10:
        result_dict['spf-error-to-many-dns-lookups'] = True
        return result_dict

    if 'spf-dns-lookup-count' not in result_dict:
        result_dict['spf-dns-lookup-count'] = 1
    else:
        result_dict['spf-dns-lookup-count'] = result_dict['spf-dns-lookup-count'] + 1

    spf_results = dns_lookup(hostname, 'TXT')
    spf_content = ''

    for result in spf_results:
        if 'v=spf1 ' in result:
            result_dict['spf-has-policy'] = True
            spf_content = result
            # print('content:', spf_content.replace(
            #     '\r\n', '\\r\\n\r\n').replace(' ', '#'))

    if 'spf-has-policy' in result_dict:
        try:
            # https://www.rfc-editor.org/rfc/rfc7208#section-9.1
            spf_sections = spf_content.split(' ')

            # http://www.open-spf.org/SPF_Record_Syntax/
            for section in spf_sections:
                if section == '':
                    result_dict['spf-error-double-space'] = True
                    continue

                # print('section:', section)
                if section.startswith('ip4:'):
                    data = section[4:]
                    if 'spf-ipv4' not in result_dict:
                        result_dict['spf-ipv4'] = list()
                    result_dict['spf-ipv4'].append(data)
                elif section.startswith('ip6:'):
                    data = section[4:]
                    if 'spf-ipv6' not in result_dict:
                        result_dict['spf-ipv6'] = list()
                    result_dict['spf-ipv6'].append(data)
                elif section.startswith('include:') or section.startswith('+include:'):
                    spf_domain = section[8:]
                    subresult_dict = Validate_SPF_Policy(
                        _, _local, spf_domain, result_dict)
                    result_dict.update(subresult_dict)
                elif section.startswith('?all'):
                    # What do this do and should we rate on it?
                    result_dict['spf-uses-neutralfail'] = True
                elif section.startswith('~all'):
                    # add support for SoftFail
                    result_dict['spf-uses-softfail'] = True
                elif section.startswith('-all'):
                    # add support for HardFail
                    result_dict['spf-uses-hardfail'] = True
                elif section.startswith('+all') or section.startswith('all'):
                    # basicly whitelist everything... Big fail
                    result_dict['spf-uses-ignorefail'] = True
                elif section.startswith('v=spf1'):
                    c = 1
                elif section.startswith('mx') or section.startswith('+mx'):
                    # TODO: What do this do and should we rate on it?
                    c = 1
                elif section.startswith('a') or section.startswith('+a'):
                    # TODO: What do this do and should we rate on it?
                    c = 1
                elif section.startswith('ptr') or section.startswith('+ptr'):
                    # What do this do and should we rate on it?
                    result_dict['spf-uses-ptr'] = True
                elif section.startswith('exists:'):
                    # TODO: What do this do and should we rate on it?
                    c = 1
                elif section.startswith('redirect='):
                    # TODO: What do this do and should we rate on it?
                    c = 1
                elif section.startswith('exp='):
                    # TODO: What do this do and should we rate on it?
                    c = 1
                else:
                    result_dict['spf-uses-none-standard'] = True
        except Exception as ex:
            print('ex C:', ex)

    return result_dict


def replace_network_with_first_and_last_ipaddress(spf_addresses):
    networs_to_remove = list()
    for ip_address in spf_addresses:
        # support for network mask
        if '/' in ip_address:
            network = False
            if ':' in ip_address:
                network = ipaddress.IPv6Network(ip_address, False)
            else:
                network = ipaddress.IPv4Network(ip_address, False)

            num_addresses = network.num_addresses
            if num_addresses > 0:
                spf_addresses.append(network.__getitem__(0).__format__('s'))
            if num_addresses > 1:
                spf_addresses.append(network.__getitem__(
                    network.num_addresses - 1).__format__('s'))

            networs_to_remove.append(ip_address)

    # remove IP networks
    for ip_address in networs_to_remove:
        spf_addresses.remove(ip_address)


def Validate_IPv6_Operation_Status(_, rating, _local, ipv6_servers):
    ipv6_servers_operational = list()
    # 1.3 - Check Start TLS
    ipv6_servers_operational_starttls = list()
    for ip_address in ipv6_servers:
        try:
            # print('SMTP CONNECT:', ip_address)
            with SMTP_WEBPERF(ip_address, port=25, local_hostname=None, timeout=request_timeout) as smtp:
                ipv6_servers_operational.append(ip_address)
                smtp.starttls()
                ipv6_servers_operational_starttls.append(ip_address)
                # print('SMTP SUCCESS')
        except smtplib.SMTPConnectError as smtp_error:
            print('SMTP ERROR: ', smtp_error)
        except Exception as error:
            # If you get this error on all sites you test against, please verfiy that your provider is not blocking port 25.
            print('GENERAL ERROR: ', error)

    ipv6_operational_rating = Rating(_, review_show_improvements_only)
    if len(ipv6_servers_operational) > 0 and len(ipv6_servers) == len(ipv6_servers_operational):
        ipv6_operational_rating.set_overall(5.0)
        ipv6_operational_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IPV6_OPERATION_SUPPORT'))
    else:
        ipv6_operational_rating.set_overall(1.0)
        ipv6_operational_rating.set_standards(
            1.0, _local('TEXT_REVIEW_IPV6_OPERATION_NO_SUPPORT'))
    rating += ipv6_operational_rating

    ipv6_operational_rating = Rating(_, review_show_improvements_only)
    if len(ipv6_servers_operational_starttls) > 0 and len(ipv6_servers) == len(ipv6_servers_operational_starttls):
        ipv6_operational_rating.set_overall(5.0)
        ipv6_operational_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IPV6_OPERATION_STARTTLS_SUPPORT'))
    else:
        ipv6_operational_rating.set_overall(1.0)
        ipv6_operational_rating.set_standards(
            1.0, _local('TEXT_REVIEW_IPV6_OPERATION_STARTTLS_NO_SUPPORT'))
    rating += ipv6_operational_rating
    return rating


def Validate_IPv4_Operation_Status(_, rating, _local, ipv4_servers):
    ipv4_servers_operational = list()
    # 1.3 - Check Start TLS
    ipv4_servers_operational_starttls = list()
    for ip_address in ipv4_servers:
        try:
            # print('SMTP CONNECT:', ip_address)
            with SMTP_WEBPERF(ip_address, port=25, local_hostname=None, timeout=request_timeout) as smtp:
                ipv4_servers_operational.append(ip_address)
                smtp.starttls()
                ipv4_servers_operational_starttls.append(ip_address)
                # print('SMTP SUCCESS')
        except smtplib.SMTPConnectError as smtp_error:
            print('SMTP ERROR: ', smtp_error)
        except Exception as error:
            # If you get this error on all sites you test against, please verfiy that your provider is not blocking port 25.
            print('GENERAL ERROR: ', error)

    ipv4_operational_rating = Rating(_, review_show_improvements_only)
    if len(ipv4_servers_operational) > 0 and len(ipv4_servers) == len(ipv4_servers_operational):
        ipv4_operational_rating.set_overall(5.0)
        ipv4_operational_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IPV4_OPERATION_SUPPORT'))
    else:
        ipv4_operational_rating.set_overall(1.0)
        ipv4_operational_rating.set_standards(
            1.0, _local('TEXT_REVIEW_IPV4_OPERATION_NO_SUPPORT'))
    rating += ipv4_operational_rating

    ipv4_operational_rating = Rating(_, review_show_improvements_only)
    if len(ipv4_servers_operational_starttls) > 0 and len(ipv4_servers) == len(ipv4_servers_operational_starttls):
        ipv4_operational_rating.set_overall(5.0)
        ipv4_operational_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IPV4_OPERATION_STARTTLS_SUPPORT'))
    else:
        ipv4_operational_rating.set_overall(1.0)
        ipv4_operational_rating.set_standards(
            1.0, _local('TEXT_REVIEW_IPV4_OPERATION_STARTTLS_NO_SUPPORT'))
    rating += ipv4_operational_rating
    return rating


def Validate_MX_Records(_, rating, result_dict, _local, hostname):
    email_results = dns_lookup(hostname, "MX")
    has_mx_records_rating = Rating(_, review_show_improvements_only)

    email_servers = list()
    # 1.1 - Check IPv4 and IPv6 support
    ipv4_servers = list()
    ipv6_servers = list()
    email_entries = list()

    has_mx_records = len(email_results) > 0
    if not has_mx_records:
        return rating, ipv4_servers, ipv6_servers

    for email_result in email_results:
        # result is in format "<priority> <domain address/ip>"
        server_address = email_result.split(' ')[1]

        email_entries.append(server_address)
        ipv_4 = dns_lookup(server_address, "A")
        ipv_6 = dns_lookup(server_address, "AAAA")

        ipv4_servers.extend(ipv_4)
        ipv6_servers.extend(ipv_6)
        # print('IPv4:', ipv_4)
        # print('IPv6:', ipv_6)

    email_servers.extend(ipv4_servers)
    email_servers.extend(ipv6_servers)

    nof_ipv4_servers = len(ipv4_servers)
    nof_ipv4_rating = Rating(_, review_show_improvements_only)
    if nof_ipv4_servers >= 2:
        nof_ipv4_rating.set_overall(5.0)
        nof_ipv4_rating.set_integrity_and_security(
            5.0, _local('TEXT_REVIEW_IPV4_REDUNDANCE'))
        nof_ipv4_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IPV4_SUPPORT'))
    elif nof_ipv4_servers == 1:
        # example: feber.se (do dns lookup also before)
        nof_ipv4_rating.set_overall(2.5)
        nof_ipv4_rating.set_integrity_and_security(
            1.0, _local('TEXT_REVIEW_IPV4_NO_REDUNDANCE'))
        nof_ipv4_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IPV4_SUPPORT'))
    else:
        nof_ipv4_rating.set_overall(1.0)
        nof_ipv4_rating.set_standards(
            1.0, _local('TEXT_REVIEW_IPV4_NO_SUPPORT'))
    rating += nof_ipv4_rating

    nof_ipv6_servers = len(ipv6_servers)
    nof_ipv6_rating = Rating(_, review_show_improvements_only)
    if nof_ipv6_servers >= 2:
        nof_ipv6_rating.set_overall(5.0)
        nof_ipv6_rating.set_integrity_and_security(
            5.0, _local('TEXT_REVIEW_IPV6_REDUNDANCE'))
        nof_ipv6_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IPV6_SUPPORT'))
    elif nof_ipv6_servers == 1:
        # example: feber.se (do dns lookup also before)
        nof_ipv6_rating.set_overall(2.5)
        nof_ipv6_rating.set_integrity_and_security(
            1.0, _local('TEXT_REVIEW_IPV6_NO_REDUNDANCE'))
        nof_ipv6_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IPV6_SUPPORT'))
    else:
        # example: huddinge.se
        nof_ipv6_rating.set_overall(1.0)
        nof_ipv6_rating.set_standards(
            1.0, _local('TEXT_REVIEW_IPV6_NO_SUPPORT'))
    rating += nof_ipv6_rating

    # 2.0 - Check GDPR for all IP-adresses
    countries_others = {}
    countries_eu_or_exception_list = {}
    for ip_address in email_servers:
        country_code = ''
        country_code = get_best_country_code(
            ip_address, country_code)
        if country_code == '' or country_code == '-':
            country_code = 'unknown'

        if is_country_code_in_eu_or_on_exception_list(country_code):
            if country_code in countries_eu_or_exception_list:
                countries_eu_or_exception_list[
                    country_code] = countries_eu_or_exception_list[country_code] + 1
            else:
                countries_eu_or_exception_list[country_code] = 1
        else:
            if country_code in countries_others:
                countries_others[country_code] = countries_others[country_code] + 1
            else:
                countries_others[country_code] = 1

    nof_gdpr_countries = len(countries_eu_or_exception_list)
    nof_none_gdpr_countries = len(countries_others)
    if nof_gdpr_countries > 0:
        gdpr_rating = Rating(_, review_show_improvements_only)
        gdpr_rating.set_overall(5.0)
        gdpr_rating.set_integrity_and_security(
            5.0, _local('TEXT_REVIEW_MX_GDPR').format(', '.join(countries_eu_or_exception_list.keys())))
        rating += gdpr_rating
    if nof_none_gdpr_countries > 0:
        none_gdpr_rating = Rating(_, review_show_improvements_only)
        none_gdpr_rating.set_overall(1.0)
        none_gdpr_rating.set_integrity_and_security(
            1.0, _local('TEXT_REVIEW_MX_NONE_GDPR').format(', '.join(countries_others.keys())))
        rating += none_gdpr_rating

    # add data to result of test
    result_dict["mx-addresses"] = email_entries
    result_dict["mx-ipv4-servers"] = ipv4_servers
    result_dict["mx-ipv6-servers"] = ipv6_servers
    result_dict["mx-gdpr-countries"] = countries_eu_or_exception_list
    result_dict["mx-none-gdpr-countries"] = countries_others

    return rating, ipv4_servers, ipv6_servers
