# -*- coding: utf-8 -*-
import smtplib
import datetime
import socket
import sys
import urllib.parse
import datetime
# https://docs.python.org/3/library/urllib.parse.html
import urllib
import config
from models import Rating
from tests.utils import dns_lookup
import gettext
_local = gettext.gettext

# DEFAULTS
request_timeout = config.http_request_timeout
useragent = config.useragent
review_show_improvements_only = config.review_show_improvements_only

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

    # 0.0 - Preflight (Will probably resolve 98% of questions from people trying this test themself)
    # 0.1 - Check for allowed connection over port 25 (most consumer ISP don't allow this)
    support_port25 = True
    # 0.2 - Check for allowed IPv6 support (GitHub Actions doesn't support it on network lever on the time of writing this)
    support_IPv6 = False

    # 1 - Get Email servers
    # dns_lookup
    rating, ipv4_servers, ipv6_servers = Validate_MX_Records(
        _, rating, result_dict, _local, hostname)

    # 1.2 - Check operational
    if support_port25:
        rating = Validate_IPv4_Operation_Status(
            _, rating, _local, ipv4_servers)

    # 1.2 - Check operational
    if support_port25 and support_IPv6:
        rating = Validate_IPv6_Operation_Status(
            _, rating, _local, ipv6_servers)

    # 1.4 - Check TLS
    # 1.5 - Check PKI
    # 1.6 - Check DNSSEC
    # 1.7 - Check DANE
    # 1.8 - Check MTA-STS policy
    rating = Validate_MTA_STS_Policy(_, rating, _local, hostname)

    # https://www.rfc-editor.org/rfc/rfc8461#section-3.2

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
            5.0, _local('TEXT_REVIEW_MT_STS_SUPPORT'))
        has_mta_sts_records_rating.set_standards(
            5.0, _local('TEXT_REVIEW_MT_STS_SUPPORT'))
    else:
        has_mta_sts_records_rating.set_overall(1.0)
        has_mta_sts_records_rating.set_integrity_and_security(
            2.5, _local('TEXT_REVIEW_MT_STS_NO_SUPPORT'))
        has_mta_sts_records_rating.set_standards(
            1.0, _local('TEXT_REVIEW_MT_STS_NO_SUPPORT'))
    rating += has_mta_sts_records_rating
    return rating


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
    email_entries = list()

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
        nof_ipv6_rating.set_integrity_and_security(
            5.0, _local('TEXT_REVIEW_IPV6_REDUNDANCE'))
        nof_ipv6_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IPV6_SUPPORT'))
    elif nof_ipv6_servers == 1:
        # example: feber.se (do dns lookup also before)
        nof_ipv6_rating.set_overall(2.5)
        nof_ipv6_rating.set_integrity_and_security(
            2.5, _local('TEXT_REVIEW_IPV6_NO_REDUNDANCE'))
        nof_ipv6_rating.set_standards(
            5.0, _local('TEXT_REVIEW_IPV6_SUPPORT'))
    else:
        # example: huddinge.se
        nof_ipv6_rating.set_overall(1.0)
        nof_ipv6_rating.set_standards(
            1.0, _local('TEXT_REVIEW_IPV6_NO_SUPPORT'))
    rating += nof_ipv6_rating

    # add data to result of test
    result_dict["mx-addresses"] = email_entries
    result_dict["mx-ipv4-servers"] = ipv4_servers
    result_dict["mx-ipv6-servers"] = ipv6_servers

    return rating, ipv4_servers, ipv6_servers
