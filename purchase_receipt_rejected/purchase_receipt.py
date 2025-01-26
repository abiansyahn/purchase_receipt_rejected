import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form
frappe.utils.logger.set_log_level("DEBUG")

def check_for_rejected_items(self, method):
    rejected_items = []
    for item in self.items:
        if item.rejected_qty > 0:
            rejected_items.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "rejected_qty": item.rejected_qty,
                "uom": item.uom,
                "stock_uom": item.stock_uom,
                "conversion_factor": item.conversion_factor,
                "price_list_rate": item.price_list_rate,
                "base_price_list_rate": item.base_price_list_rate,
                "discount_percentage": item.discount_percentage,
                "discount_amount": item.discount_amount,
                "rate": item.rate,
                "amount": item.rejected_qty * item.rate,
                "base_rate": item.base_rate,
                "base_amount": item.rejected_qty * item.base_rate,
                "purchase_order": item.purchase_order or "", 
                "purchase_order_item": item.purchase_order_item or "",
                "purchase_receipt": self.name, 
                "purchase_receipt_item": item.name or "",
            })
    
    if len(rejected_items) > 0:
        doc = frappe.new_doc("Complaint")
        doc.supplier = self.supplier
        doc.purchase_receipt = self.name
        doc.purchase_order = self.custom_po or ""
        doc.currency = self.currency or ""
        doc.conversion_rate = self.conversion_rate or ""
        doc.contact_person = self.contact_person or ""
        doc.contact_email = self.contact_email or ""
        for i in rejected_items:
            doc.append("items", i)
        doc.insert(ignore_permissions=True)

        frappe.msgprint(_("Complaint {0} created against Purchase Receipt {1}").format(get_link_to_form("Complaint", doc.name), self.name))

def update_returned_item(self, method):
    if self.return_against:
        purchase_receipt_complait = frappe.get_value("Complaint", {"purchase_receipt": self.return_against}, "name")
        if purchase_receipt_complait:
            for item in self.items:
                if item.purchase_receipt_item:
                    complaint_item = frappe.get_value("Purchase Receipt Rejected Item", {"purchase_receipt_item": item.purchase_receipt_item}, "name")
                    returned_qty = (frappe.db.sql(
                        f"""select ifnull(sum(-1*qty), 0)
                        from `tabPurchase Receipt Item` where purchase_receipt_item = '{item.purchase_receipt_item}'
                        and docstatus = 1
                        and qty < 0
                        """
                    )[0][0] or 0.0)

                    frappe.logger(allow_site=True).debug(returned_qty)
                    frappe.db.sql(
                        f"""update `tabPurchase Receipt Rejected Item`
                        set returned_qty = {flt(returned_qty)}
                        where name='{complaint_item}'
                        """
                    )

            frappe.db.sql(
                f"""update `tabComplaint`
                set returned_percent = round(
                    ifnull((select
                        ifnull(sum(case when abs(rejected_qty) > abs(returned_qty) then abs(returned_qty) else abs(rejected_qty) end), 0)
                        / sum(abs(rejected_qty)) * 100
                    from `tabPurchase Receipt Rejected Item` where parent='{purchase_receipt_complait}' and parenttype='Complaint' having sum(abs(rejected_qty)) > 0), 0), 6)
                where name='{purchase_receipt_complait}'"""
            )
            frappe.db.set_value("Complaint", purchase_receipt_complait, "is_item_returned", 1)
            frappe.db.commit()

def update_cancel_returned_item(self, method):
    if self.return_against:
        purchase_receipt_complait = frappe.get_value("Complaint", {"purchase_receipt": self.return_against}, "name")
        if purchase_receipt_complait:
            for item in self.items:
                if item.purchase_receipt_item:
                    complaint_item = frappe.get_value("Purchase Receipt Rejected Item", {"purchase_receipt_item": item.purchase_receipt_item}, "name")
                    returned_qty = (frappe.db.sql(
                        f"""select ifnull(sum(qty), 0)
                        from `tabPurchase Receipt Item` where purchase_receipt_item = '{item.purchase_receipt_item}'
                        and docstatus = 1
                        and qty < 0
                        """
                    )[0][0] or 0.0)

                    frappe.db.sql(
                        f"""update `tabPurchase Receipt Rejected Item`
                        set returned_qty = {flt(returned_qty)}
                        where name='{complaint_item}'
                        """
                    )

            frappe.db.sql(
                f"""update `tabComplaint`
                set returned_percent = round(
                    ifnull((select
                        ifnull(sum(case when abs(rejected_qty) > abs(returned_qty) then abs(returned_qty) else abs(rejected_qty) end), 0)
                        / sum(abs(rejected_qty)) * 100
                    from `tabPurchase Receipt Rejected Item` where parent='{purchase_receipt_complait}' and parenttype='Complaint' having sum(abs(rejected_qty)) > 0), 0), 6)
                where name='{purchase_receipt_complait}'"""
            )
            frappe.db.set_value("Complaint", purchase_receipt_complait, "is_item_returned", 0)
            frappe.db.commit()

def update_complaint_items(self, method):
    if self.complaint:
        for item in self.items:
            if item.complaint_item:
                submitted = frappe.db.sql(
                    "select name from `tabComplaint` where docstatus = 1 and name = %s",
                    item.complaint,
                )
                if not submitted:
                    frappe.throw(_("Complaint {0} is not submitted").format(item.complaint))

                returned_qty, redelivered_qty = frappe.get_value("Purchase Receipt Rejected Item", item.complaint_item, ["returned_qty", "redelivered_qty"])
                if item.qty > (returned_qty - redelivered_qty):
                    frappe.throw(_(f"Accepted Qty row {item.idx} can't be more than {(returned_qty - redelivered_qty)}"))

                to_redelivered_qty = (frappe.db.sql(
                    f"""select ifnull(sum(qty), 0)
                    from `tabPurchase Receipt Item` where complaint_item = '{item.complaint_item}'
                    and docstatus = 1
                    """
                )[0][0] or 0.0)
                
                frappe.db.sql(
                    f"""update `tabPurchase Receipt Rejected Item`
                    set redelivered_qty = {flt(to_redelivered_qty)}
                    where name='{item.complaint_item}'
                    """
                )

        frappe.db.sql(
            f"""update `tabComplaint`
            set redelivered_percent = round(
                ifnull((select
                    ifnull(sum(case when abs(rejected_qty) > abs(redelivered_qty) then abs(redelivered_qty) else abs(rejected_qty) end), 0)
                    / sum(abs(rejected_qty)) * 100
                from `tabPurchase Receipt Rejected Item` where parent='{self.complaint}' and parenttype='Complaint' having sum(abs(rejected_qty)) > 0), 0), 6)
            where name='{self.complaint}'"""
        )

        frappe.db.sql(
            f"""update `tabComplaint`
            set complaint_status = case 
                when redelivered_percent>=99.999999 then 'Completed'
                when redelivered_percent>=0.001 then 'On Progress'
                else complaint_status
            end
            where name='{self.complaint}'"""
        )

def update_cancel_complaint_items(self, method):
    if self.complaint:
        for item in self.items:
            if item.complaint_item:
                submitted = frappe.db.sql(
                    "select name from `tabComplaint` where docstatus = 1 and name = %s",
                    item.complaint,
                )

                if not submitted:
                    frappe.throw(_("Complaint {0} is not submitted").format(item.complaint))

                redelivered_qty = (frappe.db.sql(
                    f"""select ifnull(sum(qty), 0)
                    from `tabPurchase Receipt Item` where complaint_item = '{item.complaint_item}'
                    and docstatus = 1
                    """
                )[0][0] or 0.0)
                
                frappe.db.sql(
                    f"""update `tabPurchase Receipt Rejected Item`
                    set redelivered_qty = {flt(redelivered_qty - item.qty)}
                    where name='{item.complaint_item}'
                    """
                )

        frappe.db.sql(
            f"""update `tabComplaint`
            set redelivered_percent = round(
                ifnull((select
                    ifnull(sum(case when abs(rejected_qty) > abs(redelivered_qty) then abs(redelivered_qty) else abs(rejected_qty) end), 0)
                    / sum(abs(rejected_qty)) * 100
                from `tabPurchase Receipt Rejected Item` where parent='{self.complaint}' and parenttype='Complaint' having sum(abs(rejected_qty)) > 0), 0), 6)
            where name='{self.complaint}'"""
        )

        frappe.db.sql(
            f"""update `tabComplaint`
            set complaint_status = case 
                when redelivered_percent>=99.999999 then 'Completed'
                when redelivered_percent>=0.001 then 'On Progress'
                else complaint_status
            end
            where name='{self.complaint}'"""
        )

