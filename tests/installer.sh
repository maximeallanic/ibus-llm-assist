#!/usr/bin/env bash
# Installer round trip into a staging root: install.sh --destroot, then the same through the one-line bootstrap
# (a local tarball stands for the GitHub release), then uninstall.sh --destroot must leave the root empty.
# Needs no root and touches no session.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
WORK=$(mktemp -d "${TMPDIR:-/tmp}/ibla-installer-test.XXXXXX")
trap 'rm -rf -- "$WORK"' EXIT
fail() { echo "FAIL: $*" >&2; exit 1; }

check_tree() {  # DESTROOT
    local d=$1 component=$1/usr/share/ibus/component/ibus-llm-assist.xml
    [ -x "$d/usr/local/libexec/ibus-engine-llm-assist" ] || fail "engine launcher missing"
    [ -x "$d/usr/local/bin/ibus-llm-assist" ] || fail "CLI missing"
    [ -f "$d/usr/local/lib/ibus-llm-assist/llm_assist/controller.py" ] || fail "package missing"
    [ -f "$d/usr/share/glib-2.0/schemas/io.github.maximeallanic.IBusLlmAssist.gschema.xml" ] || fail "schema missing"
    grep -q '<exec>/usr/local/libexec/ibus-engine-llm-assist --ibus</exec>' "$component" || fail "component exec"
    grep -q '@' "$component" && fail "unsubstituted placeholder in the component"
    if command -v msgfmt >/dev/null; then
        [ -f "$d/usr/local/share/locale/fr/LC_MESSAGES/ibus-llm-assist.mo" ] || fail "French catalogue missing"
    fi
    (cd "$d" && sed 's|  /|  |' usr/local/share/ibus-llm-assist/manifest | sha256sum --check --quiet) || fail "manifest"
    "$d/usr/local/libexec/ibus-engine-llm-assist" --version | grep -qx '[0-9.]*' || fail "launcher does not run"
}

check_empty() {
    local left
    left=$(find "$1" -type f)
    [ -z "$left" ] || fail "left behind: $left"
}

echo "== install.sh --destroot"
"$ROOT/install.sh" --destroot "$WORK/a" --yes --no-deps >"$WORK/a.log" 2>&1 || { cat "$WORK/a.log"; fail "install"; }
check_tree "$WORK/a"
echo "== reinstall is idempotent"
"$ROOT/install.sh" --destroot "$WORK/a" --yes --no-deps >"$WORK/a2.log" 2>&1 || { cat "$WORK/a2.log"; fail "reinstall"; }
check_tree "$WORK/a"
echo "== uninstall.sh --destroot"
"$ROOT/uninstall.sh" --destroot "$WORK/a" --yes >"$WORK/u.log" 2>&1 || { cat "$WORK/u.log"; fail "uninstall"; }
check_empty "$WORK/a"

echo "== one-line bootstrap (curl | bash) from a local tarball"
mkdir -p "$WORK/src/ibus-llm-assist-test"
(cd "$ROOT" && git ls-files -z --cached --others --exclude-standard | xargs -0 cp --parents -t "$WORK/src/ibus-llm-assist-test")
tar -czf "$WORK/release.tar.gz" -C "$WORK/src" ibus-llm-assist-test
sum=$(sha256sum "$WORK/release.tar.gz" | cut -d' ' -f1)
XDG_CACHE_HOME=$WORK/cache IBUS_LLM_ASSIST_TARBALL=file://$WORK/release.tar.gz IBUS_LLM_ASSIST_SHA256=$sum \
    bash -s -- --destroot "$WORK/b" --yes --no-deps <"$ROOT/install.sh" >"$WORK/b.log" 2>&1 \
    || { cat "$WORK/b.log"; fail "bootstrap"; }
check_tree "$WORK/b"
echo "== bootstrap refuses a tarball with the wrong checksum"
if XDG_CACHE_HOME=$WORK/cache IBUS_LLM_ASSIST_TARBALL=file://$WORK/release.tar.gz IBUS_LLM_ASSIST_SHA256=0000 \
    bash -s -- --destroot "$WORK/c" --yes --no-deps <"$ROOT/install.sh" >"$WORK/c.log" 2>&1; then
    fail "a wrong checksum was accepted"
fi
[ ! -e "$WORK/c" ] || fail "something was installed despite the wrong checksum"
echo "installer tests: OK"
