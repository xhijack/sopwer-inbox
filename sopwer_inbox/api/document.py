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


def _document_customer(doctype, name):
	return frappe.db.get_value(doctype, name, "customer")


@frappe.whitelist()
def send_document(conversation, doctype, name):
	provider = _require_provider()
	_require_send_permission()
	if doctype not in provider.allowed_send_doctypes():
		frappe.throw(_("Document type {0} is not enabled.").format(doctype))

	conv_customer = _conversation_customer(conversation)
	doc_customer = _document_customer(doctype, name)
	# Safe-by-default: only allow when the conversation has a linked customer that
	# matches the document's customer. Block (don't silently allow) when the
	# conversation customer can't be resolved — prevents sending another
	# customer's financial document to an unlinked conversation.
	if not conv_customer or conv_customer != doc_customer:
		frappe.throw(
			_("This document does not match the conversation's customer. "
			  "Link the contact to the correct customer first.")
		)

	pdf = provider.get_document_pdf(doctype, name)
	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": f"{name}.pdf",
		"content": pdf,
		"is_private": 1,
		"attached_to_doctype": "Inbox Conversation",
		"attached_to_name": conversation,
	})
	file_doc.insert(ignore_permissions=True)

	from sopwer_inbox.api.conversation import send_message

	return send_message(
		conversation,
		text=f"{doctype} {name}",
		message_type="File",
		media_path=file_doc.file_url,
	)
