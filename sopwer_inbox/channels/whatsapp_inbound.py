# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Bridge: receive WhatsApp inbound from the `whatsapp` app and ingest it.

The `whatsapp` app's inbound webhook fans out to every handler registered under
the ``whatsapp_inbound_handlers`` hook. We register this handler (sopwer_inbox
hooks.py) so WhatsApp inbound flows into the same ingest path as Telegram —
no second Wuzapi webhook here (CLAUDE.md §5).
"""

import frappe

from sopwer_inbox.api.webhooks import ingest_payload


def handle_inbound(payload=None, account=None, **kwargs):
	"""Route a Wuzapi inbound payload to the matching WhatsApp Inbox Channel.

	``account`` = the WhatsApp Account / session id the message arrived on; we
	match it to ``Inbox Channel.wuzapi_instance``. Unknown account → ignored
	(another app/site may own that number)."""
	if not payload:
		return

	channel_name = frappe.db.get_value(
		"Inbox Channel",
		{"channel_type": "WhatsApp", "wuzapi_instance": account, "enabled": 1},
	)
	if not channel_name:
		return

	channel_doc = frappe.get_doc("Inbox Channel", channel_name)
	ingest_payload(channel_doc, payload)
