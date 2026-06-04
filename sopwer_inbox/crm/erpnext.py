# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
import frappe

from sopwer_inbox.crm.base import BaseCRMProvider

# Contact-panel cards: native date fields (the frontend reads transaction_date / posting_date).
_CONTEXT_FIELDS = {
	"Sales Order": ["name", "grand_total", "status", "transaction_date", "currency"],
	"Sales Invoice": ["name", "grand_total", "status", "posting_date", "currency"],
}
# Document picker: date aliased to a common `date` key (the picker reads `date`).
_LIST_FIELDS = {
	"Sales Order": ["name", "grand_total", "status", "transaction_date as date", "currency"],
	"Sales Invoice": ["name", "grand_total", "status", "posting_date as date", "currency"],
	"Quotation": ["name", "grand_total", "status", "transaction_date as date", "currency"],
}


class ERPNextProvider(BaseCRMProvider):
	def is_available(self) -> bool:
		return "erpnext" in frappe.get_installed_apps()

	def get_contact_context(self, contact: str) -> dict | None:
		if not self.is_available():
			return None
		customer = self._linked_customer(contact)
		if not customer:
			return None
		return {
			"customer": customer,
			"customer_since": frappe.db.get_value("Customer", customer, "creation"),
			"sales_orders": self._docs("Sales Order", customer),
			"invoices": self._docs("Sales Invoice", customer),
		}

	def linked_customer(self, contact: str):
		"""Public method — delegates to the internal implementation."""
		return self._linked_customer(contact)

	def _linked_customer(self, contact: str):
		contact_doc = frappe.get_doc("Contact", contact)
		for link in contact_doc.get("links", []):
			if link.link_doctype == "Customer":
				return link.link_name
		return None

	def _docs(self, doctype: str, customer: str, limit: int = 3) -> list:
		"""Recent documents of one type for a customer (panel cards)."""
		try:
			return frappe.get_all(
				doctype,
				filters={"customer": customer, "docstatus": ["<", 2]},
				fields=_CONTEXT_FIELDS[doctype],
				order_by="modified desc",
				limit=limit,
			)
		except Exception:
			return []

	def allowed_send_doctypes(self) -> list[str]:
		settings = frappe.get_cached_doc("Inbox CRM Settings")
		return [d.document_type for d in settings.get("sendable_doctypes", [])]

	def list_documents(self, doctype: str, customer: str | None, q: str = "") -> list[dict]:
		if doctype not in self.allowed_send_doctypes():
			frappe.throw(frappe._("Document type {0} is not enabled for sending.").format(doctype))
		filters = {"docstatus": ["<", 2]}
		if customer:
			filters["customer"] = customer
		if q:
			filters["name"] = ["like", f"%{q}%"]
		fields = _LIST_FIELDS.get(doctype, ["name", "grand_total", "status"])
		return frappe.get_all(doctype, filters=filters, fields=fields, order_by="modified desc", limit=20)

	def get_document_pdf(self, doctype: str, name: str, print_format: str | None = None) -> bytes:
		pf = print_format or frappe.db.get_single_value("Inbox CRM Settings", "print_format") or None
		return frappe.get_print(doctype, name, print_format=pf, as_pdf=True)

	def search_customers(self, q: str, limit: int = 10) -> list:
		rows = frappe.get_all(
			"Customer",
			filters={"customer_name": ["like", f"%{q}%"]},
			fields=["name", "customer_name"],
			limit=limit,
		)
		return [{"name": r.name, "label": r.customer_name or r.name} for r in rows]

	def suggest_customers_for_contact(self, contact: str) -> list:
		"""Suggest Customers linked to Contacts that share a phone number with *contact*."""
		try:
			contact_doc = frappe.get_doc("Contact", contact)
			phones = [p.phone for p in contact_doc.get("phone_nos", []) if p.phone]
			if not phones:
				return []

			customer_names: list[str] = []
			seen: set[str] = set()

			for phone in phones:
				sibling_phones = frappe.get_all(
					"Contact Phone",
					filters={"phone": phone},
					fields=["parent"],
				)
				for row in sibling_phones:
					sibling = row.parent
					if sibling == contact:
						continue
					sibling_doc = frappe.get_doc("Contact", sibling)
					for link in sibling_doc.get("links", []):
						if link.link_doctype == "Customer" and link.link_name not in seen:
							seen.add(link.link_name)
							customer_names.append(link.link_name)

			result = []
			for cust in customer_names:
				label = frappe.db.get_value("Customer", cust, "customer_name") or cust
				result.append({"name": cust, "label": label, "reason": "phone"})
			return result
		except Exception:
			return []

	def link_customer(self, contact: str, customer: str) -> None:
		if not frappe.db.exists("Customer", customer):
			frappe.throw(frappe._("Customer {0} not found").format(customer))
		contact_doc = frappe.get_doc("Contact", contact)
		# Remove any existing Customer links so there is exactly one after this call.
		contact_doc.links = [
			link for link in contact_doc.get("links", [])
			if link.link_doctype != "Customer"
		]
		contact_doc.append("links", {"link_doctype": "Customer", "link_name": customer})
		contact_doc.save(ignore_permissions=True)

	def unlink_customer(self, contact: str) -> None:
		contact_doc = frappe.get_doc("Contact", contact)
		contact_doc.links = [
			link for link in contact_doc.get("links", [])
			if link.link_doctype != "Customer"
		]
		contact_doc.save(ignore_permissions=True)

	def create_and_link_customer(self, contact: str, customer_name: str) -> str:
		customer_group = (
			frappe.db.get_single_value("Selling Settings", "customer_group") or "All Customer Groups"
		)
		territory = (
			frappe.db.get_single_value("Selling Settings", "territory") or "All Territories"
		)
		customer_doc = frappe.get_doc({
			"doctype": "Customer",
			"customer_name": customer_name,
			"customer_group": customer_group,
			"territory": territory,
		})
		customer_doc.insert(ignore_permissions=True)
		self.link_customer(contact, customer_doc.name)
		return customer_doc.name
