# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.1] - 2026-10-20

First published release: 0.1.0 was tagged but never released, because its engine failed on IBus older than 1.5.33
(Ubuntu 24.04 among others) and CI stopped the release.

### Added

- IBus engine that suggests the rest of the sentence after a pause (Ctrl+Tab accepts, Escape dismisses) and corrects
  each finished sentence in place (Ctrl+Z restores it), with a language model server.
- One engine per keyboard layout of the person, keeping its keys, dead keys and Compose sequences;
  `ibus-llm-assist enable`, `disable` and `status`.
- Language-neutral text handling: sentence and word boundaries from Pango, a rephrasing guard counted in graphemes,
  a correction token budget derived from the UTF-8 length, prompts that name no language. Ctrl+Z also works by key
  position on layouts whose letters are not Latin.
- Suggestions and Corrections switches in the keyboard menu; GSettings schema
  `io.github.maximeallanic.IBusLlmAssist` (pause, endpoint, server kind, model); optional API key file.
- llama.cpp native mode (default) and an experimental OpenAI-compatible mode.
- Installer with a one-line bootstrap (pinned release, sha256 checked), package installation for Debian/Ubuntu,
  Fedora, Arch and openSUSE, a manifest of installed files, and an optional local server: llama.cpp b11714 and
  Gemma 4 E2B q4_0, pinned and checked by sha256, as a systemd user unit on 127.0.0.1. `uninstall.sh` and `verify.sh`.
- English and French messages.
- Optional GNOME Shell 51 and GTK 4.24 patches for layouts with a variant and translucent suggestions in GtkTextView.
- End-to-end run in a nested GNOME Shell, model bench in four languages, CI.

### Fixed (since the 0.1.0 tag)

- The engine runs on IBus 1.5.26 and later. It used `IBus.AttrType.HINT`, which IBus added in 1.5.33, and raised an
  error at every suggestion on older versions, so none showed. There it now marks the suggestion with the grey colour
  that stood for a prediction before 1.5.33. Ghost text needs IBus 1.5.33 and GNOME Shell 51; with older versions the
  suggestion is ordinary underlined pre-edit text (docs/compatibility.md).
- The Suggestions and Corrections switches of the keyboard menu were sent with no icon, an invalid D-Bus message on
  Ubuntu 24.04.
- The documentation claimed "IBus 1.5"; it now gives the tested minimum and the look per IBus and GNOME version.

## [0.1.0] - 2026-10-20

Tagged, not released (see 0.1.1).

[Unreleased]: https://github.com/maximeallanic/ibus-llm-assist/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/maximeallanic/ibus-llm-assist/releases/tag/v0.1.1
[0.1.0]: https://github.com/maximeallanic/ibus-llm-assist/tree/v0.1.0
