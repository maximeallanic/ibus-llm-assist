#!/usr/bin/env bash
# ibus-llm-assist uninstaller: puts your plain keyboard layouts back, removes the engine (sudo) and the local server.
# Run it as yourself, in your desktop session.
set -euo pipefail

IBLA_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib/common.sh
. "$IBLA_ROOT/lib/common.sh"
# shellcheck source=lib/system.sh
. "$IBLA_ROOT/lib/system.sh"
# shellcheck source=lib/server.sh
. "$IBLA_ROOT/lib/server.sh"

PURGE=0
KEEP_SERVER=0
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        -y | --yes) ASSUME_YES=1 ;;
        --purge) PURGE=1 ;;
        --keep-server) KEEP_SERVER=1 ;;
        --prefix) PREFIX=${2:?}; shift ;;
        --destroot) DESTROOT=$(realpath -m "${2:?}"); shift ;;
        -h | --help)
            printf "%s\n" "$(t 'Usage: uninstall.sh [--dry-run] [-y] [--purge] [--keep-server] [--prefix DIR] [--destroot DIR]')"
            printf "%s\n" "$(t '--purge also deletes the downloaded model, llama.cpp and your settings of the engine.')"
            exit 0 ;;
        *) die "$(tf 'Unknown option: %s' "$1")" ;;
    esac
    shift
done
[ -n "$DESTROOT" ] || [ "$(id -u)" != 0 ] || die "$(t 'Run the uninstaller as yourself, not as root: it asks for sudo when it needs it.')"
compile_catalogues "$IBLA_ROOT/build/locale"

if [ -z "$DESTROOT" ]; then
    step "$(t 'Your keyboard layouts')"
    if [ -x "$PREFIX/bin/ibus-llm-assist" ]; then
        run "$PREFIX/bin/ibus-llm-assist" disable
    else
        info "$(t 'The engine is not installed: nothing to put back.')"
    fi
fi

step "$(t 'Engine (needs sudo)')"
ask "$(t 'Remove the engine from the system?')" y || exit 0
remove_system_files
[ -n "$DESTROOT" ] && exit 0
have ibus && run ibus write-cache && run ibus restart

if [ "$KEEP_SERVER" = 0 ]; then
    step "$(t 'Local language model server')"
    if [ "$PURGE" = 1 ]; then remove_server purge; else remove_server; fi
fi

if [ "$PURGE" = 1 ] && gsettings list-schemas 2>/dev/null | grep -qx "$IBLA_SCHEMA"; then
    run gsettings reset-recursively "$IBLA_SCHEMA"
elif [ "$PURGE" = 1 ]; then
    # The schema is gone with the engine: clear its stored values directly.
    run dconf reset -f /io/github/maximeallanic/IBusLlmAssist/
fi
good "$(t 'ibus-llm-assist is removed.')"
