# shellcheck shell=bash
# The system-wide part: the engine program, its IBus component, its settings schema and its translations. Built in
# a staging directory as the person, then copied as root; every file copied is listed with its sha256 in the
# manifest, which uninstall.sh and verify.sh read. Sourced by install.sh and uninstall.sh.

# Paths of the installed files, relative to the system root.
sys_libdir() { echo "$PREFIX/lib/ibus-llm-assist"; }
sys_libexecdir() { echo "$PREFIX/libexec"; }
sys_localedir() { echo "$PREFIX/share/locale"; }

# compile_catalogues DEST: po/*.po -> DEST/<lang>/LC_MESSAGES/ibus-llm-assist.mo
compile_catalogues() {
    local dest=$1 po lang
    have msgfmt || { warn "$(t 'msgfmt is missing: messages stay in English.')"; return 0; }
    for po in "$IBLA_ROOT"/po/*.po; do
        [ -f "$po" ] || continue
        lang=$(basename "$po" .po)
        mkdir -p "$dest/$lang/LC_MESSAGES"
        msgfmt --check -o "$dest/$lang/LC_MESSAGES/$IBLA_DOMAIN.mo" "$po"
    done
}

# stage_system_files STAGE: the tree to copy under /, as the person.
stage_system_files() {
    local stage=$1 libdir libexecdir
    libdir=$stage$(sys_libdir)
    libexecdir=$stage$(sys_libexecdir)
    mkdir -p "$libdir/llm_assist" "$libexecdir" "$stage$PREFIX/bin" "$stage$IBLA_COMPONENT_DIR" "$stage$IBLA_SCHEMA_DIR"
    cp "$IBLA_ROOT"/llm_assist/*.py "$libdir/llm_assist/"
    cp "$IBLA_ROOT/bin/ibus-engine-llm-assist" "$libexecdir/"
    cp "$IBLA_ROOT/bin/ibus-llm-assist" "$stage$PREFIX/bin/"
    sed -e "s|@LIBEXECDIR@|$(sys_libexecdir)|g" -e "s|@VERSION@|$IBLA_VERSION|g" \
        "$IBLA_ROOT/data/ibus-llm-assist.xml.in" >"$stage$IBLA_COMPONENT_DIR/ibus-llm-assist.xml"
    cp "$IBLA_ROOT/data/$IBLA_SCHEMA.gschema.xml" "$stage$IBLA_SCHEMA_DIR/"
    compile_catalogues "$stage$(sys_localedir)"
    # Bytecode checked against the source hash, not its timestamp: the copy as root does not keep timestamps, and
    # the engine, run as the person, cannot write it into a root-owned directory.
    python3 -m compileall -q --invalidation-mode checked-hash "$libdir/llm_assist" >/dev/null
    chmod -R u=rwX,go=rX "$stage"
    chmod 755 "$libexecdir/ibus-engine-llm-assist" "$stage$PREFIX/bin/ibus-llm-assist"
}

# install_system_files: stage, copy as root, write the manifest, compile the schemas.
install_system_files() {
    local stage manifest_tmp
    stage=$(mktemp -d "${TMPDIR:-/tmp}/ibus-llm-assist-stage.XXXXXX")
    # shellcheck disable=SC2064  # expand now: the trap must remove this very directory
    trap "rm -rf -- '$stage'" RETURN
    stage_system_files "$stage"
    manifest_tmp=$stage.manifest
    (cd "$stage" && find . -type f -print0 | sort -z | xargs -0 sha256sum) | sed 's|  \./|  /|' >"$manifest_tmp"
    mkdir -p "$stage$PREFIX/share/ibus-llm-assist"
    mv "$manifest_tmp" "$stage$PREFIX/share/ibus-llm-assist/manifest"
    if [ "$DRY_RUN" = 1 ]; then
        info "$(t 'Files that would be installed:')"
        (cd "$stage" && find . -type f | sed 's|^\.|      |' | sort)
        return 0
    fi
    # Files of an earlier version that this one no longer has.
    local old
    while IFS= read -r old; do
        [ -e "$stage$old" ] || [ ! -e "$DESTROOT$old" ] || as_root rm -f -- "$DESTROOT$old"
    done < <(manifest_paths)
    # One copy of the whole tree: existing directories (/usr, /usr/share/ibus/component…) are left as they are.
    as_root mkdir -p "${DESTROOT:-/}"
    as_root cp -R --no-preserve=ownership,timestamps "$stage/." "${DESTROOT:-/}"
    if [ -z "$DESTROOT" ]; then
        as_root glib-compile-schemas "$IBLA_SCHEMA_DIR"
    fi
}

# The installed files, from the manifest, refusing any path outside the places this project installs to.
manifest_paths() {
    local manifest path
    manifest=$(system_manifest)
    [ -f "$manifest" ] || return 0
    while read -r _sum path; do
        case "$path" in
            "$PREFIX"/lib/ibus-llm-assist/* | "$PREFIX"/libexec/ibus-engine-llm-assist | \
                "$PREFIX"/bin/ibus-llm-assist | "$PREFIX"/share/locale/*/LC_MESSAGES/ibus-llm-assist.mo | \
                "$PREFIX"/share/ibus-llm-assist/manifest | "$IBLA_COMPONENT_DIR"/ibus-llm-assist.xml | \
                "$IBLA_SCHEMA_DIR/$IBLA_SCHEMA".gschema.xml)
                echo "$path" ;;
            *) warn "$(tf 'Not removed, outside the installed paths: %s' "$path")" ;;
        esac
    done <"$manifest"
}

# Files whose content differs from the manifest (or that are missing), one per line.
changed_system_files() {
    local manifest
    manifest=$(system_manifest)
    [ -f "$manifest" ] || return 0
    (cd "${DESTROOT:-/}" && sed 's|  /|  |' "$manifest" | sha256sum --check --quiet 2>/dev/null) \
        | sed -n 's|^\(.*\): FAILED.*$|/\1|p' | sort -u
}

remove_system_files() {
    local paths path dir
    mapfile -t paths < <(manifest_paths)
    if [ "${#paths[@]}" = 0 ]; then
        info "$(t 'No system files recorded: nothing to remove.')"
        return 0
    fi
    for path in "${paths[@]}"; do
        [ -e "$DESTROOT$path" ] && as_root rm -f -- "$DESTROOT$path"
    done
    as_root rm -f -- "$(system_manifest)"
    # Bytecode of other Python versions, written if root ever ran the engine: this directory is the project's own.
    [ -d "$DESTROOT$(sys_libdir)/llm_assist/__pycache__" ] \
        && as_root rm -rf -- "$DESTROOT$(sys_libdir)/llm_assist/__pycache__"
    # Directories this project owns, removed once empty.
    for dir in "$(sys_libdir)/llm_assist" "$(sys_libdir)" "$PREFIX/share/ibus-llm-assist"; do
        [ -d "$DESTROOT$dir" ] && as_root rmdir --ignore-fail-on-non-empty -- "$DESTROOT$dir"
    done
    if [ -z "$DESTROOT" ]; then
        as_root glib-compile-schemas "$IBLA_SCHEMA_DIR"
    fi
}
