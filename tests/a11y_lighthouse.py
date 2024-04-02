# -*- coding: utf-8 -*-
from tests.lighthouse_base import run_test as lighthouse_base_run_test, get_lighthouse_translations

def run_test(global_translation, lang_code, url, strategy='mobile', category='accessibility'):
    """
    Analyzes URL with Lighthouse Accessibility.
    """

    translations = get_lighthouse_translations('a11y_lighthouse', lang_code, global_translation)
    # pylint: disable=duplicate-code
    return lighthouse_base_run_test(
        url,
        strategy,
        category,
        False,
        translations)
