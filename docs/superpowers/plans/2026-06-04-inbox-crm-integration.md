# Inbox ↔ CRM/ERP Integration (Spec #1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pluggable CRM/ERP provider to `sopwer_inbox` (ERPNext first) that powers a read-only customer context panel and lets agents send ERP documents (Quotation/Sales Order/Sales Invoice) as PDFs to the customer through the chat channel.

**Architecture:** A `BaseCRMProvider` abstraction (mirroring the existing Channel Adapter pattern) selected per-site via an `Inbox CRM Settings` Single. The core never calls a CRM/ERP API directly. ERPNext is the only concrete provider in this milestone; Frappe CRM / External are stubs. Document send reuses the existing channel media-send pipeline (`conversation.send_message` → adapter `sendDocument`/`send_file`).

**Tech Stack:** Frappe v15 (Python 3.12), `FrappeTestCase` (via `InboxTestCase` base), React + TypeScript + frappe-react-sdk frontend.

---

## Setup (run once, every command below assumes this)

```bash
export PATH=/opt/anaconda3/envs/env/bin:$PATH
cd /Users/ramdani/Documents/development/erpnext
```

- Dev/test site: **`inbox.dev`** (Frappe-only) for unit tests; ERPNext-backed behavior is mocked in tests (no real ERPNext needed).
- Run a module's tests: `bench --site inbox.dev run-tests --app sopwer_inbox --module <dotted.module>`
- After DocType JSON changes: `bench --site inbox.dev migrate`
- Frontend build: `cd apps/sopwer_inbox/frontend && npm run build`
- App python root: `apps/sopwer_inbox/sopwer_inbox/`
- Tests extend `sopwer_inbox.tests.base.InboxTestCase` (per-test rollback already handled there).

## File Structure

**Create:**
- `sopwer_inbox/crm/__init__.py` — package
- `sopwer_inbox/crm/base.py` — `BaseCRMProvider`
- `sopwer_inbox/crm/registry.py` — `get_provider()`
- `sopwer_inbox/crm/erpnext.py` — `ERPNextProvider`
- `sopwer_inbox/crm/tests/__init__.py`, `test_registry.py`, `test_erpnext_provider.py`
- `sopwer_inbox/sopwer_inbox/doctype/inbox_crm_settings/` — Single config
- `sopwer_inbox/sopwer_inbox/doctype/inbox_sendable_document_type/` — child
- `sopwer_inbox/sopwer_inbox/doctype/inbox_document_role/` — child
- `sopwer_inbox/api/document.py` — `list_sendable_documents`, `send_document`
- `sopwer_inbox/api/tests/test_document.py`
- Frontend: `frontend/src/components/DocumentPicker.tsx`

**Modify:**
- `sopwer_inbox/api/context.py` — route ERP context through the provider
- `frontend/src/hooks/useInboxApi.ts` — add document calls
- `frontend/src/components/Thread.tsx` — "Kirim Dokumen" button + modal wiring
- `frontend/src/types/index.ts` — document types

---

## Task 1: Config DocTypes (`Inbox CRM Settings` + child tables)

**Files:**
- Create: `sopwer_inbox/sopwer_inbox/doctype/inbox_document_role/inbox_document_role.json` (+ `__init__.py`, `.py`)
- Create: `sopwer_inbox/sopwer_inbox/doctype/inbox_sendable_document_type/inbox_sendable_document_type.json` (+ `__init__.py`, `.py`)
- Create: `sopwer_inbox/sopwer_inbox/doctype/inbox_crm_settings/inbox_crm_settings.json` (+ `__init__.py`, `.py`)

- [ ] **Step 1: Create the two child DocTypes**

`inbox_document_role/inbox_document_role.json`:
```json
{
 "actions": [], "creation": "2026-06-04 00:00:00", "doctype": "DocType",
 "engine": "InnoDB", "istable": 1, "module": "Sopwer Inbox",
 "name": "Inbox Document Role", "naming_rule": "Random",
 "field_order": ["role"],
 "fields": [{"fieldname": "role", "fieldtype": "Link", "options": "Role", "label": "Role", "in_list_view": 1, "reqd": 1}],
 "permissions": []
}
```

`inbox_sendable_document_type/inbox_sendable_document_type.json`:
```json
{
 "actions": [], "creation": "2026-06-04 00:00:00", "doctype": "DocType",
 "engine": "InnoDB", "istable": 1, "module": "Sopwer Inbox",
 "name": "Inbox Sendable Document Type", "naming_rule": "Random",
 "field_order": ["document_type"],
 "fields": [{"fieldname": "document_type", "fieldtype": "Link", "options": "DocType", "label": "Document Type", "in_list_view": 1, "reqd": 1}],
 "permissions": []
}
```

Each folder also gets an empty `__init__.py` and a controller `.py`:
```python
# inbox_document_role.py
import frappe  # noqa: F401
from frappe.model.document import Document


class InboxDocumentRole(Document):
	pass
```
(same shape for `InboxSendableDocumentType`).

- [ ] **Step 2: Create the `Inbox CRM Settings` Single**

`inbox_crm_settings/inbox_crm_settings.json`:
```json
{
 "actions": [], "creation": "2026-06-04 00:00:00", "doctype": "DocType",
 "engine": "InnoDB", "issingle": 1, "module": "Sopwer Inbox",
 "name": "Inbox CRM Settings", "naming_rule": "Expression",
 "field_order": ["provider", "lead_capture", "external_section", "external_base_url",
   "external_api_key", "documents_section", "sendable_doctypes", "document_send_roles", "print_format"],
 "fields": [
  {"fieldname": "provider", "fieldtype": "Select", "label": "Provider", "options": "None\nERPNext\nFrappe CRM\nExternal", "default": "None"},
  {"fieldname": "lead_capture", "fieldtype": "Select", "label": "Lead Capture", "options": "Off\nManual\nAuto", "default": "Off"},
  {"fieldname": "external_section", "fieldtype": "Section Break", "label": "External Provider", "depends_on": "eval:doc.provider=='External'"},
  {"fieldname": "external_base_url", "fieldtype": "Data", "label": "External Base URL"},
  {"fieldname": "external_api_key", "fieldtype": "Password", "label": "External API Key"},
  {"fieldname": "documents_section", "fieldtype": "Section Break", "label": "Document Sending"},
  {"fieldname": "sendable_doctypes", "fieldtype": "Table MultiSelect", "label": "Sendable Document Types", "options": "Inbox Sendable Document Type"},
  {"fieldname": "document_send_roles", "fieldtype": "Table MultiSelect", "label": "Roles Allowed to Send Documents", "options": "Inbox Document Role"},
  {"fieldname": "print_format", "fieldtype": "Data", "label": "Print Format (optional)"}
 ],
 "permissions": [
  {"role": "Inbox Manager", "read": 1, "write": 1, "create": 1},
  {"role": "System Manager", "read": 1, "write": 1, "create": 1}
 ]
}
```
Controller `inbox_crm_settings.py`:
```python
import frappe  # noqa: F401
from frappe.model.document import Document


class InboxCRMSettings(Document):
	pass
```

- [ ] **Step 3: Migrate**

Run: `bench --site inbox.dev migrate`
Expected: completes without error; `bench --site inbox.dev execute frappe.client.get_count --kwargs "{'doctype':'DocType','filters':{'module':'Sopwer Inbox'}}"` increased by 3.

- [ ] **Step 4: Commit**

```bash
git add apps/sopwer_inbox/sopwer_inbox/sopwer_inbox/doctype/inbox_crm_settings apps/sopwer_inbox/sopwer_inbox/sopwer_inbox/doctype/inbox_sendable_document_type apps/sopwer_inbox/sopwer_inbox/sopwer_inbox/doctype/inbox_document_role
git -C apps/sopwer_inbox commit -m "feat(crm): Inbox CRM Settings single + child tables"
```

---

## Task 2: `BaseCRMProvider` + registry

**Files:**
- Create: `sopwer_inbox/crm/__init__.py` (empty), `sopwer_inbox/crm/tests/__init__.py` (empty)
- Create: `sopwer_inbox/crm/base.py`
- Create: `sopwer_inbox/crm/registry.py`
- Test: `sopwer_inbox/crm/tests/test_registry.py`

- [ ] **Step 1: Write the failing test**

`sopwer_inbox/crm/tests/test_registry.py`:
```python
import frappe
from sopwer_inbox.crm.registry import get_provider
from sopwer_inbox.tests.base import InboxTestCase


class TestCRMRegistry(InboxTestCase):
	def _set_provider(self, value):
		frappe.db.set_single_value("Inbox CRM Settings", "provider", value)

	def test_none_provider_returns_none(self):
		self._set_provider("None")
		self.assertIsNone(get_provider())

	def test_erpnext_provider_selected(self):
		self._set_provider("ERPNext")
		provider = get_provider()
		# ERPNextProvider instance even if erpnext not installed (is_available() handles that)
		self.assertEqual(provider.__class__.__name__, "ERPNextProvider")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.crm.tests.test_registry`
Expected: FAIL (ModuleNotFoundError: sopwer_inbox.crm.registry)

- [ ] **Step 3: Write `base.py`**

```python
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
```

- [ ] **Step 4: Write `registry.py`**

```python
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
```

- [ ] **Step 5: Create minimal stubs so imports resolve**

`sopwer_inbox/crm/frappe_crm.py` and `sopwer_inbox/crm/external.py`:
```python
from sopwer_inbox.crm.base import BaseCRMProvider


class FrappeCRMProvider(BaseCRMProvider):  # implemented in a later spec
	def is_available(self) -> bool:
		return False


class ExternalProvider(BaseCRMProvider):  # implemented in a later spec
	def is_available(self) -> bool:
		return False
```
(put `ExternalProvider` in `external.py`, `FrappeCRMProvider` in `frappe_crm.py`.)

- [ ] **Step 6: Create `erpnext.py` skeleton** (filled in Task 3)

```python
from sopwer_inbox.crm.base import BaseCRMProvider


class ERPNextProvider(BaseCRMProvider):
	def is_available(self) -> bool:
		import frappe

		return "erpnext" in frappe.get_installed_apps()
```

- [ ] **Step 7: Run test to verify it passes**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.crm.tests.test_registry`
Expected: PASS (2 tests)

- [ ] **Step 8: Commit**

```bash
git -C apps/sopwer_inbox add sopwer_inbox/crm
git -C apps/sopwer_inbox commit -m "feat(crm): BaseCRMProvider + registry + provider stubs"
```

---

## Task 3: `ERPNextProvider.get_contact_context`

**Files:**
- Modify: `sopwer_inbox/crm/erpnext.py`
- Test: `sopwer_inbox/crm/tests/test_erpnext_provider.py`

- [ ] **Step 1: Write the failing test** (mock ERPNext absence + customer resolution)

`sopwer_inbox/crm/tests/test_erpnext_provider.py`:
```python
from unittest.mock import patch

from sopwer_inbox.crm.erpnext import ERPNextProvider
from sopwer_inbox.tests.base import InboxTestCase, make_contact


class TestERPNextProvider(InboxTestCase):
	def test_context_none_when_no_customer(self):
		contact = make_contact("NoCust", "+628000111222")
		p = ERPNextProvider()
		with patch.object(p, "_linked_customer", return_value=None):
			self.assertIsNone(p.get_contact_context(contact.name))

	def test_context_returns_customer_block(self):
		contact = make_contact("HasCust", "+628000111333")
		p = ERPNextProvider()
		with patch.object(p, "_linked_customer", return_value="CUST-0001"), patch.object(
			p, "_recent_documents", return_value=[{"name": "SO-1", "grand_total": 100}]
		):
			ctx = p.get_contact_context(contact.name)
		self.assertEqual(ctx["customer"], "CUST-0001")
		self.assertEqual(ctx["recent_documents"][0]["name"], "SO-1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.crm.tests.test_erpnext_provider`
Expected: FAIL (AttributeError: `_linked_customer`)

- [ ] **Step 3: Implement `get_contact_context` + helpers in `erpnext.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.crm.tests.test_erpnext_provider`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C apps/sopwer_inbox add sopwer_inbox/crm
git -C apps/sopwer_inbox commit -m "feat(crm): ERPNextProvider.get_contact_context"
```

---

## Task 4: Route `api/context.py` through the provider

**Files:**
- Modify: `sopwer_inbox/api/context.py`
- Test: `sopwer_inbox/api/tests/test_context.py` (existing — keep passing)

- [ ] **Step 1: Modify `get_contact_context` to use the provider**

Replace the `"erp": get_erp_context(contact_doc)` line and the `get_erp_context`/`_linked_customer` functions with:
```python
from sopwer_inbox.crm.registry import get_provider

# inside get_contact_context(...):
		"erp": _provider_context(contact_doc.name),

# new module function (replaces get_erp_context):
def _provider_context(contact_name):
	provider = get_provider()
	if not provider:
		return None
	try:
		return provider.get_contact_context(contact_name)
	except Exception:
		frappe.log_error(title="Sopwer Inbox CRM context failed", message=frappe.get_traceback())
		return None
```
Delete the old `get_erp_context` and `_linked_customer` from `context.py` (now in the provider).

- [ ] **Step 2: Run the existing context test (must still pass on a no-ERPNext site)**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.api.tests.test_context`
Expected: PASS — `test_context_safe_without_erpnext` still green (provider is `None` by default → `erp` is `None`).

- [ ] **Step 3: Commit**

```bash
git -C apps/sopwer_inbox add sopwer_inbox/api/context.py
git -C apps/sopwer_inbox commit -m "refactor(context): route ERP context through CRM provider"
```

---

## Task 5: `ERPNextProvider` — `allowed_send_doctypes` + `list_documents`

**Files:**
- Modify: `sopwer_inbox/crm/erpnext.py`
- Test: `sopwer_inbox/crm/tests/test_erpnext_provider.py`

- [ ] **Step 1: Write failing tests**

Append to `test_erpnext_provider.py`:
```python
import frappe


class TestERPNextDocuments(InboxTestCase):
	def setUp(self):
		frappe.db.set_single_value("Inbox CRM Settings", "provider", "ERPNext")
		s = frappe.get_doc("Inbox CRM Settings")
		s.set("sendable_doctypes", [])
		s.append("sendable_doctypes", {"document_type": "Sales Invoice"})
		s.save(ignore_permissions=True)

	def test_allowed_doctypes_from_settings(self):
		self.assertEqual(ERPNextProvider().allowed_send_doctypes(), ["Sales Invoice"])
```

- [ ] **Step 2: Run to verify fail**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.crm.tests.test_erpnext_provider`
Expected: FAIL (`allowed_send_doctypes` returns `[]` from base)

- [ ] **Step 3: Implement in `erpnext.py`**

```python
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
```

- [ ] **Step 4: Run to verify pass**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.crm.tests.test_erpnext_provider`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C apps/sopwer_inbox add sopwer_inbox/crm
git -C apps/sopwer_inbox commit -m "feat(crm): ERPNextProvider allowed_send_doctypes + list_documents"
```

---

## Task 6: `ERPNextProvider.get_document_pdf`

**Files:**
- Modify: `sopwer_inbox/crm/erpnext.py`
- Test: `sopwer_inbox/crm/tests/test_erpnext_provider.py`

- [ ] **Step 1: Write failing test (mock frappe.get_print)**

```python
from unittest.mock import patch


class TestERPNextPdf(InboxTestCase):
	def test_get_document_pdf_calls_get_print(self):
		with patch("frappe.get_print", return_value=b"%PDF-1.4 fake") as gp:
			data = ERPNextProvider().get_document_pdf("Sales Invoice", "INV-1")
		self.assertEqual(data, b"%PDF-1.4 fake")
		gp.assert_called_once()
```

- [ ] **Step 2: Run to verify fail**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.crm.tests.test_erpnext_provider`
Expected: FAIL (NotImplementedError from base)

- [ ] **Step 3: Implement**

```python
	def get_document_pdf(self, doctype: str, name: str, print_format: str | None = None) -> bytes:
		pf = print_format or frappe.db.get_single_value("Inbox CRM Settings", "print_format") or None
		return frappe.get_print(doctype, name, print_format=pf, as_pdf=True)
```

- [ ] **Step 4: Run to verify pass**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.crm.tests.test_erpnext_provider`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C apps/sopwer_inbox add sopwer_inbox/crm
git -C apps/sopwer_inbox commit -m "feat(crm): ERPNextProvider.get_document_pdf"
```

---

## Task 7: `api/document.list_sendable_documents`

**Files:**
- Create: `sopwer_inbox/api/document.py`
- Test: `sopwer_inbox/api/tests/test_document.py`

- [ ] **Step 1: Write failing tests (guards)**

`sopwer_inbox/api/tests/test_document.py`:
```python
from unittest.mock import patch

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
			"list_documents": lambda self, dt, cust, q="": [{"name": "INV-1"}],
		})()
		with patch.object(doc_api, "get_provider", return_value=fake), patch.object(
			doc_api, "_conversation_customer", return_value="CUST-1"
		):
			rows = doc_api.list_sendable_documents(self.conv.name, "Sales Invoice")
		self.assertEqual(rows[0]["name"], "INV-1")
```

- [ ] **Step 2: Run to verify fail**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.api.tests.test_document`
Expected: FAIL (ModuleNotFoundError sopwer_inbox.api.document)

- [ ] **Step 3: Implement `api/document.py`**

```python
# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
"""Send ERP/CRM documents to the customer through the chat channel."""

import frappe
from frappe import _

from sopwer_inbox.crm.registry import get_provider


def _require_provider():
	provider = get_provider()
	if not provider:
		frappe.throw(_("No CRM/ERP provider configured."))
	return provider


def _require_send_permission():
	settings = frappe.get_cached_doc("Inbox CRM Settings")
	allowed_roles = {r.role for r in settings.get("document_send_roles", [])} or {"Inbox Manager"}
	user_roles = set(frappe.get_roles())
	if "System Manager" in user_roles or allowed_roles & user_roles:
		return
	frappe.throw(_("You are not allowed to send documents."), frappe.PermissionError)


def _conversation_customer(conversation: str):
	contact = frappe.db.get_value("Inbox Conversation", conversation, "contact")
	if not contact:
		return None
	provider = get_provider()
	return provider._linked_customer(contact) if hasattr(provider, "_linked_customer") else None


@frappe.whitelist()
def list_sendable_documents(conversation, doctype, q=""):
	provider = _require_provider()
	_require_send_permission()
	if doctype not in provider.allowed_send_doctypes():
		frappe.throw(_("Document type {0} is not enabled.").format(doctype))
	customer = _conversation_customer(conversation)
	return provider.list_documents(doctype, customer, q)
```

- [ ] **Step 4: Run to verify pass**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.api.tests.test_document`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git -C apps/sopwer_inbox add sopwer_inbox/api/document.py sopwer_inbox/api/tests/test_document.py
git -C apps/sopwer_inbox commit -m "feat(api): list_sendable_documents with provider + role/doctype guards"
```

---

## Task 8: `api/document.send_document`

**Files:**
- Modify: `sopwer_inbox/api/document.py`
- Test: `sopwer_inbox/api/tests/test_document.py`

- [ ] **Step 1: Write failing tests**

Append:
```python
	def test_send_rejects_cross_customer_document(self):
		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"get_document_pdf": lambda self, dt, name, print_format=None: b"%PDF",
		})()
		with patch.object(doc_api, "get_provider", return_value=fake), patch.object(
			doc_api, "_conversation_customer", return_value="CUST-1"
		), patch("frappe.db.get_value", return_value="CUST-OTHER"):
			with self.assertRaises(frappe.ValidationError):
				doc_api.send_document(self.conv.name, "Sales Invoice", "INV-OTHER")

	def test_send_dispatches_document_message(self):
		fake = type("P", (), {
			"allowed_send_doctypes": lambda self: ["Sales Invoice"],
			"get_document_pdf": lambda self, dt, name, print_format=None: b"%PDF-1.4",
		})()
		sent = {}
		def fake_send(conversation, text=None, message_type="Text", media_path=None, **k):
			sent.update({"conversation": conversation, "media_path": media_path, "type": message_type})
			return {"name": "msg1"}
		with patch.object(doc_api, "get_provider", return_value=fake), patch.object(
			doc_api, "_conversation_customer", return_value="CUST-1"
		), patch.object(doc_api, "_document_customer", return_value="CUST-1"), patch(
			"sopwer_inbox.api.conversation.send_message", side_effect=fake_send
		):
			doc_api.send_document(self.conv.name, "Sales Invoice", "INV-1")
		self.assertTrue(sent["media_path"])
		self.assertEqual(sent["type"], "File")
```

- [ ] **Step 2: Run to verify fail**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.api.tests.test_document`
Expected: FAIL (`send_document` not defined)

- [ ] **Step 3: Implement `send_document` + `_document_customer`**

```python
def _document_customer(doctype, name):
	return frappe.db.get_value(doctype, name, "customer")


@frappe.whitelist()
def send_document(conversation, doctype, name):
	provider = _require_provider()
	_require_send_permission()
	if doctype not in provider.allowed_send_doctypes():
		frappe.throw(_("Document type {0} is not enabled.").format(doctype))

	conv_customer = _conversation_customer(conversation)
	doc_customer = _document_customer(doctype, name)
	if conv_customer and doc_customer and conv_customer != doc_customer:
		frappe.throw(_("This document belongs to a different customer."))

	pdf = provider.get_document_pdf(doctype, name)
	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": f"{name}.pdf",
		"content": pdf,
		"is_private": 1,
		"attached_to_doctype": "Inbox Conversation",
		"attached_to_name": conversation,
	})
	file_doc.insert(ignore_permissions=True)

	from sopwer_inbox.api.conversation import send_message

	return send_message(
		conversation,
		text=f"{doctype} {name}",
		message_type="File",
		media_path=file_doc.file_url,
	)
```

- [ ] **Step 4: Run to verify pass**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.api.tests.test_document`
Expected: PASS

- [ ] **Step 5: Run the whole suite (no regressions)**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox`
Expected: PASS (all tests, including prior phases)

- [ ] **Step 6: Commit**

```bash
git -C apps/sopwer_inbox add sopwer_inbox/api/document.py sopwer_inbox/api/tests/test_document.py
git -C apps/sopwer_inbox commit -m "feat(api): send_document -> PDF -> private File -> channel media send"
```

---

## Task 9: Frontend — API hook + types

**Files:**
- Modify: `frontend/src/hooks/useInboxApi.ts`
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add a document types block to `types/index.ts`**

```ts
export interface SendableDocument {
  name: string;
  date?: string;
  grand_total?: number;
  status?: string;
  currency?: string;
  doctype?: string;
}
```

- [ ] **Step 2: Add document calls to `useInboxApi`**

In `useInboxApi.ts`, add:
```ts
import { useFrappeGetCall } from "frappe-react-sdk";
const D = "sopwer_inbox.api.document";
// inside useInboxApi():
const { call: sendDocCall } = useFrappePostCall(`${D}.send_document`);
// add to the returned object:
sendDocument: (conversation: string, doctype: string, name: string) =>
  sendDocCall({ conversation, doctype, name }),
```
For listing, the picker uses `useFrappeGetCall("sopwer_inbox.api.document.list_sendable_documents", { conversation, doctype, q })` directly (see Task 10).

- [ ] **Step 3: Build to typecheck**

Run: `cd apps/sopwer_inbox/frontend && npm run build`
Expected: `✓ built` (tsc clean)

- [ ] **Step 4: Commit**

```bash
git -C apps/sopwer_inbox add frontend/src/hooks/useInboxApi.ts frontend/src/types/index.ts frontend/../sopwer_inbox/public/frontend
git -C apps/sopwer_inbox commit -m "feat(frontend): document send API hook + types"
```

---

## Task 10: Frontend — Document picker modal + Thread button (manual QA)

**Files:**
- Create: `frontend/src/components/DocumentPicker.tsx`
- Modify: `frontend/src/components/Thread.tsx`

- [ ] **Step 1: Create `DocumentPicker.tsx`**

A modal that: takes `conversation`, `allowedDoctypes` (from `useFrappeGetCall` on a tiny `get_send_config` OR derive from settings; for v1 hardcode the allowed list returned by a new `list_sendable_documents` precheck), shows a doctype selector + search box, lists documents via `useFrappeGetCall("sopwer_inbox.api.document.list_sendable_documents", {conversation, doctype, q})`, and on row click calls `onSend(doctype, name)`.

```tsx
import { useState } from "react";
import { useFrappeGetCall } from "frappe-react-sdk";
import { Ic } from "./icons";
import type { SendableDocument } from "@/types";

export function DocumentPicker({
  conversation,
  doctypes,
  onClose,
  onSend,
}: {
  conversation: string;
  doctypes: string[];
  onClose: () => void;
  onSend: (doctype: string, name: string) => void;
}) {
  const [doctype, setDoctype] = useState(doctypes[0] || "");
  const [q, setQ] = useState("");
  const { data } = useFrappeGetCall<{ message: SendableDocument[] }>(
    "sopwer_inbox.api.document.list_sendable_documents",
    { conversation, doctype, q },
    doctype ? undefined : null, // don't fetch until a doctype is chosen
  );
  const rows = data?.message || [];
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal doc-picker" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Kirim Dokumen</h3>
          <button className="icon-btn" onClick={onClose}><Ic.X size={16} /></button>
        </div>
        <div className="doc-controls">
          <select value={doctype} onChange={(e) => setDoctype(e.target.value)}>
            {doctypes.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <input placeholder="Cari nomor dokumen…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="doc-list">
          {rows.length === 0 && <div className="doc-empty">Tidak ada dokumen.</div>}
          {rows.map((r) => (
            <button key={r.name} className="doc-row" onClick={() => onSend(doctype, r.name)}>
              <span className="no">{r.name}</span>
              <span className="meta">{r.date} · {r.status}</span>
              <span className="total">{r.grand_total}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add the config endpoint** (so the frontend knows allowed doctypes + whether the user may send)

Add to `sopwer_inbox/api/document.py`:
```python
@frappe.whitelist()
def get_send_config():
	provider = get_provider()
	if not provider:
		return {"enabled": False, "doctypes": []}
	settings = frappe.get_cached_doc("Inbox CRM Settings")
	allowed_roles = {r.role for r in settings.get("document_send_roles", [])} or {"Inbox Manager"}
	user_roles = set(frappe.get_roles())
	can_send = "System Manager" in user_roles or bool(allowed_roles & user_roles)
	return {"enabled": can_send, "doctypes": provider.allowed_send_doctypes() if can_send else []}
```
Re-run `bench --site inbox.dev run-tests --app sopwer_inbox --module sopwer_inbox.api.tests.test_document` to confirm still green, then commit this small addition.

- [ ] **Step 3: Wire into `Thread.tsx`**

- `useFrappeGetCall("sopwer_inbox.api.document.get_send_config")` → `{enabled, doctypes}`.
- If `enabled && doctypes.length`, render a toolbar button **📄 Kirim Dokumen** (use `Ic.File`) near the composer/header that opens `<DocumentPicker>`.
- `onSend(doctype, name)` → `api.sendDocument(conv.id, doctype, name)` → on success `mutateMessages()` + close modal; the document arrives as an outgoing `File` message (existing media bubble renders it).

- [ ] **Step 4: Build**

Run: `cd apps/sopwer_inbox/frontend && npm run build`
Expected: `✓ built`

- [ ] **Step 5: Manual QA (on a site with ERPNext + a Customer linked to the contact)**

1. Set `Inbox CRM Settings`: provider=ERPNext, sendable_doctypes=[Sales Invoice], document_send_roles=[Inbox Manager].
2. Open a conversation whose Contact is linked to a Customer.
3. Click 📄 Kirim Dokumen → pick Sales Invoice → search → select → confirm.
4. Verify: outgoing File bubble appears; PDF delivered to the customer on Telegram/WhatsApp; delivery status updates; non-customer documents not listed.

- [ ] **Step 6: Commit**

```bash
git -C apps/sopwer_inbox add frontend sopwer_inbox/public/frontend sopwer_inbox/api/document.py
git -C apps/sopwer_inbox commit -m "feat(frontend): document picker + Kirim Dokumen in thread"
```

---

## Task 11: Final verification + deploy notes

- [ ] **Step 1: Full suite green**

Run: `bench --site inbox.dev run-tests --app sopwer_inbox`
Expected: PASS (all).

- [ ] **Step 2: Migrate + build on the pilot server** (deploy)

```bash
cd ~/frappe-bench/apps/sopwer_inbox && git pull origin main && cd ~/frappe-bench
bench --site retail.sopwer.id migrate
bench --site retail.sopwer.id clear-website-cache
bench restart
```
Then configure `Inbox CRM Settings` on the site (provider=ERPNext, sendable_doctypes, roles).

- [ ] **Step 3: Push**

```bash
git -C apps/sopwer_inbox push origin main
```

---

## Self-review notes (addressed)
- **Spec coverage:** Foundation (Task 1–2), Phase A context (Task 3–4), Phase C documents (Task 5–8 backend, 9–10 frontend), security guards (Task 7–8: provider/role/doctype/cross-customer), testing (each backend task), config (Task 1). Phase B/D explicitly out of scope (separate specs).
- **Types consistent:** `get_contact_context`, `allowed_send_doctypes`, `list_documents`, `get_document_pdf`, `_linked_customer`, `_conversation_customer`, `_document_customer` used consistently across tasks.
- **No placeholders:** every code step shows real code; commands have expected output. Frontend UI steps are manual-QA per the app's TDD convention (React components are manual-QA, see app CLAUDE.md).
