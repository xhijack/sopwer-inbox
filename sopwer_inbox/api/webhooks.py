# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Inbound webhook endpoints.

Only Telegram has its own webhook here. WhatsApp inbound arrives via the
delegated WhatsApp app (CLAUDE.md §5) — do NOT add a second Wuzapi webhook.
Meta (Facebook Messenger + Instagram) share a single /meta endpoint.
"""

import hashlib
import hmac
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
	req = getattr(frappe, "request", None)
	# Telegram POSTs a JSON body; Frappe then builds form_dict from that body and
	# DROPS the query string, so `channel`/`debug` arrive as None. Read them
	# straight from the query string instead.
	if req is not None:
		channel = channel or req.args.get("channel")
		debug = debug or req.args.get("debug")
	raw = req.get_data(as_text=True) if req is not None else ""
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


# ---------------------------------------------------------------------------
# Meta (Facebook Messenger + Instagram) webhook
# ---------------------------------------------------------------------------

_OBJECT_TO_CHANNEL_TYPE = {
	"page": "Facebook Messenger",
	"instagram": "Instagram",
}


def _verify_meta_signature(raw_bytes: bytes, header: str, app_secret: str) -> bool:
	"""Verify X-Hub-Signature-256 = 'sha256=' + HMAC-SHA256(app_secret, body).

	Returns False when header or app_secret are empty/missing.
	"""
	if not header or not app_secret:
		return False
	expected = "sha256=" + hmac.new(
		app_secret.encode(), raw_bytes, hashlib.sha256
	).hexdigest()
	return hmac.compare_digest(expected, header)


def _match_meta_channel(object_type: str, entry_id: str):
	"""Resolve an (object_type, entry_id) pair to an Inbox Channel doc or None.

	Looks up by meta_page_id == entry_id and channel_type matching the platform.
	"""
	channel_type = _OBJECT_TO_CHANNEL_TYPE.get(object_type)
	if not channel_type:
		return None
	results = frappe.get_all(
		"Inbox Channel",
		filters={"meta_page_id": entry_id, "channel_type": channel_type, "enabled": 1},
		fields=["name"],
		limit=1,
	)
	if not results:
		return None
	return frappe.get_doc("Inbox Channel", results[0]["name"])


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def meta():
	"""Meta (Facebook Messenger + Instagram) webhook endpoint.

	GET  — Hub verification challenge (Meta calls this when you register a webhook).
	POST — Inbound messaging events; verified via X-Hub-Signature-256.

	A single Meta App sends ALL its events here; routing to the correct Inbox
	Channel is done by matching entry.id (page_id / ig_user_id) + object type.
	"""
	log = frappe.logger("sopwer_inbox", allow_site=True)
	req = getattr(frappe, "request", None)

	# ------------------------------------------------------------------ GET --
	if req is not None and req.method == "GET":
		args = req.args
		mode = args.get("hub.mode")
		verify_token = args.get("hub.verify_token")
		challenge = args.get("hub.challenge")

		if mode == "subscribe" and verify_token:
			# Find any enabled Meta channel whose meta_verify_token matches.
			channels = frappe.get_all(
				"Inbox Channel",
				filters={"channel_type": ["in", ["Facebook Messenger", "Instagram"]], "enabled": 1},
				fields=["name", "meta_verify_token"],
			)
			for ch in channels:
				if ch.get("meta_verify_token") and ch["meta_verify_token"] == verify_token:
					log.info("meta GET challenge OK | channel=%r", ch["name"])
					from werkzeug.wrappers import Response
					return Response(challenge or "", content_type="text/plain", status=200)

		log.warning("meta GET challenge FAILED | verify_token=%r", verify_token)
		from werkzeug.wrappers import Response
		return Response("Forbidden", content_type="text/plain", status=403)

	# ----------------------------------------------------------------- POST --
	raw = req.get_data() if req is not None else b""
	try:
		payload = json.loads(raw or b"{}")
	except Exception:
		log.error("meta POST: invalid JSON body")
		return {"ok": False}

	object_type = payload.get("object", "")
	log.info("meta POST | object=%r entries=%s", object_type, len(payload.get("entry", [])))

	for entry in payload.get("entry", []):
		entry_id = entry.get("id")
		channel_doc = _match_meta_channel(object_type, entry_id)
		if not channel_doc:
			log.warning("meta POST: no channel for object=%r entry_id=%r — skipping", object_type, entry_id)
			continue

		# Verify signature per matched channel
		app_secret = channel_doc.get_password("meta_app_secret", raise_exception=False) or ""
		sig_header = (req.headers.get("X-Hub-Signature-256") or "") if req else ""

		if not app_secret:
			log.warning(
				"meta POST: meta_app_secret empty on channel %r — skipping entry for security",
				channel_doc.name,
			)
			continue

		if not _verify_meta_signature(raw, sig_header, app_secret):
			log.warning(
				"meta POST: invalid signature for channel %r — skipping entry",
				channel_doc.name,
			)
			continue

		adapter = get_adapter(channel_doc)
		for event in entry.get("messaging", []):
			try:
				for norm in adapter.parse_inbound(event):
					ingest_inbound(norm, channel_doc)
			except Exception:
				log.error(
					"meta POST: error processing event for channel=%r\n%s",
					channel_doc.name,
					frappe.get_traceback(),
				)

	return {"ok": True}


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
