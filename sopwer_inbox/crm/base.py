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

	# ------------------------------------------------------------------
	# Customer linking contract (Phase: link/create customer from inbox)
	# ------------------------------------------------------------------

	def linked_customer(self, contact: str) -> "str | None":
		"""Return the Customer linked to *contact*, or None."""
		return None

	def search_customers(self, q: str, limit: int = 10) -> list:
		"""Return a list of ``{"name": ..., "label": ...}`` dicts matching *q*."""
		return []

	def suggest_customers_for_contact(self, contact: str) -> list:
		"""Return Customer suggestions based on shared phone numbers."""
		return []

	def link_customer(self, contact: str, customer: str) -> None:
		"""Link *customer* to *contact*."""
		raise NotImplementedError

	def create_and_link_customer(self, contact: str, customer_name: str) -> str:
		"""Create a Customer named *customer_name*, link it to *contact*, return its name."""
		raise NotImplementedError
