# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import json
import os
from unittest.mock import MagicMock, patch

import frappe

from sopwer_inbox.api.webhooks import ingest_payload, register_meta_webhook, verify_secret, wuzapi
from sopwer_inbox.tests.base import InboxTestCase, make_channel

FIXTURES = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "channels", "tests", "fixtures",
)

TEXT_UPDATE = {
	"update_id": 1,
	"message": {
		"message_id": 555,
		"from": {"id": 42, "first_name": "Webhook", "last_name": "Test"},
		"chat": {"id": 42, "type": "private"},
		"date": 1717400000,
		"text": "via webhook",
	},
}


class TestWebhooks(InboxTestCase):
	def setUp(self):
		self.channel = make_channel("WH TG", "Telegram", telegram_bot_token="123:ABC")

	def test_ingest_payload_creates_message(self):
		[msg] = ingest_payload(self.channel, TEXT_UPDATE)
		self.assertIsNotNone(msg)
		conv = frappe.get_doc("Inbox Conversation", msg.conversation)
		self.assertEqual(conv.external_conversation_id, "42")
		self.assertEqual(msg.content, "via webhook")

	def test_webhook_dedup_on_replay(self):
		ingest_payload(self.channel, TEXT_UPDATE)
		results = ingest_payload(self.channel, TEXT_UPDATE)
		self.assertEqual(results, [None])

	def test_secret_no_config_allows(self):
		self.assertTrue(verify_secret(self.channel, None))

	def test_secret_mismatch_rejected(self):
		secured = make_channel("WH Secure", "Telegram", telegram_bot_token="1:A", webhook_secret="s3cr3t")
		with self.assertRaises(frappe.PermissionError):
			verify_secret(secured, "wrong")
		self.assertTrue(verify_secret(secured, "s3cr3t"))


class TestRegisterMetaWebhook(InboxTestCase):
	def _meta_channel(self, name, channel_type, **extra):
		kw = {
			"meta_app_id": "111", "meta_app_secret": "sekret", "meta_page_id": "999",
			"meta_verify_token": "vt", "meta_page_access_token": "PAGETOK",
		}
		kw.update(extra)
		return make_channel(name, channel_type, **kw)

	def test_registers_and_subscribes_page(self):
		ch = self._meta_channel("WH FB", "Facebook Messenger")
		with patch("requests.post") as post:
			post.return_value = MagicMock(json=lambda: {"success": True})
			res = register_meta_webhook(ch.name)
		self.assertTrue(res["ok"])
		self.assertEqual(res["object"], "page")
		self.assertEqual(post.call_count, 2)  # subscriptions + subscribed_apps
		self.assertIn("/111/subscriptions", post.call_args_list[0].args[0])
		self.assertIn("/999/subscribed_apps", post.call_args_list[1].args[0])
		# Meta requires an HTTPS callback — never register an http:// URL.
		self.assertTrue(res["callback_url"].startswith("https://"))
		sub_data = post.call_args_list[0].kwargs["data"]
		self.assertTrue(sub_data["callback_url"].startswith("https://"))

	def test_instagram_uses_instagram_object(self):
		ch = self._meta_channel("WH IG", "Instagram", meta_page_id="ig999")
		with patch("requests.post") as post:
			post.return_value = MagicMock(json=lambda: {"success": True})
			res = register_meta_webhook(ch.name)
		self.assertEqual(res["object"], "instagram")

	def test_missing_fields_throws(self):
		ch = make_channel("WH FB Bare", "Facebook Messenger", meta_page_id="999")
		with self.assertRaises(frappe.ValidationError):
			register_meta_webhook(ch.name)

	def test_non_meta_channel_throws(self):
		ch = make_channel("WH TG Reg", "Telegram", telegram_bot_token="1:A")
		with self.assertRaises(frappe.ValidationError):
			register_meta_webhook(ch.name)


class TestWuzapiWebhook(InboxTestCase):
	"""Tests for the wuzapi inbound webhook endpoint."""

	def _load_fixture(self, name):
		with open(os.path.join(FIXTURES, name)) as f:
			return json.load(f)

	def setUp(self):
		self.channel = make_channel(
			"WA Webhook Test",
			"WhatsApp",
			wuzapi_base_url="http://wuzapi.test",
			wuzapi_token="tok-wh",
		)

	def test_ingest_text_payload_via_ingest_payload(self):
		"""ingest_payload on a WhatsApp channel + wuzapi text fixture creates a message."""
		payload = self._load_fixture("wuzapi_inbound_text.json")
		# _fetch_inbound_media would try real HTTP; patch it out.
		with patch(
			"sopwer_inbox.channels.whatsapp.WhatsAppAdapter._fetch_inbound_media"
		):
			results = ingest_payload(self.channel, payload)
		self.assertEqual(len(results), 1)
		msg = results[0]
		self.assertIsNotNone(msg)
		conv = frappe.get_doc("Inbox Conversation", msg.conversation)
		self.assertEqual(conv.external_conversation_id, "628123344556")

	def test_dedup_on_replay(self):
		"""Second delivery of the same message must not create a duplicate."""
		payload = self._load_fixture("wuzapi_inbound_text.json")
		with patch(
			"sopwer_inbox.channels.whatsapp.WhatsAppAdapter._fetch_inbound_media"
		):
			ingest_payload(self.channel, payload)
			results = ingest_payload(self.channel, payload)
		self.assertEqual(results, [None])

	def test_missing_channel_param_raises(self):
		"""Calling wuzapi() without a channel parameter must throw ValidationError."""
		with self.assertRaises(frappe.ValidationError):
			wuzapi(channel=None)

	def test_non_whatsapp_channel_raises(self):
		"""Calling wuzapi() with a non-WhatsApp channel must throw ValidationError."""
		tg_channel = make_channel("WH TG WZ", "Telegram", telegram_bot_token="1:A")
		with self.assertRaises(frappe.ValidationError):
			wuzapi(channel=tg_channel.name)
