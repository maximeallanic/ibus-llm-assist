# Contributing

Thanks for helping.

## Ways to contribute

- **Report a bug** with the issue form: version, distribution, GNOME version, the application you typed in, the output
  of `ibus-llm-assist status`. Never paste private text you typed: reproduce with made-up text.
- **Try it on another setup** (Fedora, Arch, another GNOME version, another application, another server) and say what
  you saw, working or not.
- **Translate**: a new `po/<lang>.po` (see [docs/development.md](docs/development.md#translations)).
- **Report how it does in your language**: add cases to `dev/bench/cases.py` and share the bench output.
- **Fix something or add a feature**, as described below.

## How to contribute code

1. **Discuss first** for anything beyond a small fix: open an issue or a Discussion with the problem and the approach.
2. **Fork** and branch from `main` (`fix/short-description`, `feat/…`, `docs/…`).
3. **Keep the change focused**: one subject per pull request.
4. **Run `tests/run.sh`** and add or update tests for the behaviour you changed. For a change in what reaches the
   application, run `dev/e2e/run.sh` too.
5. **Commit with [Conventional Commits](https://www.conventionalcommits.org/)** in English
   (`fix(controller): keep the suggestion after a dead key`). The pull request title follows the same format.
6. **Open the pull request** against `main` and fill in the template.

By contributing you agree that your work is released under the repository licence (MIT). You are responsible for what
you submit, including anything produced with the help of a tool: read it, run it, and be able to explain it.

## Ground rules

- **English in the code**: identifiers, comments, commit messages, logs. User-facing strings go through gettext.
- **No language hard-coded between the model and the person.** No word lists, no regular expressions over natural
  language, no thresholds in characters of one script, no prompt that only one language can satisfy. Text boundaries
  come from Pango; lengths are graphemes or bytes. A change that only works in the languages you tested is a bug.
- **Nothing typed leaves the configured server**, nothing typed is logged or written to disk.
- **No source file over 500 lines**: split along a real seam.
- **Fix causes, not symptoms**: no swallowed errors, no retry that hides a failure, no special case for one test.
- **Pinned downloads**: a new llama.cpp or model pin comes with its sha256, and updates `CHANGELOG.md` and
  `NOTICE.md`.

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
