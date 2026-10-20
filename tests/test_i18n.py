"""Translations: the template matches the sources, every catalogue is complete and keeps the placeholders."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._path import ROOT

PLACEHOLDER = re.compile(r'\{\w+\}|%s')
needs_gettext = unittest.skipUnless(shutil.which('xgettext') and shutil.which('msgfmt'), 'gettext tools missing')


def entries(po: Path) -> dict[str, str]:
    """msgid -> msgstr of a .po/.pot file, header and obsolete entries left out."""
    text = po.read_text(encoding='utf-8')
    found = {}
    for block in re.split(r'\n\n+', text):
        if block.lstrip().startswith('#~'):
            continue
        fuzzy = re.search(r'^#,.*\bfuzzy\b', block, re.M) is not None
        m = re.search(r'^msgid ((?:".*"\n?)+)msgstr ((?:".*"\n?)+)', block, re.M)
        if not m:
            continue
        msgid = ''.join(eval(x) for x in m.group(1).split('\n') if x)  # noqa: S307 - po string literals
        msgstr = ''.join(eval(x) for x in m.group(2).split('\n') if x)  # noqa: S307
        if msgid:
            found[msgid] = '' if fuzzy else msgstr
    return found


class TemplateTest(unittest.TestCase):
    @needs_gettext
    def test_template_is_up_to_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'repo'
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns('.git', 'build', '__pycache__'))
            subprocess.run(['bash', 'po/update.sh'], cwd=copy, check=True, capture_output=True)
            fresh = entries(copy / 'po' / 'ibus-llm-assist.pot')
        current = entries(ROOT / 'po' / 'ibus-llm-assist.pot')
        self.assertEqual(sorted(fresh), sorted(current), 'run po/update.sh')


class CatalogueTest(unittest.TestCase):
    def catalogues(self):
        return [ROOT / 'po' / f'{lang}.po' for lang in (ROOT / 'po' / 'LINGUAS').read_text().split()]

    def test_every_language_in_linguas_has_a_catalogue(self):
        for po in self.catalogues():
            self.assertTrue(po.is_file(), po)

    def test_catalogues_are_complete_and_keep_placeholders(self):
        template = entries(ROOT / 'po' / 'ibus-llm-assist.pot')
        for po in self.catalogues():
            translated = entries(po)
            for msgid in template:
                with self.subTest(po=po.name, msgid=msgid):
                    msgstr = translated.get(msgid, '')
                    self.assertTrue(msgstr, 'untranslated or fuzzy')
                    self.assertEqual(sorted(PLACEHOLDER.findall(msgid)), sorted(PLACEHOLDER.findall(msgstr)))
                    self.assertEqual(msgid.endswith('\n'), msgstr.endswith('\n'))

    @needs_gettext
    def test_catalogues_compile_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            for po in self.catalogues():
                lang = po.stem
                mo = Path(tmp) / lang / 'LC_MESSAGES' / 'ibus-llm-assist.mo'
                mo.parent.mkdir(parents=True)
                subprocess.run(['msgfmt', '--check', '-o', mo, po], check=True)
            env = dict(os.environ, IBUS_LLM_ASSIST_LOCALEDIR=tmp, LANGUAGE='fr', LC_ALL='C.UTF-8')
            out = subprocess.run(
                ['python3', '-I', '-c', 'import sys; sys.path.insert(0, sys.argv[1]); '
                 'from llm_assist.i18n import _; print(_("Suggestions are on for: {layouts}"))', ROOT],
                env=env, capture_output=True, text=True, check=True).stdout
            self.assertEqual(out.strip(), 'Suggestions activées pour : {layouts}')


class LocaleDirTest(unittest.TestCase):
    def locale_dir_of(self, package_dir: Path) -> str | None:
        """_locale_dir() as computed by a copy of i18n.py placed at package_dir."""
        package_dir.mkdir(parents=True)
        shutil.copy(ROOT / 'llm_assist' / 'i18n.py', package_dir / 'i18n.py')
        env = {k: v for k, v in os.environ.items() if k != 'IBUS_LLM_ASSIST_LOCALEDIR'}
        return subprocess.run(['python3', '-I', '-c', 'import sys; sys.path.insert(0, sys.argv[1]); import i18n; '
                               'print(i18n._locale_dir())', package_dir], env=env, capture_output=True, text=True,
                              check=True).stdout.strip()

    def test_installed_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            got = self.locale_dir_of(Path(tmp) / 'usr' / 'lib' / 'ibus-llm-assist' / 'llm_assist')
            self.assertEqual(got, str(Path(tmp).resolve() / 'usr' / 'share' / 'locale'))

    def test_shallow_checkout_without_catalogues(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.locale_dir_of(Path(tmp) / 'llm_assist'), 'None')


if __name__ == '__main__':
    unittest.main()
