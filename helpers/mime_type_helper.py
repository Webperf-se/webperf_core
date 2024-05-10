# -*- coding: utf-8 -*-

import base64
import urllib
import urllib.parse
from helpers.csp_helper import handle_csp
from helpers.data_helper import append_domain_entry, has_domain_entry
from helpers.hash_helper import create_sha256_hash

def append_data_from_mimetypes(response, req_url, org_domain, req_domain, result):
    if 'content' not in response:
        return

    if 'mimeType' not in response['content']:
        return

    mime_type = response['content']['mimeType']

    # TODO: Add CSP logic here
