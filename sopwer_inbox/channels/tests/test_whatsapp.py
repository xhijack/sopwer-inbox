# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import frappe

from sopwer_inbox.channels.whatsapp import WhatsAppAdapter, _strip_jid, _wuzapi_timestamp
from sopwer_inbox.tests.base import InboxTestCase, make_channel

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return json.load(f)


class TestWhatsAppAdapter(InboxTestCase):
    def setUp(self):
        self.channel = make_channel(
            "WA Pilot",
            "WhatsApp",
            wuzapi_base_url="http://wuzapi.test",
            wuzapi_token="tok-test",
        )
        self.adapter = WhatsAppAdapter(self.channel)

    def test_parse_skips_group_chat(self):
        # Group/broadcast JIDs strip to a non-numeric id → must be skipped.
        event = {
            "event": {
                "Info": {"ID": "G1", "Chat": "6289655086045-1426388101@g.us",
                         "Sender": "628111@s.whatsapp.net"},
                "Message": {"conversation": "halo grup"},
            }
        }
        self.assertEqual(self.adapter.parse_inbound(event), [])

    def test_parse_skips_group_with_alldigit_id(self):
        # A group whose JID strips to ALL digits must still be skipped — reject by
        # the @g.us suffix, not by the digit-shape heuristic.
        event = {
            "event": {
                "Info": {"ID": "G2", "Chat": "123456789012345@g.us",
                         "Sender": "628111@s.whatsapp.net"},
                "Message": {"conversation": "halo grup numerik"},
            }
        }
        self.assertEqual(self.adapter.parse_inbound(event), [])

    def test_parse_skips_when_isgroup_flag(self):
        # whatsmeow marks group messages with IsGroup=true → skip regardless of JID.
        event = {
            "event": {
                "Info": {"ID": "G3", "Chat": "628111@s.whatsapp.net",
                         "Sender": "628111@s.whatsapp.net", "IsGroup": True},
                "Message": {"conversation": "halo"},
            }
        }
        self.assertEqual(self.adapter.parse_inbound(event), [])

    def test_parse_skips_newsletter_and_broadcast(self):
        for chat in ("120363000000000000@newsletter", "status@broadcast",
                     "1234567890@broadcast"):
            event = {
                "event": {
                    "Info": {"ID": "N-" + chat, "Chat": chat,
                             "Sender": "628111@s.whatsapp.net"},
                    "Message": {"conversation": "x"},
                }
            }
            self.assertEqual(self.adapter.parse_inbound(event), [], chat)

    def test_parse_skips_group_via_participant_field(self):
        # Leak symptom: a group message whose Chat/IsGroup are absent but which
        # still carries Participant (the member who sent it). Without this guard
        # it would fall back to the participant's real number and enter the inbox
        # showing the individual sender's name. Must be skipped.
        event = {
            "event": {
                "Info": {"ID": "GP1",
                         "Sender": "628111@s.whatsapp.net",
                         "Participant": "628111@s.whatsapp.net",
                         "PushName": "Orang di Grup"},
                "Message": {"conversation": "halo dari grup tanpa Chat"},
            }
        }
        self.assertEqual(self.adapter.parse_inbound(event), [])

    def test_parse_skips_from_me(self):
        # Messages sent from the phone (IsFromMe) must NOT enter the inbox.
        event = {
            "event": {
                "Info": {"ID": "X1", "Chat": "628999@s.whatsapp.net",
                         "Sender": "628111@s.whatsapp.net", "IsFromMe": True},
                "Message": {"conversation": "halo dari hp"},
            }
        }
        self.assertEqual(self.adapter.parse_inbound(event), [])

    def test_wuzapi_timestamp_strips_tzinfo(self):
        # RFC3339 with offset must become a naive datetime (MariaDB rejects offsets).
        dt = _wuzapi_timestamp("2026-06-06T09:29:23+07:00")
        self.assertIsNone(dt.tzinfo)

    def test_wuzapi_timestamp_none_falls_back_to_now(self):
        self.assertIsNotNone(_wuzapi_timestamp(None))

    def test_strip_jid(self):
        self.assertEqual(_strip_jid("628123344556@s.whatsapp.net"), "628123344556")
        self.assertEqual(_strip_jid("628123:1@c.us"), "628123")

    def test_parse_wuzapi_text(self):
        [msg] = self.adapter.parse_inbound(load_fixture("wuzapi_inbound_text.json"))
        self.assertEqual(msg["channel_type"], "WhatsApp")
        self.assertEqual(msg["external_conversation_id"], "628123344556")
        self.assertEqual(msg["external_message_id"], "3EB0XYZ123")
        self.assertEqual(msg["sender_name"], "Budi Santoso")
        self.assertEqual(msg["sender_phone"], "628123344556")
        self.assertIn("pesanan", msg["content"])

    def test_parse_non_message_returns_empty(self):
        self.assertEqual(self.adapter.parse_inbound({"type": "ReadReceipt", "event": {}}), [])

    def test_parse_lid_keeps_suffix_for_delivery(self):
        """A @lid sender (newer WhatsApp privacy alias) is NOT a phone number.
        Wuzapi accepts a bare-LID send (HTTP 200) but never delivers it, so the
        @lid suffix MUST be kept on external_conversation_id for outbound to work.
        The real phone number rides along in an alt field → use it for display."""
        event = {
            "event": {
                "Info": {
                    "ID": "LID1", "Chat": "41107182346431@lid",
                    "Sender": "41107182346431@lid",
                    "SenderAlt": "62818889344@s.whatsapp.net",
                    "AddressingMode": "lid", "PushName": "Pak Budi",
                },
                "Message": {"conversation": "halo via lid"},
            }
        }
        [msg] = self.adapter.parse_inbound(event)
        self.assertEqual(msg["external_conversation_id"], "41107182346431@lid")
        self.assertEqual(msg["sender_phone"], "62818889344")

    def test_classify_image_extracts_directpath_and_fileenc(self):
        """Wuzapi download needs DirectPath + FileEncSHA256 (real whatsmeow proto
        field names directPath / fileEncSHA256), else it fails 'invalid media hmac'."""
        msg = {
            "imageMessage": {
                "URL": "https://mmg.whatsapp.net/x.enc",
                "directPath": "/v/x.enc",
                "mediaKey": "cHjjKEY=",
                "mimetype": "image/jpeg",
                "fileEncSHA256": "z7gKENC=",
                "fileSHA256": "T4BYSHA=",
                "fileLength": 140845,
            }
        }
        mtype, _content, info = self.adapter._classify(msg)
        self.assertEqual(mtype, "Image")
        self.assertEqual(info["Url"], "https://mmg.whatsapp.net/x.enc")
        self.assertEqual(info["DirectPath"], "/v/x.enc")
        self.assertEqual(info["MediaKey"], "cHjjKEY=")
        self.assertEqual(info["FileEncSHA256"], "z7gKENC=")
        self.assertEqual(info["FileSHA256"], "T4BYSHA=")

    def test_parse_lid_not_skipped_as_group(self):
        # A @lid 1:1 chat must NOT be filtered out by the group/broadcast guard.
        event = {
            "event": {
                "Info": {"ID": "LID2", "Chat": "41107182346431@lid",
                         "Sender": "41107182346431@lid"},
                "Message": {"conversation": "hi"},
            }
        }
        self.assertEqual(len(self.adapter.parse_inbound(event)), 1)

    def test_send_to_lid_conversation_uses_full_jid(self):
        """Replying to a @lid conversation must send the full JID (proven to
        deliver), not the bare LID digits."""
        mock_client = MagicMock()
        mock_client.send_text.return_value = {"success": True, "data": {"Id": "x"}}
        conv = frappe.get_doc(
            {
                "doctype": "Inbox Conversation",
                "channel": self.channel.name,
                "external_conversation_id": "41107182346431@lid",
            }
        )
        with patch.object(self.adapter, "_client", return_value=mock_client):
            self.adapter.send_message(conv, text="balas")
        mock_client.send_text.assert_called_once_with("41107182346431@lid", "balas")

    def test_resolve_local_file_returns_existing_path(self):
        """file_url must be resolved to a real on-disk path for base64 encoding."""
        f = frappe.get_doc(
            {"doctype": "File", "file_name": "wa-test.png", "content": "hello"}
        ).insert(ignore_permissions=True)
        path = self.adapter._resolve_local_file(f.file_url)
        self.assertTrue(os.path.exists(path))

    def test_resolve_local_file_throws_when_missing(self):
        with self.assertRaises(frappe.ValidationError):
            self.adapter._resolve_local_file("/files/does-not-exist-zzz.png")

    # -- config validation ------------------------------------------------

    def test_send_requires_wuzapi_config(self):
        """Channel without wuzapi_base_url/token must raise ValidationError loudly."""
        bare_channel = make_channel("WA Bare Config", "WhatsApp")
        adapter = WhatsAppAdapter(bare_channel)
        conv = frappe.get_doc(
            {
                "doctype": "Inbox Conversation",
                "channel": bare_channel.name,
                "external_conversation_id": "628000",
            }
        )
        with self.assertRaises(frappe.ValidationError):
            adapter.send_message(conv, text="hi")

    # -- outbound send_text via mock client --------------------------------

    def test_send_text_calls_client_send_text(self):
        """send_message(text=...) must call client.send_text with recipient + text,
        report Sent, and capture Wuzapi's real message id from data.Id."""
        mock_client = MagicMock()
        mock_client.send_text.return_value = {
            "code": 200,
            "success": True,
            "data": {"Id": "3EB0ACK123", "Details": "Sent"},
        }
        conv = frappe.get_doc(
            {
                "doctype": "Inbox Conversation",
                "channel": self.channel.name,
                "external_conversation_id": "628999",
            }
        )
        with patch.object(self.adapter, "_client", return_value=mock_client):
            result = self.adapter.send_message(conv, text="Hello!")
        mock_client.send_text.assert_called_once_with("628999", "Hello!")
        self.assertEqual(result["delivery_status"], "Sent")
        self.assertEqual(result["external_message_id"], "3EB0ACK123")

    def test_send_text_pending_when_no_wuzapi_ack(self):
        """A response WITHOUT data.Id / success:true must NOT be reported as Sent.
        Wuzapi can accept (HTTP 200) a send onto a disconnected session and never
        deliver it — reporting that as Sent hides a silent black hole. Mark Pending."""
        mock_client = MagicMock()
        mock_client.send_text.return_value = {"ok": 1}  # ambiguous: no Id, no success
        conv = frappe.get_doc(
            {
                "doctype": "Inbox Conversation",
                "channel": self.channel.name,
                "external_conversation_id": "628999",
            }
        )
        with patch.object(self.adapter, "_client", return_value=mock_client):
            result = self.adapter.send_message(conv, text="Hello!")
        self.assertEqual(result["delivery_status"], "Pending")
        self.assertIsNone(result["external_message_id"])

    # -- outbound send_media via mock client -------------------------------

    def test_send_media_calls_client_send_media(self):
        """send_message(media_path=...) must resolve the file, detect kind, call send_media."""
        mock_client = MagicMock()
        mock_client.send_media.return_value = {
            "code": 200,
            "success": True,
            "data": {"Id": "3EB0MEDIA9", "Details": "Sent"},
        }
        conv = frappe.get_doc(
            {
                "doctype": "Inbox Conversation",
                "channel": self.channel.name,
                "external_conversation_id": "628888",
            }
        )
        # Create a real temporary PNG so file_to_wuzapi_base64 can read it.
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(b"\x89PNG\r\n\x1a\n")
            tmp_path = tmp.name
        try:
            with patch.object(self.adapter, "_client", return_value=mock_client):
                with patch.object(
                    self.adapter, "_resolve_local_file", return_value=tmp_path
                ):
                    result = self.adapter.send_message(
                        conv, text="caption", media_path="/files/fake.png"
                    )
            self.assertTrue(mock_client.send_media.called)
            call_kwargs = mock_client.send_media.call_args
            # kind should be "image" for a .png file
            self.assertEqual(call_kwargs.args[1], "image")
            self.assertEqual(result["delivery_status"], "Sent")
        finally:
            os.unlink(tmp_path)

    # -- _pick helper -----------------------------------------------------

    def test_pick_returns_first_matching_key(self):
        d = {"mediaKey": "correct", "MediaKey": "wrong"}
        result = WhatsAppAdapter._pick(d, "mediaKey", "MediaKey")
        self.assertEqual(result, "correct")

    def test_pick_falls_through_to_second_key(self):
        d = {"MediaKey": "fallback"}
        result = WhatsAppAdapter._pick(d, "mediaKey", "MediaKey")
        self.assertEqual(result, "fallback")

    def test_pick_returns_none_when_all_missing(self):
        self.assertIsNone(WhatsAppAdapter._pick({}, "url", "URL", "Url"))

    # -- _classify with image fixture -------------------------------------

    def test_classify_image_returns_media_info(self):
        payload = load_fixture("wuzapi_inbound_image.json")
        msg_dict = payload["event"]["Message"]
        message_type, content, media_info = WhatsAppAdapter._classify(msg_dict)
        self.assertEqual(message_type, "Image")
        self.assertEqual(content, "Ini foto pesanan saya")
        self.assertIsNotNone(media_info)
        self.assertEqual(media_info["kind"], "image")
        self.assertIsNotNone(media_info["Url"])
        self.assertIsNotNone(media_info["MediaKey"])
        self.assertEqual(media_info["Mimetype"], "image/jpeg")

    def test_classify_text_returns_no_media_info(self):
        msg_dict = {"conversation": "Halo min"}
        message_type, content, media_info = WhatsAppAdapter._classify(msg_dict)
        self.assertEqual(message_type, "Text")
        self.assertEqual(content, "Halo min")
        self.assertIsNone(media_info)

    def test_classify_audio_returns_no_content(self):
        msg_dict = {"audioMessage": {"url": "u", "mediaKey": "k", "mimetype": "audio/ogg",
                                      "fileSha256": "s", "fileLength": 1000}}
        message_type, content, media_info = WhatsAppAdapter._classify(msg_dict)
        self.assertEqual(message_type, "Audio")
        self.assertIsNone(content)
        self.assertIsNotNone(media_info)
        self.assertEqual(media_info["kind"], "audio")

    # -- parse_inbound with image — media fetch patched -------------------

    def test_parse_image_without_media_bytes_when_fetch_fails(self):
        """When _fetch_inbound_media raises/no-ops, message still parses (graceful fallback)."""
        payload = load_fixture("wuzapi_inbound_image.json")
        with patch.object(self.adapter, "_fetch_inbound_media"):
            [normalized] = self.adapter.parse_inbound(payload)
        self.assertEqual(normalized["message_type"], "Image")
        self.assertEqual(normalized["content"], "Ini foto pesanan saya")
        self.assertIsNone(normalized["media_url"])

    def test_parse_image_with_media_fetch_populates_bytes(self):
        """When _fetch_inbound_media succeeds, media_bytes are set in normalized."""
        payload = load_fixture("wuzapi_inbound_image.json")
        fake_bytes = b"\x89PNG\r\n\x1a\n"
        with patch.object(
            self.adapter,
            "_fetch_inbound_media",
            side_effect=lambda mi, n: n.update({
                "media_bytes": fake_bytes,
                "media_filename": "test.jpg",
                "media_mimetype": "image/jpeg",
            }),
        ):
            [normalized] = self.adapter.parse_inbound(payload)
        self.assertEqual(normalized["media_bytes"], fake_bytes)
        self.assertEqual(normalized["media_filename"], "test.jpg")

    # -- regression: existing text fixture still parses -------------------

    def test_parse_text_fixture_still_works(self):
        """Regression: existing text fixture must parse unchanged after refactor."""
        [msg] = self.adapter.parse_inbound(load_fixture("wuzapi_inbound_text.json"))
        self.assertEqual(msg["channel_type"], "WhatsApp")
        self.assertIn("pesanan", msg["content"])
        self.assertIsNone(msg.get("media_bytes"))
