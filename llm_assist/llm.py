"""Client of the language model server, asynchronous and cancellable through libsoup 3.

Two server flavours:

- ``llama.cpp`` (default): llama.cpp's own server. A completion uses the model's chat template, fetched from the
  server (/apply-template), with the user's text written again at the start of the model's turn, then a raw
  continuation (/completion). A plain chat request makes the model *reply* to the text instead of continuing it,
  and a raw prompt with no template makes it drift to another language on short beginnings (see
  docs/benchmarks.md).
- ``openai``: any OpenAI-compatible server. Corrections use /v1/chat/completions as for llama.cpp. A completion
  sends the user's text as the start of the assistant's message and asks the server to continue that message
  (``continue_final_message``); a server that ignores it answers a reply instead of a continuation.

The instructions never name a language: the model is told to stay in the language of the text.
"""
import json
import logging
import math
from collections.abc import Callable
from dataclasses import dataclass, replace

import gi

gi.require_version('Soup', '3.0')
from gi.repository import Gio, GLib, Soup  # noqa: E402

from .boundaries import cut_at_sentence_end, trim_to_word_end  # noqa: E402

LOG = logging.getLogger('ibus-llm-assist')

LLAMA_CPP, OPENAI = 'llama.cpp', 'openai'
DEFAULT_ENDPOINT = 'http://127.0.0.1:8033'

# A suggestion is a few words: the cap bounds the latency. In a script the tokenizer splits finely, 16 tokens hold
# fewer characters; the suggestion is then shorter, never wrong (it is cut back to the last word end).
MAX_COMPLETION_TOKENS = 16

# Room for a corrected sentence. A byte-level tokenizer never needs more than one token per UTF-8 byte, so a cap
# derived from the byte length fits every script, where a fixed cap would cut long sentences in scripts that take
# several tokens per character. The 30 % margin matches the most a correction may change (correction.py).
_CORRECTION_TOKENS_PER_BYTE = 1.3
_CORRECTION_TOKENS_EXTRA = 16

COMPLETE_INSTRUCTIONS = (
    'The user sends an unfinished text they are typing. Write it out again and finish its current sentence '
    'naturally, in the language of the text. Never reply to it, never comment on it.')

CORRECT_INSTRUCTIONS = (
    'You proofread one sentence. Fix spelling, grammar, agreement, punctuation and accents, in the language of '
    'the text, changing as little as possible: replace a wrong word by the right one rather than deleting it; '
    'never rephrase, never translate, never add or remove anything else. Reply with only the sentence, '
    'corrected, or unchanged if it is already correct. When two user messages are given, the first is earlier '
    'text, for context only: neither correct nor repeat it.')

OnDone = Callable[[str | None], None]


@dataclass(frozen=True)
class ServerConfig:
    endpoint: str = DEFAULT_ENDPOINT
    api: str = LLAMA_CPP
    model: str = ''
    api_key: str = ''


def correction_max_tokens(sentence: str) -> int:
    return math.ceil(len(sentence.encode('utf-8')) * _CORRECTION_TOKENS_PER_BYTE) + _CORRECTION_TOKENS_EXTRA


def _continuation(response: dict) -> str:
    # Cut by the token limit, the last word may be unfinished.
    text = response['content']
    return trim_to_word_end(text) if response.get('stop_type') == 'limit' else text


class LlmClient:
    def __init__(self, config: ServerConfig | None = None) -> None:
        self._session = Soup.Session()
        self.configure(config or ServerConfig())

    def configure(self, config: ServerConfig) -> None:
        if config.api not in (LLAMA_CPP, OPENAI):
            LOG.warning('Unknown server flavour %r, using %s', config.api, LLAMA_CPP)
            config = replace(config, api=LLAMA_CPP)
        self._config = config
        self._base = config.endpoint.rstrip('/')
        self._reported_down = False
        try:
            self._valid = GLib.Uri.parse(self._base, GLib.UriFlags.NONE).get_scheme() in ('http', 'https')
        except GLib.Error:
            self._valid = False

    def complete(self, before: str, on_done: OnDone) -> Gio.Cancellable:
        """Likely continuation of before, cut at its first sentence end."""
        cancellable = Gio.Cancellable()

        def done(text: str | None) -> None:
            on_done(cut_at_sentence_end(text) if text else None)

        messages = [{'role': 'system', 'content': COMPLETE_INSTRUCTIONS}, {'role': 'user', 'content': before}]
        if self._config.api == OPENAI:
            self._complete_openai(messages, before, done, cancellable)
            return cancellable

        def templated(head: str | None) -> None:
            # The model's own chat template, from the server: no template token is written here.
            if head is None:
                on_done(None)
                return
            body = {'prompt': head + before, 'n_predict': MAX_COMPLETION_TOKENS, 'temperature': 0.2,
                    'cache_prompt': True}
            self._post('/completion', body, _continuation, done, cancellable)

        self._post('/apply-template', {'messages': messages}, lambda r: r['prompt'], templated, cancellable)
        return cancellable

    def _complete_openai(self, messages: list[dict], before: str, done: OnDone,
                         cancellable: Gio.Cancellable) -> None:
        body = self._chat_body(messages + [{'role': 'assistant', 'content': before}], MAX_COMPLETION_TOKENS, 0.2)
        body.update(continue_final_message=True, add_generation_prompt=False)

        def extract(response: dict) -> str:
            choice = response['choices'][0]
            # Some servers answer the whole message, the prefix included.
            text = (choice['message']['content'] or '').removeprefix(before)
            return trim_to_word_end(text) if choice.get('finish_reason') == 'length' else text

        self._post('/v1/chat/completions', body, extract, done, cancellable)

    def correct(self, context: str, sentence: str, on_done: OnDone) -> Gio.Cancellable:
        """sentence corrected; context is the text before it, given to the model for meaning only."""
        texts = [context, sentence] if context.strip() else [sentence]
        messages = ([{'role': 'system', 'content': CORRECT_INSTRUCTIONS}]
                    + [{'role': 'user', 'content': t} for t in texts])
        body = self._chat_body(messages, correction_max_tokens(sentence), 0.0)

        def answer(response: dict) -> str | None:
            # Cut by the token limit, a correction lacks the end of the sentence: applying it would delete it.
            choice = response['choices'][0]
            return choice['message']['content'] if choice.get('finish_reason') == 'stop' else None

        return self._post('/v1/chat/completions', body, answer, on_done)

    def ask(self, instructions: str, text: str, max_tokens: int, on_done: OnDone) -> Gio.Cancellable:
        """A plain chat answer (the bench's judge uses it, the engine does not)."""
        body = self._chat_body([{'role': 'system', 'content': instructions}, {'role': 'user', 'content': text}],
                               max_tokens, 0.0)
        return self._post('/v1/chat/completions', body, lambda r: r['choices'][0]['message']['content'], on_done)

    def _chat_body(self, messages: list[dict], max_tokens: int, temperature: float) -> dict:
        body = {'messages': messages, 'max_tokens': max_tokens, 'temperature': temperature, 'stream': False}
        if self._config.model:
            body['model'] = self._config.model
        return body

    def _post(self, path: str, body: dict, extract: Callable[[dict], str | None], on_done: OnDone,
              cancellable: Gio.Cancellable | None = None) -> Gio.Cancellable:
        cancellable = cancellable or Gio.Cancellable()
        if not self._valid:
            self._report_down('not an http or https URL')
            GLib.idle_add(lambda: on_done(None) or False)
            return cancellable
        msg = Soup.Message.new('POST', self._base + path)
        if self._config.api_key:
            msg.get_request_headers().append('Authorization', f'Bearer {self._config.api_key}')
        msg.set_request_body_from_bytes('application/json', GLib.Bytes.new(json.dumps(body).encode()))

        def finished(session: Soup.Session, result: Gio.AsyncResult) -> None:
            on_done(self._read(session, result, msg, extract))

        self._session.send_and_read_async(msg, GLib.PRIORITY_DEFAULT, cancellable, finished)
        return cancellable

    def _read(self, session: Soup.Session, result: Gio.AsyncResult, msg: Soup.Message,
              extract: Callable[[dict], str | None]) -> str | None:
        try:
            data = session.send_and_read_finish(result).get_data()
        except GLib.Error as error:
            if not error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                self._report_down(error.message)
            return None
        if msg.get_status() != Soup.Status.OK:
            self._report_down(f'HTTP {msg.get_status()}')
            return None
        self._reported_down = False
        try:
            return extract(json.loads(data))
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
            LOG.warning('Unreadable answer from %s: %s', msg.get_uri().to_string(), error)
            return None

    def _report_down(self, reason: str) -> None:
        # Once per outage: the engine stays quiet while the server is away, the log says why.
        if not self._reported_down:
            LOG.warning('Language model server unreachable at %s: %s', self._base, reason)
            self._reported_down = True
