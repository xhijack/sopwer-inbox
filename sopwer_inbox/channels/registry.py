# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Adapter registry: maps a channel_type to its adapter class."""

import frappe
from frappe import _


def _adapter_map():
	# Imported lazily to avoid import cycles and to keep optional deps soft.
	from sopwer_inbox.channels.telegram import TelegramAdapter
	from sopwer_inbox.channels.whatsapp import WhatsAppAdapter
	from sopwer_inbox.channels.meta import MessengerAdapter, InstagramAdapter

	return {
		"Telegram": TelegramAdapter,
		"WhatsApp": WhatsAppAdapter,
		"Facebook Messenger": MessengerAdapter,
		"Instagram": InstagramAdapter,
	}


def get_adapter_class(channel_type: str):
	adapter_cls = _adapter_map().get(channel_type)
	if not adapter_cls:
		frappe.throw(_("No adapter registered for channel type {0}").format(channel_type))
	return adapter_cls


def get_adapter(channel):
	"""Return an adapter instance for the given Inbox Channel (name or doc)."""
	channel_doc = channel if hasattr(channel, "channel_type") else frappe.get_doc("Inbox Channel", channel)
	return get_adapter_class(channel_doc.channel_type)(channel_doc)
