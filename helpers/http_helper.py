# -*- coding: utf-8 -*-
"""
HTTP helper with curl_cffi fallback for WAF / TLS-fingerprint bypass.

Background
----------
Many enterprise WAF appliances (Akamai, Imperva, F5 ASM, etc.) drop the
TCP/TLS connection from python-requests at the TLS ClientHello stage,
because requests' cipher suites, extensions, ALPN order and GREASE
values do not match any real browser. The user gets a
``requests.exceptions.ConnectionError`` instead of an HTTP response,
even though a real browser to the same URL succeeds.

This is common with Swedish government sites (bolagsverket.se,
skatteverket.se, etc.) when running webperf_core's standard-files test.

Solution
--------
``curl_cffi`` uses ``curl-impersonate`` under the hood to perform the
TLS handshake (and HTTP/2 frame ordering) with byte-exact browser
fingerprints, which lets us through. We only use it as a fallback when
the normal ``requests`` call has already failed with a connection error,
keeping the common case as fast as it was before.

Install
-------
Add to ``requirements.txt``::

    curl-cffi>=0.13.0

The module is *optional*: if ``curl_cffi`` is not installed the helper
behaves exactly like a bare ``requests.get`` call.
"""
import requests

try:
    from curl_cffi import requests as cffi_requests  # type: ignore
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
    cffi_requests = None  # type: ignore


# Browser profile that ``curl_cffi`` uses to spoof the TLS / HTTP/2 fingerprint.
# Keep this reasonably current. See the list of supported impersonations at:
#   https://github.com/lexiforest/curl_cffi#supported-impersonate-versions
# Picked Chrome since it has the largest share of real-world traffic and is
# least likely to be the focus of fingerprint-specific anti-bot rules.
DEFAULT_IMPERSONATE = 'chrome131'


def http_get_with_fallback(url,
                            headers=None,
                            timeout=60,
                            allow_redirects=False):
    """
    Perform an HTTP GET request, falling back to a browser-impersonating
    client if the plain request fails at the TCP/TLS level.

    The first attempt uses ``requests`` (fast, no extra dependencies in
    the critical path). On ``requests.exceptions.ConnectionError`` we
    retry once via ``curl_cffi`` with a Chrome TLS fingerprint. If the
    fallback is unavailable or also fails, the **original** connection
    error is re-raised, so existing exception handling in callers (for
    example the broad ``except requests.exceptions.ConnectionError`` in
    ``tests.utils.get_http_content``) continues to behave the same.

    The returned object exposes the standard response interface used by
    webperf_core call sites: ``.text``, ``.content``, ``.status_code``,
    ``.headers``. Both ``requests.Response`` and ``curl_cffi``'s response
    satisfy this contract.

    Parameters
    ----------
    url : str
        The URL to GET.
    headers : dict, optional
        HTTP request headers (User-Agent, Authorization, etc.). Passed
        through unchanged to both attempts.
    timeout : int, optional
        Per-request timeout in seconds. Default 60.
    allow_redirects : bool, optional
        Whether to follow HTTP redirects. Default False, matching
        webperf_core's existing ``get_http_content`` default.

    Returns
    -------
    Response
        A ``requests.Response`` or ``curl_cffi`` response object.

    Raises
    ------
    requests.exceptions.ConnectionError
        Both the primary attempt and any fallback failed to connect.
    Other ``requests`` exceptions
        Propagated unchanged from the primary attempt (SSL errors,
        invalid URLs, timeouts, etc. are not retried via curl_cffi).
    """
    headers = headers or {}

    try:
        return requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=allow_redirects,
        )
    except requests.exceptions.ConnectionError as primary_err:
        if not HAS_CURL_CFFI:
            raise

        try:
            return cffi_requests.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=allow_redirects,
                impersonate=DEFAULT_IMPERSONATE,
            )
        except Exception:
            # The fallback also failed. Re-raise the *original* error so
            # callers see a familiar requests.exceptions.ConnectionError
            # and existing handling (logging, retry-over-HTTPS, etc.)
            # continues to work unchanged.
            raise primary_err
