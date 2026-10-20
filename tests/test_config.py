"""Server settings: what counts as local, and the optional API key file."""
import os
import tempfile
import unittest
from pathlib import Path

from tests import _path  # noqa: F401
from llm_assist.config import is_local, read_api_key


class LocalTest(unittest.TestCase):
    def test_loopback_is_local(self):
        for url in ('http://127.0.0.1:8033', 'http://localhost:11434', 'http://[::1]:8080', 'http://127.0.0.2'):
            self.assertTrue(is_local(url), url)

    def test_other_hosts_are_not(self):
        for url in ('http://192.168.1.10:8033', 'https://api.example.com', 'http://localhost.example.com', 'x'):
            self.assertFalse(is_local(url), url)


class ApiKeyTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'api-key'

    def test_missing_file_is_no_key(self):
        self.assertEqual(read_api_key(self.path), '')

    def test_private_file_is_read(self):
        self.path.write_text('secret\n')
        os.chmod(self.path, 0o600)
        self.assertEqual(read_api_key(self.path), 'secret')

    def test_file_readable_by_others_is_ignored(self):
        self.path.write_text('secret\n')
        os.chmod(self.path, 0o644)
        with self.assertLogs('ibus-llm-assist', 'WARNING'):
            self.assertEqual(read_api_key(self.path), '')


if __name__ == '__main__':
    unittest.main()
