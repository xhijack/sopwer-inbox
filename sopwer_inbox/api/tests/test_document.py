from unittest.mock import MagicMock, patch

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

	def test_list_rejects_without_permission(self):
		fake = type("P", (), {"allowed_send_doctypes": lambda self: ["Sales Invoice"]})()
		with patch.object(doc_api, "get_provider", return_value=fake), patch.object(
			doc_api, "_require_send_permission", side_effect=frappe.PermissionError
		):
			with self.assertRaises(frappe.PermissionError):
				doc_api.list_sendable_documents(self.conv.name, "Sales Invoice")

	def test_send_rejects_cross_customer_document(self):
		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"get_document_pdf": lambda self, dt, name, print_format=None: b"%PDF",
		})()
		with patch.object(doc_api, "get_provider", return_value=fake), patch.object(
			doc_api, "_conversation_customer", return_value="CUST-1"
		), patch.object(doc_api, "_document_customer", return_value="CUST-OTHER"):
			with self.assertRaises(frappe.ValidationError):
				doc_api.send_document(self.conv.name, "Sales Invoice", "INV-OTHER")

	def test_send_blocked_when_no_conversation_customer(self):
		"""Block send when the conversation has no linked ERP customer (safe-by-default)."""
		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"get_document_pdf": lambda self, dt, name, print_format=None: b"%PDF",
		})()
		with patch.object(doc_api, "get_provider", return_value=fake), patch.object(
			doc_api, "_conversation_customer", return_value=None
		), patch.object(doc_api, "_document_customer", return_value="CUST-1"):
			with self.assertRaises(frappe.ValidationError):
				doc_api.send_document(self.conv.name, "Sales Invoice", "INV-1")

	def test_send_dispatches_document_message(self):
		fake_provider = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"get_document_pdf": lambda self, dt, name, print_format=None: b"%PDF-1.4",
		})()
		sent = {}

		def fake_send(conversation, text=None, message_type="Text", media_path=None, **k):
			sent.update({"conversation": conversation, "media_path": media_path, "type": message_type})
			return {"name": "msg1"}

		fake_file = MagicMock()
		fake_file.file_url = "/private/files/INV-1.pdf"

		with patch.object(doc_api, "get_provider", return_value=fake_provider), \
				patch.object(doc_api, "_require_send_permission"), \
				patch.object(doc_api, "_conversation_customer", return_value="CUST-1"), \
				patch.object(doc_api, "_document_customer", return_value="CUST-1"), \
				patch("sopwer_inbox.api.conversation.send_message", side_effect=fake_send), \
				patch("frappe.get_doc", return_value=fake_file):
			doc_api.send_document(self.conv.name, "Sales Invoice", "INV-1")
		self.assertTrue(sent["media_path"])
		self.assertEqual(sent["type"], "File")
