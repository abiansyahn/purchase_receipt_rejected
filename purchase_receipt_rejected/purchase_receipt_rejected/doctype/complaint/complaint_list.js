frappe.listview_settings["Complaint"] = {
    get_indicator: function (doc) {
        if (doc.complaint_status === "On Progress") {
            return [__("On Progress"), "orange", "complaint_status,=,On Progress"];
        } else if (doc.complaint_status === "Completed") {
            return [__("Completed"), "green", "complaint_status,=,Completed"];
        }
    }
}