# -*- coding: utf-8 -*-
"""
Checks that the test registry in helpers/test_helper.py and the list of
tests in docs/tests/README.md agree, so that a new test is documented and
a removed one is dropped from the docs. Run from the repository root:

    python -m unittest unittests.test_registry
"""
import os
import re
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from helpers import test_helper  # noqa: E402  pylint: disable=wrong-import-position

TESTS_README = os.path.join(REPO_ROOT, 'docs', 'tests', 'README.md')


def documented_tests():
    """Returns {test number: linked file} from the list in docs/tests/README.md."""
    with open(TESTS_README, encoding='utf-8') as readme:
        content = readme.read()
    return {int(number): link for number, link in
            re.findall(r"^\* (\d+) - \[[^\]]+\]\(([^)]+)\)", content, re.MULTILINE)}


class RegistryTests(unittest.TestCase):
    def test_every_registered_test_is_documented(self):
        documented = documented_tests()
        missing = sorted(set(test_helper.TEST_ALL_FUNCS) - set(documented))
        self.assertEqual(missing, [], f"tests without a row in docs/tests/README.md: {missing}")

    def test_every_documented_test_is_registered(self):
        documented = documented_tests()
        extra = sorted(set(documented) - set(test_helper.TEST_ALL_FUNCS))
        self.assertEqual(extra, [], f"documented tests that are not registered: {extra}")

    def test_documented_pages_exist(self):
        for number, link in documented_tests().items():
            path = os.path.join(os.path.dirname(TESTS_README), link)
            self.assertTrue(os.path.exists(path), f"test {number} links to missing {link}")


if __name__ == '__main__':
    unittest.main()
