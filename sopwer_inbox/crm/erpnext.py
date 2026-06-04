# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
import frappe

from sopwer_inbox.crm.base import BaseCRMProvider

_DOC_FIELDS = {
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
			"recent_documents": self._recent_documents(customer),
		}

	def _linked_customer(self, contact: str):
		contact_doc = frappe.get_doc("Contact", contact)
		for link in contact_doc.get("links", []):
			if link.link_doctype == "Customer":
				return link.link_name
		return None

	def _recent_documents(self, customer: str):
		out = []
		for dt in ("Sales Order", "Sales Invoice"):
			try:
				rows = frappe.get_all(
					dt,
					filters={"customer": customer, "docstatus": ["<", 2]},
					fields=_DOC_FIELDS[dt],
					order_by="modified desc",
					limit=3,
				)
				for r in rows:
					r["doctype"] = dt
				out.extend(rows)
			except Exception:
				continue
		return out

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
		fields = _DOC_FIELDS.get(doctype, ["name", "grand_total", "status"])
		return frappe.get_all(doctype, filters=filters, fields=fields, order_by="modified desc", limit=20)

	def get_document_pdf(self, doctype: str, name: str, print_format: str | None = None) -> bytes:
		pf = print_format or frappe.db.get_single_value("Inbox CRM Settings", "print_format") or None
		return frappe.get_print(doctype, name, print_format=pf, as_pdf=True)
