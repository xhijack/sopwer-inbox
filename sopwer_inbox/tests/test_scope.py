# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Tests for sopwer_inbox.scope — conversation_company helper."""

from unittest.mock import patch

import frappe

from sopwer_inbox.scope import conversation_company
from sopwer_inbox.tests.base import InboxTestCase, make_channel, make_conversation


class TestConversationCompany(InboxTestCase):
    def test_returns_none_when_conversation_is_none(self):
        self.assertIsNone(conversation_company(None))

    def test_returns_none_when_conversation_has_no_channel(self):
        with patch("frappe.db.get_value", return_value=None):
            self.assertIsNone(conversation_company("CONV-GHOST"))

    def test_returns_none_when_channel_company_is_blank(self):
        channel = make_channel("Scope NoComp WA", "WhatsApp")
        conv = make_conversation(channel.name, "scope-no-company")
        # channel.company is blank by default
        self.assertIsNone(conversation_company(conv.name))

    def test_returns_company_when_set_on_channel(self):
        channel = make_channel("Scope CoComp WA", "WhatsApp")
        # Simulate a company value on the channel without needing a real Company doc.
        with patch("frappe.db.get_value") as mock_get_value:
            def side_effect(doctype, name, field):
                if doctype == "Inbox Conversation":
                    return channel.name
                if doctype == "Inbox Channel":
                    return "PT Sopwer"
                return None
            mock_get_value.side_effect = side_effect
            result = conversation_company("CONV-1")
        self.assertEqual(result, "PT Sopwer")

    def test_returns_none_when_channel_company_is_empty_string(self):
        channel = make_channel("Scope EmptyComp WA", "WhatsApp")
        with patch("frappe.db.get_value") as mock_get_value:
            def side_effect(doctype, name, field):
                if doctype == "Inbox Conversation":
                    return channel.name
                if doctype == "Inbox Channel":
                    return ""
                return None
            mock_get_value.side_effect = side_effect
            result = conversation_company("CONV-2")
        self.assertIsNone(result)
