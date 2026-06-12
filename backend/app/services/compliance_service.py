import datetime
from bson import ObjectId
from app.extensions import mongo

def _oid(id_val):
    if isinstance(id_val, ObjectId):
        return id_val
    return ObjectId(id_val) if ObjectId.is_valid(id_val) else None

def create_legal_hold(org_id, name, description, target_type, target_ids, created_by):
    doc = {
        "org_id": _oid(org_id),
        "name": name,
        "description": description,
        "target_type": target_type, # "project", "form", "response"
        "target_ids": [_oid(tid) or tid for tid in target_ids],
        "is_active": True,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "created_by": _oid(created_by) or created_by
    }
    mongo.db.legal_holds.insert_one(doc)
    return doc

def list_legal_holds(org_id):
    holds = mongo.db.legal_holds.find({"org_id": _oid(org_id)})
    result = []
    for h in holds:
        result.append({
            "_id": str(h["_id"]),
            "org_id": str(h["org_id"]),
            "name": h.get("name"),
            "description": h.get("description"),
            "target_type": h.get("target_type"),
            "target_ids": [str(tid) for tid in h.get("target_ids", [])],
            "is_active": h.get("is_active", True),
            "created_at": h.get("created_at"),
            "created_by": str(h.get("created_by", ""))
        })
    return result

def toggle_legal_hold(hold_id, is_active):
    mongo.db.legal_holds.update_one(
        {"_id": _oid(hold_id)},
        {"$set": {"is_active": is_active}}
    )

def is_resource_held(target_type, target_id):
    tid = _oid(target_id) or target_id
    if target_type == "form":
        # Check direct form hold
        if mongo.db.legal_holds.find_one({"is_active": True, "target_type": "form", "target_ids": tid}):
            return True
        # Check project hold of this form
        form = mongo.db.forms.find_one({"_id": tid})
        if form and form.get("project_id"):
            pid = _oid(form["project_id"])
            if mongo.db.legal_holds.find_one({"is_active": True, "target_type": "project", "target_ids": pid}):
                return True
    elif target_type == "project":
        if mongo.db.legal_holds.find_one({"is_active": True, "target_type": "project", "target_ids": tid}):
            return True
    elif target_type == "response":
        if mongo.db.legal_holds.find_one({"is_active": True, "target_type": "response", "target_ids": tid}):
            return True
        response = mongo.db.responses.find_one({"_id": tid})
        if response and response.get("form_id"):
            fid = _oid(response["form_id"])
            if is_resource_held("form", fid):
                return True
    return False
