# Installation

## One line

From a terminal of your GNOME session, as yourself:

```sh
curl -fsSL https://raw.githubusercontent.com/maximeallanic/ibus-llm-assist/main/install.sh | bash
```

`install.sh` notices it has no checkout next to it, downloads the release it pins (`v0.1.0`) over HTTPS, checks it
against the sha256 written in `install.sh` before unpacking anything, unpacks it into
`~/.cache/ibus-llm-assist/source-v0.1.0`, and runs the installer from there. A mismatch stops it with nothing
installed; an `install.sh` that pins no release yet refuses and tells you to use a clone. Options go after `bash -s --`:

```sh
curl -fsSL https://raw.githubusercontent.com/maximeallanic/ibus-llm-assist/main/install.sh | bash -s -- --no-server
```

The tarball and its sha256 are also on the release page; `scripts/release.sh` writes that sha256 into `install.sh`.

## From a clone

```sh
git clone https://github.com/maximeallanic/ibus-llm-assist.git
cd ibus-llm-assist
./install.sh            # --help for the options, --dry-run to see what it would do
```

## What the installer does

Every step says what it is about to do and asks first (`-y` answers yes to everything).

| Step | What | Where | Root |
|---|---|---|---|
| 1. System packages | IBus, PyGObject, the IBus and libsoup 3 typelibs, GLib tools, Pango, gettext, curl | your package manager | sudo, after asking |
| 2. Engine | the program, its IBus component, its settings schema, its translations, a manifest with the sha256 of each file | `/usr/local` (`--prefix`), `/usr/share/ibus/component`, `/usr/share/glib-2.0/schemas` | sudo |
| 3. Local server (optional) | llama.cpp b11714 (Vulkan build) and Gemma 4 E2B q4_0 (3.4 GB), both checked by sha256; a systemd user unit | `~/.local/share/ibus-llm-assist`, `~/.config/systemd/user/ibus-llm-assist-server.service` | no |
| 4. Your layouts | replaces each keyboard layout of your input sources by the same layout with suggestions | GNOME input sources | no |
| 5. Check | `ibus-llm-assist status` | | no |

The component and the schema go under `/usr/share` because IBus reads components only from there, and because a
compiled schema under `/usr/local` would hide the system's schemas from programs that look in a single place.

Step 3 is skipped when a server already answers on the port (`--port`, default 8033): it is then used as is. If the
port is taken by something else, the installer says so and leaves it. With `--endpoint URL` the installer sets up no
server and points the engine at yours.

### Distributions

| Family | Packages | Tested |
|---|---|---|
| Debian, Ubuntu | `apt-get` | desktop install on Debian testing (forky) with GNOME 51; Ubuntu untested |
| Fedora | `dnf` | packages and staged install checked in a clean `fedora:latest` container (CI); no desktop test |
| Arch, Manjaro | `pacman` | packages and staged install checked in a clean `archlinux:latest` container (CI); no desktop test |
| openSUSE | `zypper` | names unverified; the installer says so |
| Others | none | the installer lists what is missing and stops |

The engine needs IBus 1.5 with GObject introspection, which every one of them ships. The
[patches](patches.md) are separate and optional.

### Options

```
--dry-run              print what would be done, change nothing
-y, --yes              answer yes to every question
--no-deps              do not install missing system packages
--no-server            do not set up the local language model server
--port N               port of the local server (default 8033)
--endpoint URL         use this server instead (implies --no-server)
--server-api API       llama.cpp (default) or openai
--model NAME           model name to send to the server
--no-enable            install only; turn it on later with "ibus-llm-assist enable"
--prefix DIR           where the program goes (default /usr/local)
--destroot DIR         stage the system files under DIR (packaging, tests); nothing else is done
--uninstall            same as ./uninstall.sh
```

## Turning it on and off

The installer turns it on. Later:

```sh
ibus-llm-assist enable                 # every layout of your input sources
ibus-llm-assist enable --layout fr     # only this one
ibus-llm-assist disable                # your plain layouts back
ibus-llm-assist status                 # what works, what does not, and why
```

In Settings > Keyboard, the engine shows as "*Layout*, with suggestions". Without GNOME, add it with `ibus-setup`
(Input Method tab).

Layouts with a variant (`us+intl`, `fr+bepo`…) are skipped on a GNOME Shell that would type them with the plain layout;
see [patches.md](patches.md).

## Uninstall

```sh
./uninstall.sh            # from a clone or ~/.cache/ibus-llm-assist/source-v0.1.0
curl -fsSL https://raw.githubusercontent.com/maximeallanic/ibus-llm-assist/main/install.sh | bash -s -- --uninstall
```

It puts your plain layouts back, removes exactly the files listed in the manifest (sudo), stops and removes the server
unit, and keeps the model unless you pass `--purge` (which also resets the engine's settings). `--keep-server` leaves
the server running for other uses.

## Check

```sh
./verify.sh               # installed files unchanged, then ibus-llm-assist status
./verify.sh --tests       # and the unit tests of this checkout
```
