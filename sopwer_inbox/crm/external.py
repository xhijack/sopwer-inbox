# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt
from sopwer_inbox.crm.base import BaseCRMProvider


class ExternalProvider(BaseCRMProvider):  # implemented in a later spec
	def is_available(self) -> bool:
		return False
