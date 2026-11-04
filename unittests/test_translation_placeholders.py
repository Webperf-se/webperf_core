# -*- coding: utf-8 -*-
"""
Offline unit tests for the placeholder translations that are added when a
rule has no translation yet.

No network or Docker access is needed. Run from the repository root:

    python -m unittest unittests.test_translation_placeholders
"""
import os
import sys
import tempfile
import unittest

# Make the repository root importable when run as `python -m unittest ...`.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tests import utils  # noqa: E402  pylint: disable=wrong-import-position


class CreateOrAppendTranslationTests(unittest.TestCase):
    """create_or_append_translation() writes the keys that are looked up."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.locales_dir = self._tmp.name

    def _po(self, lang='sv', module='a11y-statement'):
        path = os.path.join(
            self.locales_dir, lang, 'LC_MESSAGES', f'{module}.po')
        with open(path, 'r', encoding='utf-8') as file:
            return file.read()

    def _add(self, rule, severity_key=None):
        utils.create_or_append_translation(
            'a11y-statement', 'sv', rule,
            severity_key=severity_key, locales_dir=self.locales_dir)

    def test_adds_unresolved_and_resolved_by_default(self):
        self._add('some-rule')
        content = self._po()
        self.assertIn('msgid "some-rule (unresolved)"', content)
        self.assertIn('msgstr "some-rule ({0})"', content)
        self.assertIn('msgid "some-rule (resolved)"', content)
        self.assertNotIn('some-rule (info)', content)

    def test_adds_info_key_for_info_rules(self):
        # The text of an issue with severity 'info' is looked up with the
        # key '<rule> (info)', so that key has to be created too.
        self._add('no-country-rules', severity_key='info')
        content = self._po()
        self.assertIn('msgid "no-country-rules (info)"', content)
        self.assertIn('msgstr "no-country-rules (info)"', content)

    def test_no_info_key_for_other_severities(self):
        self._add('some-rule', severity_key='unresolved')
        self.assertNotIn('(info)', self._po())

    def test_does_not_duplicate_or_overwrite_existing_keys(self):
        self._add('no-country-rules', severity_key='info')
        path = os.path.join(
            self.locales_dir, 'sv', 'LC_MESSAGES', 'a11y-statement.po')
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
        translated = content.replace(
            'msgstr "no-country-rules (info)"',
            'msgstr "Inga regler hittades"')
        with open(path, 'w', encoding='utf-8', newline='') as file:
            file.write(translated)

        self._add('no-country-rules', severity_key='info')

        content = self._po()
        self.assertEqual(content.count('msgid "no-country-rules (info)"'), 1)
        self.assertIn('msgstr "Inga regler hittades"', content)

    def test_info_key_is_added_to_a_file_that_lacks_it(self):
        # A rule translated before the info key existed still gets it.
        self._add('no-country-rules')
        self.assertNotIn('(info)', self._po())
        self._add('no-country-rules', severity_key='info')
        self.assertIn('msgid "no-country-rules (info)"', self._po())


if __name__ == '__main__':
    unittest.main()
