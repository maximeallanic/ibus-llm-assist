# How it works

```
 application ──text-input-v3──> GNOME Shell ──> ibus-daemon ──> ibus-engine-llm-assist ──HTTP──> llama-server
 (GTK, Qt, Chrome)                (keymap)                       (Python, PyGObject)            (127.0.0.1:8033)
```

## One engine per layout

IBus runs one engine at a time, and the desktop applies the keyboard layout the engine declares. So the engine
declares one IBus engine per layout you type with, named after its XKB id (`llm-assist:fr`, `llm-assist:us+intl`),
and `ibus-llm-assist enable` puts each of them in place of the plain layout in your input sources. The list comes from
the program itself (`ibus-engine-llm-assist --xml`, run by ibus-daemon when it builds its registry), from your GNOME
input sources, or from the system keyboard (systemd-localed) elsewhere; names come from xkeyboard-config's registry
and its translations.

The engine only watches keys. What it does not take goes to IBus's own key handling, which composes dead keys and
Compose sequences exactly as IBus's xkb engines do. It takes Ctrl+Tab and Escape only while a suggestion is shown, and
Ctrl+Z only right after a correction.

`llm_assist/controller.py` holds the logic, free of IBus and GLib so that it is tested on its own;
`llm_assist/engine.py` binds it to IBus.

## Suggestions

1. Each key that types something restarts a timer (`pause-ms`, 400 ms).
2. When it fires, if the cursor is at a word boundary and nothing is selected, the engine sends the text before the
   cursor, from up to three sentences back, to the server. A sentence and a word boundary are what Pango says they
   are (Unicode text segmentation, UAX #29 and the line-breaking rules), so they hold in any script.
3. With llama-server, the request goes through the model's own chat template (`/apply-template`): an instruction to
   finish the current sentence in the language of the text, the text as the user message, and the same text again as
   the start of the model's answer, which `/completion` then continues. Asking a chat question instead makes the
   model *answer* the text ("Thank you so much for" → "You're welcome"); sending the raw text alone makes it change
   language on short beginnings. Both were measured and dropped.
4. The answer is at most 16 tokens, cut at the end of the sentence and, when the token limit cut it, back to the last
   word end. It shows as pre-edit text with the "prediction" hint after the cursor.
5. Typing the same characters shortens it; anything else, a click or a move dismisses it; Ctrl+Tab commits it.

A new key cancels a request still in flight: a local server serves one request at a time, so stale requests would
only delay the next suggestion.

## Corrections

1. When a typed character ends a sentence (Pango's sentence boundary), the sentence is sent to `/v1/chat/completions`
   with the sentence before it as context, and an instruction to fix spelling, grammar, agreement, punctuation and
   accents in the language of the text, changing as little as possible.
2. The answer replaces the sentence only if the sentence is still there, unchanged, before the cursor, and if the
   correction changes at most 30 % of its graphemes (Levenshtein distance over user-perceived characters, so that an
   accented letter, a kana or an Arabic letter each count once). Above that, the model rephrased: the answer is
   dropped. Real corrections change at most 17 % in the bench ([benchmarks](benchmarks.md)).
3. The token budget of the answer is derived from the sentence's length in UTF-8 bytes, so that a long sentence in a
   script that takes several tokens per character is not cut.
4. Ctrl+Z right after puts the sentence back as typed, and that sentence is not corrected again while the field keeps
   the focus.

## Where it does nothing

Fields whose input purpose is password, PIN or terminal, and fields with the "private" or "hidden text" hints. The
engine can also skip corrections in fields marked "no spellcheck", but GNOME Shell 51 does not pass that hint to IBus.

## Settings and translations

GSettings schema `io.github.maximeallanic.IBusLlmAssist`; the engine follows every change at once. User-facing text
goes through gettext (domain `ibus-llm-assist`, catalogues in `po/`); the layout names through xkeyboard-config's
own catalogue.

## Files

| Path | What |
|---|---|
| `llm_assist/` | the engine (`engine.py`, `controller.py`, `completion.py`, `correction.py`, `boundaries.py`, `llm.py`), the layouts (`layouts.py`, `sources.py`), the CLI and its checks (`cli.py`, `doctor.py`, `shellcode.py`) |
| `bin/` | launchers: `ibus-engine-llm-assist` (run by IBus), `ibus-llm-assist` (CLI) |
| `data/` | IBus component, GSettings schema, systemd unit of the local server |
| `lib/` | installer modules: packages, system files and manifest, local server |
| `po/` | translations |
| `patches/` | optional GNOME Shell and GTK patches |
| `dev/` | the end-to-end run in a nested GNOME Shell, and the model bench |
