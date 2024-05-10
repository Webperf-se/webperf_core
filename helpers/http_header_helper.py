# -*- coding: utf-8 -*-

import urllib
import urllib.parse
from helpers.csp_helper import handle_csp_data
from helpers.data_helper import append_domain_entry, has_domain_entry

def append_data_from_response_headers(response_headers, req_url, org_domain, req_domain, result):
    for header in response_headers:
        if 'name' not in header:
            continue

        if 'value' not in header:
            continue

        name = header['name'].lower()
        value = header['value'].strip()

        if 'strict-transport-security' in name:
            handle_header_hsts(value, req_domain, result)
        elif 'location' in name:
            handle_header_location(value, req_url, req_domain, result)
        elif 'content-security-policy' in name:
            append_domain_entry(req_domain, 'features', 'CSP-HEADER-FOUND', result)
            # TODO: Add CSP logic here
            handle_csp_data(value, req_domain, result, True, org_domain)
        elif 'x-content-security-policy' in name or 'x-webkit-csp' in name:
            append_domain_entry(req_domain, 'features', 'CSP-HEADER-FOUND', result)
            append_domain_entry(req_domain, 'features', 'CSP-DEPRECATED', result)
            # TODO: Add CSP logic here
            # handle_csp_data(value, req_domain, result, True, org_domain)

def handle_header_location(value, req_url, req_domain, result):
    """
    Handles the 'Location' header for a given domain and
    updates the result dictionary based on the redirection scheme.

    This function parses the 'Location' header value and
    checks if it starts with 'https://' or 'http://'. Depending on 
    the scheme and whether the redirection is to the same domain or
    a different domain, it appends corresponding entries 
    to the result dictionary.
    It also checks if the redirection invalidates HSTS (HTTP Strict Transport Security).

    Parameters:
    value (str): The 'Location' header value to be parsed.
    req_url (str): The URL of the request.
    req_domain (str): The domain of the request.
    result (dict): The dictionary to which the results should be added.

    Returns:
    None: This function doesn't return anything; it modifies the result dictionary in-place.
    """
    o = urllib.parse.urlparse(req_url)
    req_domain = o.hostname
    req_scheme = o.scheme.lower()

    if value.startswith(f'https://{req_domain}'):
        append_domain_entry(req_domain, 'schemes', 'HTTPS-REDIRECT', result)
    elif value.startswith('https://') and req_scheme == 'http':
        append_domain_entry(req_domain, 'schemes', 'HTTPS-REDIRECT-OTHERDOMAIN', result)
        append_domain_entry(req_domain, 'features', 'INVALIDATE-HSTS', result)
    elif value.startswith(f'http://{req_domain}'):
        if req_url.startswith('https://'):
            append_domain_entry(req_domain, 'schemes', 'HTTP-REDIRECT', result)
        else:
            append_domain_entry(req_domain, 'schemes', 'HTTP-REDIRECT', result)
            append_domain_entry(req_domain, 'features', 'INVALIDATE-HSTS', result)
    elif value.startswith('http://'):
        append_domain_entry(req_domain, 'schemes', 'HTTP-REDIRECT-OTHERDOMAIN', result)
        append_domain_entry(req_domain, 'features', 'INVALIDATE-HSTS', result)


def handle_header_hsts(value, req_domain, result):
    """
    Handles the HSTS (HTTP Strict Transport Security) header for a given domain and
    updates the result dictionary.

    This function parses the HSTS header value and
    checks for the presence of certain features such as 'max-age', 
    'includeSubDomains', and 'preload'.
    Depending on the features found and their values, it appends corresponding 
    entries to the result dictionary.

    Parameters:
    value (str): The HSTS header value to be parsed.
    req_domain (str): The domain for which the HSTS header is being checked.
    result (dict): The dictionary to which the results should be added.

    Returns:
    None: This function doesn't return anything;
          it modifies the result dictionary in-place.
    """
    if has_domain_entry(req_domain, 'features', 'HSTS', result):
        return

    sections = value.split(';')
    for section in sections:
        section = section.strip()

        pair = section.split('=')

        section_name = pair[0]
        section_value = None
        if len(pair) == 2:
            section_value = pair[1]

        if 'max-age' == section_name:
            append_domain_entry(req_domain, 'features', 'HSTS-HEADER-MAXAGE-FOUND', result)
            try:
                maxage = int(section_value)
                                # 1 month =   2628000
                                # 6 month =  15768000
                                # check if maxage is more then 1 year
                if maxage >= 31536000:
                    append_domain_entry(req_domain, 'features', 'HSTS-HEADER-MAXAGE-1YEAR', result)
                elif maxage < 2628000:
                    append_domain_entry(req_domain, 'features', 'HSTS-HEADER-MAXAGE-1MONTH', result)
                elif maxage < 15768000:
                    append_domain_entry(
                        req_domain,
                        'features',
                        'HSTS-HEADER-MAXAGE-6MONTHS',
                        result)
                else:
                    append_domain_entry(
                        req_domain,
                        'features',
                        'HSTS-HEADER-MAXAGE-TOO-LOW',
                        result)

                append_domain_entry(req_domain, 'features', 'HSTS', result)
            except (TypeError, ValueError):
                _ = 1
        elif 'includeSubDomains' == section_name:
            append_domain_entry(req_domain, 'features', 'HSTS-HEADER-SUBDOMAINS-FOUND', result)
        elif 'preload' == section_name:
            append_domain_entry(req_domain, 'features', 'HSTS-HEADER-PRELOAD-FOUND', result)
