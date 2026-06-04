from unittest.mock import MagicMock, call, patch

import frappe

from sopwer_inbox.api import document as doc_api
from sopwer_inbox.tests.base import InboxTestCase, make_channel, make_conversation


class TestDocumentApi(InboxTestCase):
	def setUp(self):
		self.channel = make_channel("Doc TG", "Telegram")
		self.conv = make_conversation(self.channel.name, "doc-1")
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "ERPNext")

	def test_rejects_when_no_provider(self):
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "None")
		with self.assertRaises(frappe.ValidationError):
			doc_api.list_sendable_documents(self.conv.name, "Sales Invoice")

	def test_lists_via_provider(self):
		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"list_documents": lambda self, dt, cust, q="", company=None: [{"name": "INV-1"}],
		})()
		with patch.object(doc_api, "get_provider", return_value=fake), patch.object(
			doc_api, "_conversation_customer", return_value="CUST-1"
		):
			rows = doc_api.list_sendable_documents(self.conv.name, "Sales Invoice")
		self.assertEqual(rows[0]["name"], "INV-1")

	def test_list_empty_when_no_conversation_customer(self):
		"""list_sendable_documents must return [] and NOT call list_documents when the
		conversation has no linked ERP customer (fail-closed, mirrors send_document)."""
		mock_list_docs = MagicMock(return_value=[{"name": "INV-LEAK"}])
		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"list_documents": mock_list_docs,
		})()
		with patch.object(doc_api, "get_provider", return_value=fake), patch.object(
			doc_api, "_conversation_customer", return_value=None
		):
			result = doc_api.list_sendable_documents(self.conv.name, "Sales Invoice")
		self.assertEqual(result, [])
		mock_list_docs.assert_not_called()

	def test_list_rejects_without_permission(self):
		fake = type("P", (), {"allowed_send_doctypes": lambda self: ["Sales Invoice"]})()
		with patch.object(doc_api, "get_provider", return_value=fake), patch.object(
			doc_api, "_require_send_permission", side_effect=frappe.PermissionError
		):
			with self.assertRaises(frappe.PermissionError):
				doc_api.list_sendable_documents(self.conv.name, "Sales Invoice")

	def test_send_rejects_cross_customer_document(self):
		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"get_document_pdf": lambda self, dt, name, print_format=None: b"%PDF",
		})()
		with patch.object(doc_api, "get_provider", return_value=fake), patch.object(
			doc_api, "_conversation_customer", return_value="CUST-1"
		), patch.object(doc_api, "_document_customer", return_value="CUST-OTHER"):
			with self.assertRaises(frappe.ValidationError):
				doc_api.send_document(self.conv.name, "Sales Invoice", "INV-OTHER")

	def test_send_blocked_when_no_conversation_customer(self):
		"""Block send when the conversation has no linked ERP customer (safe-by-default)."""
		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"get_document_pdf": lambda self, dt, name, print_format=None: b"%PDF",
		})()
		with patch.object(doc_api, "get_provider", return_value=fake), patch.object(
			doc_api, "_conversation_customer", return_value=None
		), patch.object(doc_api, "_document_customer", return_value="CUST-1"):
			with self.assertRaises(frappe.ValidationError):
				doc_api.send_document(self.conv.name, "Sales Invoice", "INV-1")

	def test_send_dispatches_document_message(self):
		fake_provider = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"get_document_pdf": lambda self, dt, name, print_format=None: b"%PDF-1.4",
		})()
		sent = {}

		def fake_send(conversation, text=None, message_type="Text", media_path=None, **k):
			sent.update({"conversation": conversation, "media_path": media_path, "type": message_type})
			return {"name": "msg1"}

		fake_file = MagicMock()
		fake_file.file_url = "/private/files/INV-1.pdf"

		with patch.object(doc_api, "get_provider", return_value=fake_provider), \
				patch.object(doc_api, "_require_send_permission"), \
				patch.object(doc_api, "_conversation_customer", return_value="CUST-1"), \
				patch.object(doc_api, "_document_customer", return_value="CUST-1"), \
				patch("sopwer_inbox.api.conversation.send_message", side_effect=fake_send), \
				patch("frappe.get_doc", return_value=fake_file):
			doc_api.send_document(self.conv.name, "Sales Invoice", "INV-1")
		self.assertTrue(sent["media_path"])
		self.assertEqual(sent["type"], "File")

	# ------------------------------------------------------------------
	# get_send_config
	# ------------------------------------------------------------------

	def test_send_config_disabled_when_no_provider(self):
		"""Returns enabled=False and empty doctypes when provider is None."""
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "None")
		result = doc_api.get_send_config()
		self.assertEqual(result, {"enabled": False, "doctypes": []})

	def test_send_config_returns_doctypes_when_permitted(self):
		"""Administrator (has System Manager) gets enabled=True and the provider doctypes."""
		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
		})()
		with patch.object(doc_api, "get_provider", return_value=fake):
			result = doc_api.get_send_config()
		self.assertTrue(result["enabled"])
		self.assertEqual(result["doctypes"], ["Sales Invoice"])

	def test_send_config_hides_doctypes_when_not_permitted(self):
		"""User without System Manager or allowed roles gets enabled=False and empty doctypes."""
		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
		})()
		# Ensure document_send_roles is empty so the default {"Inbox Manager"} applies.
		settings = frappe.get_cached_doc("Inbox CRM Settings")
		settings.document_send_roles = []
		# Patch get_provider so it returns our fake, and patch get_roles to
		# return only "Inbox Agent" (no System Manager, no Inbox Manager).
		with patch.object(doc_api, "get_provider", return_value=fake), \
				patch("frappe.get_roles", return_value=["Inbox Agent"]), \
				patch("frappe.get_cached_doc", return_value=settings):
			result = doc_api.get_send_config()
		self.assertFalse(result["enabled"])
		self.assertEqual(result["doctypes"], [])


# ---------------------------------------------------------------------------
# Company scoping tests
# ---------------------------------------------------------------------------

class TestDocumentCompanyScoping(InboxTestCase):
	"""list_sendable_documents passes channel company; send_document guards cross-company."""

	def setUp(self):
		self.channel = make_channel("CompScope TG", "Telegram")
		self.conv = make_conversation(self.channel.name, "compscope-1")
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "ERPNext")

	def test_list_forwards_channel_company_to_provider(self):
		"""list_sendable_documents must pass company= from the channel to list_documents."""
		list_docs_calls = []

		def fake_list_docs(self_inner, dt, cust, q="", company=None):
			list_docs_calls.append({"company": company})
			return []

		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"list_documents": fake_list_docs,
		})()

		with patch.object(doc_api, "get_provider", return_value=fake), \
				patch.object(doc_api, "_conversation_customer", return_value="CUST-1"), \
				patch.object(doc_api, "conversation_company", return_value="PT Sopwer"):
			doc_api.list_sendable_documents(self.conv.name, "Sales Invoice")

		self.assertEqual(len(list_docs_calls), 1)
		self.assertEqual(list_docs_calls[0]["company"], "PT Sopwer")

	def test_list_passes_none_company_when_channel_has_no_company(self):
		"""When the channel has no company, list_documents receives company=None."""
		list_docs_calls = []

		def fake_list_docs(self_inner, dt, cust, q="", company=None):
			list_docs_calls.append({"company": company})
			return []

		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"list_documents": fake_list_docs,
		})()

		with patch.object(doc_api, "get_provider", return_value=fake), \
				patch.object(doc_api, "_conversation_customer", return_value="CUST-1"), \
				patch.object(doc_api, "conversation_company", return_value=None):
			doc_api.list_sendable_documents(self.conv.name, "Sales Invoice")

		self.assertIsNone(list_docs_calls[0]["company"])

	def test_send_blocked_on_company_mismatch(self):
		"""send_document throws when channel company differs from document company."""
		fake_provider = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"get_document_pdf": lambda self, dt, name, print_format=None: b"%PDF",
		})()
		with patch.object(doc_api, "get_provider", return_value=fake_provider), \
				patch.object(doc_api, "_require_send_permission"), \
				patch.object(doc_api, "_conversation_customer", return_value="CUST-1"), \
				patch.object(doc_api, "_document_customer", return_value="CUST-1"), \
				patch.object(doc_api, "conversation_company", return_value="PT Sopwer"), \
				patch("frappe.db.get_value", return_value="PT Other"):
			with self.assertRaises(frappe.ValidationError):
				doc_api.send_document(self.conv.name, "Sales Invoice", "INV-CROSS")

	def test_send_proceeds_when_company_matches(self):
		"""send_document proceeds without error when channel and document company match."""
		fake_provider = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"get_document_pdf": lambda self, dt, name, print_format=None: b"%PDF-1.4",
		})()
		sent = {}

		def fake_send(conversation, text=None, message_type="Text", media_path=None, **k):
			sent["ok"] = True
			return {"name": "msg-ok"}

		fake_file = MagicMock()
		fake_file.file_url = "/private/files/INV-OK.pdf"

		with patch.object(doc_api, "get_provider", return_value=fake_provider), \
				patch.object(doc_api, "_require_send_permission"), \
				patch.object(doc_api, "_conversation_customer", return_value="CUST-1"), \
				patch.object(doc_api, "_document_customer", return_value="CUST-1"), \
				patch.object(doc_api, "conversation_company", return_value="PT Sopwer"), \
				patch("frappe.db.get_value", return_value="PT Sopwer"), \
				patch("sopwer_inbox.api.conversation.send_message", side_effect=fake_send), \
				patch("frappe.get_doc", return_value=fake_file):
			doc_api.send_document(self.conv.name, "Sales Invoice", "INV-OK")

		self.assertTrue(sent.get("ok"))

	def test_send_proceeds_when_channel_company_blank(self):
		"""send_document proceeds without company guard when channel has no company."""
		fake_provider = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"get_document_pdf": lambda self, dt, name, print_format=None: b"%PDF-1.4",
		})()
		sent = {}

		def fake_send(conversation, text=None, message_type="Text", media_path=None, **k):
			sent["ok"] = True
			return {"name": "msg-noco"}

		fake_file = MagicMock()
		fake_file.file_url = "/private/files/INV-NOCO.pdf"

		with patch.object(doc_api, "get_provider", return_value=fake_provider), \
				patch.object(doc_api, "_require_send_permission"), \
				patch.object(doc_api, "_conversation_customer", return_value="CUST-1"), \
				patch.object(doc_api, "_document_customer", return_value="CUST-1"), \
				patch.object(doc_api, "conversation_company", return_value=None), \
				patch("sopwer_inbox.api.conversation.send_message", side_effect=fake_send), \
				patch("frappe.get_doc", return_value=fake_file):
			doc_api.send_document(self.conv.name, "Sales Invoice", "INV-NOCO")

		self.assertTrue(sent.get("ok"))
