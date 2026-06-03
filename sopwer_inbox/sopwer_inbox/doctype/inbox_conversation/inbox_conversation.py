# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class InboxConversation(Document):
	def validate(self):
		self.ensure_unique_external_conversation()

	def ensure_unique_external_conversation(self):
		"""A conversation is uniquely identified by (channel, external_conversation_id).

		This is the deliberate multi-channel key: the same person messaging two
		different business numbers yields two separate conversations (CLAUDE.md §4.2).
		"""
		if not (self.channel and self.external_conversation_id):
			return

		duplicate = frappe.db.get_value(
			"Inbox Conversation",
			{
				"channel": self.channel,
				"external_conversation_id": self.external_conversation_id,
				"name": ["!=", self.name or ""],
			},
			"name",
		)
		if duplicate:
			frappe.throw(
				_("A conversation for this contact already exists on channel {0} ({1}).").format(
					frappe.bold(self.channel), duplicate
				),
				frappe.DuplicateEntryError,
				title=_("Duplicate Conversation"),
			)
