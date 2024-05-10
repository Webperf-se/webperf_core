# -*- coding: utf-8 -*-
import ssl
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager # pylint: disable=import-error
from requests.packages.urllib3.util import ssl_ # pylint: disable=import-error
# https://docs.python.org/3/library/urllib.parse.html
from helpers.data_helper import append_domain_entry, has_domain_entry
from models import Rating
from tests.utils import get_config_or_default

# DEFAULTS
REQUEST_TIMEOUT = get_config_or_default('http_request_timeout')
USERAGENT = get_config_or_default('useragent')
REVIEW_SHOW_IMPROVEMENTS_ONLY = get_config_or_default('review_show_improvements_only')

def rate_transfer_layers(result_dict, global_translation, local_translation, domain):
    rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
    if not isinstance(result_dict[domain], dict):
        return rating

    if has_domain_entry(domain, 'transport-layers', 'TLSv1.3', result_dict):
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                                local_translation('TEXT_REVIEW_TLS1_3_SUPPORT').format(domain))
        sub_rating.set_integrity_and_security(5.0,
                                local_translation('TEXT_REVIEW_TLS1_3_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
                                local_translation('TEXT_REVIEW_TLS1_3_NO_SUPPORT').format(domain))
        sub_rating.set_integrity_and_security(1.0,
                                local_translation('TEXT_REVIEW_TLS1_3_NO_SUPPORT').format(domain))
        rating += sub_rating

    if has_domain_entry(domain, 'transport-layers', 'TLSv1.2', result_dict):
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_standards(5.0,
                                local_translation('TEXT_REVIEW_TLS1_2_SUPPORT').format(domain))
        sub_rating.set_integrity_and_security(5.0,
                                local_translation('TEXT_REVIEW_TLS1_2_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_standards(1.0,
                                local_translation('TEXT_REVIEW_TLS1_2_NO_SUPPORT').format(domain))
        sub_rating.set_integrity_and_security(1.0,
                                local_translation('TEXT_REVIEW_TLS1_2_NO_SUPPORT').format(domain))
        rating += sub_rating

    if has_domain_entry(domain, 'transport-layers', 'TLSv1.1', result_dict):
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                                local_translation('TEXT_REVIEW_TLS1_1_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0,
                                local_translation('TEXT_REVIEW_TLS1_1_NO_SUPPORT').format(domain))
        rating += sub_rating

    if has_domain_entry(domain, 'transport-layers', 'TLSv1.0', result_dict):
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(1.0)
        sub_rating.set_integrity_and_security(1.0,
                                local_translation('TEXT_REVIEW_TLS1_0_SUPPORT').format(domain))
        rating += sub_rating
    else:
        sub_rating = Rating(global_translation, REVIEW_SHOW_IMPROVEMENTS_ONLY)
        sub_rating.set_overall(5.0)
        sub_rating.set_integrity_and_security(5.0,
                                local_translation('TEXT_REVIEW_TLS1_0_NO_SUPPORT').format(domain))
        rating += sub_rating
    return rating

def check_tls_version(url, domain, protocol_version, result_dict):
    protocol_rule = False
    protocol_name = ''

    try:
        if protocol_version == ssl.PROTOCOL_TLS:
            protocol_name = 'TLSv1.3'
            assert ssl.HAS_TLSv1_3
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | \
                ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2
        elif protocol_version == ssl.PROTOCOL_TLSv1_2:
            protocol_name = 'TLSv1.2'
            assert ssl.HAS_TLSv1_2
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | \
                ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_3
        elif protocol_version == ssl.PROTOCOL_TLSv1_1:
            protocol_name = 'TLSv1.1'
            assert ssl.HAS_TLSv1_1
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | \
                ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
        elif protocol_version == ssl.PROTOCOL_TLSv1:
            protocol_name = 'TLSv1.0'
            assert ssl.HAS_TLSv1
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | \
                ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
        elif protocol_version == ssl.PROTOCOL_SSLv3:
            protocol_name = 'SSLv3'
            assert ssl.HAS_SSLv3
            protocol_rule = ssl.OP_NO_SSLv2 | ssl.OP_NO_TLSv1 | \
                ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
        elif protocol_version == ssl.PROTOCOL_SSLv2:
            protocol_name = 'SSLv2'
            protocol_rule = ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | \
                ssl.OP_NO_TLSv1_1 | ssl.OP_NO_TLSv1_2 | ssl.OP_NO_TLSv1_3
            assert ssl.HAS_SSLv2

        if has_tls_version(
            url, True, protocol_rule)[0]:
            append_domain_entry(domain, 'transport-layers', protocol_name, result_dict)
        elif has_tls_version(
            url, False, protocol_rule)[0]:
            append_domain_entry(domain, 'transport-layers', f'{protocol_name}-', result_dict)

    except ssl.SSLError as sslex:
        print('error 0.0s', sslex)
    except AssertionError:
        print(f'### No {protocol_name} support on your machine, unable to test ###')

    return result_dict

def check_tls_versions(result_dict):
    for domain in result_dict.keys():
        if not isinstance(result_dict[domain], dict):
            continue
        https_url = result_dict[domain]['urls'][0].replace('http://', 'https://')
        result_dict = check_tls_version(https_url, domain, ssl.PROTOCOL_TLS, result_dict)
        result_dict = check_tls_version(https_url, domain, ssl.PROTOCOL_TLSv1_2, result_dict)
        result_dict = check_tls_version(https_url, domain, ssl.PROTOCOL_TLSv1_1, result_dict)
        result_dict = check_tls_version(https_url, domain, ssl.PROTOCOL_TLSv1, result_dict)

    # Firefox:
    # security.tls.version.min
    # security.tls.version.max

    return result_dict

# Read post at: https://hussainaliakbar.github.io/
# restricting-tls-version-and-cipher-suites-in-python-requests-and-testing-wireshark/

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


def has_tls_version(url, validate_hostname, protocol_version):
    session = requests.session()
    if validate_hostname:
        adapter = TlsAdapterCertRequired(protocol_version)
    else:
        adapter = TlsAdapterNoCert(protocol_version)

    session.mount("https://", adapter)

    try:
        allow_redirects = False

        headers = {'user-agent': USERAGENT}
        session.get(url, verify=validate_hostname, allow_redirects=allow_redirects,
                        headers=headers, timeout=REQUEST_TIMEOUT)

        return (True, 'is ok')

    except ssl.SSLCertVerificationError as sslcertex:
        # print('protocol version SSLCertVerificationError', sslcertex)
        if validate_hostname:
            return (True, f'protocol version SSLCertVerificationError: {sslcertex}')
        return (False, f'protocol version SSLCertVerificationError: {sslcertex}')
    except ssl.SSLError as sslex:
        # print('error protocol version ', sslex)
        return (False, f'protocol version SSLError {sslex}')
    except ConnectionResetError as resetex:
        # print('error protocol version  ConnectionResetError', resetex)
        return (False, f'protocol version  ConnectionResetError {resetex}')
    except requests.exceptions.SSLError:
        # print('error protocol version  SSLError', sslerror)
        return (False, 'Unable to verify: SSL error occured')
    except requests.exceptions.ConnectionError:
        # print('error protocol version  ConnectionError', conex)
        return (False, 'Unable to verify: connection error occured')
    except requests.exceptions.MissingSchema:
        print(
            'Connection error! Missing Schema for '
            f'"{url}"')
        return (False, 'Unable to verify: Missing Schema')
    except requests.exceptions.TooManyRedirects:
        print(
            'Connection error! Too many redirects for '
            f'"{url}"')
        return (False, 'Unable to verify: Too many redirects')
    except requests.exceptions.InvalidURL:
        print(
            'Connection error! Invalid url '
            f'"{url}"')
        return (False, 'Unable to verify: Invalid url')
    except TimeoutError:
        print(
            'Error! Unfortunately the request for URL '
            f'"{url}" timed out.'
            f'The timeout is set to {REQUEST_TIMEOUT} seconds.')
        return (False, 'Unable to verify: Timed out')
