# Copyright (c) 2024, abiansyahn and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import get_link_to_form, flt
frappe.utils.logger.set_log_level("DEBUG")


class Complaint(Document):
	def on_update(self):
		pass

	def validate(self):
		self.validate_only_complaint_doc()

	def validate_only_complaint_doc(self):
		complaint_exists = frappe.db.exists("Complaint", {"purchase_receipt": self.purchase_receipt, "docstatus": ["!=", 2]})
		if complaint_exists and complaint_exists != self.name:
			frappe.throw(_("Purchase Receipt {0} already have Complaint document {1}").format(self.purchase_receipt, get_link_to_form("Complaint", complaint_exists)))

	@frappe.whitelist()
	def create_purchase_receipt(self):
		frappe.flags.ignore_account_permission = True
		new_doc = frappe.new_doc("Purchase Receipt")
		is_any_item_returned = False
		new_doc.update({
			"naming_series": "WE.YY.####",
			"supplier": self.supplier or "",
			"custom_po": self.purchase_order or "",
			"complaint": self.name or "",
			"currency": self.currency or "",
			"conversion_rate": self.conversion_rate or "",
		})
		for item in self.items:
			if (item.returned_qty - item.redelivered_qty) <= 0:
				continue
			new_doc.append("items", {
				"item_code": item.item_code,
				"item_name": item.item_name,
				"received_qty": item.returned_qty - item.redelivered_qty,
				"qty": item.returned_qty - item.redelivered_qty,
				"uom": item.uom,
				"stock_uom": item.stock_uom,
				"conversion_factor": item.conversion_factor,
				"price_list_rate": item.rate,
				"rate": item.rate,
				"amount": (item.returned_qty - item.redelivered_qty) * item.rate,
				"base_rate": item.base_rate,
				"base_amount": (item.returned_qty - item.redelivered_qty) * item.base_rate,
				"purchase_order": item.purchase_order or "", 
				"purchase_order_item": item.purchase_order_item or "",
				"complaint": item.parent,
				"complaint_item": item.name or "",
			})
			is_any_item_returned = True

		if not is_any_item_returned:
			frappe.throw(_("No item to be received in this complaint, you need to return at least 1 item"))
		return new_doc
	
@frappe.whitelist()
def make_purchase_receipt(complaint_name):
	frappe.flags.ignore_account_permission = True
	complaint_doc = frappe.get_doc("Complaint", complaint_name)
	data = {}
	data.update({
		"naming_series": "WE.YY.####",
		"supplier": complaint_doc.supplier or "",
		"custom_po": complaint_doc.purchase_order or "",
		"complaint": complaint_doc.name or "",
		"currency": complaint_doc.currency or "",
		"conversion_rate": complaint_doc.conversion_rate or "",
		"items": []
	})
	for item in complaint_doc.items:
		if (item.returned_qty - item.redelivered_qty) <= 0:
			continue
		data["items"].append({
			"item_code": item.item_code,
			"item_name": item.item_name,
			"received_qty": item.returned_qty - item.redelivered_qty,
			"qty": item.returned_qty - item.redelivered_qty,
			"uom": item.uom,
			"stock_uom": item.stock_uom,
			"conversion_factor": item.conversion_factor,
			"price_list_rate": item.rate,
			"rate": item.rate,
			"amount": (item.returned_qty - item.redelivered_qty) * item.rate,
			"base_rate": item.base_rate,
			"base_amount": (item.returned_qty - item.redelivered_qty) * item.base_rate,
			"purchase_order": item.purchase_order or "", 
			"purchase_order_item": item.purchase_order_item or "",
			"complaint": item.parent,
			"complaint_item": item.name or "",
		})
		is_any_item_returned = True

	if not is_any_item_returned:
		frappe.throw(_("No item to be received in this complaint, you need to return at least 1 item"))
	return data