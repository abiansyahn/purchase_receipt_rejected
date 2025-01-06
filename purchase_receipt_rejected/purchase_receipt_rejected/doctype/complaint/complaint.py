# Copyright (c) 2024, abiansyahn and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt
frappe.utils.logger.set_log_level("DEBUG")


class Complaint(Document):
	def on_update(self):
		pass

	@frappe.whitelist()
	def create_purchase_receipt(doc):
		frappe.flags.ignore_account_permission = True
		new_doc = frappe.new_doc("Purchase Receipt")
		new_doc.update({
			"naming_series": "MAT-PRE-.YYYY.-",
			"supplier": doc.supplier or "",
			"custom_po": doc.purchase_order or "",
			"complaint": doc.name or "",
			"currency": doc.currency or "",
			"conversion_rate": doc.conversion_rate or "",
		})
		for item in doc.items:
			new_doc.append("items", {
				"item_code": item.item_code,
				"item_name": item.item_name,
				"received_qty": item.returned_qty - item.redelivered_qty,
				"qty": item.returned_qty - item.redelivered_qty,
				"uom": item.uom,
				"stock_uom": item.stock_uom,
				"conversion_factor": item.conversion_factor,
				"rate": item.rate,
				"amount": (item.returned_qty - item.redelivered_qty) * item.rate,
				"purchase_order": item.purchase_order or "", 
				"purchase_order_item": item.purchase_order_item or "",
				"complaint": item.parent,
				"complaint_item": item.name or "",
			})

		return new_doc

