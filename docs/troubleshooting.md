# Troubleshooting

Start with:

```sh
ibus-llm-assist status
```

It checks each link of the chain and says what to do for each failure. The sections below follow its messages.

## "IBus component missing" or "Settings schema … not found"

The engine is not installed, or only partly. Run `./install.sh` again; `./verify.sh` lists the installed files that
changed or went missing.

## "IBus is not running"

GNOME starts IBus with the session. Log out and back in. Elsewhere: `ibus-daemon -drx`.

## "IBus lists none of the engines"

IBus builds its engine list from a cache:

```sh
ibus write-cache && ibus restart
```

The list comes from your input sources: an engine exists for each keyboard layout you have. Add the layout in
Settings > Keyboard first, then `ibus-llm-assist enable`.

## "No input source uses the engine"

```sh
ibus-llm-assist enable
```

## "GNOME Shell ignores the layout variant of IBus engines"

Your layout has a variant (`us+intl`…) and your GNOME Shell would type it with the plain layout. Either install the
[Shell patch](patches.md), or keep that layout plain: `ibus-llm-assist disable`, then `ibus-llm-assist enable --layout`
with your other layouts.

## "GTK_IM_MODULE=… in the session"

A `GTK_IM_MODULE` other than `ibus` (often `simple` or `xim`, set in `~/.config/environment.d/`, `~/.profile` or
`/etc/environment`) makes GTK applications bypass IBus, so the engine sees nothing they type. Remove the line, then log
out and back in. On GNOME Wayland, GTK needs no `GTK_IM_MODULE` at all.

## "No language model server at …"

- With the installer's server: `systemctl --user status ibus-llm-assist-server` and
  `journalctl --user -u ibus-llm-assist-server`. A failure at start is usually a missing Vulkan loader
  (`libvulkan.so.1`: install `libvulkan1`, `vulkan-loader` or `vulkan-icd-loader`) or a full memory (the unit is capped
  at 8 GB).
- With your own server: check the `endpoint` setting (base URL, without `/v1`) and that
  `curl http://HOST:PORT/v1/models` answers.

## No suggestion shows

- The first suggestion after five idle minutes comes late: the server reloads the model.
- Suggestions come only at the end of a word, after the pause (`pause-ms`), with the cursor at a word boundary and no
  selection.
- Not in password, PIN or private fields, nor in terminals.
- The Suggestions switch in the keyboard menu is off.
- With `server-api openai`, see [other servers](configuration.md#other-servers).
- The application does not report the text around the cursor: some toolkits do not ([compatibility](compatibility.md)).

## The suggestion looks like typed text

You added `textview > preedit.prediction` to `gtk.css` without the [GTK patch](patches.md): keep only
`text > preedit.prediction` ([configuration](configuration.md#look-of-the-suggestion)).

## Dead keys or Compose stopped working

The engine composes them like IBus's xkb engines. If an accent comes out as two characters, the layout of the engine
is not the one you expect: check it with `ibus engine` (it prints `llm-assist:<layout>`) and the variant message
above.

## A correction changed my meaning

Press Ctrl+Z right away: the sentence comes back as typed and is not corrected again in this field. If it happens
often in your language, a bigger model helps ([configuration](configuration.md#another-llama-server)), or turn
Corrections off in the keyboard menu.

## Ctrl+Tab switches tabs instead

When no suggestion is shown, Ctrl+Tab goes to the application, as always.

## Logs

The engine writes to the journal of your session, through IBus; its lines start with `ibus-llm-assist:`. It logs no
text you type.

```sh
journalctl --user -b | grep -i ibus-llm-assist
```
