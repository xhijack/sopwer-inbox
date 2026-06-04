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
		), patch.object(p, "_docs", return_value=[{"name": "SO-1", "grand_total": 100}]), patch(
			"frappe.db.get_value", return_value=None
		):
			ctx = p.get_contact_context(contact.name)
		self.assertEqual(ctx["customer"], "CUST-0001")
		# Frontend expects split sales_orders / invoices (not recent_documents).
		self.assertEqual(ctx["sales_orders"][0]["name"], "SO-1")
		self.assertIn("invoices", ctx)


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

	def test_get_document_pdf_bypasses_print_permission_then_restores(self):
		"""The render runs with ignore_print_permissions set, restored afterwards."""
		seen = {}

		def fake_print(*args, **kwargs):
			seen["flag"] = frappe.flags.ignore_print_permissions
			return b"%PDF-1.4 fake"

		frappe.flags.ignore_print_permissions = False
		with patch("frappe.get_print", side_effect=fake_print):
			ERPNextProvider().get_document_pdf("Sales Invoice", "INV-1")
		# Active during the call, restored to the original value after.
		self.assertTrue(seen["flag"])
		self.assertFalse(frappe.flags.ignore_print_permissions)


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


class TestERPNextLinkCustomerReplace(InboxTestCase):
	"""link_customer replaces any existing Customer link (exactly one after call).

	We can't actually insert links with non-existent doctypes on a Frappe-only
	site, so we use frappe.get_doc + mock to control the contact_doc state.
	"""

	def _fake_contact_with_links(self, links):
		"""Return a mock Contact doc whose .links list and .save() we control."""
		doc = MagicMock()
		doc.links = list(links)

		def get_links(key, default=None):
			return doc.links if key == "links" else (default or [])

		doc.get = get_links
		doc.append = lambda field, row: doc.links.append(frappe._dict(row))
		return doc

	def test_link_customer_replaces_existing_customer_link(self):
		"""If a contact already has a Customer link, link_customer swaps it out."""
		existing = frappe._dict(link_doctype="Customer", link_name="OLD-CUST")
		fake_doc = self._fake_contact_with_links([existing])

		p = ERPNextProvider()
		with patch("frappe.db.exists", return_value=True), \
				patch("frappe.get_doc", return_value=fake_doc):
			p.link_customer("some-contact", "NEW-CUST")

		customer_links = [l for l in fake_doc.links if l.link_doctype == "Customer"]
		self.assertEqual(len(customer_links), 1)
		self.assertEqual(customer_links[0].link_name, "NEW-CUST")
		fake_doc.save.assert_called_once_with(ignore_permissions=True)

	def test_link_customer_preserves_non_customer_links(self):
		"""Other link types (e.g. Lead) must survive a link_customer call."""
		existing = frappe._dict(link_doctype="Lead", link_name="LEAD-001")
		fake_doc = self._fake_contact_with_links([existing])

		p = ERPNextProvider()
		with patch("frappe.db.exists", return_value=True), \
				patch("frappe.get_doc", return_value=fake_doc):
			p.link_customer("some-contact", "CUST-NEW")

		link_types = {l.link_doctype for l in fake_doc.links}
		self.assertIn("Lead", link_types)
		self.assertIn("Customer", link_types)

	def test_link_customer_throws_when_customer_not_found(self):
		p = ERPNextProvider()
		with patch("frappe.db.exists", return_value=False):
			with self.assertRaises(frappe.ValidationError):
				p.link_customer("some-contact", "GHOST-CUST")


class TestERPNextUnlinkCustomer(InboxTestCase):
	"""unlink_customer removes all Customer Dynamic Links from a contact."""

	def _fake_contact_with_links(self, links):
		doc = MagicMock()
		doc.links = list(links)

		def get_links(key, default=None):
			return doc.links if key == "links" else (default or [])

		doc.get = get_links
		return doc

	def test_unlink_removes_customer_links(self):
		links = [frappe._dict(link_doctype="Customer", link_name="CUST-TO-REMOVE")]
		fake_doc = self._fake_contact_with_links(links)

		p = ERPNextProvider()
		with patch("frappe.get_doc", return_value=fake_doc):
			p.unlink_customer("some-contact")

		customer_links = [l for l in fake_doc.links if l.link_doctype == "Customer"]
		self.assertEqual(len(customer_links), 0)
		fake_doc.save.assert_called_once_with(ignore_permissions=True)

	def test_unlink_preserves_non_customer_links(self):
		links = [
			frappe._dict(link_doctype="Customer", link_name="CUST-X"),
			frappe._dict(link_doctype="Lead", link_name="LEAD-X"),
		]
		fake_doc = self._fake_contact_with_links(links)

		p = ERPNextProvider()
		with patch("frappe.get_doc", return_value=fake_doc):
			p.unlink_customer("some-contact")

		remaining = [l.link_doctype for l in fake_doc.links]
		self.assertNotIn("Customer", remaining)
		self.assertIn("Lead", remaining)

	def test_unlink_noop_when_no_customer_link(self):
		"""Should not raise even if there is no customer link."""
		fake_doc = self._fake_contact_with_links([])
		p = ERPNextProvider()
		with patch("frappe.get_doc", return_value=fake_doc):
			p.unlink_customer("some-contact")
		fake_doc.save.assert_called_once_with(ignore_permissions=True)
