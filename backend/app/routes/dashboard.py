from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
import datetime
import uuid
import json
import jwt

from app.extensions import mongo
from app.services.dashboard_service import dashboard_service, serialize_doc

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/internal/v1/dashboards")
public_dashboard_bp = Blueprint("public_dashboard", __name__, url_prefix="/api/v1/public/dashboards")

def get_current_user_id():
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            secret = current_app.config.get("JWT_SECRET_KEY") or "secret"
            decoded = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_signature": False})
            return decoded.get("user_id") or decoded.get("sub") or token
        except Exception:
            return token
            
    if request.is_json:
        try:
            body = request.get_json() or {}
            if "author_id" in body:
                return body["author_id"]
            if "user_id" in body:
                return body["user_id"]
        except Exception:
            pass
            
    uid = request.args.get("user_id")
    if uid:
        return uid
        
    return str(ObjectId())

# ----------------- CRUD ENDPOINTS -----------------

@dashboard_bp.route("", methods=["POST"])
def create_dashboard():
    data = request.get_json() or {}
    author_id = get_current_user_id()
    
    try:
        dashboard = dashboard_service.create_dashboard(data, author_id)
        return jsonify({"dashboard": serialize_doc(dashboard)}), 201
    except ValueError as e:
        msg = str(e)
        if "conflict" in msg.lower():
            return jsonify({
                "error": {
                    "code": "DASHBOARD_NAME_CONFLICT",
                    "message": msg
                }
            }), 409
        elif "project not found" in msg.lower():
            return jsonify({
                "error": {
                    "code": "PROJECT_NOT_FOUND",
                    "message": msg
                }
            }), 404
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": msg
            }
        }), 400
    except Exception as e:
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

@dashboard_bp.route("", methods=["GET"])
def list_dashboards():
    project_id = request.args.get("project_id")
    if not project_id:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "project_id is required"
            }
        }), 400
        
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search_text = request.args.get("search")
    
    try:
        dashboards, pagination = dashboard_service.list_dashboards(
            project_id=project_id,
            page=page,
            per_page=per_page,
            search_text=search_text
        )
        return jsonify({
            "dashboards": serialize_doc(dashboards),
            "pagination": pagination
        }), 200
    except Exception as e:
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

@dashboard_bp.route("/<dashboard_id>", methods=["GET"])
def get_dashboard(dashboard_id):
    try:
        res = dashboard_service.get_dashboard(dashboard_id)
        if not res:
            return jsonify({
                "error": {
                    "code": "DASHBOARD_NOT_FOUND",
                    "message": "Dashboard not found"
                }
            }), 404
            
        return jsonify(serialize_doc(res)), 200
    except Exception as e:
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

@dashboard_bp.route("/<dashboard_id>", methods=["PATCH"])
def update_dashboard(dashboard_id):
    data = request.get_json() or {}
    try:
        res = dashboard_service.update_dashboard(dashboard_id, data)
        if not res:
            return jsonify({
                "error": {
                    "code": "DASHBOARD_NOT_FOUND",
                    "message": "Dashboard not found"
                }
            }), 404
        return jsonify(serialize_doc(res)), 200
    except ValueError as e:
        msg = str(e)
        if "conflict" in msg.lower():
            return jsonify({
                "error": {
                    "code": "DASHBOARD_NAME_CONFLICT",
                    "message": msg
                }
            }), 409
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": msg
            }
        }), 400
    except Exception as e:
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

@dashboard_bp.route("/<dashboard_id>", methods=["DELETE"])
def delete_dashboard(dashboard_id):
    try:
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        # Check if dashboard exists
        exists = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
        if not exists:
            return jsonify({
                "error": {
                    "code": "DASHBOARD_NOT_FOUND",
                    "message": "Dashboard not found"
                }
            }), 404
            
        dashboard_service.delete_dashboard(dashboard_id)
        return jsonify({"message": "Dashboard deleted"}), 200
    except Exception as e:
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

# ----------------- CANVAS ENDPOINTS -----------------

@dashboard_bp.route("/<dashboard_id>/canvas", methods=["PUT"])
def save_canvas(dashboard_id):
    data = request.get_json() or {}
    canvas = data.get("canvas")
    if canvas is None:
        return jsonify({
            "error": {
                "code": "CANVAS_VALIDATION_ERROR",
                "message": "canvas object is required"
            }
        }), 400
        
    try:
        res = dashboard_service.save_canvas(dashboard_id, canvas)
        if not res:
            return jsonify({
                "error": {
                    "code": "DASHBOARD_NOT_FOUND",
                    "message": "Dashboard not found"
                }
            }), 404
        return jsonify(serialize_doc(res)), 200
    except ValueError as e:
        msg = str(e)
        if "exist" in msg or "not found" in msg:
            return jsonify({
                "error": {
                    "code": "INVALID_ANALYSIS_BINDING",
                    "message": msg
                }
            }), 400
        return jsonify({
            "error": {
                "code": "CANVAS_VALIDATION_ERROR",
                "message": msg
            }
        }), 400
    except Exception as e:
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

@dashboard_bp.route("/<dashboard_id>/canvas/data", methods=["GET"])
@dashboard_bp.route("/<dashboard_id>/data", methods=["GET"])
def get_canvas_data(dashboard_id):
    d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
    if not dashboard:
        return jsonify({
            "error": {
                "code": "DASHBOARD_NOT_FOUND",
                "message": "Dashboard not found"
            }
        }), 404
        
    filter_state_raw = request.args.get("filter_state")
    filter_state = {}
    if filter_state_raw:
        try:
            filter_state = json.loads(filter_state_raw)
        except Exception:
            return jsonify({
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid filter_state JSON"
                }
            }), 400
            
    try:
        widget_data = dashboard_service.resolve_widget_data(dashboard, filter_state)
        return jsonify({
            "canvas": serialize_doc(dashboard.get("canvas")),
            "widget_data": serialize_doc(widget_data)
        }), 200
    except Exception as e:
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

@dashboard_bp.route("/<dashboard_id>/widgets/<widget_id>/data", methods=["GET"])
def get_widget_data(dashboard_id, widget_id):
    d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
    if not dashboard:
        return jsonify({
            "error": {
                "code": "DASHBOARD_NOT_FOUND",
                "message": "Dashboard not found"
            }
        }), 404
        
    widgets = dashboard.get("canvas", {}).get("widgets", [])
    widget = next((w for w in widgets if w.get("id") == widget_id), None)
    if not widget:
        return jsonify({
            "error": {
                "code": "WIDGET_NOT_FOUND",
                "message": f"Widget {widget_id} not found in dashboard"
            }
        }), 404
        
    filter_state_raw = request.args.get("filter_state")
    filter_state = {}
    if filter_state_raw:
        try:
            filter_state = json.loads(filter_state_raw)
        except Exception:
            pass
            
    try:
        # Resolve for this widget only, using a temporary dashboard structure
        temp_db = {
            "canvas": {
                "widgets": [widget]
            }
        }
        res = dashboard_service.resolve_widget_data(temp_db, filter_state)
        w_data = res.get(widget_id, {})
        return jsonify({
            "widget_id": widget_id,
            "status": w_data.get("status"),
            "data": serialize_doc(w_data.get("data")),
            "generated_at": w_data.get("generated_at"),
            "error": w_data.get("error")
        }), 200
    except Exception as e:
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

@dashboard_bp.route("/<dashboard_id>/filter-options", methods=["GET"])
def get_filter_options(dashboard_id):
    analysis_id = request.args.get("analysis_id")
    node_id = request.args.get("node_id")
    column = request.args.get("column")
    limit = request.args.get("limit", 200, type=int)
    
    if not analysis_id or not node_id or not column:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "analysis_id, node_id, and column are required parameters"
            }
        }), 400
        
    try:
        res = dashboard_service.get_filter_options(analysis_id, node_id, column, limit)
        return jsonify(serialize_doc(res)), 200
    except Exception as e:
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

# ----------------- PUBLIC TOKEN ENDPOINTS -----------------

@dashboard_bp.route("/<dashboard_id>/public-token", methods=["POST"])
def enable_public_sharing(dashboard_id):
    d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
    if not dashboard:
        return jsonify({
            "error": {
                "code": "DASHBOARD_NOT_FOUND",
                "message": "Dashboard not found"
            }
        }), 404
        
    token = str(uuid.uuid4())
    
    mongo.db.dashboards.update_one(
        {"_id": d_oid},
        {"$set": {
            "is_public": True,
            "public_token": token,
            "updated_at": datetime.datetime.utcnow().isoformat()
        }}
    )
    
    # Audit log
    mongo.db.audit_logs.insert_one({
        "org_id": dashboard.get("org_id"),
        "entity_type": "dashboard",
        "entity_id": d_oid,
        "action": "dashboard_made_public",
        "timestamp": datetime.datetime.utcnow().isoformat()
    })
    
    platform_config = mongo.db.system_config.find_one({"key": "platform_url"})
    platform_url = platform_config.get("value") if platform_config else request.host_url
    public_url = f"{platform_url.rstrip('/')}/public/dashboard/{token}"
    
    return jsonify({
        "is_public": True,
        "public_token": token,
        "public_url": public_url
    }), 200

@dashboard_bp.route("/<dashboard_id>/public-token", methods=["DELETE"])
def revoke_public_sharing(dashboard_id):
    d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
    if not dashboard:
        return jsonify({
            "error": {
                "code": "DASHBOARD_NOT_FOUND",
                "message": "Dashboard not found"
            }
        }), 404
        
    mongo.db.dashboards.update_one(
        {"_id": d_oid},
        {"$set": {
            "is_public": False,
            "public_token": None,
            "updated_at": datetime.datetime.utcnow().isoformat()
        }}
    )
    
    return jsonify({"message": "Public access revoked"}), 200

# ----------------- PUBLIC (UNAUTHENTICATED) ACCESS -----------------

def strip_bindings_from_canvas(canvas):
    """
    Deep copies canvas and strips data_binding details from widgets.
    """
    if not canvas:
        return canvas
    canvas_copy = json.loads(json.dumps(canvas))
    widgets = canvas_copy.get("widgets", [])
    for w in widgets:
        # Keep empty data_binding or remove sensitive details (analysis_id, node_id)
        if "data_binding" in w:
            w["data_binding"] = {
                "refresh_mode": w["data_binding"].get("refresh_mode", "with_dashboard")
            }
    return canvas_copy

@public_dashboard_bp.route("/<token>", methods=["GET"])
def get_public_dashboard(token):
    dashboard = mongo.db.dashboards.find_one({
        "public_token": token,
        "is_public": True,
        "is_deleted": False
    })
    if not dashboard:
        return jsonify({
            "error": {
                "code": "PUBLIC_TOKEN_NOT_FOUND",
                "message": "Public dashboard not found or sharing disabled"
            }
        }), 404
        
    filter_state_raw = request.args.get("filter_state")
    filter_state = {}
    if filter_state_raw:
        try:
            filter_state = json.loads(filter_state_raw)
        except Exception:
            pass
            
    try:
        widget_data = dashboard_service.resolve_widget_data(dashboard, filter_state)
        # Clean widget_data and strip internal fields
        public_widget_data = {}
        for wid, val in widget_data.items():
            public_widget_data[wid] = {
                "status": val.get("status"),
                "data": val.get("data"),
                "generated_at": val.get("generated_at")
            }
            
        clean_canvas = strip_bindings_from_canvas(dashboard.get("canvas"))
        
        return jsonify({
            "dashboard": {
                "name": dashboard.get("name"),
                "description": dashboard.get("description"),
                "canvas": serialize_doc(clean_canvas),
                "settings": serialize_doc(dashboard.get("settings")),
                "last_updated": dashboard.get("updated_at")
            },
            "widget_data": serialize_doc(public_widget_data)
        }), 200
    except Exception as e:
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

@public_dashboard_bp.route("/<token>/data", methods=["GET"])
def get_public_dashboard_data(token):
    dashboard = mongo.db.dashboards.find_one({
        "public_token": token,
        "is_public": True,
        "is_deleted": False
    })
    if not dashboard:
        return jsonify({
            "error": {
                "code": "PUBLIC_TOKEN_NOT_FOUND",
                "message": "Public dashboard not found or sharing disabled"
            }
        }), 404
        
    filter_state_raw = request.args.get("filter_state")
    filter_state = {}
    if filter_state_raw:
        try:
            filter_state = json.loads(filter_state_raw)
        except Exception:
            pass
            
    try:
        widget_data = dashboard_service.resolve_widget_data(dashboard, filter_state)
        public_widget_data = {}
        for wid, val in widget_data.items():
            public_widget_data[wid] = {
                "status": val.get("status"),
                "data": val.get("data"),
                "generated_at": val.get("generated_at")
            }
            
        return jsonify({
            "widget_data": serialize_doc(public_widget_data),
            "server_time": datetime.datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

# ----------------- SNAPSHOTS ENDPOINTS -----------------

@dashboard_bp.route("/<dashboard_id>/snapshots", methods=["POST"])
def create_snapshot(dashboard_id):
    author_id = get_current_user_id()
    try:
        res = dashboard_service.create_snapshot(dashboard_id, author_id)
        if not res:
            return jsonify({
                "error": {
                    "code": "DASHBOARD_NOT_FOUND",
                    "message": "Dashboard not found"
                }
            }), 404
        return jsonify({"snapshot": serialize_doc(res)}), 201
    except Exception as e:
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e)
            }
        }), 500

@dashboard_bp.route("/<dashboard_id>/snapshots", methods=["GET"])
def list_snapshots(dashboard_id):
    d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    
    query = {"dashboard_id": d_oid, "is_deleted": False}
    total = mongo.db.dashboard_snapshots.count_documents(query)
    
    snapshots_cursor = mongo.db.dashboard_snapshots.find(
        query,
        # Exclude widget data
        {"data.widget_data": 0}
    ).sort("created_at", -1).skip((page - 1) * per_page).limit(per_page)
    
    snapshots = []
    for snap in snapshots_cursor:
        creator_id = snap.get("created_by")
        if creator_id:
            user = mongo.db.users.find_one({"_id": ObjectId(creator_id) if ObjectId.is_valid(creator_id) else creator_id})
            if user:
                snap["created_by_user"] = {
                    "_id": str(user["_id"]),
                    "full_name": user.get("full_name") or user.get("name") or "Unknown"
                }
            else:
                snap["created_by_user"] = {
                    "_id": str(creator_id),
                    "full_name": "Unknown"
                }
        snapshots.append(snap)
        
    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    return jsonify({
        "snapshots": serialize_doc(snapshots),
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }
    }), 200

@dashboard_bp.route("/<dashboard_id>/snapshots/<snapshot_id>", methods=["GET"])
def get_snapshot(dashboard_id, snapshot_id):
    snap_oid = ObjectId(snapshot_id) if ObjectId.is_valid(snapshot_id) else snapshot_id
    snap = mongo.db.dashboard_snapshots.find_one({"_id": snap_oid, "is_deleted": False})
    if not snap:
        return jsonify({
            "error": {
                "code": "SNAPSHOT_NOT_FOUND",
                "message": "Snapshot not found"
            }
        }), 404
        
    return jsonify(serialize_doc(snap)), 200

@dashboard_bp.route("/<dashboard_id>/snapshots/<snapshot_id>", methods=["DELETE"])
def delete_snapshot(dashboard_id, snapshot_id):
    snap_oid = ObjectId(snapshot_id) if ObjectId.is_valid(snapshot_id) else snapshot_id
    # Check exists
    snap = mongo.db.dashboard_snapshots.find_one({"_id": snap_oid, "is_deleted": False})
    if not snap:
        return jsonify({
            "error": {
                "code": "SNAPSHOT_NOT_FOUND",
                "message": "Snapshot not found"
            }
        }), 404
        
    mongo.db.dashboard_snapshots.update_one(
        {"_id": snap_oid},
        {"$set": {
            "is_deleted": True,
            "deleted_at": datetime.datetime.utcnow().isoformat()
        }}
    )
    return jsonify({"message": "Snapshot deleted"}), 200
