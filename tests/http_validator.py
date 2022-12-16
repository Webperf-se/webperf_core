# -*- coding: utf-8 -*-
import http3
import datetime
import h2
import h11
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

    # We must take in consideration "www." subdomains...

    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    if hostname.startswith('www.'):
        url = url.replace(hostname, hostname[4:])

    nof_checks = 0
    check_url = True

    while check_url and nof_checks < 10:
        checked_url_rating = validate_url(url, _, _local)

        redirect_result = has_redirect(url)
        check_url = redirect_result[0]
        url = redirect_result[1]
        nof_checks += 1

        rating += checked_url_rating

    if nof_checks > 1:
        rating.overall_review += _local('TEXT_REVIEW_SCORE_IS_DIVIDED').format(
            nof_checks)

    # if len(review) == 0:
    #    review = _('TEXT_REVIEW_NO_REMARKS')

    print(_('TEXT_TEST_END').format(
        datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    return (rating, result_dict)


def validate_url(url, _, _local):
    rating = Rating(_, review_show_improvements_only)

    # points = 0.0
    # review = ''

    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    rating += http_to_https_score(url, _, _local)

    rating += tls_version_score(url, _, _local)

    rating += ip_version_score(hostname, _, _local)

    rating += http_version_score(hostname, url, _, _local)

    return rating


def http_to_https_score(url, _, _local):
    rating = Rating(_, review_show_improvements_only)
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
        rating.set_overall(1.0)
        rating.set_integrity_and_security(
            1.0, _local('TEXT_REVIEW_HTTP_TO_HTTP_REDIRECT_UNABLE_TO_VERIFY'))
        rating.set_standards(1.0, _local(
            'TEXT_REVIEW_HTTP_TO_HTTP_REDIRECT_UNABLE_TO_VERIFY'))
        return rating

    result_url_o = urllib.parse.urlparse(result_url)

    if (result_url_o.scheme == 'http'):
        rating.set_overall(1.0)
        rating.set_integrity_and_security(
            1.0, _local('TEXT_REVIEW_HTTP_TO_HTTP_REDIRECT_NO_REDIRECT'))
        rating.set_standards(1.0, _local(
            'TEXT_REVIEW_HTTP_TO_HTTP_REDIRECT_NO_REDIRECT'))
        return rating
    else:
        rating.set_overall(5.0)
        rating.set_integrity_and_security(
            5.0, _local('TEXT_REVIEW_HTTP_TO_HTTP_REDIRECT_REDIRECTED'))
        rating.set_standards(5.0, _local(
            'TEXT_REVIEW_HTTP_TO_HTTP_REDIRECT_REDIRECTED'))
        return rating


def ip_version_score(hostname, _, _local):
    rating = Rating(_, review_show_improvements_only)
    # review += _('TEXT_REVIEW_IP_VERSION')
    ip4_result = dns_lookup(hostname, "A")

    ip6_result = dns_lookup(hostname, "AAAA")

    nof_ip6 = len(ip6_result)
    nof_ip4 = len(ip4_result)

    ip6_rating = Rating(_, review_show_improvements_only)
    if nof_ip6 > 0:
        ip6_rating.set_overall(5.0)
        ip6_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IP_VERSION_IPV6_SUPPORT'))
    else:
        ip6_rating.set_overall(1.0)
        ip6_rating.set_standards(
            1.0, _local('TEXT_REVIEW_IP_VERSION_IPV6_NO_SUPPORT'))

    rating += ip6_rating

    ip4_rating = Rating(_, review_show_improvements_only)
    if nof_ip4 > 0:
        ip4_rating.set_overall(5.0)
        ip4_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IP_VERSION_IPV4_SUPPORT'))
    else:
        ip4_rating.set_overall(1.0)
        ip4_rating.set_standards(
            1.0, _local('TEXT_REVIEW_IP_VERSION_IPV4_NO_SUPPORT'))
    rating += ip4_rating

    return rating


def protocol_version_score(url, protocol_version, _, _local):
    rating = Rating(_, review_show_improvements_only)
    # points = 0.0
    # review = ''
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
                rating.set_integrity_and_security(
                    5.0, _local('TEXT_REVIEW_' + protocol_translate_name + '_SUPPORT'))
                rating.set_overall(5.0)
            else:
                rating.set_integrity_and_security(
                    1.0, _local('TEXT_REVIEW_' + protocol_translate_name + '_SUPPORT'))
                rating.set_overall(2.5)
            rating.set_standards(5.0, _local(
                'TEXT_REVIEW_' + protocol_translate_name + '_SUPPORT'))
        elif has_wrong_cert:
            rating.set_integrity_and_security(
                1.0, _local('TEXT_REVIEW_' + protocol_translate_name + '_SUPPORT_WRONG_CERT'))
            rating.set_standards(
                2.5, _local('TEXT_REVIEW_' + protocol_translate_name + '_SUPPORT_WRONG_CERT'))
            rating.set_overall(2.5)
        else:
            if not protocol_is_secure:
                rating.set_integrity_and_security(
                    5.0, _local('TEXT_REVIEW_' + protocol_translate_name + '_NO_SUPPORT'))
                rating.set_overall(5.0)
            else:
                rating.set_standards(
                    1.0, _local('TEXT_REVIEW_' + protocol_translate_name + '_NO_SUPPORT'))
                rating.set_integrity_and_security(
                    1.0, _local('TEXT_REVIEW_' + protocol_translate_name + '_NO_SUPPORT'))
                rating.set_overall(1.0)

        result_insecure_cipher = (False, 'unset')
        try:
            result_insecure_cipher = has_insecure_cipher(
                url, protocol_rule)
        except ssl.SSLError as sslex:
            print('error insecure_cipher', sslex)
            pass
        # if result_insecure_cipher[0]:
        #    review += _('TEXT_REVIEW_' +
        #                protocol_translate_name + '_INSECURE_CIPHERS')

        result_weak_cipher = (False, 'unset')
        try:
            result_weak_cipher = has_weak_cipher(
                url, protocol_rule)
        except ssl.SSLError as sslex:
            print('error weak_cipher', sslex)
            pass
        # if result_weak_cipher[0]:
        #    review += _('TEXT_REVIEW_' +
        #                protocol_translate_name + '_WEAK_CIPHERS')
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

    return rating


def tls_version_score(orginal_url, _, _local):
    rating = Rating(_, review_show_improvements_only)
    # review += _('TEXT_REVIEW_TLS_VERSION')
    url = orginal_url.replace('http://', 'https://')

    # TODO: check cipher security
    # TODO: re add support for identify wrong certificate

    try:
        tls1_3_rating = protocol_version_score(
            url, ssl.PROTOCOL_TLS, _, _local)
        if tls1_3_rating.get_overall() == 5.0:
            tls1_3_rating.set_performance(
                5.0, _local('TEXT_REVIEW_TLS1_3_SUPPORT'))
        else:
            tls1_3_rating.set_performance(
                4.0, _local('TEXT_REVIEW_TLS1_3_NO_SUPPORT'))
        rating += tls1_3_rating
    except:
        pass

    try:
        rating += protocol_version_score(url, ssl.PROTOCOL_TLSv1_2, _, _local)
    except:
        pass

    try:
        rating += protocol_version_score(url, ssl.PROTOCOL_TLSv1_1, _, _local)
    except:
        pass

    try:
        rating += protocol_version_score(url, ssl.PROTOCOL_TLSv1, _, _local)
    except:
        pass

    try:
        # HOW TO ENABLE SSLv3, https://askubuntu.com/questions/893155/simple-way-of-enabling-sslv2-and-sslv3-in-openssl
        rating += protocol_version_score(url, ssl.PROTOCOL_SSLv3, _, _local)
    except:
        pass

    try:
        # HOW TO ENABLE SSLv2, https://askubuntu.com/questions/893155/simple-way-of-enabling-sslv2-and-sslv3-in-openssl
        rating += protocol_version_score(url, ssl.PROTOCOL_SSLv2, _, _local)
    except:
        pass

    return rating


def http_version_score(hostname, url, _, _local):
    rating = Rating(_, review_show_improvements_only)

    # review += _('TEXT_REVIEW_HTTP_VERSION')

    rating += check_http11(hostname, _, _local)

    rating += check_http2(hostname, _, _local)

    # If we still have 1.0 points something must have gone wrong, try fallback
    if rating.get_overall() == 1.0:
        rating = check_http_fallback(url, _, _local)

    rating += check_http3(hostname, _, _local)

    return rating


def check_http11(hostname, _, _local):
    rating = Rating(_, review_show_improvements_only)
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
            rating.set_overall(5.0)
            rating.set_standards(
                5.0, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_1_1_SUPPORT'))
        else:
            rating.set_overall(1.0)
            rating.set_standards(
                1.0, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_1_1_NO_SUPPORT'))
    except Exception:
        # rating.set_overall(1.0)
        return rating
    return rating


def check_http2(hostname, _, _local):
    rating = Rating(_, review_show_improvements_only)
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
            rating.set_overall(5.0)
            rating.set_standards(
                5.0, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_2_SUPPORT'))
            rating.set_performance(
                5.0, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_2_SUPPORT'))
        else:
            rating.set_overall(1.0)
            rating.set_standards(
                1.0, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_2_NO_SUPPORT'))
            rating.set_performance(
                1.0, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_2_NO_SUPPORT'))
    except Exception:
        return rating

    return rating


def check_http3(host, _, _local):
    rating = Rating(_, review_show_improvements_only)

    has_quic_support = False
    has_http3_support = False

    try:
        url = 'https://http3check.net/?host={0}'.format(host)
        headers = {'user-agent': useragent}
        request = requests.get(url, allow_redirects=True,
                               headers=headers, timeout=request_timeout)

        # We use variable to validate it once
        requestText = ''
        hasRequestText = False

        if request.text:
            requestText = request.text
            hasRequestText = True

        if hasRequestText:
            try:
                soup = BeautifulSoup(requestText, 'lxml')
                elements_success = soup.find_all(
                    class_="uk-text-success")
                for result in elements_success:
                    supportText = result.text.lower()
                    has_quic_support = has_quic_support or 'quic' in supportText
                    has_http3_support = has_quic_support or 'http/3' in supportText

            except:
                print(
                    'Error getting HTTP/3 or QUIC support!\nMessage:\n{0}'.format(sys.exc_info()[0]))

    except Exception as ex:
        print(
            'General Error getting HTTP/3 or QUIC support!\nMessage:\n{0}'.format(sys.exc_info()[0]))

    http3_rating = Rating(_, review_show_improvements_only)
    if (has_http3_support):
        http3_rating.set_overall(5.0)
        http3_rating.set_standards(
            5.0, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_3_SUPPORT'))
        http3_rating.set_performance(
            5.0, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_3_SUPPORT'))
    else:
        http3_rating.set_overall(1.0)
        http3_rating.set_performance(
            2.5, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_3_NO_SUPPORT'))
        http3_rating.set_standards(1.0, _local(
            'TEXT_REVIEW_HTTP_VERSION_HTTP_3_NO_SUPPORT'))
    rating += http3_rating

    quic_rating = Rating(_, review_show_improvements_only)
    if (has_quic_support):
        quic_rating.set_overall(5.0)
        quic_rating.set_performance(
            5.0, _local('TEXT_REVIEW_HTTP_VERSION_QUIC_SUPPORT'))
        quic_rating.set_standards(
            5.0, _local('TEXT_REVIEW_HTTP_VERSION_QUIC_SUPPORT'))
    else:
        quic_rating.set_overall(1.0)
        quic_rating.set_performance(
            2.5, _local('TEXT_REVIEW_HTTP_VERSION_QUIC_NO_SUPPORT'))
        quic_rating.set_standards(1.0, _local(
            'TEXT_REVIEW_HTTP_VERSION_QUIC_NO_SUPPORT'))
    rating += quic_rating

    return rating


def check_http_fallback(url, _, _local):
    rating = Rating(_, review_show_improvements_only)
    has_http2 = False
    has_http11 = False
    try:
        r = http3.get(url, allow_redirects=True)

        has_http2 = r.protocol == "HTTP/2"
        has_http11 = r.protocol == "HTTP1.1"
    except ssl.CertificateError as error:
        print('ERR1', error)
        pass
    except Exception as e:
        print('ERR2', e)
        pass

    try:
        if not has_http11:
            # This call only supports HTTP/1.1
            content = httpRequestGetContent(url, True)
            if '</html>' in content:
                has_http11 = True
    except Exception as e:
        # Probably a CERT validation error, ignore
        print('ERR3', e)
        pass

    http11_rating = Rating(_, review_show_improvements_only)
    if has_http11:
        http11_rating.set_overall(5.0)
        http11_rating.set_standards(5.0, _local(
            'TEXT_REVIEW_HTTP_VERSION_HTTP_1_1_SUPPORT'))
    else:
        http11_rating.set_overall(1.0)
        http11_rating.set_standards(
            1.0, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_1_1_NO_SUPPORT'))
    rating += http11_rating

    http2_rating = Rating(_, review_show_improvements_only)
    if has_http2:
        http2_rating.set_overall(5.0)
        http2_rating.set_standards(5.0, _local(
            'TEXT_REVIEW_HTTP_VERSION_HTTP_2_SUPPORT'))
        http2_rating.set_performance(
            5.0, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_2_SUPPORT'))
    else:
        http2_rating.set_overall(1.0)
        http2_rating.set_standards(
            1.0, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_2_NO_SUPPORT'))
        http2_rating.set_performance(
            1.0, _local('TEXT_REVIEW_HTTP_VERSION_HTTP_2_NO_SUPPORT'))
    rating += http2_rating

    return rating


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
        a = session.get(url, verify=validate_hostname, allow_redirects=allow_redirects,
                        headers=headers, timeout=request_timeout)

        if a.status_code == 200 or a.status_code == 301 or a.status_code == 302:
            return (True, 'is ok')

        if not validate_hostname and a.status_code == 404:
            return (True, 'is ok')

        resulted_in_html = '<html' in a.text

        return (resulted_in_html, 'has <html tag in result')
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
