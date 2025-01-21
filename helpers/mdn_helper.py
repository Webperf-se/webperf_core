# -*- coding: utf-8 -*-
import getopt
import sys
from datetime import datetime, timedelta
from pathlib import Path
import json
import re
import os
from bs4 import BeautifulSoup
from tests.utils import get_http_content
from helpers.setting_helper import get_config
from helpers.test_helper import get_error_info

USE_CACHE = get_config('general.cache.use')
CACHE_TIME_DELTA = timedelta(minutes=get_config('general.cache.max-age'))
CONFIG_WARNINGS = {}

def get_mdn_web_docs_css_features():
    """
    Returns a tuple containing 2 lists, first one of CSS features and
    second of CSS functions keys formatted as non-existent properties.
    """
    features = {}
    functions = {}

    html = get_http_content(
        'https://developer.mozilla.org/en-US/docs/Web/CSS/Reference')

    soup = BeautifulSoup(html, 'lxml')

    index_element = soup.find('div', class_='index')
    if index_element:
        links = index_element.find_all('a')
        for link in links:
            regex = r'(?P<name>[a-z\-0-9]+)(?P<func>[()]{0,2})[ ]*'
            matches = re.search(regex, link.string)
            if matches:
                property_name = matches.group('name')
                is_function = matches.group('func') in '()'
                if is_function:
                    functions[f"{property_name}"] = link.get('href')
                else:
                    features[f"{property_name}"] = link.get('href')
    else:
        print('no index element found')

    return (features, functions)

def get_mdn_web_docs_deprecated_elements():
    """
    Returns a list of strings, of deprecated html elements.
    """
    elements = []

    html = get_http_content(
        ('https://developer.mozilla.org/'
         'en-US/docs/Web/HTML/Element'
         '#obsolete_and_deprecated_elements'))

    soup = BeautifulSoup(html, 'lxml')

    header = soup.find('h2', id = 'obsolete_and_deprecated_elements')
    if header is None:
        return []

    section = header.parent
    if section is None:
        return []

    tbody = section.find('tbody')
    if tbody is None:
        return []

    table_rows = tbody.find_all('tr')
    if table_rows is None:
        return []

    for table_row in table_rows:
        if table_row is None:
            continue

        first_td = table_row.find('td')
        if first_td is None:
            continue

        code = first_td.find('code')
        if code is None:
            continue

        regex = r'(\&lt;|<)(?P<name>[^<>]+)(\&gt;|>)'
        matches = re.search(regex, code.string)
        if matches:
            property_name = '<' + matches.group('name')
            elements.append(property_name)

    elements = sorted(list(set(elements)))

    return elements

def update_mdn_rules():
    data = {}
    css_features, css_functions = get_mdn_web_docs_css_features()

    data['css'] = {
        'features': css_features,
        'functions': css_functions
    }

    html_deprecated_elements = get_mdn_web_docs_deprecated_elements()

    data['html'] = {
        'deprecated': {
            'elements': html_deprecated_elements
        }
    }

    save_mdn_rules(data)


def save_mdn_rules(rules):
    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent

    file_path = os.path.join(base_directory, 'defaults', 'mdn-rules.json')

    rules["loaded"] = True

    with open(file_path, 'w', encoding='utf-8') as outfile:
        json.dump(rules, outfile, indent=4)
    return rules
