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

    language = gettext.translation(
        'http_validator', localedir='locales', languages=[langCode])
    language.install()
    _ = language.gettext

    print(_('TEXT_RUNNING_TEST'))

    nof_checks = 0
    check_url = True

    while check_url and nof_checks < 10:
        review += _('TEXT_REVIEW_RESULT_FOR').format(url)
        url_result = validate_url(url, _)
        points += url_result[0]
        review += url_result[1]

        redirect_result = has_redirect(url)
        check_url = redirect_result[0]
        url = redirect_result[1]
        nof_checks += 1

    if nof_checks > 1:
        review += _('TEXT_REVIEW_SCORE_IS_DIVIDED').format(
            nof_checks)

    points = points / nof_checks

    if len(review) == 0:
        review = _('TEXT_REVIEW_NO_REMARKS')

    if points < 1.0:
        points = 1.0

    return (points, review, result_dict)


def validate_url(url, _):
    points = 0.0
    review = ''

    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    result = http_to_https_score(url, _)
    points += result[0]
    review += result[1]

    result = tls_version_score(url, _)

    points += result[0]
    review += _('TEXT_REVIEW_TLS_VERSION')
    review += result[1]

    result = ip_version_score(hostname, _)
    points += result[0]
    review += _('TEXT_REVIEW_IP_VERSION')
    review += result[1]

    result = http_version_score(hostname, url, _)
    points += result[0]
    review += _('TEXT_REVIEW_HTTP_VERSION')
    review += result[1]

    return (points, review)


def http_to_https_score(url, _):
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
        return (0.0, _('TEXT_REVIEW_HTTP_TO_HTTP_REDIRECT_UNABLE_TO_VERIFY'))

    result_url_o = urllib.parse.urlparse(result_url)

    if (result_url_o.scheme == 'http'):
        return (0.0, _('TEXT_REVIEW_HTTP_TO_HTTP_REDIRECT_NO_REDIRECT'))
    else:
        return (1.0, _('TEXT_REVIEW_HTTP_TO_HTTP_REDIRECT_REDIRECTED'))


def dns_score(hostname, _):
    result = dns_lookup('_esni.' + hostname, "TXT")

    if result[0]:
        return (1.0, _('TEXT_REVIEW_DNS_HAS_ESNI'))

    return (0.0, _('TEXT_REVIEW_DNS_NO_ESNI'))


def ip_version_score(hostname, _):
    ip4_result = dns_lookup(hostname, "A")

    ip6_result = dns_lookup(hostname, "AAAA")

    if ip4_result[0] and ip6_result[0]:
        return (1.0, _('TEXT_REVIEW_IP_VERSION_BOTH_IPV4_AND_IPV6'))

    if ip6_result[0]:
        return (0.5, _('TEXT_REVIEW_IP_VERSION_IPV6'))

    if ip4_result[0]:
        return (0.5, _('TEXT_REVIEW_IP_VERSION_IPV4'))

    return (0.0, _('TEXT_REVIEW_IP_VERSION_UNABLE_TO_VERIFY'))


def protocol_version_score(url, protocol_version, _):
    points = 0.0
    review = ''
    result_not_validated = (False, '')
    result_validated = (False, '')

    protocol_rule = False
    protocol_name = ''
    protocol_translate_name = ''
    protocol_is_secure = False

    try:
        if protocol_version == ssl.PROTOCOL_TLS:
            protocol_name = 'TLSv1.3'
            protocol_translate_name = 'TLS1_3'
            assert ssl.HAS_TLSv1_3
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2
            protocol_is_secure = True
        elif protocol_version == ssl.PROTOCOL_TLSv1_2:
            protocol_name = 'TLSv1.2'
            protocol_translate_name = 'TLS1_2'
            assert ssl.HAS_TLSv1_2
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_3
            protocol_is_secure = True
        elif protocol_version == ssl.PROTOCOL_TLSv1_1:
            protocol_name = 'TLSv1.1'
            protocol_translate_name = 'TLS1_1'
            assert ssl.HAS_TLSv1_1
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
            protocol_is_secure = False
        elif protocol_version == ssl.PROTOCOL_TLSv1:
            protocol_name = 'TLSv1.0'
            protocol_translate_name = 'TLS1_0'
            assert ssl.HAS_TLSv1
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
            protocol_is_secure = False
        elif protocol_version == ssl.PROTOCOL_SSLv3:
            protocol_name = 'SSLv3'
            protocol_translate_name = 'SSL3_0'
            assert ssl.HAS_SSLv3
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
            protocol_is_secure = False
        elif protocol_version == ssl.PROTOCOL_SSLv2:
            protocol_name = 'SSLv2'
            protocol_translate_name = 'SSL2_0'
            protocol_rule = ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
            assert ssl.HAS_SSLv2
            protocol_is_secure = False

        result_not_validated = has_protocol_version(
            url, False, protocol_rule)

        result_validated = has_protocol_version(
            url, True, protocol_rule)

        has_full_support = result_not_validated[0] and result_validated[0]
        has_wrong_cert = result_not_validated[0]

        if has_full_support:
            if protocol_is_secure:
                points += 0.5
            review += _('TEXT_REVIEW_' +
                        protocol_translate_name + '_SUPPORT')
        elif has_wrong_cert:
            review += _('TEXT_REVIEW_' +
                        protocol_translate_name + '_SUPPORT_WRONG_CERT')
        else:
            review += _('TEXT_REVIEW_' +
                        protocol_translate_name + '_NO_SUPPORT')
            if not protocol_is_secure:
                points += 0.5

        result_weak_cipher = (False, 'unset')
        try:
            result_weak_cipher = has_weak_cipher(
                url, protocol_rule)
        except ssl.SSLError as sslex:
            print('error weak_cipher', sslex)
            pass
        if result_weak_cipher[0]:
            review += _('TEXT_REVIEW_' +
                        protocol_translate_name + '_WEAK_CIPHERS')
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

    return (points, review)


def tls_version_score(orginal_url, _):
    points = 0.0
    review = ''

    url = orginal_url.replace('http://', 'https://')

    # TODO: check cipher security
    # TODO: re add support for identify wrong certificate

    try:
        result = protocol_version_score(url, ssl.PROTOCOL_TLS, _)
        points += result[0]
        review += result[1]
    except:
        pass

    try:
        result = protocol_version_score(url, ssl.PROTOCOL_TLSv1_2, _)
        points += result[0]
        review += result[1]
    except:
        pass

    try:
        result = protocol_version_score(url, ssl.PROTOCOL_TLSv1_1, _)
        points += result[0]
        review += result[1]
    except:
        pass

    try:
        result = protocol_version_score(url, ssl.PROTOCOL_TLSv1, _)
        points += result[0]
        review += result[1]
    except:
        pass

    try:
        # HOW TO ENABLE SSLv3, https://askubuntu.com/questions/893155/simple-way-of-enabling-sslv2-and-sslv3-in-openssl
        result = protocol_version_score(url, ssl.PROTOCOL_SSLv3, _)
        points += result[0]
        review += result[1]
    except:
        pass

    try:
        # HOW TO ENABLE SSLv2, https://askubuntu.com/questions/893155/simple-way-of-enabling-sslv2-and-sslv3-in-openssl
        result = protocol_version_score(url, ssl.PROTOCOL_SSLv2, _)
        points += result[0]
        review += result[1]
    except:
        pass

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


def http_version_score(hostname, url, _):
    points = 0.0
    review = ''

    result = check_http11(hostname)
    if result[0]:
        points += 0.5
        review += _('TEXT_REVIEW_HTTP_VERSION_HTTP_1_1')

    result = check_http2(hostname)
    if result[0]:
        points += 0.5
        review += _('TEXT_REVIEW_HTTP_VERSION_HTTP_2')

    # If we still have 0.0 points something must have gone wrong, try fallback
    if points == 0.0:
        result = check_http_fallback(url)
        if result[0]:
            points += 0.5
            review += _('TEXT_REVIEW_HTTP_VERSION_HTTP_1_1')
        if result[1]:
            points += 0.5
            review += _('TEXT_REVIEW_HTTP_VERSION_HTTP_2')

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

    try:
        if not has_http11:
            # This call only supports HTTP/1.1
            content = httpRequestGetContent(url, True)
            if '</html>' in content:
                has_http11 = True
    except Exception as e:
        # Probably a CERT validation error, ignore
        print(e)
        pass

    return (has_http11, has_http2)


# Read post at: https://hussainaliakbar.github.io/restricting-tls-version-and-cipher-suites-in-python-requests-and-testing-wireshark/
WEAK_CIPHERS = (
    'ECDH+AES128+CBC+SHA:'
    'ECDH+AES256+CBC+SHA:'
    'RSA+AES128+GCM+SHA256:'
    'RSA+AES256+GCM+SHA:'
    'RSA+AES256+GCM+SHA:'
    'RSA+3DES+EDE+CBC+SHA'


    # 'RSA+CAMELLIA128:RSA+CAMELLIA256:'
    # 'ECDH+AES256:ECDH+AES128:ECDH+3DES:'
    # 'DH+3DES:'
    # 'RSA+AESGCM:RSA+AES:RSA+3DES:'
    # 'aNULL:'
    # 'eNULL:MD5'
)


class TlsAdapterCiphers(HTTPAdapter):

    def __init__(self, ssl_options=0, **kwargs):
        self.ssl_options = ssl_options
        super(TlsAdapterCiphers, self).__init__(**kwargs)

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
        return super(TlsAdapterCiphers, self).proxy_manager_for(*args, **kwargs)


def has_weak_cipher(url, protocol_version):
    session = False

    try:
        print('ssl._DEFAULT_CIPHERS', ssl._DEFAULT_CIPHERS)

        session = requests.session()
        adapter = TlsAdapterCiphers(protocol_version)

        session.mount(url, adapter)

    except ssl.SSLError as sslex:
        print('### No weak cipher support on your machine, unable to test: {0} ###'.format(
            WEAK_CIPHERS))

        print('error has_weak_cipher SSLError3', sslex)
        return (False, 'weak_cipher SSLError {0}'.format(sslex))

    try:
        allow_redirects = False

        headers = {'user-agent': useragent}
        a = session.get(url, verify=False, allow_redirects=allow_redirects,
                        headers=headers, timeout=request_timeout)

        if a.status_code == 200 or a.status_code == 301 or a.status_code == 302 or a.status_code == 404:
            print('is ok')
            return (True, 'is ok')

        resulted_in_html = '<html' in a.text

        if resulted_in_html:
            print('has html')
        else:
            print('no html')
        return (resulted_in_html, 'has <html tag in result')
    except ssl.SSLCertVerificationError as sslcertex:
        print('weak_cipher SSLCertVerificationError', sslcertex)
        return (True, 'weak_cipher SSLCertVerificationError: {0}'.format(sslcertex))
    except ssl.SSLError as sslex:
        print('error has_weak_cipher SSLError1', sslex)
        return (False, 'weak_cipher SSLError {0}'.format(sslex))
    except ConnectionResetError as resetex:
        print('error ConnectionResetError', resetex)
        return (False, 'weak_cipher ConnectionResetError {0}'.format(resetex))
    except requests.exceptions.SSLError as sslerror:
        print('error weak_cipher SSLError2', sslerror)
        return (False, 'Unable to verify: SSL error occured')
    except requests.exceptions.ConnectionError as conex:
        print('error weak_cipher ConnectionError', conex)
        return (False, 'Unable to verify: connection error occured')
    except Exception as exception:
        print('weak_cipher test', exception)
        return (False, 'weak_cipher Exception {0}'.format(exception))


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
        a = session.get(url, verify=validate_hostname, allow_redirects=allow_redirects,
                        headers=headers, timeout=request_timeout)

        if a.status_code == 200 or a.status_code == 301 or a.status_code == 302:
            return (True, 'is ok')

        if not validate_hostname and a.status_code == 404:
            return (True, 'is ok')

        resulted_in_html = '<html' in a.text

        return (resulted_in_html, 'has <html tag in result')
    except ssl.SSLCertVerificationError as sslcertex:
        print('protocol version SSLCertVerificationError', sslcertex)
        if validate_hostname:
            return (True, 'protocol version SSLCertVerificationError: {0}'.format(sslcertex))
        else:
            return (False, 'protocol version SSLCertVerificationError: {0}'.format(sslcertex))
    except ssl.SSLError as sslex:
        print('protocol version SSLError', sslex)
        return (False, 'protocol version SSLError: {0}'.format(sslex))
    except ssl.SSLCertVerificationError as sslcertex:
        print('protocol version SSLCertVerificationError', sslcertex)
        return (True, 'protocol version SSLCertVerificationError: {0}'.format(sslcertex))
    except ssl.SSLError as sslex:
        print('error protocol version ', sslex)
        return (False, 'protocol version SSLError {0}'.format(sslex))
    except ConnectionResetError as resetex:
        print('error protocol version  ConnectionResetError', resetex)
        return (False, 'protocol version  ConnectionResetError {0}'.format(resetex))
    except requests.exceptions.SSLError as sslerror:
        print('error protocol version  SSLError', sslerror)
        return (False, 'Unable to verify: SSL error occured')
    except requests.exceptions.ConnectionError as conex:
        print('error protocol version  ConnectionError', conex)
        return (False, 'Unable to verify: connection error occured')
    except Exception as exception:
        print('protocol version  test', exception)
        return (False, 'protocol version  Exception {0}'.format(exception))
