# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Shared test base + factory helpers for Sopwer Inbox.

Forward-compatible across Frappe v15 (FrappeTestCase) and v16
(IntegrationTestCase). Always extend ``InboxTestCase``.
"""

import frappe

try:  # Frappe v16+
	from frappe.tests import IntegrationTestCase as _BaseTestCase
except ImportError:  # Frappe v15
	from frappe.tests.utils import FrappeTestCase as _BaseTestCase


class InboxTestCase(_BaseTestCase):
	"""Base test case for the Sopwer Inbox app.

	Frappe v15's ``FrappeTestCase`` only rolls back once per class, so test
	methods within a class would otherwise share data. We roll back after each
	method to get proper per-test isolation (v16's IntegrationTestCase already
	does this). Safe because none of our code commits inside a test.
	"""

	def tearDown(self):
		frappe.db.rollback()
		super().tearDown()


# ---------------------------------------------------------------------------
# Factory helpers — keep tests terse and intention-revealing.
# ---------------------------------------------------------------------------

def make_channel(channel_name="Test WA", channel_type="WhatsApp", **kwargs):
	if frappe.db.exists("Inbox Channel", channel_name):
		return frappe.get_doc("Inbox Channel", channel_name)
	doc = frappe.get_doc(
		{
			"doctype": "Inbox Channel",
			"channel_name": channel_name,
			"channel_type": channel_type,
			"enabled": 1,
			**kwargs,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def make_contact(first_name="Budi", phone="+628123456789"):
	doc = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": first_name,
		}
	)
	if phone:
		doc.append("phone_nos", {"phone": phone, "is_primary_phone": 1})
	doc.insert(ignore_permissions=True)
	return doc


def make_conversation(channel, external_conversation_id, contact=None, **kwargs):
	doc = frappe.get_doc(
		{
			"doctype": "Inbox Conversation",
			"channel": channel,
			"external_conversation_id": external_conversation_id,
			"contact": contact,
			**kwargs,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc
