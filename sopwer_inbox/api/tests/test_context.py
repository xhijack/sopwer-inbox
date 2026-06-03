# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import frappe

from sopwer_inbox.api.context import get_contact_context
from sopwer_inbox.tests.base import InboxTestCase, make_channel, make_contact, make_conversation


class TestContext(InboxTestCase):
	def setUp(self):
		self.channel = make_channel("Ctx TG", "Telegram")
		self.contact = make_contact("Budi Ctx", "+628999000111")
		self.conv = make_conversation(self.channel.name, "ctx-1", contact=self.contact.name)

	def test_context_safe_without_erpnext(self):
		"""On a site without ERPNext, the endpoint must return erp=None, not raise."""
		data = get_contact_context(conversation=self.conv.name)
		self.assertEqual(data["contact"]["name"], self.contact.name)
		if "erpnext" not in frappe.get_installed_apps():
			self.assertIsNone(data["erp"])
		self.assertTrue(any(c["name"] == self.conv.name for c in data["previous_conversations"]))

	def test_unknown_contact_returns_empty(self):
		data = get_contact_context(contact="Nonexistent-Contact-XYZ")
		self.assertIsNone(data["contact"])
		self.assertEqual(data["previous_conversations"], [])
