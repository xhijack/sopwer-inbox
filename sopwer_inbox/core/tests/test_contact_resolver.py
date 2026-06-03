# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

from sopwer_inbox.core import contact_resolver
from sopwer_inbox.tests.base import InboxTestCase


class TestContactResolver(InboxTestCase):
	def test_create_new_contact_with_phone(self):
		contact = contact_resolver.resolve_or_create_contact(
			"WhatsApp", external_id="628111", name="Budi", phone="+628111000111"
		)
		self.assertEqual(contact.first_name, "Budi")
		self.assertTrue(any(p.phone == "+628111000111" for p in contact.phone_nos))

	def test_resolve_existing_by_phone(self):
		first = contact_resolver.resolve_or_create_contact(
			"WhatsApp", external_id="628222", name="Siti", phone="+628222000222"
		)
		again = contact_resolver.resolve_or_create_contact(
			"WhatsApp", external_id="628222", name="Siti Lain", phone="+628222000222"
		)
		self.assertEqual(first.name, again.name)

	def test_telegram_creates_contact_by_name(self):
		contact = contact_resolver.resolve_or_create_contact(
			"Telegram", external_id="tg-555", name="Rizki", phone=None
		)
		self.assertEqual(contact.first_name, "Rizki")
