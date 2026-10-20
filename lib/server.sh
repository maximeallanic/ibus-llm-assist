# shellcheck shell=bash
# The optional local language model server: llama.cpp's official build and Google's Gemma 4 E2B, both pinned and
# checked by sha256, run by a systemd user unit on 127.0.0.1. Everything goes in the person's home directory; no
# root. Sourced by install.sh and uninstall.sh.

# llama.cpp release b11714 (2026-10, commit c0fd78626405c6d9b934efef0ec7291fcc20e3d6), Vulkan builds. The sha256
# are the digests GitHub publishes for the release assets.
LLAMA_BUILD=b11714
declare -A LLAMA_ASSET=(
    [x86_64]="llama-b11714-bin-ubuntu-vulkan-x64.tar.gz a41bc4a20dc7935492a7a1216aa10c39ff7919349864873a46c74022bcd28a26"
    [aarch64]="llama-b11714-bin-ubuntu-vulkan-arm64.tar.gz 2e021febe3aa84ece1f7ba1865c3744fb3b960b28dac142dc7e84aac41899851"
)
# Gemma 4 E2B instruction-tuned, Google's official QAT q4_0 GGUF (Apache 2.0), at a fixed revision of the repository.
MODEL_REPO=google/gemma-4-E2B-it-qat-q4_0-gguf
MODEL_REV=675cff42a74c774d6cb76f76d8eacb49b48c9b93
MODEL_FILE=gemma-4-E2B_q4_0-it.gguf
MODEL_SHA256=fa401b55b07ee70a54c6dae3903c783a6e65064312529ea57175cb5f8dec6634
MODEL_SIZE_GB=3.4
MODEL_ALIAS=gemma-4-e2b
SERVER_UNIT=ibus-llm-assist-server.service
SERVER_PORT=${SERVER_PORT:-8033}

server_dir() { echo "$(user_data_dir)/llama.cpp/$LLAMA_BUILD"; }
model_path() { echo "$(user_data_dir)/models/$MODEL_FILE"; }
server_unit_path() { echo "$(user_unit_dir)/$SERVER_UNIT"; }

# server_answers URL: 0 when an OpenAI-compatible server lists its models there.
server_answers() {
    curl --silent --fail --max-time 10 "${1%/}/v1/models" >/dev/null 2>&1
}

# fetch URL FILE SHA256: download (resuming a partial file), then check; a mismatch stops the install.
fetch() {
    local url=$1 file=$2 sum=$3
    if echo "$sum  $file" | sha256sum --check --status 2>/dev/null; then
        good "$(tf 'Already downloaded: %s' "$file")"
        return 0
    fi
    run mkdir -p "$(dirname "$file")"
    run curl --fail --location --continue-at - --retry 3 --progress-bar --output "$file" "$url"
    [ "$DRY_RUN" = 1 ] && return 0
    echo "$sum  $file" | sha256sum --check --status \
        || die "$(tf 'Checksum mismatch for %s: delete it and run the installer again.' "$file")"
}

install_llama_cpp() {
    local arch asset name sum archive
    arch=$(uname -m)
    asset=${LLAMA_ASSET[$arch]:-}
    [ -n "$asset" ] || die "$(tf 'No prebuilt llama.cpp for %s: build llama-server yourself and point the engine at it (docs/configuration.md).' "$arch")"
    read -r name sum <<<"$asset"
    if [ -x "$(server_dir)/llama-server" ]; then
        good "$(tf 'llama.cpp %s already installed.' "$LLAMA_BUILD")"
        return 0
    fi
    archive="$(user_data_dir)/downloads/$name"
    fetch "https://github.com/ggml-org/llama.cpp/releases/download/$LLAMA_BUILD/$name" "$archive" "$sum"
    run mkdir -p "$(server_dir)"
    run tar -xzf "$archive" -C "$(server_dir)" --strip-components=1
    run rm -f -- "$archive"
}

write_server_unit() {
    local unit
    unit=$(server_unit_path)
    run mkdir -p "$(dirname "$unit")"
    [ "$DRY_RUN" = 1 ] && return 0
    sed -e "s|@LLAMA_SERVER@|$(server_dir)/llama-server|g" -e "s|@MODEL_PATH@|$(model_path)|g" \
        -e "s|@MODEL_ALIAS@|$MODEL_ALIAS|g" -e "s|@MODEL_NAME@|Gemma 4 E2B|g" -e "s|@PORT@|$SERVER_PORT|g" \
        "$IBLA_ROOT/data/ibus-llm-assist-server.service.in" >"$unit.new"
    mv "$unit.new" "$unit"
}

wait_for_server() {
    local url=http://127.0.0.1:$SERVER_PORT i
    [ "$DRY_RUN" = 1 ] && return 0
    info "$(t 'Waiting for the model to load (up to 3 minutes the first time)…')"
    for i in $(seq 180); do
        curl --silent --fail --max-time 2 "$url/health" >/dev/null 2>&1 && return 0
        [ $((i % 30)) = 0 ] && info "$(tf '%s s…' "$i")"
        sleep 1
    done
    return 1
}

# setup_server: the whole optional step. Returns 1 when the person declines or it cannot be done.
setup_server() {
    local endpoint=http://127.0.0.1:$SERVER_PORT
    if server_answers "$endpoint"; then
        good "$(tf 'A language model server already answers at %s: it will be used.' "$endpoint")"
        return 0
    fi
    if curl --silent --max-time 3 "$endpoint" >/dev/null 2>&1; then
        warn "$(tf 'Port %s is taken by another program. Choose another one with --port.' "$SERVER_PORT")"
        return 1
    fi
    info "$(tf 'This downloads llama.cpp %s (about 30 MB) and the Gemma 4 E2B model (%s GB) into %s, and runs them as a user service on 127.0.0.1:%s.' \
        "$LLAMA_BUILD" "$MODEL_SIZE_GB" "$(user_data_dir)" "$SERVER_PORT")"
    ask "$(t 'Set up the local language model server now?')" y || return 1
    have systemctl || die "$(t 'systemd is needed to run the server as a user service.')"
    ensure_packages server || warn "$(t 'Without the Vulkan loader the model runs on the processor, more slowly.')"
    install_llama_cpp
    fetch "https://huggingface.co/$MODEL_REPO/resolve/$MODEL_REV/$MODEL_FILE" "$(model_path)" "$MODEL_SHA256"
    if [ "$DRY_RUN" != 1 ] && ! "$(server_dir)/llama-server" --list-devices 2>/dev/null | grep -q 'Vulkan'; then
        warn "$(t 'No GPU usable through Vulkan: the model runs on the processor. Suggestions will be slower.')"
    fi
    write_server_unit
    run systemctl --user daemon-reload
    run systemctl --user enable --now "$SERVER_UNIT"
    if wait_for_server; then
        good "$(tf 'Language model server ready at %s.' "$endpoint")"
    else
        warn "$(tf 'The server did not answer in time. See: journalctl --user -u %s' "$SERVER_UNIT")"
        return 1
    fi
}

# remove_server [purge]: stop the unit; with purge, also delete llama.cpp and the model.
remove_server() {
    local unit
    unit=$(server_unit_path)
    if [ -f "$unit" ]; then
        run systemctl --user disable --now "$SERVER_UNIT"
        run rm -f -- "$unit"
        run systemctl --user daemon-reload
    fi
    if [ "${1:-}" = purge ]; then
        [ -d "$(user_data_dir)/llama.cpp" ] && run rm -rf -- "$(user_data_dir)/llama.cpp"
        [ -f "$(model_path)" ] && run rm -f -- "$(model_path)"
        [ -d "$(user_data_dir)/models" ] && run rmdir --ignore-fail-on-non-empty -- "$(user_data_dir)/models"
        [ -d "$(user_data_dir)/downloads" ] && run rm -rf -- "$(user_data_dir)/downloads"
        [ -d "$(user_data_dir)" ] && run rmdir --ignore-fail-on-non-empty -- "$(user_data_dir)"
    elif [ -d "$(user_data_dir)" ]; then
        info "$(tf 'The model and llama.cpp stay in %s (--purge deletes them).' "$(user_data_dir)")"
    fi
}
