# Compatibility

## Desktop

| | Status |
|---|---|
| GNOME 51 on Wayland | tested (Debian testing) |
| GNOME 46 to 50 | should work, untested; layouts with a variant would need the [Shell patch](patches.md) adapted |
| GNOME on X11 | untested |
| KDE Plasma, other desktops with IBus | add the engine with `ibus-setup`; `ibus-llm-assist enable` only edits GNOME input sources; untested |

## Applications

The engine works in applications that talk to IBus and report the text around the cursor ("surrounding text").

| Application | Suggestion | Correction |
|---|---|---|
| GTK 4 (Files, Text Editor, Settings…) | ghost text; translucent with the [CSS rule](configuration.md#look-of-the-suggestion), in multi-line fields only with the [GTK patch](patches.md) | yes |
| Chrome 155 (Wayland) | underlined, at full opacity: Chromium ignores the "prediction" hint | yes |
| GTK 3, Qt, Electron, Firefox | depends on their IBus or text-input-v3 support; untested | untested |
| Terminals | off on purpose | off |
| Password, PIN, private fields | off on purpose | off |

## Languages

Every language the model writes well, with no setting: the engine has no word list, rule or threshold tied to a
language or a script.

- **Layouts typed directly** (Latin, Cyrillic, Greek, Arabic, Hebrew, Armenian, Georgian, Devanagari, Thai…): yes.
  Right-to-left text works (tested in Arabic).
- **Languages typed through an input method** (Chinese, Japanese, Korean, Vietnamese with Telex…): not yet. IBus runs
  one engine at a time, and this one does not compose; you would have to choose between your input method and this
  engine. The model itself handles Japanese ([benchmarks](benchmarks.md)): what is missing is an engine that chains to
  an input method.
- **Thai, Lao, Khmer, Burmese**: suggestions after a space or punctuation only. These scripts write no space between
  words, and Pango finds word ends in them only with a dictionary it does not ship, so the engine cannot tell it stands
  at the end of a word.
- **Quality** depends on the model. Gemma 4 E2B is small: excellent in French, English and Arabic in the bench, weaker
  in Japanese corrections. A bigger model on the same server fixes that at the cost of speed.
- **Interface**: the installer and the engine's messages are in English and French. Other languages fall back to
  English. Translations are welcome (`po/`, see [development.md](development.md)).

## Keyboard layouts

Any layout of xkeyboard-config. Layouts with a variant (`us+intl`, `de+neo`, `fr+bepo`…) need the
[Shell patch](patches.md); without it the installer leaves them as they are and says why.

## Hardware for the local server

| | |
|---|---|
| x86_64 with a Vulkan GPU (Intel, AMD, NVIDIA) | tested on Intel Iris Xe: suggestion in 0.7 to 1 s |
| x86_64 without Vulkan | runs on the processor, slower |
| aarch64 | the pinned llama.cpp build exists; untested |
| Memory | about 5 GB while the model is loaded |
