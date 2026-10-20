# Privacy

## What the engine sees

Like every input method, the engine receives the keys you type in the applications that use IBus, and the text
around the cursor that the application reports.

## What it sends, and where

Only to the server in the `endpoint` setting (default `http://127.0.0.1:8033`, this computer):

- for a suggestion: the text before the cursor, from the start of the third sentence before the current one;
- for a correction: the finished sentence and the sentence before it.

Nothing else: no text after the cursor, no window or application name, no identifier. The engine keeps nothing,
writes nothing to disk and logs no text (its journal messages say only that a server failed or answered with an
error).

## The local server

The installer's server is llama.cpp's `llama-server`, bound to 127.0.0.1 so that other machines cannot reach it.
Web pages cannot read its answers either: its CORS answer allows only `localhost` origins, without credentials (by
default llama-server lets any web page you visit send it prompts and read the answers). It writes nothing to disk;
it keeps the last request in memory to answer the next one faster, until it unloads the model.

The installer downloads llama.cpp from its GitHub releases and the model from Hugging Face, at fixed versions, and
checks their sha256 before using them.

## Another server

If you set `endpoint` to another machine, everything above goes there, including over plain `http`. The engine
accepts it because you may run the model on your own server, but `ibus-llm-assist status` warns about any endpoint
that is not a loopback address. An API key, if the server needs one, is read from a file only you can read
([configuration](configuration.md#api-key)).

## Where it never runs

Password and PIN fields, fields marked private or hidden by the application, terminals. The Suggestions and
Corrections switches in the keyboard menu turn each feature off everywhere; `ibus-llm-assist disable` removes the
engine from your input sources.
