# Launch posts

Drafts for the first public announcement. Nothing has been posted. Every claim below is in the README, `docs/` or
`screenshots/`; keep it that way when editing.

## Read this first: these are drafts to rewrite, not to paste

- **Hacker News** forbids generated or AI-edited text in posts and comments ("users should write their own text",
  [guidelines](https://news.ycombinator.com/newsguidelines.html)). The Show HN title can be used as is; the first
  comment below is a list of facts to say in your own words, around your own motivation.
- **r/LocalLLaMA**: its wiki (read through a mirror, the live page could not be fetched) bans posts that are mostly
  LLM-generated, treats the 1/10 self-promotion ratio as a guideline, and needs some comment and subreddit karma to
  post. Rewrite the draft in your voice and check the sidebar before posting.
- **r/linux and r/gnome**: their rules could not be fetched (Reddit blocks automated reads). Read each sidebar before
  posting: both usually expect the poster to take part in the community, not only announce.
- **Mastodon**: no central rule; your instance's rules apply. Norms: alt text on every image, CamelCase hashtags (read
  correctly by screen readers), no hashtag stuffing.
- Expect the question "was this written with AI?" Decide your answer before posting (see owner decisions at the end).

## Before posting

1. The repository is public, `scripts/release.sh 0.1.1` has pinned the release, the `v0.1.1` tag and release exist
   (the one-line installer downloads that release and refuses while none is pinned), CI is green.
2. The social preview is uploaded (`docs/marketing/github-metadata.md`).
3. Run the one-liner once on a clean user account or VM, so that the first reports are not about the install.
4. Post one venue at a time, when you can answer for the next two or three hours. Never ask anyone to upvote.

## r/LocalLLaMA

Flair: "Resources" or "Other", whichever the sidebar says fits a project.

**Title:** Gemma 4 E2B on llama.cpp as inline autocomplete and sentence correction in Linux apps (open-source IBus
engine)

**Body:**

> I wrote an IBus input method that puts a local model behind the keyboard on Linux. You pause, the rest of the
> sentence shows as grey ghost text after the cursor, Ctrl+Tab takes it. When you finish a sentence, it is corrected
> in place, Ctrl+Z puts it back. It runs in the apps that use IBus (GTK 4 and Chrome tested on GNOME 51).
>
> The parts this sub may find interesting:
>
> - **Default model**: Gemma 4 E2B q4_0 on llama-server (Vulkan build), bound to 127.0.0.1, unloaded after 5 idle
>   minutes (`--sleep-idle-seconds 300`). Among the models I compared it was the fastest that stayed reliable in
>   French, English, Japanese and Arabic.
> - **Getting a continuation, not an answer**: a plain chat request makes the model *reply* to the text ("Thank you so
>   much for" → "You're welcome"), and raw completion makes it switch language on short beginnings. What works: the
>   model's own chat template via `/apply-template`, an instruction to finish the sentence, the text as the user
>   message and the same text again as the start of the assistant turn, continued with `/completion`. 16 tokens max,
>   cut at the sentence end.
> - **Corrections that don't rephrase**: the answer is dropped if it changes more than 30 % of the sentence's
>   graphemes (Levenshtein over user-perceived characters, so a kana or an Arabic letter counts once). Real fixes in
>   the bench change at most 17 %.
> - **Latency** (bench in the repo, Iris Xe i7-1265U, mains power): suggestion median 0.65–0.97 s on a quiet machine,
>   2.0–2.8 s with other GPU jobs running. Corrections: 8/8 in FR/EN/AR, 7/8 in JA; correct sentences left alone 4/4.
>   8 cases per language, one machine: an order of magnitude, not a leaderboard. `dev/bench/run.py` runs it on yours.
> - **Not language-specific**: no word list or per-language rule; boundaries come from Pango (UAX #29).
> - **llama-server's default CORS** lets any web page you visit query it; the installed unit restricts it to
>   localhost origins.
>
> Where I need help: an OpenAI-compatible mode exists for Ollama/vLLM/LM Studio, but it is **experimental**, tested
> only against a stub. Suggestions need the server to continue a prefilled assistant message
> (`continue_final_message`, `add_generation_prompt: false`); if yours ignores that, suggestions read like replies.
> Reports welcome.
>
> Limits: GNOME on Wayland is the only tested desktop; languages typed through an input method (Chinese, Japanese,
> Korean…) can't use it yet; two optional GNOME Shell/GTK patches are needed for layouts with a variant and for
> translucent ghost text in multi-line fields.
>
> Repo (MIT): https://github.com/maximeallanic/ibus-llm-assist

Attach `screenshots/en-demo.gif` (or link it) as the first thing people see.

## r/gnome (or r/linux)

r/gnome is the better first venue: the audience uses IBus and the GNOME-specific details matter there. For r/linux,
keep the same text and drop the patch paragraph to one line.

**Title:** I made an IBus engine that suggests the rest of your sentence and fixes typos with a local model

**Body:**

> It's an input method, so it works in the apps that talk to IBus without a plugin per app: GTK 4 apps (Flatpak too)
> and Chrome, tested on GNOME 51 on Wayland. Pause while typing and the end of the sentence appears as ghost text,
> Ctrl+Tab accepts. Finish a sentence and spelling, grammar and accents are fixed in place, Ctrl+Z restores it. Two
> switches in the keyboard menu turn each part off.
>
> The model runs locally (llama.cpp + Gemma 4 E2B on 127.0.0.1, about 5 GB of memory while loaded, a Vulkan GPU
> helps). Nothing is sent anywhere else, and it stays off in password fields and terminals.
>
> It keeps your layout: the engine stands in for each input source and keeps its dead keys and Compose. It is not
> tied to a language: the recordings in the README are in English, French and Arabic (right to left).
>
> Two things on stock GNOME 51 needed small patches, shipped in the repo and optional: GNOME Shell drops the layout
> variant of IBus engines (`us+intl` types as `us`; a two-line fix in `keyboard.js`), and GtkTextView ignores the
> alpha of pre-edit colours (the ghost text is italic but opaque there). Neither is submitted upstream yet; if someone
> knows the right path for them, I'd like to hear it.
>
> Install is one line with a prompt before each step, or `./install.sh --dry-run` from a clone:
> https://github.com/maximeallanic/ibus-llm-assist

Attach `screenshots/en-demo.gif` and `screenshots/en-menu.png`.

## Show HN

**Title (80 characters, the limit):**

`Show HN: Ibus-llm-assist – local LLM autocomplete and corrections for Linux apps`

HN capitalises the first letter of a lowercase title; if that bothers you, use the variant
`Show HN: Local-LLM autocomplete and sentence correction in Linux apps, via IBus` (79).

**URL:** the GitHub repository.

**First comment** (post it right after submitting; write it yourself from these points):

> [YOUR MOTIVATION: why you built it, in two or three sentences of your own. For example what you missed on Linux,
> or what you tried before.]

Facts to cover, in your words:

- What it does: ghost-text completion after a pause (Ctrl+Tab), correction of each finished sentence (Ctrl+Z undoes),
  in apps that use IBus; GNOME 51 on Wayland tested.
- Why an input method: every IBus app already hands the IME its keystrokes and the text around the cursor, so one
  engine covers them without per-app plugins or a browser extension.
- Local by default: llama.cpp + Gemma 4 E2B on 127.0.0.1; it sends only the sentence being typed and up to three
  before it; keeps and logs nothing.
- Numbers with their conditions: median suggestion 0.65–0.97 s on a quiet Iris Xe laptop, 2.0–2.8 s with other GPU
  load; small bench, in the repo.
- The prompt finding (chat template + prefilled assistant turn, because a chat request *answers* the text).
- Honest limits: input-method languages not yet, optional patches for two GNOME/GTK gaps, OpenAI-compatible mode
  experimental.
- What feedback you want.

## Mastodon (474 characters as Mastodon counts them, a link counting 23; limit 500)

> I made an IBus input method that brings local-LLM autocomplete to Linux apps.
>
> Pause, and the rest of your sentence shows as ghost text; Ctrl+Tab takes it. Finish a sentence, and its typos are
> fixed in place; Ctrl+Z undoes. llama.cpp + Gemma 4 E2B on 127.0.0.1: nothing you type leaves the machine.
>
> Any language the model writes (demos in English, French, Arabic). Tested on GNOME 51, Wayland. MIT.
>
> https://github.com/maximeallanic/ibus-llm-assist
>
> #Linux #GNOME #FOSS #LocalLLM #LlamaCpp #Privacy

Attach `screenshots/en-demo.gif` with this alt text: "A text field: 'Thank you so much for' is typed, the grey
suggestion 'your help with this project.' appears and Ctrl+Tab accepts it; then 'I has a question about the
invoice.' is typed and corrected to 'I have a question about the invoice.'"

A French version for French-speaking instances can follow the same lines with `screenshots/fr-demo.gif`.

## Other venues

- **r/selfhosted** is about services you host; a desktop input method fits only through the "your own model server"
  angle. Skip it at launch, or post later in its weekly or "what are you working on" thread if it has one.
- **GNOME Discourse** (discourse.gnome.org) is the place to ask about upstreaming the two patches, which is a
  conversation, not an announcement.

## Owner decisions

- Your motivation for the HN first comment, and the final wording of every post (HN requires it to be yours).
- What to say if asked whether AI helped build the project.
- Which venue first, and the day: one at a time.
- Whether to submit the GNOME Shell and GTK patches upstream before or after launch; "not upstream yet" will be asked.
