# -*- coding: utf-8 -*-
from tests.lighthouse_base import run_test as lighthouse_base_run_test, get_lighthouse_translations

def run_test(global_translation, lang_code, url, strategy='mobile', category='pwa'):
    """
    Analyzes URL with Lighthouse PWA.
    """

    translations = get_lighthouse_translations('pwa_lighthouse', lang_code, global_translation)
    # pylint: disable=duplicate-code
    return lighthouse_base_run_test(
        url,
        strategy,
        category,
        False,
        translations)
