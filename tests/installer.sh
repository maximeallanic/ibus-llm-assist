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

# piped PIN URL [PROTOCOLS] ARGS...: install.sh fed to bash through a pipe, as by curl | bash, with the pin and the
# download URL replaced. PROTOCOLS widens curl's protocol list so that a local file:// stands for the GitHub release;
# left empty, the installer keeps its own HTTPS-only list.
piped() {
    local pin=$1 url=$2 proto=$3
    shift 3
    sed -e "s|^RELEASE_SHA256=.*|RELEASE_SHA256='$pin'|" -e "s|^RELEASE_URL=.*|RELEASE_URL='$url'|" \
        -e "s|--proto '=https'|--proto '=${proto:-https}'|" "$ROOT/install.sh" \
        | XDG_CACHE_HOME=$WORK/cache bash -s -- "$@"
}
no_download_left() { ! compgen -G "$WORK/cache/ibus-llm-assist/.download.*" >/dev/null || fail "download dir left: $1"; }
for line in "^RELEASE_SHA256=" "^RELEASE_URL=" "--proto '=https' "; do
    grep -q -- "$line" "$ROOT/install.sh" || fail "install.sh has no '$line' for the bootstrap tests to replace"
done

echo "== piped bootstrap refuses without a pinned release"
# The pin is emptied here, as scripts/release.sh does in the tarball: the test does not depend on whether the checkout
# is a release commit.
if out=$(piped '' https://example.invalid/none.tar.gz '' --destroot "$WORK/n" --yes --no-deps 2>&1); then
    fail "bootstrap ran without a pin"
fi
grep -q "no release of ibus-llm-assist is pinned" <<<"$out" || fail "no clear refusal: $out"
grep -q "git clone" <<<"$out" || fail "no clone instructions: $out"
grep -q Downloading <<<"$out" && fail "downloaded without a pin: $out"
[ ! -e "$WORK/cache" ] || fail "the refusal created files"

echo "== piped bootstrap installs a release that matches the pin"
mkdir -p "$WORK/src/ibus-llm-assist-test"
(cd "$ROOT" && git ls-files -z --cached --others --exclude-standard | xargs -0 cp --parents -t "$WORK/src/ibus-llm-assist-test")
tar -czf "$WORK/release.tar.gz" -C "$WORK/src" ibus-llm-assist-test
sum=$(sha256sum "$WORK/release.tar.gz" | cut -d' ' -f1)
piped "$sum" "file://$WORK/release.tar.gz" https,file --destroot "$WORK/b" --yes --no-deps >"$WORK/b.log" 2>&1 \
    || { cat "$WORK/b.log"; fail "bootstrap"; }
check_tree "$WORK/b"
[ -x "$WORK/cache/ibus-llm-assist/source-v$(sed -n 's/^RELEASE_VERSION=//p' "$ROOT/install.sh")/uninstall.sh" ] \
    || fail "unpacked release not kept for uninstall.sh"
no_download_left "after an install"

echo "== piped bootstrap refuses a tampered release and cleans up"
cp "$WORK/release.tar.gz" "$WORK/tampered.tar.gz"
printf 'x' >>"$WORK/tampered.tar.gz"
if piped "$sum" "file://$WORK/tampered.tar.gz" https,file --destroot "$WORK/c" --yes --no-deps >"$WORK/c.log" 2>&1; then
    fail "a tampered release was accepted"
fi
grep -q "does not match the pinned sha256" "$WORK/c.log" || { cat "$WORK/c.log"; fail "no checksum refusal"; }
[ ! -e "$WORK/c" ] || fail "something was installed from a tampered release"
no_download_left "after a refused checksum"

echo "== piped bootstrap downloads over HTTPS only"
if piped "$sum" "file://$WORK/release.tar.gz" '' --destroot "$WORK/d" --yes --no-deps >"$WORK/d.log" 2>&1; then
    fail "a non-HTTPS URL was downloaded"
fi
[ ! -e "$WORK/d" ] || fail "something was installed from a non-HTTPS URL"
no_download_left "after a refused protocol"
echo "installer tests: OK"
