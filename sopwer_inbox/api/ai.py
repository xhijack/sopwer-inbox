# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""AI agent-assist API.

Draft-only ("Sarankan balasan"): ``suggest_reply`` returns a draft string for
the composer — the agent reviews, edits, and sends manually via
``api.conversation.send_message``. Nothing here ever sends to the customer.

Settings live in the ``Inbox AI Settings`` single doctype (Manager-only write).
The API key is NEVER returned to the browser.
"""

import frappe
from frappe import _

from sopwer_inbox.core.ai import AIError, generate_draft, ping

SETTINGS = "Inbox AI Settings"
HISTORY_LIMIT = 20  # how many recent messages feed the AI prompt
PROVIDERS = {"Ollama", "Claude", "OpenAI"}


# --------------------------------------------------------------------------- #
# Settings
# --------------------------------------------------------------------------- #

def _stored_config() -> dict:
	"""Read the full AI config (including the decrypted api_key) for server use.

	Read via the single-value path so this works regardless of the caller's role
	(agents trigger suggest_reply). The api_key is decrypted here but is ONLY used
	to call the provider — it is never returned by any whitelisted endpoint."""
	doc = frappe.get_cached_doc(SETTINGS)
	return {
		"enabled": bool(doc.enabled),
		"provider": doc.provider or "Ollama",
		"endpoint": doc.endpoint or "",
		"model": doc.model or "",
		"api_key": doc.get_password("api_key", raise_exception=False) or "",
		"system_prompt": doc.system_prompt or "",
	}


@frappe.whitelist()
def get_ai_settings() -> dict:
	"""Non-sensitive AI settings for the UI. Never returns the API key.

	Callable by any agent (the composer needs ``enabled`` to show the button);
	``has_api_key`` lets the manager modal show whether a key is already stored."""
	doc = frappe.get_cached_doc(SETTINGS)
	return {
		"enabled": bool(doc.enabled),
		"provider": doc.provider or "Ollama",
		"endpoint": doc.endpoint or "",
		"model": doc.model or "",
		"system_prompt": doc.system_prompt or "",
		"has_api_key": bool(doc.get_password("api_key", raise_exception=False)),
	}


def _assert_manager():
	if not frappe.has_permission(SETTINGS, "write"):
		frappe.throw(_("Only an Inbox Manager can change AI settings."), frappe.PermissionError)


@frappe.whitelist()
def save_ai_settings(enabled=0, provider="Ollama", endpoint="", model="", api_key=None, system_prompt=None):
	"""Persist AI settings. Manager-only.

	A blank ``api_key`` leaves the stored key untouched (so the manager doesn't
	have to re-enter it on every save); pass a new value to replace it. Likewise
	``system_prompt=None`` leaves the stored prompt untouched — the composer modal
	doesn't edit it, so it stays editable via the Frappe desk form."""
	_assert_manager()
	if provider not in PROVIDERS:
		frappe.throw(_("Invalid provider {0}").format(provider))

	doc = frappe.get_doc(SETTINGS)
	doc.enabled = int(frappe.utils.cint(enabled))
	doc.provider = provider
	doc.endpoint = (endpoint or "").strip()
	doc.model = (model or "").strip()
	if system_prompt is not None:
		doc.system_prompt = system_prompt.strip()
	# Only overwrite the key when a non-blank value is supplied.
	if api_key:
		doc.api_key = api_key
	doc.save(ignore_permissions=True)
	frappe.db.commit()
	return get_ai_settings()


@frappe.whitelist()
def test_ai_connection(provider=None, endpoint=None, model=None, api_key=None, system_prompt=None):
	"""Ping the provider to verify reachability/credentials. Manager-only.

	Uses the stored config, with any non-blank argument overriding it — so the
	manager can test a new provider/model/key BEFORE saving."""
	_assert_manager()
	config = _stored_config()
	if provider:
		config["provider"] = provider
	if endpoint is not None:
		config["endpoint"] = endpoint
	if model:
		config["model"] = model
	if api_key:
		config["api_key"] = api_key
	if system_prompt is not None:
		config["system_prompt"] = system_prompt
	try:
		ping(config)
	except AIError as e:
		frappe.throw(_("AI connection failed: {0}").format(str(e)))
	return {"ok": True}


# --------------------------------------------------------------------------- #
# Draft
# --------------------------------------------------------------------------- #

def _build_transcript(conversation: str) -> list[dict]:
	"""Last HISTORY_LIMIT non-internal messages, oldest→newest, as AI turns."""
	rows = frappe.get_all(
		"Inbox Message",
		filters={"conversation": conversation, "is_internal": 0},
		fields=["direction", "content", "message_type"],
		order_by="message_timestamp desc, creation desc",
		limit=HISTORY_LIMIT,
	)
	rows.reverse()
	transcript = []
	for r in rows:
		content = (r.get("content") or "").strip()
		if not content:
			# Media-only message — give the model a placeholder so context survives.
			content = f"[{(r.get('message_type') or 'media').lower()}]"
		transcript.append({
			"role": "agent" if r.get("direction") == "Outgoing" else "customer",
			"content": content,
		})
	return transcript


@frappe.whitelist()
def suggest_reply(conversation: str) -> dict:
	"""Return ``{"draft": "..."}`` — a suggested next agent reply. Never sends."""
	if not conversation:
		frappe.throw(_("Missing conversation"))

	config = _stored_config()
	if not config["enabled"]:
		frappe.throw(_("AI assist is not enabled."))

	transcript = _build_transcript(conversation)
	try:
		draft = generate_draft(transcript, config)
	except AIError as e:
		frappe.throw(_("AI could not draft a reply: {0}").format(str(e)))
	return {"draft": draft}
