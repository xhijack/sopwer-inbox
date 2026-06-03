# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import frappe

from sopwer_inbox.tests.base import InboxTestCase, make_channel, make_conversation


class TestInboxConversation(InboxTestCase):
	def setUp(self):
		self.channel = make_channel("Test TG", "Telegram")

	def test_create_conversation(self):
		conv = make_conversation(self.channel.name, "chat-100")
		self.assertEqual(conv.status, "Open")
		self.assertEqual(conv.unread_count, 0)

	def test_duplicate_conversation_rejected(self):
		make_conversation(self.channel.name, "chat-200")
		with self.assertRaises(frappe.DuplicateEntryError):
			make_conversation(self.channel.name, "chat-200")

	def test_same_external_id_different_channel_allowed(self):
		"""Same external id on a *different* channel must create a separate
		conversation — deliberate multi-channel semantics (CLAUDE.md §4.2)."""
		other = make_channel("Test WA CS", "WhatsApp")
		c1 = make_conversation(self.channel.name, "shared-id")
		c2 = make_conversation(other.name, "shared-id")
		self.assertNotEqual(c1.name, c2.name)
