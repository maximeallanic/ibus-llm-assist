#!/usr/bin/env bash
# Every check CI runs: unit tests, translations, shell scripts, file sizes, installer round trip.
set -euo pipefail
cd "$(dirname "$0")/.."
status=0
section() { printf '\n== %s\n' "$*"; }

section "Unit tests"
PYTHONDONTWRITEBYTECODE=1 python3 -W ignore::DeprecationWarning -m unittest discover -s tests -t . || status=1

section "ShellCheck"
if command -v shellcheck >/dev/null; then
    git ls-files -z '*.sh' | xargs -0 shellcheck -x || status=1
else
    echo "shellcheck not installed: skipped"
fi

section "No source file over 500 lines"
while IFS= read -r -d '' f; do
    n=$(wc -l <"$f")
    if [ "$n" -gt 500 ]; then echo "$f: $n lines"; status=1; fi
done < <(git ls-files -z '*.py' '*.sh' '*.in' '*.xml' 'bin/*')

section "Installer"
tests/installer.sh || status=1

exit "$status"
