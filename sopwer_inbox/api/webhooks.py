# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Inbound webhook endpoints.

Only Telegram has its own webhook here. WhatsApp inbound arrives via the
delegated WhatsApp app (CLAUDE.md §5) — do NOT add a second Wuzapi webhook.
"""

import json

import frappe
from frappe import _

from sopwer_inbox.channels.registry import get_adapter
from sopwer_inbox.core.ingest import ingest_inbound

TELEGRAM_SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
API_BASE = "https://api.telegram.org"
TIMEOUT = 20


def verify_secret(channel_doc, provided_secret):
	"""Constant-time-ish check. If the channel has no secret configured, allow
	(pilot convenience); otherwise the provided secret must match."""
	expected = channel_doc.get_password("webhook_secret", raise_exception=False)
	if not expected:
		return True
	if provided_secret and provided_secret == expected:
		return True
	frappe.throw(_("Invalid webhook secret"), frappe.PermissionError)


def ingest_payload(channel_doc, payload):
	"""Normalize + ingest every message in a raw webhook payload.

	Testable core of the webhook — call this directly in tests."""
	adapter = get_adapter(channel_doc)
	results = []
	for normalized in adapter.parse_inbound(payload):
		results.append(ingest_inbound(normalized, channel_doc))
	return results


@frappe.whitelist(allow_guest=True, methods=["POST"])
def telegram(channel=None, debug=None):
	"""Telegram webhook. URL carries ?channel=<Inbox Channel name>.

	Telegram authenticates via the X-Telegram-Bot-Api-Secret-Token header, set
	when the webhook is registered.

	Debug: append ``&debug=1`` to log the raw request to logs/sopwer_inbox.log
	and return immediately WITHOUT verifying the secret or touching the database —
	use it to confirm whether requests actually reach this code.
	"""
	log = frappe.logger("sopwer_inbox", allow_site=True)
	raw = frappe.request.get_data(as_text=True) if getattr(frappe, "request", None) else ""
	log.info(
		"telegram webhook HIT | channel=%r debug=%r secret_header=%r expect=%r body_len=%s body=%s",
		channel,
		debug,
		frappe.get_request_header(TELEGRAM_SECRET_HEADER),
		frappe.get_request_header("Expect"),
		len(raw or ""),
		(raw or "")[:2000],
	)

	if frappe.utils.cint(debug):
		# Debug mode: log only. No secret check, no parsing, no DB writes.
		return {"ok": True, "debug": True, "received_bytes": len(raw or "")}

	try:
		if not channel:
			frappe.throw(_("Missing channel parameter"))
		channel_doc = frappe.get_doc("Inbox Channel", channel)
		verify_secret(channel_doc, frappe.get_request_header(TELEGRAM_SECRET_HEADER))
		payload = json.loads(raw or "{}")
		results = ingest_payload(channel_doc, payload)
		log.info("telegram webhook OK | channel=%r ingested=%s", channel, len(results))
		return {"ok": True}
	except Exception:
		log.error("telegram webhook FAILED | channel=%r\n%s", channel, frappe.get_traceback())
		raise


@frappe.whitelist()
def register_telegram_webhook(channel, base_url):
	"""Admin helper used at go-live (HITL-1): point Telegram at our webhook.

	``base_url`` is the public HTTPS origin of this site (ngrok/cloudflared/domain).
	Requires Inbox Manager / System Manager (whitelisted, not guest).
	"""
	import requests

	channel_doc = frappe.get_doc("Inbox Channel", channel)
	if channel_doc.channel_type != "Telegram":
		frappe.throw(_("Channel {0} is not a Telegram channel").format(channel))

	token = channel_doc.get_password("telegram_bot_token")
	secret = channel_doc.get_password("webhook_secret", raise_exception=False)
	hook_url = (
		f"{base_url.rstrip('/')}/api/method/sopwer_inbox.api.webhooks.telegram"
		f"?channel={frappe.utils.quote(channel)}"
	)
	body = {"url": hook_url}
	if secret:
		body["secret_token"] = secret

	resp = requests.post(f"{API_BASE}/bot{token}/setWebhook", json=body, timeout=TIMEOUT)
	return resp.json()
