# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Thin subclasses for Meta channel adapters.

MessengerAdapter — Facebook Messenger (webhook object: "page")
InstagramAdapter — Instagram DM    (webhook object: "instagram")

All logic lives in MetaBaseAdapter; these classes exist only to pin the two
class attributes that distinguish the two platforms.
"""

from sopwer_inbox.channels.meta_base import MetaBaseAdapter


class MessengerAdapter(MetaBaseAdapter):
    PLATFORM = "messenger"
    WEBHOOK_OBJECT = "page"


class InstagramAdapter(MetaBaseAdapter):
    PLATFORM = "instagram"
    WEBHOOK_OBJECT = "instagram"
