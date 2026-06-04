# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
"""Send ERP/CRM documents to the customer through the chat channel."""

import frappe
from frappe import _

from sopwer_inbox.crm.registry import get_provider


def _require_provider():
	provider = get_provider()
	if not provider:
		frappe.throw(_("No CRM/ERP provider configured."))
	return provider


def _require_send_permission():
	settings = frappe.get_cached_doc("Inbox CRM Settings")
	allowed_roles = {r.role for r in settings.get("document_send_roles", [])} or {"Inbox Manager"}
	user_roles = set(frappe.get_roles())
	if "System Manager" in user_roles or allowed_roles & user_roles:
		return
	frappe.throw(_("You are not allowed to send documents."), frappe.PermissionError)


def _conversation_customer(conversation: str):
	contact = frappe.db.get_value("Inbox Conversation", conversation, "contact")
	if not contact:
		return None
	provider = get_provider()
	return provider._linked_customer(contact) if hasattr(provider, "_linked_customer") else None


@frappe.whitelist()
def list_sendable_documents(conversation, doctype, q=""):
	provider = _require_provider()
	_require_send_permission()
	if doctype not in provider.allowed_send_doctypes():
		frappe.throw(_("Document type {0} is not enabled.").format(doctype))
	customer = _conversation_customer(conversation)
	return provider.list_documents(doctype, customer, q)
