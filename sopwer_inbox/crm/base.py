# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
"""CRM/ERP provider contract — the core never calls a CRM/ERP API directly."""


class BaseCRMProvider:
	def is_available(self) -> bool:
		raise NotImplementedError

	def get_contact_context(self, contact: str) -> dict | None:
		return None

	def allowed_send_doctypes(self) -> list[str]:
		return []

	def list_documents(self, doctype: str, customer: str | None, q: str = "") -> list[dict]:
		return []

	def get_document_pdf(self, doctype: str, name: str, print_format: str | None = None) -> bytes:
		raise NotImplementedError

	def create_lead(self, conversation, fields: dict):  # Phase B
		raise NotImplementedError

	def link_conversation(self, conversation):  # Phase D
		raise NotImplementedError
