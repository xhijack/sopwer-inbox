# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Channel health checks + visibility helper.

``get_visible_conversations`` is the single seam for per-agent channel access.
In the pilot every agent sees every channel; the later "agent X only handles WA CS"
feature adds a filter HERE without touching Inbox Conversation (CLAUDE.md §4.2).
"""

import frappe
from frappe import _


@frappe.whitelist()
def check_channel_health(channel):
	"""Lightweight connectivity check per channel type. Never raises — returns a
	status dict so the UI can show a non-blocking banner."""
	channel_doc = frappe.get_doc("Inbox Channel", channel)
	if not channel_doc.enabled:
		return {"channel": channel, "ok": False, "status": "disabled"}

	try:
		if channel_doc.channel_type == "Telegram":
			return _telegram_health(channel_doc)
		if channel_doc.channel_type == "WhatsApp":
			return _whatsapp_health(channel_doc)
	except Exception as e:
		return {"channel": channel, "ok": False, "status": "error", "detail": str(e)}

	return {"channel": channel, "ok": False, "status": "unknown_type"}


def _telegram_health(channel_doc):
	import requests

	token = channel_doc.get_password("telegram_bot_token", raise_exception=False)
	if not token:
		return {"channel": channel_doc.name, "ok": False, "status": "no_token"}
	resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15)
	data = resp.json()
	return {
		"channel": channel_doc.name,
		"ok": bool(data.get("ok")),
		"status": "connected" if data.get("ok") else "disconnected",
		"username": (data.get("result") or {}).get("username"),
	}


def _whatsapp_health(channel_doc):
	# Delegated transport (Phase 4). Until the delegate app is wired, report pending.
	from sopwer_inbox.channels.whatsapp import DELEGATE_APP

	installed = DELEGATE_APP in frappe.get_installed_apps()
	return {
		"channel": channel_doc.name,
		"ok": installed,
		"status": "connected" if installed else "delegate_missing",
		"detail": _("WhatsApp transport delegated to {0}").format(DELEGATE_APP),
	}


def get_visible_conversations(user=None, filters=None, limit=50, start=0):
	"""Return conversations visible to ``user``. Pilot: all channels visible.

	Wrap all conversation-list queries through here so per-agent channel
	restriction can be added in one place later."""
	query_filters = dict(filters or {})
	return frappe.get_all(
		"Inbox Conversation",
		filters=query_filters,
		fields=[
			"name",
			"contact",
			"channel",
			"external_conversation_id",
			"subject",
			"status",
			"assigned_to",
			"last_message_at",
			"last_message_preview",
			"unread_count",
		],
		order_by="last_message_at desc",
		limit_page_length=limit,
		limit_start=start,
	)
