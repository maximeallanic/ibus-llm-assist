"""Unicode boundaries computed by Pango: graphemes and sentence ends, in several scripts."""
import unittest

from tests import _path  # noqa: F401
from llm_assist.boundaries import (at_word_boundary, cut_at_sentence_end, ends_sentence, graphemes,  # noqa: E402
                                   sentence_start_before, trim_to_word_end)


class GraphemesTest(unittest.TestCase):
    def test_graphemes_combining_and_zwj(self):
        self.assertEqual(graphemes('e\u0301té'), ['e\u0301', 't', 'é'])
        self.assertEqual(len(graphemes('👩\u200d💻a')), 2)

    def test_graphemes_empty(self):
        self.assertEqual(graphemes(''), [])


class SentenceTest(unittest.TestCase):
    def test_sentence_end_french(self):
        t = 'Il pleut. Je '
        self.assertTrue(ends_sentence(t, len('Il pleut. ')))
        self.assertFalse(ends_sentence(t, len('Il pl')))
        self.assertFalse(ends_sentence(t, len(t)))

    def test_sentence_end_japanese(self):
        self.assertTrue(ends_sentence('雨です。', 4))
        self.assertFalse(ends_sentence('雨です。', 2))

    def test_sentence_end_arabic(self):
        t = 'هل تمطر؟ '
        self.assertTrue(ends_sentence(t, len(t)))

    def test_sentence_start_before(self):
        t = 'One. Two words. '
        self.assertEqual(sentence_start_before(t, len(t)), len('One. '))
        self.assertEqual(sentence_start_before('Solo. ', 6), 0)

    def test_cut_at_sentence_end(self):
        self.assertEqual(cut_at_sentence_end(' the rain. Then more'), ' the rain.')
        self.assertEqual(cut_at_sentence_end('雨です。次'), '雨です。')
        self.assertEqual(cut_at_sentence_end(' no end'), ' no end')


class WordEndTest(unittest.TestCase):
    def test_trim_to_word_end_drops_partial_word(self):
        self.assertEqual(trim_to_word_end(' a short sto'), ' a short')
        self.assertEqual(trim_to_word_end(' رائد فضاء يكت'), ' رائد فضاء')

    def test_trim_to_word_end_keeps_single_word(self):
        self.assertEqual(trim_to_word_end(' alone'), ' alone')


class WordBoundaryTest(unittest.TestCase):
    def test_inside_a_word_is_no_boundary(self):
        self.assertFalse(at_word_boundary('Hello world', 3))
        self.assertTrue(at_word_boundary('Hello world', 5))
        self.assertTrue(at_word_boundary('Hello world', 11))

    def test_scripts_without_spaces(self):
        # Between ideographs and kana runs, Pango finds boundaries; the end of the text always is one.
        self.assertTrue(at_word_boundary('東京に行った', 2))
        self.assertTrue(at_word_boundary('สวัสดีครับ', 10))

    def test_right_to_left(self):
        text = 'مرحبا بالعالم'
        self.assertTrue(at_word_boundary(text, 5))
        self.assertFalse(at_word_boundary(text, 2))


if __name__ == '__main__':
    unittest.main()
