# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
"""Select the configured CRM/ERP provider for this site."""

import frappe


def get_settings():
	return frappe.get_cached_doc("Inbox CRM Settings")


def get_provider():
	"""Return the configured provider instance, or None when provider == 'None'."""
	provider = (get_settings().provider or "None").strip()
	if provider == "None" or not provider:
		return None
	if provider == "ERPNext":
		from sopwer_inbox.crm.erpnext import ERPNextProvider

		return ERPNextProvider()
	if provider == "Frappe CRM":
		from sopwer_inbox.crm.frappe_crm import FrappeCRMProvider

		return FrappeCRMProvider()
	if provider == "External":
		from sopwer_inbox.crm.external import ExternalProvider

		return ExternalProvider()
	return None
