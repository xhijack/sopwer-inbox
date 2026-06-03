# Sopwer Inbox

**Omnichannel Customer Inbox** for the Frappe ecosystem — all customer chats
(pilot: Telegram + WhatsApp) land in one interface, handled by CS agents in
realtime. Concept: **Chatwoot / Intercom** (external contacts, status,
assignment, canned responses) — *not* internal team chat (not Slack/Raven).

Pure Frappe app (`required_apps = ["frappe"]`) — installs on any Frappe site,
**ERPNext optional** (only enriches the contact panel when present).

## Architecture

| Layer | What |
|---|---|
| DocTypes | `Inbox Channel`, `Inbox Conversation`, `Inbox Message`, `Inbox Canned Response`, `Inbox Settings` |
| `channels/` | `BaseChannelAdapter` + `registry`; `telegram.py` (direct Bot API), `whatsapp.py` (delegates to a WhatsApp app) |
| `core/` | `ingest.py` (inbound: dedup, conversation, realtime), `contact_resolver.py` |
| `api/` | `webhooks.py` (Telegram), `conversation.py` (send/status/assign/note/retry), `context.py` (ERP-optional), `channel.py` (health) |
| `frontend/` | React inbox UI mounted at `/inbox` (Phase 6) |

The **core never calls a channel API directly** — only via an adapter. Adding a
channel = adding one adapter module. See `CLAUDE.md` (build spec) for the full
contract.

## Install on a client server

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app sopwer_inbox $REPO_URL --branch main
bench --site <site_name> install-app sopwer_inbox
bench --site <site_name> migrate
bench build --app sopwer_inbox
bench restart
```

This creates roles `Inbox Agent` and `Inbox Manager` and adds a sticky
`inbox_notes` field to `Contact`.

## Configure a channel (admin, one-time)

Channels are configured via the standard Frappe **Inbox Channel** DocType form
(no in-app "add channel" UI by design):

- **Telegram** — set `Telegram Bot Token` (from @BotFather), then register the
  webhook: `bench --site <site_name> execute sopwer_inbox.api.webhooks.register_telegram_webhook --kwargs "{'channel':'<channel_name>','base_url':'https://<public-host>'}"`
- **WhatsApp** — delegated to a WhatsApp app (see `channels/whatsapp.py`).

## Demo data

```bash
bench --site <site_name> execute sopwer_inbox.seed.create_demo_data
bench --site <site_name> execute sopwer_inbox.seed.clear_demo_data
```

## Tests

```bash
bench --site <site_name> run-tests --app sopwer_inbox
```

All business logic (ingest/dedup, adapters, outbound API, context) is covered by
mocked tests — no real channel API is called during tests.

## License

mit
