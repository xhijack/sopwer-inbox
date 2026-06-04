# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Shared Meta (Facebook / Instagram) channel adapter base.

Both Facebook Messenger and Instagram DM share ~90% of the Graph API surface:
same Page Access Token, same send endpoint, same webhook envelope, same inbound
media CDN URL pattern.  This base class captures all shared logic; thin
subclasses in meta.py set PLATFORM / WEBHOOK_OBJECT and may override hooks.
"""

import hashlib
import hmac
import json
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

# Attachment type → Graph API kind
_MIME_TO_KIND = {
    "image": "image",
    "video": "video",
    "audio": "audio",
}


def meta_attachment_kind(mimetype: str) -> str:
    """Map a mimetype to the Graph API attachment type string.

    Returns 'image', 'video', 'audio', or 'file' (fallback).
    """
    if not mimetype:
        return "file"
    top = mimetype.split("/")[0].lower()
    return _MIME_TO_KIND.get(top, "file")


def _unix_ms_to_site_tz(unix_ms):
    """Meta timestamps are Unix milliseconds UTC. Convert to site timezone (naive)."""
    try:
        utc_naive = datetime.utcfromtimestamp(int(unix_ms) / 1000)
        return frappe.utils.convert_utc_to_system_timezone(utc_naive).replace(tzinfo=None)
    except Exception:
        return now_datetime()


class MetaBaseAdapter(BaseChannelAdapter):
    """Shared adapter for Facebook Messenger and Instagram DM.

    Subclasses must set:
        PLATFORM       = "messenger" | "instagram"
        WEBHOOK_OBJECT = "page"      | "instagram"
    """

    PLATFORM = None
    WEBHOOK_OBJECT = None

    # -- helpers ---------------------------------------------------------------

    def _api_version(self):
        return (self.channel.get("meta_api_version") or "v21.0").strip()

    def _graph_url(self, path):
        return f"https://graph.facebook.com/{self._api_version()}/{path.lstrip('/')}"

    def _token(self):
        token = self.channel.get_password("meta_page_access_token", raise_exception=False)
        if not token:
            frappe.throw(
                _("Channel {0}: Page Access Token is not configured.").format(self.channel.name)
            )
        return token

    def _page_id(self):
        page_id = self.channel.get("meta_page_id") or ""
        if not page_id:
            frappe.throw(
                _("Channel {0}: Page ID / IG User ID is not configured.").format(self.channel.name)
            )
        return page_id

    def _fetch_profile(self, psid):
        """Best-effort: GET /{psid}?fields=name to resolve a display name.

        Never raises — on any failure returns None (id will be used as fallback).
        """
        try:
            resp = requests.get(
                self._graph_url(psid),
                params={"fields": "name", "access_token": self._token()},
                timeout=TIMEOUT,
            )
            data = resp.json()
            return data.get("name")
        except Exception:
            frappe.log_error(
                title="Meta _fetch_profile failed",
                message=frappe.get_traceback(),
            )
            return None

    def _resolve_local_file(self, media_path):
        """Map a Frappe file_url (/files/.. or /private/files/..) to an absolute path."""
        name = frappe.db.get_value("File", {"file_url": media_path}, "name")
        if name:
            return frappe.get_doc("File", name).get_full_path()
        frappe.throw(_("Cannot resolve media file: {0}").format(media_path))

    def _upload_attachment(self, local_path):
        """Upload a local file as a reusable Meta attachment.

        Returns the attachment_id string from the Graph API response.
        """
        token = self._token()
        page_id = self._page_id()
        mimetype, _ = mimetypes.guess_type(local_path)
        mimetype = mimetype or "application/octet-stream"
        kind = meta_attachment_kind(mimetype)
        basename = os.path.basename(local_path)

        with open(local_path, "rb") as fh:
            resp = requests.post(
                self._graph_url(f"{page_id}/message_attachments"),
                data={
                    "message": json.dumps(
                        {"attachment": {"type": kind, "payload": {"is_reusable": True}}}
                    )
                },
                files={"filedata": (basename, fh, mimetype)},
                params={"access_token": token},
                timeout=TIMEOUT_UPLOAD,
            )
        resp.raise_for_status()
        attachment_id = resp.json().get("attachment_id")
        if not attachment_id:
            frappe.throw(
                _("Meta attachment upload did not return attachment_id: {0}").format(resp.text[:200])
            )
        return attachment_id

    # -- inbound ---------------------------------------------------------------

    def parse_inbound(self, event: dict) -> list[dict]:
        """Normalize ONE Meta messaging event into a list of normalized dicts.

        Returns [] for echoes, delivery/read receipts, or events with no message.
        """
        message = event.get("message")
        if not message:
            return []

        # Skip echo events (messages sent by the page itself)
        if message.get("is_echo"):
            return []

        # Skip delivery / read receipts (they have no mid at this level)
        mid = message.get("mid")
        if not mid:
            return []

        sender = (event.get("sender") or {}).get("id")
        if not sender:
            return []

        ts_raw = event.get("timestamp")
        timestamp = _unix_ms_to_site_tz(ts_raw) if ts_raw else now_datetime()

        # Classify message type + media_url
        message_type = "Text"
        content = message.get("text")
        media_url = None

        attachments = message.get("attachments")
        if attachments:
            att = attachments[0]
            att_type = att.get("type", "")
            payload = att.get("payload") or {}
            media_url = payload.get("url")
            if att_type == "image":
                message_type = "Image"
            elif att_type == "video":
                message_type = "Video"
            elif att_type == "audio":
                message_type = "Audio"
            elif att_type in ("file", "fallback"):
                message_type = "File"
            else:
                message_type = "File"

        # Best-effort profile fetch (never fatal)
        try:
            sender_name = self._fetch_profile(sender)
        except Exception:
            sender_name = None

        normalized = {
            "channel_type": self.channel.channel_type,
            "external_conversation_id": sender,
            "external_message_id": mid,
            "sender_external_id": sender,
            "sender_name": sender_name,
            "sender_phone": None,
            "message_type": message_type,
            "content": content,
            "media_url": media_url,
            "timestamp": timestamp,
            "raw": event,
        }
        return [normalized]

    # -- outbound --------------------------------------------------------------

    def send_message(self, conversation_doc, *, text=None, media_path=None) -> dict:
        token = self._token()
        page_id = self._page_id()
        recipient = conversation_doc.external_conversation_id

        if media_path:
            local = self._resolve_local_file(media_path)
            attachment_id = self._upload_attachment(local)
            mimetype, _ = mimetypes.guess_type(local)
            kind = meta_attachment_kind(mimetype or "")
            message_payload = {
                "attachment": {
                    "type": kind,
                    "payload": {"attachment_id": attachment_id},
                }
            }
        else:
            message_payload = {"text": text or ""}

        resp = requests.post(
            self._graph_url(f"{page_id}/messages"),
            json={
                "recipient": {"id": recipient},
                "messaging_type": "RESPONSE",
                "message": message_payload,
            },
            params={"access_token": token},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return {
            "external_message_id": resp.json().get("message_id"),
            "delivery_status": "Sent",
        }
