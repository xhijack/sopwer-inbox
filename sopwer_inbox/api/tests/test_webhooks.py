# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

import frappe

from sopwer_inbox.api.webhooks import ingest_payload, register_meta_webhook, verify_secret
from sopwer_inbox.tests.base import InboxTestCase, make_channel

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
