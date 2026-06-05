# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""WhatsApp Cloud API channel adapter.

Implements the official WhatsApp Business Platform (Meta Cloud API), distinct
from the Wuzapi-based WhatsApp adapter.  Two-way text + media via the Graph API.

Inbound flow:
  webhook POST → webhooks.meta() → parse_inbound(change.value) → ingest_inbound

Outbound flow:
  send_message() → POST /{phone_number_id}/messages
"""

import mimetypes
import os
from datetime import datetime

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime

from sopwer_inbox.channels.base import BaseChannelAdapter

TIMEOUT = 20
TIMEOUT_UPLOAD = 60

# WhatsApp Cloud API media kind from MIME top-type
_MIME_TO_WACLOUD_KIND = {
	"image": "image",
	"video": "video",
	"audio": "audio",
}


def wacloud_kind(mimetype: str) -> str:
	"""Map a mimetype to the WhatsApp Cloud API media kind.

	Returns 'image', 'video', 'audio', or 'document' (fallback — WA Cloud uses
	'document' for arbitrary files, not 'file' like the Graph Messenger API).
	"""
	if not mimetype:
		return "document"
	top = mimetype.split("/")[0].lower()
	return _MIME_TO_WACLOUD_KIND.get(top, "document")


def _unix_s_to_site_tz(unix_s):
	"""WA Cloud timestamps are Unix seconds UTC. Convert to site timezone (naive)."""
	try:
		utc_naive = datetime.utcfromtimestamp(int(unix_s))
		return frappe.utils.convert_utc_to_system_timezone(utc_naive).replace(tzinfo=None)
	except Exception:
		return now_datetime()


class WhatsAppCloudAdapter(BaseChannelAdapter):
	"""Adapter for the WhatsApp Business Platform (Cloud API)."""

	# -- helpers ---------------------------------------------------------------

	def _api_version(self):
		return (self.channel.get("meta_api_version") or "v21.0").strip()

	def _graph_url(self, path):
		return f"https://graph.facebook.com/{self._api_version()}/{path.lstrip('/')}"

	def _token(self):
		token = self.channel.get_password("meta_page_access_token", raise_exception=False)
		if not token:
			frappe.throw(
				_("Channel {0}: WhatsApp token (Page Access Token) is not configured.").format(
					self.channel.name
				)
			)
		return token

	def _phone_number_id(self):
		phone_id = self.channel.get("meta_phone_number_id") or ""
		if not phone_id:
			frappe.throw(
				_("Channel {0}: WA Phone Number ID is not configured.").format(self.channel.name)
			)
		return phone_id.strip()

	def _headers(self):
		return {"Authorization": f"Bearer {self._token()}"}

	def _resolve_local_file(self, media_path):
		"""Map a Frappe file_url (/files/.. or /private/files/..) to an absolute path."""
		name = frappe.db.get_value("File", {"file_url": media_path}, "name")
		if name:
			return frappe.get_doc("File", name).get_full_path()
		frappe.throw(_("Cannot resolve media file: {0}").format(media_path))

	# -- inbound ---------------------------------------------------------------

	def parse_inbound(self, value: dict) -> list[dict]:
		"""Normalize one WhatsApp Cloud webhook change.value into a list of normalized dicts.

		``value`` is the dict at ``entry[].changes[].value`` for a change with
		``field == "messages"``.

		Returns [] when ``value`` contains only statuses (delivery/read receipts)
		or has no messages.
		"""
		messages = value.get("messages")
		if not messages:
			return []

		# Build wa_id → display name lookup from contacts block
		contacts = value.get("contacts") or []
		name_by_id = {}
		for c in contacts:
			wa_id = c.get("wa_id")
			profile = c.get("profile") or {}
			if wa_id and profile.get("name"):
				name_by_id[wa_id] = profile["name"]

		results = []
		for m in messages:
			sender = m.get("from")
			if not sender:
				continue
			mid = m.get("id")
			if not mid:
				continue
			ts_raw = m.get("timestamp")
			timestamp = _unix_s_to_site_tz(ts_raw) if ts_raw else now_datetime()

			msg_type = m.get("type", "")
			message_type = "Text"
			content = None
			media_bytes = None
			media_filename = None
			media_mimetype = None

			if msg_type == "text":
				message_type = "Text"
				content = (m.get("text") or {}).get("body")

			elif msg_type in ("image", "video", "audio", "document", "sticker"):
				type_map = {
					"image": "Image",
					"video": "Video",
					"audio": "Audio",
					"document": "File",
					"sticker": "File",
				}
				message_type = type_map.get(msg_type, "File")
				media_block = m.get(msg_type) or {}
				content = media_block.get("caption")
				media_id = media_block.get("id")
				raw_mime = media_block.get("mime_type")
				raw_filename = media_block.get("filename")

				if media_id:
					try:
						fetched = self._fetch_media_bytes(media_id)
						if fetched is not None:
							media_bytes = fetched
							# Guess extension from mime
							ext = ""
							if raw_mime:
								ext_guess = mimetypes.guess_extension(raw_mime.split(";")[0].strip())
								if ext_guess:
									ext = ext_guess
							media_filename = raw_filename or f"wa-media{ext}"
							media_mimetype = raw_mime
					except Exception:
						frappe.log_error(
							title="WhatsApp Cloud inbound media fetch failed",
							message=frappe.get_traceback(),
						)

			else:
				# Unknown / unsupported type (reaction, location, etc.) — ingest as Text
				message_type = "Text"

			normalized = {
				"channel_type": self.channel.channel_type,
				"external_conversation_id": sender,
				"external_message_id": mid,
				"sender_external_id": sender,
				"sender_phone": sender,
				"sender_name": name_by_id.get(sender),
				"message_type": message_type,
				"content": content,
				"media_url": None,
				"timestamp": timestamp,
				"raw": m,
			}
			if media_bytes is not None:
				normalized["media_bytes"] = media_bytes
				normalized["media_filename"] = media_filename
				normalized["media_mimetype"] = media_mimetype

			results.append(normalized)

		return results

	def _fetch_media_bytes(self, media_id):
		"""Two-step WA Cloud media download: GET /{media_id} → url → GET url → bytes.

		Best-effort — returns None on any error, never raises.
		"""
		try:
			meta_resp = requests.get(
				self._graph_url(media_id),
				headers=self._headers(),
				timeout=TIMEOUT,
			)
			meta_resp.raise_for_status()
			url = meta_resp.json().get("url")
			if not url:
				return None
			media_resp = requests.get(url, headers=self._headers(), timeout=TIMEOUT)
			media_resp.raise_for_status()
			return media_resp.content
		except Exception:
			frappe.log_error(
				title="WhatsApp Cloud _fetch_media_bytes failed",
				message=frappe.get_traceback(),
			)
			return None

	# -- outbound --------------------------------------------------------------

	def send_message(self, conversation_doc, *, text=None, media_path=None) -> dict:
		to = conversation_doc.external_conversation_id
		phone_id = self._phone_number_id()
		url = self._graph_url(f"{phone_id}/messages")
		headers = {**self._headers(), "Content-Type": "application/json"}

		if media_path:
			local = self._resolve_local_file(media_path)
			media_id = self._upload_media(local)
			mimetype, _ = mimetypes.guess_type(local)
			kind = wacloud_kind(mimetype or "")
			media_block = {"id": media_id}
			if text and kind in ("image", "video", "document"):
				media_block["caption"] = text
			body = {
				"messaging_product": "whatsapp",
				"recipient_type": "individual",
				"to": to,
				"type": kind,
				kind: media_block,
			}
		else:
			body = {
				"messaging_product": "whatsapp",
				"recipient_type": "individual",
				"to": to,
				"type": "text",
				"text": {"body": text or ""},
			}

		resp = requests.post(url, json=body, headers=headers, timeout=TIMEOUT)
		resp.raise_for_status()
		mid = (resp.json().get("messages") or [{}])[0].get("id")
		return {"external_message_id": mid, "delivery_status": "Sent"}

	def _upload_media(self, local_path: str) -> str:
		"""Upload a local file to the WA Cloud media endpoint.

		Returns the media id string from the API response.
		"""
		phone_id = self._phone_number_id()
		url = self._graph_url(f"{phone_id}/media")
		mimetype, _ = mimetypes.guess_type(local_path)
		mimetype = mimetype or "application/octet-stream"
		basename = os.path.basename(local_path)

		with open(local_path, "rb") as fh:
			resp = requests.post(
				url,
				data={"messaging_product": "whatsapp", "type": mimetype},
				files={"file": (basename, fh, mimetype)},
				headers=self._headers(),
				timeout=TIMEOUT_UPLOAD,
			)
		resp.raise_for_status()
		media_id = resp.json().get("id")
		if not media_id:
			frappe.throw(
				_("WhatsApp Cloud media upload did not return id: {0}").format(resp.text[:200])
			)
		return media_id
