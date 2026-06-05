# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""WhatsApp channel adapter — talks to Wuzapi directly via Inbox Channel fields.

Outbound: reads ``wuzapi_base_url`` + ``wuzapi_token`` from the Inbox Channel
and calls Wuzapi's REST API directly (no dependency on the ``whatsapp`` app).

Inbound: arrives via the new ``sopwer_inbox.api.webhooks.wuzapi`` endpoint
(point the Wuzapi session webhook at that URL).  ``parse_inbound`` normalises
the Wuzapi/whatsmeow event shape — unchanged from before.
"""

import mimetypes
import os

import frappe
from frappe import _

from sopwer_inbox.channels.base import BaseChannelAdapter
from sopwer_inbox.channels.wuzapi_client import (
    WuzapiClient,
    extract_wuzapi_base64,
    file_to_wuzapi_base64,
    guess_mimetype,
    wuzapi_kind,
)


def _strip_jid(jid: str) -> str:
    """628xxx@s.whatsapp.net / 628xxx@c.us -> 628xxx"""
    if not jid:
        return jid
    return jid.split("@", 1)[0].split(":", 1)[0]


class WhatsAppAdapter(BaseChannelAdapter):
    # -- transport helpers -------------------------------------------------

    def _client(self) -> WuzapiClient:
        base_url = (self.channel.get("wuzapi_base_url") or "").strip()
        token = self.channel.get_password("wuzapi_token", raise_exception=False) or ""
        if not base_url:
            frappe.throw(
                _("Channel {0}: set 'Wuzapi Base URL' before sending messages.").format(
                    self.channel.name
                )
            )
        if not token:
            frappe.throw(
                _("Channel {0}: set 'Wuzapi Token' before sending messages.").format(
                    self.channel.name
                )
            )
        return WuzapiClient(base_url, token)

    def _resolve_local_file(self, media_path):
        """Turn a Frappe file_url (/files/.. or /private/files/..) into a real
        local filesystem path — needed to read the file for base64 encoding."""
        name = frappe.db.get_value("File", {"file_url": media_path}, "name")
        if name:
            return frappe.get_doc("File", name).get_full_path()
        frappe.throw(_("Cannot resolve media file: {0}").format(media_path))

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
        message_type, content, media_info = self._classify(event.get("Message") or {})
        if content is None and media_info is None and message_type == "Text":
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
            "media_url": None,
            "timestamp": (
                frappe.utils.get_datetime(info.get("Timestamp"))
                if info.get("Timestamp")
                else frappe.utils.now_datetime()
            ),
            "raw": payload,
        }

        if media_info:
            self._fetch_inbound_media(media_info, normalized)

        return [normalized]

    def _fetch_inbound_media(self, media_info: dict, normalized: dict):
        """Download inbound WhatsApp media via Wuzapi and populate normalized.

        Best-effort: on any failure the message is still ingested as text/caption
        and media_url remains None.  Never raises.
        """
        try:
            client = self._client()
            resp = client.download_media(media_info["kind"], media_info)
            media_bytes = extract_wuzapi_base64(resp)
            if media_bytes:
                mimetype = media_info.get("media_mimetype") or ""
                ext = mimetypes.guess_extension(mimetype.split(";")[0].strip()) or ""
                filename = (
                    media_info.get("file_name")
                    or media_info.get("media_filename")
                    or f"wa-media{ext}"
                )
                normalized["media_bytes"] = media_bytes
                normalized["media_filename"] = filename
                normalized["media_mimetype"] = mimetype
        except Exception:
            frappe.log_error(
                title="WhatsApp inbound media fetch failed",
                message=frappe.get_traceback(),
            )

    @staticmethod
    def _pick(d: dict, *keys):
        """Try multiple key name variants, return the first non-None value found."""
        for k in keys:
            v = d.get(k)
            if v is not None:
                return v
        return None

    @staticmethod
    def _classify(message: dict):
        """Return (message_type, content, media_info).

        media_info is None for text/location; for media types it is a dict with
        normalised keys ready to pass to Wuzapi download.  Field names in the
        whatsmeow proto JSON are uncertain — we extract them defensively via _pick.
        """
        if message.get("conversation"):
            return "Text", message["conversation"], None
        ext = message.get("extendedTextMessage") or {}
        if ext.get("text"):
            return "Text", ext["text"], None

        _pick = WhatsAppAdapter._pick

        if message.get("imageMessage"):
            m = message["imageMessage"] or {}
            caption = _pick(m, "caption", "Caption")
            media_info = {
                "kind": "image",
                "Url": _pick(m, "url", "URL", "Url"),
                "MediaKey": _pick(m, "mediaKey", "MediaKey"),
                "Mimetype": _pick(m, "mimetype", "Mimetype", "mimeType"),
                "FileSHA256": _pick(m, "fileSha256", "fileSHA256", "FileSHA256"),
                "FileLength": _pick(m, "fileLength", "FileLength"),
                "file_name": _pick(m, "fileName", "FileName", "file_name"),
                "media_mimetype": _pick(m, "mimetype", "Mimetype", "mimeType"),
                "caption": caption,
            }
            return "Image", caption, media_info

        if message.get("documentMessage"):
            m = message["documentMessage"] or {}
            caption = _pick(m, "caption", "Caption", "title", "Title")
            media_info = {
                "kind": "document",
                "Url": _pick(m, "url", "URL", "Url"),
                "MediaKey": _pick(m, "mediaKey", "MediaKey"),
                "Mimetype": _pick(m, "mimetype", "Mimetype", "mimeType"),
                "FileSHA256": _pick(m, "fileSha256", "fileSHA256", "FileSHA256"),
                "FileLength": _pick(m, "fileLength", "FileLength"),
                "file_name": _pick(m, "fileName", "FileName", "file_name"),
                "media_mimetype": _pick(m, "mimetype", "Mimetype", "mimeType"),
                "caption": caption,
            }
            return "File", caption, media_info

        if message.get("audioMessage"):
            m = message["audioMessage"] or {}
            media_info = {
                "kind": "audio",
                "Url": _pick(m, "url", "URL", "Url"),
                "MediaKey": _pick(m, "mediaKey", "MediaKey"),
                "Mimetype": _pick(m, "mimetype", "Mimetype", "mimeType"),
                "FileSHA256": _pick(m, "fileSha256", "fileSHA256", "FileSHA256"),
                "FileLength": _pick(m, "fileLength", "FileLength"),
                "file_name": _pick(m, "fileName", "FileName", "file_name"),
                "media_mimetype": _pick(m, "mimetype", "Mimetype", "mimeType"),
                "caption": None,
            }
            return "Audio", None, media_info

        if message.get("videoMessage"):
            m = message["videoMessage"] or {}
            caption = _pick(m, "caption", "Caption")
            media_info = {
                "kind": "video",
                "Url": _pick(m, "url", "URL", "Url"),
                "MediaKey": _pick(m, "mediaKey", "MediaKey"),
                "Mimetype": _pick(m, "mimetype", "Mimetype", "mimeType"),
                "FileSHA256": _pick(m, "fileSha256", "fileSHA256", "FileSHA256"),
                "FileLength": _pick(m, "fileLength", "FileLength"),
                "file_name": _pick(m, "fileName", "FileName", "file_name"),
                "media_mimetype": _pick(m, "mimetype", "Mimetype", "mimeType"),
                "caption": caption,
            }
            return "Video", caption, media_info

        if message.get("locationMessage"):
            loc = message["locationMessage"] or {}
            return "Location", f"{loc.get('degreesLatitude')},{loc.get('degreesLongitude')}", None

        return "Text", None, None

    # -- outbound ----------------------------------------------------------

    def send_message(self, conversation_doc, *, text=None, media_path=None) -> dict:
        client = self._client()
        recipient = conversation_doc.external_conversation_id

        if media_path:
            local = self._resolve_local_file(media_path)
            mime = guess_mimetype(local)
            kind = wuzapi_kind(mime)
            data_uri = file_to_wuzapi_base64(local, mime)
            client.send_media(
                recipient,
                kind,
                data_uri,
                file_name=os.path.basename(local),
                caption=text,
            )
        else:
            client.send_text(recipient, text)

        # Wuzapi does not return a reliable provider message id; mark Sent.
        return {"external_message_id": None, "delivery_status": "Sent"}
