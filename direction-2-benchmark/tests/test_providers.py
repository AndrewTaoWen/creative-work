"""Check request and reply handling offline, against each real SDK."""

import json
import unittest

from voicebench.providers import FatalGenerationError, GenerationError, Request

try:
    import anthropic
    import httpx2
    import openai
    from voicebench.providers.claude import FALLBACK_BETA, ClaudeProvider
    from voicebench.providers.openai import OpenAIProvider
except ImportError:
    anthropic = None

REQUEST = Request("model-x", "system text", "user text", "medium")


def fake_http(status, body, seen):
    def handle(request):
        seen.append(request)
        return httpx2.Response(status, json=body)

    return httpx2.Client(transport=httpx2.MockTransport(handle))


def claude_body(content, stop_reason="end_turn", iterations=None):
    return {
        "id": "msg_1", "type": "message", "role": "assistant", "model": "model-x",
        "content": content, "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 3, "output_tokens": 4, "iterations": iterations},
    }


@unittest.skipIf(anthropic is None, "needs the anthropic and openai packages")
class ClaudeTests(unittest.TestCase):
    def _provider(self, status, body, seen):
        client = anthropic.Anthropic(
            api_key="test", max_retries=0, http_client=fake_http(status, body, seen)
        )
        return ClaudeProvider(client)

    def test_request_shape(self):
        seen = []
        body = claude_body([{"type": "thinking", "thinking": "", "signature": "s"},
                            {"type": "text", "text": " Hello "}])
        reply = self._provider(200, body, seen).generate(REQUEST)
        self.assertEqual(reply.text, "Hello")
        self.assertFalse(reply.fell_back)
        sent = json.loads(seen[0].content)
        self.assertEqual(sent["fallbacks"], "default")
        self.assertEqual(sent["thinking"], {"type": "adaptive"})
        self.assertEqual(sent["output_config"], {"effort": "medium"})
        self.assertEqual(sent["system"], "system text")
        for name in ("temperature", "top_p", "top_k"):
            self.assertNotIn(name, sent)
        self.assertIn(FALLBACK_BETA, seen[0].headers["anthropic-beta"])

    def test_records_fallback(self):
        body = claude_body([{"type": "text", "text": "Hi"}], iterations=[
            {"type": "fallback_message", "input_tokens": 1, "output_tokens": 1}])
        self.assertTrue(self._provider(200, body, []).generate(REQUEST).fell_back)

    def test_refusal_and_truncation_are_not_output(self):
        for stop_reason in ("refusal", "max_tokens"):
            body = claude_body([{"type": "text", "text": "partial"}], stop_reason)
            with self.assertRaisesRegex(GenerationError, stop_reason):
                self._provider(200, body, []).generate(REQUEST)

    def test_bad_key_is_fatal(self):
        body = {"type": "error", "error": {"type": "authentication_error", "message": "no"}}
        with self.assertRaises(FatalGenerationError):
            self._provider(401, body, []).generate(REQUEST)

    def test_rate_limit_is_not_fatal(self):
        body = {"type": "error", "error": {"type": "rate_limit_error", "message": "slow"}}
        with self.assertRaises(GenerationError):
            self._provider(429, body, []).generate(REQUEST)


@unittest.skipIf(anthropic is None, "needs the anthropic and openai packages")
class OpenAITests(unittest.TestCase):
    def _provider(self, status, body, seen):
        client = openai.OpenAI(
            api_key="test", max_retries=0, http_client=fake_http(status, body, seen)
        )
        return OpenAIProvider(client)

    def _body(self, status="completed"):
        return {
            "id": "resp_1", "object": "response", "created_at": 1, "model": "model-x",
            "status": status, "parallel_tool_calls": False, "tool_choice": "auto", "tools": [],
            "output": [{"type": "message", "id": "m1", "role": "assistant",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": " Hello ",
                                     "annotations": []}]}],
            "usage": {"input_tokens": 3, "output_tokens": 4, "total_tokens": 7,
                      "input_tokens_details": {"cached_tokens": 0},
                      "output_tokens_details": {"reasoning_tokens": 0}},
        }

    def test_request_shape(self):
        seen = []
        request = Request("gpt", "system text", "user text", "none", 1.3)
        reply = self._provider(200, self._body(), seen).generate(request)
        self.assertEqual(reply.text, "Hello")
        sent = json.loads(seen[0].content)
        self.assertEqual(sent["temperature"], 1.3)
        self.assertEqual(sent["reasoning"], {"effort": "none"})
        self.assertEqual(sent["instructions"], "system text")

    def test_omits_unset_temperature(self):
        seen = []
        self._provider(200, self._body(), seen).generate(REQUEST)
        self.assertNotIn("temperature", json.loads(seen[0].content))

    def test_incomplete_is_not_output(self):
        with self.assertRaisesRegex(GenerationError, "incomplete"):
            self._provider(200, self._body("incomplete"), []).generate(REQUEST)

    def test_bad_key_is_fatal(self):
        body = {"error": {"message": "no", "type": "invalid_request_error"}}
        with self.assertRaises(FatalGenerationError):
            self._provider(401, body, []).generate(REQUEST)


if __name__ == "__main__":
    unittest.main()
