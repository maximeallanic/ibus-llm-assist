# shellcheck shell=bash
# System packages: what the engine needs, checked by capability (a command, a typelib), then mapped to the package
# names of the distribution family. Sourced by install.sh.

# capability -> "debian fedora arch suse" package names (- when the capability comes with another package).
declare -A IBLA_PACKAGES=(
    [ibus]="ibus ibus ibus ibus"
    [python-gi]="python3-gi python3-gobject python-gobject python3-gobject"
    [typelib-ibus]="gir1.2-ibus-1.0 ibus-libs - typelib-1_0-IBus-1_0"
    [typelib-soup]="gir1.2-soup-3.0 libsoup3 libsoup3 typelib-1_0-Soup-3_0"
    [glib-tools]="libglib2.0-bin glib2 glib2 glib2-tools"
    [pango]="libpango-1.0-0 pango pango libpango-1_0-0"
    [msgfmt]="gettext gettext gettext gettext-tools"
    [curl]="curl curl curl curl"
)
# Needed by the local server only: the Vulkan loader (the GPU driver itself comes with the desktop).
declare -A IBLA_SERVER_PACKAGES=(
    [vulkan]="libvulkan1 vulkan-loader vulkan-icd-loader libvulkan1"
)

_family_index() {
    case "$1" in debian) echo 0 ;; fedora) echo 1 ;; arch) echo 2 ;; suse) echo 3 ;; *) echo -1 ;; esac
}

_python_has() {  # <gi namespace> <version>
    python3 -c "import gi; gi.require_version('$1', '$2'); from gi.repository import $1" 2>/dev/null
}

# Capabilities missing on this system, one per line.
missing_capabilities() {
    have ibus || echo ibus
    if ! python3 -c 'import gi' 2>/dev/null; then
        # Without PyGObject the typelibs cannot be probed: ask for them too (a package already there is a no-op).
        printf '%s\n' python-gi typelib-ibus typelib-soup
    else
        _python_has IBus 1.0 || echo typelib-ibus
        _python_has Soup 3.0 || echo typelib-soup
    fi
    have glib-compile-schemas || echo glib-tools
    python3 -c "import ctypes; ctypes.CDLL('libpango-1.0.so.0')" 2>/dev/null || echo pango
    have msgfmt || echo msgfmt
    have curl || echo curl
}

missing_server_capabilities() {
    python3 -c "import ctypes; ctypes.CDLL('libvulkan.so.1')" 2>/dev/null || echo vulkan
}

# packages_for FAMILY CAPABILITY...: package names, deduplicated.
packages_for() {
    local family=$1 index cap names
    shift
    index=$(_family_index "$family")
    [ "$index" -ge 0 ] || return 1
    for cap in "$@"; do
        names=${IBLA_PACKAGES[$cap]:-${IBLA_SERVER_PACKAGES[$cap]:-}}
        read -r -a list <<<"$names"
        [ "${list[$index]:-}" = - ] || echo "${list[$index]}"
    done | sort -u
}

install_command() {  # FAMILY
    case "$1" in
        debian) echo "apt-get install -y --no-install-recommends" ;;
        fedora) echo "dnf install -y" ;;
        arch) echo "pacman -S --needed --noconfirm" ;;
        suse) echo "zypper --non-interactive install" ;;
    esac
}

# ensure_packages KIND: KIND is "engine" or "server". Installs what is missing after asking, or explains.
ensure_packages() {
    local kind=$1 family caps pkgs cmd
    if [ "$kind" = server ]; then caps=$(missing_server_capabilities); else caps=$(missing_capabilities); fi
    [ -n "$caps" ] || { good "$(t 'All needed system packages are installed.')"; return 0; }
    family=$(distro_family)
    # shellcheck disable=SC2086  # one capability per word
    if ! pkgs=$(packages_for "$family" $caps) || [ -z "$pkgs" ]; then
        warn "$(tf 'Missing on this system: %s. Install them with your package manager, then run the installer again.' "${caps//$'\n'/ }")"
        return 1
    fi
    cmd=$(install_command "$family")
    info "$(tf 'Missing packages: %s' "${pkgs//$'\n'/ }")"
    [ "$family" = suse ] && warn "$(t 'openSUSE package names are untested.')"
    if [ "${SKIP_DEPS:-0}" = 1 ]; then
        warn "$(t 'Skipped (--no-deps): install them yourself.')"
        return 1
    fi
    ask "$(tf 'Install them now with "sudo %s"?' "$cmd")" y || return 1
    [ "$family" = debian ] && as_root apt-get update -qq
    # shellcheck disable=SC2086  # word splitting of the command and the package list is wanted
    as_root $cmd $pkgs
    [ "${DRY_RUN:-0}" = 1 ] && return 0
    if [ "$kind" = server ]; then caps=$(missing_server_capabilities); else caps=$(missing_capabilities); fi
    if [ -n "$caps" ]; then
        warn "$(tf 'Still missing after the install: %s.' "${caps//$'\n'/ }")"
        return 1
    fi
    good "$(t 'All needed system packages are installed.')"
}
