# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Unit tests for the provider-agnostic AI draft dispatcher (no DB, no network)."""

import unittest
from unittest.mock import MagicMock, patch

from sopwer_inbox.core import ai
from sopwer_inbox.core.ai import AIError, generate_draft


def _resp(status=200, json_body=None, text=""):
	m = MagicMock()
	m.status_code = status
	m.text = text
	m.json.return_value = json_body if json_body is not None else {}
	return m


TRANSCRIPT = [
	{"role": "customer", "content": "halo, pesanan saya mana?"},
	{"role": "agent", "content": "sebentar ya kak"},
	{"role": "customer", "content": "udah 3 hari loh"},
]


class TestAIDispatcher(unittest.TestCase):
	# -- routing + payload shape ------------------------------------------

	@patch("sopwer_inbox.core.ai.requests.post")
	def test_ollama_routes_and_returns_content(self, post):
		post.return_value = _resp(json_body={"message": {"content": "Maaf kak, kami cek dulu."}})
		out = generate_draft(TRANSCRIPT, {"provider": "ollama", "model": "llama3.1:8b"})
		self.assertEqual(out, "Maaf kak, kami cek dulu.")
		url = post.call_args[0][0]
		self.assertTrue(url.endswith("/api/chat"))
		body = post.call_args[1]["json"]
		# system prepended, customer→user, agent→assistant
		self.assertEqual(body["messages"][0]["role"], "system")
		self.assertEqual(body["messages"][1]["role"], "user")
		self.assertEqual(body["messages"][2]["role"], "assistant")

	@patch("sopwer_inbox.core.ai.requests.post")
	def test_claude_routes_and_parses_blocks(self, post):
		post.return_value = _resp(json_body={"content": [{"type": "text", "text": "Halo kak 👋"}]})
		out = generate_draft(
			TRANSCRIPT, {"provider": "claude", "model": "claude-x", "api_key": "sk-test"}
		)
		self.assertEqual(out, "Halo kak 👋")
		self.assertEqual(post.call_args[0][0], ai._ANTHROPIC_URL)
		headers = post.call_args[1]["headers"]
		self.assertEqual(headers["x-api-key"], "sk-test")
		# system block is cache-controlled
		body = post.call_args[1]["json"]
		self.assertEqual(body["system"][0]["cache_control"]["type"], "ephemeral")

	@patch("sopwer_inbox.core.ai.requests.post")
	def test_openai_routes_and_parses_choices(self, post):
		post.return_value = _resp(json_body={"choices": [{"message": {"content": "Sip kak"}}]})
		out = generate_draft(
			TRANSCRIPT, {"provider": "openai", "model": "gpt-4o", "api_key": "sk-o"}
		)
		self.assertEqual(out, "Sip kak")
		self.assertTrue(post.call_args[0][0].endswith("/v1/chat/completions"))
		self.assertEqual(post.call_args[1]["headers"]["Authorization"], "Bearer sk-o")

	# -- validation -------------------------------------------------------

	def test_unknown_provider_raises(self):
		with self.assertRaises(AIError):
			generate_draft(TRANSCRIPT, {"provider": "magic"})

	def test_empty_transcript_raises(self):
		with self.assertRaises(AIError):
			generate_draft([], {"provider": "ollama", "model": "m"})

	def test_cloud_missing_api_key_raises(self):
		with self.assertRaises(AIError):
			generate_draft(TRANSCRIPT, {"provider": "claude", "model": "m"})

	def test_missing_model_raises(self):
		with self.assertRaises(AIError):
			generate_draft(TRANSCRIPT, {"provider": "ollama"})

	# -- error handling ---------------------------------------------------

	@patch("sopwer_inbox.core.ai.requests.post")
	def test_http_error_status_raises(self, post):
		post.return_value = _resp(status=401, text="unauthorized")
		with self.assertRaises(AIError):
			generate_draft(TRANSCRIPT, {"provider": "openai", "model": "m", "api_key": "k"})

	@patch("sopwer_inbox.core.ai.requests.post")
	def test_empty_provider_response_raises(self, post):
		post.return_value = _resp(json_body={"message": {"content": "   "}})
		with self.assertRaises(AIError):
			generate_draft(TRANSCRIPT, {"provider": "ollama", "model": "m"})

	@patch("sopwer_inbox.core.ai.requests.post")
	def test_network_error_raises_aierror(self, post):
		post.side_effect = ai.requests.RequestException("boom")
		with self.assertRaises(AIError):
			generate_draft(TRANSCRIPT, {"provider": "ollama", "model": "m"})

	@patch("sopwer_inbox.core.ai.requests.post")
	def test_system_prompt_appended(self, post):
		post.return_value = _resp(json_body={"message": {"content": "ok"}})
		generate_draft(
			TRANSCRIPT,
			{"provider": "ollama", "model": "m", "system_prompt": "Gunakan bahasa formal."},
		)
		system_msg = post.call_args[1]["json"]["messages"][0]["content"]
		self.assertIn("Gunakan bahasa formal.", system_msg)


if __name__ == "__main__":
	unittest.main()
