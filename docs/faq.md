# FAQ

**Does anything I type leave my computer?**
Not with the default setup: the model runs on 127.0.0.1. See [privacy.md](privacy.md).

**Which languages?**
Any language you type with a keyboard layout and the model writes well. No setting: the engine follows the language of
the text. Input-method languages (Chinese, Japanese, Korean…) are not supported yet ([compatibility](compatibility.md)).

**Why Ctrl+Tab and not Tab?**
Tab already means something in most fields (focus, indentation, completion). Ctrl+Tab is free in text fields, and goes
to the application (switching tabs) whenever no suggestion is shown.

**Why does it replace my keyboard layout in the input sources?**
IBus runs one engine at a time, and that engine decides the layout. So the engine stands in for your layout and keeps
its keys: you type exactly as before. `ibus-llm-assist disable` puts the plain layouts back.

**Can I use another model?**
Yes, any instruction-tuned chat model served by llama-server; point `endpoint` at it, or replace the model path in the
server unit with `systemctl --user edit ibus-llm-assist-server`. Other OpenAI-compatible servers work for corrections;
for suggestions that mode is experimental ([configuration](configuration.md#other-servers)).

**How much memory and power does it use?**
About 5 GB while the model is loaded; it unloads after five idle minutes. Each suggestion is a short burst of GPU work
(well under a second on an integrated Intel GPU).

**Why Gemma 4 E2B?**
Among the models compared, it was the fastest that stayed reliable in every language of the [benchmarks](benchmarks.md),
and its licence (Apache 2.0) is permissive.

**Is it a spell checker?**
No dictionary is involved: the model reads the whole sentence, so it fixes agreement and wrong-but-real words too, and
it can also miss things a dictionary would catch. A guard drops any answer that changes more than 30 % of the
sentence, so it does not rewrite your style.

**Does it work in Flatpak applications?**
Yes for GTK 4 applications on Wayland, which talk to the compositor's text-input protocol, not to IBus directly.

**Why is the menu label "English (English (US), with suggestions)"?**
GNOME Shell writes the language of an IBus engine before its name. The name keeps the layout so that the same engine
list reads well in `ibus-setup` and in Settings.

**Can I build a package?**
`./install.sh --destroot DIR --no-deps --prefix /usr` stages the system files under `DIR` with nothing else done; the
local server stays a per-user setup.
