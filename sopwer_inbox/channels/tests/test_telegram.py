# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import json
import os
from unittest.mock import MagicMock, patch

import frappe

from sopwer_inbox.channels.telegram import TelegramAdapter
from sopwer_inbox.tests.base import InboxTestCase, make_channel

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
	with open(os.path.join(FIXTURES, name)) as f:
		return json.load(f)


class TestTelegramAdapter(InboxTestCase):
	def setUp(self):
		self.channel = make_channel("TG Bot", "Telegram", telegram_bot_token="123:ABC")
		self.adapter = TelegramAdapter(self.channel)

	def test_parse_text_update(self):
		[msg] = self.adapter.parse_inbound(load_fixture("telegram_text_update.json"))
		self.assertEqual(msg["channel_type"], "Telegram")
		self.assertEqual(msg["external_conversation_id"], "8891234")
		self.assertEqual(msg["external_message_id"], "4567")
		self.assertEqual(msg["message_type"], "Text")
		self.assertIn("pesanan", msg["content"])
		self.assertEqual(msg["sender_name"], "Budi Santoso")

	def test_parse_photo_update(self):
		[msg] = self.adapter.parse_inbound(load_fixture("telegram_photo_update.json"))
		self.assertEqual(msg["message_type"], "Image")
		self.assertEqual(msg["content"], "Ini foto resi pengiriman")

	def test_parse_non_message_returns_empty(self):
		self.assertEqual(self.adapter.parse_inbound({"update_id": 1, "callback_query": {}}), [])

	def test_send_message_mocked(self):
		fake = MagicMock()
		fake.json.return_value = {"ok": True, "result": {"message_id": 9001}}
		conv = MagicMock(external_conversation_id="8891234")
		with patch("sopwer_inbox.channels.telegram.requests.post", return_value=fake) as post:
			result = self.adapter.send_message(conv, text="Halo balik")
		self.assertEqual(result["external_message_id"], "9001")
		self.assertEqual(result["delivery_status"], "Sent")
		post.assert_called_once()
		# token must be in the URL, never logged elsewhere
		self.assertIn("/bot", post.call_args.args[0])

	def test_send_message_failure_raises(self):
		fake = MagicMock()
		fake.json.return_value = {"ok": False, "description": "chat not found"}
		conv = MagicMock(external_conversation_id="000")
		with patch("sopwer_inbox.channels.telegram.requests.post", return_value=fake):
			with self.assertRaises(frappe.ValidationError):
				self.adapter.send_message(conv, text="x")
