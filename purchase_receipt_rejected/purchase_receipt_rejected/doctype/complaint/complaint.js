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
    make_purchase_receipt: function (frm) {
		frappe.call({
            doc: frm.doc,
            method: "create_purchase_receipt",
            callback: function(r) {
                console.log("message", r.message);
                console.log("exe", r.exe);
                if (!r.exe) {
                    var doc = frappe.model.sync(r.message);
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
    }
});
