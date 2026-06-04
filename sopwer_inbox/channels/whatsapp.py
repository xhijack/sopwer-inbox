# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""WhatsApp channel adapter — DELEGATES to the Sopwer ``whatsapp`` app (Wuzapi).

Audit result (Phase 4, CLAUDE.md §5):
- Delegation target is the **``whatsapp``** app (author: PT Sopwer Teknologi
  Indonesia, Wuzapi provider) — NOT ``frappe_whatsapp`` (Meta Cloud API).
- OUTBOUND: ``whatsapp.setup.whatsapp_handler.WhatsAppHandler(account).send_message(
  sender, message, recipient)`` — we delegate to it (no Wuzapi calls duplicated here).
- INBOUND: the ``whatsapp`` app currently has **no inbound webhook** (it is
  outbound/notification-only). Receiving customer replies requires adding a small
  inbound hook *inside the ``whatsapp`` app* that emits an event / calls
  ``ingest_payload`` — that change touches a shared app and is gated on HITL-2.
  ``parse_inbound`` below already normalizes the Wuzapi event shape, so once that
  hook is added the inbound path works without further changes here.

Channel mapping: ``Inbox Channel.wuzapi_instance`` holds the **WhatsApp Account**
name (the business number/session) in the ``whatsapp`` app.
"""

import frappe
from frappe import _

from sopwer_inbox.channels.base import BaseChannelAdapter

DELEGATE_APP = "whatsapp"


def _ensure_delegate_installed():
	if DELEGATE_APP not in frappe.get_installed_apps():
		frappe.throw(
			_(
				"WhatsApp channel requires the '{0}' app, which is not installed. "
				"WhatsApp transport is delegated to that app (no second webhook here)."
			).format(DELEGATE_APP)
		)


def _strip_jid(jid: str) -> str:
	"""628xxx@s.whatsapp.net / 628xxx@c.us -> 628xxx"""
	if not jid:
		return jid
	return jid.split("@", 1)[0].split(":", 1)[0]


class WhatsAppAdapter(BaseChannelAdapter):
	def _resolve_local_file(self, media_path):
		"""Turn a Frappe file_url (/files/.. or /private/files/..) into a real local
		filesystem path — the whatsapp handler reads the file from disk."""
		name = frappe.db.get_value("File", {"file_url": media_path}, "name")
		if name:
			return frappe.get_doc("File", name).get_full_path()
		frappe.throw(_("Cannot resolve media file: {0}").format(media_path))

	def _account(self):
		account_id = self.channel.get("wuzapi_instance")
		if not account_id:
			frappe.throw(
				_("Channel {0}: set 'Wuzapi Instance' to the WhatsApp Account name.").format(self.channel.name)
			)
		return frappe.get_doc("WhatsApp Account", account_id)

	# -- inbound -----------------------------------------------------------
	def parse_inbound(self, payload: dict) -> list[dict]:
		"""Normalize a Wuzapi inbound event into the inbox schema.

		Wuzapi (whatsmeow) shape::
		    {"type": "Message",
		     "event": {"Info": {"ID","Chat","Sender","PushName","Timestamp"},
		               "Message": {"conversation": "..."}}}
		"""
		event = (payload or {}).get("event") or payload or {}
		info = event.get("Info") or {}
		if not info.get("ID"):
			return []

		chat = _strip_jid(info.get("Chat") or info.get("Sender"))
		message_type, content, media_url = self._classify(event.get("Message") or {})
		if content is None and media_url is None and message_type == "Text":
			# not a user-visible message (receipt, presence, etc.)
			return []

		normalized = {
			"channel_type": "WhatsApp",
			"external_conversation_id": chat,
			"external_message_id": info.get("ID"),
			"sender_external_id": _strip_jid(info.get("Sender")),
			"sender_name": info.get("PushName"),
			"sender_phone": chat,
			"message_type": message_type,
			"content": content,
			"media_url": media_url,
			"timestamp": frappe.utils.get_datetime(info.get("Timestamp")) if info.get("Timestamp") else frappe.utils.now_datetime(),
			"raw": payload,
		}
		return [normalized]

	@staticmethod
	def _classify(message: dict):
		if message.get("conversation"):
			return "Text", message["conversation"], None
		ext = message.get("extendedTextMessage") or {}
		if ext.get("text"):
			return "Text", ext["text"], None
		if message.get("imageMessage"):
			return "Image", (message["imageMessage"] or {}).get("caption"), None
		if message.get("documentMessage"):
			return "File", (message["documentMessage"] or {}).get("caption"), None
		if message.get("audioMessage"):
			return "Audio", None, None
		if message.get("videoMessage"):
			return "Video", (message["videoMessage"] or {}).get("caption"), None
		if message.get("locationMessage"):
			loc = message["locationMessage"] or {}
			return "Location", f"{loc.get('degreesLatitude')},{loc.get('degreesLongitude')}", None
		return "Text", None, None

	# -- outbound ----------------------------------------------------------
	def send_message(self, conversation_doc, *, text=None, media_path=None) -> dict:
		_ensure_delegate_installed()
		from whatsapp.setup.whatsapp_handler import WhatsAppHandler

		account = self._account()
		handler = WhatsAppHandler(account)
		recipient = conversation_doc.external_conversation_id

		if media_path:
			local = self._resolve_local_file(media_path)
			handler.send_file(account.whatsapp_number, local, recipient, caption=text)
		else:
			handler.send_message(account.whatsapp_number, text or "", recipient)

		# The whatsapp app logs to its own WhatsApp Message and does not surface a
		# provider message id; mark Sent (outbound dedup is not required).
		return {"external_message_id": None, "delivery_status": "Sent"}
