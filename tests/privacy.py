# -*- coding: utf-8 -*-
import atexit
from datetime import datetime
import os
import re
import json
import subprocess
import time
import urllib.parse
from urllib.parse import urlparse, urljoin
import requests
from helpers.models import Rating
from helpers.setting_helper import get_config
from tests.utils import get_translation
from tests.tracking_validator import get_domains_from_blocklistproject_file

# Referrer policies that protect the visitor from leaking
# the visited address to other websites.
# 'strict-origin-when-cross-origin' (the modern browser default) is
# deliberately NOT included: it still leaks the origin cross-site, which
# Webbkoll (test 20) also flags as a warning.
GOOD_REFERRER_POLICIES = (
    'no-referrer',
    'same-origin',
    'strict-origin')

ONE_YEAR_IN_SECONDS = 365 * 24 * 60 * 60
HSTS_MIN_MAX_AGE = 15768000  # 6 months
OLD_TLS_PROTOCOLS = ('TLS 1.0', 'TLS 1.1', 'SSLv3', 'SSLv2')

# Keeps track of the webbkoll-backend process we may have started ourselves,
# so we only start it once per run and can stop it when webperf_core exits.
BACKEND_PROCESS = {
    'process': None
}

def stop_backend():
    """
    Stops the webbkoll-backend process if this run started it.
    """
    process = BACKEND_PROCESS['process']
    if process is None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
    BACKEND_PROCESS['process'] = None

def is_backend_alive(api_url):
    """
    Checks if a webbkoll-backend service is responding at the given URL.
    """
    try:
        request = requests.get(f'{api_url}/status', timeout=2)
        return request.status_code == 200
    except requests.exceptions.RequestException:
        return False

def ensure_backend_running(api_url):
    """
    Makes sure a webbkoll-backend service is available at the given URL.

    If nothing is listening and the URL points at localhost,
    the npm installed copy (node_modules/webbkoll-backend) is started,
    the same way other tests use their npm dependencies.
    The started process is stopped again when webperf_core exits.

    Returns:
        bool: True if a backend is (now) responding at the URL.
    """
    if is_backend_alive(api_url):
        return True

    parsed_api_url = urlparse(api_url)
    if parsed_api_url.hostname not in ('localhost', '127.0.0.1', '::1'):
        return False

    if BACKEND_PROCESS['process'] is not None:
        return False

    backend_dir = os.path.join('node_modules', 'webbkoll-backend')
    backend_script = os.path.join(backend_dir, 'index.js')
    if not os.path.exists(backend_script):
        return False

    port = parsed_api_url.port
    if port is None:
        port = 8100

    with open(os.devnull, 'w', encoding='utf-8') as devnull:
        BACKEND_PROCESS['process'] = subprocess.Popen( # pylint: disable=consider-using-with
            ['node', 'index.js', str(port)],
            cwd=backend_dir,
            stdout=devnull,
            stderr=devnull)
    atexit.register(stop_backend)

    walltime_ends = time.time() + 15
    while time.time() < walltime_ends:
        if is_backend_alive(api_url):
            return True
        time.sleep(0.5)
    return False

def run_test(global_translation, url):
    """
    This function runs a privacy test on a given URL and
    returns a rating and a dictionary.

    It is the successor of test 20 (privacy_webbkollen).
    Instead of scraping the hosted Webbkoll website it calls a
    self-hosted webbkoll-backend service
    (https://codeberg.org/marcusosterberg/webbkoll-backend)
    that visits the URL with a real browser and returns raw data
    (cookies, requests, headers, TLS info and mixed content) as JSON.
    The rating is then calculated locally from that data.

    Parameters:
    global_translation (function): A function to translate text to a global language.
    url (str): The URL to be tested.

    Returns:
    tuple: A tuple containing the rating object and a dictionary with the raw check data.
    """
    review = ''
    return_dict = {}
    rating = Rating(global_translation, get_config('general.review.improve-only'))

    local_translation = get_translation('privacy', get_config('general.language'))

    print(local_translation('TEXT_RUNNING_TEST'))

    print(global_translation('TEXT_TEST_START').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    data = get_backend_data(url, local_translation)
    if data is None or not data.get('success', False):
        error_rating = Rating(
            global_translation,
            get_config('general.review.improve-only'))
        error_rating.overall_review = global_translation('TEXT_SITE_UNAVAILABLE')
        return (error_rating, {'failed': True})

    final_url = data.get('final_url', url)
    return_dict['input_url'] = url
    return_dict['final_url'] = final_url

    rating += rate_https(data, local_translation, global_translation, return_dict)
    rating += rate_referrer_policy(data, local_translation, global_translation, return_dict)
    rating += rate_cookies(data, final_url, local_translation, global_translation, return_dict)
    rating += rate_third_parties(data, final_url, local_translation,
                                 global_translation, return_dict)
    rating += rate_headers(data, local_translation, global_translation, return_dict)
    rating += rate_sri(data, final_url, local_translation, global_translation, return_dict)
    collect_localstorage(data, return_dict)

    points = rating.get_integrity_and_security()
    if points >= 5:
        review = local_translation('TEXT_REVIEW_VERY_GOOD') + review
    elif points >= 4:
        review = local_translation('TEXT_REVIEW_IS_GOOD') + review
    elif points >= 3:
        review = local_translation('TEXT_REVIEW_IS_OK') + review
    elif points >= 2:
        review = local_translation('TEXT_REVIEW_IS_BAD') + review
    elif points >= 1:
        review = local_translation('TEXT_REVIEW_IS_VERY_BAD') + review
    else:
        review = local_translation('TEXT_REVIEW_IS_VERY_BAD') + review
        points = 1.0

    rating.set_overall(points)
    rating.overall_review = review

    print(global_translation('TEXT_TEST_END').format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    reviews = rating.get_reviews()
    print(global_translation('TEXT_SITE_RATING'), rating)
    if get_config('general.review.show'):
        print(
            global_translation('TEXT_SITE_REVIEW'),
            reviews)

    if get_config('general.review.data'):
        nice_json_data = json.dumps(return_dict, indent=3)
        print(
            global_translation('TEXT_SITE_REVIEW_DATA'),
            f'```json\r\n{nice_json_data}\r\n```')

    return (rating, return_dict)

def get_backend_data(url, local_translation):
    """
    Calls the self-hosted webbkoll-backend service and returns its JSON result.

    Args:
        url (str): The URL of the webpage to be checked.
        local_translation (function): A function that translates text to the local language.

    Returns:
        dict: The parsed JSON result from the backend, or None if the
              backend could not be reached or returned invalid data.
    """
    api_url = get_config('tests.webbkoll.api-url')
    if api_url is None or api_url == '':
        api_url = 'http://localhost:8100'
    api_url = api_url.rstrip('/')

    if not ensure_backend_running(api_url):
        print(local_translation('TEXT_SERVICE_UNAVAILABLE').format(api_url))
        return None

    timeout = get_config('general.request.timeout')
    # The backend visits the page with a real browser,
    # retries different wait strategies and waits an additional
    # 10 seconds after load, so allow it more time than a plain request.
    http_timeout = (timeout * 3) + 30

    try:
        request = requests.get(
            (f'{api_url}/?fetch_url={urllib.parse.quote(url)}'
             f'&timeout={timeout * 1000}'),
            timeout=http_timeout)
        return request.json()
    except requests.exceptions.RequestException:
        print(local_translation('TEXT_SERVICE_UNAVAILABLE').format(api_url))
        return None
    except ValueError:
        print(local_translation('TEXT_SERVICE_UNAVAILABLE').format(api_url))
        return None

def get_first_party_domains(url):
    """
    Returns the set of domain suffixes that are considered first party
    for the given URL, using the same approach as the tracking test.
    """
    domains = set()
    hostname = urlparse(url).hostname
    if hostname is None:
        return domains
    domains.add(hostname)

    hostname_sections = hostname.split(".")
    if len(hostname_sections) > 2:
        domains.add(".".join(hostname_sections[-3:]))
    if len(hostname_sections) >= 2:
        domains.add(".".join(hostname_sections[-2:]))

    return domains

def is_first_party(hostname, first_party_domains):
    """
    Checks if a hostname belongs to any of the first party domain suffixes.
    """
    if hostname is None:
        return True
    for domain in first_party_domains:
        if hostname == domain or hostname.endswith('.' + domain):
            return True
    return False

def is_domain_in_set(hostname, domains):
    """
    Checks if a hostname, or any of its parent domains, is in the given set.
    """
    if hostname is None:
        return False
    sections = hostname.split('.')
    for index in range(len(sections) - 1):
        if '.'.join(sections[index:]) in domains:
            return True
    return False

def get_lowercase_headers(data):
    """
    Returns the response headers of the main document with lowercase names.
    """
    headers = data.get('response_headers')
    if not isinstance(headers, dict):
        return {}
    return {name.lower(): value for name, value in headers.items()}

def rate_https(data, local_translation, global_translation, return_dict):
    """
    Rates if the website uses HTTPS,
    if any resources are loaded over insecure HTTP (mixed content) and
    if the TLS protocol version used is outdated.
    """
    rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))

    final_url = data.get('final_url', '')
    uses_https = final_url.startswith('https://')

    insecure_urls = set()
    for response in data.get('responses', []):
        response_url = response.get('url', '')
        if response_url.startswith('http://'):
            insecure_urls.add(response_url)

    mixed_content = data.get('mixed_content')
    if isinstance(mixed_content, dict):
        insecure_urls.update(mixed_content.keys())

    security_info = data.get('security_info')
    tls_protocol = ''
    if isinstance(security_info, dict):
        tls_protocol = security_info.get('protocol', '')

    reviews = []
    points = 5.0
    if not uses_https:
        points = 1.0
        reviews.append(local_translation('TEXT_REVIEW_HTTPS_NO_HTTPS'))
    else:
        nof_insecure = len(insecure_urls)
        if nof_insecure > 0:
            points -= min(0.5 * nof_insecure, 4.0)
            reviews.append(local_translation(
                'TEXT_REVIEW_HTTPS_MIXED_CONTENT').format(nof_insecure))
        if tls_protocol in OLD_TLS_PROTOCOLS:
            points -= 1.0
            reviews.append(local_translation(
                'TEXT_REVIEW_HTTPS_OLD_TLS').format(tls_protocol))

    points = max(points, 1.0)
    if len(reviews) == 0:
        review = local_translation('TEXT_REVIEW_HTTPS_VERY_GOOD')
    else:
        review = '- ' + '; '.join(reviews)

    return_dict['https'] = {
        'uses_https': uses_https,
        'nof_insecure_requests': len(insecure_urls),
        'insecure_requests': sorted(insecure_urls),
        'tls_protocol': tls_protocol
    }

    rating.set_integrity_and_security(points, review)
    return rating

def rate_referrer_policy(data, local_translation, global_translation, return_dict):
    """
    Rates the referrer policy of the website,
    set either as a HTTP header or as a meta element.
    """
    rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))

    headers = get_lowercase_headers(data)
    policy = ''
    if 'referrer-policy' in headers:
        # a comma separated list is allowed, the last valid policy wins
        policy = headers['referrer-policy'].split(',')[-1].strip().lower()

    if policy == '':
        content = data.get('content', '')
        regex = (r'<meta[^>]+name=["\']referrer["\'][^>]+'
                 r'content=["\'](?P<policy>[^"\']+)["\']')
        matches = re.finditer(regex, content, re.IGNORECASE)
        for _, match in enumerate(matches, start=1):
            policy = match.group('policy').strip().lower()

    if policy in GOOD_REFERRER_POLICIES:
        points = 5.0
        review = local_translation(
            'TEXT_REVIEW_REFERRER_POLICY_VERY_GOOD').format(policy)
    elif policy == '':
        points = 3.0
        review = '- ' + local_translation('TEXT_REVIEW_REFERRER_POLICY_MISSING')
    else:
        points = 2.0
        review = '- ' + local_translation(
            'TEXT_REVIEW_REFERRER_POLICY_LEAKY').format(policy)

    return_dict['referrer-policy'] = {
        'policy': policy
    }

    rating.set_integrity_and_security(points, review)
    return rating

def rate_cookies(data, final_url, local_translation, global_translation, return_dict):
    """
    Rates the cookies set by the website:
    third party cookies, cookies that live longer than a year and
    cookies missing the Secure attribute.
    """
    rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))

    first_party_domains = get_first_party_domains(final_url)
    uses_https = final_url.startswith('https://')
    now = datetime.now().timestamp()

    cookies = data.get('cookies', [])
    nof_third_party = 0
    nof_long_lived = 0
    nof_not_secure = 0
    nof_not_http_only = 0
    nof_weak_same_site = 0
    for cookie in cookies:
        cookie_domain = cookie.get('domain', '').lstrip('.')
        if not is_first_party(cookie_domain, first_party_domains):
            nof_third_party += 1
        expires = cookie.get('expires', -1)
        if not cookie.get('session', False) and expires > 0 and \
                (expires - now) > ONE_YEAR_IN_SECONDS:
            nof_long_lived += 1
        if uses_https and not cookie.get('secure', False):
            nof_not_secure += 1
        if not cookie.get('httpOnly', False):
            nof_not_http_only += 1
        # 'None' (must be paired with Secure) and an unset/empty value leave
        # the cookie exposed to cross-site requests. 'Lax' and 'Strict' are ok.
        if cookie.get('sameSite', '').strip().lower() not in ('lax', 'strict'):
            nof_weak_same_site += 1

    reviews = []
    points = 5.0
    if nof_third_party > 0:
        points -= 2.5 + min(0.25 * nof_third_party, 1.5)
        reviews.append(local_translation(
            'TEXT_REVIEW_COOKIES_THIRD_PARTY').format(nof_third_party))
    if nof_long_lived > 0:
        points -= min(0.25 * nof_long_lived, 1.0)
        reviews.append(local_translation(
            'TEXT_REVIEW_COOKIES_LONG_LIVED').format(nof_long_lived))
    if nof_not_secure > 0:
        points -= min(0.25 * nof_not_secure, 1.0)
        reviews.append(local_translation(
            'TEXT_REVIEW_COOKIES_NOT_SECURE').format(nof_not_secure))
    if nof_not_http_only > 0:
        points -= min(0.25 * nof_not_http_only, 1.0)
        reviews.append(local_translation(
            'TEXT_REVIEW_COOKIES_NOT_HTTP_ONLY').format(nof_not_http_only))
    if nof_weak_same_site > 0:
        points -= min(0.25 * nof_weak_same_site, 1.0)
        reviews.append(local_translation(
            'TEXT_REVIEW_COOKIES_WEAK_SAME_SITE').format(nof_weak_same_site))

    points = max(points, 1.0)
    if len(reviews) == 0:
        review = local_translation('TEXT_REVIEW_COOKIES_VERY_GOOD')
    else:
        review = '- ' + '; '.join(reviews)

    return_dict['cookies'] = {
        'nof_cookies': len(cookies),
        'nof_third_party': nof_third_party,
        'nof_long_lived': nof_long_lived,
        'nof_not_secure': nof_not_secure,
        'nof_not_http_only': nof_not_http_only,
        'nof_weak_same_site': nof_weak_same_site
    }

    rating.set_integrity_and_security(points, review)
    return rating

def rate_third_parties(data, final_url, local_translation, global_translation, return_dict):
    """
    Rates the number of third party domains the website makes requests to and
    if any of them are known tracker domains.
    """
    rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))

    first_party_domains = get_first_party_domains(final_url)

    request_domains = set()
    for response in data.get('responses', []):
        hostname = urlparse(response.get('url', '')).hostname
        if hostname is not None:
            request_domains.add(hostname)

    third_party_domains = set()
    for hostname in request_domains:
        if not is_first_party(hostname, first_party_domains):
            third_party_domains.add(hostname)

    tracker_domains = set()
    if len(third_party_domains) > 0:
        known_tracker_domains = get_domains_from_blocklistproject_file(
            os.path.join('data', 'blocklistproject-tracking-nl.txt'))
        for hostname in third_party_domains:
            if is_domain_in_set(hostname, known_tracker_domains):
                tracker_domains.add(hostname)

    reviews = []
    points = 5.0
    if len(third_party_domains) > 0:
        points -= min(0.15 * len(third_party_domains), 2.0)
        reviews.append(local_translation(
            'TEXT_REVIEW_THIRD_PARTY_REQUESTS').format(len(third_party_domains)))
    if len(tracker_domains) > 0:
        points -= 2.0 + min(0.25 * len(tracker_domains), 1.0)
        reviews.append(local_translation(
            'TEXT_REVIEW_THIRD_PARTY_TRACKERS').format(len(tracker_domains)))

    points = max(points, 1.0)
    if len(reviews) == 0:
        review = local_translation('TEXT_REVIEW_THIRD_PARTY_VERY_GOOD')
    else:
        review = '- ' + '; '.join(reviews)

    return_dict['third-parties'] = {
        'nof_third_party_domains': len(third_party_domains),
        'third_party_domains': sorted(third_party_domains),
        'nof_tracker_domains': len(tracker_domains),
        'tracker_domains': sorted(tracker_domains)
    }

    rating.set_integrity_and_security(points, review)
    return rating

def rate_headers(data, local_translation, global_translation, return_dict):
    """
    Rates privacy and security related HTTP headers:
    Strict-Transport-Security, X-Content-Type-Options and
    protection against the page being embedded by other websites.
    """
    rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))

    headers = get_lowercase_headers(data)
    uses_https = data.get('final_url', '').startswith('https://')

    reviews = []
    points = 5.0

    hsts = headers.get('strict-transport-security', '')
    if uses_https:
        if hsts == '':
            points -= 1.5
            reviews.append(local_translation('TEXT_REVIEW_HEADERS_HSTS_MISSING'))
        else:
            hsts_lower = hsts.lower()
            max_age = 0
            regex = r"max-age=(?P<seconds>[0-9]+)"
            matches = re.finditer(regex, hsts, re.IGNORECASE)
            for _, match in enumerate(matches, start=1):
                max_age = int(match.group('seconds'))
            if max_age < HSTS_MIN_MAX_AGE:
                points -= 0.5
                reviews.append(local_translation('TEXT_REVIEW_HEADERS_HSTS_SHORT'))
            if 'includesubdomains' not in hsts_lower:
                points -= 0.5
                reviews.append(local_translation('TEXT_REVIEW_HEADERS_HSTS_NO_SUBDOMAINS'))
            if 'preload' not in hsts_lower:
                points -= 0.25
                reviews.append(local_translation('TEXT_REVIEW_HEADERS_HSTS_NO_PRELOAD'))

    if headers.get('x-content-type-options', '').strip().lower() != 'nosniff':
        points -= 0.5
        reviews.append(local_translation('TEXT_REVIEW_HEADERS_XCTO_MISSING'))

    has_frame_protection = 'x-frame-options' in headers or \
        'frame-ancestors' in headers.get('content-security-policy', '').lower()
    if not has_frame_protection:
        points -= 0.5
        reviews.append(local_translation('TEXT_REVIEW_HEADERS_XFO_MISSING'))

    points = max(points, 1.0)
    if len(reviews) == 0:
        review = local_translation('TEXT_REVIEW_HEADERS_VERY_GOOD')
    else:
        review = '- ' + '; '.join(reviews)

    return_dict['headers'] = {
        'strict-transport-security': hsts,
        'x-content-type-options': headers.get('x-content-type-options', ''),
        'x-frame-options': headers.get('x-frame-options', '')
    }

    rating.set_integrity_and_security(points, review)
    return rating

def is_third_party_subresource(tag, attr, final_url, first_party_domains):
    """
    Resolves the src/href URL of a subresource tag against final_url and
    returns True only when it points to a third-party (cross-origin) host.

    SRI provides no meaningful protection for same-origin subresources: an
    attacker able to tamper with a first-party file at the origin can equally
    rewrite the integrity attribute that references it. SRI's purpose is
    pinning third-party resources, so only those are considered here.
    Relative URLs (same-origin by definition) are treated as first party.
    """
    url_match = re.search(
        attr + r'\s*=\s*["\']?(?P<url>[^"\'>\s]+)', tag, re.IGNORECASE)
    if url_match is None:
        return False
    hostname = urlparse(urljoin(final_url, url_match.group('url'))).hostname
    return not is_first_party(hostname, first_party_domains)

def get_sri_subresources(content, final_url):
    """
    Counts third-party scripts and stylesheets in the rendered content that
    are loaded with a src/href but without a Subresource Integrity (integrity)
    attribute.

    Only cross-origin subresources are counted, since SRI is what protects a
    resource the site does not control from being tampered with; a missing
    integrity attribute on such a resource lowers the rating.

    Returns:
        tuple: (nof_subresources, nof_without_integrity)
    """
    nof_total = 0
    nof_missing = 0
    first_party_domains = get_first_party_domains(final_url)

    for match in re.finditer(r'<script\b[^>]*>', content, re.IGNORECASE):
        tag = match.group(0)
        if re.search(r'\ssrc\s*=', tag, re.IGNORECASE) is None:
            continue
        if not is_third_party_subresource(tag, r'\ssrc', final_url, first_party_domains):
            continue
        nof_total += 1
        if re.search(r'\sintegrity\s*=', tag, re.IGNORECASE) is None:
            nof_missing += 1

    for match in re.finditer(r'<link\b[^>]*>', content, re.IGNORECASE):
        tag = match.group(0)
        if re.search(r'\shref\s*=', tag, re.IGNORECASE) is None:
            continue
        rel_match = re.search(r'\srel\s*=\s*["\']?(?P<rel>[^"\'>]+)', tag, re.IGNORECASE)
        rel = rel_match.group('rel').strip().lower() if rel_match else ''
        if 'stylesheet' not in rel:
            continue
        if not is_third_party_subresource(tag, r'\shref', final_url, first_party_domains):
            continue
        nof_total += 1
        if re.search(r'\sintegrity\s*=', tag, re.IGNORECASE) is None:
            nof_missing += 1

    return nof_total, nof_missing

def rate_sri(data, final_url, local_translation, global_translation, return_dict):
    """
    Rates Subresource Integrity (SRI) usage:
    how many third-party scripts and stylesheets are loaded without an
    integrity attribute.
    """
    rating = Rating(
        global_translation,
        get_config('general.review.improve-only'))

    content = data.get('content', '')
    nof_total, nof_missing = get_sri_subresources(content, final_url)

    points = 5.0
    if nof_missing > 0:
        points -= min(0.5 * nof_missing, 4.0)
        review = '- ' + local_translation('TEXT_REVIEW_SRI_MISSING').format(nof_missing)
    else:
        review = local_translation('TEXT_REVIEW_SRI_VERY_GOOD')

    points = max(points, 1.0)

    return_dict['sri'] = {
        'nof_subresources': nof_total,
        'nof_without_integrity': nof_missing
    }

    rating.set_integrity_and_security(points, review)
    return rating

def collect_localstorage(data, return_dict):
    """
    Records localStorage usage in the raw review data without affecting
    the rating.

    Unlike cookies, localStorage is same-origin only and is never
    automatically sent with requests, so on its own it is a weak privacy
    signal and is commonly used for benign functional state (theme,
    language, consent choices, form drafts). Webbkoll and the predecessor
    test 20 therefore report it as information only, which we mirror here.
    """
    local_storage = data.get('localStorage')
    nof_keys = len(local_storage) if isinstance(local_storage, dict) else 0
    return_dict['localstorage'] = {
        'nof_keys': nof_keys
    }
