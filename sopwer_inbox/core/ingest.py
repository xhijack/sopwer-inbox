# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Inbound ingest: the brain of the app, independent of any channel.

``ingest_inbound(normalized, channel)`` finds/creates the contact and
conversation, deduplicates by external_message_id, stores the message, updates
conversation activity, and emits a realtime event (CLAUDE.md §5).
"""

import frappe
from frappe.utils import now_datetime

from sopwer_inbox.core import contact_resolver

PREVIEW_LEN = 140

_MEDIA_PREVIEW = {
	"Image": "📷 Image",
	"File": "📎 File",
	"Audio": "🎙 Audio",
	"Video": "🎬 Video",
	"Location": "📍 Location",
}


def _get_channel_doc(channel):
	return channel if hasattr(channel, "channel_type") else frappe.get_doc("Inbox Channel", channel)


def _find_or_create_conversation(normalized, channel_doc):
	external_conversation_id = normalized["external_conversation_id"]
	name = frappe.db.get_value(
		"Inbox Conversation",
		{"channel": channel_doc.name, "external_conversation_id": external_conversation_id},
		"name",
	)
	if name:
		return frappe.get_doc("Inbox Conversation", name)

	contact = contact_resolver.resolve_or_create_contact(
		channel_doc.channel_type,
		external_id=normalized.get("sender_external_id") or external_conversation_id,
		name=normalized.get("sender_name"),
		phone=normalized.get("sender_phone"),
	)
	conversation = frappe.get_doc(
		{
			"doctype": "Inbox Conversation",
			"channel": channel_doc.name,
			"external_conversation_id": external_conversation_id,
			"contact": contact.name,
			"subject": normalized.get("sender_name") or contact.first_name,
			"status": "Open",
			"assigned_to": channel_doc.get("default_assignee"),
			"unread_count": 0,
		}
	)
	conversation.insert(ignore_permissions=True)
	return conversation


def _is_duplicate(conversation_name, external_message_id):
	if not external_message_id:
		return False
	return bool(
		frappe.db.exists(
			"Inbox Message",
			{"conversation": conversation_name, "external_message_id": external_message_id},
		)
	)


def _preview(normalized):
	content = (normalized.get("content") or "").strip()
	if content:
		return content[:PREVIEW_LEN]
	return _MEDIA_PREVIEW.get(normalized.get("message_type"), "")


def _download_media(media_url, conversation_name):
	"""Download inbound media to a private File and return its file_url.

	Best-effort: on failure the message is still stored (text/caption only)."""
	import requests

	try:
		resp = requests.get(media_url, timeout=30)
		resp.raise_for_status()
		content = resp.content
	except Exception:
		frappe.log_error(title="Sopwer Inbox media download failed", message=frappe.get_traceback())
		return None

	fname = (media_url.split("/")[-1].split("?")[0]) or "media"
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": fname,
			"content": content,
			"is_private": 1,
			"attached_to_doctype": "Inbox Conversation",
			"attached_to_name": conversation_name,
		}
	)
	f.insert(ignore_permissions=True)
	return f.file_url


def ingest_inbound(normalized, channel):
	"""Ingest one normalized inbound message. Returns the Inbox Message doc,
	or ``None`` when the message was a duplicate (idempotent webhooks)."""
	channel_doc = _get_channel_doc(channel)
	conversation = _find_or_create_conversation(normalized, channel_doc)

	if _is_duplicate(conversation.name, normalized.get("external_message_id")):
		return None

	media_file = None
	if normalized.get("media_url"):
		media_file = _download_media(normalized["media_url"], conversation.name)

	message = frappe.get_doc(
		{
			"doctype": "Inbox Message",
			"conversation": conversation.name,
			"direction": "Incoming",
			"sender_type": "Contact",
			"is_internal": 0,
			"message_type": normalized.get("message_type") or "Text",
			"content": normalized.get("content"),
			"media_file": media_file,
			"external_message_id": normalized.get("external_message_id"),
			"delivery_status": "Delivered",
			"message_timestamp": normalized.get("timestamp") or now_datetime(),
		}
	)
	try:
		message.insert(ignore_permissions=True)
	except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
		# Lost a race against a concurrent redelivery of the same message.
		frappe.db.rollback()
		return None

	conversation.last_message_at = normalized.get("timestamp") or now_datetime()
	conversation.last_message_preview = _preview(normalized)
	conversation.unread_count = (conversation.unread_count or 0) + 1
	if conversation.status == "Resolved":
		conversation.status = "Open"
	conversation.save(ignore_permissions=True)

	publish_new_message(conversation, message)
	return message


def publish_new_message(conversation, message):
	frappe.publish_realtime(
		"inbox:new_message",
		{
			"conversation": conversation.name,
			"channel": conversation.channel,
			"message": message.name,
			"direction": message.direction,
			"is_internal": message.is_internal,
		},
	)
