"""The engine's logic, free of IBus and GLib: which keys to take, when to ask the model, what to show or replace.

The application owns the text. The controller only watches keys and the surrounding text the application reports,
shows a suggestion as pre-edit text after the cursor, and replaces a finished sentence by its correction.
"""
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from .boundaries import at_word_boundary, ends_sentence, sentence_start_before
from .completion import Suggestion
from .correction import LastCorrection, is_light_edit

TAB, ESCAPE, Z = 0xff09, 0xff1b, 0x7a
# Linux input code of the key in the Z position of a QWERTY keyboard (IBus passes these codes, keycode - 8 of X11).
KEY_Z = 44

# Keys that only modify others (X11 keysymdef.h): Shift_L to Hyper_R, the ISO lock and level group, Mode_switch and
# Num_Lock. The Shell forwards their presses too; they neither type nor dismiss anything.
_MODIFIER_KEYSYMS = frozenset(range(0xffe1, 0xffef)) | frozenset(range(0xfe01, 0xfe10)) | {0xff7e, 0xff7f}

# Keys that edit the text whatever modifier goes with them: BackSpace, Delete, KP_Delete, Return and KP_Enter.
_EDIT_KEYSYMS = frozenset({0xff08, 0xffff, 0xff9f, 0xff0d, 0xff8d})

# IBus.InputPurpose and IBus.InputHints values (IBus 1.5.35 typelib).
_PASSWORD, _PIN, _TERMINAL = 8, 9, 10
_NO_SPELLCHECK, _PRIVATE, _HIDDEN_TEXT = 2, 2048, 4096



def is_undo_key(keysym: int, keycode: int) -> bool:
    """Whether Ctrl with this key means undo: the key that types z, or, on a layout whose key there types no Latin
    letter (Arabic, Cyrillic, Greek, Hebrew…), the key in the QWERTY Z position, as browsers and GTK match shortcuts."""
    if keysym in (Z, Z - 0x20):
        return True
    latin_letter = 0x41 <= keysym <= 0x5a or 0x61 <= keysym <= 0x7a
    return not latin_letter and keycode == KEY_Z


# Sentences before the current one given to the model as context for a completion.
_CONTEXT_SENTENCES = 3


class Cancellable(Protocol):
    def cancel(self) -> None: ...


class Sink(Protocol):
    def show_prediction(self, text: str) -> None: ...
    def clear_preedit(self) -> None: ...
    def commit(self, text: str) -> None: ...
    def delete_surrounding(self, offset: int, n_chars: int) -> None: ...


@dataclass(eq=False)
class _Request:
    """A sentence sent for correction. start follows the engine's own replacements made while the answer is awaited."""
    focus: int
    start: int
    sentence: str
    cancellable: Cancellable | None = None   # cancels the request while the model has not answered


class Controller:
    PAUSE_MS = 400

    def __init__(self, sink: Sink, llm, schedule: Callable[[int, Callable[[], None]], int],
                 unschedule: Callable[[int], None]) -> None:
        self.completion_enabled = True
        self.correction_enabled = True
        self._sink, self._llm = sink, llm
        self._schedule, self._unschedule = schedule, unschedule
        self._active = False          # the client reports surrounding text
        self._excluded = False        # password, PIN, terminal, private or hidden field
        self._no_spellcheck = False
        self._text, self._cursor, self._anchor = '', 0, 0
        self._typed = False           # the last key edited the text: it explains the next surrounding change
        # The engine's own replacement, as (text before the cursor once deleted, once inserted, text after it): the
        # application may report the deletion and the insertion as one surrounding change or as two.
        self._own: tuple[str, str, str] | None = None
        self._focus = 0               # bumped by every focus change; corrections of an older focus are dropped
        self._requests: list[_Request] = []   # corrections asked and not yet applied or dropped
        self._deferred: list[tuple[_Request, str]] = []   # answers that landed while a key was in flight
        self._suggestion = Suggestion()
        self._timer: int | None = None
        self._pending = None          # cancellable of the completion request in flight
        self._generation = 0          # bumped by every key; answers of older generations are stale
        self._checked: tuple[int, str] | None = None   # last sentence sent for correction (start, text)
        self._rejected: set[str] = set()   # sentences whose correction was undone in this focus
        self._last: LastCorrection | None = None

    # Inputs from the engine

    def on_capabilities(self, has_surrounding: bool) -> None:
        self._active = has_surrounding
        if not has_surrounding:
            self._reset()

    def on_content_type(self, purpose: int, hints: int) -> None:
        self._excluded = purpose in (_PASSWORD, _PIN, _TERMINAL) or bool(hints & (_PRIVATE | _HIDDEN_TEXT))
        self._no_spellcheck = bool(hints & _NO_SPELLCHECK)
        if self._excluded:
            self._reset()

    def on_focus_out(self) -> None:
        self._reset()
        self._checked = None
        self._rejected = set()
        # What follows comes from another field: nothing in flight, nothing known of its text.
        self._focus += 1
        self._typed, self._own = False, None
        self._deferred = []
        self._text, self._cursor, self._anchor = '', 0, 0

    def on_key(self, char: str | None, ctrl: bool, keysym: int, keycode: int = 0) -> bool:
        """A key press; True when the engine takes it, False when it goes on to the application.

        char is the text the key types, None when it types none or goes with a command modifier (Alt, Super);
        keycode is the Linux input code of the physical key (0 when unknown).
        """
        if keysym in _MODIFIER_KEYSYMS or not self._active or self._excluded:
            return False
        self._cancel_completion()
        # Only a key that edits explains the next report; arrows, Escape or a shortcut leave the text as it was, and a
        # report that follows them (or a click after them) is a move. Each key replaces the verdict of the one before,
        # so a key the application answered with no report is forgotten at the next one.
        self._typed = keysym in _EDIT_KEYSYMS or bool(char) and not ctrl and (char.isprintable() or char == '\t')
        last, self._last = self._last, None
        if ctrl and last and is_undo_key(keysym, keycode):
            self._typed = False   # the engine's own edit, recognised by self._own
            self._undo(last)
            return True
        if not self._suggestion.text:
            return False
        if ctrl and keysym == TAB:
            self._typed = True
            self._sink.clear_preedit()
            self._sink.commit(self._suggestion.take())
            return True
        if keysym == ESCAPE:
            self._clear_suggestion()
            return True
        if char and not ctrl and self._suggestion.consume(char) and self._suggestion.text:
            self._sink.show_prediction(self._suggestion.text)
            return False
        # Typed something else, or the last character of the suggestion: the pre-edit goes, the key goes on.
        self._suggestion.clear()
        self._sink.clear_preedit()
        return False

    def on_surrounding(self, text: str, cursor: int, anchor: int) -> None:
        self._on_report(text, cursor, anchor)
        # Applying one answer makes an edit of the engine's own; the next waits until the application reports it.
        while self._deferred and not self._typed and not self._own:
            self._apply(*self._deferred.pop(0))

    def _on_report(self, text: str, cursor: int, anchor: int) -> None:
        moved = (text, cursor, anchor) != (self._text, self._cursor, self._anchor)
        self._text, self._cursor, self._anchor = text, cursor, anchor
        typed, self._typed = self._typed, False
        if not moved:
            return
        if self._own:
            deleted, inserted, after = self._own
            if text[cursor:] == after and text[:cursor] in (deleted, inserted):
                if text[:cursor] == inserted:
                    self._own = None
                return
            self._own = None
        if not typed:
            # Click, selection or edit by the application itself: whatever was offered no longer fits.
            self._cancel_completion()
            self._clear_suggestion()
            self._last = None
            return
        if self._last and not text[:cursor].endswith(self._last.corrected):
            self._last = None
        if not self._active or self._excluded or cursor != anchor:
            return
        self._maybe_correct()
        if self.completion_enabled and not self._suggestion.text:
            self._timer = self._schedule(self.PAUSE_MS, self._on_pause)

    # Completion

    def _on_pause(self) -> bool:
        self._timer = None
        text, cursor = self._text, self._cursor
        before = text[:cursor]
        if not before.strip() or not at_word_boundary(text, cursor) or cursor != self._anchor:
            return False
        start = cursor
        for _ in range(_CONTEXT_SENTENCES + 1):
            start = sentence_start_before(text, start) if start else 0
        generation = self._generation

        def done(answer: str | None) -> None:
            if generation != self._generation or not answer or not answer.strip():
                return
            self._pending = None
            self._suggestion.show(answer)
            self._sink.show_prediction(answer)

        self._pending = self._llm.complete(text[start:cursor], done)
        return False

    def _cancel_completion(self) -> None:
        self._generation += 1
        if self._timer is not None:
            self._unschedule(self._timer)
            self._timer = None
        if self._pending is not None:
            self._pending.cancel()
            self._pending = None

    def _clear_suggestion(self) -> None:
        if self._suggestion.text:
            self._suggestion.clear()
            self._sink.clear_preedit()

    # Correction

    def _maybe_correct(self) -> None:
        if not self.correction_enabled or self._no_spellcheck:
            return
        text, cursor = self._text, self._cursor
        if not ends_sentence(text, cursor):
            return
        start = sentence_start_before(text, cursor)
        sentence = text[start:cursor].rstrip()
        if not sentence or sentence in self._rejected or self._checked == (start, sentence):
            return
        self._checked = (start, sentence)
        context = text[sentence_start_before(text, start):start] if start else ''
        request = _Request(self._focus, start, sentence)
        self._requests.append(request)
        request.cancellable = self._llm.correct(context, sentence, lambda answer: self._apply(request, answer))

    def _apply(self, request: _Request, answer: str | None) -> None:
        if not answer or request.focus != self._focus or not self._active or self._excluded:
            self._forget(request)
            return
        if self._typed or self._own:
            # The application holds text it has not reported yet: offsets known here would miss it.
            self._deferred.append((request, answer))
            return
        self._forget(request)
        text, cursor = self._text, self._cursor
        start, sentence = request.start, request.sentence
        corrected = answer.strip()
        end = start + len(sentence)
        if text[start:end] != sentence or cursor < end or cursor != self._anchor:
            # The sentence changed while the model read it: once the cursor ends it again, it is asked again.
            if self._checked == (start, sentence):
                self._checked = None
            return
        if corrected == sentence or sentence in self._rejected or not is_light_edit(sentence, corrected):
            return
        rest = text[end:cursor]
        self._clear_suggestion()
        self._replace_before_cursor(cursor - start, corrected + rest)
        self._shift_after(start, len(corrected) - len(sentence))
        if self._checked == (start, sentence):
            self._checked = (start, corrected)
        self._last = LastCorrection(sentence=sentence, original=sentence + rest, corrected=corrected + rest)

    def _undo(self, last: LastCorrection) -> None:
        self._clear_suggestion()
        self._replace_before_cursor(len(last.corrected), last.original)
        start = self._cursor - len(last.corrected)
        self._shift_after(start, len(last.original) - len(last.corrected))
        # The person refused this correction: the sentence is not asked again while the field keeps the focus, wherever
        # it reappears (the text typed after it erased, the same sentence typed again further on).
        self._rejected.add(last.sentence)

    def _cancel_corrections(self) -> None:
        """Stop the corrections the model still reads: a local server often serves one request at a time."""
        for request in self._requests:
            if request.cancellable is not None:
                request.cancellable.cancel()
            if self._checked == (request.start, request.sentence):
                self._checked = None   # never answered: asked again if the field takes it back as it is
        self._requests = []

    def _forget(self, request: _Request) -> None:
        if request in self._requests:
            self._requests.remove(request)

    def _shift_after(self, start: int, delta: int) -> None:
        """The engine replaced text from start on: sentences still awaiting a correction after it move by delta."""
        for request in self._requests:
            if request.start > start:
                request.start += delta
        if self._checked and self._checked[0] > start:
            self._checked = (self._checked[0] + delta, self._checked[1])

    def _replace_before_cursor(self, n_chars: int, text: str) -> None:
        deleted = self._text[:self._cursor - n_chars]
        self._own = (deleted, deleted + text, self._text[self._cursor:])
        self._sink.delete_surrounding(-n_chars, n_chars)
        self._sink.commit(text)

    def _reset(self) -> None:
        self._cancel_completion()
        self._cancel_corrections()
        self._clear_suggestion()
        self._last = None
