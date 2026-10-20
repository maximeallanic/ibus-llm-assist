# shellcheck shell=bash
# Shared helpers of install.sh, uninstall.sh and verify.sh: messages, translations, prompts, privileged steps,
# distribution detection. Sourced, never run.

IBLA_VERSION=0.1.1
IBLA_REPO=maximeallanic/ibus-llm-assist
IBLA_SCHEMA=io.github.maximeallanic.IBusLlmAssist
IBLA_DOMAIN=ibus-llm-assist
# ibus-daemon reads components from this directory only (IBUS_COMPONENT_PATH aside), whatever the prefix.
IBLA_COMPONENT_DIR=/usr/share/ibus/component
# The distribution's schema directory: a gschemas.compiled under /usr/local would come first in XDG_DATA_DIRS and
# hide every other schema from programs that look up the default source non-recursively.
IBLA_SCHEMA_DIR=/usr/share/glib-2.0/schemas

DRY_RUN=${DRY_RUN:-0}
ASSUME_YES=${ASSUME_YES:-0}
# Staging root for packagers and tests: system files go under it, nothing is run as root, no session is touched.
DESTROOT=${DESTROOT:-}
PREFIX=${PREFIX:-/usr/local}

# Translations: gettext from the catalogues compiled in the checkout (build/locale), when gettext is installed.
export TEXTDOMAIN=$IBLA_DOMAIN
export TEXTDOMAINDIR=${IBLA_ROOT:?}/build/locale
t() {
    if command -v gettext >/dev/null 2>&1; then gettext "$1"; else printf '%s' "$1"; fi
}
# tf FORMAT ARGS...: printf with a translated format.
tf() {
    local fmt
    fmt=$(t "$1")
    shift
    # shellcheck disable=SC2059  # the format is ours, from the catalogue
    printf -- "$fmt" "$@"
}

if [ -t 1 ]; then
    C_BOLD=$'\e[1m' C_DIM=$'\e[2m' C_RED=$'\e[31m' C_GREEN=$'\e[32m' C_YELLOW=$'\e[33m' C_RESET=$'\e[0m'
else
    C_BOLD='' C_DIM='' C_RED='' C_GREEN='' C_YELLOW='' C_RESET=''
fi

step() { printf '\n%s==> %s%s\n' "$C_BOLD" "$*" "$C_RESET"; }
info() { printf '    %s\n' "$*"; }
good() { printf '    %s%s%s\n' "$C_GREEN" "$*" "$C_RESET"; }
warn() { printf '    %s%s%s\n' "$C_YELLOW" "$*" "$C_RESET" >&2; }
die() { printf '%s%s%s\n' "$C_RED" "$*" "$C_RESET" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

# The terminal, for questions: with "curl … | bash" the standard input is the script itself.
tty_in() {
    if [ -r /dev/tty ] && { : </dev/tty; } 2>/dev/null; then echo /dev/tty; else echo /dev/stdin; fi
}

# ask QUESTION [default y|n]: 0 for yes. With --yes, or without a terminal, the default is taken. What counts as
# "yes" is the locale's own answer pattern (locale yesexpr), so a reply in the person's language works.
ask() {
    local question=$1 default=${2:-y} reply hint yes input
    if [ "$default" = y ]; then hint=$(t '[Y/n]'); else hint=$(t '[y/N]'); fi
    input=$(tty_in)
    if [ "$ASSUME_YES" = 1 ] || { [ "$input" = /dev/stdin ] && [ ! -t 0 ]; }; then
        info "$question $hint"
        [ "$default" = y ]
        return
    fi
    read -r -p "    $question $hint " reply <"$input" || reply=
    [ -n "$reply" ] || { [ "$default" = y ]; return; }
    yes=$(locale yesexpr 2>/dev/null) || yes='^[+1yY]'
    [[ $reply =~ ${yes:-^[+1yY]} ]]
}

# run CMD...: print it, and run it unless --dry-run.
run() {
    printf '    %s$ %s%s\n' "$C_DIM" "$*" "$C_RESET"
    [ "$DRY_RUN" = 1 ] || "$@"
}

# as_root CMD...: run with sudo, or directly when staging into DESTROOT or already root.
as_root() {
    if [ -n "$DESTROOT" ] || [ "$(id -u)" = 0 ]; then
        run "$@"
    else
        run sudo "$@"
    fi
}

# Distribution family from /etc/os-release: debian, fedora, arch, suse or unknown.
distro_family() {
    local id='' like=''
    if [ -r "${IBLA_OS_RELEASE:-/etc/os-release}" ]; then
        # shellcheck source=/dev/null
        id=$(. "${IBLA_OS_RELEASE:-/etc/os-release}" && echo "${ID:-}")
        # shellcheck source=/dev/null
        like=$(. "${IBLA_OS_RELEASE:-/etc/os-release}" && echo "${ID_LIKE:-}")
    fi
    for word in $id $like; do
        case "$word" in
            debian | ubuntu) echo debian; return ;;
            fedora | rhel | centos) echo fedora; return ;;
            arch | archlinux) echo arch; return ;;
            suse | opensuse | opensuse-tumbleweed | opensuse-leap) echo suse; return ;;
        esac
    done
    echo unknown
}

# Paths of the person's own files (XDG defaults).
user_data_dir() { echo "${XDG_DATA_HOME:-$HOME/.local/share}/ibus-llm-assist"; }
user_unit_dir() { echo "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"; }
system_manifest() { echo "$DESTROOT$PREFIX/share/ibus-llm-assist/manifest"; }

# The desktop session is reachable (D-Bus of the session, as the person who runs the script).
have_session() {
    [ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ] || [ -S "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/bus" ]
}
