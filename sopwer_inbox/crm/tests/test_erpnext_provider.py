import frappe
from unittest.mock import patch

from sopwer_inbox.crm.erpnext import ERPNextProvider
from sopwer_inbox.tests.base import InboxTestCase, make_contact


class TestERPNextProvider(InboxTestCase):
	def test_context_none_when_no_customer(self):
		contact = make_contact("NoCust", "+628000111222")
		p = ERPNextProvider()
		with patch.object(p, "is_available", return_value=True), patch.object(
			p, "_linked_customer", return_value=None
		):
			self.assertIsNone(p.get_contact_context(contact.name))

	def test_context_returns_customer_block(self):
		contact = make_contact("HasCust", "+628000111333")
		p = ERPNextProvider()
		with patch.object(p, "is_available", return_value=True), patch.object(
			p, "_linked_customer", return_value="CUST-0001"
		), patch.object(p, "_recent_documents", return_value=[{"name": "SO-1", "grand_total": 100}]), patch(
			"frappe.db.get_value", return_value=None
		):
			ctx = p.get_contact_context(contact.name)
		self.assertEqual(ctx["customer"], "CUST-0001")
		self.assertEqual(ctx["recent_documents"][0]["name"], "SO-1")


class TestERPNextDocuments(InboxTestCase):
	def setUp(self):
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "ERPNext")
		s = frappe.get_doc("Inbox CRM Settings")
		s.set("sendable_doctypes", [])
		s.append("sendable_doctypes", {"document_type": "Sales Invoice"})
		s.flags.ignore_links = True
		s.save(ignore_permissions=True)

	def test_allowed_doctypes_from_settings(self):
		self.assertEqual(ERPNextProvider().allowed_send_doctypes(), ["Sales Invoice"])
