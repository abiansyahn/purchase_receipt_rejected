import frappe
from frappe import _
from frappe.utils import flt
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
                "rate": item.rate,
                "amount": item.rejected_qty * item.rate,
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

def update_returned_item(self, method):
    if self.return_against:
        purchase_receipt_complait = frappe.get_list("Complaint", {"purchase_receipt": self.return_against}, "name")
        if len(purchase_receipt_complait) > 0:
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
                    from `tabPurchase Receipt Rejected Item` where parent='{purchase_receipt_complait[0].name}' and parenttype='Complaint' having sum(abs(rejected_qty)) > 0), 0), 6)
                where name='{purchase_receipt_complait[0].name}'"""
            )
            frappe.db.set_value("Complaint", purchase_receipt_complait[0].name, "is_item_returned", 1)
            frappe.db.commit()

def update_cancel_returned_item(self, method):
    if self.return_against:
        purchase_receipt_complait = frappe.get_list("Complaint", {"purchase_receipt": self.return_against}, "name")
        if len(purchase_receipt_complait) > 0:
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
                    from `tabPurchase Receipt Rejected Item` where parent='{purchase_receipt_complait[0].name}' and parenttype='Complaint' having sum(abs(rejected_qty)) > 0), 0), 6)
                where name='{purchase_receipt_complait[0].name}'"""
            )
            frappe.db.set_value("Complaint", purchase_receipt_complait[0].name, "is_item_returned", 0)
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

                rejected_qty = frappe.get_value("Purchase Receipt Rejected Item", item.complaint_item, "rejected_qty")
                if item.qty > rejected_qty:
                    frappe.throw(_(f"Accepted Qty row {item.idx} can't be more than {rejected_qty}"))

                redelivered_qty = (frappe.db.sql(
                    f"""select ifnull(sum(qty), 0)
                    from `tabPurchase Receipt Item` where complaint_item = '{item.complaint_item}'
                    and docstatus = 1
                    """
                )[0][0] or 0.0)
                
                frappe.db.sql(
                    f"""update `tabPurchase Receipt Rejected Item`
                    set redelivered_qty = {flt(redelivered_qty)}
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

        complaint_status, purchase_receipt = frappe.db.get_value("Complaint", self.complaint, ["complaint_status", "purchase_receipt"])
        workflow_state = frappe.get_value("Purchase Receipt", purchase_receipt, "workflow_state")
        if workflow_state:
            if complaint_status == "Completed":
                frappe.db.set_value("Purchase Receipt", purchase_receipt, "workflow_state", "Delivery Checked")

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

        complaint_status, purchase_receipt = frappe.db.get_value("Complaint", self.complaint, ["complaint_status", "purchase_receipt"])
        workflow_state = frappe.get_value("Purchase Receipt", purchase_receipt, "workflow_state")
        if workflow_state:
            if complaint_status == "Completed":
                frappe.db.set_value("Purchase Receipt", purchase_receipt, "workflow_state", "Delivery Checked")
            else:
                frappe.db.set_value("Purchase Receipt", purchase_receipt, "workflow_state", "Fehlbuchung")

