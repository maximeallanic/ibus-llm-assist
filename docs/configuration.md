# Configuration

## Switches

The keyboard menu of the top bar (the layout indicator) has two switches, **Suggestions** and **Corrections**. They
take effect at once and are kept in GSettings.

## Settings

Schema `io.github.maximeallanic.IBusLlmAssist`. Read them with `gsettings list-recursively
io.github.maximeallanic.IBusLlmAssist`; every change takes effect at once, without restarting anything.

| Key | Default | Meaning |
|---|---|---|
| `completion-enabled` | `true` | suggest the rest of the sentence after a pause |
| `correction-enabled` | `true` | correct each sentence once it is finished |
| `pause-ms` | `400` | pause in typing, in milliseconds (100 to 5000), before a suggestion is asked for |
| `endpoint` | `'http://127.0.0.1:8033'` | base URL of the server, without `/v1` |
| `server-api` | `'llama.cpp'` | `llama.cpp` (llama-server) or `openai` (any OpenAI-compatible server, experimental) |
| `model` | `''` | model name sent to the server; empty for the server's default |

```sh
gsettings set io.github.maximeallanic.IBusLlmAssist pause-ms 700
gsettings reset io.github.maximeallanic.IBusLlmAssist endpoint
```

## The local server

The installer's server is a systemd user unit:

```sh
systemctl --user status ibus-llm-assist-server
journalctl --user -u ibus-llm-assist-server
systemctl --user edit ibus-llm-assist-server      # change its options in a drop-in
```

It runs `llama-server` from `~/.local/share/ibus-llm-assist/llama.cpp/b11714` with
`~/.local/share/ibus-llm-assist/models/gemma-4-E2B_q4_0-it.gguf`, on 127.0.0.1 only, with every layer on the GPU when
Vulkan finds one. It unloads the model after five idle minutes and loads it again at the next request (a few seconds,
the first suggestion after a break comes late). Loaded, it takes about 5 GB of memory with an integrated GPU, whose
memory is the system's. Its memory is capped by the unit (`MemoryHigh=7G`, `MemoryMax=8G`).

## Another llama-server

Any llama.cpp server works with the default `server-api`: the engine uses its native `/apply-template` and
`/completion` endpoints for suggestions and `/v1/chat/completions` for corrections. Point the engine at it:

```sh
gsettings set io.github.maximeallanic.IBusLlmAssist endpoint 'http://127.0.0.1:8080'
```

A bigger model corrects better (Japanese in particular, see [benchmarks](benchmarks.md)) and suggests more slowly. The
model must be an instruction-tuned chat model with a chat template.

## Other servers

`server-api openai` uses only `/v1/chat/completions`. Corrections are a plain chat request. Suggestions are an
assistant message prefilled with the text, which the server must continue rather than answer: the request sets
`continue_final_message` and `add_generation_prompt: false` (vLLM's names); a server that repeats the text before its
continuation is handled too. **This mode is experimental**: it is tested against a stub server, not against Ollama,
vLLM or LM Studio. A server that ignores these fields *answers* the text instead of continuing it, and the
suggestions read like replies: turn Suggestions off in the keyboard menu and keep the corrections, which are plain
chat requests. llama-server is such a server through its OpenAI API (checked with Gemma 4), which is why the default
mode uses its native endpoints. Reports are welcome.

```sh
gsettings set io.github.maximeallanic.IBusLlmAssist endpoint 'http://127.0.0.1:11434'
gsettings set io.github.maximeallanic.IBusLlmAssist server-api openai
gsettings set io.github.maximeallanic.IBusLlmAssist model 'name-of-the-model'
```

### API key

A server that wants a bearer token reads it from `~/.config/ibus-llm-assist/api-key` (first line). The file is
ignored, with a warning in the journal, if other users can read it:

```sh
install -D -m 600 /dev/null ~/.config/ibus-llm-assist/api-key
editor ~/.config/ibus-llm-assist/api-key
```

The key is not kept in GSettings, which every program of your session can read.

A server that is not on this machine receives everything you type in the fields where the engine works:
`ibus-llm-assist status` warns about it. See [privacy.md](privacy.md).

## Look of the suggestion

The suggestion is pre-edit text with the "prediction" hint. GTK 4 styles it through the CSS node
`preedit.prediction`, in italic by default. This needs IBus 1.5.33 and GNOME Shell 51 or later: with older versions
GTK 4 receives no hint and underlines the suggestion, and the rules below change nothing
([compatibility](compatibility.md#look-of-the-suggestion-by-version)). For grey ghost text, add to `~/.config/gtk-4.0/gtk.css`:

```css
/* ibus-llm-assist: suggestions as translucent ghost text */
text > preedit.prediction { color: alpha(currentColor, 0.5); font-style: normal; }
```

That covers single-line fields (GtkEntry, search fields, GtkText). Multi-line fields (GtkTextView) need the
[GTK patch](patches.md) to draw the transparency; with it, use:

```css
text > preedit.prediction, textview > preedit.prediction { color: alpha(currentColor, 0.5); font-style: normal; }
```

Without the patch, leave `textview` out: there, the rule would remove the italic and the transparency would be
ignored, so the suggestion would look like typed text. Applications read the file when they start.

The installer does not touch this file. GTK 3, Qt and Chrome draw pre-edit text their own way (Chrome underlines it).

## Keys

| Key | When | Does |
|---|---|---|
| Ctrl+Tab | a suggestion is shown | accepts it |
| Escape | a suggestion is shown | dismisses it |
| the same letters as the suggestion | a suggestion is shown | keeps the rest of it |
| Ctrl+Z | right after a correction | brings back the sentence as typed; it is not corrected again in this field |

Every other key goes to the application, and Ctrl+Tab and Escape do too when no suggestion is shown. On a layout
whose letters are not Latin (Arabic, Cyrillic, Greek…), Ctrl+Z is the key in the Z position of a QWERTY keyboard, as
in browsers.
