# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import json
import os

import frappe

from sopwer_inbox.channels.whatsapp_inbound import handle_inbound
from sopwer_inbox.tests.base import InboxTestCase, make_channel

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def wuzapi_payload():
	with open(os.path.join(FIXTURES, "wuzapi_inbound_text.json")) as f:
		return json.load(f)


class TestWhatsAppInboundBridge(InboxTestCase):
	def setUp(self):
		self.channel = make_channel("WA Inbound", "WhatsApp", wuzapi_instance="ACC-IN-1")

	def test_inbound_ingested_for_matching_account(self):
		handle_inbound(payload=wuzapi_payload(), account="ACC-IN-1")
		conv = frappe.db.get_value(
			"Inbox Conversation",
			{"channel": self.channel.name, "external_conversation_id": "628123344556"},
		)
		self.assertTrue(conv)
		self.assertTrue(
			frappe.db.exists("Inbox Message", {"conversation": conv, "external_message_id": "3EB0XYZ123"})
		)

	def test_unknown_account_ignored(self):
		handle_inbound(payload=wuzapi_payload(), account="NOT-A-CHANNEL")
		self.assertFalse(
			frappe.db.exists("Inbox Conversation", {"external_conversation_id": "628123344556"})
		)

	def test_empty_payload_safe(self):
		# Should not raise.
		handle_inbound(payload=None, account="ACC-IN-1")
