# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Self-contained Wuzapi HTTP client + media helpers.

Ported from ``whatsapp.setup.media`` and ``whatsapp.setup.wuzapi`` so the
inbox can talk to Wuzapi directly without importing the ``whatsapp`` app.
Intentionally Frappe-free so the helpers are unit-testable standalone.
"""

import base64
import mimetypes
import re
import uuid
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Media helpers (ported from whatsapp.setup.media)
# ---------------------------------------------------------------------------

# WhatsApp voice notes require Opus-in-Ogg. Other audio (mp3, m4a) is sent as a
# document so Wuzapi does not reject it for not being Opus.
_AUDIO_INLINE = {"audio/ogg", "audio/opus", "audio/ogg; codecs=opus"}

_DATA_URI_RE = re.compile(r"^data:[^;]+;base64,", re.IGNORECASE)


def guess_mimetype(file_path: str) -> str:
    return mimetypes.guess_type(file_path)[0] or "application/octet-stream"


def wuzapi_kind(mimetype: str | None) -> str:
    """Map a MIME type to the Wuzapi send endpoint kind."""
    m = (mimetype or "").lower()
    if m.startswith("image/"):
        return "image"
    if m.startswith("video/"):
        return "video"
    if m in _AUDIO_INLINE:
        return "audio"
    return "document"


def file_to_wuzapi_base64(file_path: str, mimetype: str | None = None) -> str:
    """Read a local file and return a Wuzapi data URI (``data:<mime>;base64,<…>``)."""
    data = Path(file_path).read_bytes()
    b64_str = base64.b64encode(data).decode("ascii")
    mime = mimetype or guess_mimetype(file_path)
    return f"data:{mime};base64,{b64_str}"


def decode_data_uri(s: str) -> bytes | None:
    """Strip an optional ``data:<mime>;base64,`` prefix and decode the payload.

    Returns the raw bytes, or ``None`` if ``s`` is not valid base64.
    """
    if not s:
        return None
    stripped = _DATA_URI_RE.sub("", s.strip())
    # base64 requires padding — add it if missing.
    padding = (4 - len(stripped) % 4) % 4
    stripped += "=" * padding
    try:
        return base64.b64decode(stripped)
    except Exception:
        return None


def extract_wuzapi_base64(resp: dict) -> bytes | None:
    """Defensively extract and decode media bytes from a Wuzapi download response.

    Tries several known and plausible paths before scanning all string values:

    1. ``resp["data"]["Data"]``   — observed in some Wuzapi builds
    2. ``resp["Data"]``           — top-level variant
    3. ``resp["data"]``           — when data is itself the b64 string
    4. ``resp["base64"]``         — alternative key name
    5. Any string value in ``resp`` or ``resp["data"]`` that looks like base64
       (min 20 chars — may carry a data-URI prefix).

    Returns decoded bytes, or ``None`` if nothing decodable was found.
    """
    if not isinstance(resp, dict):
        return None

    candidates: list[str] = []

    data_block = resp.get("data")
    if isinstance(data_block, dict):
        for key in ("Data", "data", "base64", "Base64"):
            v = data_block.get(key)
            if isinstance(v, str):
                candidates.append(v)
    elif isinstance(data_block, str):
        candidates.append(data_block)

    for key in ("Data", "base64", "Base64"):
        v = resp.get(key)
        if isinstance(v, str):
            candidates.append(v)

    def _collect_strings(d):
        if not isinstance(d, dict):
            return
        for v in d.values():
            if isinstance(v, str) and v not in candidates:
                candidates.append(v)

    _collect_strings(resp)
    if isinstance(data_block, dict):
        _collect_strings(data_block)

    _B64_RE = re.compile(r"^[A-Za-z0-9+/=\r\n]{20,}$")

    for candidate in candidates:
        stripped = _DATA_URI_RE.sub("", candidate.strip())
        if _B64_RE.match(stripped):
            decoded = decode_data_uri(candidate)
            if decoded is not None:
                return decoded

    return None


# ---------------------------------------------------------------------------
# WuzapiClient
# ---------------------------------------------------------------------------

class WuzapiError(Exception):
    """Wuzapi accepted the HTTP request but reported a failed send."""


class WuzapiClient:
    """Thin HTTP client for the Wuzapi REST API."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict:
        return {"Content-Type": "application/json", "Token": self.token}

    def _check(self, resp) -> dict:
        """Raise on a failed send. Wuzapi can return HTTP 200 with
        ``{"success": false, "error": "..."}`` — without this, the caller would
        wrongly treat it as delivered."""
        resp.raise_for_status()
        try:
            body = resp.json()
        except Exception:
            return {}
        if isinstance(body, dict) and body.get("success") is False:
            raise WuzapiError(str(body.get("error") or body.get("data") or "Wuzapi send gagal"))
        return body

    def send_text(self, to: str, body: str) -> dict:
        """POST /chat/send/text — plain text message."""
        url = f"{self.base_url}/chat/send/text"
        payload = {
            "Phone": to,
            "Body": body or "",
            "Id": str(uuid.uuid4()),
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=20)
        return self._check(resp)

    def send_media(
        self,
        to: str,
        kind: str,
        data_uri: str,
        file_name: str | None = None,
        caption: str | None = None,
    ) -> dict:
        """POST /chat/send/{kind} — image | video | audio | document.

        Payload key is the capitalized kind (Image/Video/Audio/Document).
        Caption is included for image, video, document; omitted for audio.
        FileName is included for document.
        """
        url = f"{self.base_url}/chat/send/{kind}"
        payload: dict = {
            kind.capitalize(): data_uri,
            "Phone": to,
            "Id": str(uuid.uuid4()),
        }
        if kind != "audio":
            payload["Caption"] = caption or ""
        if kind == "document" and file_name:
            payload["FileName"] = file_name
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=20)
        return self._check(resp)

    def download_media(self, kind: str, info: dict) -> dict:
        """POST /chat/download{kind} — decrypt inbound WhatsApp media.

        kind: one of image|video|audio|document.
        info: dict from the inbound webhook. Must carry DirectPath + FileEncSHA256
        in addition to Url/MediaKey/Mimetype/FileSHA256/FileLength — without them
        whatsmeow cannot fetch/verify the media and returns "invalid media hmac".
        Returns the raw Wuzapi JSON response dict.
        """
        url = f"{self.base_url}/chat/download{kind}"
        payload = {
            "Url": info.get("Url"),
            "DirectPath": info.get("DirectPath"),
            "MediaKey": info.get("MediaKey"),
            "Mimetype": info.get("Mimetype"),
            "FileEncSHA256": info.get("FileEncSHA256"),
            "FileSHA256": info.get("FileSHA256"),
            "FileLength": info.get("FileLength"),
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=20)
        return resp.json()
