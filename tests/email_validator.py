# -*- coding: utf-8 -*-
import smtplib
import http3
import datetime
import h2
import h11
import dns.resolver
import urllib.parse
import textwrap
import ipaddress
import hashlib
import datetime
import binascii
import base64
import sys
import socket
import ssl
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from requests.packages.urllib3.util import ssl_
# https://docs.python.org/3/library/urllib.parse.html
import urllib
from urllib.parse import urlparse
import uuid
import re
from bs4 import BeautifulSoup
import config
from models import Rating
from tests.utils import dns_lookup, httpRequestGetContent, has_redirect
import gettext
_local = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
review_show_improvements_only = config.review_show_improvements_only


def run_test(_, langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    rating = Rating(_, review_show_improvements_only)
    result_dict = {}

    language = gettext.translation(
        'http_validator', localedir='locales', languages=[langCode])
    language.install()
    _local = language.gettext

    print(_local('TEXT_RUNNING_TEST'))

    print(_('TEXT_TEST_START').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    # 1 - Get Email servers
    # dns_lookup
    email_results = dns_lookup(hostname, "MX")
    has_mx_records_rating = Rating(_, review_show_improvements_only)
    if len(email_results) > 0:
        has_mx_records_rating.set_overall(5.0)
        has_mx_records_rating.set_standards(
            5.0, _local('TEXT_REVIEW_MX_SUPPORT'))
    else:
        has_mx_records_rating.set_overall(1.0)
        has_mx_records_rating.set_standards(
            1.0, _local('TEXT_REVIEW_MX_NO_SUPPORT'))
    rating += has_mx_records_rating

    email_servers = list()
    # 1.1 - Check IPv4 and IPv6 support
    ipv4_servers = list()
    ipv6_servers = list()

    for email_result in email_results:
        # result is in format "<priority> <domain address/ip>"
        server_address = email_result.split(' ')[1]

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
            2.5, _local('TEXT_REVIEW_IPV4_NO_REDUNDANCE'))
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
        nof_ipv4_rating.set_integrity_and_security(
            5.0, _local('TEXT_REVIEW_IPV6_REDUNDANCE'))
        nof_ipv4_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IPV6_SUPPORT'))
    elif nof_ipv6_servers == 1:
        # example: feber.se (do dns lookup also before)
        nof_ipv6_rating.set_overall(2.5)
        nof_ipv4_rating.set_integrity_and_security(
            2.5, _local('TEXT_REVIEW_IPV6_NO_REDUNDANCE'))
        nof_ipv4_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IPV6_SUPPORT'))
    else:
        # example: huddinge.se
        nof_ipv6_rating.set_overall(1.0)
        nof_ipv6_rating.set_standards(
            1.0, _local('TEXT_REVIEW_IPV6_NO_SUPPORT'))
    rating += nof_ipv6_rating

    # 1.2 - Check operational
    ipv4_servers_operational = list()
    # 1.3 - Check Start TLS
    ipv4_servers_operational_starttls = list()
    for ip_address in ipv4_servers:
        try:
            # print('SMTP CONNECT:', ip_address)
            with smtplib.SMTP(ip_address, port=25, timeout=request_timeout) as smtp:
                ipv4_servers_operational.append(ip_address)
                smtp.starttls()
                ipv4_servers_operational_starttls.append(ip_address)
            # print('SMTP SUCCESS')
        except smtplib.SMTPConnectError as smtp_error:
            print('SMTP ERROR: ', smtp_error)
        except Exception as error:
            # If you get this error on all sites you test against, please verfiy that your provider is not blocking port 25.
            print('GENERAL ERROR: ', error)
    # 1.2 - Check operational
    ipv6_servers_operational = list()
    # 1.3 - Check Start TLS
    ipv6_servers_operational_starttls = list()
    for ip_address in ipv6_servers:
        try:
            # print('SMTP CONNECT:', ip_address)
            with smtplib.SMTP(ip_address, port=25, timeout=request_timeout) as smtp:
                ipv6_servers_operational.append(ip_address)
                smtp.starttls()
                ipv6_servers_operational_starttls.append(ip_address)
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

    # 1.4 - Check TLS
    # 1.5 - Check PKI
    # 1.6 - Check DNSSEC
    # 1.7 - Check DANE
    # 2.0 - Check GDPR for all IP-adresses
    # for ip_address in email_servers:

    # nof_checks = 0
    # check_url = True

    # while check_url and nof_checks < 10:
    #     checked_url_rating = validate_url(url, _, _local)

    #     redirect_result = has_redirect(url)
    #     check_url = redirect_result[0]
    #     url = redirect_result[1]
    #     nof_checks += 1

    #     rating += checked_url_rating

    # if nof_checks > 1:
    #     rating.overall_review += _local('TEXT_REVIEW_SCORE_IS_DIVIDED').format(
    #         nof_checks)

    # if len(review) == 0:
    #    review = _('TEXT_REVIEW_NO_REMARKS')

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)
