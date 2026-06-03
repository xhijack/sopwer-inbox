# Design — Inbox ↔ CRM/ERP Integration (Spec #1: Foundation + Context Panel + Document Send)

**Date:** 2026-06-04
**App:** `sopwer_inbox`
**Status:** Approved (brainstorm) — ready for implementation plan

---

## 1. Overview

Connect the omnichannel inbox to a CRM/ERP backend so CS agents can see customer
context beside the chat and send business documents (Quotation / Sales Order /
Sales Invoice) as PDFs straight to the customer through the chat channel.

The integration is **provider-pluggable, per-client**: each site picks a provider
(ERPNext, Frappe CRM, or an external CRM) via config. The core inbox never calls a
CRM/ERP API directly — only through a `BaseCRMProvider`. This mirrors the existing
**Channel Adapter** pattern and the **ERP-optional** guard already in the app.

This spec covers the **first milestone (ERPNext provider v1)**:
- **Foundation** — provider adapter contract + registry + per-site config.
- **Phase A** — read-only CRM/ERP context panel (generalizes today's ERP card).
- **Phase C** — send a document (PDF) to the customer via the channel.

**Out of scope here (future specs):** Phase B (lead capture), Phase D (two-way
chat history inside the CRM), and the Frappe CRM / External providers (contract is
designed for them, but only ERPNext is implemented now).

## 2. Goals & non-goals

**Goals**
- One provider abstraction usable for ERPNext (now), Frappe CRM + External (later).
- Per-client config; if no provider / backing app missing, all CRM features hide
  cleanly and the inbox still works fully (zero hard coupling).
- Agents see the contact's customer + recent documents + open lead/opportunity.
- Agents (gated by role + admin-enabled doctypes) send a document PDF to the
  customer, reusing the existing media-send pipeline.

**Non-goals (this spec)**
- Creating leads/deals from chat (Phase B).
- Surfacing chat history inside the CRM UI (Phase D).
- Editing/creating ERP documents from the inbox (read + send only).

## 3. Architecture — Provider Adapter + Config

```
sopwer_inbox/crm/
├── base.py         # BaseCRMProvider (abstract)
├── registry.py     # get_provider(): reads Inbox CRM Settings, returns instance or None
├── erpnext.py      # ERPNextProvider  (implemented now)
├── frappe_crm.py   # FrappeCRMProvider (stub/later)
└── external.py     # ExternalProvider — HTTP/webhook (stub/later)
```

### `BaseCRMProvider` contract

```python
class BaseCRMProvider:
    def is_available(self) -> bool: ...
        # backing app installed & provider configured; else features hide

    def get_contact_context(self, contact: str) -> dict | None: ...
        # { customer, customer_since, lead, opportunity, recent_documents:[...] }

    # Phase C
    def allowed_send_doctypes(self) -> list[str]: ...
    def list_documents(self, doctype: str, customer: str | None, q: str = "") -> list[dict]: ...
        # [{ name, date, grand_total, status, currency }]
    def get_document_pdf(self, doctype: str, name: str, print_format: str | None = None) -> bytes: ...

    # Phase B / D (contract only for now, not implemented)
    def create_lead(self, conversation, fields: dict): raise NotImplementedError
    def link_conversation(self, conversation): raise NotImplementedError
```

All methods are optional/guarded. Unknown/unsupported → return `None`/`[]` or raise
a clear error; never crash the inbox.

### `ERPNextProvider` (implementation #1)
- `is_available()` → `"erpnext" in frappe.get_installed_apps()` and provider == ERPNext.
- Resolve **Customer** from the core Contact via Dynamic Links (Contact `links`
  table → `Customer`), falling back to phone match where feasible.
- `get_contact_context` → Customer name + `creation`, last 3 Sales Orders, last 3
  submitted Sales Invoices (already implemented in `api/context.py` — moved here),
  plus open Lead/Opportunity for the customer/contact if present.
- `list_documents(doctype, customer, q)` → `frappe.get_all(doctype, filters={customer, ...}, ...)`
  using dict-syntax filters (v15/v16 safe); only doctypes in `allowed_send_doctypes()`.
- `get_document_pdf` → `frappe.get_print(doctype, name, print_format, as_pdf=True)`.

### Config — new Single DocType `Inbox CRM Settings` (per-site = per-client)
| Field | Type | Notes |
|---|---|---|
| `provider` | Select: `None`/`ERPNext`/`Frappe CRM`/`External` | default `None` |
| `external_base_url` | Data | provider=External |
| `external_api_key` | Password | provider=External |
| `lead_capture` | Select: `Off`/`Manual`/`Auto` | Phase B; default `Off` |
| `sendable_doctypes` | Table MultiSelect → child `Inbox Sendable Document Type` (field: `document_type`, Link→DocType) | e.g. Quotation, Sales Order, Sales Invoice; empty = feature hidden |
| `document_send_roles` | Table MultiSelect → child `Inbox Document Role` (field: `role`, Link→Role) | default seeded with `Inbox Manager` |
| `print_format` | Data | optional override for PDF rendering |

`registry.get_provider()` reads this Single and returns the matching provider
instance, or `None` when `provider == None`.

## 4. Phase A — Context panel (read-only)

- Refactor `api/context.py`: replace the hardcoded `get_erp_context()` with
  `provider = get_provider(); erp = provider.get_contact_context(contact) if provider else None`.
- Response shape for `erp` stays compatible with the existing frontend card; add an
  optional `lead`/`opportunity` block.
- Frontend `ContactPanel`: the existing "DARI ERPNEXT" card renders from the provider
  data; when `erp` is `None` the card is hidden (already the behavior).
- **Test:** site without ERPNext / provider None → `erp` is `None`, endpoint safe.

## 5. Phase C — Send document

### Config gate
- `sendable_doctypes` limits which doctypes appear; empty → feature hidden.
- `document_send_roles` limits who can send; backend enforces (never trust UI).

### UI flow (frontend)
1. Thread toolbar button **📄 Kirim Dokumen** (visible only if provider set,
   `sendable_doctypes` non-empty, and the user holds a `document_send_roles` role).
2. Modal: pick doctype (allowed only) → list documents **auto-filtered to the
   conversation's linked customer** + free-text search → row shows `name`, date,
   `grand_total`, status.
3. Select → confirm → send. Optimistic outgoing **document bubble**.

### Backend `api/document.py`
- `list_sendable_documents(conversation, doctype, q="")`
  - guard: provider set, doctype in `allowed_send_doctypes()`, user in
    `document_send_roles`.
  - resolve customer from the conversation's contact; call
    `provider.list_documents(doctype, customer, q)`.
- `send_document(conversation, doctype, name)`
  - same guards + verify the document belongs to the conversation's customer.
  - `pdf = provider.get_document_pdf(doctype, name)` → save as private File
    attached to the conversation → call the existing channel-outbound path
    (`conversation.send_message` with `media_path` + `message_type="File"`), so it
    flows through `TelegramAdapter.sendDocument` / `WhatsAppAdapter.send_file` and
    appears as an outgoing document message with delivery status + retry.

### Security
- Role + enabled-doctype enforced server-side on **both** endpoints.
- Ownership check: the requested document's `customer` must equal the
  conversation's resolved customer (prevents sending another customer's invoice).
- PDF stored as **private** File.

## 6. Data flow

```
Panel:   ContactPanel → api.context.get_contact_context
                        → registry.get_provider().get_contact_context(contact)

Docs:    Thread "Kirim Dokumen" → api.document.list_sendable_documents
                                 → provider.list_documents(doctype, customer, q)
         pick → api.document.send_document
                → provider.get_document_pdf → File(private)
                → conversation.send_message(media_path, type=File)
                → channel adapter sendDocument/send_file → outgoing bubble
```

## 7. Error handling
- Provider missing/None or backing app absent → features hide; inbox unaffected.
- `list_documents` failure → empty list + soft error toast; never 500 the panel.
- `send_document` failure (PDF render or channel send) → message marked `Failed`
  with retry (reuses existing failed-send flow); error logged, UI not blocked.
- All external/ERP reads wrapped defensively (return None/[] on exception).

## 8. Testing (mocked, per app convention)
- `registry.get_provider`: None when unset; ERPNextProvider when configured.
- `ERPNextProvider.get_contact_context`: safe with no customer linked; returns
  customer + docs when linked (mock ERPNext docs).
- `list_sendable_documents`: rejects disallowed doctype; rejects user without role;
  filters to the conversation's customer.
- `send_document`: rejects cross-customer document; on success creates a private
  File + an outgoing `File` message and dispatches via the (mocked) channel adapter;
  on adapter failure marks the message `Failed`.
- Context endpoint safe on a site without ERPNext (provider None).

## 9. Build order (future specs)
- **Spec #1 (this):** Foundation + Phase A + Phase C (ERPNext provider).
- **Spec #2:** Phase B — lead capture (`create_lead`, Off/Manual/Auto).
- **Spec #3:** Phase D — two-way chat history in CRM; Frappe CRM + External providers.
