# -*- coding: utf-8 -*-
# pylint: disable=too-many-lines
import re
import json
import smtplib
from datetime import datetime
import socket
import ipaddress
import sys
import urllib
import urllib.parse
import time
from bs4 import BeautifulSoup
import dns
from helpers.models import Rating
from tests.utils import dns_lookup, get_best_country_code, \
    get_http_content, get_translation, \
    is_country_code_in_eu_or_on_exception_list, get_root_url
from helpers.setting_helper import get_config

checked_urls = {}

# We are doing this to support IPv6
class SmtpWebperf(smtplib.SMTP): # pylint: disable=too-many-instance-attributes,missing-class-docstring
    def __init__(self, host='', port=0, local_hostname=None, # pylint: disable=too-many-arguments, super-init-not-called
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
                port = int(port)
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
                    self.local_hostname = f'[{name[0]}]'
                elif self.sock.family == socket.AF_INET6:
                    self.local_hostname = f'[IPv6:{name[0]}]'
                else:
                    if self.debuglevel > 0:
                        print("Unknown address family in SMTP socket")
            except socket.gaierror as e:
                if self.debuglevel > 0:
                    print("Error while resolving hostname: ", e.string())
        return (code, msg)


def run_test(global_translation, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    local_translation = get_translation(
            'email_validator',
            get_config('general.language')
        )

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    result_dict = {}
    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    rating, result_dict = validate_email_domain(
        hostname, result_dict, global_translation, local_translation)
    if rating.get_overall() == -1.0:
        # NO MX record found for domain, look for e-mail on website for alternative e-mail domain.
        content = get_http_content(url, True)
        time.sleep(1)
        result = search_for_email_domain(content)
        if result is None:
            interesting_urls = get_interesting_urls(content, url, 0)
            for interesting_url in interesting_urls:
                content = get_http_content(interesting_url, True)
                result = search_for_email_domain(content)
                if result is not None:
                    break
                time.sleep(1)

        if result is not None:
            rating, result_dict = validate_email_domain(
                result, result_dict, global_translation, local_translation)
            rating.overall_review = local_translation('TEXT_REVIEW_MX_ALTERATIVE').format(
                result, rating.overall_review)

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    reviews = rating.get_reviews()
    print(global_translation('TEXT_SITE_RATING'), rating)
    if get_config('general.review.show'):
        print(
            global_translation('TEXT_SITE_REVIEW'),
            reviews)

    if get_config('general.review.data'):
        nice_json_data = json.dumps(result_dict, indent=3)
        print(
            global_translation('TEXT_SITE_REVIEW_DATA'),
            f'```json\r\n{nice_json_data}\r\n```')

    return (rating, result_dict)


def search_for_email_domain(content):
    """
    Extracts the domain from an email address found in the given content.

    Parameters:
    content (str): The content to search for an email address.

    Returns:
    str: The domain of the found email address, or None if no valid email domain is found.
    """
    content_match = re.search(
        r"[\"' ]mailto:(?P<email>[^\"'\r\n\\]+)[\"'\r\n\\]", content)

    if content_match is None:
        return None

    email = content_match.group('email')
    domain_match = re.search(r'@(?P<domain>.*)', email)
    if domain_match is None:
        return None

    domain = domain_match.group('domain')
    if domain is None:
        return None

    domain = domain.lower().strip()

    # Ignore imy.se in text as it can be related to GDPR texts
    if 'imy.se' == domain:
        return None
    # Ignore digg.se in text as it can be related to WCAG texts
    if 'digg.se' == domain:
        return None

    return domain

def get_text_precision(text):
    """
    Determines the precision of a given text based on matching patterns.

    This function checks the input text against a list of predefined regex patterns. Each pattern is
    associated with a precision value. If the text matches a pattern, the corresponding precision
    value is returned.

    Parameters:
    text (str): The text to check for precision.

    Returns:
    float: The precision of the text. If no pattern matches, a default precision of 0.1 is returned.

    Note:
    The function uses regex for pattern matching.
    """
    patterns = [
        {
            'regex': r'^[ \t\r\n]*kontakt',
            'precision': 0.66
        },
        {
            'regex': r'^[ \t\r\n]*kontakta oss',
            'precision': 0.65
        },
        {
            'regex': r'^[ \t\r\n]*kontakta [a-z]+',
            'precision': 0.60
        },
        {
            'regex': (
                r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog'
                r'(.{1,6}|ö|&ouml;|&#246;)relse$'
            ),
            'precision': 0.55
        },
        {
            'regex': (
                r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighetsredog'
                r'(.{1,6}|ö|&ouml;|&#246;)relse'),
            'precision': 0.5
        },
        {
            'regex': r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighet$',
            'precision': 0.4
        },
        {
            'regex': r'^[ \t\r\n]*tillg(.{1,6}|ä|&auml;|&#228;)nglighet',
            'precision': 0.35
        },
        {
            'regex': r'^[ \t\r\n]*personuppgifter',
            'precision': 0.32
        },
        {
            'regex': r'tillg(.{1,6}|ä|&auml;|&#228;)nglighet',
            'precision': 0.30
        },
        {
            'regex': r'om webbplats',
            'precision': 0.29
        },
        {
            'regex': r'^[ \t\r\n]*om [a-z]+$',
            'precision': 0.25
        },
        {
            'regex': r'^[ \t\r\n]*om [a-z]+',
            'precision': 0.2
        }
    ]

    for pattern in patterns:
        if re.match(pattern['regex'], text, flags=re.MULTILINE | re.IGNORECASE) is not None:
            return pattern['precision']

    return 0.1


def get_interesting_urls(content, org_url_start, depth):
    """
    Extracts and processes URLs from the given HTML content.

    Parameters:
    content (str): The HTML content to extract URLs from.
    org_url_start (str): The original URL to be used as a base for relative URLs.
    depth (int): The depth value to be included in the result.

    Returns:
    dict: A dictionary where keys are URLs and
          values are dictionaries containing information about each URL.
    """
    urls = {}

    soup = BeautifulSoup(content, 'lxml')
    links = soup.find_all("a")

    for link in links:
        if not link.find(string=re.compile((
                    r"(kontakt(a [a-z]+){0,1}|om [a-z]+|personuppgifter|"
                    r"(tillg(.{1,6}|ä|&auml;|&#228;)nglighet"
                    r"(sredog(.{1,6}|ö|&ouml;|&#246;)relse){0,1}))"
                ), flags=re.MULTILINE | re.IGNORECASE)):
            continue

        url = f"{link.get('href')}"

        if url is None:
            continue
        if url.endswith('.pdf'):
            continue
        if url.startswith('//'):
            continue
        if url.startswith('#'):
            continue

        if url.startswith('/'):
            url = f'{org_url_start}{url}'

        if not url.startswith(org_url_start):
            continue

        text = link.get_text().strip()

        precision = get_text_precision(text)

        info = get_default_info(
            url, 'security.txt', 'url.text', precision, depth)
        if url not in checked_urls:
            urls[url] = info

    # Lets add security.txt content as backup to improve finding of e-mails
    root_url = get_root_url(org_url_start)
    security_txt_url = f'{root_url}security.txt'
    urls[security_txt_url] = get_default_info(
            security_txt_url, 'security.txt', 'url.text', 0.15, 10)
    security_txt_url = f'{root_url}.well-known/security.txt'
    urls[security_txt_url] = get_default_info(
            security_txt_url, '.well-known/security.txt', 'url.text', 0.15, 10)

    if len(urls) > 0:
        tmp = sorted(urls.items(), key=get_sort_on_precision)
        # Take top 10
        tmp = tmp[:10]
        urls = dict(tmp)

        return urls
    return urls


def get_sort_on_precision(item):
    """
    Extracts the 'precision' value from a given item.

    Parameters:
    item (tuple): A tuple where the second element is a dictionary containing a 'precision' key.

    Returns:
    int/float: The value of 'precision' from the dictionary.
    """
    return item[1]["precision"]


def get_default_info(url, text, method, precision, depth):
    """
    Constructs a dictionary with default information.

    Parameters:
    url (str): The URL to be included in the result.
    text (str): The text to be processed and included in the result.
    method (str): The method to be included in the result.
    precision (int/float): The precision value to be included in the result.
    depth (int): The depth value to be included in the result.

    Returns:
    dict: A dictionary containing the processed input parameters.
    """
    result = {}

    if text is not None:
        text = text.lower().strip('.').strip('-').strip()

    result['url'] = url
    result['method'] = method
    result['precision'] = precision
    result['text'] = text
    result['depth'] = depth

    return result


def validate_email_domain(hostname, result_dict, global_translation, local_translation):
    """
    Validates the email domain of a given hostname and
    updates the rating based on the validation results.

    Parameters:
    - hostname (str): The hostname to validate the email domain for.
    - result_dict (dict): The results dictionary.
    - global_translation (function): A function to translate text globally.
    - local_translation (function): A function to translate text locally.

    Returns:
    - rating (Rating): The updated Rating object.
    - result_dict (dict): The updated results dictionary.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    result_dict = {}
    # We must take in consideration "www." subdomains...
    if hostname.startswith('www.'):
        hostname = hostname[4:]

    # 1 - Get Email servers
    # dns_lookup
    rating, ipv4_servers, ipv6_servers = validate_mx_records(
        global_translation, rating, result_dict, local_translation, hostname)

    # If we have -1.0 in rating, we have no MX records, ignore test.
    if rating.get_overall() != -1.0:
        # 1.2 - Check operational
        if get_config('tests.email.support.port25') and len(ipv4_servers) > 0:
            rating = validate_ip4_operation_status(
                global_translation, rating, local_translation, ipv4_servers)

        # 1.2 - Check operational
        if get_config('tests.email.support.port25') and\
              get_config('tests.email.support.ipv6') and\
              len(ipv6_servers) > 0:
            rating = validate_ip6_operation_status(
                global_translation, rating, local_translation, ipv6_servers)

        # 1.4 - Check TLS
        # 1.5 - Check PKI
        # 1.6 - Check DNSSEC
        # 1.7 - Check DANE
        # 1.8 - Check MTA-STS policy
        rating = validate_mta_sts_policy(
            global_translation,
            rating,
            result_dict,
            local_translation,
            hostname)
        # 1.9 - Check SPF policy
        rating = validate_spf_policies(
            global_translation, rating, result_dict, local_translation, hostname)
        # 2.0 - Check DMARK
        rating = validate_dmarc_policies(
            global_translation, rating, result_dict, local_translation, hostname)

    return rating, result_dict


def validate_mta_sts_policy(global_translation, rating, result_dict, local_translation, hostname):
    """
    Validates the MTA STS policy of a given hostname and
    updates the rating based on the validation results.

    Parameters:
    - global_translation (function): A function to translate text globally.
    - rating (Rating): The initial Rating object.
    - result_dict (dict): The results dictionary.
    - local_translation (function): A function to translate text locally.
    - hostname (str): The hostname to validate the MTA STS policy for.

    Returns:
    - rating (Rating): The updated Rating object.
    """
    rating += rate_mts_sts_records(
        global_translation,
        local_translation,
        has_dns_mta_sts_policy(hostname))

    # https://mta-sts.example.com/.well-known/mta-sts.txt
    content = get_http_content(
        f"https://mta-sts.{hostname}/.well-known/mta-sts.txt")

    has_mta_sts_txt_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    # https://www.rfc-editor.org/rfc/rfc8461#section-3.2
    if 'STSv1' in content:

        # version: STSv1
        # mode: enforce
        # mx: mail1.polisen.se
        # mx: mail2.polisen.se
        # max_age: 604800
        result_dict['mta-sts.txt'] = {
            'valid': True,
            'has_version': False,
            'has_mode': False,
            'has_mx': False,
            'has_max_age': False
        }

        rows = content.split('\r\n')
        if len(rows) == 1:
            rows = content.split('\n')

        for row in rows:
            if row == '':
                continue
            key_value_pair = row.split(':')
            if len(key_value_pair) != 2:
                print('invalid pair:', key_value_pair)
                result_dict['mta-sts.txt']['valid'] = False
                continue

            rating += handle_mta_sts_txt_row(
                key_value_pair,
                result_dict,
                global_translation,
                local_translation)

        result_dict['mta-sts.txt']['valid'] = result_dict['mta-sts.txt']['valid'] and\
            result_dict['mta-sts.txt']['has_version'] and\
            result_dict['mta-sts.txt']['has_mode'] and\
            result_dict['mta-sts.txt']['has_mx'] and\
            result_dict['mta-sts.txt']['has_max_age']

        if result_dict['mta-sts.txt']['valid']:
            has_mta_sts_txt_rating.set_overall(5.0)
            has_mta_sts_txt_rating.set_integrity_and_security(
                5.0, local_translation('TEXT_REVIEW_MTA_STS_TXT_SUPPORT'))
            has_mta_sts_txt_rating.set_standards(
                5.0, local_translation('TEXT_REVIEW_MTA_STS_TXT_SUPPORT'))
        else:
            has_mta_sts_txt_rating.set_overall(2.0)
            has_mta_sts_txt_rating.set_integrity_and_security(
                1.0, local_translation('TEXT_REVIEW_MTA_STS_TXT_INVALID_FORMAT'))
            has_mta_sts_txt_rating.set_standards(
                1.0, local_translation('TEXT_REVIEW_MTA_STS_TXT_INVALID_FORMAT'))

    else:
        has_mta_sts_txt_rating.set_overall(1.0)
        has_mta_sts_txt_rating.set_integrity_and_security(
            1.0, local_translation('TEXT_REVIEW_MTA_STS_TXT_NO_SUPPORT'))
        has_mta_sts_txt_rating.set_standards(
            1.0, local_translation('TEXT_REVIEW_MTA_STS_TXT_NO_SUPPORT'))
    rating += has_mta_sts_txt_rating
    return rating

def handle_mta_sts_txt_row(key_value_pair, result_dict, global_translation, local_translation):
    """
    Handles a row of MTA STS TXT record and updates the rating and result dictionary.

    Parameters:
    - key_value_pair (tuple): The key-value pair from the MTA STS TXT record.
    - result_dict (dict): The results dictionary.
    - global_translation (function): A function to translate text globally.
    - local_translation (function): A function to translate text locally.

    Returns:
    - rating (Rating): The updated Rating object.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    key = key_value_pair[0].strip(' ')
    value = key_value_pair[1].strip(' ')

    if 'version' in key:
        result_dict['mta-sts.txt']['has_version'] = True
    elif 'mode' in key:
        if value == 'enforce':
            _ = 1
        elif value in ('testing', 'none'):
            mta_sts_records_not_enforced_rating = Rating(
                        global_translation, get_config('general.review.improve-only'))
            mta_sts_records_not_enforced_rating.set_overall(3.0)
            mta_sts_records_not_enforced_rating.set_integrity_and_security(
                        1.0, local_translation('TEXT_REVIEW_MTA_STS_DNS_RECORD_NOT_ENFORCED'))
            mta_sts_records_not_enforced_rating.set_standards(
                        5.0, local_translation('TEXT_REVIEW_MTA_STS_DNS_RECORD_VALID_MODE'))
            rating += mta_sts_records_not_enforced_rating
        else:
            mta_sts_records_invalid_mode_rating = Rating(
                        global_translation, get_config('general.review.improve-only'))
            mta_sts_records_invalid_mode_rating.set_overall(1.0)
            mta_sts_records_invalid_mode_rating.set_integrity_and_security(
                        1.0, local_translation('TEXT_REVIEW_MTA_STS_DNS_RECORD_INVALID_MODE'))
            mta_sts_records_invalid_mode_rating.set_standards(
                        1.0, local_translation('TEXT_REVIEW_MTA_STS_DNS_RECORD_INVALID_MODE'))
            rating += mta_sts_records_invalid_mode_rating

        result_dict['mta-sts.txt']['has_mode'] = True
    elif 'mx' in key:
        result_dict['mta-sts.txt']['has_mx'] = True
    elif 'max_age' in key:
        result_dict['mta-sts.txt']['has_max_age'] = True
    else:
        print('invalid key:', key)
        result_dict['mta-sts.txt']['valid'] = False
    return rating

def has_dns_mta_sts_policy(hostname):
    """
    Checks if the given hostname has a DNS MTA STS policy.

    Parameters:
    - hostname (str): The hostname to check.

    Returns:
    - bool: True if a MTA STS policy exists, False otherwise.
    """
    has_mta_sts_policy = False
    # https://www.rfc-editor.org/rfc/rfc8461#section-3.1
    mta_sts_results = dns_lookup('_mta-sts.' + hostname, dns.rdatatype.TXT)
    for result in mta_sts_results:
        if 'v=STSv1;' in result:
            has_mta_sts_policy = True
    return has_mta_sts_policy

def rate_mts_sts_records(global_translation, local_translation, has_mta_sts_policy):
    """
    This function rates the MTS STS records based on whether a MTA STS policy exists.

    Parameters:
    - global_translation (function): A function to translate text globally.
    - local_translation (function): A function to translate text locally.
    - has_mta_sts_policy (bool): A boolean indicating whether a MTA STS policy exists.

    Returns:
    - has_mta_sts_records_rating (Rating): A Rating object with the overall rating,
                                           integrity and security, and
                                           standards set based on the existence of MTA STS records.
    """
    has_mta_sts_records_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if has_mta_sts_policy:
        has_mta_sts_records_rating.set_overall(5.0)
        has_mta_sts_records_rating.set_integrity_and_security(
            5.0, local_translation('TEXT_REVIEW_MTA_STS_DNS_RECORD_SUPPORT'))
        has_mta_sts_records_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_MTA_STS_DNS_RECORD_SUPPORT'))
    else:
        has_mta_sts_records_rating.set_overall(1.0)
        has_mta_sts_records_rating.set_integrity_and_security(
            1.0, local_translation('TEXT_REVIEW_MTA_STS_DNS_RECORD_NO_SUPPORT'))
        has_mta_sts_records_rating.set_standards(
            1.0, local_translation('TEXT_REVIEW_MTA_STS_DNS_RECORD_NO_SUPPORT'))
    return has_mta_sts_records_rating


def validate_dmarc_policies(global_translation, rating, result_dict, local_translation, hostname):
    """
    This function validates the DMARC policies of a given hostname and
    updates the rating based on the validation results.

    Parameters:
    - global_translation (function): A function to translate text globally.
    - rating (Rating): The initial Rating object.
    - result_dict (dict): A dictionary containing the results of the DMARC policy checks.
    - local_translation (function): A function to translate text locally.
    - hostname (str): The hostname to validate the DMARC policies for.

    Returns:
    - rating (Rating): The updated Rating object with the rating results of the DMARC policies.
    """
    dmarc_result_dict = validate_dmarc_policy(local_translation, hostname, result_dict)
    result_dict.update(dmarc_result_dict)

    rating = rate_has_dmarc_policies(global_translation, rating, result_dict, local_translation)

    return rating


def validate_dmarc_policy(local_translation, hostname, result_dict):
    """
    This function validates the DMARC policy of a given hostname.

    Parameters:
    - local_translation (function): A function to translate text locally.
    - hostname (str): The hostname to validate the DMARC policy for.
    - result_dict (dict): A dictionary containing the results of the DMARC policy checks.

    Returns:
    - result_dict (dict): The updated results dictionary with the
                          validation results of the DMARC policy.
    """
    # https://proton.me/support/anti-spoofing-custom-domain

    dmarc_results = dns_lookup(f"_dmarc.{hostname}", "TXT")
    dmarc_content = ''

    for result in dmarc_results:
        if result.startswith('v=DMARC1'):
            result_dict['dmarc-has-policy'] = True
            dmarc_content = result

    if 'dmarc-has-policy' in result_dict:
        result_dict['dmarc-errors'] = []
        result_dict['dmarc-warnings'] = []
        result_dict['dmarc-pct'] = 100
        result_dict['dmarc-ri'] = 86400
        result_dict['dmarc-fo'] = []
        result_dict['dmarc-ruf'] = []
        result_dict['dmarc-rua'] = []

        # https://www.rfc-editor.org/rfc/rfc7489.txt
        # https://www.rfc-editor.org/rfc/rfc7489#section-6.1
        dmarc_content = dmarc_content.rstrip(';')
        dmarc_sections = dmarc_content.split(';')

        for section in dmarc_sections:
            section = section.strip()
            if section == '':
                result_dict['dmarc-errors'].append(
                    local_translation('TEXT_REVIEW_DMARC_EMPTY_SECTION_WHILE_PARSE'))
                continue

            pair = section.split('=')
            if len(pair) != 2:
                result_dict['dmarc-errors'].append(
                    local_translation('TEXT_REVIEW_DMARC_PAIR_INVALID'))
                continue

            key = pair[0]
            data = pair[1]

            handle_dmarc_section(key, data, result_dict, local_translation)

    return result_dict


def rate_has_dmarc_policies(global_translation, rating, result_dict, local_translation):
    """
    This function rates the DMARC policies based on the provided results dictionary.

    Parameters:
    - global_translation (function): A function to translate text globally.
    - rating (Rating): The initial Rating object.
    - result_dict (dict): A dictionary containing the results of the DMARC policy checks.
    - local_translation (function): A function to translate text locally.

    Returns:
    - rating (Rating): A Rating object with the overall rating, integrity and security,
    and standards set based on the DMARC policies.
    """
    if 'dmarc-has-policy' in result_dict:
        no_dmarc_record_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        no_dmarc_record_rating.set_overall(5.0)
        no_dmarc_record_rating.set_integrity_and_security(
            5.0, local_translation('TEXT_REVIEW_DMARC_SUPPORT'))
        no_dmarc_record_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_DMARC_SUPPORT'))
        rating += no_dmarc_record_rating

        rating += rate_dmarc_policy(global_translation, result_dict, local_translation)
        rating += rate_dmarc_subpolicy(global_translation, result_dict, local_translation)

        if result_dict['dmarc-pct'] is not None:
            rating += rate_dmarc_pct(global_translation, result_dict, local_translation)

        if len(result_dict['dmarc-fo']) != 0 and\
              len(result_dict['dmarc-ruf']) == 0:
            result_dict['dmarc-errors'].append(
                local_translation('TEXT_REVIEW_DMARC_USES_FO_BUT_NO_RUF'))

        if len(result_dict['dmarc-errors']) != 0:
            for error in result_dict['dmarc-errors']:
                error_rating = Rating(
                    global_translation,
                    get_config('general.review.improve-only'))
                error_rating.set_overall(1.0)
                error_rating.set_standards(
                    1.0, error)
                rating += error_rating
        else:
            no_errors_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            no_errors_rating.set_overall(5.0)
            no_errors_rating.set_standards(
                5.0, local_translation('TEXT_REVIEW_DMARC_NO_PARSE_ERRORS'))
            rating += no_errors_rating

        if len(result_dict['dmarc-warnings']) != 0:
            for warning in result_dict['dmarc-warnings']:
                warning_rating = Rating(
                    global_translation,
                    get_config('general.review.improve-only'))
                warning_rating.set_overall(3.0)
                warning_rating.set_standards(
                    3.0, warning)
                rating += warning_rating
        else:
            no_errors_rating = Rating(
                global_translation,
                get_config('general.review.improve-only'))
            no_errors_rating.set_overall(5.0)
            no_errors_rating.set_standards(
                5.0, local_translation('TEXT_REVIEW_DMARC_NO_WARNINGS'))
            rating += no_errors_rating
    else:
        no_dmarc_record_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        no_dmarc_record_rating.set_overall(1.0)
        no_dmarc_record_rating.set_integrity_and_security(
            1.0, local_translation('TEXT_REVIEW_DMARC_NO_SUPPORT'))
        no_dmarc_record_rating.set_standards(
            1.0, local_translation('TEXT_REVIEW_DMARC_NO_SUPPORT'))
        rating += no_dmarc_record_rating
    return rating

def rate_dmarc_pct(global_translation, result_dict, local_translation):
    """
    This function rates the DMARC percentage (pct) based on the provided results dictionary.

    Parameters:
    - global_translation (function): A function to translate text globally.
    - result_dict (dict): A dictionary containing the results of the DMARC policy checks.
    - local_translation (function): A function to translate text locally.

    Returns:
    - percentage_rating (Rating): A Rating object with the overall rating, integrity and security,
                                  and standards set based on the DMARC percentage.
    """
    percentage_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if result_dict['dmarc-pct'] < 100:
        percentage_rating.set_overall(3.0)
        percentage_rating.set_integrity_and_security(
                    1.0, local_translation('TEXT_REVIEW_DMARC_PCT_NOT_100'))
        percentage_rating.set_standards(
                    5.0, local_translation('TEXT_REVIEW_DMARC_PCT'))
    else:
        percentage_rating.set_overall(5.0)
        percentage_rating.set_integrity_and_security(
                    5.0, local_translation('TEXT_REVIEW_DMARC_PCT'))
        percentage_rating.set_standards(
                    5.0, local_translation('TEXT_REVIEW_DMARC_PCT'))
    return percentage_rating

def rate_dmarc_subpolicy(global_translation, result_dict, local_translation):
    """
    This function rates the DMARC subpolicy based on the provided results dictionary.

    Parameters:
    - global_translation (function): A function to translate text globally.
    - result_dict (dict): A dictionary containing the results of the DMARC policy checks.
    - local_translation (function): A function to translate text locally.

    The function checks the 'dmarc-sp' and 'dmarc-p' fields in the results dictionary. 
    It sets the overall rating and standards based on the values of these fields.

    Returns:
    - dmarc_subpolicy_rating (Rating): A Rating object with the overall rating and
                                       standards set based on the DMARC subpolicy.
    """
    dmarc_subpolicy_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if 'dmarc-sp' in result_dict and\
                'dmarc-p' in result_dict and\
                result_dict['dmarc-p'] == result_dict['dmarc-sp']:
        dmarc_subpolicy_rating.set_overall(3.0)
        dmarc_subpolicy_rating.set_standards(
                3.0, local_translation('TEXT_REVIEW_DMARC_SUBPOLICY_REDUNDANT'))
    elif 'dmarc-sp' in result_dict:
        if 'reject' == result_dict['dmarc-sp']:
            dmarc_subpolicy_rating.set_overall(5.0)
            dmarc_subpolicy_rating.set_integrity_and_security(
                    5.0, local_translation('TEXT_REVIEW_DMARC_SUBPOLICY_QUARANTINE'))
            dmarc_subpolicy_rating.set_standards(
                    5.0, local_translation('TEXT_REVIEW_DMARC_SUBPOLICY_QUARANTINE'))
        elif 'quarantine' == result_dict['dmarc-sp']:
            dmarc_subpolicy_rating.set_overall(4.0)
            dmarc_subpolicy_rating.set_integrity_and_security(
                    4.0, local_translation('TEXT_REVIEW_DMARC_SUBPOLICY_REJECT'))
            dmarc_subpolicy_rating.set_standards(
                    5.0, local_translation('TEXT_REVIEW_DMARC_SUBPOLICY_REJECT'))
        elif 'none' == result_dict['dmarc-sp']:
            dmarc_subpolicy_rating.set_overall(3.0)
            dmarc_subpolicy_rating.set_integrity_and_security(
                    1.0, local_translation('TEXT_REVIEW_DMARC_SUBPOLICY_NONE'))
            dmarc_subpolicy_rating.set_standards(
                    5.0, local_translation('TEXT_REVIEW_DMARC_SUBPOLICY_NONE'))
    return dmarc_subpolicy_rating

def rate_dmarc_policy(global_translation, result_dict, local_translation):
    """
    Rates DMARC policy based on its configuration.

    Parameters:
    global_translation, local_translation (function): Translation functions.
    result_dict (dict): Stores DMARC results.

    Returns:
    dmarc_policy_rating (Rating): Rating object after DMARC policy rating.
    """
    dmarc_policy_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if 'dmarc-p' in result_dict:
        if 'reject' == result_dict['dmarc-p']:
            dmarc_policy_rating.set_overall(5.0)
            dmarc_policy_rating.set_integrity_and_security(
                    5.0, local_translation('TEXT_REVIEW_DMARC_POLICY_REJECT'))
            dmarc_policy_rating.set_standards(
                    5.0, local_translation('TEXT_REVIEW_DMARC_POLICY_REJECT'))
        elif 'quarantine' == result_dict['dmarc-p']:
            dmarc_policy_rating.set_overall(4.0)
            dmarc_policy_rating.set_integrity_and_security(
                    4.0, local_translation('TEXT_REVIEW_DMARC_POLICY_QUARANTINE'))
            dmarc_policy_rating.set_standards(
                    5.0, local_translation('TEXT_REVIEW_DMARC_POLICY_QUARANTINE'))
        elif 'none' == result_dict['dmarc-p']:
            dmarc_policy_rating.set_overall(3.0)
            dmarc_policy_rating.set_integrity_and_security(
                    1.0, local_translation('TEXT_REVIEW_DMARC_POLICY_NONE'))
            dmarc_policy_rating.set_standards(
                    5.0, local_translation('TEXT_REVIEW_DMARC_POLICY_NONE'))
    if not dmarc_policy_rating.is_set:
        dmarc_policy_rating.set_overall(1.0)
        dmarc_policy_rating.set_integrity_and_security(
                1.0, local_translation('TEXT_REVIEW_DMARC_NO_POLICY'))
        dmarc_policy_rating.set_standards(
                1.0, local_translation('TEXT_REVIEW_DMARC_NO_POLICY'))

    return dmarc_policy_rating


def validate_spf_policies(global_translation, rating, result_dict, local_translation, hostname):
    """
    Validates SPF policies and rates them based on various criteria.

    Parameters:
    global_translation, local_translation (function): Translation functions.
    hostname (str): The hostname to validate SPF policies for.
    rating (Rating): The current rating object.
    result_dict (dict): Stores SPF results.

    Returns:
    rating (Rating): Updated rating object after SPF policy validation and rating.
    """
    spf_result_dict = validate_spf_policy(
        global_translation,
        local_translation,
        hostname,
        result_dict)
    result_dict.update(spf_result_dict)

    rating = rate_has_spf_policies(global_translation, rating, result_dict, local_translation)
    rating = rate_invalid_format_spf_policies(
        global_translation,
        rating,
        result_dict,
        local_translation)
    rating = rate_too_many_dns_lookup_for_spf_policies(
        global_translation, rating, result_dict, local_translation)
    rating = rate_use_of_ptr_for_spf_policies(
        global_translation,
        rating,
        result_dict,
        local_translation)

    rating = rate_fail_configuration_for_spf_policies(
        global_translation, rating, result_dict, local_translation)

    rating = rate_gdpr_for_spf_policies(global_translation, rating, result_dict, local_translation)

    return rating


def rate_use_of_ptr_for_spf_policies(global_translation, rating, result_dict, local_translation):
    """
    Rates SPF policies based on their use of PTR records.

    Parameters:
    global_translation, local_translation (function): Translation functions.
    rating (Rating): The current rating object.
    result_dict (dict): Stores SPF results.

    Returns:
    rating (Rating): Updated rating object after SPF PTR records usage check.
    """
    if 'spf-uses-ptr' in result_dict:
        has_spf_record_ptr_being_used_rating = Rating(
            global_translation, get_config('general.review.improve-only'))
        has_spf_record_ptr_being_used_rating.set_overall(1.0)
        has_spf_record_ptr_being_used_rating.set_standards(
            1.0, local_translation('TEXT_REVIEW_SPF_DNS_RECORD_PTR_USED'))
        rating += has_spf_record_ptr_being_used_rating

    return rating


def rate_fail_configuration_for_spf_policies(
        global_translation,
        rating,
        result_dict,
        local_translation):
    """
    Rates SPF policies based on their fail configuration.

    Parameters:
    global_translation, local_translation (function): Translation functions.
    rating (Rating): The current rating object.
    result_dict (dict): Stores SPF results.

    Returns:
    rating (Rating): Updated rating object after SPF fail configuration check.
    """
    if 'spf-uses-ignorefail' in result_dict:
        has_spf_ignore_records_rating = Rating(
            global_translation, get_config('general.review.improve-only'))
        has_spf_ignore_records_rating.set_overall(2.0)
        has_spf_ignore_records_rating.set_integrity_and_security(
            1.0, local_translation('TEXT_REVIEW_SPF_DNS_IGNORE_RECORD_NO_SUPPORT'))
        has_spf_ignore_records_rating.set_standards(
            2.5, local_translation('TEXT_REVIEW_SPF_DNS_IGNORE_RECORD_NO_SUPPORT'))
        rating += has_spf_ignore_records_rating

    if 'spf-uses-neutralfail' in result_dict:
        has_spf_dns_record_neutralfail_records_rating = Rating(
            global_translation, get_config('general.review.improve-only'))
        has_spf_dns_record_neutralfail_records_rating.set_overall(
            3.0)
        has_spf_dns_record_neutralfail_records_rating.set_integrity_and_security(
            2.0, local_translation('TEXT_REVIEW_SPF_DNS_NEUTRALFAIL_RECORD'))
        has_spf_dns_record_neutralfail_records_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_SPF_DNS_NEUTRALFAIL_RECORD'))
        rating += has_spf_dns_record_neutralfail_records_rating

    if 'spf-uses-softfail' in result_dict:
        has_spf_dns_record_softfail_records_rating = Rating(
            global_translation, get_config('general.review.improve-only'))
        has_spf_dns_record_softfail_records_rating.set_overall(5.0)
        has_spf_dns_record_softfail_records_rating.set_integrity_and_security(
            2.0, local_translation('TEXT_REVIEW_SPF_DNS_SOFTFAIL_RECORD'))
        has_spf_dns_record_softfail_records_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_SPF_DNS_SOFTFAIL_RECORD'))
        rating += has_spf_dns_record_softfail_records_rating

    if 'spf-uses-hardfail' in result_dict:
        has_spf_dns_record_hardfail_records_rating = Rating(
            global_translation, get_config('general.review.improve-only'))
        has_spf_dns_record_hardfail_records_rating.set_overall(5.0)
        has_spf_dns_record_hardfail_records_rating.set_integrity_and_security(
            5.0, local_translation('TEXT_REVIEW_SPF_DNS_HARDFAIL_RECORD'))
        has_spf_dns_record_hardfail_records_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_SPF_DNS_HARDFAIL_RECORD'))
        rating += has_spf_dns_record_hardfail_records_rating
    return rating


def rate_invalid_format_spf_policies(global_translation, rating, result_dict, local_translation):
    """
    Rates SPF policies based on their format validity.

    Parameters:
    global_translation, local_translation (function): Translation functions.
    rating (Rating): The current rating object.
    result_dict (dict): Stores SPF results.

    Returns:
    rating (Rating): Updated rating object after SPF format validity check.
    """
    if 'spf-uses-none-standard' in result_dict:
        has_spf_unknown_section_rating = Rating(
            global_translation, get_config('general.review.improve-only'))
        has_spf_unknown_section_rating.set_overall(1.0)
        has_spf_unknown_section_rating.set_standards(
            1.0, local_translation('TEXT_REVIEW_SPF_UNKNOWN_SECTION'))
        rating += has_spf_unknown_section_rating

    if 'spf-error-double-space' in result_dict:
        has_spf_dns_record_double_space_rating = Rating(
            global_translation, get_config('general.review.improve-only'))
        has_spf_dns_record_double_space_rating.set_overall(
            1.5)
        has_spf_dns_record_double_space_rating.set_standards(
            1.5, local_translation('TEXT_REVIEW_SPF_DNS_DOUBLE_SPACE_RECORD'))
        rating += has_spf_dns_record_double_space_rating
    return rating


def rate_has_spf_policies(global_translation, rating, result_dict, local_translation):
    """
    Rates the presence of SPF policies in DNS records.

    Parameters:
    global_translation, local_translation (function): Translation functions.
    rating (Rating): The current rating object.
    result_dict (dict): Stores SPF results.

    Returns:
    rating (Rating): Updated rating object after SPF policy presence check.
    """
    has_spf_records_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if 'spf-has-policy' in result_dict:
        txt = local_translation('TEXT_REVIEW_SPF_DNS_RECORD_SUPPORT')
        has_spf_records_rating.set_overall(5.0)
        has_spf_records_rating.set_integrity_and_security(
            5.0, txt)
        has_spf_records_rating.set_standards(
            5.0, txt)
    else:
        txt = local_translation('TEXT_REVIEW_SPF_DNS_RECORD_NO_SUPPORT')
        has_spf_records_rating.set_overall(1.0)
        has_spf_records_rating.set_integrity_and_security(
            1.0, txt)
        has_spf_records_rating.set_standards(
            1.0, txt)
    rating += has_spf_records_rating
    return rating


def rate_too_many_dns_lookup_for_spf_policies(
        global_translation,
        rating,
        result_dict,
        local_translation):
    """
    Rates SPF policies based on DNS lookups count.

    Parameters:
    global_translation, local_translation (function): Translation functions.
    rating (Rating): The current rating object.
    result_dict (dict): Stores SPF results.

    Returns:
    rating (Rating): Updated rating object after DNS lookups count check.
    """
    if 'spf-error-to-many-dns-lookups' in result_dict:
        to_many_spf_dns_lookups_rating = Rating(
            global_translation, get_config('general.review.improve-only'))
        to_many_spf_dns_lookups_rating.set_overall(1.0)
        to_many_spf_dns_lookups_rating.set_standards(
            1.0, local_translation('TEXT_REVIEW_SPF_TO_MANY_DNS_LOOKUPS'))
        to_many_spf_dns_lookups_rating.set_performance(
            4.0, local_translation('TEXT_REVIEW_SPF_TO_MANY_DNS_LOOKUPS'))
        rating += to_many_spf_dns_lookups_rating
    return rating


def rate_gdpr_for_spf_policies(global_translation, rating, result_dict, local_translation):
    """
    Rates GDPR compliance for SPF policies based on IP addresses.

    Parameters:
    global_translation, local_translation (function): Translation functions.
    rating (Rating): The current rating object.
    result_dict (dict): Stores SPF results.

    Returns:
    rating (Rating): Updated rating object after GDPR compliance check.
    """
    spf_addresses = []
    if 'spf-ipv4' not in result_dict:
        result_dict['spf-ipv4'] = []
    if 'spf-ipv6' not in result_dict:
        result_dict['spf-ipv6'] = []
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
        if country_code in ('', '-'):
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
        gdpr_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        gdpr_rating.set_overall(5.0)
        gdpr_rating.set_integrity_and_security(
            5.0, local_translation('TEXT_REVIEW_SPF_GDPR').format(
                ', '.join(countries_eu_or_exception_list.keys())))
        rating += gdpr_rating
    if nof_none_gdpr_countries > 0:
        none_gdpr_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        none_gdpr_rating.set_overall(1.0)
        none_gdpr_rating.set_integrity_and_security(
            1.0, local_translation('TEXT_REVIEW_SPF_NONE_GDPR').format(
                ', '.join(countries_others.keys())))
        rating += none_gdpr_rating
    return rating

def handle_spf_ip4(section, result_dict, _, _2):
    """
    Updates 'result_dict' with SPF IPv4 data from 'section'.

    Parameters:
    section (list): Contains SPF data.
    result_dict (dict): Stores SPF results.

    Returns:
    None. Updates 'result_dict' in place.
    """

    if not section.startswith('ip4:'):
        result_dict['spf-uses-none-standard'] = True
        return

    data = section[4:]
    if 'spf-ipv4' not in result_dict:
        result_dict['spf-ipv4'] = []
    result_dict['spf-ipv4'].append(data)

def handle_spf_ip6(section, result_dict, _, _2):
    """
    Updates 'result_dict' with SPF IPv6 data from 'section'.

    Parameters:
    section (list): Contains SPF data.
    result_dict (dict): Stores SPF results.

    Returns:
    None. Updates 'result_dict' in place.
    """
    if not section.startswith('ip6:'):
        result_dict['spf-uses-none-standard'] = True
        return
    data = section[4:]
    if 'spf-ipv6' not in result_dict:
        result_dict['spf-ipv6'] = []
    result_dict['spf-ipv6'].append(data)

def handle_spf_include(section, result_dict, global_translation, local_translation):
    """
    Handles the 'include' mechanism in an SPF (Sender Policy Framework) record.

    Parameters:
        section (str): The SPF section to be handled.
        result_dict (dict): Stores the results.
        global_translation (function): Translates text messages globally.
        local_translation (function): Translates text messages locally.

    The function extracts the domain from the 'include' section,
    validates the SPF policy of the domain,
    and updates the result dictionary with the validation results.
    """
    if section.startswith('+'):
        section = section[1:]

    if not section.startswith('include:'):
        result_dict['spf-uses-none-standard'] = True
        return
    spf_domain = section[8:]
    subresult_dict = validate_spf_policy(
        global_translation, local_translation, spf_domain, result_dict)
    result_dict.update(subresult_dict)

def handle_spf_neutral_all(_, result_dict, _2, _3):
    """
    Handles the '?all' mechanism in an SPF (Sender Policy Framework) record.

    Parameters:
        _ (_): Ignored parameter.
        result_dict (dict): Stores the results.
        _2, _3: Ignored parameters.

    The function marks the SPF record as using the '?all' mechanism, which indicates a NeutralFail.
    """
    # What do this do and should we rate on it?
    result_dict['spf-uses-neutralfail'] = True

def handle_spf_soft_all(_, result_dict, _2, _3):
    """
    Handles the '~all' mechanism in an SPF (Sender Policy Framework) record.

    Parameters:
        _ (_): Ignored parameter.
        result_dict (dict): Stores the results.
        _2, _3: Ignored parameters.

    The function marks the SPF record as using the '~all' mechanism, which indicates a SoftFail.
    This means that any IP not authorized by the SPF record should
    be treated as a potential spam source, but not definitively so.
    """
    # add support for SoftFail
    result_dict['spf-uses-softfail'] = True

def handle_spf_hard_all(_, result_dict, _2, _3):
    """
    Handles the '-all' mechanism in an SPF (Sender Policy Framework) record.

    Parameters:
        _ (_): Ignored parameter.
        result_dict (dict): Stores the results.
        _2, _3: Ignored parameters.

    The function marks the SPF record as using the '-all' mechanism,
    which indicates a HardFail.
    This means that any IP not authorized by the SPF record should
    be treated as a definitive spam source.
    """
    # add support for HardFail
    result_dict['spf-uses-hardfail'] = True

def handle_spf_ignore_all(_, result_dict, _2, _3):
    """
    Handles the '+all' mechanism in an SPF (Sender Policy Framework) record.

    Parameters:
        _ (str): Ignored parameter.
        result_dict (dict): Stores the results.
        _2, _3: Ignored parameters.

    The function marks the SPF record as using the '+all' mechanism,
    which essentially whitelists all sending hosts.
    This is generally considered a poor practice in SPF policy.
    """
    # basicly whitelist everything... Big fail
    result_dict['spf-uses-ignorefail'] = True

def handle_spf_noop(_, _2, _3, _4):
    """
    A no-operation (noop) function for handling certain SPF (Sender Policy Framework) mechanisms.

    Parameters:
        _ (_): Ignored parameter.
        _2 (_): Ignored parameter.
        _3 (_): Ignored parameter.
        _4 (_): Ignored parameter.

    This function does nothing and
    is used as a placeholder for SPF mechanisms that require no specific handling.
    """
    return

def handle_spf_ptr(_, result_dict, _2, _3):
    """
    Handles the 'ptr' mechanism in an SPF (Sender Policy Framework) record.

    Parameters:
        _ (_): Ignored parameter.
        result_dict (dict): Stores the results.
        _2, _3: Ignored parameters.

    The function marks the SPF record as using the 'ptr' mechanism.
    The 'ptr' mechanism is generally not recommended due to potential performance and
    security issues.
    """
    # What do this do and should we rate on it?
    result_dict['spf-uses-ptr'] = True


def handle_spf_section(section, result_dict, global_translation, local_translation):
    """
    Handles SPF (Sender Policy Framework) sections.

    Parameters:
        section (str): The SPF section to be handled.
        result_dict (dict): Stores the results.
        global_translation (function): Translates text messages globally.
        local_translation (function): Translates text messages locally.

    The function maps SPF sections to their respective handlers.
    If a section starts with a specific option, the corresponding handler is invoked.
    If the section doesn't start with any of the specified options,
    it's marked as non-standard in the result dictionary.
    """
    spf_section_handlers = {
        "ip4": handle_spf_ip4,
        "ip6": handle_spf_ip6,
        "include": handle_spf_include,
        "+include": handle_spf_include,
        "?all": handle_spf_neutral_all,
        "~all": handle_spf_soft_all,
        "-all": handle_spf_hard_all,
        "+all": handle_spf_ignore_all,
        "v=spf1": handle_spf_noop,
        "mx": handle_spf_noop,
        "+mx": handle_spf_noop,
        "a": handle_spf_noop,
        "+a": handle_spf_noop,
        "ptr": handle_spf_ptr,
        "+ptr": handle_spf_ptr,
        "exists:": handle_spf_noop,
        "redirect=": handle_spf_noop,
        "exp=": handle_spf_noop,
    }

    for option, handler in spf_section_handlers.items():
        if section.startswith(option):
            handler(section, result_dict, global_translation, local_translation)
        else:
            result_dict['spf-uses-none-standard'] = True

def handle_dmarc_p(data, result_dict, local_translation):
    """
    Handles the DMARC 'p' tag.

    Parameters:
        data (str): The 'p' value.
        result_dict (dict): Stores the results, including warnings.
        local_translation (function): Translates text messages.
    """
    if data in ('none', 'quarantine', 'reject'):
        result_dict['dmarc-p'] = data
    else:
        result_dict['dmarc-errors'].append(
            local_translation(
                'TEXT_REVIEW_DMARC_POLICY_INVALID'))

def handle_dmarc_sp(data, result_dict, local_translation):
    """
    Handles the DMARC 'sp' tag.

    Parameters:
        data (str): The 'sp' value.
        result_dict (dict): Stores the results, including warnings.
        local_translation (function): Translates text messages.
    """
    if data in ('none', 'quarantine', 'reject'):
        result_dict['dmarc-sp'] = data
    else:
        result_dict['dmarc-errors'].append(
            local_translation(
                'TEXT_REVIEW_DMARC_SUBPOLICY_INVALID'))

def handle_dmarc_adkim(data, result_dict, local_translation):
    """
    Handles the DMARC 'adkim' tag.

    Parameters:
        data (str): The 'adkim' value.
        result_dict (dict): Stores the results, including warnings.
        local_translation (function): Translates text messages.
    """
    if data == 'r':
        result_dict['dmarc-warnings'].append(
            local_translation(
                'TEXT_REVIEW_DMARC_ADKIM_USES_DEFAULT'))
    elif data == 's':
        result_dict['dmarc-adkim'] = data
    else:
        result_dict['dmarc-errors'].append(
            local_translation(
                'TEXT_REVIEW_DMARC_ADKIM_INVALID'))

def handle_dmarc_aspf(data, result_dict, local_translation):
    """
    Handles the DMARC 'aspf' tag.

    Parameters:
        data (str): The 'aspf' value.
        result_dict (dict): Stores the results, including warnings.
        local_translation (function): Translates text messages.
    """
    if data == 'r':
        result_dict['dmarc-warnings'].append(
            local_translation(
                'TEXT_REVIEW_DMARC_ASPF_USES_DEFAULT'))
    elif data == 's':
        result_dict['dmarc-aspf'] = data
    else:
        result_dict['dmarc-errors'].append(
            local_translation(
                'TEXT_REVIEW_DMARC_ASPF_INVALID'))

def handle_dmarc_fo(data, result_dict, local_translation):
    """
    Handles the DMARC 'fo' tag.

    Parameters:
        data (str): The 'fo' value.
        result_dict (dict): Stores the results, including warnings.
        local_translation (function): Translates text messages.
    """
    result_dict['dmarc-fo'] = []
    fields = data.split(',')
    for field in fields:
        if field == '0':
            result_dict['dmarc-fo'].append(field)
            result_dict['dmarc-warnings'].append(
                local_translation(
                    'TEXT_REVIEW_DMARC_FO_USES_DEFAULT'))
        elif field in ('1', 'd', 's'):
            result_dict['dmarc-fo'].append(field)
        else:
            result_dict['dmarc-errors'].append(
                local_translation(
                    'TEXT_REVIEW_DMARC_FO_INVALID'))

def handle_dmarc_rua(data, result_dict, _):
    """
    Handles the DMARC 'rua' tag.

    Parameters:
        data (str): The 'rua' value.
        result_dict (dict): Stores the results, including warnings.
        local_translation (function): Translates text messages.
    """
    fields = data.split(',')
    for field in fields:
        result_dict['dmarc-rua'].append(field)

def handle_dmarc_ruf(data, result_dict, _):
    """
    Handles the DMARC 'ruf' tag.

    Parameters:
        data (str): The 'ruf' value.
        result_dict (dict): Stores the results, including warnings.
        local_translation (function): Translates text messages.
    """
    fields = data.split(',')
    for field in fields:
        result_dict['dmarc-ruf'].append(field)

def handle_dmarc_rf(data, result_dict, local_translation):
    """
    Handles the DMARC 'rf' tag.

    Parameters:
        data (str): The 'rf' value.
        result_dict (dict): Stores the results, including warnings.
        local_translation (function): Translates text messages.
    """
    if data == 'afrf':
        result_dict['dmarc-warnings'].append(local_translation(
            'TEXT_REVIEW_DMARC_RF_USES_DEFAULT'))
    result_dict['dmarc-rf'] = data

def handle_dmarc_pct(data, result_dict, local_translation):
    """
    This function handles the DMARC percentage (pct) tag in a DMARC DNS record.

    Parameters:
        data (str): The DMARC pct value to be processed.
        result_dict (dict): A dictionary to store the results of the DMARC pct processing.
                            This includes any warnings or errors encountered during processing.
        local_translation (function): A function to translate text messages into the local language.
    """
    try:
        result_dict['dmarc-pct'] = int(data)
        if result_dict['dmarc-pct'] == 100:
            result_dict['dmarc-warnings'].append(
                local_translation('TEXT_REVIEW_DMARC_PCT_USES_DEFAULT'))
        elif 100 < result_dict['dmarc-pct'] < 0:
            result_dict['dmarc-errors'].append(
                local_translation('TEXT_REVIEW_DMARC_PCT_INVALID'))
            result_dict['dmarc-pct'] = None
    except (TypeError, ValueError):
        result_dict['dmarc-errors'].append(
            local_translation('TEXT_REVIEW_DMARC_PCT_INVALID'))
        result_dict['dmarc-pct'] = None

def handle_dmarc_ri(data, result_dict, local_translation):
    """
    Handles the DMARC Reporting Interval (RI) by validating and processing the input data.

    Args:
        data (str): The DMARC RI data to be processed.
        result_dict (dict): The dictionary to store the results of the processing.
        local_translation (function): The function to translate text messages.
    """
    try:
        result_dict['dmarc-ri'] = int(data)
        if result_dict['dmarc-ri'] == 86400:
            result_dict['dmarc-warnings'].append(
                local_translation('TEXT_REVIEW_DMARC_RI_USES_DEFAULT'))
    except (TypeError, ValueError):
        result_dict['dmarc-errors'].append(
            local_translation('TEXT_REVIEW_DMARC_RI_INVALID'))
        result_dict['dmarc-ri'] = None

def handle_dmarc_section(key, data, result_dict, local_translation):
    """
    Handles a DMARC section based on its key.

    Args:
        key (str): The key of the DMARC section.
        data (str): The data of the DMARC section.
        result_dict (dict): Dictionary to store results.
        local_translation (function): Local text translator.
    """
    dmarc_section_handlers = {
        "p": handle_dmarc_p,
        "sp": handle_dmarc_sp,
        "adkim:": handle_dmarc_adkim,
        "aspf": handle_dmarc_aspf,
        "fo": handle_dmarc_fo,
        "rua": handle_dmarc_rua,
        "ruf": handle_dmarc_ruf,
        "rf": handle_dmarc_rf,
        "pct": handle_dmarc_pct,
        "ri": handle_dmarc_ri,
    }

    for option, handler in dmarc_section_handlers.items():
        if key == option:
            handler(data, result_dict, local_translation)

def validate_spf_policy(global_translation, local_translation, hostname, result_dict):
    """
    Validates the SPF policy of a hostname.

    Args:
        global_translation (function): Global text translator.
        local_translation (function): Local text translator.
        hostname (str): The hostname to validate.
        result_dict (dict): Dictionary to store results.

    Returns:
        result_dict (dict): Updated dictionary with SPF validation results.
    """
    # https://proton.me/support/anti-spoofing-custom-domain

    if 'spf-dns-lookup-count' in result_dict and result_dict['spf-dns-lookup-count'] >= 10:
        result_dict['spf-error-to-many-dns-lookups'] = True
        return result_dict

    if 'spf-dns-lookup-count' not in result_dict:
        result_dict['spf-dns-lookup-count'] = 1
    else:
        result_dict['spf-dns-lookup-count'] = result_dict['spf-dns-lookup-count'] + 1

    spf_results = dns_lookup(hostname, dns.rdatatype.TXT)
    spf_content = ''

    for result in spf_results:
        if 'v=spf1 ' in result:
            result_dict['spf-has-policy'] = True
            spf_content = result

    if 'spf-has-policy' in result_dict:
        # https://www.rfc-editor.org/rfc/rfc7208#section-9.1
        spf_sections = spf_content.split(' ')

        # http://www.open-spf.org/SPF_Record_Syntax/
        for section in spf_sections:
            if section == '':
                result_dict['spf-error-double-space'] = True
                continue
            handle_spf_section(section, result_dict, global_translation, local_translation)

    return result_dict


def replace_network_with_first_and_last_ipaddress(spf_addresses):
    """
    Replaces network addresses with their first and last IP addresses.

    Args:
        spf_addresses (list): List of SPF addresses.
    """
    networs_to_remove = []
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
                spf_addresses.append(str(network[0]))
            if num_addresses > 1:
                spf_addresses.append(str(network[network.num_addresses - 1]))

            networs_to_remove.append(ip_address)

    # remove IP networks
    for ip_address in networs_to_remove:
        spf_addresses.remove(ip_address)


def validate_ip6_operation_status(global_translation, rating, local_translation, ipv6_servers):
    """
    Validates IPv6 server operation status and rates it.

    Args:
        global_translation (function): Global text translator.
        local_translation (function): Local text translator.
        rating (Rating): Initial Rating object.
        ipv6_servers (list): List of IPv6 servers.

    Returns:
        rating (Rating): Updated Rating object.
    """
    ipv6_servers_operational = []
    # 1.3 - Check Start TLS
    ipv6_servers_operational_starttls = []
    for ip_address in ipv6_servers:
        try:
            # print('SMTP CONNECT:', ip_address)
            with SmtpWebperf(
                    ip_address,
                    port=25,
                    local_hostname=None,
                    timeout=get_config('general.request.timeout')) as smtp:
                ipv6_servers_operational.append(ip_address)
                smtp.starttls()
                ipv6_servers_operational_starttls.append(ip_address)
                # print('SMTP SUCCESS')
        except smtplib.SMTPConnectError as smtp_error:
            print('SMTP ERROR: ', smtp_error)

    ipv6_operational_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if len(ipv6_servers_operational) > 0 and len(ipv6_servers) == len(ipv6_servers_operational):
        ipv6_operational_rating.set_overall(5.0)
        ipv6_operational_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_IPV6_OPERATION_SUPPORT'))
    else:
        ipv6_operational_rating.set_overall(1.0)
        ipv6_operational_rating.set_standards(
            1.0, local_translation('TEXT_REVIEW_IPV6_OPERATION_NO_SUPPORT'))
    rating += ipv6_operational_rating

    ipv6_operational_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if len(ipv6_servers_operational_starttls) > 0 and\
          len(ipv6_servers) == len(ipv6_servers_operational_starttls):
        ipv6_operational_rating.set_overall(5.0)
        ipv6_operational_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_IPV6_OPERATION_STARTTLS_SUPPORT'))
    else:
        ipv6_operational_rating.set_overall(1.0)
        ipv6_operational_rating.set_standards(
            1.0, local_translation('TEXT_REVIEW_IPV6_OPERATION_STARTTLS_NO_SUPPORT'))
    rating += ipv6_operational_rating
    return rating


def validate_ip4_operation_status(global_translation, rating, local_translation, ipv4_servers):
    """
    Validates IPv4 server operation status and rates it.

    Args:
        global_translation (function): Global text translator.
        local_translation (function): Local text translator.
        rating (Rating): Initial Rating object.
        ipv4_servers (list): List of IPv4 servers.

    Returns:
        rating (Rating): Updated Rating object.
    """
    ipv4_servers_operational = []
    # 1.3 - Check Start TLS
    ipv4_servers_operational_starttls = []
    for ip_address in ipv4_servers:
        try:
            with SmtpWebperf(
                    ip_address,
                    port=25,
                    local_hostname=None,
                    timeout=get_config('general.request.timeout')) as smtp:
                ipv4_servers_operational.append(ip_address)
                smtp.starttls()
                ipv4_servers_operational_starttls.append(ip_address)
        except smtplib.SMTPConnectError as smtp_error:
            print('SMTP ERROR: ', smtp_error)

    ipv4_operational_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if len(ipv4_servers_operational) > 0 and len(ipv4_servers) == len(ipv4_servers_operational):
        ipv4_operational_rating.set_overall(5.0)
        ipv4_operational_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_IPV4_OPERATION_SUPPORT'))
    else:
        ipv4_operational_rating.set_overall(1.0)
        ipv4_operational_rating.set_standards(
            1.0, local_translation('TEXT_REVIEW_IPV4_OPERATION_NO_SUPPORT'))
    rating += ipv4_operational_rating

    ipv4_operational_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if len(ipv4_servers_operational_starttls) > 0 and\
            len(ipv4_servers) == len(ipv4_servers_operational_starttls):
        ipv4_operational_rating.set_overall(5.0)
        ipv4_operational_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_IPV4_OPERATION_STARTTLS_SUPPORT'))
    else:
        ipv4_operational_rating.set_overall(1.0)
        ipv4_operational_rating.set_standards(
            1.0, local_translation('TEXT_REVIEW_IPV4_OPERATION_STARTTLS_NO_SUPPORT'))
    rating += ipv4_operational_rating
    return rating

def get_email_entries(hostname):
    """
    Retrieves email entries for a given hostname.

    Args:
        hostname (str): The hostname to retrieve email entries for.

    Returns:
        email_entries (list): List of email entries for the hostname.
    """
    email_entries = []
    email_results = dns_lookup(hostname, dns.rdatatype.MX)
    has_mx_records = len(email_results) > 0
    if not has_mx_records:
        return email_entries

    for email_result in email_results:
        # result is in format "<priority> <domain address/ip>"
        email_result_sections = email_result.split(' ')
        if len(email_result_sections) > 1:
            server_address = email_result_sections[1]
        else:
            return email_entries

        email_entries.append(server_address)

    return email_entries

def get_addresses_for_dnstype(email_entries, rdatatype):
    """
    Retrieves addresses for a specific DNS type from email entries.

    Args:
        email_entries (list): List of email entries.
        rdatatype (int): DNS record type.

    Returns:
        ipv4_servers (list): List of servers of the specified DNS type.
    """
    ipv4_servers = []
    for email_entry in email_entries:
        ipv_4 = dns_lookup(email_entry, rdatatype)
        ipv4_servers.extend(ipv_4)
    return ipv4_servers

def validate_mx_records(global_translation, rating, result_dict, local_translation, hostname):
    """
    Validates mail exchange records and rates them based on IPv4/IPv6 usage and GDPR compliance.

    Args:
        global_translation (function): Global text translator.
        local_translation (function): Local text translator.
        rating (Rating): Initial Rating object.
        result_dict (dict): Dictionary to store results.
        hostname (str): The hostname to validate.

    Returns:
        rating (Rating): Updated Rating object.
        ipv4_servers (list): List of IPv4 servers.
        ipv6_servers (list): List of IPv6 servers.
    """
    # 1.1 - Check IPv4 and IPv6 support
    email_entries = get_email_entries(hostname)

    ipv4_servers = get_addresses_for_dnstype(email_entries, dns.rdatatype.A)
    ipv6_servers = get_addresses_for_dnstype(email_entries, dns.rdatatype.AAAA)

    email_servers = []
    email_servers.extend(ipv4_servers)
    email_servers.extend(ipv6_servers)

    rating += rate_mx_ip4_usage(global_translation, local_translation, ipv4_servers)
    rating += rate_mx_ip6_usage(global_translation, local_translation, ipv6_servers)

    # 2.0 - Check GDPR for all IP-adresses
    countries_others = {}
    countries_eu_or_exception_list = {}
    for ip_address in email_servers:
        country_code = ''
        country_code = get_best_country_code(
            ip_address, country_code)
        if country_code in ('', '-'):
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

    rating += rate_mx_gdpr(
        global_translation,
        local_translation,
        countries_others,
        countries_eu_or_exception_list)

    # add data to result of test
    result_dict["mx-addresses"] = email_entries
    result_dict["mx-ipv4-servers"] = ipv4_servers
    result_dict["mx-ipv6-servers"] = ipv6_servers
    result_dict["mx-gdpr-countries"] = countries_eu_or_exception_list
    result_dict["mx-none-gdpr-countries"] = countries_others

    return rating, ipv4_servers, ipv6_servers

def rate_mx_gdpr(
        global_translation,
        local_translation,
        countries_others,
        countries_eu_or_exception_list):
    """
    Rates the GDPR compliance of mail exchange servers.

    Args:
        global_translation (function): Global text translator.
        local_translation (function): Local text translator.
        countries_others (dict): Non-GDPR compliant countries.
        countries_eu_or_exception_list (dict): GDPR compliant countries.

    Returns:
        rating (Rating): Rating of GDPR compliance based on country lists.
    """
    rating = Rating(global_translation, get_config('general.review.improve-only'))
    nof_gdpr_countries = len(countries_eu_or_exception_list)
    nof_none_gdpr_countries = len(countries_others)
    if nof_gdpr_countries > 0:
        gdpr_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        gdpr_rating.set_overall(5.0)
        gdpr_rating.set_integrity_and_security(
            5.0, local_translation('TEXT_REVIEW_MX_GDPR').format(
                ', '.join(countries_eu_or_exception_list.keys())))
        rating += gdpr_rating
    if nof_none_gdpr_countries > 0:
        none_gdpr_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        none_gdpr_rating.set_overall(1.0)
        none_gdpr_rating.set_integrity_and_security(
            1.0, local_translation('TEXT_REVIEW_MX_NONE_GDPR').format(
                ', '.join(countries_others.keys())))
        rating += none_gdpr_rating
    return rating

def rate_mx_ip6_usage(global_translation, local_translation, ipv6_servers):
    """
    Rates the usage of IPv6 servers.

    Args:
        global_translation (function): Global text translator.
        local_translation (function): Local text translator.
        ipv6_servers (list): List of IPv6 servers.

    Returns:
        nof_ipv6_rating (Rating): Rating of IPv6 usage based on server count.
    """
    nof_ipv6_servers = len(ipv6_servers)
    nof_ipv6_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if nof_ipv6_servers >= 2:
        nof_ipv6_rating.set_overall(5.0)
        nof_ipv6_rating.set_integrity_and_security(
            5.0, local_translation('TEXT_REVIEW_IPV6_REDUNDANCE'))
        nof_ipv6_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_IPV6_SUPPORT'))
    elif nof_ipv6_servers == 1:
        # example: feber.se (do dns lookup also before)
        nof_ipv6_rating.set_overall(2.5)
        nof_ipv6_rating.set_integrity_and_security(
            1.0, local_translation('TEXT_REVIEW_IPV6_NO_REDUNDANCE'))
        nof_ipv6_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_IPV6_SUPPORT'))
    else:
        # example: huddinge.se
        nof_ipv6_rating.set_overall(1.0)
        nof_ipv6_rating.set_standards(
            1.0, local_translation('TEXT_REVIEW_IPV6_NO_SUPPORT'))

    return nof_ipv6_rating

def rate_mx_ip4_usage(global_translation, local_translation, ipv4_servers):
    """
    This function rates the usage of IPv4 servers based on their number.

    Args:
        global_translation (function): A function to translate text globally.
        local_translation (function): A function to translate text locally.
        ipv4_servers (list): A list of IPv4 servers.

    Returns:
        nof_ipv4_rating (Rating): A Rating object that represents the rating of IPv4 usage.
    """
    nof_ipv4_servers = len(ipv4_servers)
    nof_ipv4_rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))
    if nof_ipv4_servers >= 2:
        nof_ipv4_rating.set_overall(5.0)
        nof_ipv4_rating.set_integrity_and_security(
            5.0, local_translation('TEXT_REVIEW_IPV4_REDUNDANCE'))
        nof_ipv4_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_IPV4_SUPPORT'))
    elif nof_ipv4_servers == 1:
        # example: feber.se (do dns lookup also before)
        nof_ipv4_rating.set_overall(2.5)
        nof_ipv4_rating.set_integrity_and_security(
            1.0, local_translation('TEXT_REVIEW_IPV4_NO_REDUNDANCE'))
        nof_ipv4_rating.set_standards(
            5.0, local_translation('TEXT_REVIEW_IPV4_SUPPORT'))
    else:
        nof_ipv4_rating.set_overall(1.0)
        nof_ipv4_rating.set_standards(
            1.0, local_translation('TEXT_REVIEW_IPV4_NO_SUPPORT'))
    return nof_ipv4_rating
