# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""One-off maintenance helpers.

Group-conversation cleanup — remove WhatsApp group/broadcast/newsletter
conversations that leaked into the inbox BEFORE the group filter fix
(``channels/whatsapp.py`` parse_inbound). A group conversation's
``external_conversation_id`` is the group JID (``…@g.us`` / ``…@broadcast`` /
``…@newsletter``).

Dry-run first (list, no writes):
    bench --site <site> execute sopwer_inbox.maintenance.list_group_conversations

Delete (after confirming the list):
    bench --site <site> execute sopwer_inbox.maintenance.delete_group_conversations
"""

import frappe

# Group/broadcast/newsletter/status JIDs carry one of these server suffixes.
_GROUP_SUFFIXES = ("@g.us", "@broadcast", "@newsletter")


def _group_conversation_names() -> list[str]:
	"""Return Inbox Conversation names whose external_conversation_id is a group JID."""
	or_filters = [
		["external_conversation_id", "like", f"%{suffix}"] for suffix in _GROUP_SUFFIXES
	]
	rows = frappe.get_all(
		"Inbox Conversation",
		or_filters=or_filters,
		fields=["name", "external_conversation_id", "subject"],
		limit=0,
	)
	return rows


def list_group_conversations():
	"""Dry-run: print group conversations that would be deleted. No writes."""
	rows = _group_conversation_names()
	if not rows:
		print("No group/broadcast/newsletter conversations found. Inbox is clean.")
		return rows
	print(f"Found {len(rows)} group conversation(s):")
	for r in rows:
		print(f"  - {r['name']} | {r['external_conversation_id']} | {r.get('subject') or ''}")
	print("\nRun delete_group_conversations to remove them (and their messages).")
	return rows


def delete_group_conversations():
	"""Delete the leaked group conversations and their child Inbox Messages.

	Idempotent: safe to run repeatedly. Returns the count deleted.
	"""
	rows = _group_conversation_names()
	if not rows:
		print("Nothing to delete — no group conversations found.")
		return 0

	deleted = 0
	for r in rows:
		name = r["name"]
		# Remove the conversation's messages first (no cascade on the link field).
		msgs = frappe.get_all(
			"Inbox Message", filters={"conversation": name}, fields=["name"], limit=0
		)
		for m in msgs:
			frappe.delete_doc("Inbox Message", m["name"], force=True, ignore_permissions=True)
		frappe.delete_doc(
			"Inbox Conversation", name, force=True, ignore_permissions=True
		)
		deleted += 1
		print(f"Deleted {name} ({r['external_conversation_id']}) + {len(msgs)} message(s)")

	frappe.db.commit()
	print(f"\nDone. Deleted {deleted} group conversation(s).")
	return deleted
