# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Tests for the WhatsApp Cloud API adapter.

All network calls are mocked — this suite runs on a Frappe-only site
with no real Meta App access.
"""

import json
import os
from unittest.mock import MagicMock, patch

import frappe

from sopwer_inbox.channels.whatsapp_cloud import WhatsAppCloudAdapter, wacloud_kind
from sopwer_inbox.api.webhooks import _match_wa_channel, register_meta_webhook
from sopwer_inbox.tests.base import InboxTestCase, make_channel

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
	with open(os.path.join(FIXTURES, name)) as f:
		return json.load(f)


def make_wacloud_channel(
	name,
	phone_number_id="PHONE_NUM_ID_123",
	waba_id="WABA_456",
	token="wacloudtoken",
	app_secret="wacloudappsecret",
	verify_token="vt-wacloud",
):
	"""Factory for WhatsApp Cloud Inbox Channel docs."""
	if frappe.db.exists("Inbox Channel", name):
		return frappe.get_doc("Inbox Channel", name)
	doc = frappe.get_doc(
		{
			"doctype": "Inbox Channel",
			"channel_name": name,
			"channel_type": "WhatsApp Cloud",
			"enabled": 1,
			"meta_phone_number_id": phone_number_id,
			"meta_waba_id": waba_id,
			"meta_app_id": "APP_111",
			"meta_page_access_token": token,
			"meta_app_secret": app_secret,
			"meta_verify_token": verify_token,
			"meta_api_version": "v21.0",
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


# ---------------------------------------------------------------------------
# wacloud_kind mapping
# ---------------------------------------------------------------------------

class TestWacloudKind(InboxTestCase):
	def test_image(self):
		self.assertEqual(wacloud_kind("image/jpeg"), "image")
		self.assertEqual(wacloud_kind("image/png"), "image")

	def test_video(self):
		self.assertEqual(wacloud_kind("video/mp4"), "video")

	def test_audio(self):
		self.assertEqual(wacloud_kind("audio/ogg"), "audio")
		self.assertEqual(wacloud_kind("audio/mpeg"), "audio")

	def test_document_fallback(self):
		self.assertEqual(wacloud_kind("application/pdf"), "document")
		self.assertEqual(wacloud_kind("text/plain"), "document")
		self.assertEqual(wacloud_kind(""), "document")
		self.assertEqual(wacloud_kind(None), "document")


# ---------------------------------------------------------------------------
# _match_wa_channel routing
# ---------------------------------------------------------------------------

class TestMatchWaChannel(InboxTestCase):
	def setUp(self):
		self.ch = make_wacloud_channel("WA Cloud Route Test", phone_number_id="PH_ROUTE_999")

	def test_routes_by_phone_number_id(self):
		result = _match_wa_channel("PH_ROUTE_999")
		self.assertIsNotNone(result)
		self.assertEqual(result.channel_type, "WhatsApp Cloud")
		self.assertEqual(result.meta_phone_number_id, "PH_ROUTE_999")

	def test_unknown_phone_number_id_returns_none(self):
		self.assertIsNone(_match_wa_channel("UNKNOWN_000"))

	def test_disabled_channel_not_matched(self):
		doc = make_wacloud_channel("WA Cloud Disabled", phone_number_id="PH_DISABLED")
		doc.enabled = 0
		doc.save(ignore_permissions=True)
		self.assertIsNone(_match_wa_channel("PH_DISABLED"))


# ---------------------------------------------------------------------------
# WhatsAppCloudAdapter.parse_inbound
# ---------------------------------------------------------------------------

class TestWaCloudParseInbound(InboxTestCase):
	def setUp(self):
		self.channel = make_wacloud_channel("WA Cloud Parse Test")
		self.adapter = WhatsAppCloudAdapter(self.channel)

	def test_text_message(self):
		value = load_fixture("wacloud_inbound_text.json")
		with patch.object(self.adapter, "_fetch_media_bytes", return_value=None):
			results = self.adapter.parse_inbound(value)
		self.assertEqual(len(results), 1)
		msg = results[0]
		self.assertEqual(msg["channel_type"], "WhatsApp Cloud")
		self.assertEqual(msg["external_conversation_id"], "628111222333")
		self.assertEqual(msg["external_message_id"], "wamid.text001")
		self.assertEqual(msg["sender_external_id"], "628111222333")
		self.assertEqual(msg["sender_phone"], "628111222333")
		self.assertEqual(msg["sender_name"], "Siti Cloud")
		self.assertEqual(msg["message_type"], "Text")
		self.assertIn("stok", msg["content"])
		self.assertIsNone(msg["media_url"])

	def test_image_message_fetches_media_bytes(self):
		value = load_fixture("wacloud_inbound_image.json")
		fake_bytes = b"\xff\xd8\xff\xe0fake-jpeg"
		with patch.object(self.adapter, "_fetch_media_bytes", return_value=fake_bytes) as mock_fetch:
			results = self.adapter.parse_inbound(value)
		self.assertEqual(len(results), 1)
		msg = results[0]
		self.assertEqual(msg["message_type"], "Image")
		self.assertEqual(msg["content"], "Foto produk")
		self.assertEqual(msg["media_bytes"], fake_bytes)
		self.assertIsNotNone(msg["media_filename"])
		self.assertEqual(msg["media_mimetype"], "image/jpeg")
		mock_fetch.assert_called_once_with("media-id-abc")

	def test_statuses_only_returns_empty(self):
		value = load_fixture("wacloud_status.json")
		results = self.adapter.parse_inbound(value)
		self.assertEqual(results, [])

	def test_media_fetch_failure_still_ingests(self):
		"""If media fetch fails, message is still ingested (no media_bytes key)."""
		value = load_fixture("wacloud_inbound_image.json")
		with patch.object(self.adapter, "_fetch_media_bytes", return_value=None):
			results = self.adapter.parse_inbound(value)
		self.assertEqual(len(results), 1)
		self.assertNotIn("media_bytes", results[0])

	def test_empty_value_returns_empty(self):
		self.assertEqual(self.adapter.parse_inbound({}), [])

	def test_no_sender_name_when_not_in_contacts(self):
		value = {
			"metadata": {"phone_number_id": "PHONE_NUM_ID_123"},
			"messages": [
				{
					"from": "628999000111",
					"id": "wamid.anon001",
					"timestamp": "1749081600",
					"type": "text",
					"text": {"body": "Anonymous"},
				}
			],
		}
		results = self.adapter.parse_inbound(value)
		self.assertEqual(len(results), 1)
		self.assertIsNone(results[0]["sender_name"])


# ---------------------------------------------------------------------------
# WhatsAppCloudAdapter._fetch_media_bytes
# ---------------------------------------------------------------------------

class TestFetchMediaBytes(InboxTestCase):
	def setUp(self):
		self.channel = make_wacloud_channel("WA Cloud Media Test")
		self.adapter = WhatsAppCloudAdapter(self.channel)

	def test_two_step_download(self):
		"""GET /{media_id} → url → GET url → bytes."""
		fake_meta = MagicMock()
		fake_meta.raise_for_status = MagicMock()
		fake_meta.json.return_value = {"url": "https://cdn.whatsapp.net/v/media-file"}

		fake_content = MagicMock()
		fake_content.raise_for_status = MagicMock()
		fake_content.content = b"fake-image-data"

		with patch("sopwer_inbox.channels.whatsapp_cloud.requests.get",
				   side_effect=[fake_meta, fake_content]) as mock_get:
			result = self.adapter._fetch_media_bytes("media-id-xyz")

		self.assertEqual(result, b"fake-image-data")
		self.assertEqual(mock_get.call_count, 2)
		first_url = mock_get.call_args_list[0].args[0]
		self.assertIn("media-id-xyz", first_url)

	def test_returns_none_on_error(self):
		with patch(
			"sopwer_inbox.channels.whatsapp_cloud.requests.get",
			side_effect=Exception("network error"),
		):
			result = self.adapter._fetch_media_bytes("bad-id")
		self.assertIsNone(result)


# ---------------------------------------------------------------------------
# WhatsAppCloudAdapter.send_message — text
# ---------------------------------------------------------------------------

class TestWaCloudSendMessage(InboxTestCase):
	def setUp(self):
		self.channel = make_wacloud_channel("WA Cloud Send Test")
		self.adapter = WhatsAppCloudAdapter(self.channel)

	def test_send_text_body_shape(self):
		fake_resp = MagicMock()
		fake_resp.raise_for_status = MagicMock()
		fake_resp.json.return_value = {"messages": [{"id": "wamid.sent001"}]}

		conv = MagicMock(external_conversation_id="628111222333")

		with patch("sopwer_inbox.channels.whatsapp_cloud.requests.post",
				   return_value=fake_resp) as mock_post:
			result = self.adapter.send_message(conv, text="Halo dari cloud")

		self.assertEqual(result["delivery_status"], "Sent")
		self.assertEqual(result["external_message_id"], "wamid.sent001")

		call_kw = mock_post.call_args
		url = call_kw.args[0]
		self.assertIn("PHONE_NUM_ID_123/messages", url)
		self.assertIn("v21.0", url)

		body = call_kw.kwargs["json"]
		self.assertEqual(body["messaging_product"], "whatsapp")
		self.assertEqual(body["to"], "628111222333")
		self.assertEqual(body["type"], "text")
		self.assertEqual(body["text"]["body"], "Halo dari cloud")

	def test_send_media_calls_upload_then_send(self):
		fake_send_resp = MagicMock()
		fake_send_resp.raise_for_status = MagicMock()
		fake_send_resp.json.return_value = {"messages": [{"id": "wamid.media001"}]}

		conv = MagicMock(external_conversation_id="628111222333")

		with patch.object(self.adapter, "_resolve_local_file", return_value="/tmp/photo.jpg"), \
			 patch.object(self.adapter, "_upload_media", return_value="media-id-uploaded") as mock_upload, \
			 patch("sopwer_inbox.channels.whatsapp_cloud.requests.post",
				   return_value=fake_send_resp) as mock_post:
			result = self.adapter.send_message(conv, media_path="/private/files/photo.jpg",
											   text="Lihat foto ini")

		self.assertEqual(result["delivery_status"], "Sent")
		mock_upload.assert_called_once_with("/tmp/photo.jpg")

		body = mock_post.call_args.kwargs["json"]
		self.assertEqual(body["messaging_product"], "whatsapp")
		self.assertEqual(body["type"], "image")
		self.assertEqual(body["image"]["id"], "media-id-uploaded")
		self.assertEqual(body["image"]["caption"], "Lihat foto ini")

	def test_send_document_no_caption_for_audio(self):
		"""Audio kind does not set caption even if text is provided."""
		fake_send_resp = MagicMock()
		fake_send_resp.raise_for_status = MagicMock()
		fake_send_resp.json.return_value = {"messages": [{"id": "wamid.aud001"}]}

		conv = MagicMock(external_conversation_id="628111222333")

		with patch.object(self.adapter, "_resolve_local_file", return_value="/tmp/voice.ogg"), \
			 patch.object(self.adapter, "_upload_media", return_value="media-id-audio"), \
			 patch("sopwer_inbox.channels.whatsapp_cloud.requests.post",
				   return_value=fake_send_resp) as mock_post:
			self.adapter.send_message(conv, media_path="/private/files/voice.ogg",
									  text="some caption")

		body = mock_post.call_args.kwargs["json"]
		self.assertEqual(body["type"], "audio")
		# audio kind does not support caption — should not be in audio block
		self.assertNotIn("caption", body.get("audio", {}))


# ---------------------------------------------------------------------------
# register_meta_webhook — WhatsApp Cloud path
# ---------------------------------------------------------------------------

class TestRegisterMetaWebhookWaCloud(InboxTestCase):
	def test_registers_and_subscribes_waba(self):
		ch = make_wacloud_channel("WH WA Cloud Reg")
		with patch("requests.post") as mock_post:
			mock_post.return_value = MagicMock(json=lambda: {"success": True})
			res = register_meta_webhook(ch.name)

		self.assertTrue(res["ok"])
		self.assertEqual(res["object"], "whatsapp_business_account")
		self.assertEqual(mock_post.call_count, 2)

		# First call: /{app_id}/subscriptions
		first_url = mock_post.call_args_list[0].args[0]
		self.assertIn("/APP_111/subscriptions", first_url)
		sub_data = mock_post.call_args_list[0].kwargs["data"]
		self.assertEqual(sub_data["object"], "whatsapp_business_account")
		self.assertEqual(sub_data["fields"], "messages")
		self.assertTrue(res["callback_url"].startswith("https://"))
		self.assertTrue(sub_data["callback_url"].startswith("https://"))

		# Second call: /{waba_id}/subscribed_apps with params (not data)
		second_url = mock_post.call_args_list[1].args[0]
		self.assertIn("/WABA_456/subscribed_apps", second_url)
		# Uses params (query string with access_token), not form data
		second_params = mock_post.call_args_list[1].kwargs.get("params") or {}
		self.assertIn("access_token", second_params)

	def test_missing_waba_id_throws(self):
		ch = make_channel("WH WA Cloud Bare", "WhatsApp Cloud",
						  meta_app_id="X", meta_app_secret="Y",
						  meta_verify_token="T", meta_page_access_token="TOK",
						  meta_phone_number_id="PH")
		with self.assertRaises(frappe.ValidationError):
			register_meta_webhook(ch.name)

	def test_non_meta_channel_throws(self):
		ch = make_channel("WH TG WA Reg", "Telegram", telegram_bot_token="1:A")
		with self.assertRaises(frappe.ValidationError):
			register_meta_webhook(ch.name)
