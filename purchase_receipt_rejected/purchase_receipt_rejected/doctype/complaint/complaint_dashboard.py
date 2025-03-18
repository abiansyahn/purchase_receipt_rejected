from frappe import _


def get_data():
    return {
		"fieldname": "complaint",
        "transactions": [
            {"label": _("Purchase Receipt"), "items": ["Purchase Receipt"]},
        ]
    }