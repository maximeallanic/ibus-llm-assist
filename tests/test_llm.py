"""LlmClient against a fake OpenAI-compatible server: answers, cancellation, server down, prompt wording."""
import json
import socket
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from gi.repository import GLib

from tests import _path  # noqa: F401
from llm_assist.llm import OPENAI, LlmClient, ServerConfig, correction_max_tokens


class FakeServer:
    def __init__(self, answer: str, delay: float = 0.0, stop_type: str = 'eos', finish_reason: str = 'stop'):
        self.stop_type = stop_type
        self.bodies: list[dict] = []
        self.paths: list[str] = []
        self.headers: list[dict] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                outer.bodies.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                outer.headers.append(dict(self.headers))
                time.sleep(delay)
                outer.paths.append(self.path)
                if self.path == '/apply-template':
                    user = outer.bodies[-1]['messages'][-1]['content']
                    payload = json.dumps({'prompt': f'<turn>{user}<model>'}).encode()
                elif self.path == '/completion':
                    payload = json.dumps({'content': answer, 'stop_type': outer.stop_type}).encode()
                else:
                    payload = json.dumps({'choices': [{'message': {'role': 'assistant', 'content': answer},
                                                       'finish_reason': finish_reason}]}).encode()
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def client(url: str, **kwargs) -> LlmClient:
    return LlmClient(ServerConfig(url, **kwargs))


def closed_port() -> int:
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class LlmClientTest(unittest.TestCase):
    def call(self, client: LlmClient, method: str, *args, cancel_after: float | None = None):
        loop = GLib.MainLoop()
        result = {}

        def done(text):
            result['text'] = text
            loop.quit()

        cancellable = getattr(client, method)(*args, done)
        if cancel_after is not None:
            GLib.timeout_add(int(cancel_after * 1000), lambda: cancellable.cancel() or False)
        GLib.timeout_add(5000, loop.quit)
        loop.run()
        self.assertIn('text', result, 'on_done was never called')
        return result['text']

    def test_complete_returns_text_cut_at_sentence_end(self):
        server = FakeServer(' the rain. And')
        self.addCleanup(server.close)
        self.assertEqual(self.call(client(server.url), 'complete', 'Here comes'), ' the rain.')

    def test_correct_returns_sentence(self):
        server = FakeServer('Il a été.')
        self.addCleanup(server.close)
        self.assertEqual(self.call(client(server.url), 'correct', '', 'Il a ete.'), 'Il a été.')

    def test_correction_cut_by_token_limit_is_no_answer(self):
        server = FakeServer('Il a', finish_reason='length')
        self.addCleanup(server.close)
        self.assertIsNone(self.call(client(server.url), 'correct', '', 'Il a ete tres content.'))

    def test_cancel_yields_none(self):
        server = FakeServer('late', delay=2)
        self.addCleanup(server.close)
        self.assertIsNone(self.call(client(server.url), 'complete', 'x', cancel_after=0.05))

    def test_server_down_yields_none(self):
        client = LlmClient(ServerConfig(f'http://127.0.0.1:{closed_port()}'))
        self.assertIsNone(self.call(client, 'complete', 'x'))

    def test_complete_prefills_model_turn_with_the_text(self):
        server = FakeServer(' votre aide')
        self.addCleanup(server.close)
        self.assertEqual(self.call(client(server.url), 'complete', 'Merci pour'), ' votre aide')
        self.assertEqual(server.paths, ['/apply-template', '/completion'])
        system, user = server.bodies[0]['messages']
        self.assertIn('language of the text', system['content'])
        self.assertEqual(user['content'], 'Merci pour')
        self.assertEqual(server.bodies[1]['prompt'], '<turn>Merci pour<model>Merci pour')

    def test_complete_cut_by_token_limit_ends_on_a_word(self):
        server = FakeServer(' a short sto', stop_type='limit')
        self.addCleanup(server.close)
        self.assertEqual(self.call(client(server.url), 'complete', 'Write'), ' a short')

    def test_complete_stops_at_line_break(self):
        server = FakeServer('します\n\nどのような')
        self.addCleanup(server.close)
        self.assertEqual(self.call(client(server.url), 'complete', 'よろしくお願い'), 'します')

    def test_correction_prompt_names_no_language_and_keeps_user_text_apart(self):
        server = FakeServer('ok')
        self.addCleanup(server.close)
        self.call(client(server.url), 'correct', 'Avant.', 'Il a ete.')
        messages = server.bodies[0]['messages']
        self.assertIn('language of the text', messages[0]['content'])
        self.assertNotIn('ete', messages[0]['content'])
        self.assertEqual([m['content'] for m in messages[1:]], ['Avant.', 'Il a ete.'])

    def test_correction_room_grows_with_the_bytes_of_the_sentence(self):
        server = FakeServer('ok')
        self.addCleanup(server.close)
        sentence = 'ሰላም ነው። ' * 30   # Ethiopic: three bytes per character, often one token per byte
        self.call(client(server.url), 'correct', '', sentence)
        self.assertEqual(server.bodies[0]['max_tokens'], correction_max_tokens(sentence))
        self.assertGreater(correction_max_tokens(sentence), len(sentence.encode()))

    def test_model_and_key_are_sent_when_set(self):
        server = FakeServer('ok')
        self.addCleanup(server.close)
        self.call(client(server.url, model='my-model', api_key='secret'), 'correct', '', 'x.')
        self.assertEqual(server.bodies[0]['model'], 'my-model')
        self.assertEqual(server.headers[0]['Authorization'], 'Bearer secret')

    def test_no_model_nor_key_by_default(self):
        server = FakeServer('ok')
        self.addCleanup(server.close)
        self.call(client(server.url), 'correct', '', 'x.')
        self.assertNotIn('model', server.bodies[0])
        self.assertNotIn('Authorization', server.headers[0])

    def test_openai_completion_continues_the_assistant_message(self):
        server = FakeServer(' votre aide. Et')
        self.addCleanup(server.close)
        self.assertEqual(self.call(client(server.url, api=OPENAI), 'complete', 'Merci pour'), ' votre aide.')
        self.assertEqual(server.paths, ['/v1/chat/completions'])
        body = server.bodies[0]
        self.assertEqual(body['messages'][-1], {'role': 'assistant', 'content': 'Merci pour'})
        self.assertTrue(body['continue_final_message'])
        self.assertFalse(body['add_generation_prompt'])

    def test_openai_completion_drops_an_echoed_prefix(self):
        server = FakeServer('Merci pour votre aide')
        self.addCleanup(server.close)
        self.assertEqual(self.call(client(server.url, api=OPENAI), 'complete', 'Merci pour'), ' votre aide')

    def test_openai_completion_cut_by_token_limit_ends_on_a_word(self):
        server = FakeServer(' a short sto', finish_reason='length')
        self.addCleanup(server.close)
        self.assertEqual(self.call(client(server.url, api=OPENAI), 'complete', 'Write'), ' a short')

    def test_invalid_endpoint_yields_none(self):
        self.assertIsNone(self.call(client('not a url'), 'complete', 'x'))


if __name__ == '__main__':
    unittest.main()
