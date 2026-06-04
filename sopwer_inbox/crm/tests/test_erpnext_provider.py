from unittest.mock import patch

from sopwer_inbox.crm.erpnext import ERPNextProvider
from sopwer_inbox.tests.base import InboxTestCase, make_contact


class TestERPNextProvider(InboxTestCase):
	def test_context_none_when_no_customer(self):
		contact = make_contact("NoCust", "+628000111222")
		p = ERPNextProvider()
		with patch.object(p, "_linked_customer", return_value=None):
			self.assertIsNone(p.get_contact_context(contact.name))

	def test_context_returns_customer_block(self):
		contact = make_contact("HasCust", "+628000111333")
		p = ERPNextProvider()
		with patch.object(p, "is_available", return_value=True), patch.object(
			p, "_linked_customer", return_value="CUST-0001"
		), patch.object(p, "_recent_documents", return_value=[{"name": "SO-1", "grand_total": 100}]):
			ctx = p.get_contact_context(contact.name)
		self.assertEqual(ctx["customer"], "CUST-0001")
		self.assertEqual(ctx["recent_documents"][0]["name"], "SO-1")
