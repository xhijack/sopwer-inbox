# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import frappe

from sopwer_inbox.api.webhooks import ingest_payload, verify_secret
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
