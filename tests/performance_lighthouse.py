# -*- coding: utf-8 -*-
from helpers.setting_helper import get_config
from tests.lighthouse_base import run_test as lighthouse_base_run_test, get_lighthouse_translations

# DEFAULTS
STRATEGY = 'mobile'
CATEGORY = 'performance'

def run_test(global_translation, url, silance=False):
    """
    Analyzes URL with Lighthouse Performance.
    """

    translations = get_lighthouse_translations('performance_lighthouse',
                                               get_config('general.language'),
                                               global_translation)
    # pylint: disable=duplicate-code
    return lighthouse_base_run_test(
        url,
        STRATEGY,
        CATEGORY,
        silance,
        translations)
