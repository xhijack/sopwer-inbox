# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Tests for Meta (Facebook Messenger + Instagram) channel adapters.

All network calls are mocked — this suite runs on a Frappe-only site
with no real Meta App access.
"""

import hashlib
import hmac
import json
import os
from unittest.mock import MagicMock, patch

import frappe

from sopwer_inbox.channels.meta import InstagramAdapter, MessengerAdapter
from sopwer_inbox.channels.meta_base import MetaBaseAdapter, meta_attachment_kind
from sopwer_inbox.api.webhooks import _match_meta_channel, _verify_meta_signature
from sopwer_inbox.tests.base import InboxTestCase, make_channel

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return json.load(f)


def make_meta_channel(name, channel_type, page_id, verify_token="vt-test", app_secret="secret123"):
    """Factory for Meta Inbox Channel docs."""
    if frappe.db.exists("Inbox Channel", name):
        return frappe.get_doc("Inbox Channel", name)
    doc = frappe.get_doc(
        {
            "doctype": "Inbox Channel",
            "channel_name": name,
            "channel_type": channel_type,
            "enabled": 1,
            "meta_page_id": page_id,
            # Instagram routes inbound by the IG account id (entry.id); mirror page_id
            # here so existing routing tests keep matching.
            "meta_ig_account_id": page_id if channel_type == "Instagram" else None,
            "meta_verify_token": verify_token,
            "meta_page_access_token": "token-abc",
            "meta_app_secret": app_secret,
            "meta_api_version": "v21.0",
        }
    )
    doc.insert(ignore_permissions=True)
    return doc


# ---------------------------------------------------------------------------
# meta_attachment_kind mapping
# ---------------------------------------------------------------------------

class TestMetaAttachmentKind(InboxTestCase):
    def test_image_mimetypes(self):
        self.assertEqual(meta_attachment_kind("image/jpeg"), "image")
        self.assertEqual(meta_attachment_kind("image/png"), "image")

    def test_video_mimetype(self):
        self.assertEqual(meta_attachment_kind("video/mp4"), "video")

    def test_audio_mimetype(self):
        self.assertEqual(meta_attachment_kind("audio/mpeg"), "audio")
        self.assertEqual(meta_attachment_kind("audio/ogg"), "audio")

    def test_file_fallback(self):
        self.assertEqual(meta_attachment_kind("application/pdf"), "file")
        self.assertEqual(meta_attachment_kind(""), "file")
        self.assertEqual(meta_attachment_kind(None), "file")


# ---------------------------------------------------------------------------
# _verify_meta_signature
# ---------------------------------------------------------------------------

class TestVerifyMetaSignature(InboxTestCase):
    def _make_sig(self, body: bytes, secret: str) -> str:
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    def test_valid_signature_passes(self):
        body = b'{"object":"page"}'
        sig = self._make_sig(body, "mysecret")
        self.assertTrue(_verify_meta_signature(body, sig, "mysecret"))

    def test_tampered_body_fails(self):
        body = b'{"object":"page"}'
        sig = self._make_sig(body, "mysecret")
        self.assertFalse(_verify_meta_signature(b'{"object":"tampered"}', sig, "mysecret"))

    def test_wrong_secret_fails(self):
        body = b'{"object":"page"}'
        sig = self._make_sig(body, "mysecret")
        self.assertFalse(_verify_meta_signature(body, sig, "wrongsecret"))

    def test_empty_header_fails(self):
        body = b'{"object":"page"}'
        self.assertFalse(_verify_meta_signature(body, "", "mysecret"))
        self.assertFalse(_verify_meta_signature(body, None, "mysecret"))

    def test_empty_secret_fails(self):
        body = b'{"object":"page"}'
        sig = self._make_sig(body, "mysecret")
        self.assertFalse(_verify_meta_signature(body, sig, ""))


# ---------------------------------------------------------------------------
# _match_meta_channel routing
# ---------------------------------------------------------------------------

class TestMatchMetaChannel(InboxTestCase):
    def setUp(self):
        self.ch_fb = make_meta_channel("FB Page Test", "Facebook Messenger", "111222333")
        self.ch_ig = make_meta_channel("IG Acc Test", "Instagram", "999888777")

    def test_routes_messenger_by_page_id(self):
        ch = _match_meta_channel("page", "111222333")
        self.assertIsNotNone(ch)
        self.assertEqual(ch.channel_type, "Facebook Messenger")
        self.assertEqual(ch.meta_page_id, "111222333")

    def test_routes_instagram_by_ig_id(self):
        ch = _match_meta_channel("instagram", "999888777")
        self.assertIsNotNone(ch)
        self.assertEqual(ch.channel_type, "Instagram")
        self.assertEqual(ch.meta_page_id, "999888777")

    def test_unknown_entry_id_returns_none(self):
        self.assertIsNone(_match_meta_channel("page", "000000000"))

    def test_unknown_object_type_returns_none(self):
        self.assertIsNone(_match_meta_channel("unknown_object", "111222333"))

    def test_cross_platform_no_match(self):
        # IG page ID should not match a Messenger query
        self.assertIsNone(_match_meta_channel("page", "999888777"))


# ---------------------------------------------------------------------------
# MessengerAdapter.parse_inbound
# ---------------------------------------------------------------------------

class TestMessengerParseInbound(InboxTestCase):
    def setUp(self):
        self.channel = make_meta_channel("FB Parse Test", "Facebook Messenger", "111222333")
        self.adapter = MessengerAdapter(self.channel)

    def _parse(self, fixture_name):
        fixture = load_fixture(fixture_name)
        entry = fixture["entry"][0]
        event = entry["messaging"][0]
        with patch.object(self.adapter, "_fetch_profile", return_value="Budi Test"):
            return self.adapter.parse_inbound(event)

    def test_text_message(self):
        [msg] = self._parse("meta_inbound_messenger_text.json")
        self.assertEqual(msg["channel_type"], "Facebook Messenger")
        self.assertEqual(msg["external_conversation_id"], "5551234567")
        self.assertEqual(msg["external_message_id"], "m_abc123messenger")
        self.assertEqual(msg["sender_external_id"], "5551234567")
        self.assertEqual(msg["message_type"], "Text")
        self.assertIn("pesanan", msg["content"])
        self.assertIsNone(msg["sender_phone"])
        self.assertIsNone(msg["media_url"])

    def test_image_attachment(self):
        [msg] = self._parse("meta_inbound_messenger_image.json")
        self.assertEqual(msg["message_type"], "Image")
        self.assertEqual(msg["media_url"], "https://cdn.fbsbx.com/v/images/sample.jpg")
        self.assertIsNone(msg["content"])
        self.assertEqual(msg["external_message_id"], "m_img456messenger")

    def test_echo_skipped(self):
        event = {
            "sender": {"id": "5551234567"},
            "recipient": {"id": "111222333"},
            "timestamp": 1749081600000,
            "message": {
                "mid": "m_echo",
                "is_echo": True,
                "text": "sent by page",
            },
        }
        with patch.object(self.adapter, "_fetch_profile", return_value=None):
            result = self.adapter.parse_inbound(event)
        self.assertEqual(result, [])

    def test_delivery_receipt_skipped(self):
        # Delivery receipts have no 'message' key
        event = {
            "sender": {"id": "5551234567"},
            "recipient": {"id": "111222333"},
            "timestamp": 1749081600000,
            "delivery": {"mids": ["m_abc"], "watermark": 1749081600000, "seq": 1},
        }
        with patch.object(self.adapter, "_fetch_profile", return_value=None):
            result = self.adapter.parse_inbound(event)
        self.assertEqual(result, [])

    def test_read_receipt_skipped(self):
        # Read receipts have no 'message' key
        event = {
            "sender": {"id": "5551234567"},
            "recipient": {"id": "111222333"},
            "timestamp": 1749081600000,
            "read": {"watermark": 1749081600000, "seq": 2},
        }
        with patch.object(self.adapter, "_fetch_profile", return_value=None):
            result = self.adapter.parse_inbound(event)
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# InstagramAdapter.parse_inbound
# ---------------------------------------------------------------------------

class TestInstagramParseInbound(InboxTestCase):
    def setUp(self):
        self.channel = make_meta_channel("IG Parse Test", "Instagram", "999888777")
        self.adapter = InstagramAdapter(self.channel)

    def test_text_message(self):
        fixture = load_fixture("meta_inbound_instagram_text.json")
        event = fixture["entry"][0]["messaging"][0]
        with patch.object(self.adapter, "_fetch_profile", return_value="Citra IG"):
            [msg] = self.adapter.parse_inbound(event)
        self.assertEqual(msg["channel_type"], "Instagram")
        self.assertEqual(msg["external_conversation_id"], "6661234567")
        self.assertEqual(msg["external_message_id"], "m_abcinstagram")
        self.assertEqual(msg["message_type"], "Text")
        self.assertIn("DM", msg["content"])


# ---------------------------------------------------------------------------
# MessengerAdapter.send_message — text
# ---------------------------------------------------------------------------

class TestMessengerSendMessage(InboxTestCase):
    def setUp(self):
        self.channel = make_meta_channel("FB Send Test", "Facebook Messenger", "111222333")
        self.adapter = MessengerAdapter(self.channel)

    def test_send_text(self):
        fake_resp = MagicMock()
        fake_resp.json.return_value = {"message_id": "mid.send.abc"}
        fake_resp.raise_for_status = MagicMock()

        conv = MagicMock(external_conversation_id="5551234567")

        with patch("sopwer_inbox.channels.meta_base.requests.post", return_value=fake_resp) as post:
            result = self.adapter.send_message(conv, text="Halo balik dari FB")

        self.assertEqual(result["delivery_status"], "Sent")
        self.assertEqual(result["external_message_id"], "mid.send.abc")

        call_args = post.call_args
        url = call_args.args[0]
        self.assertIn("111222333/messages", url)
        self.assertIn("v21.0", url)

        body = call_args.kwargs["json"]
        self.assertEqual(body["recipient"]["id"], "5551234567")
        self.assertEqual(body["messaging_type"], "RESPONSE")
        self.assertEqual(body["message"]["text"], "Halo balik dari FB")

    def test_send_media(self):
        fake_send_resp = MagicMock()
        fake_send_resp.json.return_value = {"message_id": "mid.media.xyz"}
        fake_send_resp.raise_for_status = MagicMock()

        conv = MagicMock(external_conversation_id="5551234567")

        with patch.object(self.adapter, "_resolve_local_file", return_value="/tmp/test.jpg"), \
             patch.object(self.adapter, "_upload_attachment", return_value="att-999") as upload, \
             patch("sopwer_inbox.channels.meta_base.requests.post", return_value=fake_send_resp) as post:
            result = self.adapter.send_message(conv, media_path="/private/files/test.jpg")

        self.assertEqual(result["delivery_status"], "Sent")
        self.assertEqual(result["external_message_id"], "mid.media.xyz")
        upload.assert_called_once_with("/tmp/test.jpg")

        # Check the send payload references attachment_id
        send_call = post.call_args
        body = send_call.kwargs["json"]
        self.assertEqual(body["message"]["attachment"]["payload"]["attachment_id"], "att-999")


# ---------------------------------------------------------------------------
# GET challenge endpoint (via webhooks module directly)
# ---------------------------------------------------------------------------

class TestMetaWebhookGet(InboxTestCase):
    def setUp(self):
        self.channel = make_meta_channel("FB WH Test", "Facebook Messenger", "111222333",
                                         verify_token="tok-correct")

    def test_matching_verify_token_returns_challenge(self):
        """The GET handler must return the challenge when verify_token matches."""
        from sopwer_inbox.api.webhooks import meta as meta_endpoint
        from unittest.mock import patch as _patch

        mock_req = MagicMock()
        mock_req.method = "GET"
        mock_req.args = {
            "hub.mode": "subscribe",
            "hub.verify_token": "tok-correct",
            "hub.challenge": "CHALLENGE_RESPONSE",
        }

        with _patch("frappe.request", mock_req):
            resp = meta_endpoint()

        # Should be a werkzeug Response with the challenge text
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"CHALLENGE_RESPONSE", resp.get_data())

    def test_wrong_verify_token_returns_403(self):
        from sopwer_inbox.api.webhooks import meta as meta_endpoint
        from unittest.mock import patch as _patch

        mock_req = MagicMock()
        mock_req.method = "GET"
        mock_req.args = {
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "CHALLENGE_RESPONSE",
        }

        with _patch("frappe.request", mock_req):
            resp = meta_endpoint()

        self.assertEqual(resp.status_code, 403)
