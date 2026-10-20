"""Guard against rephrasing: a correction must stay a light edit, measured in graphemes in any script."""
import unittest

from tests import _path  # noqa: F401
from llm_assist.correction import is_light_edit


class LightEditTest(unittest.TestCase):
    def test_light_edit_accepts_accent_fix(self):
        self.assertTrue(is_light_edit('Il a ete', 'Il a été'))

    def test_light_edit_rejects_rewrite(self):
        self.assertFalse(is_light_edit('ok cool', 'That sounds wonderful to me'))

    def test_light_edit_japanese(self):
        self.assertTrue(is_light_edit('雨がふる。', '雨が降る。'))

    def test_light_edit_arabic(self):
        self.assertTrue(is_light_edit('ذهبت الى المدرسه', 'ذهبت إلى المدرسة'))

    def test_identical_is_light(self):
        self.assertTrue(is_light_edit('Same.', 'Same.'))


if __name__ == '__main__':
    unittest.main()
