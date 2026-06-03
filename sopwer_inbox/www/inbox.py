import json
import os

import frappe


no_cache = 1


def get_context(context):
	"""Serve the Sopwer Inbox React SPA.

	Injects the Vite-built asset URLs (from the build manifest) plus the CSRF
	token and socketio port so the SPA can talk to the backend.
	"""
	if frappe.session.user == "Guest":
		frappe.throw("Login diperlukan untuk mengakses Inbox.", frappe.PermissionError)

	context.csrf_token = frappe.sessions.get_csrf_token()
	context.socketio_port = frappe.conf.socketio_port or 9000
	# Pre-serialize with Frappe's datetime-aware encoder; Jinja's tojson (plain
	# json.dumps) chokes on the datetime objects inside boot.
	context.boot = frappe.as_json(frappe.sessions.get())
	context.entry = _read_manifest_entry()
	context.no_cache = 1
	return context


def _read_manifest_entry():
	"""Read built assets from the Vite manifest.

	Returns a dict with the JS entry and any CSS files, or None if the SPA
	hasn't been built yet (build with `cd frontend && npm run build`).
	"""
	app_path = frappe.get_app_path("sopwer_inbox")
	manifest_paths = [
		os.path.join(app_path, "public", "frontend", ".vite", "manifest.json"),
		os.path.join(app_path, "public", "frontend", "manifest.json"),
	]
	manifest_path = next((p for p in manifest_paths if os.path.exists(p)), None)
	if not manifest_path:
		return None

	with open(manifest_path) as f:
		manifest = json.load(f)

	entry = manifest.get("index.html") or next(
		(v for v in manifest.values() if v.get("isEntry")), None
	)
	if not entry:
		return None

	base = "/assets/sopwer_inbox/frontend/"
	return {
		"js": base + entry["file"],
		"css": [base + c for c in entry.get("css", [])],
	}
