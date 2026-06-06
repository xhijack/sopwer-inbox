# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""WhatsApp channel adapter — talks to Wuzapi directly via Inbox Channel fields.

Outbound: reads ``wuzapi_base_url`` + ``wuzapi_token`` from the Inbox Channel
and calls Wuzapi's REST API directly (no dependency on the ``whatsapp`` app).

Inbound: arrives via the new ``sopwer_inbox.api.webhooks.wuzapi`` endpoint
(point the Wuzapi session webhook at that URL).  ``parse_inbound`` normalises
the Wuzapi/whatsmeow event shape — unchanged from before.
"""

import datetime
import json
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


def _conv_id(jid: str) -> str:
    """Conversation identity AND outbound send-to address for WhatsApp.

    Phone-number JIDs (``…@s.whatsapp.net`` / ``…@c.us``) collapse to bare digits
    — unchanged, and Wuzapi delivers to bare digits.  ``@lid`` JIDs MUST keep
    their suffix: a bare LID like ``41107182346431`` is NOT a phone number, so
    Wuzapi accepts a send to it (HTTP 200, "Sent") but silently never delivers.
    Sending the full ``…@lid`` JID does deliver."""
    if jid and jid.endswith("@lid"):
        return jid
    return _strip_jid(jid)


def _phone_jid(info: dict) -> str | None:
    """Best-effort real phone number (bare digits) from the inbound event.

    Newer WhatsApp accounts are addressed by a ``@lid`` alias; the actual phone
    number rides along in an alt field (whatsmeow ``SenderAlt``/``RecipientAlt``).
    Scan every value defensively so JSON field-name variants still work.  Returns
    ``None`` when no ``@s.whatsapp.net`` JID is present."""
    for v in (info or {}).values():
        if isinstance(v, str) and v.endswith("@s.whatsapp.net"):
            return _strip_jid(v)
    return None


def _wuzapi_timestamp(value):
    """Wuzapi (whatsmeow) timestamps are RFC3339 with a timezone offset, e.g.
    ``2026-06-06T09:29:23+07:00``. MariaDB datetime columns reject tz-aware values,
    so convert to a NAIVE datetime in the site timezone (matching now_datetime())."""
    if not value:
        return frappe.utils.now_datetime()
    try:
        dt = frappe.utils.get_datetime(value)
    except Exception:
        return frappe.utils.now_datetime()
    if dt.tzinfo is not None:
        utc_naive = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        dt = frappe.utils.convert_utc_to_system_timezone(utc_naive)
        if getattr(dt, "tzinfo", None) is not None:
            dt = dt.replace(tzinfo=None)
    return dt


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

        # TEMP DIAGNOSTIC (remove after recipient/LID fix is confirmed): dump the
        # full Info so we can see which field carries the real phone-number JID
        # (@s.whatsapp.net) vs the @lid alias. ERROR level — logger sits at 40.
        try:
            frappe.logger("sopwer_inbox", allow_site=True).error(
                "WA-IN-TRACE info=%s", json.dumps(info)[:2500]
            )
        except Exception:
            pass

        # Wuzapi emits an event for EVERY message on the session, including ones
        # sent by the connected account itself (from the phone). Those must not
        # enter the inbox as inbound — they'd appear to come from the customer.
        if info.get("IsFromMe") or info.get("FromMe") or info.get("is_from_me"):
            return []

        chat = _conv_id(info.get("Chat") or info.get("Sender"))
        local = _strip_jid(chat)
        # Only accept 1:1 customer chats. Group (@g.us), broadcast/status, and
        # newsletter JIDs strip to non-numeric ids (e.g. "62...-1426388101") that
        # are not valid phone numbers — skip them entirely (don't enter the inbox).
        if not local or not local.isdigit():
            return []

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
            "sender_phone": _phone_jid(info) or local,
            "message_type": message_type,
            "content": content,
            "media_url": None,
            "timestamp": _wuzapi_timestamp(info.get("Timestamp")),
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
        resp = None
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
                return
        except Exception:
            frappe.log_error(
                title="WhatsApp inbound media fetch failed",
                message=frappe.get_traceback(),
            )
            return

        # No exception but no bytes — surface WHY (param vs response shape) so the
        # real Wuzapi field names / download response can be debugged from the UI.
        try:
            present = {k: bool(media_info.get(k)) for k in
                       ("Url", "MediaKey", "Mimetype", "FileSHA256", "FileLength")}
            frappe.log_error(
                title="WhatsApp inbound media: no bytes",
                message="kind={0}\nparams_present={1}\nresp={2}\nraw_message={3}".format(
                    media_info.get("kind"),
                    present,
                    (json.dumps(resp) if isinstance(resp, (dict, list)) else str(resp))[:2500],
                    json.dumps((normalized.get("raw") or {}).get("event", {}).get("Message", {}))[:3000],
                ),
            )
        except Exception:
            pass

    @staticmethod
    def _pick(d: dict, *keys):
        """Try multiple key name variants, return the first non-None value found."""
        for k in keys:
            v = d.get(k)
            if v is not None:
                return v
        return None

    @staticmethod
    def _media_info(m: dict, kind: str, caption) -> dict:
        """Normalise a whatsmeow media proto into the dict Wuzapi download needs.

        Includes DirectPath + FileEncSHA256: Wuzapi's download struct requires
        them to fetch and verify the encrypted media — omitting them makes every
        download fail with "invalid media hmac".  Field names in the proto JSON
        vary, so extract defensively via _pick."""
        _pick = WhatsAppAdapter._pick
        return {
            "kind": kind,
            "Url": _pick(m, "url", "URL", "Url"),
            "DirectPath": _pick(m, "directPath", "DirectPath", "direct_path"),
            "MediaKey": _pick(m, "mediaKey", "MediaKey"),
            "Mimetype": _pick(m, "mimetype", "Mimetype", "mimeType"),
            "FileEncSHA256": _pick(m, "fileEncSha256", "fileEncSHA256", "FileEncSHA256"),
            "FileSHA256": _pick(m, "fileSha256", "fileSHA256", "FileSHA256"),
            "FileLength": _pick(m, "fileLength", "FileLength"),
            "file_name": _pick(m, "fileName", "FileName", "file_name"),
            "media_mimetype": _pick(m, "mimetype", "Mimetype", "mimeType"),
            "caption": caption,
        }

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

        _media_info = WhatsAppAdapter._media_info

        if message.get("imageMessage"):
            m = message["imageMessage"] or {}
            caption = _pick(m, "caption", "Caption")
            return "Image", caption, _media_info(m, "image", caption)

        if message.get("documentMessage"):
            m = message["documentMessage"] or {}
            caption = _pick(m, "caption", "Caption", "title", "Title")
            return "File", caption, _media_info(m, "document", caption)

        if message.get("audioMessage"):
            m = message["audioMessage"] or {}
            return "Audio", None, _media_info(m, "audio", None)

        if message.get("videoMessage"):
            m = message["videoMessage"] or {}
            caption = _pick(m, "caption", "Caption")
            return "Video", caption, _media_info(m, "video", caption)

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
            resp = client.send_media(
                recipient,
                kind,
                data_uri,
                file_name=os.path.basename(local),
                caption=text,
            )
        else:
            resp = client.send_text(recipient, text)

        result = self._send_result(resp)
        self._trace_outbound(recipient, resp, result, media=bool(media_path))
        return result

    @staticmethod
    def _trace_outbound(recipient, resp, result, *, media):
        """TEMP DIAGNOSTIC (remove once outbound delivery is confirmed): trace
        EVERY outbound send to logs/sopwer_inbox.log — including ones Wuzapi
        reports as success — so a 'success but never delivered' send is visible.
        Logged at ERROR level on purpose: the sopwer_inbox logger is configured
        at level 40, so WARNING/INFO would be filtered and never written."""
        try:
            raw = json.dumps(resp) if isinstance(resp, (dict, list)) else str(resp)
            frappe.logger("sopwer_inbox", allow_site=True).error(
                "WA-OUT-TRACE to=%s media=%s status=%s id=%s resp=%s",
                recipient, media, result.get("delivery_status"),
                result.get("external_message_id"), raw[:2000],
            )
        except Exception:
            pass

    @staticmethod
    def _send_result(resp) -> dict:
        """Map Wuzapi's send response onto inbox delivery fields.

        Wuzapi acknowledges a real send as
        ``{"code":200,"success":true,"data":{"Id":"3EB0..","Details":"Sent"}}``.
        ``_check`` already raised on ``success:false``, so here we only need to
        tell a genuine ack apart from an ambiguous body.  When there is NO clear
        ack we must NOT report "Sent": Wuzapi can accept (HTTP 200) a send onto a
        disconnected/logged-out session and silently never deliver it.  Mark it
        "Pending" and log the raw response so the failure is never invisible.
        """
        data = resp.get("data") if isinstance(resp, dict) else None
        msg_id = data.get("Id") or data.get("id") if isinstance(data, dict) else None
        acked = bool(msg_id) or (isinstance(resp, dict) and resp.get("success") is True)
        if acked:
            return {
                "external_message_id": str(msg_id)[:500] if msg_id else None,
                "delivery_status": "Sent",
            }
        frappe.log_error(
            title="WhatsApp outbound: no Wuzapi ack",
            message=(json.dumps(resp) if isinstance(resp, (dict, list)) else str(resp))[:3000],
        )
        return {"external_message_id": None, "delivery_status": "Pending"}
