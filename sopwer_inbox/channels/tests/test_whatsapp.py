# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import json
import os
from unittest.mock import patch

import frappe

from sopwer_inbox.channels.whatsapp import WhatsAppAdapter, _strip_jid
from sopwer_inbox.tests.base import InboxTestCase, make_channel

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
	with open(os.path.join(FIXTURES, name)) as f:
		return json.load(f)


class TestWhatsAppAdapter(InboxTestCase):
	def setUp(self):
		self.channel = make_channel("WA Pilot", "WhatsApp", wuzapi_instance="ACC-1")
		self.adapter = WhatsAppAdapter(self.channel)

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

	def test_resolve_local_file_returns_existing_path(self):
		"""file_url must be resolved to a real on-disk path for the whatsapp handler."""
		f = frappe.get_doc(
			{"doctype": "File", "file_name": "wa-test.png", "content": "hello"}
		).insert(ignore_permissions=True)
		path = self.adapter._resolve_local_file(f.file_url)
		self.assertTrue(os.path.exists(path))

	def test_resolve_local_file_throws_when_missing(self):
		with self.assertRaises(frappe.ValidationError):
			self.adapter._resolve_local_file("/files/does-not-exist-zzz.png")

	def test_send_requires_delegate_app(self):
		"""On a site without the 'whatsapp' app, sending must fail loudly — never
		silently no-op (CLAUDE.md §5)."""
		if "whatsapp" in frappe.get_installed_apps():
			self.skipTest("whatsapp app installed on this site")
		conv = frappe.get_doc(
			{
				"doctype": "Inbox Conversation",
				"channel": self.channel.name,
				"external_conversation_id": "628000",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			self.adapter.send_message(conv, text="hi")

	# -- _pick helper ---------------------------------------------------------

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

	# -- _classify with image fixture -----------------------------------------

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

	# -- parse_inbound with image — whatsapp app NOT installed ----------------

	def test_parse_image_without_delegate_app_no_media_bytes(self):
		"""When whatsapp app is not installed, media_bytes must be absent/None but
		message must still be parsed (graceful fallback)."""
		if "whatsapp" in frappe.get_installed_apps():
			self.skipTest("whatsapp app is installed on this site")
		payload = load_fixture("wuzapi_inbound_image.json")
		[normalized] = self.adapter.parse_inbound(payload)
		self.assertEqual(normalized["message_type"], "Image")
		self.assertEqual(normalized["content"], "Ini foto pesanan saya")
		# media_url stays None for WA encrypted media
		self.assertIsNone(normalized["media_url"])
		# media_bytes not set (delegate app absent)
		self.assertIsNone(normalized.get("media_bytes"))

	# -- parse_inbound with image — whatsapp app installed and media fetched --

	def test_parse_image_with_delegate_app_fetches_media(self):
		"""When whatsapp app is installed, _fetch_inbound_media is called and
		media_bytes are populated in normalized."""
		if "whatsapp" not in frappe.get_installed_apps():
			self.skipTest("whatsapp app not installed on this site")
		payload = load_fixture("wuzapi_inbound_image.json")
		fake_bytes = b"\x89PNG\r\n\x1a\n"
		with patch.object(self.adapter, "_fetch_inbound_media",
		                  side_effect=lambda mi, n: n.update({"media_bytes": fake_bytes,
		                                                       "media_filename": "test.jpg",
		                                                       "media_mimetype": "image/jpeg"})):
			[normalized] = self.adapter.parse_inbound(payload)
		self.assertEqual(normalized["media_bytes"], fake_bytes)
		self.assertEqual(normalized["media_filename"], "test.jpg")

	# -- existing text fixture still parses -----------------------------------

	def test_parse_text_fixture_still_works(self):
		"""Regression: existing text fixture must parse unchanged after refactor."""
		[msg] = self.adapter.parse_inbound(load_fixture("wuzapi_inbound_text.json"))
		self.assertEqual(msg["channel_type"], "WhatsApp")
		self.assertIn("pesanan", msg["content"])
		self.assertIsNone(msg.get("media_bytes"))
