# -*- coding: utf-8 -*-
from datetime import timedelta
import json
import os
from pathlib import Path
from helpers.setting_helper import get_config

USE_CACHE = get_config('general.cache.use')
CACHE_TIME_DELTA = timedelta(minutes=get_config('general.cache.max-age'))
CONFIG_WARNINGS = {}

def update_stylelint_rules():
    print('updates rules used in defaults/css-stylelint-standard.json')

    base_directory = Path(os.path.dirname(
        os.path.realpath(__file__)) + os.path.sep).parent
    rules_path = os.path.join(base_directory, 'node_modules', 'stylelint', 'lib', 'rules')
    rule_names = os.listdir(rules_path)

    rules = {}
    for rule_name in rule_names:
        if 'no-unknown' in rule_name:
            rules[rule_name] = True
        elif 'no-deprecated' in rule_name:
            rules[rule_name] = True
        elif 'no-invalid' in rule_name:
            rules[rule_name] = True
        elif 'no-vendor' in rule_name:
            rules[rule_name] = True
        elif 'no-empty' in rule_name:
            rules[rule_name] = True
        elif 'no-nonstandard' in rule_name:
            rules[rule_name] = True
        elif 'no-important' in rule_name:
            rules[rule_name] = True

    stylelint_standard_path = os.path.join(base_directory, 'defaults', 'css-stylelint-standard.json')
    with open(stylelint_standard_path, 'w', encoding='utf-8') as outfile:
        json.dump({
            'rules': rules
        }, outfile, indent=4)

