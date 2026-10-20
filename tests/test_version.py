"""One version everywhere: the package, the installer, the bootstrap's release, the translation template and the
changelog."""
import re
import unittest

from llm_assist import __version__
from tests._path import ROOT


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


class VersionTest(unittest.TestCase):
    def test_versions_agree(self):
        self.assertEqual(re.search(r'^IBLA_VERSION=(\S+)$', read('lib/common.sh'), re.M).group(1), __version__)
        self.assertEqual(re.search(r'^IBLA_RELEASE=v(\S+)$', read('install.sh'), re.M).group(1), __version__)
        self.assertIn(f'--package-version={__version__} ', read('po/update.sh'))
        self.assertIn(f'"Project-Id-Version: ibus-llm-assist {__version__}\\n"', read('po/ibus-llm-assist.pot'))

    def test_changelog_has_this_version(self):
        self.assertRegex(read('CHANGELOG.md'), rf'(?m)^## \[{re.escape(__version__)}\] - \d{{4}}-\d{{2}}-\d{{2}}$')


if __name__ == '__main__':
    unittest.main()
