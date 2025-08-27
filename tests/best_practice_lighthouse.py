# -*- coding: utf-8 -*-
from helpers.setting_helper import get_config
from tests.lighthouse_base import run_test as lighthouse_base_run_test, get_lighthouse_translations

def run_test(global_translation, url, strategy='mobile', category='best-practices'):
    """
    Analyzes URL with Lighthouse Best-practices.
    """
    translations = get_lighthouse_translations(
        'best_practice_lighthouse',
        get_config('general.language'),
        global_translation)
    # pylint: disable=duplicate-code
    return lighthouse_base_run_test(
        url,
        strategy,
        category,
        False,
        translations)
