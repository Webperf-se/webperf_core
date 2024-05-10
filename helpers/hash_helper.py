# -*- coding: utf-8 -*-

import base64
import hashlib

def create_sha256_hash(data):
    """
    Creates a SHA-256 hash of the given data and returns it in base64 encoded format.

    This function first creates a SHA-256 hash of the input data. It then encodes this hash 
    using base64 encoding and returns the result as a string.

    Parameters:
    data (bytes): The data to be hashed. This should be in bytes format.

    Returns:
    str: The base64 encoded SHA-256 hash of the input data.
    """
    sha_signature = hashlib.sha256(data).digest()
    base64_encoded_sha_signature = base64.b64encode(sha_signature).decode()
    return base64_encoded_sha_signature
