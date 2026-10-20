#!/usr/bin/env bash
# ibus-llm-assist installer. Run it as yourself, in your desktop session; it asks before using sudo.
#
#   From a checkout:  ./install.sh [options]          (./install.sh --help)
#   In one line:      curl -fsSL https://raw.githubusercontent.com/maximeallanic/ibus-llm-assist/main/install.sh | bash
#
# Run without a checkout next to it, it downloads the source of the release it belongs to and runs that.
set -euo pipefail

IBLA_RELEASE=v0.1.0

bootstrap() {
    local ref=${IBUS_LLM_ASSIST_REF:-$IBLA_RELEASE} url cache archive dir
    url=${IBUS_LLM_ASSIST_TARBALL:-https://github.com/maximeallanic/ibus-llm-assist/archive/$ref.tar.gz}
    cache=${XDG_CACHE_HOME:-$HOME/.cache}/ibus-llm-assist
    archive=$cache/source-$ref.tar.gz
    dir=$cache/source-$ref
    command -v curl >/dev/null || { echo "curl is needed to download ibus-llm-assist." >&2; exit 1; }
    echo "==> Downloading ibus-llm-assist $ref"
    mkdir -p "$cache"
    curl --fail --location --silent --show-error --output "$archive" "$url"
    if [ -n "${IBUS_LLM_ASSIST_SHA256:-}" ]; then
        echo "$IBUS_LLM_ASSIST_SHA256  $archive" | sha256sum --check --status \
            || { echo "Checksum mismatch for $archive." >&2; exit 1; }
    fi
    rm -rf -- "${dir:?}"
    mkdir -p "$dir"
    tar -xzf "$archive" -C "$dir" --strip-components=1
    rm -f -- "$archive"
    exec bash "$dir/install.sh" "$@"
}

usage() {
    cat <<EOF
$(t 'Usage: install.sh [options]')

$(t 'Installs the ibus-llm-assist engine (asks for sudo for the system files), optionally a local language model
server in your home directory, and turns the engine on for your keyboard layouts.')

  --dry-run              $(t 'print what would be done, change nothing')
  -y, --yes              $(t 'answer yes to every question')
  --no-deps              $(t 'do not install missing system packages')
  --no-server            $(t 'do not set up the local language model server')
  --port N               $(t 'port of the local server (default 8033)')
  --endpoint URL         $(t 'use this server instead (implies --no-server)')
  --server-api API       $(t 'llama.cpp (default) or openai')
  --model NAME           $(t 'model name to send to the server')
  --no-enable            $(t 'install only; turn it on later with "ibus-llm-assist enable"')
  --prefix DIR           $(t 'where the program goes (default /usr/local)')
  --destroot DIR         $(t 'stage the system files under DIR (packaging, tests); nothing else is done')
  --uninstall            $(t 'same as ./uninstall.sh')
  --version, -h, --help
EOF
}

parse_args() {
    NO_SERVER=0 NO_ENABLE=0 ENDPOINT='' SERVER_API='' MODEL=''
    while [ $# -gt 0 ]; do
        case "$1" in
            --dry-run) DRY_RUN=1 ;;
            -y | --yes) ASSUME_YES=1 ;;
            --no-deps) SKIP_DEPS=1 ;;
            --no-server) NO_SERVER=1 ;;
            --port) SERVER_PORT=${2:?}; shift ;;
            --endpoint) ENDPOINT=${2:?}; NO_SERVER=1; shift ;;
            --server-api) SERVER_API=${2:?}; shift ;;
            --model) MODEL=${2:?}; shift ;;
            --no-enable) NO_ENABLE=1 ;;
            --prefix) PREFIX=${2:?}; shift ;;
            --destroot) DESTROOT=$(realpath -m "${2:?}"); shift ;;
            --uninstall) shift; exec "$IBLA_ROOT/uninstall.sh" "$@" ;;
            --version) echo "$IBLA_VERSION"; exit 0 ;;
            -h | --help) usage; exit 0 ;;
            *) usage >&2; die "$(tf 'Unknown option: %s' "$1")" ;;
        esac
        shift
    done
    case "$SERVER_API" in '' | llama.cpp | openai) ;; *) die "$(t '--server-api is llama.cpp or openai')" ;; esac
    case "$SERVER_PORT" in *[!0-9]* | '') die "$(t '--port takes a number')" ;; esac
}

preflight() {
    if [ -z "$DESTROOT" ] && [ "$(id -u)" = 0 ]; then
        die "$(t 'Run the installer as yourself, not as root: it asks for sudo when it needs it.')"
    fi
    have python3 || die "$(t 'Python 3 is needed.')"
    python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' \
        || die "$(t 'Python 3.10 or newer is needed.')"
    [ -n "$DESTROOT" ] && return 0
    have_session || die "$(t 'No desktop session found: run the installer from a terminal of your desktop session.')"
    case "${XDG_CURRENT_DESKTOP:-}" in
        *GNOME*) ;;
        *) warn "$(t 'Only GNOME is tested. Elsewhere, add the engine yourself with "ibus-setup" after the install.')" ;;
    esac
}

configure_settings() {
    local args=()
    [ -n "$ENDPOINT" ] && args+=(endpoint "$ENDPOINT")
    [ -z "$ENDPOINT" ] && [ "$SERVER_PORT" != 8033 ] && args+=(endpoint "http://127.0.0.1:$SERVER_PORT")
    [ -n "$SERVER_API" ] && args+=(server-api "$SERVER_API")
    [ -n "$MODEL" ] && args+=(model "$MODEL")
    while [ ${#args[@]} -gt 0 ]; do
        run gsettings set "$IBLA_SCHEMA" "${args[0]}" "${args[1]}"
        args=("${args[@]:2}")
    done
}

main() {
    parse_args "$@"
    preflight
    compile_catalogues "$IBLA_ROOT/build/locale"

    printf '%sibus-llm-assist %s%s\n' "$C_BOLD" "$IBLA_VERSION" "$C_RESET"
    info "$(t 'Suggests the rest of your sentence (Ctrl+Tab accepts) and corrects each finished sentence, with a language model that runs on this computer.')"
    [ "$DRY_RUN" = 1 ] && warn "$(t 'Dry run: nothing will be changed.')"

    step "$(t '1/5 System packages')"
    ensure_packages engine || [ "$DRY_RUN" = 1 ] || [ -n "$DESTROOT" ] \
        || die "$(t 'Missing system packages: see above.')"

    step "$(tf '2/5 Engine (into %s, needs sudo)' "${DESTROOT}$PREFIX")"
    install_system_files
    if [ -n "$DESTROOT" ]; then
        good "$(tf 'Staged under %s.' "$DESTROOT")"
        return 0
    fi

    step "$(t '3/5 Language model server')"
    if [ "$NO_SERVER" = 1 ]; then
        info "$(t 'Skipped: the engine will use the server you configured.')"
    elif ! setup_server; then
        warn "$(t 'No local server set up. The engine stays silent until a server answers (docs/configuration.md).')"
    fi
    if [ "$DRY_RUN" != 1 ]; then configure_settings; fi

    step "$(t '4/5 Your keyboard layouts')"
    if [ "$NO_ENABLE" = 1 ]; then
        info "$(t 'Skipped: run "ibus-llm-assist enable" when you are ready.')"
    else
        run "$PREFIX/bin/ibus-llm-assist" enable || warn "$(t 'Not turned on: see the message above.')"
    fi

    step "$(t '5/5 Check')"
    if [ "$DRY_RUN" = 1 ]; then
        printf '\n%s\n' "$(t 'Dry run finished: nothing was changed.')"
        return 0
    fi
    if "$PREFIX/bin/ibus-llm-assist" status; then
        printf '\n%s%s%s\n' "$C_GREEN" "$(t 'Done. Type in any application, pause, and press Ctrl+Tab to accept a suggestion.')" "$C_RESET"
    else
        printf '\n%s\n' "$(t 'Installed, with the problems listed above. docs/troubleshooting.md explains each one.')"
    fi
    info "$(t 'Settings: the keyboard menu in the top bar.')"
    info "$(tf 'Uninstall: %s' "$IBLA_ROOT/uninstall.sh")"
}

if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ] \
    && [ -f "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh" ]; then
    IBLA_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
    # shellcheck source=lib/common.sh
    . "$IBLA_ROOT/lib/common.sh"
    # shellcheck source=lib/deps.sh
    . "$IBLA_ROOT/lib/deps.sh"
    # shellcheck source=lib/system.sh
    . "$IBLA_ROOT/lib/system.sh"
    # shellcheck source=lib/server.sh
    . "$IBLA_ROOT/lib/server.sh"
    main "$@"
else
    bootstrap "$@"
fi
