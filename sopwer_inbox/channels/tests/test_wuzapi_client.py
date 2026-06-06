# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Tests for sopwer_inbox.channels.wuzapi_client.

Ported / adapted from whatsapp.setup.tests.test_media.
Run via bench:
    bench --site inbox.dev run-tests --app sopwer_inbox \
        --module sopwer_inbox.channels.tests.test_wuzapi_client
"""

import base64
import os
import tempfile
from unittest.mock import MagicMock, patch

from sopwer_inbox.channels.wuzapi_client import (
    WuzapiClient,
    WuzapiError,
    decode_data_uri,
    extract_wuzapi_base64,
    file_to_wuzapi_base64,
    guess_mimetype,
    wuzapi_kind,
)
from sopwer_inbox.tests.base import InboxTestCase


class TestWuzapiKind(InboxTestCase):
    def test_image_kinds(self):
        self.assertEqual(wuzapi_kind("image/jpeg"), "image")
        self.assertEqual(wuzapi_kind("image/png"), "image")

    def test_video_kind(self):
        self.assertEqual(wuzapi_kind("video/mp4"), "video")

    def test_audio_opus_is_voice_note(self):
        self.assertEqual(wuzapi_kind("audio/ogg"), "audio")
        self.assertEqual(wuzapi_kind("audio/opus"), "audio")

    def test_non_opus_audio_falls_back_to_document(self):
        self.assertEqual(wuzapi_kind("audio/mpeg"), "document")
        self.assertEqual(wuzapi_kind("audio/mp4"), "document")

    def test_pdf_and_unknown_are_document(self):
        self.assertEqual(wuzapi_kind("application/pdf"), "document")
        self.assertEqual(wuzapi_kind(None), "document")
        self.assertEqual(wuzapi_kind(""), "document")

    def test_guess_mimetype(self):
        self.assertEqual(guess_mimetype("photo.jpg"), "image/jpeg")
        self.assertEqual(guess_mimetype("doc.pdf"), "application/pdf")
        self.assertEqual(guess_mimetype("mystery.unknownext"), "application/octet-stream")


class TestFileToBase64(InboxTestCase):
    def test_data_uri_carries_real_mimetype(self):
        fd, path = tempfile.mkstemp(suffix=".png")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(b"\x89PNG\r\n\x1a\n")
            uri = file_to_wuzapi_base64(path, "image/png")
            self.assertTrue(uri.startswith("data:image/png;base64,"))
        finally:
            os.remove(path)

    def test_mimetype_inferred_when_not_given(self):
        fd, path = tempfile.mkstemp(suffix=".jpg")
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(b"\xff\xd8\xff")
            uri = file_to_wuzapi_base64(path)
            self.assertTrue(uri.startswith("data:image/jpeg;base64,"))
        finally:
            os.remove(path)


class TestDecodeDataUri(InboxTestCase):
    def test_strips_prefix_and_decodes(self):
        raw = b"hello world!!"
        uri = "data:image/png;base64," + base64.b64encode(raw).decode()
        self.assertEqual(decode_data_uri(uri), raw)

    def test_plain_base64_without_prefix(self):
        raw = b"\x00\x01\x02\x03\x04"
        b64 = base64.b64encode(raw).decode()
        self.assertEqual(decode_data_uri(b64), raw)

    def test_none_on_empty(self):
        self.assertIsNone(decode_data_uri(""))
        self.assertIsNone(decode_data_uri(None))

    def test_none_on_garbage(self):
        self.assertIsNone(decode_data_uri("not-base64-!!!"))


# 15 bytes → 24-char base64 (above the 20-char minimum guard)
_RAW = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
_B64 = base64.b64encode(_RAW).decode()
_DATA_URI = f"data:image/png;base64,{_B64}"


def _enc(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


class TestExtractWuzapiBase64(InboxTestCase):
    def test_nested_data_data(self):
        resp = {"data": {"Data": _DATA_URI}}
        self.assertEqual(extract_wuzapi_base64(resp), _RAW)

    def test_top_level_Data(self):
        resp = {"Data": _enc(_RAW)}
        self.assertEqual(extract_wuzapi_base64(resp), _RAW)

    def test_data_is_string(self):
        resp = {"data": _enc(_RAW)}
        self.assertEqual(extract_wuzapi_base64(resp), _RAW)

    def test_base64_key(self):
        resp = {"base64": _enc(_RAW)}
        self.assertEqual(extract_wuzapi_base64(resp), _RAW)

    def test_missing_returns_none(self):
        self.assertIsNone(extract_wuzapi_base64({}))
        self.assertIsNone(extract_wuzapi_base64({"status": "ok"}))

    def test_non_dict_returns_none(self):
        self.assertIsNone(extract_wuzapi_base64(None))
        self.assertIsNone(extract_wuzapi_base64("string"))

    def test_fallback_scans_string_values(self):
        resp = {"result": _enc(_RAW)}
        self.assertEqual(extract_wuzapi_base64(resp), _RAW)


class TestWuzapiClientSendText(InboxTestCase):
    def setUp(self):
        self.client = WuzapiClient("http://wuzapi.test", "TOKEN-123")

    def test_posts_to_correct_endpoint(self):
        with patch("sopwer_inbox.channels.wuzapi_client.requests.post") as post:
            post.return_value = MagicMock(json=lambda: {"ok": 1})
            self.client.send_text("628111", "Hello!")
        self.assertEqual(post.call_args.args[0], "http://wuzapi.test/chat/send/text")

    def test_payload_has_phone_body_id(self):
        with patch("sopwer_inbox.channels.wuzapi_client.requests.post") as post:
            post.return_value = MagicMock(json=lambda: {"ok": 1})
            self.client.send_text("628111", "Hi")
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["Phone"], "628111")
        self.assertEqual(body["Body"], "Hi")
        self.assertIn("Id", body)

    def test_token_in_headers(self):
        with patch("sopwer_inbox.channels.wuzapi_client.requests.post") as post:
            post.return_value = MagicMock(json=lambda: {"ok": 1})
            self.client.send_text("628111", "Hi")
        headers = post.call_args.kwargs["headers"]
        self.assertEqual(headers["Token"], "TOKEN-123")

    def test_raises_on_success_false(self):
        # Wuzapi returns HTTP 200 with success:false → must NOT be treated as sent.
        with patch("sopwer_inbox.channels.wuzapi_client.requests.post") as post:
            post.return_value = MagicMock(
                raise_for_status=lambda: None,
                json=lambda: {"success": False, "error": "No session for user"},
            )
            with self.assertRaises(WuzapiError):
                self.client.send_text("628111", "Hi")

    def test_no_raise_when_success_absent(self):
        # Responses without a `success` key are treated as OK (don't break working sends).
        with patch("sopwer_inbox.channels.wuzapi_client.requests.post") as post:
            post.return_value = MagicMock(raise_for_status=lambda: None, json=lambda: {"code": 200})
            self.client.send_text("628111", "Hi")  # should not raise


class TestWuzapiClientSendMedia(InboxTestCase):
    def setUp(self):
        self.client = WuzapiClient("http://wuzapi.test", "TOKEN-123")

    def _send(self, kind, **kw):
        with patch("sopwer_inbox.channels.wuzapi_client.requests.post") as post:
            post.return_value = MagicMock(json=lambda: {"ok": 1})
            self.client.send_media("628111", kind, "data:image/png;base64,AAAA", **kw)
        return post.call_args

    def test_image_endpoint_and_payload(self):
        call = self._send("image", caption="hi")
        self.assertEqual(call.args[0], "http://wuzapi.test/chat/send/image")
        body = call.kwargs["json"]
        self.assertEqual(body["Image"], "data:image/png;base64,AAAA")
        self.assertEqual(body["Caption"], "hi")
        self.assertEqual(body["Phone"], "628111")

    def test_video_endpoint(self):
        call = self._send("video")
        self.assertEqual(call.args[0], "http://wuzapi.test/chat/send/video")
        self.assertIn("Video", call.kwargs["json"])

    def test_audio_has_no_caption(self):
        call = self._send("audio")
        self.assertEqual(call.args[0], "http://wuzapi.test/chat/send/audio")
        body = call.kwargs["json"]
        self.assertIn("Audio", body)
        self.assertNotIn("Caption", body)

    def test_document_includes_filename(self):
        call = self._send("document", file_name="report.pdf", caption="see attached")
        self.assertEqual(call.args[0], "http://wuzapi.test/chat/send/document")
        body = call.kwargs["json"]
        self.assertEqual(body["Document"], "data:image/png;base64,AAAA")
        self.assertEqual(body["FileName"], "report.pdf")


class TestWuzapiClientDownloadMedia(InboxTestCase):
    def setUp(self):
        self.client = WuzapiClient("http://wuzapi.test", "TOKEN-123")

    def _download(self, kind, info=None):
        with patch("sopwer_inbox.channels.wuzapi_client.requests.post") as post:
            post.return_value = MagicMock(json=lambda: {"Data": "AAAA"})
            self.client.download_media(kind, info or {})
        return post.call_args

    def test_image_endpoint(self):
        call = self._download("image")
        self.assertEqual(call.args[0], "http://wuzapi.test/chat/downloadimage")

    def test_document_endpoint(self):
        call = self._download("document")
        self.assertEqual(call.args[0], "http://wuzapi.test/chat/downloaddocument")

    def test_audio_endpoint(self):
        call = self._download("audio")
        self.assertEqual(call.args[0], "http://wuzapi.test/chat/downloadaudio")

    def test_video_endpoint(self):
        call = self._download("video")
        self.assertEqual(call.args[0], "http://wuzapi.test/chat/downloadvideo")

    def test_all_fields_in_payload(self):
        # Wuzapi's download struct needs DirectPath + FileEncSHA256 too — without
        # them whatsmeow cannot fetch/verify the media and fails "invalid media hmac".
        info = {
            "Url": "u", "DirectPath": "d", "MediaKey": "k", "Mimetype": "m",
            "FileEncSHA256": "e", "FileSHA256": "s", "FileLength": 1,
        }
        call = self._download("image", info)
        body = call.kwargs["json"]
        for field in ("Url", "DirectPath", "MediaKey", "Mimetype",
                      "FileEncSHA256", "FileSHA256", "FileLength"):
            self.assertIn(field, body)
        self.assertEqual(body["DirectPath"], "d")
        self.assertEqual(body["FileEncSHA256"], "e")
