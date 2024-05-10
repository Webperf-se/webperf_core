# -*- coding: utf-8 -*-

import base64
import hashlib

def create_sha256_hash(data):
    sha_signature = hashlib.sha256(data).digest()
    base64_encoded_sha_signature = base64.b64encode(sha_signature).decode()
    return base64_encoded_sha_signature
