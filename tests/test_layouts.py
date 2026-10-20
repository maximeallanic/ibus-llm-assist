"""Layouts the engine is offered with, the engine list ibus-daemon reads, and the input-source swap."""
import tempfile
import textwrap
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from tests import _path  # noqa: F401
from llm_assist.layouts import Layout, engine_layout, engines_xml, layouts_in_sources, read_registry
from llm_assist.sources import disable, enable, enabled_layouts

RULES = textwrap.dedent('''\
    <xkbConfigRegistry version="1.1">
      <layoutList>
        <layout>
          <configItem><name>fr</name><shortDescription>fr</shortDescription><description>French</description>
            <languageList><iso639Id>fra</iso639Id></languageList></configItem>
          <variantList>
            <variant><configItem><name>oss</name><description>French (alt.)</description></configItem></variant>
          </variantList>
        </layout>
        <layout>
          <configItem><name>ara</name><shortDescription>ar</shortDescription><description>Arabic</description>
            <languageList><iso639Id>ara</iso639Id></languageList></configItem>
        </layout>
        <layout><configItem><name>custom</name><description>Custom</description></configItem></layout>
      </layoutList>
    </xkbConfigRegistry>
    ''')


class RegistryTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / 'evdev.xml'
        path.write_text(RULES)
        self.registry = read_registry(path)

    def test_layouts_and_variants(self):
        self.assertEqual(self.registry['fr'], Layout('fr', 'French', 'fr', 'fra'))
        # A variant inherits the short label and language of its layout.
        self.assertEqual(self.registry['fr+oss'], Layout('fr+oss', 'French (alt.)', 'fr', 'fra'))
        self.assertEqual(self.registry['custom'].language, 'other')

    def test_engines_xml(self):
        engines = ET.fromstring(engines_xml(['fr+oss', 'ara', 'unknown'], self.registry))
        names = [e.findtext('name') for e in engines]
        self.assertEqual(names, ['llm-assist:fr+oss', 'llm-assist:ara'])
        first, second = engines
        self.assertEqual((first.findtext('layout'), first.findtext('layout_variant')), ('fr', 'oss'))
        self.assertIsNone(second.find('layout_variant'))
        self.assertEqual((second.findtext('language'), second.findtext('symbol')), ('ara', 'ar'))
        self.assertIn('Arabic', second.findtext('longname'))

    def test_real_registry_has_common_layouts(self):
        registry = read_registry()
        if not registry:
            self.skipTest('no xkeyboard-config registry on this system')
        for xkb_id in ('us', 'fr', 'de', 'ara', 'jp', 'us+intl'):
            self.assertIn(xkb_id, registry)


class SourcesTest(unittest.TestCase):
    SOURCES = [('xkb', 'fr'), ('ibus', 'mozc-jp'), ('xkb', 'us+intl')]

    def test_engine_layout(self):
        self.assertEqual(engine_layout('llm-assist:us+intl'), 'us+intl')
        self.assertIsNone(engine_layout('mozc-jp'))

    def test_layouts_in_sources_reads_both_forms(self):
        self.assertEqual(layouts_in_sources([('xkb', 'fr'), ('ibus', 'llm-assist:de'), ('ibus', 'mozc-jp'),
                                             ('xkb', 'de')]), ['fr', 'de'])

    def test_enable_replaces_layouts_in_place(self):
        self.assertEqual(enable(self.SOURCES),
                         [('ibus', 'llm-assist:fr'), ('ibus', 'mozc-jp'), ('ibus', 'llm-assist:us+intl')])

    def test_enable_only_wanted(self):
        self.assertEqual(enable(self.SOURCES, lambda x: '+' not in x),
                         [('ibus', 'llm-assist:fr'), ('ibus', 'mozc-jp'), ('xkb', 'us+intl')])

    def test_enable_drops_a_layout_whose_engine_is_listed(self):
        self.assertEqual(enable([('ibus', 'llm-assist:fr'), ('xkb', 'fr')]), [('ibus', 'llm-assist:fr')])

    def test_disable_round_trip(self):
        self.assertEqual(disable(enable(self.SOURCES)), self.SOURCES)

    def test_disable_keeps_sources_added_since(self):
        enabled = enable(self.SOURCES) + [('xkb', 'de')]
        self.assertEqual(disable(enabled), self.SOURCES + [('xkb', 'de')])

    def test_disable_drops_an_engine_whose_layout_is_listed(self):
        self.assertEqual(disable([('xkb', 'fr'), ('ibus', 'llm-assist:fr')]), [('xkb', 'fr')])

    def test_enabled_layouts(self):
        self.assertEqual(enabled_layouts(enable(self.SOURCES)), ['fr', 'us+intl'])


if __name__ == '__main__':
    unittest.main()
