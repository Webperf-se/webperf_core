# -*- coding: utf-8 -*-
import http3
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
from tests.utils import *
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

    url1_result = check_url(url)
    points += url1_result[0]

    redirect_result = has_redirect(url)
    if (redirect_result[0]):
        review += '* Domain before redirect:\r\n'
        review += url1_result[1]

        url2_result = check_url(redirect_result[1])
        points += url2_result[0]
        review += '* Domain after redirect:\r\n'
        review += url2_result[1]
        points /= 2
    else:
        review += url1_result[1]

    #print('DNS Info:', result)

    # print('\r\n\r\n')

    #result = check_http_version(o.netloc)
    #print('HTTP version(any):', result)
    #result = check_http11(o.netloc)
    #print('HTTPv1.1:', result)
    #result = check_http2(o.netloc)
    #print('HTTPv2:', result)

    #result = check_http3(url)
    #print('HTTPv3:', result)

    #result = test(o.netloc)
    #print('TEST:', result)

    # httpRequestGetContent(url)
    #print('TEST2:', result)

    if len(review) == 0:
        review = _('TEXT_REVIEW_NO_REMARKS')

    if points == 0:
        points = 1.0

    return (points, review, result_dict)


def check_url(url):
    points = 0.0
    review = ''

    o = urllib.parse.urlparse(url)
    #hostname = o.netloc
    hostname = o.hostname
    #print('TEST:', o.hostname)
    # url = '{0}://{1}/{3}/{2}'.format(o.scheme, o.netloc,
    #                                 'finns-det-en-sida/pa-den-har-adressen/testanrop/', get_guid(5))

    result = http_to_https_score(url)
    points += result[0]
    review += result[1]

    result = tls_version_score(hostname)
    points += result[0]
    review += '- TLS Version:\r\n'
    review += result[1]
    #print('TLS Version(s):', result[1])

    result = ip_version_score(hostname)
    points += result[0]
    review += '- IP Version:\r\n'
    review += result[1]
    #print('IP Version:', result)

    result = dns_score(hostname)
    points += result[0]
    review += '- DNS Info:\r\n'
    review += result[1]

    return (points, review)


def http_to_https_score(url):
    http_url = ''
    https_url = ''

    o = urllib.parse.urlparse(url)

    if (o.scheme == 'https'):
        https_url = url
        http_url = url.replace('https://', 'http://')
    else:
        http_url = url
        https_url = url.replace('http://', 'https://')

    redirect_result = has_redirect(http_url)
    result_url = ''
    if (redirect_result[0]):
        result_url = redirect_result[1]
    else:
        result_url = redirect_result[1]

    result_url_o = urllib.parse.urlparse(result_url)

    if (result_url_o.scheme == 'http'):
        return (0.0, '- No HTTP to HTTPS redirect (0.0 points)\r\n')
    else:
        return (1.0, '- HTTP to HTTPS redirect (1.0 points)\r\n')

    # if result[0]:
    #    return (1.0, '-- Have ESNI record (+1.0 points)\r\n')


def dns_score(hostname):
    result = dns_lookup('_esni.' + hostname, "TXT")

    if result[0]:
        return (1.0, '-- Have ESNI record (+1.0 points)\r\n')

    return (0.0, '-- No ESNI record found (0.0 points)\r\n')


def ip_version_score(hostname):
    # TODO: check for sub domain (for example redirect from dn.se -> www.dn.se)
    ip4_result = dns_lookup(hostname, "A")
    #print('IPv4:', ip4_result)

    ip6_result = dns_lookup(hostname, "AAAA")
    #print('IPv6:', result)

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
    # TODO: Check for insecure versions (ALL SSL, TLS 1.0 and TLS 1.1)
    result = has_tls13(hostname)
    #print(' - TLS v1.3:', result)
    if result[0]:
        points += 0.8
        review += '-- TLS 1.3 support (+0.8 points)\r\n'
    else:
        review += '-- No TLS 1.3 support\r\n'
    #    return (1.0, result[1])

    result = has_tls12(hostname)
    #print(' - TLS v1.2:', result)
    if result[0]:
        points += 0.2
        review += '-- TLS 1.2 support (+0.2 points)\r\n'
    else:
        review += '-- No TLS 1.2 support\r\n'
    #    return (0.5, result[1])

    result = has_tls11(hostname)
    #print(' - TLS v1.1:', result)
    if result[0]:
        points = 0.0
        review += '-- TLS 1.1 INSECURE support (-1.0 points)\r\n'
    #    return (0.1, result[1])

    result = has_tls10(hostname)
    #print(' - TLS v1.0:', result)
    if result[0]:
        points = 0.0
        review += '-- TLS 1.0 INSECURE support (-1.0 points)\r\n'
    #    return (0.1, result[1])

    return (points, review)


def dns_lookup(hostname, record_type):
    """Look up _esni TXT record for a hostname.
    Resolves the _esni TXT (_esni.hostname) record, which has the ESNI keys
    that we later check for validity.
    :return tuple: (True, record) if the lookup was successful,
                   (False, error) if it failed
    """
    try:
        dns_record = dns.resolver.query(hostname, record_type)
    except dns.resolver.NXDOMAIN:
        return (False, "No record found")
    except (dns.resolver.NoAnswer, dns.resolver.NoNameservers) as error:
        return (False, error)

    # print('first dns', dns_record[0])
    record = '' + str(dns_record[0])
    # record = dns_record[0].strings[0]
    return (True, record)


def check_http_version(hostname):
    try:
        socket.setdefaulttimeout(10)
        conn = ssl.create_default_context()
        conn.set_alpn_protocols(['h2', 'spdy/3', 'http/1.1', 'http/1.0'])

        ssock = conn.wrap_socket(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname=hostname)
        ssock.connect((hostname, 443))

        pp = ssock.selected_alpn_protocol()

        if pp != None:
            return (True, pp)
        else:
            return (False, "None")
    except Exception as e:
        print(e)


def check_http11(hostname):
    try:
        socket.setdefaulttimeout(10)
        conn = ssl.create_default_context()
        conn.set_alpn_protocols(['http/1.1'])

        ssock = conn.wrap_socket(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname=hostname)
        ssock.connect((hostname, 443))

        pp = ssock.selected_alpn_protocol()
        print('HTTPv1.1:', pp)
        if pp == "http/1.1":
            return (True, "http/1.1")
        else:
            return (False, "http/1.1")
    except Exception as e:
        print(e)


def check_http2(hostname):
    try:
        socket.setdefaulttimeout(10)
        conn = ssl.create_default_context()
        # conn.set_alpn_protocols(['h2', 'spdy/3', 'http/1.1'])
        conn.set_alpn_protocols(['h2'])

        ssock = conn.wrap_socket(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname=hostname)
        ssock.connect((hostname, 443))

        pp = ssock.selected_alpn_protocol()
        print('HTTPv2:', pp)

        if pp == "h2":
            return (True, "http2")
        else:
            return (False, "http2")
    except Exception as e:
        print(e)


def check_http3(url):
    try:
        r = http3.get(url, allow_redirects=True)

        pp = r.protocol
        print('HTTPv3:', pp)

        if pp == "HTTP/3":
            return (True, "http3")
        else:
            return (False, "http3")
    except Exception as e:
        print(e)


def test(hostname):
    """Check if the hostname supports TLSv1.3

    TLSv1.3 is required for ESNI so this method connects to the server and
    tries to initiate a connection using that. If the connection is
    successful, we confirm TLSv1.3 support, otherwise we return the highest
    protocol supported by the server.

    Note that as per the documentation, `create_default_context` uses
    `ssl.PROTOCOL_TLS`, which in turn selects the highest protocol version
    that both the client and the server support.

    :return tuple: (True, protocol) if TLSv1.3 is supported,
                   (False, protocol with error message) if it is not
    """
    conn = ssl.create_default_context()
    try:
        socket.setdefaulttimeout(10)
        with socket.create_connection((hostname, 443)) as sock:
            with conn.wrap_socket(sock,
                                  server_hostname=hostname) as ssock:
                protocol = ssock.version()
                print('TEST', ssock.getpeername())
    except (ConnectionRefusedError, ConnectionResetError):
        return (False, "Unable to connect to port 443")
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


def has_tls13(hostname):
    """Check if the hostname supports TLSv1.3

    TLSv1.3 is required for ESNI so this method connects to the server and
    tries to initiate a connection using that. If the connection is
    successful, we confirm TLSv1.3 support, otherwise we return the highest
    protocol supported by the server.

    Note that as per the documentation, `create_default_context` uses
    `ssl.PROTOCOL_TLS`, which in turn selects the highest protocol version
    that both the client and the server support.

    :return tuple: (True, protocol) if TLSv1.3 is supported,
                   (False, protocol with error message) if it is not
    """
    assert ssl.HAS_TLSv1_3
    conn = ssl.create_default_context()
    try:
        socket.setdefaulttimeout(10)
        with socket.create_connection((hostname, 443)) as sock:
            with conn.wrap_socket(sock,
                                  server_hostname=hostname) as ssock:
                protocol = ssock.version()
                #print('TEST v1.3', ssock.cipher())
    except (ConnectionRefusedError, ConnectionResetError):
        return (False, "Unable to connect to port 443")
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


def has_tls12(hostname):
    """Check if the hostname supports TLSv1.2

    TLSv1.2 is required for ESNI so this method connects to the server and
    tries to initiate a connection using that. If the connection is
    successful, we confirm TLSv1.2 support, otherwise we return the highest
    protocol supported by the server.

    Note that as per the documentation, `create_default_context` uses
    `ssl.PROTOCOL_TLS`, which in turn selects the highest protocol version
    that both the client and the server support.

    :return tuple: (True, protocol) if TLSv1.2 is supported,
                   (False, protocol with error message) if it is not
    """
    assert ssl.HAS_TLSv1_2
    #conn = ssl.create_default_context()
    conn = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    try:
        socket.setdefaulttimeout(10)
        with socket.create_connection((hostname, 443)) as sock:
            with conn.wrap_socket(sock,
                                  server_hostname=hostname) as ssock:
                protocol = ssock.version()
                #print('TEST v1.2', ssock.cipher())
    except (ConnectionRefusedError, ConnectionResetError):
        return (False, "Unable to connect to port 443")
    except ssl.SSLError as error:
        return (False, error.reason)
    except socket.gaierror:
        return (False, "Hostname lookup failed")
    except socket.timeout:
        return (False, "Hostname connection failed")
    if protocol == "TLSv1.2":
        return (True, protocol)
    else:
        return (False, f"{hostname} supports {protocol}")


def has_tls11(hostname):
    """Check if the hostname supports TLSv1.1

    TLSv1.1 is required for ESNI so this method connects to the server and
    tries to initiate a connection using that. If the connection is
    successful, we confirm TLSv1.1 support, otherwise we return the highest
    protocol supported by the server.

    Note that as per the documentation, `create_default_context` uses
    `ssl.PROTOCOL_TLS`, which in turn selects the highest protocol version
    that both the client and the server support.

    :return tuple: (True, protocol) if TLSv1.1 is supported,
                   (False, protocol with error message) if it is not
    """
    assert ssl.HAS_TLSv1_1
    #conn = ssl.create_default_context()
    conn = ssl.SSLContext(ssl.PROTOCOL_TLSv1_1)
    try:
        socket.setdefaulttimeout(10)
        with socket.create_connection((hostname, 443)) as sock:
            with conn.wrap_socket(sock,
                                  server_hostname=hostname) as ssock:
                protocol = ssock.version()
                #print('TEST v1.1', ssock.cipher())
    except (ConnectionRefusedError, ConnectionResetError):
        return (False, "Unable to connect to port 443")
    except ssl.SSLError as error:
        return (False, error.reason)
    except socket.gaierror:
        return (False, "Hostname lookup failed")
    except socket.timeout:
        return (False, "Hostname connection failed")
    if protocol == "TLSv1.1":
        return (True, protocol)
    else:
        return (False, f"{hostname} supports {protocol}")


def has_tls10(hostname):
    """Check if the hostname supports TLSv1.0

    TLSv1.0 is required for ESNI so this method connects to the server and
    tries to initiate a connection using that. If the connection is
    successful, we confirm TLSv1.0 support, otherwise we return the highest
    protocol supported by the server.

    Note that as per the documentation, `create_default_context` uses
    `ssl.PROTOCOL_TLS`, which in turn selects the highest protocol version
    that both the client and the server support.

    :return tuple: (True, protocol) if TLSv1.0 is supported,
                   (False, protocol with error message) if it is not
    """
    assert ssl.HAS_TLSv1
    #conn = ssl.create_default_context()
    conn = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    try:
        socket.setdefaulttimeout(10)
        with socket.create_connection((hostname, 443)) as sock:
            with conn.wrap_socket(sock,
                                  server_hostname=hostname) as ssock:
                protocol = ssock.version()
                #print('TEST v1.0', ssock.cipher())
    except (ConnectionRefusedError, ConnectionResetError):
        return (False, "Unable to connect to port 443")
    except ssl.SSLError as error:
        return (False, error.reason)
    except socket.gaierror:
        return (False, "Hostname lookup failed")
    except socket.timeout:
        return (False, "Hostname connection failed")
    if protocol == "TLSv1.0":
        return (True, protocol)
    else:
        return (False, f"{hostname} supports {protocol}")
