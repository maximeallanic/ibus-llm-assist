# Development

## Layout

See [how-it-works.md](how-it-works.md#files). The engine is plain Python 3.10+ with PyGObject; no build step.

## Tests

```sh
tests/run.sh
```

runs everything CI runs: the unit tests, ShellCheck, the 500-line limit per source file, and the installer round trip
(`tests/installer.sh`: install into a staging root, reinstall, uninstall, then the one-line bootstrap: refused without a
pinned release, a local archive that matches the pin, a tampered archive and a non-HTTPS URL refused). None of it needs root or touches your session.

`tests/distro.sh debian|fedora|arch`, run as root in a clean container, lets the installer install its own packages,
then runs the unit tests against them (CI runs it on `debian:testing`, `fedora:latest` and `archlinux:latest`):

```sh
docker run --rm -v "$PWD":/repo:ro fedora:latest /repo/tests/distro.sh fedora
```

The unit tests alone: `python3 -m unittest discover -s tests -t .` They need `python3-gi`, the IBus and libsoup 3
typelibs, Pango, and gettext for the translation tests. `tests/test_engine_contract.py` runs a real IBus engine on a
private D-Bus.

## End to end, in a nested GNOME Shell

```sh
dev/e2e/run.sh en out/en            # or fr, de, ar: dev/e2e/scenarios.py
dev/e2e/run.sh en out/en --record   # also frames for a GIF
dev/e2e/make-media.sh out/en screenshots en
```

`run.sh` starts a headless GNOME Shell with its own runtime directory, D-Bus, dconf database and configuration, an
input source with the engine for the scenario's layout, and the engine straight from the checkout (through
`IBUS_COMPONENT_PATH`); nothing is installed and your session is untouched. It opens a GTK 4 window, types through a
virtual keyboard of the nested Shell, accepts a suggestion, types a sentence with a mistake, undoes the correction,
types dead keys where the layout has them, opens the keyboard menu, and checks the text the window received. It needs
`gnome-shell`, GTK 4 and a model server (default `http://127.0.0.1:8033`, `--endpoint` otherwise). Run one at a time; on
a busy machine, inside `systemd-run --user --scope -p MemoryHigh=4G -p MemoryMax=6G`.

The screenshots in `screenshots/` come from it ([screenshots/README.md](../screenshots/README.md)).

## Model bench

`dev/bench/run.py`, see [benchmarks.md](benchmarks.md).

## Translations

User-facing strings go through gettext: `_()` in Python, `t` and `tf` in the shell scripts. After changing one:

```sh
po/update.sh        # regenerates po/ibus-llm-assist.pot and merges it into each po/<lang>.po
```

`tests/test_i18n.py` fails while the template is out of date or a catalogue misses a string or a placeholder. A new
language: `msginit -i po/ibus-llm-assist.pot -l <lang> -o po/<lang>.po`, translate, add `<lang>` to `po/LINGUAS`.

## Releases

1. Set the version everywhere `tests/test_version.py` checks, and give `CHANGELOG.md` its `## [X.Y.Z] - date` section.
2. `scripts/release.sh X.Y.Z` builds the reproducible tarball, writes its sha256 into `install.sh` and commits
   `chore(release): X.Y.Z`.
3. Tag `vX.Y.Z` and push it. `.github/workflows/release.yml` runs the tests, rebuilds the tarball with
   `scripts/release.sh --build-only`, fails if it does not match the pin, and publishes it with its sha256.

## Rules

- Code, comments, logs in English.
- No language, script or locale hard-coded between the model and the person: no word lists, no regular expressions
  over natural language, no length thresholds counted in characters of one script. Text boundaries come from Pango,
  lengths are graphemes or bytes.
- No source file over 500 lines.
- Fix the cause; no swallowed errors.
