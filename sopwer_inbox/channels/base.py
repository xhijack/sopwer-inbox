# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Channel adapter contract.

The core never talks to a channel API directly — only through an adapter.
Adding a new channel = adding one adapter module, without touching the core
(CLAUDE.md §5).
"""


class BaseChannelAdapter:
	def __init__(self, channel_doc):
		self.channel = channel_doc  # Inbox Channel doc

	def parse_inbound(self, payload: dict) -> list[dict]:
		"""Turn a raw webhook payload into a list of NORMALIZED message dicts.

		One webhook may carry >1 message. Return [] when the payload is not a
		message (status update, typing indicator, etc.).

		Normalized schema (CLAUDE.md §5):
		    {
		      "channel_type": "Telegram" | "WhatsApp",
		      "external_conversation_id": str,
		      "external_message_id": str,
		      "sender_external_id": str,
		      "sender_name": str | None,
		      "sender_phone": str | None,
		      "message_type": "Text"|"Image"|"File"|"Audio"|"Video"|"Location",
		      "content": str | None,
		      "media_url": str | None,       # GET-able URL (Telegram); None for WA
		      "timestamp": datetime,
		      "raw": dict,

		      # Optional — set by WhatsApp adapter when media bytes were downloaded
		      # via Wuzapi (encrypted media has no plain GET URL).
		      "media_bytes":    bytes | None,   # decoded media content
		      "media_filename": str | None,     # suggested file name
		      "media_mimetype": str | None,     # MIME type from the webhook
		    }
		"""
		raise NotImplementedError

	def send_message(self, conversation_doc, *, text=None, media_path=None) -> dict:
		"""Send an outgoing message to the channel.

		Return at minimum::

		    {"external_message_id": str, "delivery_status": "Sent"}
		"""
		raise NotImplementedError
