# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Resolve an external sender to a Frappe-core Contact.

Resolve by identity (phone for WhatsApp), not by channel — one person may hold
several conversations across different channels (CLAUDE.md §4.2 / §4.6).
"""

import frappe


def find_contact_by_phone(phone: str):
	if not phone:
		return None
	row = frappe.get_all(
		"Contact Phone",
		filters={"phone": phone},
		fields=["parent"],
		limit=1,
	)
	if row:
		return frappe.get_doc("Contact", row[0].parent)
	return None


def resolve_or_create_contact(channel_type, external_id, name=None, phone=None):
	"""Return a Contact doc for this sender, creating one if needed.

	- WhatsApp: dedup by phone number.
	- Telegram: no global phone key in the pilot; create a contact keyed by name.
	"""
	if phone:
		existing = find_contact_by_phone(phone)
		if existing:
			return existing

	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": (name or external_id or "Unknown").strip() or "Unknown",
		}
	)
	if phone:
		contact.append("phone_nos", {"phone": phone, "is_primary_phone": 1})
	contact.insert(ignore_permissions=True)
	return contact
