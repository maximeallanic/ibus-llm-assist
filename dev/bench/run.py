"""Bench of the engine's model calls against a real server: completion latency and language, correction accuracy,
untouched correct sentences, and how the rephrasing guard treats real corrections. The cases are in cases.py; the
judge that rates the completions is the same model, so its figures are indicative only.

    python3 dev/bench/run.py [--endpoint URL] [--server-api llama.cpp|openai] [--model NAME] [--out results.json]

On a busy machine, run it in its own memory-capped unit, with nothing else on the GPU:
    systemd-run --user --scope -p MemoryHigh=4G -p MemoryMax=6G python3 dev/bench/run.py
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from gi.repository import GLib

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from cases import COMPLETIONS, CORRECT, FAULTY  # noqa: E402
from llm_assist.boundaries import graphemes  # noqa: E402
from llm_assist.correction import MAX_EDIT_RATIO, _distance, is_light_edit  # noqa: E402
from llm_assist.llm import DEFAULT_ENDPOINT, LLAMA_CPP, OPENAI, LlmClient, ServerConfig  # noqa: E402

# Bench-only judge, never used by the engine: the model says whether two texts share a language.
JUDGE = ('Answer with one word, yes or no: is the second text written in the same language as the first? '
         'First: {a!r}. Second: {b!r}.')
CONTINUES = ('Answer with one word, yes or no: is {b!r} a natural continuation of the unfinished text {a!r}, '
             'as if the same person kept writing, and not a reply to it nor a repetition of it?')


def call(fn, *args) -> tuple[str | None, float]:
    loop, out = GLib.MainLoop(), {}
    start = time.monotonic()

    def done(text):
        out['text'], out['t'] = text, time.monotonic() - start
        loop.quit()

    fn(*args, done)
    loop.run()
    return out['text'], out['t']


def judge(client: LlmClient, question: str) -> bool:
    text, _ = call(client.ask, 'You are a careful judge.', question, 3)
    return bool(text) and text.strip().lower().startswith('yes')


def ratio(a: str, b: str) -> float:
    ga = graphemes(a)
    return _distance(ga, graphemes(b)) / len(ga)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    parser.add_argument('--server-api', default=LLAMA_CPP, choices=(LLAMA_CPP, OPENAI))
    parser.add_argument('--model', default='')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    client = LlmClient(ServerConfig(endpoint=args.endpoint, api=args.server_api, model=args.model))
    call(client.complete, 'Warm-up')  # loads the model if llama-server put it to sleep
    report, ok = {}, True
    for lang in COMPLETIONS:
        rows, times = [], []
        # Completions first, judges after: a judge call in between would evict the prompt cache and skew timing.
        for before in COMPLETIONS[lang]:
            text, t = call(client.complete, before)
            times.append(t)
            rows.append({'before': before, 'completion': text, 's': round(t, 2)})
        for row in rows:
            before, text = row['before'], row['completion']
            row['same_language'] = bool(text) and judge(client, JUDGE.format(a=before, b=before + text))
            row['continues'] = bool(text) and judge(client, CONTINUES.format(a=before, b=text))
        fixes = []
        for faulty, accepted in FAULTY[lang]:
            text, t = call(client.correct, '', faulty)
            got = (text or '').strip()
            fixes.append({'faulty': faulty, 'got': got, 's': round(t, 2), 'right': got in accepted,
                          'guard_accepts': is_light_edit(faulty, got) if got else False,
                          'expected_ratio': round(min(ratio(faulty, a) for a in accepted), 3)})
        kept = []
        for sentence in CORRECT[lang]:
            text, _ = call(client.correct, '', sentence)
            kept.append({'sentence': sentence, 'got': (text or '').strip(),
                         'unchanged': (text or '').strip() == sentence})
        summary = {
            'completion_median_s': round(statistics.median(times), 2),
            'completion_p90_s': round(sorted(times)[int(0.9 * (len(times) - 1))], 2),
            'completion_empty': sum(not r['completion'] for r in rows),
            'judge_same_language': sum(r['same_language'] for r in rows) / len(rows),
            'judge_continues': sum(r['continues'] for r in rows) / len(rows),
            'corrections_right': sum(f['right'] for f in fixes) / len(fixes),
            'guard_accepts_right': all(f['guard_accepts'] for f in fixes if f['right']),
            'max_expected_ratio': max(f['expected_ratio'] for f in fixes),
            'correct_unchanged': sum(k['unchanged'] for k in kept) / len(kept),
        }
        # The judge figures are indicative only: the E2B judge rejects plainly good continuations (2026-10-18).
        ok &= (summary['corrections_right'] >= 0.9 and summary['correct_unchanged'] == 1
               and summary['completion_median_s'] <= 1.5 and summary['guard_accepts_right'])
        report[lang] = {'summary': summary, 'completions': rows, 'corrections': fixes, 'unchanged': kept}
        print(lang, json.dumps(summary, ensure_ascii=False))
    print(f'MAX_EDIT_RATIO = {MAX_EDIT_RATIO}; verdict: {"PASS" if ok else "FAIL"}')
    if args.out:
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
