# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe

from sopwer_inbox.api import ai as ai_api
from sopwer_inbox.core.ai import AIError
from sopwer_inbox.tests.base import InboxTestCase, make_channel, make_conversation

SETTINGS = "Inbox AI Settings"


def _set_ai(**values):
	doc = frappe.get_doc(SETTINGS)
	for k, v in values.items():
		setattr(doc, k, v)
	doc.save(ignore_permissions=True)
	frappe.clear_document_cache(SETTINGS, SETTINGS)
	return doc


def _msg(conversation, direction, content, **kw):
	frappe.get_doc({
		"doctype": "Inbox Message",
		"conversation": conversation,
		"direction": direction,
		"sender_type": "Contact" if direction == "Incoming" else "Agent",
		"message_type": kw.get("message_type", "Text"),
		"content": content,
		"is_internal": kw.get("is_internal", 0),
		"delivery_status": "Delivered",
		"message_timestamp": frappe.utils.now_datetime(),
	}).insert(ignore_permissions=True)


class TestSuggestReply(InboxTestCase):
	def setUp(self):
		self.channel = make_channel("AI WA", "WhatsApp", wuzapi_base_url="http://x", wuzapi_token="t")
		self.conv = make_conversation(self.channel.name, "628999")
		_set_ai(enabled=1, provider="Ollama", model="llama3.1:8b")

	def test_suggest_returns_draft(self):
		_msg(self.conv.name, "Incoming", "pesanan saya mana?")
		with patch.object(ai_api, "generate_draft", return_value="Sebentar ya kak, kami cek.") as gd:
			out = ai_api.suggest_reply(self.conv.name)
		self.assertEqual(out, {"draft": "Sebentar ya kak, kami cek."})
		# transcript passed has the customer message mapped to role "customer"
		transcript = gd.call_args[0][0]
		self.assertEqual(transcript[-1], {"role": "customer", "content": "pesanan saya mana?"})

	def test_disabled_raises(self):
		_set_ai(enabled=0)
		_msg(self.conv.name, "Incoming", "halo")
		with self.assertRaises(frappe.ValidationError):
			ai_api.suggest_reply(self.conv.name)

	def test_provider_error_becomes_clean_throw(self):
		_msg(self.conv.name, "Incoming", "halo")
		with patch.object(ai_api, "generate_draft", side_effect=AIError("provider down")):
			with self.assertRaises(frappe.ValidationError):
				ai_api.suggest_reply(self.conv.name)

	def test_transcript_skips_internal_and_orders_oldest_first(self):
		_msg(self.conv.name, "Incoming", "satu")
		_msg(self.conv.name, "Outgoing", "dua")
		_msg(self.conv.name, "Outgoing", "catatan", is_internal=1)  # must be excluded
		_msg(self.conv.name, "Incoming", "tiga")
		transcript = ai_api._build_transcript(self.conv.name)
		self.assertEqual(
			transcript,
			[
				{"role": "customer", "content": "satu"},
				{"role": "agent", "content": "dua"},
				{"role": "customer", "content": "tiga"},
			],
		)

	def test_transcript_media_placeholder(self):
		_msg(self.conv.name, "Incoming", None, message_type="Image")
		transcript = ai_api._build_transcript(self.conv.name)
		self.assertEqual(transcript, [{"role": "customer", "content": "[image]"}])


class TestAISettingsAPI(InboxTestCase):
	def setUp(self):
		_set_ai(enabled=1, provider="Claude", model="claude-x", endpoint="", api_key="secret-key")

	def test_get_never_leaks_api_key(self):
		out = ai_api.get_ai_settings()
		self.assertNotIn("api_key", out)
		self.assertNotIn("apiKey", out)
		self.assertTrue(out["has_api_key"])
		self.assertEqual(out["provider"], "Claude")

	def test_save_blank_key_preserves_existing(self):
		ai_api.save_ai_settings(enabled=1, provider="Claude", model="claude-y", api_key="")
		doc = frappe.get_doc(SETTINGS)
		self.assertEqual(doc.get_password("api_key", raise_exception=False), "secret-key")
		self.assertEqual(doc.model, "claude-y")

	def test_save_new_key_replaces(self):
		ai_api.save_ai_settings(enabled=1, provider="Claude", model="claude-x", api_key="new-key")
		doc = frappe.get_doc(SETTINGS)
		self.assertEqual(doc.get_password("api_key", raise_exception=False), "new-key")

	def test_save_invalid_provider_raises(self):
		with self.assertRaises(frappe.ValidationError):
			ai_api.save_ai_settings(provider="Gemini")

	def test_save_requires_manager_permission(self):
		with patch("sopwer_inbox.api.ai.frappe.has_permission", return_value=False):
			with self.assertRaises(frappe.PermissionError):
				ai_api.save_ai_settings(enabled=1, provider="Ollama")
