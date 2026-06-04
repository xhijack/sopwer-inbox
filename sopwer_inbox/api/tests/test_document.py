from unittest.mock import patch

import frappe

from sopwer_inbox.api import document as doc_api
from sopwer_inbox.tests.base import InboxTestCase, make_channel, make_conversation


class TestDocumentApi(InboxTestCase):
	def setUp(self):
		self.channel = make_channel("Doc TG", "Telegram")
		self.conv = make_conversation(self.channel.name, "doc-1")
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "ERPNext")

	def test_rejects_when_no_provider(self):
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "None")
		with self.assertRaises(frappe.ValidationError):
			doc_api.list_sendable_documents(self.conv.name, "Sales Invoice")

	def test_lists_via_provider(self):
		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"list_documents": lambda self, dt, cust, q="": [{"name": "INV-1"}],
		})()
		with patch.object(doc_api, "get_provider", return_value=fake), patch.object(
			doc_api, "_conversation_customer", return_value="CUST-1"
		):
			rows = doc_api.list_sendable_documents(self.conv.name, "Sales Invoice")
		self.assertEqual(rows[0]["name"], "INV-1")
