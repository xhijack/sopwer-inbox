# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Agent-facing conversation API (outbound send, status, assignment, notes)."""

import frappe
from frappe import _
from frappe.utils import now_datetime

from sopwer_inbox.channels.registry import get_adapter
from sopwer_inbox.core.ingest import publish_new_message

PREVIEW_LEN = 140


def _get_conversation(conversation):
	return frappe.get_doc("Inbox Conversation", conversation)


def _touch(conversation_doc, preview, *, reset_unread=False):
	conversation_doc.last_message_at = now_datetime()
	conversation_doc.last_message_preview = (preview or "")[:PREVIEW_LEN]
	if reset_unread:
		conversation_doc.unread_count = 0
	conversation_doc.save(ignore_permissions=True)


def _dispatch(conversation_doc, message, *, text, media_path):
	"""Send an outgoing message through the channel adapter. On failure, mark the
	message Failed instead of crashing the UI (CLAUDE.md §7)."""
	try:
		adapter = get_adapter(conversation_doc.channel)
		result = adapter.send_message(conversation_doc, text=text, media_path=media_path)
		message.external_message_id = result.get("external_message_id")
		message.delivery_status = result.get("delivery_status", "Sent")
	except Exception:
		message.delivery_status = "Failed"
		frappe.log_error(
			title="Sopwer Inbox outbound send failed",
			message=frappe.get_traceback(),
		)
	message.save(ignore_permissions=True)
	return message


@frappe.whitelist()
def send_message(conversation, text=None, message_type="Text", media_path=None, is_internal=0):
	"""Send an outgoing reply, OR record an internal note.

	is_internal=1 → the message is stored & broadcast for the UI but is NEVER
	dispatched to the channel adapter (CLAUDE.md §5 / §7).
	"""
	is_internal = int(is_internal or 0)
	conversation_doc = _get_conversation(conversation)

	message = frappe.get_doc(
		{
			"doctype": "Inbox Message",
			"conversation": conversation_doc.name,
			"direction": "Outgoing",
			"sender_type": "Agent",
			"sender_user": frappe.session.user,
			"is_internal": is_internal,
			"message_type": message_type or "Text",
			"content": text,
			"media_file": media_path,
			"delivery_status": "Pending",
			"message_timestamp": now_datetime(),
		}
	)
	message.insert(ignore_permissions=True)

	if is_internal:
		# Internal note: persist + notify UI, then STOP. Never touch the adapter.
		_touch(conversation_doc, f"[catatan internal] {text or ''}", reset_unread=True)
		publish_new_message(conversation_doc, message)
		return _message_payload(message)

	_dispatch(conversation_doc, message, text=text, media_path=media_path)
	_touch(conversation_doc, text or message_type, reset_unread=True)
	publish_new_message(conversation_doc, message)
	return _message_payload(message)


@frappe.whitelist()
def add_internal_note(conversation, text):
	"""Explicit internal-note endpoint (delegates to send_message with the guard)."""
	return send_message(conversation, text=text, is_internal=1)


@frappe.whitelist()
def retry_message(message):
	"""Re-dispatch a previously Failed outgoing message."""
	msg = frappe.get_doc("Inbox Message", message)
	if msg.is_internal:
		frappe.throw(_("Internal notes are never sent to the customer."))
	if msg.direction != "Outgoing":
		frappe.throw(_("Only outgoing messages can be retried."))
	conversation_doc = _get_conversation(msg.conversation)
	msg.delivery_status = "Pending"
	msg.save(ignore_permissions=True)
	_dispatch(conversation_doc, msg, text=msg.content, media_path=msg.media_file)
	publish_new_message(conversation_doc, msg)
	return _message_payload(msg)


@frappe.whitelist()
def set_status(conversation, status):
	if status not in ("Open", "Pending", "Resolved"):
		frappe.throw(_("Invalid status {0}").format(status))
	conversation_doc = _get_conversation(conversation)
	conversation_doc.status = status
	conversation_doc.save(ignore_permissions=True)
	_publish_conversation_updated(conversation_doc)
	return {"status": status}


@frappe.whitelist()
def assign(conversation, user=None):
	conversation_doc = _get_conversation(conversation)
	conversation_doc.assigned_to = user or None
	conversation_doc.save(ignore_permissions=True)
	_publish_conversation_updated(conversation_doc)
	return {"assigned_to": conversation_doc.assigned_to}


@frappe.whitelist()
def mark_read(conversation):
	conversation_doc = _get_conversation(conversation)
	conversation_doc.unread_count = 0
	conversation_doc.save(ignore_permissions=True)
	_publish_conversation_updated(conversation_doc)
	return {"unread_count": 0}


def _publish_conversation_updated(conversation_doc):
	frappe.publish_realtime(
		"inbox:conversation_updated",
		{
			"conversation": conversation_doc.name,
			"status": conversation_doc.status,
			"assigned_to": conversation_doc.assigned_to,
			"unread_count": conversation_doc.unread_count,
		},
	)


def _message_payload(message):
	return {
		"name": message.name,
		"conversation": message.conversation,
		"direction": message.direction,
		"is_internal": message.is_internal,
		"delivery_status": message.delivery_status,
		"external_message_id": message.external_message_id,
	}
