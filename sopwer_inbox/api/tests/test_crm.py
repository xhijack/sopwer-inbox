# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
"""Tests for api/crm.py — link/create Customer from Inbox."""

from unittest.mock import MagicMock, patch

import frappe

from sopwer_inbox.api import crm as crm_api
from sopwer_inbox.tests.base import InboxTestCase, make_channel, make_contact, make_conversation


class TestCustomerOptions(InboxTestCase):
	"""customer_options returns linked customer and suggestions for a conversation."""

	def setUp(self):
		self.channel = make_channel("CRM Opts WA", "WhatsApp")
		self.contact = make_contact("Budi Options", "+628111222333")
		self.conv = make_conversation(
			self.channel.name, "crm-opts-1", contact=self.contact.name
		)
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "ERPNext")

	def test_rejects_when_no_provider(self):
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "None")
		with self.assertRaises(frappe.ValidationError):
			crm_api.customer_options(self.conv.name)

	def test_returns_linked_and_suggestions(self):
		fake = MagicMock()
		fake.linked_customer.return_value = None
		fake.suggest_customers_for_contact.return_value = [
			{"name": "CUST-1", "label": "Cust One", "reason": "phone"}
		]
		with patch.object(crm_api, "get_provider", return_value=fake):
			result = crm_api.customer_options(self.conv.name)
		self.assertIsNone(result["linked"])
		self.assertEqual(len(result["suggestions"]), 1)
		self.assertEqual(result["suggestions"][0]["name"], "CUST-1")
		fake.linked_customer.assert_called_once_with(self.contact.name)
		fake.suggest_customers_for_contact.assert_called_once_with(self.contact.name)

	def test_returns_linked_customer_when_set(self):
		fake = MagicMock()
		fake.linked_customer.return_value = "CUST-9"
		fake.suggest_customers_for_contact.return_value = []
		with patch.object(crm_api, "get_provider", return_value=fake):
			result = crm_api.customer_options(self.conv.name)
		self.assertEqual(result["linked"], "CUST-9")

	def test_returns_empty_when_no_contact_on_conversation(self):
		conv_no_contact = make_conversation(self.channel.name, "crm-opts-nocontact")
		fake = MagicMock()
		fake.linked_customer.return_value = None
		fake.suggest_customers_for_contact.return_value = []
		with patch.object(crm_api, "get_provider", return_value=fake):
			result = crm_api.customer_options(conv_no_contact.name)
		self.assertIsNone(result["linked"])
		self.assertEqual(result["suggestions"], [])
		fake.linked_customer.assert_not_called()
		fake.suggest_customers_for_contact.assert_not_called()

	def test_customer_options_requires_inbox_role(self):
		fake = MagicMock()
		with patch.object(crm_api, "get_provider", return_value=fake), \
				patch("frappe.get_roles", return_value=["Guest"]):
			with self.assertRaises(frappe.PermissionError):
				crm_api.customer_options(self.conv.name)


class TestSearchCustomers(InboxTestCase):
	"""search_customers requires inbox role and proxies the provider."""

	def setUp(self):
		self.channel = make_channel("CRM Search WA", "WhatsApp")
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "ERPNext")

	def test_rejects_when_no_provider(self):
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "None")
		with self.assertRaises(frappe.ValidationError):
			crm_api.search_customers("acme")

	def test_rejects_when_no_inbox_role(self):
		fake = MagicMock()
		with patch.object(crm_api, "get_provider", return_value=fake), \
				patch("frappe.get_roles", return_value=["Guest"]):
			with self.assertRaises(frappe.PermissionError):
				crm_api.search_customers("acme")

	def test_returns_provider_list_when_permitted(self):
		fake = MagicMock()
		fake.search_customers.return_value = [{"name": "CUST-1", "label": "Acme"}]
		with patch.object(crm_api, "get_provider", return_value=fake), \
				patch("frappe.get_roles", return_value=["Inbox Agent"]):
			result = crm_api.search_customers("acme")
		self.assertEqual(result, [{"name": "CUST-1", "label": "Acme"}])
		fake.search_customers.assert_called_once_with("acme")

	def test_inbox_manager_role_permitted(self):
		fake = MagicMock()
		fake.search_customers.return_value = []
		with patch.object(crm_api, "get_provider", return_value=fake), \
				patch("frappe.get_roles", return_value=["Inbox Manager"]):
			result = crm_api.search_customers("x")
		self.assertEqual(result, [])

	def test_system_manager_role_permitted(self):
		fake = MagicMock()
		fake.search_customers.return_value = []
		with patch.object(crm_api, "get_provider", return_value=fake), \
				patch("frappe.get_roles", return_value=["System Manager"]):
			result = crm_api.search_customers("x")
		self.assertEqual(result, [])


class TestLinkCustomer(InboxTestCase):
	"""link_customer guards role, resolves contact, delegates to provider."""

	def setUp(self):
		self.channel = make_channel("CRM Link WA", "WhatsApp")
		self.contact = make_contact("Budi Link", "+628111333444")
		self.conv = make_conversation(
			self.channel.name, "crm-link-1", contact=self.contact.name
		)
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "ERPNext")

	def test_rejects_when_no_provider(self):
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "None")
		with self.assertRaises(frappe.ValidationError):
			crm_api.link_customer(self.conv.name, "CUST-1")

	def test_rejects_when_no_inbox_role(self):
		fake = MagicMock()
		with patch.object(crm_api, "get_provider", return_value=fake), \
				patch("frappe.get_roles", return_value=["Guest"]):
			with self.assertRaises(frappe.PermissionError):
				crm_api.link_customer(self.conv.name, "CUST-1")

	def test_throws_when_no_contact(self):
		conv_no_contact = make_conversation(self.channel.name, "crm-link-nocontact")
		fake = MagicMock()
		with patch.object(crm_api, "get_provider", return_value=fake), \
				patch("frappe.get_roles", return_value=["Inbox Agent"]):
			with self.assertRaises(frappe.ValidationError):
				crm_api.link_customer(conv_no_contact.name, "CUST-1")

	def test_calls_provider_link_customer_and_returns_ok(self):
		fake = MagicMock()
		fake.link_customer.return_value = None
		with patch.object(crm_api, "get_provider", return_value=fake), \
				patch("frappe.get_roles", return_value=["Inbox Agent"]):
			result = crm_api.link_customer(self.conv.name, "CUST-1")
		fake.link_customer.assert_called_once_with(self.contact.name, "CUST-1")
		self.assertTrue(result["ok"])
		self.assertEqual(result["customer"], "CUST-1")


class TestCreateAndLinkCustomer(InboxTestCase):
	"""create_and_link_customer checks Customer create perm + delegates."""

	def setUp(self):
		self.channel = make_channel("CRM Create WA", "WhatsApp")
		self.contact = make_contact("Budi Create", "+628111444555")
		self.conv = make_conversation(
			self.channel.name, "crm-create-1", contact=self.contact.name
		)
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "ERPNext")

	def test_rejects_when_no_provider(self):
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "None")
		with self.assertRaises(frappe.ValidationError):
			crm_api.create_and_link_customer(self.conv.name, "New Corp")

	def test_rejects_when_no_create_permission(self):
		fake = MagicMock()
		with patch.object(crm_api, "get_provider", return_value=fake), \
				patch("frappe.has_permission", return_value=False):
			with self.assertRaises(frappe.PermissionError):
				crm_api.create_and_link_customer(self.conv.name, "New Corp")

	def test_throws_when_no_contact(self):
		conv_no_contact = make_conversation(self.channel.name, "crm-create-nocontact")
		fake = MagicMock()
		with patch.object(crm_api, "get_provider", return_value=fake), \
				patch("frappe.has_permission", return_value=True):
			with self.assertRaises(frappe.ValidationError):
				crm_api.create_and_link_customer(conv_no_contact.name, "New Corp")

	def test_creates_and_returns_ok(self):
		fake = MagicMock()
		fake.create_and_link_customer.return_value = "CUST-9"
		with patch.object(crm_api, "get_provider", return_value=fake), \
				patch("frappe.has_permission", return_value=True):
			result = crm_api.create_and_link_customer(self.conv.name, "New Corp")
		fake.create_and_link_customer.assert_called_once_with(self.contact.name, "New Corp")
		self.assertTrue(result["ok"])
		self.assertEqual(result["customer"], "CUST-9")

	def test_create_customer_requires_inbox_role(self):
		fake = MagicMock()
		with patch.object(crm_api, "get_provider", return_value=fake), \
				patch("frappe.get_roles", return_value=["Accounts User"]), \
				patch("frappe.has_permission", return_value=True):
			with self.assertRaises(frappe.PermissionError):
				crm_api.create_and_link_customer(self.conv.name, "New Corp")
