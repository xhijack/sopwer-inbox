# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime

from sopwer_inbox.core.ingest import ingest_inbound
from sopwer_inbox.tests.base import InboxTestCase, make_channel


def normalized(**overrides):
	base = {
		"channel_type": "Telegram",
		"external_conversation_id": "chat-777",
		"external_message_id": "msg-1",
		"sender_external_id": "user-777",
		"sender_name": "Budi Santoso",
		"sender_phone": None,
		"message_type": "Text",
		"content": "Halo min, pesanan saya kok belum sampai?",
		"media_url": None,
		"timestamp": now_datetime(),
		"raw": {},
	}
	base.update(overrides)
	return base


class TestIngest(InboxTestCase):
	def setUp(self):
		self.channel = make_channel("Ingest TG", "Telegram")

	def test_creates_conversation_and_message(self):
		msg = ingest_inbound(normalized(), self.channel.name)
		self.assertIsNotNone(msg)
		self.assertEqual(msg.direction, "Incoming")
		conv = frappe.get_doc("Inbox Conversation", msg.conversation)
		self.assertEqual(conv.external_conversation_id, "chat-777")
		self.assertEqual(conv.unread_count, 1)
		self.assertTrue(conv.contact)
		self.assertIn("pesanan", conv.last_message_preview)

	def test_appends_to_existing_conversation(self):
		first = ingest_inbound(normalized(external_message_id="m1"), self.channel.name)
		second = ingest_inbound(normalized(external_message_id="m2", content="dua"), self.channel.name)
		self.assertEqual(first.conversation, second.conversation)
		conv = frappe.get_doc("Inbox Conversation", first.conversation)
		self.assertEqual(conv.unread_count, 2)

	def test_dedup_skips_duplicate(self):
		ingest_inbound(normalized(external_message_id="dup"), self.channel.name)
		result = ingest_inbound(normalized(external_message_id="dup"), self.channel.name)
		self.assertIsNone(result)
		count = frappe.db.count(
			"Inbox Message", {"external_message_id": "dup"}
		)
		self.assertEqual(count, 1)

	def test_reopen_resolved_conversation(self):
		msg = ingest_inbound(normalized(external_message_id="r1"), self.channel.name)
		conv = frappe.get_doc("Inbox Conversation", msg.conversation)
		conv.status = "Resolved"
		conv.save(ignore_permissions=True)

		ingest_inbound(normalized(external_message_id="r2"), self.channel.name)
		conv.reload()
		self.assertEqual(conv.status, "Open")

	def test_media_message_preview(self):
		msg = ingest_inbound(
			normalized(external_message_id="img1", message_type="Image", content=None),
			self.channel.name,
		)
		conv = frappe.get_doc("Inbox Conversation", msg.conversation)
		self.assertTrue(conv.last_message_preview)

	def test_ingest_with_media_bytes_saves_file(self):
		"""When normalized carries media_bytes, ingest saves a private File and
		sets media_file on the message — no network call needed."""
		raw_bytes = b"\x89PNG\r\n\x1a\n"
		msg = ingest_inbound(
			normalized(
				external_message_id="wa-img-1",
				message_type="Image",
				content="foto",
				media_bytes=raw_bytes,
				media_filename="receipt.png",
				media_mimetype="image/png",
			),
			self.channel.name,
		)
		self.assertIsNotNone(msg)
		self.assertIsNotNone(msg.media_file)
		# The saved File must exist and have the right name.
		file_doc = frappe.get_doc("File", {"file_url": msg.media_file})
		self.assertEqual(file_doc.file_name, "receipt.png")
		self.assertEqual(file_doc.is_private, 1)

	def test_ingest_media_bytes_takes_priority_over_media_url(self):
		"""media_bytes path must be used even when media_url is also set.
		Uses a .ogg (audio) extension so Frappe does not run JPEG EXIF stripping."""
		raw_bytes = b"OggS\x00\x02\x00\x00"
		msg = ingest_inbound(
			normalized(
				external_message_id="wa-audio-2",
				message_type="Audio",
				content=None,
				media_bytes=raw_bytes,
				media_filename="voice.ogg",
				media_url="https://example.com/should-not-be-fetched.ogg",
			),
			self.channel.name,
		)
		self.assertIsNotNone(msg.media_file)
		# Confirm we did NOT hit the URL (would fail with a real request on test env).
		file_doc = frappe.get_doc("File", {"file_url": msg.media_file})
		self.assertEqual(file_doc.file_name, "voice.ogg")
