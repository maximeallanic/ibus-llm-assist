#!/usr/bin/env bash
# Run as root in a clean container of a distribution (CI matrix, or by hand with
# "docker run --rm -v "$PWD":/repo:ro fedora:latest /repo/tests/distro.sh fedora"): adds only what is needed to run
# install.sh, lets install.sh install the engine's packages itself, stages the engine, runs the unit tests against
# those packages, and uninstalls. No desktop session: the steps that need one are not exercised.
set -euo pipefail
family=${1:?debian, fedora or arch}
case "$family" in
    debian) export DEBIAN_FRONTEND=noninteractive
            apt-get update -qq && apt-get install -y -qq --no-install-recommends python3 ca-certificates curl git >/dev/null ;;
    fedora) dnf install -y -q python3 git-core dbus-daemon >/dev/null ;;   # dbus-daemon: the private bus of the tests
    arch) pacman -Sy --noconfirm --needed python git >/dev/null ;;
    *) echo "unknown family $family" >&2; exit 2 ;;
esac
src=$(mktemp -d)
cp -a "$(cd "$(dirname "$0")/.." && pwd)/." "$src"
cd "$src"
git config --global --add safe.directory "$src"
./install.sh --destroot /stage --yes
[ "$(/stage/usr/local/bin/ibus-llm-assist --version)" = "$(sed -n 's/^IBLA_VERSION=//p' lib/common.sh)" ]
python3 -W ignore::DeprecationWarning -m unittest discover -s tests -t .
./uninstall.sh --destroot /stage --yes
left=$(find /stage -type f)
[ -z "$left" ] || { echo "left behind: $left" >&2; exit 1; }
echo "distro test ($family): OK"
