# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Telegram channel adapter — talks directly to the Telegram Bot API via webhook."""

from datetime import datetime

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime

from sopwer_inbox.channels.base import BaseChannelAdapter

API_BASE = "https://api.telegram.org"
TIMEOUT = 20


def _unix_to_site_tz(unix_ts):
	"""Telegram `date` is Unix UTC seconds. Convert to the site's timezone
	(naive) so inbound timestamps match outbound (now_datetime). Otherwise they
	are off by the server's UTC offset (e.g. 7h on a UTC server vs WIB)."""
	utc_naive = datetime.utcfromtimestamp(int(unix_ts))
	try:
		return frappe.utils.convert_utc_to_system_timezone(utc_naive).replace(tzinfo=None)
	except Exception:
		return now_datetime()


class TelegramAdapter(BaseChannelAdapter):
	# -- inbound -----------------------------------------------------------
	def parse_inbound(self, payload: dict) -> list[dict]:
		message = (payload or {}).get("message") or (payload or {}).get("edited_message")
		if not message:
			# callback_query, my_chat_member, channel_post, etc. — not a chat message
			return []

		chat = message.get("chat", {})
		sender = message.get("from", {})
		message_type, content, file_id = self._classify(message)
		media_url = self._file_download_url(file_id) if file_id else None

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
			"timestamp": now_datetime(),
			"raw": message,
		}
		if message.get("date"):
			normalized["timestamp"] = _unix_to_site_tz(message["date"])
		return [normalized]

	@staticmethod
	def _sender_name(sender):
		name = " ".join(filter(None, [sender.get("first_name"), sender.get("last_name")]))
		return name or sender.get("username")

	@staticmethod
	def _classify(message):
		"""Return (message_type, content, file_id). file_id (Telegram) is resolved
		to a download URL by the caller; None for text/location."""
		if message.get("text"):
			return "Text", message["text"], None
		caption = message.get("caption")
		if message.get("photo"):
			photos = message["photo"] or []
			return "Image", caption, (photos[-1].get("file_id") if photos else None)
		if message.get("voice"):
			return "Audio", caption, message["voice"].get("file_id")
		if message.get("audio"):
			return "Audio", caption, message["audio"].get("file_id")
		if message.get("video"):
			return "Video", caption, message["video"].get("file_id")
		if message.get("location"):
			loc = message["location"]
			return "Location", f"{loc.get('latitude')},{loc.get('longitude')}", None
		if message.get("document"):
			return "File", caption, message["document"].get("file_id")
		return "Text", caption, None

	def _file_download_url(self, file_id):
		"""Resolve a Telegram file_id to a downloadable URL via getFile."""
		token = self.channel.get_password("telegram_bot_token")
		try:
			resp = requests.get(f"{API_BASE}/bot{token}/getFile", params={"file_id": file_id}, timeout=TIMEOUT)
			data = resp.json()
			if data.get("ok"):
				return f"{API_BASE}/file/bot{token}/{data['result']['file_path']}"
		except Exception:
			frappe.log_error(title="Telegram getFile failed", message=frappe.get_traceback())
		return None

	def _resolve_local_file(self, media_path):
		"""Map a Frappe file URL (/files/.. or /private/files/..) to an absolute path."""
		name = frappe.db.get_value("File", {"file_url": media_path}, "name")
		if name:
			return frappe.get_doc("File", name).get_full_path()
		frappe.throw(_("Cannot resolve media file: {0}").format(media_path))

	# -- outbound ----------------------------------------------------------
	def send_message(self, conversation_doc, *, text=None, media_path=None) -> dict:
		token = self.channel.get_password("telegram_bot_token")
		if not token:
			frappe.throw(_("Telegram bot token is not configured for channel {0}").format(self.channel.name))

		chat_id = conversation_doc.external_conversation_id

		if media_path:
			local = self._resolve_local_file(media_path)
			is_image = str(media_path).lower().rsplit(".", 1)[-1] in ("jpg", "jpeg", "png", "gif", "webp")
			method, field = ("sendPhoto", "photo") if is_image else ("sendDocument", "document")
			data = {"chat_id": chat_id}
			if text:
				data["caption"] = text
			with open(local, "rb") as fh:
				resp = requests.post(
					f"{API_BASE}/bot{token}/{method}", data=data, files={field: fh}, timeout=60
				)
		else:
			resp = requests.post(
				f"{API_BASE}/bot{token}/sendMessage",
				json={"chat_id": chat_id, "text": text or ""},
				timeout=TIMEOUT,
			)

		data = resp.json()
		if not data.get("ok"):
			frappe.throw(_("Telegram send failed: {0}").format(data.get("description", "unknown error")))

		return {
			"external_message_id": str(data["result"]["message_id"]),
			"delivery_status": "Sent",
		}
