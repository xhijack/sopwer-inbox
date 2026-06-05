// Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
// For license information, please see license.txt

frappe.ui.form.on("Inbox Channel", {
	refresh(frm) {
		if (frm.is_new()) return;

		const is_meta =
			frm.doc.channel_type === "Facebook Messenger" ||
			frm.doc.channel_type === "Instagram";

		if (is_meta) {
			frm.add_custom_button(
				__("Daftarkan Webhook"),
				() => register_meta_webhook(frm),
				__("Meta"),
			);
		}
	},
});

function register_meta_webhook(frm) {
	frappe.dom.freeze(__("Menghubungi Meta…"));
	frappe.call({
		method: "sopwer_inbox.api.webhooks.register_meta_webhook",
		args: { channel: frm.doc.name },
		callback(r) {
			frappe.dom.unfreeze();
			const m = r.message || {};
			if (m.ok) {
				frappe.msgprint({
					title: __("Berhasil"),
					indicator: "green",
					message: __(
						"Webhook terdaftar & Page ter-subscribe.<br><b>Callback:</b> {0}<br>Kirim DM ke Page untuk menguji.",
						[frappe.utils.escape_html(m.callback_url || "")],
					),
				});
			} else {
				frappe.msgprint({
					title: __("Sebagian/seluruhnya gagal"),
					indicator: "orange",
					message:
						__("Respon Meta:") +
						"<pre style='white-space:pre-wrap'>" +
						frappe.utils.escape_html(JSON.stringify(m, null, 2)) +
						"</pre>",
				});
			}
		},
		error() {
			frappe.dom.unfreeze();
		},
	});
}
