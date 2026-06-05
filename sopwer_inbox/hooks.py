app_name = "sopwer_inbox"
app_title = "Sopwer Inbox"
app_publisher = "PT Sopwer Teknologi Indonesia"
app_description = "Omnichannel Customer Inbox (Chatwoot-style) on Frappe"
app_email = "sopwer.id@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["frappe"]

# Website
# ------------------
# Resolve /inbox and any sub-path to the SPA www page (client-side routing).
website_route_rules = [
	{"from_route": "/inbox/<path:app_path>", "to_route": "inbox"},
]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "sopwer_inbox",
# 		"logo": "/assets/sopwer_inbox/logo.png",
# 		"title": "Sopwer Inbox",
# 		"route": "/sopwer_inbox",
# 		"has_permission": "sopwer_inbox.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/sopwer_inbox/css/sopwer_inbox.css"
# app_include_js = "/assets/sopwer_inbox/js/sopwer_inbox.js"

# include js, css files in header of web template
# web_include_css = "/assets/sopwer_inbox/css/sopwer_inbox.css"
# web_include_js = "/assets/sopwer_inbox/js/sopwer_inbox.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "sopwer_inbox/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "sopwer_inbox/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "sopwer_inbox.utils.jinja_methods",
# 	"filters": "sopwer_inbox.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "sopwer_inbox.install.before_install"
# after_install = "sopwer_inbox.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "sopwer_inbox.uninstall.before_uninstall"
# after_uninstall = "sopwer_inbox.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "sopwer_inbox.utils.before_app_install"
# after_app_install = "sopwer_inbox.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "sopwer_inbox.utils.before_app_uninstall"
# after_app_uninstall = "sopwer_inbox.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "sopwer_inbox.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"sopwer_inbox.tasks.all"
# 	],
# 	"daily": [
# 		"sopwer_inbox.tasks.daily"
# 	],
# 	"hourly": [
# 		"sopwer_inbox.tasks.hourly"
# 	],
# 	"weekly": [
# 		"sopwer_inbox.tasks.weekly"
# 	],
# 	"monthly": [
# 		"sopwer_inbox.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "sopwer_inbox.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "sopwer_inbox.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "sopwer_inbox.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["sopwer_inbox.utils.before_request"]
# after_request = ["sopwer_inbox.utils.after_request"]

# Job Events
# ----------
# before_job = ["sopwer_inbox.utils.before_job"]
# after_job = ["sopwer_inbox.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"sopwer_inbox.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []



# Fixtures
# --------
fixtures = [
	{"dt": "Role", "filters": [["name", "in", ["Inbox Agent", "Inbox Manager"]]]},
	{"dt": "Custom Field", "filters": [["name", "in", ["Contact-inbox_notes"]]]},
]
