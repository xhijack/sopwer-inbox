# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""DB-level dedup guard for inbound messages (Phase 8 hardening).

A unique index on (conversation, external_message_id) makes webhook idempotency
race-safe: concurrent redelivery of the same message can no longer both insert.
NULL external_message_id (outgoing/failed) is exempt — MySQL treats NULLs as
distinct in a unique index, so multiple outgoing messages are unaffected.
"""

import frappe


INDEX_NAME = "unique_inbox_msg_dedup"


def execute():
	if not frappe.db.table_exists("Inbox Message"):
		return

	existing = frappe.db.sql(
		"""SELECT 1 FROM information_schema.STATISTICS
		   WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'tabInbox Message' AND INDEX_NAME = %s
		   LIMIT 1""",
		(frappe.conf.db_name, INDEX_NAME),
	)
	if existing:
		return

	try:
		frappe.db.add_unique(
			"Inbox Message",
			["conversation", "external_message_id"],
			constraint_name=INDEX_NAME,
		)
		frappe.db.commit()
	except Exception:
		# Pre-existing duplicates could block it; dedup is also enforced at the
		# application layer (core.ingest), so this is best-effort.
		frappe.db.rollback()
