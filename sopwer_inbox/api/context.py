# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Contact context panel data.

The ERP card is the moat vs standalone Chatwoot — but it is strictly optional:
guarded by ``erpnext in installed_apps`` and never required (CLAUDE.md §7, anti-pattern #2).
"""

import frappe


@frappe.whitelist()
def get_contact_context(contact=None, conversation=None):
	if conversation and not contact:
		contact = frappe.db.get_value("Inbox Conversation", conversation, "contact")

	if not contact or not frappe.db.exists("Contact", contact):
		return {"contact": None, "previous_conversations": [], "erp": None}

	contact_doc = frappe.get_doc("Contact", contact)
	return {
		"contact": {
			"name": contact_doc.name,
			"full_name": contact_doc.get("full_name") or contact_doc.first_name,
			"first_name": contact_doc.first_name,
			"phone": _primary_phone(contact_doc),
			"inbox_notes": contact_doc.get("inbox_notes"),
		},
		"previous_conversations": _previous_conversations(contact),
		"erp": get_erp_context(contact_doc),
	}


def _primary_phone(contact_doc):
	for row in contact_doc.get("phone_nos", []):
		if row.is_primary_phone:
			return row.phone
	phones = contact_doc.get("phone_nos", [])
	return phones[0].phone if phones else None


def _previous_conversations(contact):
	return frappe.get_all(
		"Inbox Conversation",
		filters={"contact": contact},
		fields=["name", "channel", "status", "last_message_at", "last_message_preview"],
		order_by="last_message_at desc",
		limit=10,
	)


def get_erp_context(contact_doc):
	"""Return last Sales Order + Sales Invoice for the contact's customer.

	Returns ``None`` when ERPNext is not installed or no customer is linked — the
	UI hides the card entirely in that case (no empty placeholder)."""
	if "erpnext" not in frappe.get_installed_apps():
		return None

	customer = _linked_customer(contact_doc)
	if not customer:
		return None

	try:
		sales_orders = frappe.get_all(
			"Sales Order",
			filters={"customer": customer},
			fields=["name", "grand_total", "status", "transaction_date"],
			order_by="transaction_date desc",
			limit=3,
		)
		invoices = frappe.get_all(
			"Sales Invoice",
			filters={"customer": customer, "docstatus": 1},
			fields=["name", "grand_total", "status", "posting_date"],
			order_by="posting_date desc",
			limit=3,
		)
	except Exception:
		return None

	return {"customer": customer, "sales_orders": sales_orders, "invoices": invoices}


def _linked_customer(contact_doc):
	for link in contact_doc.get("links", []):
		if link.link_doctype == "Customer":
			return link.link_name
	return None
