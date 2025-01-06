import frappe

def after_install():
    create_workflow_state()
    create_workflow_action()
    add_workflow_action()

def before_uninstall():
    remove_workflow_action()

def create_workflow_state():
    if not frappe.db.exists("Workflow State", "Half Received"):
        try:
            workflow_state = frappe.new_doc("Workflow State")
            workflow_state.workflow_state_name = "Half Received"
            workflow_state.insert(ignore_permissions=True)
        except Exception as e:
            raise e

def create_workflow_action():
    if not frappe.db.exists("Workflow Action Master", "Half Received"):
        try:
            workflow_action = frappe.new_doc("Workflow Action Master")
            workflow_action.workflow_action_name = "Half Received"
            workflow_action.insert(ignore_permissions=True)
        except Exception as e:
            raise e

def add_workflow_action():
    try:
        workflow_doc = frappe.get_doc("Workflow", "Purchase Receipt")
        workflow_doc.append("states", {
            "state": "Half Received",
            "doc_status": "1",
            "allow_edit": "Logistics User"
        })
        workflow_doc.append("transitions", {
            "state": "Goods Received",
            "action": "Half Received",
            "next_state": "Half Received",
            "allowed": "Logistics User",
            "allow_self_approval": 1,
            "dont_send_notification_workflow": 1
        })
        workflow_doc.append("transitions", {
            "state": "Half Received",
            "action": "Abbrechen",
            "next_state": "Fehlbuchung",
            "allowed": "Logistics User",
            "allow_self_approval": 1,
            "dont_send_notification_workflow": 1
        })
        workflow_doc.append("transitions", {
            "state": "Half Received",
            "action": "All Items Checked",
            "next_state": "Delivery Checked",
            "allowed": "Logistics User",
            "allow_self_approval": 1,
            "dont_send_notification_workflow": 1
        })
        workflow_doc.save(ignore_permissions=True)
    except Exception as e:
        raise e

def remove_workflow_action():
    state_list = frappe.get_list("Workflow Document State", {"state": "Half Received"}, ["name"])
    transition_list = frappe.get_list("Workflow Transition", {"state": "Half Received"}, ["name"])
    for state in state_list:
        frappe.delete_doc("Workflow Document State", state.get("name"))
    for transition in transition_list:
        frappe.delete_doc("Workflow Transition", transition.get("name"))