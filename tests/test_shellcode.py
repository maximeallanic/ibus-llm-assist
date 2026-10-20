"""Reading GNOME Shell's JavaScript out of its library."""
import tempfile
import unittest
from pathlib import Path

from tests import _path  # noqa: F401
from llm_assist.shellcode import KEYBOARD_JS, gresource_sections, resource_text, shell_libraries


class ShellCodeTest(unittest.TestCase):
    def test_not_an_elf_file(self):
        with tempfile.NamedTemporaryFile() as f:
            f.write(b'#!/bin/sh\n')
            f.flush()
            self.assertEqual(gresource_sections(Path(f.name)), [])

    def test_installed_shell(self):
        libs = shell_libraries()
        if not libs:
            self.skipTest('GNOME Shell is not installed')
        self.assertIn('_getXkbId', resource_text(libs[0], KEYBOARD_JS))


if __name__ == '__main__':
    unittest.main()
