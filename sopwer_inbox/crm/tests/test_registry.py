import frappe
from sopwer_inbox.crm.registry import get_provider
from sopwer_inbox.tests.base import InboxTestCase


class TestCRMRegistry(InboxTestCase):
	def _set_provider(self, value):
		frappe.db.set_single_value("Inbox CRM Settings", "provider", value)

	def test_none_provider_returns_none(self):
		self._set_provider("None")
		self.assertIsNone(get_provider())

	def test_erpnext_provider_selected(self):
		self._set_provider("ERPNext")
		provider = get_provider()
		# ERPNextProvider instance even if erpnext not installed (is_available() handles that)
		self.assertEqual(provider.__class__.__name__, "ERPNextProvider")
