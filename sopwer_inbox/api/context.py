# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Contact context panel data.

The ERP card is the moat vs standalone Chatwoot — but it is strictly optional:
guarded by the configured CRM provider and never required (CLAUDE.md §7, anti-pattern #2).
"""

import frappe

from sopwer_inbox.crm.registry import get_provider
from sopwer_inbox.scope import conversation_company


@frappe.whitelist()
def get_contact_context(contact=None, conversation=None):
	if conversation and not contact:
		contact = frappe.db.get_value("Inbox Conversation", conversation, "contact")

	if not contact or not frappe.db.exists("Contact", contact):
		return {"contact": None, "previous_conversations": [], "erp": None}

	contact_doc = frappe.get_doc("Contact", contact)
	company = conversation_company(conversation)
	return {
		"contact": {
			"name": contact_doc.name,
			"full_name": contact_doc.get("full_name") or contact_doc.first_name,
			"first_name": contact_doc.first_name,
			"phone": _primary_phone(contact_doc),
			"inbox_notes": contact_doc.get("inbox_notes"),
		},
		"previous_conversations": _previous_conversations(contact),
		"erp": _provider_context(contact_doc.name, company),
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


def _provider_context(contact_name, company=None):
	provider = get_provider()
	if not provider:
		return None
	try:
		return provider.get_contact_context(contact_name, company)
	except Exception:
		frappe.log_error(title="Sopwer Inbox CRM context failed", message=frappe.get_traceback())
		return None
