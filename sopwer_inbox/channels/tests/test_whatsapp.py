# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import json
import os

import frappe

from sopwer_inbox.channels.whatsapp import WhatsAppAdapter, _strip_jid
from sopwer_inbox.tests.base import InboxTestCase, make_channel

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
	with open(os.path.join(FIXTURES, name)) as f:
		return json.load(f)


class TestWhatsAppAdapter(InboxTestCase):
	def setUp(self):
		self.channel = make_channel("WA Pilot", "WhatsApp", wuzapi_instance="ACC-1")
		self.adapter = WhatsAppAdapter(self.channel)

	def test_strip_jid(self):
		self.assertEqual(_strip_jid("628123344556@s.whatsapp.net"), "628123344556")
		self.assertEqual(_strip_jid("628123:1@c.us"), "628123")

	def test_parse_wuzapi_text(self):
		[msg] = self.adapter.parse_inbound(load_fixture("wuzapi_inbound_text.json"))
		self.assertEqual(msg["channel_type"], "WhatsApp")
		self.assertEqual(msg["external_conversation_id"], "628123344556")
		self.assertEqual(msg["external_message_id"], "3EB0XYZ123")
		self.assertEqual(msg["sender_name"], "Budi Santoso")
		self.assertEqual(msg["sender_phone"], "628123344556")
		self.assertIn("pesanan", msg["content"])

	def test_parse_non_message_returns_empty(self):
		self.assertEqual(self.adapter.parse_inbound({"type": "ReadReceipt", "event": {}}), [])

	def test_send_requires_delegate_app(self):
		"""On a site without the 'whatsapp' app, sending must fail loudly — never
		silently no-op (CLAUDE.md §5)."""
		if "whatsapp" in frappe.get_installed_apps():
			self.skipTest("whatsapp app installed on this site")
		conv = frappe.get_doc(
			{
				"doctype": "Inbox Conversation",
				"channel": self.channel.name,
				"external_conversation_id": "628000",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			self.adapter.send_message(conv, text="hi")
