"""What the IBus side relies on: the pre-edit hint, key events, the component file, the settings schema."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import gi

gi.require_version('IBus', '1.0')
from gi.repository import Gio, GLib, IBus  # noqa: E402

from tests import _path  # noqa: F401,E402
from llm_assist.config import SCHEMA  # noqa: E402
from llm_assist.engine import HAS_PREDICTION_HINT, LlmAssistEngine, prediction_attribute, prediction_text  # noqa: E402
from llm_assist.layouts import Layout, engines_xml  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / 'data'


class ContractTest(unittest.TestCase):
    def test_prediction_is_the_prediction_hint_when_ibus_has_hints(self):
        # IBUS_ATTR_TYPE_HINT (4) with IBUS_ATTR_PREEDIT_PREDICTION (3), IBus 1.5.33 and later.
        self.assertEqual(prediction_attribute(hint=True), (4, 3))

    def test_prediction_is_the_legacy_grey_without_hints(self):
        # Before IBus 1.5.33: the foreground colour IBus maps to and from IBUS_ATTR_PREEDIT_PREDICTION.
        self.assertEqual(prediction_attribute(hint=False), (2, 0x7F7F7F))  # IBUS_ATTR_TYPE_FOREGROUND

    def test_this_ibus_gets_the_form_it_supports(self):
        # Built with the IBus the tests run on, which refuses an attribute type it does not know (before 1.5.33,
        # IBus.Attribute.new returns NULL for the hint).
        has_hint = hasattr(IBus.AttrType, 'HINT')
        self.assertEqual(HAS_PREDICTION_HINT, has_hint)
        text = prediction_text('été là')
        self.assertEqual(text.get_text(), 'été là')
        attr = text.get_attributes().get(0)
        self.assertIsNone(text.get_attributes().get(1))
        self.assertEqual((attr.get_attr_type(), attr.get_value()), prediction_attribute(has_hint))
        self.assertEqual((attr.get_start_index(), attr.get_end_index()), (0, 6))

    def test_component_lists_the_engines_its_program_prints(self):
        # ibus-daemon runs the <engines exec> command: here a stand-in printing what --xml prints for one layout.
        layouts = {'fr+oss': Layout('fr+oss', 'French (alt.)', 'fr', 'fra')}
        with tempfile.TemporaryDirectory() as tmp:
            program = Path(tmp) / 'ibus-engine-llm-assist'
            program.write_text(f"#!/bin/sh\ncat <<'EOF'\n{engines_xml(['fr+oss'], layouts)}\nEOF\n")
            program.chmod(0o755)
            component_file = Path(tmp) / 'ibus-llm-assist.xml'
            component_file.write_text((DATA / 'ibus-llm-assist.xml.in').read_text()
                                      .replace('@LIBEXECDIR@', tmp).replace('@VERSION@', '0'))
            component = IBus.Component.new_from_file(str(component_file))
        self.assertEqual(component.get_name(), 'io.github.maximeallanic.IBusLlmAssist')
        self.assertEqual(component.get_exec(), f'{tmp}/ibus-engine-llm-assist --ibus')
        engine, = component.get_engines()
        self.assertEqual(engine.get_name(), 'llm-assist:fr+oss')
        self.assertEqual((engine.get_layout(), engine.get_layout_variant()), ('fr', 'oss'))

    def test_schema_compiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(DATA / f'{SCHEMA}.gschema.xml', tmp)
            subprocess.run(['glib-compile-schemas', '--strict', tmp], check=True)


class _Settings:
    def __init__(self):
        self.handlers = set()

    def get_boolean(self, key):
        return True

    def get_int(self, key):
        return 400

    def connect(self, *args):
        self.handlers.add(len(self.handlers) + 1)
        return len(self.handlers)

    def disconnect(self, handler):
        self.handlers.remove(handler)


class _Keys:
    def __init__(self):
        self.calls = []

    def on_key(self, char, ctrl, keysym, keycode=0):
        self.calls.append((char, ctrl, keysym))
        return False

    def on_focus_out(self):
        self.calls.append('focus-out')


# Gio.TestDBus starts a private bus with the dbus-daemon program (Fedora's default bus is dbus-broker: install the
# dbus-daemon package to run this test there).
@unittest.skipUnless(shutil.which('dbus-daemon'), 'dbus-daemon is needed for a private test bus')
class KeyEventTest(unittest.TestCase):
    """Key events as ibus-daemon delivers them: through the process-key-event signal of a live engine."""

    @classmethod
    def setUpClass(cls):
        cls.bus = Gio.TestDBus.new(Gio.TestDBusFlags.NONE)
        cls.bus.up()
        cls.connection = Gio.DBusConnection.new_for_address_sync(
            cls.bus.get_bus_address(),
            Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION)

    @classmethod
    def tearDownClass(cls):
        cls.connection.close_sync()
        cls.bus.down()

    def setUp(self):
        self.settings = _Settings()
        self.engine = LlmAssistEngine(None, self.settings, engine_name='llm-assist', connection=self.connection,
                                      object_path=f'/test/Engine/{id(self)}')
        self.keys = self.engine._controller = _Keys()

    def press(self, keyval, state=0):
        return self.engine.emit('process-key-event', keyval, 0, state)

    def test_character_keys_reach_the_controller(self):
        self.press(ord('a'))
        self.press(0xe9)  # é
        self.assertEqual(self.keys.calls, [('a', False, ord('a')), ('é', False, 0xe9)])

    def test_key_without_character_has_none(self):
        self.press(0xffe3)  # Control_L
        self.assertEqual(self.keys.calls, [(None, False, 0xffe3)])

    def test_ctrl_tab_is_ctrl(self):
        self.press(0xff09, IBus.ModifierType.CONTROL_MASK)
        self.assertEqual(self.keys.calls, [(None, True, 0xff09)])

    def test_shortcut_types_no_character(self):
        self.press(ord('c'), IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.SHIFT_MASK)
        self.press(ord('f'), IBus.ModifierType.MOD1_MASK)
        self.press(ord('e'), IBus.ModifierType.MOD5_MASK)  # AltGr still types
        self.assertEqual(self.keys.calls, [(None, False, ord('c')), (None, False, ord('f')), ('e', False, ord('e'))])

    def test_release_is_ignored(self):
        self.press(ord('a'), IBus.ModifierType.RELEASE_MASK)
        self.assertEqual(self.keys.calls, [])

    def test_dead_key_composes_with_the_next_letter(self):
        # With an IBus source active the Shell gives every key to the engine: composing is the engine's job, as for
        # IBus's own xkb engines, and the application never sees the dead key.
        commits = []
        sub = self.connection.signal_subscribe(
            None, 'org.freedesktop.IBus.Engine', 'CommitText', f'/test/Engine/{id(self)}', None,
            Gio.DBusSignalFlags.NONE,
            lambda *args: commits.append(IBus.Serializable.deserialize_object(args[5].get_child_value(0)).get_text()))
        self.addCleanup(self.connection.signal_unsubscribe, sub)
        handled = [self.press(0xfe51), self.press(ord('e'))]  # dead_acute, e
        context, deadline = GLib.MainContext.default(), GLib.get_monotonic_time() + 2_000_000
        while not commits and GLib.get_monotonic_time() < deadline:
            context.iteration(False)
        self.assertEqual((handled, commits), ([True, True], ['é']))

    def _commits(self):
        commits = []
        sub = self.connection.signal_subscribe(
            None, 'org.freedesktop.IBus.Engine', 'CommitText', f'/test/Engine/{id(self)}', None,
            Gio.DBusSignalFlags.NONE,
            lambda *args: commits.append(IBus.Serializable.deserialize_object(args[5].get_child_value(0)).get_text()))
        self.addCleanup(self.connection.signal_unsubscribe, sub)
        return commits

    def _settle(self):
        context, deadline = GLib.MainContext.default(), GLib.get_monotonic_time() + 500_000
        while GLib.get_monotonic_time() < deadline:
            context.iteration(False)

    def test_pending_dead_key_dropped_on_focus_out(self):
        # One engine serves every field: a dead key left pending must not compose in the next one (a password field).
        commits = self._commits()
        self.press(0xfe51)
        self.engine.emit('focus-out')
        self.assertFalse(self.press(ord('e')))
        self._settle()
        self.assertEqual(commits, [])

    def test_pending_dead_key_dropped_on_reset(self):
        commits = self._commits()
        self.press(0xfe51)
        self.engine.emit('reset')
        self.assertFalse(self.press(ord('e')))
        self._settle()
        self.assertEqual(commits, [])

    def test_plain_letter_goes_back_to_the_application(self):
        self.assertFalse(self.press(ord('e')))

    def test_menu_properties_serialize(self):
        # Every string field must be set: a NULL one (the icon, on Ubuntu 24.04) makes an invalid D-Bus message.
        for i in range(2):
            prop = self.engine._props.get(i)
            self.assertEqual(prop.get_icon(), '')
            self.assertIsNotNone(IBus.Serializable.serialize_object(prop))

    def test_destroy_releases_controller_and_settings(self):
        # ibus-daemon recreates engines on a source switch: a dropped one must keep no timer, request nor handler.
        destroyed = []
        self.engine.connect('destroy', destroyed.append)
        self.engine.destroy()
        self.assertEqual((self.keys.calls, self.settings.handlers, destroyed), (['focus-out'], set(), [self.engine]))


if __name__ == '__main__':
    unittest.main()
