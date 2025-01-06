# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe import _

def get_dashboard_for_purchase_receipt(data):
    data["transactions"].append({
        "label": _("Complaint"), "items": ["Complaint"]
    })
    
    data["non_standard_fieldnames"].update(
		{"Complaint": "purchase_receipt"}
	)
    
    return data