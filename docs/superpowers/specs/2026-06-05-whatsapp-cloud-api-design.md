# WhatsApp Cloud API Channel — Design

**Date:** 2026-06-05
**Status:** Approved (build authorized in one iteration)

## Goal

Add an official **WhatsApp Cloud API** channel (Meta WhatsApp Business Platform),
distinct from the existing unofficial **Wuzapi** WhatsApp channel and from the
Messenger/Instagram Meta channels. Two-way text + media, reusing the Meta App,
single webhook endpoint, and X-Hub-Signature-256 verification already in place.

## Why a new adapter (not reusing Messenger/IG)

WhatsApp Cloud differs at almost every layer:
- Webhook `object` = `whatsapp_business_account`.
- Payload = `entry[].changes[].value.messages[]` (NOT `entry[].messaging[]`).
- Routing key = `value.metadata.phone_number_id` (a WABA may have many numbers).
- Send = `POST /{phone-number-id}/messages` with
  `{messaging_product:"whatsapp", to, type, ...}` (Bearer token).
- Inbound media = a media **id** → `GET /{media-id}` returns a URL → fetch that
  URL with the token → bytes (reuse the `media_bytes` ingest path from WhatsApp/Wuzapi).

## Inbox Channel — new fields

- `channel_type` Select: add **"WhatsApp Cloud"**.
- `meta_phone_number_id` (Data) — the Cloud API Phone Number ID (send target +
  inbound routing key).
- `meta_waba_id` (Data) — WhatsApp Business Account ID (used for the
  `/{waba-id}/subscribed_apps` registration).
- Reuse existing Meta fields: `meta_app_id`, `meta_app_secret`, `meta_verify_token`,
  `meta_api_version`, and `meta_page_access_token` (holds the WhatsApp token —
  System User / long-lived token with `whatsapp_business_messaging`).

## Adapter — `channels/whatsapp_cloud.py`

`WhatsAppCloudAdapter(BaseChannelAdapter)`:
- `parse_inbound(value: dict) -> list[dict]`: `value` is one `change.value`. Iterate
  `value["messages"]`; for each: `from` = customer wa_id (= external_conversation_id +
  sender_external_id + sender_phone), `id` = wamid (external_message_id), `timestamp`
  (unix seconds → site tz). Type mapping: `text`→Text (text.body), `image/video/
  audio/document/sticker`→Image/Video/Audio/File (caption→content). Sender name from
  `value["contacts"][0].profile.name` (match by wa_id). For media: fetch bytes via the
  Graph media endpoint and set `media_bytes`/`media_filename`/`media_mimetype`
  (best-effort; failure logged, message still ingested). Skip statuses (`value` may
  carry `statuses` instead of `messages` — delivery/read receipts → return []).
- `send_message(conversation_doc, *, text=None, media_path=None)`:
  - text → `POST /{phone_number_id}/messages` body
    `{messaging_product:"whatsapp", recipient_type:"individual", to, type:"text",
    text:{body}}`, header `Authorization: Bearer {token}`.
  - media → upload local file via `POST /{phone_number_id}/media`
    (multipart: `messaging_product=whatsapp`, file, type=mime) → media id; then send
    `{type:<kind>, <kind>:{id: media_id, caption?}}`. kind from mime
    (image/video/audio/document). Reuse `_resolve_local_file`.
  - return `{external_message_id: resp.messages[0].id, delivery_status:"Sent"}`.
- `_fetch_media_bytes(media_id)`: `GET /{media-id}` → `url`; then `GET url` with Bearer
  token → bytes. Best-effort.

## Webhook (`api/webhooks.py::meta`) — add a WhatsApp branch

In the entry loop, branch on `object_type`:
- `whatsapp_business_account`: for each `change` in `entry["changes"]` where
  `field=="messages"`: `value = change["value"]`;
  `phone_id = value["metadata"]["phone_number_id"]`; match channel by
  `meta_phone_number_id == phone_id` + `channel_type=="WhatsApp Cloud"`; verify
  signature with that channel's `meta_app_secret`; then
  `for norm in adapter.parse_inbound(value): ingest_inbound(norm, channel)` (per-change
  try/except → log + Error Log).
- `page`/`instagram`: unchanged.

Add `whatsapp_business_account` → `"WhatsApp Cloud"` to the object map and a
`_match_wa_channel(phone_number_id)` helper.

## One-click "Daftarkan Webhook" — extend `register_meta_webhook`

For `channel_type == "WhatsApp Cloud"`:
- `obj = "whatsapp_business_account"`, `fields = "messages"`.
- App subscription: `POST /{app_id}/subscriptions` (object=whatsapp_business_account,
  callback, verify_token, fields) — same as others.
- Subscribe the WABA: `POST /{meta_waba_id}/subscribed_apps` with the token
  (Bearer/access_token). (For Messenger/IG it's `/{page_id}/subscribed_apps`.)
- Keep the HTTPS-forcing of callback_url.

## Frontend

`ChannelGlyph`: map `"WhatsApp Cloud"` → existing `"wa"` glyph (WhatsApp logo). No
other UI changes (channel-agnostic).

## Error handling
- Invalid signature / no app_secret → skip (secure default), as today.
- Outbound failure → `_dispatch` marks Failed + Error Log (existing).
- 24-hour session window: send session messages; outside the window Meta rejects →
  Failed. Template messages are OUT OF SCOPE for the MVP.
- Inbound media fetch failure → logged, message still ingested (text/caption).

## Testing (Frappe-only, network mocked)
- `parse_inbound`: text value fixture → Text+content+from/wamid; image value → Image +
  media fetch (mock) sets media_bytes; statuses-only value → []. 
- Routing: `_match_wa_channel(phone_id)` resolves the right channel; unknown → None.
- `send_message`: text payload shape (messaging_product:whatsapp, to, text.body);
  media path → upload then send referencing media id (mock requests).
- `register_meta_webhook`: WhatsApp Cloud → object whatsapp_business_account +
  `/{waba_id}/subscribed_apps`.
- Signature reuse (existing helper).

**Live QA needed** (cannot unit-test): real webhook payload shape, media download
2-step, 24h window, token scopes (`whatsapp_business_messaging`,
`whatsapp_business_management`), and that the number is registered on Cloud API.

## Files
- New: `channels/whatsapp_cloud.py`, `channels/tests/test_whatsapp_cloud.py`,
  `channels/tests/fixtures/wacloud_inbound_*.json`.
- Modified: `channels/registry.py`, `api/webhooks.py`,
  `doctype/inbox_channel/inbox_channel.json`, `frontend/src/lib/format.ts` +
  `components/icons.tsx` (glyph map).
