// Copyright (c) 2024, abiansyahn and contributors
// For license information, please see license.txt

frappe.ui.form.on("Complaint", {
	refresh(frm) {
        if (frm.doc.docstatus == 1 && flt(frm.doc.returned_percent, 2) < 100) {
            frm.add_custom_button(
                __("Purchase Return"),
                () => {
                    frm.events.make_purchase_return(frm);
                },
                __("Create"));
        }
        if (frm.doc.docstatus == 1 && flt(frm.doc.redelivered_percent, 2) < 100) {
            frm.add_custom_button(
                __("Purchase Receipt"),
                () => {
                    frm.events.make_purchase_receipt(frm);
                },
                __("Create"));
        }
	},
    supplier: function(frm) {
        frm.set_query("purchase_receipt", function (doc) {
            return {
                filters: {
                    supplier: doc.supplier,
                    docstatus: 1
                }
            }
        });
    },
    purchase_receipt: function(frm) {
        frm.events.get_purchase_receipt_data(frm);
    },
    make_purchase_receipt: function (frm) {
		frappe.call({
            doc: frm.doc,
            method: "create_purchase_receipt",
            callback: function(r) {
                if (!r.exe) {
                    var doc = frappe.model.sync(r.message.new_doc);
                    frappe.set_route("Form", doc[0].doctype, doc[0].name);
                }
            }
        })
	},
    make_purchase_return: function (frm) {
        frappe.call({
            method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_return_against_rejected_warehouse",
            args: {
                source_name: cur_frm.doc.purchase_receipt,
            },
            callback: function (r) {
                if (r.message) {
                    frappe.model.sync(r.message);
                    frappe.set_route("Form", r.message.doctype, r.message.name);
                }
            },
        });
    },
    get_purchase_receipt_data: function (frm) {
        frm.doc.items = [];
        frappe.model.with_doc("Purchase Receipt", frm.doc.purchase_receipt, function() {
            var purchase_receipt = frappe.model.get_doc("Purchase Receipt", frm.doc.purchase_receipt);
            if (!frm.doc.supplier) {
                frm.set_value("supplier", purchase_receipt.supplier);
            }
            frm.set_value("currency", purchase_receipt.currency);
            frm.set_value("conversion_rate", purchase_receipt.conversion_rate);
            frm.set_value("contact_person", purchase_receipt.contact_person);
            frm.set_value("contact_email", purchase_receipt.contact_email);
            purchase_receipt.items.forEach((item) => {
                if (item.rejected_qty > 0) {
                    frm.add_child("items", {
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "rejected_qty": item.rejected_qty,
                        "uom": item.uom,
                        "stock_uom": item.stock_uom,
                        "conversion_factor": item.conversion_factor,
                        "rate": item.rate,
                        "amount": item.rejected_qty * item.rate,
                        "base_rate": item.base_rate,
                        "base_amount": item.rejected_qty * item.base_rate,
                        "purchase_order": item.purchase_order || "", 
                        "purchase_order_item": item.purchase_order_item || "",
                        "purchase_receipt": frm.doc.purchase_receipt, 
                        "purchase_receipt_item": item.name || "",
                    });
                }
            });
            frm.refresh_fields();
        })
    }
});
