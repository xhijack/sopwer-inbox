from sopwer_inbox.crm.base import BaseCRMProvider


class ERPNextProvider(BaseCRMProvider):
	def is_available(self) -> bool:
		import frappe

		return "erpnext" in frappe.get_installed_apps()
