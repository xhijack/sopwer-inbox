# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
"""Whitelisted endpoints for linking / creating Customers from an Inbox conversation."""

import frappe
from frappe import _

from sopwer_inbox.crm.registry import get_provider

_INBOX_ROLES = {"Inbox Agent", "Inbox Manager", "System Manager"}


def _require_provider():
	provider = get_provider()
	if not provider:
		frappe.throw(_("No CRM/ERP provider configured."))
	return provider


def _contact_of(conversation: str):
	return frappe.db.get_value("Inbox Conversation", conversation, "contact")


def _require_inbox_role():
	if _INBOX_ROLES & set(frappe.get_roles()):
		return
	frappe.throw(_("You do not have permission to perform this action."), frappe.PermissionError)


@frappe.whitelist()
def customer_options(conversation):
	"""Return the currently linked Customer and suggestions for the conversation's contact."""
	provider = _require_provider()
	_require_inbox_role()
	contact = _contact_of(conversation)
	return {
		"linked": provider.linked_customer(contact) if contact else None,
		"suggestions": provider.suggest_customers_for_contact(contact) if contact else [],
	}


@frappe.whitelist()
def search_customers(q=""):
	"""Search Customers by name fragment. Requires an Inbox role."""
	provider = _require_provider()
	_require_inbox_role()
	return provider.search_customers(q)


@frappe.whitelist()
def link_customer(conversation, customer):
	"""Link *customer* to the contact of *conversation*."""
	provider = _require_provider()
	_require_inbox_role()
	contact = _contact_of(conversation)
	if not contact:
		frappe.throw(_("This conversation has no linked contact."))
	provider.link_customer(contact, customer)
	return {"ok": True, "customer": customer}


@frappe.whitelist()
def create_and_link_customer(conversation, customer_name):
	"""Create a new Customer named *customer_name* and link it to the conversation's contact."""
	provider = _require_provider()
	_require_inbox_role()
	if not frappe.has_permission("Customer", "create"):
		frappe.throw(_("Not allowed to create Customer"), frappe.PermissionError)
	contact = _contact_of(conversation)
	if not contact:
		frappe.throw(_("This conversation has no linked contact."))
	name = provider.create_and_link_customer(contact, customer_name)
	return {"ok": True, "customer": name}
