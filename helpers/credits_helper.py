# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path


def get_credits(global_translation):
    text = '# Credits\r\n' # global_translation('TEXT_CREDITS')
    text += 'Following shows projects and contributors for webperf-core and its dependencies.\r\n'

    folder = 'defaults'
    base_directory = os.path.join(Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent)

    credits_path = os.path.join(base_directory, folder, 'credits.json')
    if not os.path.exists(credits_path):
        os.makedirs(credits_path)

    with open(credits_path, encoding='utf-8') as json_input_file:
        data = json.load(json_input_file)
        text += '\r\n'
        for creditor in data['creditors']:
            text += f'## {creditor["name"]}\r\n'
            if 'license' in creditor and creditor["license"] != '':
                text += f'License: {creditor["license"]}\r\n'
            if 'usage' in creditor and len(creditor["usage"]) > 0:
                text += f'usage: {creditor["usage"]}\r\n'
            if 'contributors' in creditor and creditor["contributors"] != '':
                text += 'Contributors:\r\n'
                for contributor in creditor["contributors"]:
                    text += f'- {contributor}\r\n'
    return text

def set_credits():
    # Get all websites used by get_http_content
    # - get_http_content\(['"\r\n\t ]+[^"']+["']
    # Get all contributors of repo
    # - https://api.github.com/repos/Webperf-se/webperf_core/contributors
    a = 1
