# Compatibility

## Desktop

| | Status |
|---|---|
| GNOME 51 on Wayland | tested (Debian testing) |
| GNOME 46 to 50 | should work, untested; layouts with a variant would need the [Shell patch](patches.md) adapted |
| GNOME on X11 | untested |
| KDE Plasma, other desktops with IBus | add the engine with `ibus-setup`; `ibus-llm-assist enable` only edits GNOME input sources; untested |

## Look of the suggestion by version

The engine marks the suggestion as a *prediction*, and the desktop decides how it looks. Two versions decide it:

- **IBus 1.5.33** added the "hint" attribute (`IBUS_ATTR_TYPE_HINT`) that names the role of pre-edit text. The engine
  sends the prediction hint when the installed IBus has it. With an older IBus it sends the form a prediction had
  before: the grey foreground colour `#7F7F7F` of ibus-typing-booster, which IBus 1.5.33 itself converts to and from
  the prediction hint.
- **GNOME Shell 51** is the first to pass pre-edit hints on to applications. GNOME Shell 50 and earlier drop every
  pre-edit style, so applications draw the suggestion as plain pre-edit text: GTK 4 underlines it.

| IBus | GNOME Shell | The suggestion in GTK 4 |
|---|---|---|
| 1.5.33 or later | 51 or later | ghost text: the `preedit.prediction` CSS node, italic by default, translucent with the [CSS rule](configuration.md#look-of-the-suggestion) |
| 1.5.33 or later | 50 or earlier | underlined, at full opacity |
| 1.5.26 to 1.5.32 | 50 or earlier | underlined, at full opacity |

Applications that draw IBus colours themselves (the IBus input modules of GTK 3 and Qt, IBus's own Wayland client
on other desktops) show the older form in grey; untested. Accepting, dismissing and correcting work the same in
every row.

What the distributions ship (2026-10-20):

| Distribution | IBus | GNOME Shell | Suggestion |
|---|---|---|---|
| Debian testing (forky) | 1.5.35~rc1 | 51.0 | ghost text (tested) |
| Arch | 1.5.34 | 51.1 | ghost text |
| Fedora 44 | 1.5.34~rc1 | 50.6 | underlined |
| Fedora 43 | 1.5.33 | 49.10 | underlined |
| Debian 13 (trixie) | 1.5.32 | 48.7 | underlined |
| Ubuntu 24.04 | 1.5.29 | 46.0 | underlined |
| Debian 12 (bookworm) | 1.5.27 | 43.9 | underlined |
| Ubuntu 22.04 | 1.5.26 | 42.9 | underlined |

The unit tests run on IBus 1.5.26, 1.5.29 and 1.5.35; the desktop is tested on Debian testing only.

## Applications

The engine works in applications that talk to IBus and report the text around the cursor ("surrounding text").

| Application | Suggestion | Correction |
|---|---|---|
| GTK 4 (Files, Text Editor, Settings…) | ghost text; translucent with the [CSS rule](configuration.md#look-of-the-suggestion), in multi-line fields only with the [GTK patch](patches.md). Underlined before IBus 1.5.33 and GNOME 51 ([above](#look-of-the-suggestion-by-version)) | yes |
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
