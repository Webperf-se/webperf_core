# -*- coding: utf-8 -*-
from tests.lighthouse_base import run_test as lighthouse_base_run_test
from tests.utils import get_translation

# DEFAULTS
STRATEGY = 'mobile'
CATEGORY = 'performance'


def run_test(global_translation, lang_code, url, silance=False):
    """
    Analyzes URL with Lighthouse Performance.
    """

    local_translation = get_translation('performance_lighthouse', lang_code)
    # pylint: disable=duplicate-code
    return lighthouse_base_run_test(
        lang_code,
        url,
        STRATEGY,
        CATEGORY,
        silance,
        global_translation,
        local_translation)
