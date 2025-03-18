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
			pr_item_doc = frappe.get_doc("Purchase Receipt Item", item.purchase_receipt_item)
			added_item = pr_item_doc
			added_item.received_qty = item.returned_qty - item.redelivered_qty
			added_item.qty = item.returned_qty - item.redelivered_qty
			added_item.rejected_qty = 0
			added_item.amount = (item.returned_qty - item.redelivered_qty) * item.rate
			added_item.base_amount = (item.returned_qty - item.redelivered_qty) * item.base_rate
			added_item.complaint = item.parent
			added_item.complaint_item = item.name or ""
			new_doc.append("items", added_item)
			is_any_item_returned = True

		if not is_any_item_returned:
			frappe.throw(_("No item to be received in this complaint, you need to return at least 1 item"))
		return {"new_doc":new_doc, "new_doc_items": new_doc.items}
	
@frappe.whitelist()
def map_purchase_receipt(source_name, target_doc=None):
	def update_item(obj, target, source_parent):
		target.received_qty = flt(obj.returned_qty) - flt(obj.redelivered_qty)
		target.qty = flt(obj.returned_qty) - flt(obj.redelivered_qty)
		target.rejected_qty = 0
		target.amount = (flt(obj.returned_qty) - flt(obj.redelivered_qty)) * flt(obj.rate)
		target.base_amount = (flt(obj.returned_qty) - flt(obj.redelivered_qty)) * flt(obj.base_rate)

	doc = get_mapped_doc(
		"Complaint",
		source_name, 
		{
			"Complaint": {
				"doctype": "Purchase Receipt",
				"field_map": {
					"supplier": "supplier",
					"purchase_order": "custom_po",
					"name": "complaint",
					"currency": "currency",
					"conversion_rate": "conversion_rate",
				},
			},
			"Purchase Receipt Rejected Item": {
				"doctype": "Purchase Receipt Item",
				"field_map": {
					"name": "complaint_item",
					"parent": "complaint",
					"item_code": "item_code",
					"item_name": "item_name",
					"uom": "uom",
					"stock_uom": "stock_uom",
					"conversion_factor": "conversion_factor",
					"price_list_rate": "price_list_rate",
					"price_list_rate_company": "price_list_rate_company",
					"discount_percentage": "discount_percentage",
					"discount_amount": "discount_amount",
					"purchase_order": "purchase_order",
					"purchase_order_item": "purchase_order_item",
				},
				"postprocess": update_item,
				"condition": lambda item: abs(item.returned_qty - item.redelivered_qty) > 0
			},
		}, 
		target_doc
	)
	return target_doc

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
		pr_item_doc = frappe.get_doc("Purchase Receipt Item", item.purchase_receipt_item)
		added_item = pr_item_doc
		added_item.received_qty = item.returned_qty - item.redelivered_qty
		added_item.qty = item.returned_qty - item.redelivered_qty
		added_item.rejected_qty = 0
		added_item.amount = (item.returned_qty - item.redelivered_qty) * item.rate
		added_item.base_amount = (item.returned_qty - item.redelivered_qty) * item.base_rate
		added_item.complaint = item.parent
		added_item.complaint_item = item.name or ""
		data["items"].append(added_item)
		is_any_item_returned = True

	if not is_any_item_returned:
		frappe.throw(_("No item to be received in this complaint, you need to return at least 1 item"))
	return data

@frappe.whitelist()
def make_complaint(source_name, target_doc=None, args=None):
	def update_item(obj, target, source_parent):
		target.returned_qty = 0
		target.redelivered_qty = 0
		target.rate = obj.rate
		target.base_rate = obj.base_rate

	doc = get_mapped_doc(
		"Purchase Receipt",
		source_name, 
		{
			"Purchase Receipt": {
				"doctype": "Complaint",
				"field_map": {
					"supplier": "supplier",
					"name": "purchase_receipt",
					"custom_po": "purchase_order",
					"currency": "currency",
					"conversion_rate": "conversion_rate",
					"contact_person": "contact_person",
					"contact_email": "contact_email",
				},
			},
			"Purchase Receipt Item": {
				"doctype": "Purchase Receipt Rejected Item",
				"field_map": {
					"qty": "returned_qty",
					"rate": "rate",
					"base_rate": "base_rate",
					"name": "purchase_receipt_item",
					"parent": "purchase_receipt",
				},
				"postprocess": update_item,
			},
		}, 
		target_doc
	)
	return doc