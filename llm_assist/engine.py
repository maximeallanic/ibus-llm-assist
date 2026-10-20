"""IBus side of the engine: turns IBus calls into Controller inputs and Controller outputs into IBus requests.

Keys are only observed: whatever the controller does not take goes to IBus.EngineSimple, which composes dead keys
and Compose sequences as IBus's own xkb engines do (with an IBus source active, the application composes nothing),
and hands every other key back to the application.
"""
import gi

gi.require_version('IBus', '1.0')
from gi.repository import Gio, GLib, IBus  # noqa: E402

from .controller import Controller  # noqa: E402
from .i18n import _  # noqa: E402
from .llm import LlmClient  # noqa: E402

# IBus.AttrPreedit.PREDICTION. PyGObject declares the enum as flags and hides the non-power-of-two members.
_PREDICTION = 3
_OTHER_MODIFIERS = (IBus.ModifierType.SHIFT_MASK | IBus.ModifierType.MOD1_MASK | IBus.ModifierType.MOD4_MASK
                    | IBus.ModifierType.SUPER_MASK)
# Modifiers that turn a key into a shortcut: with one held, the key types nothing (AltGr is MOD5 and still types).
_COMMAND_MODIFIERS = (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK | IBus.ModifierType.MOD4_MASK
                      | IBus.ModifierType.SUPER_MASK)
# Settings keys shown as toggles in the input source menu, with their labels.
_TOGGLES = (('completion-enabled', _('Suggestions')), ('correction-enabled', _('Corrections')))


def prediction_text(text: str) -> IBus.Text:
    """text marked as predicted, so that the application styles it as a suggestion."""
    ibus_text = IBus.Text.new_from_string(text)
    attrs = IBus.AttrList()
    attrs.append(IBus.Attribute.new(IBus.AttrType.HINT, _PREDICTION, 0, len(text)))
    ibus_text.set_attributes(attrs)
    return ibus_text


class LlmAssistEngine(IBus.EngineSimple):
    __gtype_name__ = 'LlmAssistEngine'

    def __init__(self, llm: LlmClient, settings: Gio.Settings, **kwargs) -> None:
        super().__init__(**kwargs)
        self._settings = settings
        self._controller = Controller(self, llm, lambda ms, fn: GLib.timeout_add(ms, fn), GLib.source_remove)
        self._props = IBus.PropList()
        for key, label in _TOGGLES:
            self._props.append(IBus.Property(key=key, prop_type=IBus.PropType.TOGGLE,
                                             label=IBus.Text.new_from_string(label), visible=True))
        self._settings_handler = settings.connect('changed', lambda *_: self._sync_settings())
        self._sync_settings()

    # Sink

    def show_prediction(self, text: str) -> None:
        # Cursor at 0: the suggestion sits after the caret, which stays where the user typed.
        self.update_preedit_text_with_mode(prediction_text(text), 0, True, IBus.PreeditFocusMode.CLEAR)

    def clear_preedit(self) -> None:
        self.update_preedit_text_with_mode(IBus.Text.new_from_string(''), 0, False, IBus.PreeditFocusMode.CLEAR)

    def commit(self, text: str) -> None:
        self.commit_text(IBus.Text.new_from_string(text))

    def delete_surrounding(self, offset: int, n_chars: int) -> None:
        self.delete_surrounding_text(offset, n_chars)

    # IBus

    def do_process_key_event(self, keyval: int, keycode: int, state: int) -> bool:
        if state & IBus.ModifierType.RELEASE_MASK:
            return False
        ctrl = bool(state & IBus.ModifierType.CONTROL_MASK) and not state & _OTHER_MODIFIERS
        # PyGObject returns the character as a str, empty for a key that types none.
        char = '' if state & _COMMAND_MODIFIERS else IBus.keyval_to_unicode(keyval)
        return (self._controller.on_key(char or None, ctrl, keyval, keycode)
                or IBus.EngineSimple.do_process_key_event(self, keyval, keycode, state))

    def do_set_surrounding_text(self, text: IBus.Text, cursor_pos: int, anchor_pos: int) -> None:
        IBus.Engine.do_set_surrounding_text(self, text, cursor_pos, anchor_pos)
        self._controller.on_surrounding(text.get_text(), cursor_pos, anchor_pos)

    def do_set_capabilities(self, caps: int) -> None:
        self._controller.on_capabilities(bool(caps & IBus.Capabilite.SURROUNDING_TEXT))

    def do_set_content_type(self, purpose: int, hints: int) -> None:
        self._controller.on_content_type(purpose, hints)

    # Focus and reset chain to EngineSimple, which drops a pending dead key: one engine serves every field.

    def do_focus_in(self) -> None:
        IBus.EngineSimple.do_focus_in(self)
        self.register_properties(self._props)
        # The first request makes the client start reporting its surrounding text.
        self.get_surrounding_text()

    def do_focus_out(self) -> None:
        self._controller.on_focus_out()
        IBus.EngineSimple.do_focus_out(self)

    def do_reset(self) -> None:
        self._controller.on_focus_out()
        IBus.EngineSimple.do_reset(self)

    def do_destroy(self) -> None:
        # ibus-daemon drops this engine (source switch, restart): nothing of it may outlive the D-Bus object, neither
        # the pause timer nor the requests the model still reads nor the handler on the settings every engine shares.
        self._controller.on_focus_out()
        self._settings.disconnect(self._settings_handler)
        IBus.EngineSimple.do_destroy(self)

    def do_property_activate(self, prop_name: str, prop_state: int) -> None:
        if prop_name in dict(_TOGGLES):
            self._settings.set_boolean(prop_name, prop_state == IBus.PropState.CHECKED)

    def _sync_settings(self) -> None:
        self._controller.completion_enabled = self._settings.get_boolean('completion-enabled')
        self._controller.correction_enabled = self._settings.get_boolean('correction-enabled')
        self._controller.PAUSE_MS = self._settings.get_int('pause-ms')
        for i, (key, _label) in enumerate(_TOGGLES):
            prop = self._props.get(i)
            prop.set_state(IBus.PropState.CHECKED if self._settings.get_boolean(key) else IBus.PropState.UNCHECKED)
            self.update_property(prop)
