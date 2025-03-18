frappe.ui.form.on("Purchase Receipt", {
    refresh: function (frm) {
		if (frm.doc.docstatus == 0) {
			frm.add_custom_button(
				__("Complaint"),
				function () {
					console.log("TESTING")
					// frm.trigger("get_items_from_complaint");
					let filters = {
						complaint_status: ["not in", ["Completed"]],
						returned_percent: [">", 0],
						docstatus: 1,
					};
	
					if (frm.doc.supplier) {
						filters.supplier = frm.doc.supplier;	
					}
					
					erpnext.utils.map_current_doc({
						method: "purchase_receipt_rejected.purchase_receipt_rejected.doctype.complaint.complaint.map_purchase_receipt",
						source_doctype: "Complaint",
						target: frm,
						setters: {
							supplier: frm.doc.supplier || null,
							purchase_receipt: null,
							purchase_order: null,
						},
						get_query_filters: filters,
					});
				},
				__("Get Items From")
			);
		};
		if (frm.doc.docstatus == 1 && frm.doc.status != "Closed") {
			frm.add_custom_button(
				__("Complaint"),
				function () {
					frappe.model.open_mapped_doc({
						method: "purchase_receipt_rejected.purchase_receipt_rejected.doctype.complaint.complaint.make_complaint",
						frm: cur_frm,
					});
				},
				__("Create")
			);
		}
	},
	get_items_from_complaint: function (frm) {
		var d = new frappe.ui.form.MultiSelectDialog({
			doctype: "Complaint",
			target: frm,
			date_field: "posting_date",
			add_filters_group: 1,
			setters: {
				supplier: frm.doc.supplier || null,
				purchase_receipt: null,
				purchase_order: null,
			},
			get_query() {
				let filters = {
					complaint_status: ["not in", ["Completed"]],
					returned_percent: [">", 0],
					docstatus: 1,
				};

				if (frm.doc.supplier) {
					filters.supplier = frm.doc.supplier;	
				}

				return {
					filters: filters,
				};
			},
			action(complaint) {
				if (complaint.length < 1) {
					frappe.msgprint(
						__("Please select a Complaint document")
					);
					return;
				} else if (complaint.length > 1) {
					frappe.msgprint(
						__("Please select only one Complaint document")
					);
					return;
				}

				frappe
					.call({
						method: "purchase_receipt_rejected.purchase_receipt_rejected.doctype.complaint.complaint.make_purchase_receipt",
						args: {
							complaint_name: complaint[0],
						},
						callback: function (r) {
							if (r.message) {
								frm.set_value("naming_series", r.message.naming_series);
								frm.set_value("supplier", r.message.supplier);
								frm.set_value("complaint", r.message.complaint);
								frm.set_value("custom_po", r.message.custom_po);
								frm.set_value("currency", r.message.currency);
								frm.set_value("conversion_rate", r.message.conversion_rate);
								frm.set_value("items", r.message.items);
								frm.doc.items.forEach((item, index) => {
									const complaintItem = r.message.items[index];
									if (complaintItem) {
										console.log(complaintItem.price_list_rate)
										frappe.model.set_value(item.doctype, item.name, "price_list_rate", complaintItem.price_list_rate);
									}
								});
								d.dialog.hide();
							}
						},
					})
			},
		});
	},
});