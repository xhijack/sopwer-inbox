# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Company scoping helpers — resolve the Company configured on a conversation's channel."""

import frappe


def conversation_company(conversation):
    """Resolve the Company configured on a conversation's channel (None if unset)."""
    if not conversation:
        return None
    channel = frappe.db.get_value("Inbox Conversation", conversation, "channel")
    if not channel:
        return None
    return frappe.db.get_value("Inbox Channel", channel, "company") or None
