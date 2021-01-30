# -*- coding: utf-8 -*-
import http3
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
import urllib  # https://docs.python.org/3/library/urllib.parse.html
from urllib.parse import urlparse
import uuid
import re
from bs4 import BeautifulSoup
import config
from tests.utils import httpRequestGetContent, has_redirect
import gettext
_ = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent


def run_test(langCode, url):
    """
    Only work on a domain-level. Returns tuple with decimal for grade and string with review
    """

    points = 0.0
    review = ''
    result_dict = {}

    # language = gettext.translation(
    #    'certificate_check', localedir='locales', languages=[langCode])
    # language.install()
    # _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

    nof_checks = 0
    check_url = True

    while check_url and nof_checks < 10:
        review += '* Result for: ' + url + '\r\n'
        url_result = validate_url(url)
        points += url_result[0]
        review += url_result[1]

        redirect_result = has_redirect(url)
        check_url = redirect_result[0]
        url = redirect_result[1]
        nof_checks += 1

    if nof_checks > 1:
        review += '* Score is divided by {0} (number of urls tested with redirects)'.format(
            nof_checks)

    points = points / nof_checks

    if len(review) == 0:
        review = _('TEXT_REVIEW_NO_REMARKS')

    if points < 1.0:
        points = 1.0

    return (points, review, result_dict)


def validate_url(url):
    points = 0.0
    review = ''

    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    result = http_to_https_score(url)
    points += result[0]
    review += result[1]

    result = tls_version_score(hostname)
    points += result[0]
    review += '- TLS Version(s):\r\n'
    review += result[1]

    result = ip_version_score(hostname)
    points += result[0]
    review += '- IP Version(s):\r\n'
    review += result[1]

    result = dns_score(hostname)
    points += result[0]
    review += '- DNS Info:\r\n'
    review += result[1]

    result = http_version_score(hostname, url)
    points += result[0]
    review += '- HTTP Version(s):\r\n'
    review += result[1]

    return (points, review)


def http_to_https_score(url):
    http_url = ''

    o = urllib.parse.urlparse(url)

    if (o.scheme == 'https'):
        http_url = url.replace('https://', 'http://')
    else:
        http_url = url

    redirect_result = has_redirect(http_url)

    result_url = ''
    if (redirect_result[0]):
        result_url = redirect_result[1]
    else:
        result_url = http_url

    if result_url == None:
        return (0.0, '- Unable to verify HTTP to HTTPS redirect (0.0 points)\r\n')

    result_url_o = urllib.parse.urlparse(result_url)

    if (result_url_o.scheme == 'http'):
        return (0.0, '- No HTTP to HTTPS redirect (0.0 points)\r\n')
    else:
        return (1.0, '- HTTP to HTTPS redirect (1.0 points)\r\n')


def dns_score(hostname):
    result = dns_lookup('_esni.' + hostname, "TXT")

    if result[0]:
        return (1.0, '-- Have ESNI record (+1.0 points)\r\n')

    return (0.0, '-- No ESNI record found (0.0 points)\r\n')


def ip_version_score(hostname):
    ip4_result = dns_lookup(hostname, "A")

    ip6_result = dns_lookup(hostname, "AAAA")

    if ip4_result[0] and ip6_result[0]:
        return (1.0, '-- Both IPv4 and IPv6 support (+1.0 points)\r\n')

    if ip6_result[0]:
        return (0.5, '-- Only IPv6 support (+0.5 points)\r\n')

    if ip4_result[0]:
        return (0.5, '-- Only IPv4 support (+0.5 points)\r\n')

    return (0.0, '-- Unable to get IP version info\r\n')


def tls_version_score(hostname):
    points = 0.0
    review = ''
    # TODO: check cipher security
    result_not_validated = has_tls13(hostname, False)
    result_validated = has_tls13(hostname, True)

    if result_not_validated[0] and result_validated[0]:
        points += 0.6
        review += '-- TLSv1.3 support (+0.6 points)\r\n'
    elif result_not_validated[0]:
        review += '-- TLSv1.3 support but wrong certificate (0.0 points)\r\n'
    else:
        review += '-- No TLSv1.3 support (0.0 points)\r\n'

    result_not_validated = has_tls12(hostname, False)
    result_validated = has_tls12(hostname, True)

    if result_not_validated[0] and result_validated[0]:
        points += 0.4
        review += '-- TLSv1.2 support (+0.4 points)\r\n'
    elif result_not_validated[0]:
        review += '-- TLSv1.2 support but wrong certificate (0.0 points)\r\n'
    else:
        review += '-- No TLSv1.2 support (0.0 points)\r\n'

    result_not_validated = has_tls11(hostname, False)
    result_validated = has_tls11(hostname, True)

    if result_not_validated[0] and result_validated[0]:
        points = 0.0
        review += '-- TLSv1.1 support, is insecure (=0.0 points)\r\n'
    elif result_not_validated[0]:
        points = 0.0
        review += '-- TLSv1.1 support but wrong certificate, is insecure (=0.0 points)\r\n'

    result_not_validated = has_tls10(hostname, False)
    result_validated = has_tls10(hostname, True)

    if result_not_validated[0] and result_validated[0]:
        points = 0.0
        review += '-- TLSv1.0 support, is insecure (=0.0 points)\r\n'
    elif result_validated[0]:
        points = 0.0
        review += '-- TLSv1.0 support but wrong certificate, is insecure (=0.0 points)\r\n'

    return (points, review)


def dns_lookup(hostname, record_type):
    try:
        dns_record = dns.resolver.query(hostname, record_type)
    except dns.resolver.NXDOMAIN:
        return (False, "No record found")
    except (dns.resolver.NoAnswer, dns.resolver.NoNameservers) as error:
        return (False, error)

    record = '' + str(dns_record[0])
    return (True, record)


def http_version_score(hostname, url):
    points = 0.0
    review = ''

    result = check_http11(hostname)
    if result[0]:
        points += 0.5
        review += '-- HTTPv1.1 support (+0.5 points)\r\n'

    result = check_http2(hostname)
    if result[0]:
        points += 0.5
        review += '-- HTTPv2 support (+0.5 points)\r\n'

    # If we still have 0.0 points something must have gone wrong, try fallback
    if points == 0.0:
        result = check_http_fallback(url)
        if result[0]:
            points += 0.5
            review += '-- HTTPv1.1 support (+0.5 points)\r\n'
        if result[1]:
            points += 0.5
            review += '-- HTTPv2 support (+0.5 points)\r\n'

    return (points, review)


def check_http11(hostname):
    try:
        socket.setdefaulttimeout(10)
        conn = ssl.create_default_context()
        conn.set_alpn_protocols(['http/1.1'])
        try:
            conn.set_npn_protocols(["http/1.1"])
        except NotImplementedError:
            pass

        ssock = conn.wrap_socket(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname=hostname)
        ssock.connect((hostname, 443))

        negotiated_protocol = ssock.selected_alpn_protocol()
        if negotiated_protocol is None:
            negotiated_protocol = ssock.selected_npn_protocol()

        if negotiated_protocol == "http/1.1":
            return (True, "http/1.1")
        else:
            return (False, "http/1.1")
    except Exception:
        return (False, "http/1.1")


def check_http2(hostname):
    try:
        socket.setdefaulttimeout(10)
        conn = ssl.create_default_context()
        conn.set_alpn_protocols(['h2'])
        try:
            conn.set_npn_protocols(["h2"])
        except NotImplementedError:
            pass
        ssock = conn.wrap_socket(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname=hostname)
        ssock.connect((hostname, 443))

        negotiated_protocol = ssock.selected_alpn_protocol()
        if negotiated_protocol is None:
            negotiated_protocol = ssock.selected_npn_protocol()

        if negotiated_protocol == "h2":
            return (True, "http2")
        else:
            return (False, "http2")
    except Exception:
        return (False, "http2")


def check_http_fallback(url):
    has_http2 = False
    has_http11 = False
    try:
        r = http3.get(url, allow_redirects=True)

        has_http2 = r.protocol == "HTTP/2"
        has_http11 = r.protocol == "HTTP1.1"
    except ssl.CertificateError as error:
        print(error)
        pass
    except Exception as e:
        print(e)
        pass

    if not has_http11:
        # This call only supports HTTP/1.1
        content = httpRequestGetContent(url, True)
        if '</html>' in content:
            has_http11 = True

    return (has_http11, has_http2)


def has_tls13(hostname, validate_hostname):
    assert ssl.HAS_TLSv1_3
    conn = ssl.create_default_context()

    # Ensure we validate certificate provided with the hostname
    if validate_hostname:
        conn.load_default_certs()
        conn.verify_mode = ssl.CERT_REQUIRED
        conn.check_hostname = True

    try:
        socket.setdefaulttimeout(10)
        with socket.create_connection((hostname, 443)) as sock:
            with conn.wrap_socket(sock,
                                  server_hostname=hostname) as ssock:
                protocol = ssock.version()
    except (ConnectionRefusedError, ConnectionResetError):
        return (False, "Unable to connect to port 443")
    except ssl.CertificateError as error:
        return (False, error.reason)
    except ssl.SSLError as error:
        return (False, error.reason)
    except socket.gaierror:
        return (False, "Hostname lookup failed")
    except socket.timeout:
        return (False, "Hostname connection failed")
    if protocol == "TLSv1.3":
        return (True, protocol)
    else:
        return (False, f"{hostname} supports {protocol}")


def has_tls12(hostname, validate_hostname):
    assert ssl.HAS_TLSv1_2
    conn = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

    # Ensure we validate certificate provided with the hostname
    if validate_hostname:
        conn.load_default_certs()
        conn.verify_mode = ssl.CERT_REQUIRED
        conn.check_hostname = True

    try:
        socket.setdefaulttimeout(10)
        with socket.create_connection((hostname, 443)) as sock:
            with conn.wrap_socket(sock,
                                  server_hostname=hostname) as ssock:
                protocol = ssock.version()
    except (ConnectionRefusedError, ConnectionResetError):
        return (False, "Unable to connect to port 443")
    except ssl.SSLError as error:
        return (False, error.reason)
    except ssl.CertificateError as error:
        return (False, error.reason)
    except socket.gaierror:
        return (False, "Hostname lookup failed")
    except socket.timeout:
        return (False, "Hostname connection failed")
    if protocol == "TLSv1.2":
        return (True, protocol)
    else:
        return (False, f"{hostname} supports {protocol}")


def has_tls11(hostname, validate_hostname):
    assert ssl.HAS_TLSv1_1
    conn = ssl.SSLContext(ssl.PROTOCOL_TLSv1_1)

    # Ensure we validate certificate provided with the hostname
    if validate_hostname:
        conn.load_default_certs()
        conn.verify_mode = ssl.CERT_REQUIRED
        conn.check_hostname = True

    try:
        socket.setdefaulttimeout(10)
        with socket.create_connection((hostname, 443)) as sock:
            with conn.wrap_socket(sock,
                                  server_hostname=hostname) as ssock:
                protocol = ssock.version()
    except (ConnectionRefusedError, ConnectionResetError):
        return (False, "Unable to connect to port 443")
    except ssl.SSLError as error:
        return (False, error.reason)
    except ssl.CertificateError as error:
        return (False, error.reason)
    except socket.gaierror:
        return (False, "Hostname lookup failed")
    except socket.timeout:
        return (False, "Hostname connection failed")
    if protocol == "TLSv1.1":
        return (True, protocol)
    else:
        return (False, f"{hostname} supports {protocol}")


def has_tls10(hostname, validate_hostname):
    assert ssl.HAS_TLSv1
    conn = ssl.SSLContext(ssl.PROTOCOL_TLSv1)

    # Ensure we validate certificate provided with the hostname
    if validate_hostname:
        conn.load_default_certs()
        conn.verify_mode = ssl.CERT_REQUIRED
        conn.check_hostname = True

    try:
        socket.setdefaulttimeout(10)
        with socket.create_connection((hostname, 443)) as sock:
            with conn.wrap_socket(sock,
                                  server_hostname=hostname) as ssock:
                protocol = ssock.version()
    except (ConnectionRefusedError, ConnectionResetError):
        return (False, "Unable to connect to port 443")
    except ssl.SSLError as error:
        return (False, error.reason)
    except ssl.CertificateError as error:
        return (False, error.reason)
    except socket.gaierror:
        return (False, "Hostname lookup failed")
    except socket.timeout:
        return (False, "Hostname connection failed")
    if protocol == "TLSv1.0":
        return (True, protocol)
    else:
        return (False, f"{hostname} supports {protocol}")
