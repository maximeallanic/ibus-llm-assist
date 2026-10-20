"""The suggestion shown after the cursor: shrinking while the user types along, accepting, clearing."""
import unittest

from tests import _path  # noqa: F401
from llm_assist.completion import Suggestion


class SuggestionTest(unittest.TestCase):
    def test_consume_matching_prefix_keeps_rest(self):
        s = Suggestion()
        s.show('rain today')
        self.assertTrue(s.consume('r'))
        self.assertEqual(s.text, 'ain today')

    def test_consume_mismatch_clears(self):
        s = Suggestion()
        s.show('rain')
        self.assertFalse(s.consume('x'))
        self.assertEqual(s.text, '')

    def test_consume_grapheme_not_codepoint(self):
        s = Suggestion()
        s.show('e\u0301t')
        self.assertTrue(s.consume('e\u0301'))
        self.assertEqual(s.text, 't')

    def test_consume_last_char_empties(self):
        s = Suggestion()
        s.show('a')
        self.assertTrue(s.consume('a'))
        self.assertEqual(s.text, '')

    def test_consume_without_suggestion(self):
        self.assertFalse(Suggestion().consume('a'))

    def test_take_returns_and_clears(self):
        s = Suggestion()
        s.show('abc')
        self.assertEqual(s.take(), 'abc')
        self.assertEqual(s.text, '')


if __name__ == '__main__':
    unittest.main()
