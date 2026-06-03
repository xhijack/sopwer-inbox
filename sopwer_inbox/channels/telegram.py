# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Telegram channel adapter — talks directly to the Telegram Bot API via webhook."""

from datetime import datetime

import frappe
import requests
from frappe import _
from frappe.utils import get_datetime

from sopwer_inbox.channels.base import BaseChannelAdapter

API_BASE = "https://api.telegram.org"
TIMEOUT = 20


class TelegramAdapter(BaseChannelAdapter):
	# -- inbound -----------------------------------------------------------
	def parse_inbound(self, payload: dict) -> list[dict]:
		message = (payload or {}).get("message") or (payload or {}).get("edited_message")
		if not message:
			# callback_query, my_chat_member, channel_post, etc. — not a chat message
			return []

		chat = message.get("chat", {})
		sender = message.get("from", {})
		message_type, content, media_url = self._classify(message)

		normalized = {
			"channel_type": "Telegram",
			"external_conversation_id": str(chat.get("id")),
			"external_message_id": str(message.get("message_id")),
			"sender_external_id": str(sender.get("id")),
			"sender_name": self._sender_name(sender),
			"sender_phone": (message.get("contact") or {}).get("phone_number"),
			"message_type": message_type,
			"content": content,
			"media_url": media_url,
			"timestamp": get_datetime(),
			"raw": message,
		}
		if message.get("date"):
			normalized["timestamp"] = datetime.fromtimestamp(message["date"])
		return [normalized]

	@staticmethod
	def _sender_name(sender):
		name = " ".join(filter(None, [sender.get("first_name"), sender.get("last_name")]))
		return name or sender.get("username")

	@staticmethod
	def _classify(message):
		"""Return (message_type, content, media_url). media_url is deferred to a
		File download step (Phase 8); we keep the caption/text here."""
		if message.get("text"):
			return "Text", message["text"], None
		caption = message.get("caption")
		if message.get("photo"):
			return "Image", caption, None
		if message.get("voice") or message.get("audio"):
			return "Audio", caption, None
		if message.get("video"):
			return "Video", caption, None
		if message.get("location"):
			loc = message["location"]
			return "Location", f"{loc.get('latitude')},{loc.get('longitude')}", None
		if message.get("document"):
			return "File", caption, None
		return "Text", caption, None

	# -- outbound ----------------------------------------------------------
	def send_message(self, conversation_doc, *, text=None, media_path=None) -> dict:
		token = self.channel.get_password("telegram_bot_token")
		if not token:
			frappe.throw(_("Telegram bot token is not configured for channel {0}").format(self.channel.name))

		url = f"{API_BASE}/bot{token}/sendMessage"
		resp = requests.post(
			url,
			json={"chat_id": conversation_doc.external_conversation_id, "text": text or ""},
			timeout=TIMEOUT,
		)
		data = resp.json()
		if not data.get("ok"):
			frappe.throw(_("Telegram send failed: {0}").format(data.get("description", "unknown error")))

		return {
			"external_message_id": str(data["result"]["message_id"]),
			"delivery_status": "Sent",
		}
