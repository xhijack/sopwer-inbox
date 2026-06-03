# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

import frappe

from sopwer_inbox.api import conversation as conv_api
from sopwer_inbox.tests.base import InboxTestCase, make_channel, make_conversation


class TestConversationAPI(InboxTestCase):
	def setUp(self):
		self.channel = make_channel("Conv TG", "Telegram", telegram_bot_token="1:A")
		self.conv = make_conversation(self.channel.name, "chat-conv-1")

	def _fake_adapter(self, send_return=None, raises=False):
		adapter = MagicMock()
		if raises:
			adapter.send_message.side_effect = RuntimeError("boom")
		else:
			adapter.send_message.return_value = send_return or {
				"external_message_id": "ext-1",
				"delivery_status": "Sent",
			}
		return adapter

	def test_send_message_dispatches_and_marks_sent(self):
		adapter = self._fake_adapter()
		with patch.object(conv_api, "get_adapter", return_value=adapter):
			payload = conv_api.send_message(self.conv.name, text="Halo Pak Budi")
		adapter.send_message.assert_called_once()
		msg = frappe.get_doc("Inbox Message", payload["name"])
		self.assertEqual(msg.direction, "Outgoing")
		self.assertEqual(msg.delivery_status, "Sent")
		self.assertEqual(msg.external_message_id, "ext-1")

	def test_internal_note_never_dispatched(self):
		adapter = self._fake_adapter()
		with patch.object(conv_api, "get_adapter", return_value=adapter):
			payload = conv_api.send_message(self.conv.name, text="cek gudang", is_internal=1)
		adapter.send_message.assert_not_called()
		msg = frappe.get_doc("Inbox Message", payload["name"])
		self.assertEqual(msg.is_internal, 1)

	def test_add_internal_note_helper(self):
		adapter = self._fake_adapter()
		with patch.object(conv_api, "get_adapter", return_value=adapter):
			payload = conv_api.add_internal_note(self.conv.name, "rahasia antar agen")
		adapter.send_message.assert_not_called()
		self.assertEqual(frappe.get_doc("Inbox Message", payload["name"]).is_internal, 1)

	def test_send_failure_marks_failed_without_crash(self):
		adapter = self._fake_adapter(raises=True)
		with patch.object(conv_api, "get_adapter", return_value=adapter):
			payload = conv_api.send_message(self.conv.name, text="will fail")
		msg = frappe.get_doc("Inbox Message", payload["name"])
		self.assertEqual(msg.delivery_status, "Failed")

	def test_retry_message_redispatches(self):
		adapter = self._fake_adapter(raises=True)
		with patch.object(conv_api, "get_adapter", return_value=adapter):
			payload = conv_api.send_message(self.conv.name, text="retry me")
		# now succeed
		ok_adapter = self._fake_adapter()
		with patch.object(conv_api, "get_adapter", return_value=ok_adapter):
			conv_api.retry_message(payload["name"])
		self.assertEqual(frappe.get_doc("Inbox Message", payload["name"]).delivery_status, "Sent")

	def test_set_status(self):
		conv_api.set_status(self.conv.name, "Resolved")
		self.assertEqual(frappe.db.get_value("Inbox Conversation", self.conv.name, "status"), "Resolved")
		with self.assertRaises(frappe.ValidationError):
			conv_api.set_status(self.conv.name, "Bogus")

	def test_assign_and_mark_read(self):
		conv_api.assign(self.conv.name, "Administrator")
		self.assertEqual(frappe.db.get_value("Inbox Conversation", self.conv.name, "assigned_to"), "Administrator")
		# simulate unread then mark read
		frappe.db.set_value("Inbox Conversation", self.conv.name, "unread_count", 5)
		conv_api.mark_read(self.conv.name)
		self.assertEqual(frappe.db.get_value("Inbox Conversation", self.conv.name, "unread_count"), 0)
