from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
import datetime
import uuid
import json
import jwt

from app.extensions import mongo
from app.services.auth_service import decode_request_bearer_token
from app.services.dashboard_service import dashboard_service, serialize_doc

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/internal/v1/dashboards")
public_dashboard_bp = Blueprint("public_dashboard", __name__, url_prefix="/api/v1/public/dashboards")


def success_response(data=None, legacy=None, status_code=200):
    payload = {"status": "success", "data": data if data is not None else {}}
    if isinstance(legacy, dict):
        payload.update(legacy)
    return jsonify(payload), status_code


def error_response(code, message, status_code=400, details=None):
    details = details or {}
    payload = {
        "status": "error",
        "code": code,
        "message": message,
        "details": details,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
    }
    return jsonify(payload), status_code


def _decode_access_token():
    try:
        _, decoded = decode_request_bearer_token(request.headers.get("Authorization", ""))
        if decoded.get("system_role") not in ("super_admin", "user"):
            return None
        return decoded
    except ValueError:
        return None


def get_request_context():
    decoded = _decode_access_token()
    if decoded:
        org_ids = []
        for org in decoded.get("orgs", []):
            if org.get("status") == "active" and org.get("org_id") is not None:
                org_ids.append(str(org.get("org_id")))
        return {
            "authenticated": True,
            "user_id": decoded.get("sub"),
            "system_role": decoded.get("system_role", "user"),
            "org_ids": org_ids,
            "decoded": decoded,
        }

    if current_app.config.get("TESTING"):
        return {
            "authenticated": False,
            "user_id": request.headers.get("X-Test-User-Id") or "test-user",
            "system_role": "super_admin",
            "org_ids": [],
            "decoded": {},
        }

    return None


def require_request_context():
    context = get_request_context()
    if context and context.get("user_id"):
        return context
    return None


def _dashboard_matches_org_access(dashboard, context):
    if not context:
        return False
    if context.get("system_role") == "super_admin":
        return True
    dashboard_org_id = dashboard.get("org_id")
    if dashboard_org_id is None:
        return True
    return str(dashboard_org_id) in set(context.get("org_ids", []))


def _dashboard_lookup(dashboard_id):
    d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    return d_oid, mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})


def _public_dashboard_payload(dashboard, widget_data):
    clean_canvas = strip_bindings_from_canvas(dashboard.get("canvas"))
    return {
        "dashboard": {
            "name": dashboard.get("name"),
            "description": dashboard.get("description"),
            "canvas": serialize_doc(clean_canvas),
            "settings": serialize_doc(dashboard.get("settings")),
            "last_updated": dashboard.get("updated_at"),
        },
        "widget_data": serialize_doc(widget_data),
    }


# ----------------- CRUD ENDPOINTS -----------------


@dashboard_bp.route("", methods=["POST"])
def create_dashboard():
    data = request.get_json() or {}
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    try:
        dashboard = dashboard_service.create_dashboard(data, context["user_id"], context)
        serialized = serialize_doc(dashboard)
        return success_response({"dashboard": serialized}, {"dashboard": serialized}, 201)
    except ValueError as e:
        msg = str(e)
        if "conflict" in msg.lower():
            return error_response("DASHBOARD_NAME_CONFLICT", msg, 409)
        if "project not found" in msg.lower():
            return error_response("PROJECT_NOT_FOUND", msg, 404)
        return error_response("VALIDATION_ERROR", msg, 400)
    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e), 500)


@dashboard_bp.route("", methods=["GET"])
def list_dashboards():
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    project_id = request.args.get("project_id")
    if not project_id:
        return error_response("VALIDATION_ERROR", "project_id is required", 400)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search_text = request.args.get("search")

    try:
        dashboards, pagination = dashboard_service.list_dashboards(
            project_id=project_id,
            page=page,
            per_page=per_page,
            search_text=search_text,
            context=context,
        )
        serialized = serialize_doc(dashboards)
        payload = {"dashboards": serialized, "pagination": pagination}
        return success_response(payload, payload, 200)
    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e), 500)


@dashboard_bp.route("/<dashboard_id>", methods=["GET"])
def get_dashboard(dashboard_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    try:
        res = dashboard_service.get_dashboard(dashboard_id, context)
        if not res:
            return error_response("DASHBOARD_NOT_FOUND", "Dashboard not found", 404)

        serialized = serialize_doc(res)
        legacy = {"dashboard": serialized, "linked_analyses": serialized.get("linked_analyses", [])}
        return success_response(serialized, legacy, 200)
    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e), 500)


@dashboard_bp.route("/<dashboard_id>", methods=["PATCH"])
def update_dashboard(dashboard_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    data = request.get_json() or {}
    try:
        res = dashboard_service.update_dashboard(dashboard_id, data, context)
        if not res:
            return error_response("DASHBOARD_NOT_FOUND", "Dashboard not found", 404)

        serialized = serialize_doc(res)
        return success_response({"dashboard": serialized}, {"dashboard": serialized}, 200)
    except ValueError as e:
        msg = str(e)
        if "conflict" in msg.lower():
            return error_response("DASHBOARD_NAME_CONFLICT", msg, 409)
        return error_response("VALIDATION_ERROR", msg, 400)
    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e), 500)


@dashboard_bp.route("/<dashboard_id>", methods=["DELETE"])
def delete_dashboard(dashboard_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    try:
        d_oid, exists = _dashboard_lookup(dashboard_id)
        if not exists:
            return error_response("DASHBOARD_NOT_FOUND", "Dashboard not found", 404)

        dashboard_service.delete_dashboard(dashboard_id, context)
        return success_response({"message": "Dashboard deleted"}, {"message": "Dashboard deleted"}, 200)
    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e), 500)


# ----------------- CANVAS ENDPOINTS -----------------


@dashboard_bp.route("/<dashboard_id>/canvas", methods=["PUT"])
def save_canvas(dashboard_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    data = request.get_json() or {}
    canvas = data.get("canvas")
    if canvas is None:
        return error_response("CANVAS_VALIDATION_ERROR", "canvas object is required", 400)

    try:
        res = dashboard_service.save_canvas(dashboard_id, canvas, context)
        if not res:
            return error_response("DASHBOARD_NOT_FOUND", "Dashboard not found", 404)

        serialized = serialize_doc(res)
        return success_response({"dashboard": serialized}, {"dashboard": serialized}, 200)
    except ValueError as e:
        msg = str(e)
        if "exist" in msg.lower() or "not found" in msg.lower():
            return error_response("INVALID_ANALYSIS_BINDING", msg, 400)
        return error_response("CANVAS_VALIDATION_ERROR", msg, 400)
    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e), 500)


@dashboard_bp.route("/<dashboard_id>/canvas/data", methods=["GET"])
@dashboard_bp.route("/<dashboard_id>/data", methods=["GET"])
def get_canvas_data(dashboard_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
    if not dashboard:
        return error_response("DASHBOARD_NOT_FOUND", "Dashboard not found", 404)

    filter_state_raw = request.args.get("filter_state")
    filter_state = {}
    if filter_state_raw:
        try:
            filter_state = json.loads(filter_state_raw)
        except Exception:
            return error_response("VALIDATION_ERROR", "Invalid filter_state JSON", 400)

    try:
        widget_data = dashboard_service.resolve_widget_data(dashboard, filter_state)
        payload = {
            "canvas": serialize_doc(dashboard.get("canvas")),
            "widget_data": serialize_doc(widget_data),
        }
        return success_response(payload, payload, 200)
    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e), 500)


@dashboard_bp.route("/<dashboard_id>/widgets/<widget_id>/data", methods=["GET"])
def get_widget_data(dashboard_id, widget_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
    if not dashboard:
        return error_response("DASHBOARD_NOT_FOUND", "Dashboard not found", 404)

    widgets = dashboard.get("canvas", {}).get("widgets", [])
    widget = next((w for w in widgets if w.get("id") == widget_id), None)
    if not widget:
        return error_response("WIDGET_NOT_FOUND", f"Widget {widget_id} not found in dashboard", 404)

    filter_state_raw = request.args.get("filter_state")
    filter_state = {}
    if filter_state_raw:
        try:
            filter_state = json.loads(filter_state_raw)
        except Exception:
            pass

    try:
        temp_db = {"canvas": {"widgets": [widget]}}
        res = dashboard_service.resolve_widget_data(temp_db, filter_state)
        w_data = res.get(widget_id, {})
        payload = {
            "widget_id": widget_id,
            "status": w_data.get("status"),
            "data": serialize_doc(w_data.get("data")),
            "generated_at": w_data.get("generated_at"),
            "error": w_data.get("error"),
        }
        return success_response(payload, payload, 200)
    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e), 500)


@dashboard_bp.route("/<dashboard_id>/filter-options", methods=["GET"])
def get_filter_options(dashboard_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    analysis_id = request.args.get("analysis_id")
    node_id = request.args.get("node_id")
    column = request.args.get("column")
    limit = request.args.get("limit", 200, type=int)

    if not analysis_id or not node_id or not column:
        return error_response("VALIDATION_ERROR", "analysis_id, node_id, and column are required parameters", 400)

    try:
        res = dashboard_service.get_filter_options(analysis_id, node_id, column, limit, context)
        return success_response(serialize_doc(res), serialize_doc(res), 200)
    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e), 500)


# ----------------- PUBLIC TOKEN ENDPOINTS -----------------


@dashboard_bp.route("/<dashboard_id>/public-token", methods=["POST"])
def enable_public_sharing(dashboard_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
    if not dashboard:
        return error_response("DASHBOARD_NOT_FOUND", "Dashboard not found", 404)

    token = str(uuid.uuid4())
    mongo.db.dashboards.update_one(
        {"_id": d_oid},
        {
            "$set": {
                "is_public": True,
                "public_token": token,
                "updated_at": datetime.datetime.utcnow().isoformat(),
            }
        },
    )

    mongo.db.audit_logs.insert_one(
        {
            "org_id": dashboard.get("org_id"),
            "entity_type": "dashboard",
            "entity_id": d_oid,
            "action": "dashboard_made_public",
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }
    )

    platform_config = mongo.db.system_config.find_one({"key": "platform_url"})
    platform_url = platform_config.get("value") if platform_config else request.host_url
    public_url = f"{platform_url.rstrip('/')}/public/dashboard/{token}"

    payload = {"is_public": True, "public_token": token, "public_url": public_url}
    return success_response(payload, payload, 200)


@dashboard_bp.route("/<dashboard_id>/public-token", methods=["DELETE"])
def revoke_public_sharing(dashboard_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
    if not dashboard:
        return error_response("DASHBOARD_NOT_FOUND", "Dashboard not found", 404)

    mongo.db.dashboards.update_one(
        {"_id": d_oid},
        {
            "$set": {
                "is_public": False,
                "public_token": None,
                "updated_at": datetime.datetime.utcnow().isoformat(),
            }
        },
    )

    return success_response({"message": "Public access revoked"}, {"message": "Public access revoked"}, 200)


# ----------------- PUBLIC (UNAUTHENTICATED) ACCESS -----------------


def strip_bindings_from_canvas(canvas):
    if not canvas:
        return canvas

    canvas_copy = json.loads(json.dumps(canvas))
    widgets = canvas_copy.get("widgets", [])
    for widget in widgets:
        if "data_binding" in widget:
            widget["data_binding"] = {
                "refresh_mode": widget["data_binding"].get("refresh_mode", "with_dashboard")
            }
    return canvas_copy


@public_dashboard_bp.route("/<token>", methods=["GET"])
def get_public_dashboard(token):
    dashboard = mongo.db.dashboards.find_one(
        {"public_token": token, "is_public": True, "is_deleted": False}
    )
    if not dashboard:
        return error_response(
            "PUBLIC_TOKEN_NOT_FOUND",
            "Public dashboard not found or sharing disabled",
            404,
        )

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
                "generated_at": val.get("generated_at"),
            }

        payload = _public_dashboard_payload(dashboard, public_widget_data)
        return success_response(payload, payload, 200)
    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e), 500)


@public_dashboard_bp.route("/<token>/data", methods=["GET"])
def get_public_dashboard_data(token):
    dashboard = mongo.db.dashboards.find_one(
        {"public_token": token, "is_public": True, "is_deleted": False}
    )
    if not dashboard:
        return error_response(
            "PUBLIC_TOKEN_NOT_FOUND",
            "Public dashboard not found or sharing disabled",
            404,
        )

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
                "generated_at": val.get("generated_at"),
            }

        payload = {
            "widget_data": serialize_doc(public_widget_data),
            "server_time": datetime.datetime.utcnow().isoformat(),
        }
        return success_response(payload, payload, 200)
    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e), 500)


# ----------------- SNAPSHOTS ENDPOINTS -----------------


@dashboard_bp.route("/<dashboard_id>/snapshots", methods=["POST"])
def create_snapshot(dashboard_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    try:
        res = dashboard_service.create_snapshot(dashboard_id, context["user_id"], context)
        if not res:
            return error_response("DASHBOARD_NOT_FOUND", "Dashboard not found", 404)

        serialized = serialize_doc(res)
        return success_response({"snapshot": serialized}, {"snapshot": serialized}, 201)
    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e), 500)


@dashboard_bp.route("/<dashboard_id>/snapshots", methods=["GET"])
def list_snapshots(dashboard_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    query = {"dashboard_id": d_oid, "is_deleted": False}
    total = mongo.db.dashboard_snapshots.count_documents(query)

    snapshots_cursor = mongo.db.dashboard_snapshots.find(query, {"data.widget_data": 0}).sort(
        "created_at", -1
    ).skip((page - 1) * per_page).limit(per_page)

    snapshots = []
    for snap in snapshots_cursor:
        creator_id = snap.get("created_by")
        if creator_id:
            user = mongo.db.users.find_one({"_id": ObjectId(creator_id) if ObjectId.is_valid(creator_id) else creator_id})
            if user:
                snap["created_by_user"] = {
                    "_id": str(user["_id"]),
                    "full_name": user.get("full_name") or user.get("name") or "Unknown",
                }
            else:
                snap["created_by_user"] = {"_id": str(creator_id), "full_name": "Unknown"}
        snapshots.append(snap)

    total_pages = (total + per_page - 1) // per_page if total > 0 else 0
    payload = {
        "snapshots": serialize_doc(snapshots),
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        },
    }
    return success_response(payload, payload, 200)


@dashboard_bp.route("/<dashboard_id>/snapshots/<snapshot_id>", methods=["GET"])
def get_snapshot(dashboard_id, snapshot_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    snap_oid = ObjectId(snapshot_id) if ObjectId.is_valid(snapshot_id) else snapshot_id
    snap = mongo.db.dashboard_snapshots.find_one({"_id": snap_oid, "is_deleted": False})
    if not snap:
        return error_response("SNAPSHOT_NOT_FOUND", "Snapshot not found", 404)

    payload = serialize_doc(snap)
    return success_response(payload, payload, 200)


@dashboard_bp.route("/<dashboard_id>/snapshots/<snapshot_id>", methods=["DELETE"])
def delete_snapshot(dashboard_id, snapshot_id):
    context = require_request_context()
    if not context:
        return error_response("UNAUTHORIZED", "Valid bearer token is required", 401)

    snap_oid = ObjectId(snapshot_id) if ObjectId.is_valid(snapshot_id) else snapshot_id
    snap = mongo.db.dashboard_snapshots.find_one({"_id": snap_oid, "is_deleted": False})
    if not snap:
        return error_response("SNAPSHOT_NOT_FOUND", "Snapshot not found", 404)

    mongo.db.dashboard_snapshots.update_one(
        {"_id": snap_oid},
        {"$set": {"is_deleted": True, "deleted_at": datetime.datetime.utcnow().isoformat()}},
    )
    return success_response({"message": "Snapshot deleted"}, {"message": "Snapshot deleted"}, 200)
