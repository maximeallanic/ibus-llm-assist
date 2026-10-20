# GitHub metadata

What to paste into the repository settings when it is created. Nothing here is applied automatically.

## Description (297 characters, limit 350)

> IBus input method for Linux that suggests the rest of your sentence inline (Ctrl+Tab accepts) and corrects each
> sentence you finish, in your apps and in any language the model writes. Uses a local LLM (llama.cpp + Gemma 4 E2B
> on 127.0.0.1): nothing you type leaves your computer. GNOME on Wayland.

Every part of it is backed by the repository: inline suggestion and Ctrl+Tab (`docs/how-it-works.md`), sentence
correction, language-neutral engine (`docs/compatibility.md`), local server on 127.0.0.1 (`docs/privacy.md`), GNOME 51
on Wayland as the tested desktop.

## Website field

Leave empty, or point it at `docs/index.md` once a docs site exists. The README is the landing page.

## Topics (12)

`ibus` `input-method` `gnome` `wayland` `linux` `autocomplete` `text-prediction` `grammar-checker` `local-llm`
`llama-cpp` `gemma` `privacy`

`ibus`, `input-method`, `gnome` and `linux` are where Linux users browse; `autocomplete`, `text-prediction` and
`grammar-checker` are what people search for; `local-llm`, `llama-cpp` and `gemma` bring the r/LocalLLaMA crowd;
`privacy` is the main promise. Left out on purpose: `ai` and `llm` alone (crowded and vague), `copilot` and
`grammarly` (other people's trademarks), `spell-checker` (it has no dictionary).

## Social preview

`docs/marketing/social-preview.png`, 1280×640, under 1 MB. Upload it in Settings → General → Social preview.

The three strips are unretouched crops of `screenshots/en-suggestion.png`, `fr-suggestion.png` and
`ar-suggestion.png`; the rest is drawn by `docs/marketing/social-preview.svg`. librsvg only reads images next to or
below the SVG, so render it from the repository root:

```sh
sed 's#\.\./\.\./screenshots/#screenshots/#' docs/marketing/social-preview.svg > social-preview.tmp.svg
rsvg-convert -w 1280 -h 640 social-preview.tmp.svg -o docs/marketing/social-preview.png
rm social-preview.tmp.svg
```

## Name check

Recommendation: **keep `ibus-llm-assist`.**

For it:

- It says where it lives (IBus, so Linux users know at once how it integrates) and what powers it. Searching
  "ibus llm" on GitHub finds it.
- It is free on GitHub. The nearest names are `ibus-llm-suggest` (feeds LLM-generated phrases into
  ibus-typing-booster's database every hour, through a cloud or local OpenAI-compatible API) and
  `ibus_llm_pinyin_input` (Chinese pinyin). Neither does inline sentence completion, but `ibus-llm-suggest` is close
  enough in name that the README and posts should say what this one does in the first line, which they do.
- The name is already baked into the GSettings schema (`io.github.maximeallanic.IBusLlmAssist`), the engine names
  (`llm-assist:fr`), the command, the systemd unit and the install paths. Renaming means a migration for nothing.

Against it:

- "llm" is jargon to many GNOME users and a red flag to people tired of AI products; "assist" does not say
  autocomplete. The tagline carries that load: lead every post with what it does, not the name.

Alternatives considered, none better enough to rename:

| Name | Why not |
|---|---|
| ibus-ghostwriter | ghostwriter is an established KDE Markdown editor |
| ibus-ghosttext | GhostText is an existing browser extension |
| ibus-predict | generic, says nothing about correction or local models |
| ibus-autocomplete | accurate but undistinguished; collides with typing-booster's pitch |
| a brand name (e.g. "Murmur") | memorable, but loses the "IBus" search hit, which is how people find input methods |

If a friendlier display name is ever wanted, it can head the README while the repository and package names stay.
