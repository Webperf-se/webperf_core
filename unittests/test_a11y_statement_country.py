# -*- coding: utf-8 -*-
"""
Checks that tests.a11y-statement.country reaches plugin-accessibility-statement.

    python -m unittest unittests.test_a11y_statement_country
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helpers import test_helper  # noqa: E402  pylint: disable=wrong-import-position


class CountryArgTests(unittest.TestCase):
    def _arg(self, value):
        with mock.patch.object(test_helper, 'get_config', return_value=value):
            return test_helper.get_a11y_statement_country_arg()

    def test_empty_setting_lets_the_plugin_choose(self):
        self.assertEqual(self._arg(''), '')
        self.assertEqual(self._arg(None), '')

    def test_country_is_passed_in_lowercase(self):
        self.assertEqual(self._arg('SE'), '--allystatement.country se ')

    def test_anything_but_letters_is_ignored(self):
        self.assertEqual(self._arg('se --plugins.add x'), '')


if __name__ == '__main__':
    unittest.main()
