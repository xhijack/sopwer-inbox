# Meta Channels (Facebook Messenger + Instagram DM) — Design

**Date:** 2026-06-05
**Status:** Approved (design); pending implementation plan
**Author:** ramdani + Claude

## Goal

Add two new omnichannel inbox channels backed by Meta's Graph API / Messenger
Platform: **Facebook Messenger** (Page messages) and **Instagram Direct**. Full
two-way messaging with media, consistent with the existing Telegram / WhatsApp
channels. MVP uses manual credential paste (no OAuth onboarding).

## Decisions (locked during brainstorming)

1. **Scope:** Messenger **and** Instagram together, as one shared adapter family
   (they share ~90%: Graph API send endpoint, webhook infra, Page token,
   PSID/IGSID identity, inbound media as URLs).
2. **Auth:** Manual token paste per Inbox Channel (Page Access Token, App Secret,
   verify token) — same pattern as Telegram bot token / Wuzapi. No Facebook Login
   OAuth flow, no embedded signup. Suits self-owned Pages/IG accounts.
3. **Depth:** Full two-way + media — receive & reply text, inbound media (download
   from Meta CDN URL), and outbound media (via attachment upload).

## Architecture

**Approach A — shared base + thin subclasses** (chosen over a single
`platform`-flagged class or two copy-pasted adapters).

- `channels/meta_base.py` — `MetaBaseAdapter(BaseChannelAdapter)` with all shared
  logic: `parse_inbound`, `send_message`, `_fetch_profile`, `_upload_attachment`,
  `_graph_url`, `_account_token`.
- `channels/meta.py` — `MessengerAdapter` and `InstagramAdapter`, each setting two
  class attributes:
  - `PLATFORM` = `"messenger"` | `"instagram"`
  - `WEBHOOK_OBJECT` = `"page"` | `"instagram"`
  - (subclasses may override `_resolve_sender_name` if profile fields differ)
- `channels/registry.py` — add to `_adapter_map()`:
  `"Facebook Messenger": MessengerAdapter`, `"Instagram": InstagramAdapter`.

### Single Meta webhook endpoint

Meta sends all events for one Meta App to **one** webhook URL, covering every
Page / IG account subscribed under that app. New endpoint
`api/webhooks.py::meta`:

- **GET** (subscription verification): read `hub.mode`, `hub.verify_token`,
  `hub.challenge` from query args. If a configured Inbox Channel's
  `meta_verify_token` matches, return the raw `hub.challenge` (plain text, 200).
  Otherwise 403.
- **POST** (events):
  1. Read the raw request body (bytes) before JSON parsing.
  2. Verify `X-Hub-Signature-256` = `sha256=` + HMAC-SHA256(app_secret, raw_body).
     The app_secret comes from the channel matched to this delivery (see routing).
     Invalid signature → 403. Missing/empty app_secret on the matched channel →
     log a warning and reject (secure default).
  3. Parse `object` (`"page"` | `"instagram"`) and iterate `entry[].messaging[]`.
  4. For each entry, route by `entry.id` (Page ID for Messenger, IG user id for
     Instagram) + the platform implied by `object` to the matching Inbox Channel
     (`meta_page_id` == entry.id and channel_type maps to that platform).
  5. Call `adapter.parse_inbound(event)` then `ingest_inbound(normalized, channel)`
     — reusing the existing ingest pipeline.

Because signature verification needs the channel's app_secret, the endpoint first
resolves the channel from `entry.id`, then verifies. If multiple entries map to
different channels (rare), verify per matched channel; events whose channel cannot
be resolved are skipped + logged (never crash the batch).

## Inbox Channel — new fields

Add a "Meta" section to the `Inbox Channel` DocType:

- `channel_type` Select — add options **"Facebook Messenger"** and **"Instagram"**
  (existing: Telegram, WhatsApp).
- `meta_page_id` (Data) — Page ID (Messenger) or IG user id (Instagram). Used to
  route inbound deliveries and as the `{page_id}` in outbound Graph calls.
- `meta_page_access_token` (Password) — long-lived Page Access Token.
- `meta_app_secret` (Password) — for `X-Hub-Signature-256` verification.
- `meta_verify_token` (Data) — shared secret for GET subscription verification.
- `meta_api_version` (Data, default `v21.0`).

All fields optional at the DocType level; the adapter throws a clear error if a
required field is missing when actually used (mirrors the WhatsApp adapter's
`_account` guard).

## Data flow

- **Identity:** sender is a PSID (Messenger) / IGSID (Instagram), not a phone.
  - `external_conversation_id` = sender PSID/IGSID (1:1 conversation).
  - `sender_external_id` = same id; `sender_phone` = None.
  - `sender_name` = best-effort via `GET /{psid}?fields=name&access_token=...`
    (Messenger) or the username present in the IG webhook when available; fallback
    to the id. Profile-fetch failure is logged and non-fatal.
- **Inbound media:** `message.attachments[].payload.url` is a directly
  GET-able Meta CDN URL → set `normalized["media_url"]`; the existing
  `core/ingest.py` `_download_media` path saves it to a private File. No new
  `media_bytes` path needed (unlike WhatsApp's encrypted media). `message_type`
  derived from attachment `type` (`image`→Image, `video`→Video, `audio`→Audio,
  `file`→File). Text/caption → `content`.
- **Outbound text:** `POST /v{ver}/{page_id}/messages?access_token=...` with
  `{recipient:{id: PSID}, messaging_type:"RESPONSE", message:{text}}`.
- **Outbound media:** our File is private, so:
  1. Upload bytes via `POST /v{ver}/{page_id}/message_attachments` (multipart, with
     `message={attachment:{type, payload:{is_reusable:true}}}` + the file) →
     receive `attachment_id`.
  2. Send `message:{attachment:{type, payload:{attachment_id}}}`.
  Attachment `type` from the file's mimetype (image/video/audio/file). The adapter
  resolves the file_url to a local path (reuse the `_resolve_local_file` helper
  pattern from the WhatsApp adapter) before upload.

## Error handling

- Invalid `X-Hub-Signature-256` → 403; the batch is not processed.
- Empty `meta_app_secret` on the matched channel → log warning + reject (secure
  default). Can be relaxed for local dev if needed.
- **24-hour messaging window:** outbound uses `messaging_type: "RESPONSE"`. Outside
  the 24h window Meta rejects the send; `api/conversation.py::_dispatch` already
  catches adapter exceptions and marks the message `Failed` (retry available).
  Message tags / human-agent tag are out of scope for the MVP.
- Profile-fetch and inbound media-download failures are best-effort: logged, and
  the message is still ingested (id as name / text-only).
- Unresolvable channel for an incoming `entry.id` → skip that entry + log; never
  crash the rest of the batch.

## Frontend

- `components/icons.tsx::ChannelGlyph` — extend `ch` union to
  `"wa" | "tg" | "ig" | "fb"`; add Instagram and Messenger glyphs with brand-ish
  colors.
- Wherever channel_type → glyph mapping happens, map "Facebook Messenger"→`fb`,
  "Instagram"→`ig`. No other UI flow changes (conversation list, thread, composer
  all already channel-agnostic).

## Testing (Frappe-only site; Meta mocked)

- **Signature:** `_verify_meta_signature(raw, header, app_secret)` — valid passes,
  tampered/empty fails.
- **GET challenge:** correct verify_token returns the challenge; wrong token 403.
- **parse_inbound:** Messenger and Instagram sample payload fixtures →
  message_type, content, sender ids, media_url for an attachment event.
- **Routing:** `entry.id` resolves to the correct Inbox Channel by
  `meta_page_id` + platform; unknown id → skipped.
- **Outbound:** text payload shape; media path triggers attachment upload then a
  send referencing the returned `attachment_id` (mock `requests`).
- **Attachment type mapping:** mimetype → image/video/audio/file.

**Must be verified against a live Meta App** (cannot be unit-tested): real webhook
payload shapes for Messenger vs Instagram, exact attachment `payload.url` behavior,
24h-window rejection, and Page-token permission scopes (`pages_messaging`,
`instagram_manage_messages`, `pages_manage_metadata`).

## Out of scope (MVP)

- Facebook Login / OAuth onboarding & token refresh.
- Instagram comments / story mentions / @mentions (DM only).
- Messenger handover protocol, persistent menu, ice breakers.
- Message tags for sending outside the 24h window.

## Files (anticipated)

- New: `channels/meta_base.py`, `channels/meta.py`,
  `channels/tests/test_meta.py`, `channels/tests/fixtures/meta_inbound_*.json`.
- Modified: `channels/registry.py`, `api/webhooks.py`,
  `doctype/inbox_channel/inbox_channel.json`, `frontend/src/components/icons.tsx`
  (+ glyph mapping site).
