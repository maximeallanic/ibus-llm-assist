#!/usr/bin/env bash
# Checks an installed ibus-llm-assist: installed files unchanged since the install, then "ibus-llm-assist status"
# (engine known to IBus, input sources, server, session). --tests also runs the unit tests of this checkout.
set -uo pipefail

IBLA_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib/common.sh
. "$IBLA_ROOT/lib/common.sh"
# shellcheck source=lib/system.sh
. "$IBLA_ROOT/lib/system.sh"

TESTS=0
for arg in "$@"; do
    case "$arg" in
        --tests) TESTS=1 ;;
        --prefix=*) PREFIX=${arg#--prefix=} ;;
        -h | --help) printf "%s\n" "$(t 'Usage: verify.sh [--tests] [--prefix=DIR]')"; exit 0 ;;
        *) die "$(tf 'Unknown option: %s' "$arg")" ;;
    esac
done
compile_catalogues "$IBLA_ROOT/build/locale" 2>/dev/null
status=0

if [ ! -f "$(system_manifest)" ]; then
    printf '%s  %s\n' "$(t 'FAIL')" "$(tf 'Not installed (no %s): run ./install.sh' "$(system_manifest)")"
    exit 1
fi
changed=$(changed_system_files)
if [ -z "$changed" ]; then
    printf '%s  %s\n' "$(t 'OK  ')" "$(t 'Installed files are as installed')"
else
    status=1
    while IFS= read -r file; do
        printf '%s  %s\n' "$(t 'FAIL')" "$(tf 'Changed or missing: %s (run ./install.sh again)' "$file")"
    done <<<"$changed"
fi

"$PREFIX/bin/ibus-llm-assist" status || status=1

if [ "$TESTS" = 1 ]; then
    if (cd "$IBLA_ROOT" && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -t . >/dev/null 2>&1); then
        printf '%s  %s\n' "$(t 'OK  ')" "$(t 'Unit tests pass')"
    else
        printf '%s  %s\n' "$(t 'FAIL')" "$(t 'Unit tests fail: python3 -m unittest discover -s tests -t .')"
        status=1
    fi
fi
exit "$status"
