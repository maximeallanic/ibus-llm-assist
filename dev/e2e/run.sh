#!/usr/bin/env bash
# End-to-end run of the engine from this checkout, in a headless nested GNOME Shell: never the real session, and
# nothing is installed. Private runtime, D-Bus, dconf and configuration; the Shell starts its own ibus-daemon,
# which finds the engine through IBUS_COMPONENT_PATH. The input source is the scenario's layout with suggestions;
# GTK applications get the translucent suggestion style of docs/configuration.md.
#
#   dev/e2e/run.sh LANG OUT [--record] [--endpoint URL]      LANG: en, fr, de, ar (dev/e2e/scenarios.py)
#
# Needs gnome-shell, a language model server (default http://127.0.0.1:8033) and python3-gi with GTK 4. Run it
# alone (one nested Shell at a time) and, on a busy machine, in its own memory-capped unit:
#   systemd-run --user --scope -p MemoryHigh=4G -p MemoryMax=6G dev/e2e/run.sh en out/en
set -euo pipefail

LANG_CODE=${1:?language: en, fr, de or ar}
OUT=$(realpath -m "${2:?output folder}")
shift 2
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
HERE=$ROOT/dev/e2e
ENDPOINT=http://127.0.0.1:8033
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
    [ "${args[i]}" = --endpoint ] && ENDPOINT=${args[i + 1]}
done
LAYOUT=$(python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); from scenarios import SCENARIOS
print(SCENARIOS[sys.argv[2]].layout)' "$HERE" "$LANG_CODE")
case "$LANG_CODE" in en) LOCALE=en_US.UTF-8 ;; fr) LOCALE=fr_FR.UTF-8 ;; de) LOCALE=de_DE.UTF-8 ;; ar) LOCALE=ar_EG.UTF-8 ;; esac

mkdir -p "$OUT"
RUN=$(mktemp -d "${XDG_RUNTIME_DIR:?}/ibus-llm-assist-e2e.XXXXXX")
# The nested xdg-document-portal leaves with its bus, a moment after the session: wait for it to unmount
# runtime/doc, and unmount it only if it is stuck.
cleanup() {
    for _ in $(seq 50); do
        mountpoint -q "$RUN/runtime/doc" || break
        sleep 0.1
    done
    if mountpoint -q "$RUN/runtime/doc"; then fusermount3 -u "$RUN/runtime/doc"; fi
    rm -rf -- "$RUN"
}
trap cleanup EXIT
mkdir -p "$RUN/config/dconf" "$RUN/config/gtk-4.0" "$RUN/keys" "$RUN/runtime" "$RUN/cache" "$RUN/component" \
    "$RUN/schemas" "$RUN/locale"

# The engine, its schema and its translations, from the checkout. IBus's own components (its dconf config, without
# which ibus-daemon exits) stay on the path, after ours.
IBUS_COMPONENTS=$(dirname "$(dirname "$(command -v ibus-daemon)")")/share/ibus/component
sed -e "s|@LIBEXECDIR@|$ROOT/bin|g" -e "s|@VERSION@|e2e|g" "$ROOT/data/ibus-llm-assist.xml.in" \
    >"$RUN/component/ibus-llm-assist.xml"
cp "$ROOT/data/io.github.maximeallanic.IBusLlmAssist.gschema.xml" "$RUN/schemas/"
glib-compile-schemas "$RUN/schemas"
for po in "$ROOT"/po/*.po; do
    mkdir -p "$RUN/locale/$(basename "$po" .po)/LC_MESSAGES"
    msgfmt -o "$RUN/locale/$(basename "$po" .po)/LC_MESSAGES/ibus-llm-assist.mo" "$po"
done
cat >"$RUN/config/gtk-4.0/gtk.css" <<'CSS'
text > preedit.prediction, textview > preedit.prediction { color: alpha(currentColor, 0.5); font-style: normal; }
CSS

# A fresh dconf database: defaults everywhere, the scenario's input source, no extensions, no search providers
# (which would start the indexer).
cat >"$RUN/keys/10-e2e" <<KEYS
[org/gnome/desktop/input-sources]
sources=[('ibus', 'llm-assist:$LAYOUT')]
[org/gnome/shell]
disable-user-extensions=true
welcome-dialog-last-shown-version='999'
[org/gnome/desktop/search-providers]
disable-external=true
[io/github/maximeallanic/IBusLlmAssist]
endpoint='$ENDPOINT'
KEYS
dconf compile "$RUN/config/dconf/user" "$RUN/keys"

# shellcheck disable=SC2016  # the inner bash expands its own arguments
env -u WAYLAND_DISPLAY -u DISPLAY -u IBUS_ADDRESS -u GTK_IM_MODULE -u QT_IM_MODULE -u LANGUAGE \
    LANG="$LOCALE" LC_ALL="$LOCALE" \
    XDG_RUNTIME_DIR="$RUN/runtime" XDG_CONFIG_HOME="$RUN/config" XDG_CACHE_HOME="$RUN/cache" \
    IBUS_COMPONENT_PATH="$RUN/component:$IBUS_COMPONENTS" GSETTINGS_SCHEMA_DIR="$RUN/schemas" \
    IBUS_LLM_ASSIST_LOCALEDIR="$RUN/locale" \
    dbus-run-session -- bash -c '
        gnome-shell --headless --no-x11 --virtual-monitor 1920x1080 --unsafe-mode --wayland-display e2e \
            > "$1/shell.log" 2>&1 &
        shell=$!
        WAYLAND_DISPLAY=e2e python3 "$2/driver.py" "${@:3}" "$1"
        status=$?
        echo "driver.py exit $status" >&2
        kill "$shell"; wait "$shell" 2>/dev/null
        exit "$status"' _ "$OUT" "$HERE" "$LANG_CODE" "$@"
