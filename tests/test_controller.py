"""Controller: key routing, completion life cycle, correction and its undo, excluded contexts."""
import unittest

from tests import _path  # noqa: F401
from llm_assist.controller import ESCAPE, KEY_Z, TAB, Z, Controller, is_undo_key

CONTROL_L, SHIFT_L = 0xffe3, 0xffe1
RIGHT, BACKSPACE, RETURN = 0xff53, 0xff08, 0xff0d

PASSWORD, PIN, TERMINAL = 8, 9, 10
NO_SPELLCHECK, PRIVATE, HIDDEN_TEXT = 2, 2048, 4096


class FakeSink:
    def __init__(self):
        self.calls = []

    def show_prediction(self, text):
        self.calls.append(('show', text))

    def clear_preedit(self):
        self.calls.append(('clear',))

    def commit(self, text):
        self.calls.append(('commit', text))

    def delete_surrounding(self, offset, n_chars):
        self.calls.append(('delete', offset, n_chars))


class FakeCancellable:
    def __init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class FakeLlm:
    def __init__(self):
        self.completions = []  # (before, on_done, cancellable)
        self.corrections = []  # (context, sentence, on_done, cancellable)

    def complete(self, before, on_done):
        c = FakeCancellable()
        self.completions.append((before, on_done, c))
        return c

    def correct(self, context, sentence, on_done):
        c = FakeCancellable()
        self.corrections.append((context, sentence, on_done, c))
        return c


class FakeClock:
    def __init__(self):
        self.now, self.timers, self.next_id = 0, {}, 1

    def schedule(self, ms, fn):
        self.timers[self.next_id] = (self.now + ms, fn)
        self.next_id += 1
        return self.next_id - 1

    def unschedule(self, timer_id):
        self.timers.pop(timer_id, None)

    def advance(self, ms):
        self.now += ms
        for timer_id, (due, fn) in sorted(self.timers.items()):
            if due <= self.now:
                del self.timers[timer_id]
                fn()


class ControllerTest(unittest.TestCase):
    def setUp(self):
        self.sink, self.llm, self.clock = FakeSink(), FakeLlm(), FakeClock()
        self.c = Controller(self.sink, self.llm, self.clock.schedule, self.clock.unschedule)
        self.c.on_capabilities(True)
        self.c.on_content_type(0, 0)

    def type(self, text_after, char=None):
        """A key press, then the surrounding text the application reports after it."""
        taken = self.c.on_key(char or text_after[-1:], False, ord(char or text_after[-1:] or ' '))
        self.c.on_surrounding(text_after, len(text_after), len(text_after))
        return taken

    def suggest(self, before='Hello wor', answer='ld'):
        self.type(before)
        self.clock.advance(self.c.PAUSE_MS)
        self.llm.completions[-1][1](answer)

    # Completion

    def test_pause_requests_then_shows_prediction(self):
        self.type('Hello wor')
        self.clock.advance(self.c.PAUSE_MS - 1)
        self.assertEqual(self.llm.completions, [])
        self.clock.advance(1)
        self.assertEqual(self.llm.completions[0][0], 'Hello wor')
        self.llm.completions[0][1]('ld')
        self.assertEqual(self.sink.calls[-1], ('show', 'ld'))

    def test_ctrl_tab_commits_suggestion(self):
        self.suggest()
        self.assertTrue(self.c.on_key(None, True, TAB))
        self.assertEqual(self.sink.calls[-2:], [('clear',), ('commit', 'ld')])

    def test_ctrl_tab_typed_with_control_key_first(self):
        # A person presses Control before Tab, and the Shell forwards that press too.
        self.suggest()
        self.assertFalse(self.c.on_key(None, False, CONTROL_L))
        self.assertTrue(self.c.on_key(None, True, TAB))
        self.assertEqual(self.sink.calls[-2:], [('clear',), ('commit', 'ld')])

    def test_shift_then_matching_capital_keeps_suggestion(self):
        self.suggest('Say ', 'Hello there')
        self.assertFalse(self.c.on_key(None, False, SHIFT_L))
        self.assertFalse(self.c.on_key('H', False, ord('H')))
        self.assertEqual(self.sink.calls[-1], ('show', 'ello there'))

    def test_ctrl_tab_without_suggestion_passes(self):
        self.type('Hello')
        self.sink.calls.clear()
        self.assertFalse(self.c.on_key(None, True, TAB))
        self.assertEqual(self.sink.calls, [])

    def test_escape_clears_suggestion(self):
        self.suggest()
        self.assertTrue(self.c.on_key(None, False, ESCAPE))
        self.assertEqual(self.sink.calls[-1], ('clear',))
        self.assertFalse(self.c.on_key(None, False, ESCAPE))

    def test_typing_matching_char_shrinks(self):
        self.suggest()
        self.assertFalse(self.c.on_key('l', False, ord('l')))
        self.assertEqual(self.sink.calls[-1], ('show', 'd'))
        self.c.on_surrounding('Hello worl', 10, 10)
        self.assertNotEqual(self.sink.calls[-1], ('clear',))

    def test_typing_other_char_clears(self):
        self.suggest()
        self.assertFalse(self.c.on_key('x', False, ord('x')))
        self.assertEqual(self.sink.calls[-1], ('clear',))

    def test_stale_completion_is_dropped(self):
        self.type('Hello wor')
        self.clock.advance(self.c.PAUSE_MS)
        _, on_done, cancellable = self.llm.completions[0]
        self.type('Hello worl')
        self.assertTrue(cancellable.cancelled)
        on_done('ld')
        self.assertNotIn(('show', 'ld'), self.sink.calls)

    def test_surrounding_change_clears_suggestion(self):
        self.suggest()
        self.c.on_surrounding('Hello wor', 2, 2)
        self.assertEqual(self.sink.calls[-1], ('clear',))

    def test_focus_out_clears_without_commit(self):
        self.suggest()
        self.c.on_focus_out()
        self.assertEqual(self.sink.calls[-1], ('clear',))
        self.assertFalse(any(call[0] == 'commit' for call in self.sink.calls))

    def test_no_completion_mid_word_or_selection(self):
        self.c.on_key('o', False, ord('o'))
        self.c.on_surrounding('word', 2, 2)
        self.clock.advance(self.c.PAUSE_MS)
        self.c.on_key('o', False, ord('o'))
        self.c.on_surrounding('word ', 4, 0)
        self.clock.advance(self.c.PAUSE_MS)
        self.assertEqual(self.llm.completions, [])

    def test_no_completion_after_cursor_move_without_typing(self):
        self.c.on_surrounding('Hello wor', 9, 9)
        self.clock.advance(self.c.PAUSE_MS)
        self.assertEqual(self.llm.completions, [])

    def test_excluded_purposes(self):
        for purpose, hints in ((PASSWORD, 0), (PIN, 0), (TERMINAL, 0), (0, PRIVATE), (0, HIDDEN_TEXT)):
            with self.subTest(purpose=purpose, hints=hints):
                self.c.on_content_type(purpose, hints)
                self.type('Il a ete. ')
                self.clock.advance(self.c.PAUSE_MS)
                self.assertEqual(self.llm.completions, [])
                self.assertEqual(self.llm.corrections, [])

    def test_passive_without_surrounding_capability(self):
        self.c.on_capabilities(False)
        self.assertFalse(self.type('Il a ete. '))
        self.clock.advance(self.c.PAUSE_MS)
        self.assertFalse(self.c.on_key(None, True, TAB))
        self.assertEqual((self.llm.completions, self.llm.corrections), ([], []))

    def test_context_limited_to_recent_sentences(self):
        self.type('One. Two. Three. Four. Fi')
        self.clock.advance(self.c.PAUSE_MS)
        self.assertEqual(self.llm.completions[0][0], 'Two. Three. Four. Fi')

    # Correction

    def test_sentence_end_requests_correction(self):
        self.type('Il a ete. ')
        self.assertEqual(self.llm.corrections[0][:2], ('', 'Il a ete.'))

    def test_correction_gets_previous_sentence_as_context(self):
        self.type('Bonjour. Il a ete.')
        self.assertEqual(self.llm.corrections[-1][:2], ('Bonjour. ', 'Il a ete.'))

    def test_correction_requested_once_per_sentence(self):
        self.type('Il a ete.')
        self.type('Il a ete. ')
        self.assertEqual(len(self.llm.corrections), 1)

    def test_correction_applied(self):
        self.type('Il a ete. ')
        self.llm.corrections[0][2]('Il a été.')
        self.assertEqual(self.sink.calls[-2:], [('delete', -10, 10), ('commit', 'Il a été. ')])

    def test_correction_keeps_text_typed_meanwhile(self):
        self.type('Il a ete. ')
        self.type('Il a ete. Pu')
        self.llm.corrections[0][2]('Il a été.')
        self.assertEqual(self.sink.calls[-2:], [('delete', -12, 12), ('commit', 'Il a été. Pu')])

    def test_correction_aborted_when_text_moved(self):
        self.type('Il a ete. ')
        self.type('Il a et', char='\b')
        self.llm.corrections[0][2]('Il a été.')
        self.assertFalse(any(call[0] in ('delete', 'commit') for call in self.sink.calls))

    def test_unchanged_correction_does_nothing(self):
        self.type('Fine. ')
        self.llm.corrections[0][2]('Fine.')
        self.assertFalse(any(call[0] in ('delete', 'commit') for call in self.sink.calls))

    def test_heavy_rewrite_rejected(self):
        self.type('ok cool. ')
        self.llm.corrections[0][2]('That sounds wonderful to me.')
        self.assertFalse(any(call[0] in ('delete', 'commit') for call in self.sink.calls))

    def test_no_spellcheck_hint_disables_correction_only(self):
        self.c.on_content_type(0, NO_SPELLCHECK)
        self.type('Il a ete. ')
        self.assertEqual(self.llm.corrections, [])
        self.clock.advance(self.c.PAUSE_MS)
        self.assertEqual(len(self.llm.completions), 1)

    def apply_correction(self):
        self.type('Il a ete. ')
        self.llm.corrections[0][2]('Il a été.')
        self.c.on_surrounding('Il a été. ', 10, 10)

    def test_ctrl_z_after_correction_restores(self):
        self.apply_correction()
        self.assertTrue(self.c.on_key(None, True, Z))
        self.assertEqual(self.sink.calls[-2:], [('delete', -10, 10), ('commit', 'Il a ete. ')])
        self.c.on_surrounding('Il a ete. ', 10, 10)
        self.assertEqual(len(self.llm.corrections), 1)
        self.assertFalse(self.c.on_key(None, True, Z))

    def test_ctrl_z_on_a_non_latin_layout_restores(self):
        # Arabic layout: the Z key types ARABIC LETTER YEH WITH HAMZA ABOVE (keysym 0x5c6).
        self.apply_correction()
        self.assertTrue(self.c.on_key(None, True, 0x5c6, KEY_Z))
        self.assertEqual(self.sink.calls[-1], ('commit', 'Il a ete. '))

    def test_undone_sentence_with_text_after_is_not_corrected_again(self):
        self.type('Il a ete. ')
        self.type('Il a ete. Pu')
        self.llm.corrections[0][2]('Il a été.')
        self.c.on_surrounding('Il a été. Pu', 12, 12)
        self.assertTrue(self.c.on_key(None, True, Z))
        self.c.on_surrounding('Il a ete. Pu', 12, 12)
        for text in ('Il a ete. P', 'Il a ete. '):
            self.assertFalse(self.c.on_key(None, False, BACKSPACE))
            self.c.on_surrounding(text, len(text), len(text))
        self.assertEqual(len(self.llm.corrections), 1)

    def test_undone_sentence_is_not_corrected_again_elsewhere_in_the_field(self):
        self.apply_correction()
        self.assertTrue(self.c.on_key(None, True, Z))
        self.c.on_surrounding('Il a ete. ', 10, 10)
        self.type('Il a ete. Bonjour. ')
        self.type('Il a ete. Bonjour. Il a ete. ')
        self.assertEqual([c[1] for c in self.llm.corrections], ['Il a ete.', 'Bonjour.'])

    def test_undone_sentence_is_corrected_again_in_another_focus(self):
        self.apply_correction()
        self.assertTrue(self.c.on_key(None, True, Z))
        self.c.on_focus_out()
        self.type('Il a ete. ')
        self.assertEqual([c[1] for c in self.llm.corrections], ['Il a ete.', 'Il a ete.'])

    def test_answer_for_an_undone_sentence_is_not_applied(self):
        # The same sentence was asked twice before the person undid the first correction.
        self.type('Il a ete. ')
        self.type('Il a ete. Bonjour. Il a ete. ')
        self.llm.corrections[0][2]('Il a été.')
        self.c.on_surrounding('Il a été. Bonjour. Il a ete. ', 29, 29)
        self.assertTrue(self.c.on_key(None, True, Z))
        self.c.on_surrounding('Il a ete. Bonjour. Il a ete. ', 29, 29)
        calls = len(self.sink.calls)
        self.llm.corrections[-1][2]('Il a été.')
        self.assertEqual(self.sink.calls[calls:], [])

    def test_ctrl_z_after_correction_reported_in_two_steps(self):
        # An application reports the deletion and the insertion as two separate surrounding-text updates.
        self.type('Il a ete. ')
        self.llm.corrections[0][2]('Il a été.')
        self.c.on_surrounding('', 0, 0)
        self.c.on_surrounding('Il a été. ', 10, 10)
        self.assertTrue(self.c.on_key(None, True, Z))
        self.assertEqual(self.sink.calls[-2:], [('delete', -10, 10), ('commit', 'Il a ete. ')])

    def test_own_edit_does_not_start_a_completion(self):
        self.type('Il a ete. ')
        self.clock.advance(self.c.PAUSE_MS)  # the pause after typing asks once
        self.llm.corrections[0][2]('Il a été.')
        self.c.on_surrounding('', 0, 0)
        self.c.on_surrounding('Il a été. ', 10, 10)
        self.clock.advance(self.c.PAUSE_MS)
        self.assertEqual(len(self.llm.completions), 1)

    def test_external_edit_after_own_edit_drops_undo(self):
        self.apply_correction()
        self.c.on_surrounding('Autre chose', 11, 11)
        self.assertFalse(self.c.on_key(None, True, Z))

    def test_ctrl_z_typed_with_control_key_first(self):
        self.apply_correction()
        self.assertFalse(self.c.on_key(None, False, CONTROL_L))
        self.assertTrue(self.c.on_key(None, True, Z))

    def test_correction_waits_for_the_key_in_flight(self):
        # The application has the 'e' already but has not reported it when the answer lands.
        self.type('Il a ete. ')
        self.type('Il a ete. J')
        self.c.on_key('e', False, ord('e'))
        self.llm.corrections[0][2]('Il a été.')
        self.assertFalse(any(call[0] in ('delete', 'commit') for call in self.sink.calls))
        self.c.on_surrounding('Il a ete. Je', 12, 12)
        self.assertEqual(self.sink.calls[-2:], [('delete', -12, 12), ('commit', 'Il a été. Je')])

    def test_correction_dropped_after_focus_out(self):
        self.type('Il a ete. ')
        self.c.on_focus_out()
        self.llm.corrections[0][2]('Il a été.')
        self.assertFalse(any(call[0] in ('delete', 'commit') for call in self.sink.calls))

    def test_focus_out_cancels_corrections_in_flight(self):
        # llama-server serves one request at a time: a correction for a field left behind would hold up the next one.
        self.type('Il a ete. ')
        self.c.on_focus_out()
        self.assertTrue(self.llm.corrections[0][3].cancelled)

    def test_exclusion_cancels_corrections_and_asks_again_after(self):
        self.type('Il a ete. ')
        self.c.on_content_type(PASSWORD, 0)
        self.assertTrue(self.llm.corrections[0][3].cancelled)
        self.llm.corrections[0][2](None)   # what a cancelled request answers
        self.c.on_content_type(0, 0)
        self.type('Il a ete. J', 'J')
        self.type('Il a ete. ', ' ')
        self.assertEqual(len(self.llm.corrections), 2)

    def test_applied_correction_is_not_cancelled(self):
        self.type('Il a ete. ')
        self.llm.corrections[0][2]('Il a été.')
        self.c.on_focus_out()
        self.assertFalse(self.llm.corrections[0][3].cancelled)

    def test_second_correction_follows_a_first_that_changed_the_length(self):
        self.type('I has a car. ')
        self.type('I has a car. We was late. ')
        self.llm.corrections[0][2]('I have a car.')
        self.c.on_surrounding('I have a car. We was late. ', 27, 27)
        self.llm.corrections[1][2]('We were late.')
        self.assertEqual(self.sink.calls[-2:], [('delete', -13, 13), ('commit', 'We were late. ')])

    def test_second_correction_landing_before_the_first_is_reported(self):
        self.type('I has a car. ')
        self.type('I has a car. We was late. ')
        self.llm.corrections[0][2]('I have a car.')
        self.llm.corrections[1][2]('We were late.')
        self.assertEqual(self.sink.calls[-2:], [('delete', -26, 26), ('commit', 'I have a car. We was late. ')])
        self.c.on_surrounding('I have a car. We was late. ', 27, 27)
        self.assertEqual(self.sink.calls[-2:], [('delete', -13, 13), ('commit', 'We were late. ')])

    def test_answers_landing_during_a_key_in_flight_are_all_kept(self):
        self.type('I has a car. ')
        self.type('I has a car. We was late. ')
        self.c.on_key('S', False, ord('S'))
        self.llm.corrections[0][2]('I have a car.')
        self.llm.corrections[1][2]('We were late.')
        self.c.on_surrounding('I has a car. We was late. S', 27, 27)
        self.assertEqual(self.sink.calls[-2:], [('delete', -27, 27), ('commit', 'I have a car. We was late. S')])
        self.c.on_surrounding('I have a car. We was late. S', 28, 28)
        self.assertEqual(self.sink.calls[-2:], [('delete', -14, 14), ('commit', 'We were late. S')])

    def test_sentence_changed_while_read_is_asked_again(self):
        self.type('We was late. ')
        self.type('We was lat', char='\b')
        self.llm.corrections[0][2]('We were late.')
        self.type('We was late. ')
        self.assertEqual([c[1] for c in self.llm.corrections], ['We was late.', 'We was late.'])

    def test_focus_out_forgets_key_in_flight(self):
        # The first report of the newly focused field is not something the person just typed.
        self.c.on_key('a', False, ord('a'))
        self.c.on_focus_out()
        self.c.on_surrounding('Il a ete content.', 17, 17)
        self.clock.advance(self.c.PAUSE_MS)
        self.assertEqual((self.llm.corrections, self.llm.completions), ([], []))

    def test_ctrl_z_after_other_key_passes(self):
        self.apply_correction()
        self.type('Il a été. a')
        self.assertFalse(self.c.on_key(None, True, Z))

    # What counts as typing

    TEXT = 'Il a ete content. Elle est partie hier soir'

    def assert_nothing_asked(self):
        self.clock.advance(self.c.PAUSE_MS)
        self.assertEqual((self.llm.corrections, self.llm.completions), ([], []))

    def test_arrow_navigation_is_not_typing(self):
        self.c.on_surrounding(self.TEXT, 0, 0)
        for cursor in range(1, 20):
            self.assertFalse(self.c.on_key(None, False, RIGHT))
            self.c.on_surrounding(self.TEXT, cursor, cursor)
        self.assert_nothing_asked()

    def test_click_after_escape_without_suggestion_is_not_typing(self):
        # Escape changes nothing, so the application reports nothing: the click that follows is a move.
        self.c.on_surrounding(self.TEXT, len(self.TEXT), len(self.TEXT))
        self.assertFalse(self.c.on_key(None, False, ESCAPE))
        self.c.on_surrounding(self.TEXT, 18, 18)
        self.assert_nothing_asked()

    def test_shortcut_is_not_typing(self):
        self.c.on_surrounding(self.TEXT, 0, 17)
        self.assertFalse(self.c.on_key(None, True, ord('c')))
        self.c.on_surrounding(self.TEXT, 18, 18)
        self.assert_nothing_asked()

    def test_key_left_unreported_is_forgotten_at_the_next_key(self):
        self.c.on_surrounding(self.TEXT, 0, 0)
        self.c.on_key('a', False, ord('a'))   # the application took it and changed nothing
        self.c.on_key(None, False, RIGHT)
        self.c.on_surrounding(self.TEXT, 18, 18)
        self.assert_nothing_asked()

    def test_deletion_and_return_are_typing(self):
        self.c.on_surrounding('Hello word', 10, 10)
        self.c.on_key(None, False, BACKSPACE)
        self.c.on_surrounding('Hello wor', 9, 9)
        self.clock.advance(self.c.PAUSE_MS)
        self.assertEqual(self.llm.completions[-1][0], 'Hello wor')
        self.c.on_key('\r', False, RETURN)
        self.c.on_surrounding('Il a ete.\n', 10, 10)
        self.assertEqual(self.llm.corrections[-1][1], 'Il a ete.')

    def test_space_in_any_script_is_typing(self):
        self.type('東京に行った。 ', char=' ')
        self.clock.advance(self.c.PAUSE_MS)
        self.assertEqual(self.llm.completions[-1][0], '東京に行った。 ')

    def test_toggles_disable_features(self):
        self.c.completion_enabled = False
        self.c.correction_enabled = False
        self.type('Il a ete. ')
        self.clock.advance(self.c.PAUSE_MS)
        self.assertEqual((self.llm.completions, self.llm.corrections), ([], []))



class UndoKeyTest(unittest.TestCase):
    def test_the_key_that_types_z(self):
        self.assertTrue(is_undo_key(Z, 0))
        self.assertTrue(is_undo_key(ord('Z'), 0))
        self.assertTrue(is_undo_key(Z, 17))       # AZERTY: z sits where QWERTY has w

    def test_qwerty_position_only_when_the_key_types_no_latin_letter(self):
        self.assertTrue(is_undo_key(0x5c6, KEY_Z))   # Arabic
        self.assertTrue(is_undo_key(0x6d1, KEY_Z))   # Cyrillic ya
        self.assertFalse(is_undo_key(ord('w'), KEY_Z))   # AZERTY: the QWERTY Z position types w
        self.assertFalse(is_undo_key(ord('y'), KEY_Z))   # QWERTZ
        self.assertFalse(is_undo_key(0x5c6, 30))


if __name__ == '__main__':
    unittest.main()
