from flask import Blueprint, request, jsonify
from bson import ObjectId
from app.extensions import mongo
from app.services.auth_service import verify_bearer_token, check_permission
from app.services.compliance_service import (
    create_legal_hold,
    list_legal_holds,
    toggle_legal_hold
)

compliance_bp = Blueprint("compliance_bp", __name__, url_prefix="/api")

def _error(msg, code=400):
    return jsonify({"error": msg}), code

def _success(data=None, msg="Success", code=200):
    return jsonify({"data": data, "message": msg}), code

def _auth():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    try:
        user_doc, decoded = verify_bearer_token(auth_header.split(" ", 1)[1])
        return {"user_doc": user_doc, "decoded": decoded}
    except Exception:
        return None

@compliance_bp.route("/orgs/<org_id>/compliance/holds", methods=["GET"])
def get_holds(org_id):
    auth = _auth()
    if not auth:
        return _error("Unauthorized", 401)
    
    # check adopt_compliance permission or similar admin permission
    if not check_permission(auth["user_doc"], auth["decoded"], "adopt_compliance", {"type": "org", "org_id": org_id}):
        return _error("Forbidden", 403)
        
    holds = list_legal_holds(org_id)
    return _success({"holds": holds})

@compliance_bp.route("/orgs/<org_id>/compliance/holds", methods=["POST"])
def add_hold(org_id):
    auth = _auth()
    if not auth:
        return _error("Unauthorized", 401)
        
    if not check_permission(auth["user_doc"], auth["decoded"], "adopt_compliance", {"type": "org", "org_id": org_id}):
        return _error("Forbidden", 403)
        
    data = request.get_json() or {}
    name = data.get("name")
    description = data.get("description", "")
    target_type = data.get("target_type") # "project" or "form"
    target_ids = data.get("target_ids", [])
    
    if not name or not target_type:
        return _error("Missing required fields: name, target_type")
        
    hold = create_legal_hold(
        org_id=org_id,
        name=name,
        description=description,
        target_type=target_type,
        target_ids=target_ids,
        created_by=str(auth["user_doc"]["_id"])
    )
    # Convert ObjectIds to strings
    hold["_id"] = str(hold["_id"])
    hold["org_id"] = str(hold["org_id"])
    hold["created_by"] = str(hold["created_by"])
    hold["target_ids"] = [str(tid) for tid in hold.get("target_ids", [])]
    
    return _success(hold, "Legal hold created", 201)

@compliance_bp.route("/compliance/holds/<hold_id>", methods=["PUT"])
def toggle_hold(hold_id):
    auth = _auth()
    if not auth:
        return _error("Unauthorized", 401)
        
    # Find hold to verify org permission
    hold = mongo.db.legal_holds.find_one({"_id": ObjectId(hold_id) if ObjectId.is_valid(hold_id) else hold_id})
    if not hold:
        return _error("Legal hold not found", 404)
        
    if not check_permission(auth["user_doc"], auth["decoded"], "adopt_compliance", {"type": "org", "org_id": str(hold["org_id"])}):
        return _error("Forbidden", 403)
        
    data = request.get_json() or {}
    is_active = data.get("is_active", True)
    
    toggle_legal_hold(hold_id, is_active)
    return _success(None, "Legal hold updated successfully")
