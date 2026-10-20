# Benchmarks

`dev/bench/run.py` measures the model calls of the engine against a real server: for each language, 8 text beginnings
to complete, 8 sentences with a mistake (with the accepted corrections) and 4 correct sentences that must come back
unchanged. The cases are in `dev/bench/cases.py`, in four scripts and both writing directions.

```sh
python3 dev/bench/run.py [--endpoint URL] [--server-api llama.cpp|openai] [--model NAME] [--out results.json]
```

Verdict: at least 90 % right corrections, no correct sentence changed, a median suggestion time of at most 1.5 s, and
the rephrasing guard accepting every right correction.

## Gemma 4 E2B (q4_0), llama.cpp, Intel Iris Xe (i7-1265U), on mains power

Quiet machine, 2026-10-18:

| Language | Suggestion median / p90 | No suggestion | Right corrections | Correct sentences kept |
|---|---|---|---|---|
| French | 0.83 s / 0.92 s | 0/8 | 8/8 | 4/4 |
| English | 0.69 s / 1.15 s | 1/8 | 8/8 | 4/4 |
| Japanese | 0.65 s / 0.85 s | 0/8 | **7/8** | 4/4 |
| Arabic | 0.97 s / 1.40 s | 1/8 | 8/8 | 4/4 |

Same machine with several other GPU jobs running, 2026-10-20 (the accuracy is the same; the times show what a busy
GPU does):

| Language | Suggestion median / p90 | No suggestion | Right corrections | Correct sentences kept |
|---|---|---|---|---|
| French | 2.54 s / 3.22 s | 0/8 | 8/8 | 4/4 |
| English | 2.83 s / 4.32 s | 1/8 | 8/8 | 4/4 |
| Japanese | 2.01 s / 2.64 s | 0/8 | **7/8** | 4/4 |
| Arabic | 2.49 s / 3.38 s | 1/8 | 8/8 | 4/4 |

- **Japanese**: `明日わ休みです。` becomes `明日休みです。`: the model drops the wrong particle instead of replacing it by
  `は`. Readable, not right, and reproducible. A larger model fixes it.
- **No suggestion**: now and then the model returns nothing usable for a beginning; the engine then shows nothing.
- **Rephrasing guard**: the expected corrections change at most 17 % of the graphemes (French 13.6 %, English 16.7 %,
  Japanese 14.3 %, Arabic 15.4 %); the guard drops answers above 30 %.
- **Judge**: the bench also asks the model whether each suggestion is in the language of the text and continues it.
  A small model judging itself rejects plainly good continuations, so these figures are indicative and stay out of
  the verdict. The suggestions were also read by hand: natural, and in the language of the text.

## How a suggestion is asked for

Three forms were compared on these cases. A plain chat request makes the model *answer* the text ("Thank you so much
for" → "You're welcome"). The raw text alone makes it switch language on short beginnings. The chat template with the
text repeated at the start of the answer, which the model continues, is what the engine uses.

## End to end

`dev/e2e/run.sh` types into a real GTK 4 window in a nested GNOME Shell and checks the result (see
[development.md](development.md)). On 2026-10-20 it passed in English (`us`), French (`fr`, with dead keys) and Arabic
(`ara`, right to left, Ctrl+Z by key position).
