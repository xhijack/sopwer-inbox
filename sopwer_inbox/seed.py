# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
"""Demo/seed data for client demos and frontend QA.

Run:  bench --site <site> execute sopwer_inbox.seed.create_demo_data
Wipe: bench --site <site> execute sopwer_inbox.seed.clear_demo_data

Idempotent: safe to run repeatedly. Mirrors the channels in the approved design
(WA CS / WA Toko / WA Reseller / Telegram CS / Telegram Promo).
"""

import frappe
from frappe.utils import add_to_date, now_datetime

CHANNELS = [
	{"channel_name": "WA CS", "channel_type": "WhatsApp"},
	{"channel_name": "WA Toko", "channel_type": "WhatsApp"},
	{"channel_name": "WA Reseller", "channel_type": "WhatsApp"},
	{"channel_name": "Telegram CS", "channel_type": "Telegram"},
	{"channel_name": "Telegram Promo", "channel_type": "Telegram"},
]

CANNED = [
	{"title": "Salam pembuka", "shortcut": "/salam", "message": "Halo, terima kasih sudah menghubungi Sopwer. Ada yang bisa kami bantu?"},
	{"title": "Cek pesanan", "shortcut": "/cek", "message": "Baik, boleh saya minta nomor pesanannya untuk saya cek statusnya?"},
	{"title": "Tutup percakapan", "shortcut": "/terimakasih", "message": "Terima kasih sudah menghubungi kami. Senang bisa membantu, semoga harinya menyenangkan!"},
	{"title": "Minta nomor", "shortcut": "/nomor", "message": "Boleh saya minta nomor HP yang terdaftar pada pesanan Anda?"},
]


def _ensure(doctype, key_filters, values):
	name = frappe.db.get_value(doctype, key_filters)
	if name:
		return frappe.get_doc(doctype, name)
	doc = frappe.get_doc({"doctype": doctype, **values})
	doc.insert(ignore_permissions=True)
	return doc


def create_demo_data():
	channels = {}
	for c in CHANNELS:
		channels[c["channel_name"]] = _ensure(
			"Inbox Channel", {"channel_name": c["channel_name"]}, {"enabled": 1, **c}
		)

	for c in CANNED:
		_ensure("Inbox Canned Response", {"title": c["title"]}, c)

	# Conversation 1: Budi @ WA CS, with an internal note + delivered replies.
	budi = _ensure("Contact", {"first_name": "Budi Santoso"}, {"first_name": "Budi Santoso"})
	_set_phone(budi, "+62 812-3344-5566")
	budi.db_set("inbox_notes", "Pelanggan langganan, sering order kain cotton. Lebih suka dihubungi sore hari.")
	conv1 = _conversation(channels["WA CS"], "6281233445566", budi, "Pengiriman", status="Open")
	_msg(conv1, "Incoming", "Halo min, saya mau tanya pesanan saya kok belum sampai ya?", ext="d1")
	_msg(conv1, "Incoming", 'Order SO-2026-1184, sudah 3 hari statusnya masih "dikirim"', ext="d2")
	_msg(conv1, "Outgoing", "Halo Pak Budi, terima kasih sudah menghubungi Sopwer. Mohon ditunggu sebentar ya, saya cek dulu status pengirimannya.", ext="d3", status="Read", sender="Agent")
	_msg(conv1, "Outgoing", "Cek ke gudang: paket Pak Budi tertahan di transit Bandung karena salah sortir. Sudah saya minta dipercepat.", internal=1, sender="Agent")
	_msg(conv1, "Outgoing", "Pesanan Bapak sudah dalam perjalanan dan saat ini berada di gudang transit Bandung. Estimasi tiba besok sore.", ext="d4", status="Read", sender="Agent")

	# Conversation 2: Maya @ WA CS, failed outgoing (retry demo), no ERP orders.
	maya = _ensure("Contact", {"first_name": "Maya Putri"}, {"first_name": "Maya Putri"})
	_set_phone(maya, "+62 856-7788-9900")
	conv2 = _conversation(channels["WA CS"], "6285677889900", maya, "Komplain", status="Open")
	_msg(conv2, "Incoming", "Min barang yang saya terima rusak", ext="m1")
	_msg(conv2, "Outgoing", "Mohon maaf atas ketidaknyamanannya Bu Maya, boleh kirim foto barangnya?", status="Failed", sender="Agent")

	# Conversation 3: Telegram Promo, resolved.
	rizki = _ensure("Contact", {"first_name": "Rizki Pratama"}, {"first_name": "Rizki Pratama"})
	conv3 = _conversation(channels["Telegram Promo"], "tg-99001", rizki, "Promo", status="Resolved")
	_msg(conv3, "Incoming", "Promo cotton combed masih ada?", ext="t1")
	_msg(conv3, "Outgoing", "Terima kasih Pak Rizki, promo masih berlaku sampai akhir bulan.", ext="t2", status="Read", sender="Agent")

	frappe.db.commit()
	return {"channels": len(channels), "conversations": 3}


def _set_phone(contact, phone):
	if not any(p.phone == phone for p in contact.get("phone_nos", [])):
		contact.append("phone_nos", {"phone": phone, "is_primary_phone": 1})
		contact.save(ignore_permissions=True)


def _conversation(channel, external_id, contact, tags, status="Open"):
	existing = frappe.db.get_value(
		"Inbox Conversation",
		{"channel": channel.name, "external_conversation_id": external_id},
	)
	if existing:
		return frappe.get_doc("Inbox Conversation", existing)
	doc = frappe.get_doc(
		{
			"doctype": "Inbox Conversation",
			"channel": channel.name,
			"external_conversation_id": external_id,
			"contact": contact.name,
			"subject": contact.first_name,
			"status": status,
			"tags": tags,
			"last_message_at": now_datetime(),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _msg(conv, direction, content, ext=None, status="Delivered", sender="Contact", internal=0):
	if ext and frappe.db.exists("Inbox Message", {"conversation": conv.name, "external_message_id": ext}):
		return
	frappe.get_doc(
		{
			"doctype": "Inbox Message",
			"conversation": conv.name,
			"direction": direction,
			"sender_type": sender,
			"is_internal": internal,
			"message_type": "Text",
			"content": content,
			"external_message_id": ext,
			"delivery_status": status,
			"message_timestamp": now_datetime(),
		}
	).insert(ignore_permissions=True)
	if not internal:
		frappe.db.set_value(
			"Inbox Conversation",
			conv.name,
			{"last_message_preview": (content or "")[:140], "last_message_at": now_datetime()},
			update_modified=False,
		)


DEMO_CONTACTS = ["Budi Santoso", "Maya Putri", "Rizki Pratama"]


def clear_demo_data(wipe_channels=True, wipe_canned=True, wipe_contacts=True):
	"""Empty the inbox for a clean production start.

	Deletes conversations + messages always; channels, canned responses, and the
	seeded demo contacts by default. Pass flags as 0 to keep any of them."""
	for dt in ("Inbox Message", "Inbox Conversation"):
		for name in frappe.get_all(dt, pluck="name"):
			frappe.delete_doc(dt, name, force=1, ignore_permissions=True)

	if int(wipe_canned):
		for name in frappe.get_all("Inbox Canned Response", pluck="name"):
			frappe.delete_doc("Inbox Canned Response", name, force=1, ignore_permissions=True)

	if int(wipe_channels):
		for name in frappe.get_all("Inbox Channel", pluck="name"):
			frappe.delete_doc("Inbox Channel", name, force=1, ignore_permissions=True)

	if int(wipe_contacts):
		for cname in DEMO_CONTACTS:
			if frappe.db.exists("Contact", cname):
				frappe.delete_doc("Contact", cname, force=1, ignore_permissions=True)

	frappe.db.commit()
	return "cleared"
