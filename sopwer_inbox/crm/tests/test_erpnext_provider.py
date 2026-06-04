import frappe
from unittest.mock import MagicMock, patch

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


class TestERPNextPdf(InboxTestCase):
	def test_get_document_pdf_calls_get_print(self):
		with patch("frappe.get_print", return_value=b"%PDF-1.4 fake") as gp:
			data = ERPNextProvider().get_document_pdf("Sales Invoice", "INV-1")
		self.assertEqual(data, b"%PDF-1.4 fake")
		gp.assert_called_once()


class TestERPNextLinkedCustomer(InboxTestCase):
	"""linked_customer (public) delegates to _linked_customer (private)."""

	def test_linked_customer_delegates(self):
		p = ERPNextProvider()
		with patch.object(p, "_linked_customer", return_value="CUST-X") as m:
			result = p.linked_customer("some-contact")
		m.assert_called_once_with("some-contact")
		self.assertEqual(result, "CUST-X")

	def test_linked_customer_returns_none_when_no_link(self):
		p = ERPNextProvider()
		with patch.object(p, "_linked_customer", return_value=None):
			self.assertIsNone(p.linked_customer("no-link-contact"))


class TestERPNextSearchCustomers(InboxTestCase):
	"""search_customers queries frappe.get_all and maps to label dicts."""

	def test_search_returns_mapped_list(self):
		fake_rows = [
			frappe._dict(name="CUST-001", customer_name="Acme Corp"),
			frappe._dict(name="CUST-002", customer_name="Beta Ltd"),
		]
		p = ERPNextProvider()
		with patch("frappe.get_all", return_value=fake_rows) as ga:
			result = p.search_customers("acme", limit=5)
		ga.assert_called_once_with(
			"Customer",
			filters={"customer_name": ["like", "%acme%"]},
			fields=["name", "customer_name"],
			limit=5,
		)
		self.assertEqual(result, [
			{"name": "CUST-001", "label": "Acme Corp"},
			{"name": "CUST-002", "label": "Beta Ltd"},
		])

	def test_search_uses_name_as_label_when_customer_name_empty(self):
		fake_rows = [frappe._dict(name="CUST-003", customer_name="")]
		p = ERPNextProvider()
		with patch("frappe.get_all", return_value=fake_rows):
			result = p.search_customers("CUST")
		self.assertEqual(result[0]["label"], "CUST-003")

	def test_search_empty_string_returns_all_up_to_limit(self):
		p = ERPNextProvider()
		with patch("frappe.get_all", return_value=[]) as ga:
			result = p.search_customers("")
		ga.assert_called_once()
		self.assertEqual(result, [])
