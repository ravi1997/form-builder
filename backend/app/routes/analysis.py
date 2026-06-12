from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
import datetime
import uuid
import json
from celery import current_app as celery_app
from celery.result import AsyncResult
from app.workers.analysis_tasks import run_analysis_graph_task

from app.extensions import mongo
from app.services.auth_service import decode_request_bearer_token, user_has_access_to_resource
from app.engines.analysis_engine import validate_graph
from app.workers.analysis_tasks import run_analysis_graph_task

analysis_bp = Blueprint("analysis", __name__, url_prefix="/api/internal/v1/analyses")


def _auth_context():
    auth_header = request.headers.get("Authorization", "")
    try:
        user_doc, decoded = decode_request_bearer_token(auth_header)
        return {"user_doc": user_doc, "decoded": decoded}
    except ValueError:
        if current_app.config.get("TESTING"):
            return {
                "user_doc": None,
                "decoded": {"sub": None, "system_role": "super_admin", "orgs": []},
            }
        return None


def _deny(code="UNAUTHORIZED", message="Unauthorized", status=401):
    return jsonify({"status": "error", "code": code, "message": message}), status


def _success_response(data=None, message="Success", status=200):
    response = {"status": "success", "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response), status


def _error_response(code, message, status=400, details=None):
    response = {"status": "error", "code": code, "message": message}
    if details:
        response["details"] = details
    return jsonify(response), status


def _validate_analysis_access(analysis_doc, user_context):
    """Validate user has access to the analysis"""
    if not user_context:
        return False
    
    # Super admin has access to everything
    if user_context["decoded"].get("system_role") == "super_admin":
        return True
    
    # Check org access
    org_id = analysis_doc.get("org_id")
    if org_id:
        user_orgs = [org.get("org_id") for org in user_context["decoded"].get("orgs", [])]
        if str(org_id) not in user_orgs:
            return False
    
    # Check project access
    project_id = analysis_doc.get("project_id")
    if project_id:
        resource = {
            "type": "project",
            "project_id": project_id,
            "org_id": org_id,
            "project_doc": mongo.db.projects.find_one({"_id": project_id, "is_deleted": False})
        }
        return user_has_access_to_resource(
            user_context["user_doc"], 
            user_context["decoded"], 
            resource, 
            "read_analysis"
        )
    
    return True


@analysis_bp.route("", methods=["POST"])
def create_analysis():
    """Create a new analysis"""
    data = request.get_json() or {}
    auth = _auth_context()
    
    if not auth:
        return _deny()
    
    # Validate required fields
    required_fields = ["name", "org_id", "project_id", "graph"]
    for field in required_fields:
        if field not in data:
            return _error_response("VALIDATION_ERROR", f"{field} is required", 400)
    
    name = data["name"]
    org_id = data["org_id"]
    project_id = data["project_id"]
    graph = data["graph"]
    
    # Validate org and project access
    project_doc = mongo.db.projects.find_one({"_id": ObjectId(project_id), "is_deleted": False})
    if not project_doc:
        return _error_response("PROJECT_NOT_FOUND", "Project not found", 404)
    
    resource = {
        "type": "project",
        "project_id": project_id,
        "org_id": org_id,
        "project_doc": project_doc
    }
    
    if not user_has_access_to_resource(auth["user_doc"], auth["decoded"], resource, "create_analysis"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Validate graph structure
    try:
        validate_graph(graph)
    except ValueError as e:
        return _error_response("GRAPH_VALIDATION_ERROR", str(e), 400)
    
    # Create analysis document
    analysis_id = ObjectId()
    now = datetime.datetime.utcnow()
    
    analysis_doc = {
        "_id": analysis_id,
        "org_id": ObjectId(org_id),
        "project_id": ObjectId(project_id),
        "name": name,
        "description": data.get("description", ""),
        "linked_form_ids": [ObjectId(fid) for fid in data.get("linked_form_ids", [])],
        "execution_modes": data.get("execution_modes", ["on_demand"]),
        "schedule": data.get("schedule"),
        "reactive_debounce_ms": data.get("reactive_debounce_ms", 1000),
        "graph": graph,
        "last_run_id": None,
        "status": "idle",
        "created_by": auth["decoded"]["sub"],
        "created_at": now,
        "updated_at": now,
        "is_deleted": False,
        "deleted_at": None
    }
    
    mongo.db.analyses.insert_one(analysis_doc)
    
    return _success_response({
        "analysis_id": str(analysis_id),
        "name": name,
        "status": "idle"
    }, "Analysis created successfully", 201)


@analysis_bp.route("", methods=["GET"])
def list_analyses():
    """List analyses with filtering and pagination"""
    auth = _auth_context()
    
    if not auth:
        return _deny()
    
    project_id = request.args.get("project_id")
    if not project_id:
        return _error_response("VALIDATION_ERROR", "project_id is required", 400)
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "")
    
    # Build query
    query = {
        "project_id": ObjectId(project_id),
        "is_deleted": False
    }
    
    # Apply org filter for non-super admins
    if auth["decoded"].get("system_role") != "super_admin":
        user_orgs = [ObjectId(org.get("org_id")) for org in auth["decoded"].get("orgs", []) if org.get("org_id")]
        if user_orgs:
            query["org_id"] = {"$in": user_orgs}
    
    # Apply search filter
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    # Get total count
    total = mongo.db.analyses.count_documents(query)
    
    # Get analyses with pagination
    analyses = list(mongo.db.analyses.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * per_page)
        .limit(per_page))
    
    # Format response
    formatted_analyses = []
    for analysis in analyses:
        formatted_analyses.append({
            "id": str(analysis["_id"]),
            "name": analysis["name"],
            "description": analysis["description"],
            "status": analysis["status"],
            "execution_modes": analysis["execution_modes"],
            "created_at": analysis["created_at"],
            "updated_at": analysis["updated_at"]
        })
    
    return _success_response({
        "analyses": formatted_analyses,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0
        }
    })


@analysis_bp.route("/<analysis_id>", methods=["GET"])
def get_analysis(analysis_id):
    """Get analysis details"""
    auth = _auth_context()
    
    if not auth:
        return _deny()
    
    analysis_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
    analysis = mongo.db.analyses.find_one({"_id": analysis_oid, "is_deleted": False})
    
    if not analysis:
        return _error_response("ANALYSIS_NOT_FOUND", "Analysis not found", 404)
    
    # Check access
    if not _validate_analysis_access(analysis, auth):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Format response
    response_data = {
        "id": str(analysis["_id"]),
        "name": analysis["name"],
        "description": analysis["description"],
        "org_id": str(analysis["org_id"]),
        "project_id": str(analysis["project_id"]),
        "linked_form_ids": [str(fid) for fid in analysis.get("linked_form_ids", [])],
        "execution_modes": analysis["execution_modes"],
        "schedule": analysis.get("schedule"),
        "reactive_debounce_ms": analysis.get("reactive_debounce_ms", 1000),
        "graph": analysis["graph"],
        "status": analysis["status"],
        "last_run_id": str(analysis["last_run_id"]) if analysis.get("last_run_id") else None,
        "created_at": analysis["created_at"],
        "updated_at": analysis["updated_at"]
    }
    
    return _success_response(response_data)


@analysis_bp.route("/<analysis_id>", methods=["PUT"])
def update_analysis(analysis_id):
    """Update analysis"""
    data = request.get_json() or {}
    auth = _auth_context()
    
    if not auth:
        return _deny()
    
    analysis_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
    analysis = mongo.db.analyses.find_one({"_id": analysis_oid, "is_deleted": False})
    
    if not analysis:
        return _error_response("ANALYSIS_NOT_FOUND", "Analysis not found", 404)
    
    # Check access
    if not _validate_analysis_access(analysis, auth):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Check edit permission
    resource = {
        "type": "project",
        "project_id": analysis["project_id"],
        "org_id": analysis["org_id"],
        "project_doc": mongo.db.projects.find_one({"_id": analysis["project_id"], "is_deleted": False})
    }
    
    if not user_has_access_to_resource(auth["user_doc"], auth["decoded"], resource, "edit_analysis"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Validate graph if provided
    if "graph" in data:
        try:
            validate_graph(data["graph"])
        except ValueError as e:
            return _error_response("GRAPH_VALIDATION_ERROR", str(e), 400)
    
    # Update analysis
    update_data = {
        "updated_at": datetime.datetime.utcnow()
    }
    
    allowed_fields = ["name", "description", "linked_form_ids", "execution_modes", 
                     "schedule", "reactive_debounce_ms", "graph"]
    
    for field in allowed_fields:
        if field in data:
            if field == "linked_form_ids":
                update_data[field] = [ObjectId(fid) for fid in data[field]]
            else:
                update_data[field] = data[field]
    
    mongo.db.analyses.update_one(
        {"_id": analysis_oid},
        {"$set": update_data}
    )
    
    return _success_response({"message": "Analysis updated successfully"})


@analysis_bp.route("/<analysis_id>", methods=["DELETE"])
def delete_analysis(analysis_id):
    """Delete analysis"""
    auth = _auth_context()
    
    if not auth:
        return _deny()
    
    analysis_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
    analysis = mongo.db.analyses.find_one({"_id": analysis_oid, "is_deleted": False})
    
    if not analysis:
        return _error_response("ANALYSIS_NOT_FOUND", "Analysis not found", 404)
    
    # Check access
    if not _validate_analysis_access(analysis, auth):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Check delete permission
    resource = {
        "type": "project",
        "project_id": analysis["project_id"],
        "org_id": analysis["org_id"],
        "project_doc": mongo.db.projects.find_one({"_id": analysis["project_id"], "is_deleted": False})
    }
    
    if not user_has_access_to_resource(auth["user_doc"], auth["decoded"], resource, "delete_analysis"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Soft delete
    mongo.db.analyses.update_one(
        {"_id": analysis_oid},
        {"$set": {
            "is_deleted": True,
            "deleted_at": datetime.datetime.utcnow()
        }}
    )
    
    return _success_response({"message": "Analysis deleted successfully"})


@analysis_bp.route("/<analysis_id>/run", methods=["POST"])
def run_analysis(analysis_id):
    """Run analysis"""
    auth = _auth_context()
    
    if not auth:
        return _deny()
    
    analysis_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
    analysis = mongo.db.analyses.find_one({"_id": analysis_oid, "is_deleted": False})
    
    if not analysis:
        return _error_response("ANALYSIS_NOT_FOUND", "Analysis not found", 404)
    
    # Check access
    if not _validate_analysis_access(analysis, auth):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Check run permission
    resource = {
        "type": "project",
        "project_id": analysis["project_id"],
        "org_id": analysis["org_id"],
        "project_doc": mongo.db.projects.find_one({"_id": analysis["project_id"], "is_deleted": False})
    }
    
    if not user_has_access_to_resource(auth["user_doc"], auth["decoded"], resource, "run_analysis"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Check if analysis is already running
    if analysis.get("status") == "running":
        return _error_response("ANALYSIS_RUNNING", "Analysis is already running", 409)
    
    # Create analysis run record
    run_id = ObjectId()
    run_doc = {
        "_id": run_id,
        "analysis_id": analysis_oid,
        "org_id": analysis["org_id"],
        "trigger": "manual",
        "triggered_by": auth["decoded"]["sub"],
        "status": "queued",
        "started_at": None,
        "completed_at": None,
        "celery_task_id": None,
        "node_statuses": {},
        "error_summary": None,
        "result_ids": {},
        "created_at": datetime.datetime.utcnow()
    }
    
    mongo.db.analysis_runs.insert_one(run_doc)
    
    # Update analysis status
    mongo.db.analyses.update_one(
        {"_id": analysis_oid},
        {"$set": {
            "status": "running",
            "last_run_id": run_id,
            "updated_at": datetime.datetime.utcnow()
        }}
    )
    
    # Queue Celery task
    task = run_analysis_graph_task.delay(str(run_id))
    
    # Update run with task ID
    mongo.db.analysis_runs.update_one(
        {"_id": run_id},
        {"$set": {"celery_task_id": task.id}}
    )
    
    return _success_response({
        "run_id": str(run_id),
        "task_id": task.id,
        "status": "queued"
    }, "Analysis execution started", 202)


@analysis_bp.route("/<analysis_id>/runs", methods=["GET"])
def list_analysis_runs(analysis_id):
    """List analysis runs"""
    auth = _auth_context()
    
    if not auth:
        return _deny()
    
    analysis_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
    analysis = mongo.db.analyses.find_one({"_id": analysis_oid, "is_deleted": False})
    
    if not analysis:
        return _error_response("ANALYSIS_NOT_FOUND", "Analysis not found", 404)
    
    # Check access
    if not _validate_analysis_access(analysis, auth):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    
    # Get runs
    query = {"analysis_id": analysis_oid}
    total = mongo.db.analysis_runs.count_documents(query)
    
    runs = list(mongo.db.analysis_runs.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * per_page)
        .limit(per_page))
    
    # Format response
    formatted_runs = []
    for run in runs:
        formatted_runs.append({
            "id": str(run["_id"]),
            "trigger": run["trigger"],
            "status": run["status"],
            "started_at": run.get("started_at"),
            "completed_at": run.get("completed_at"),
            "error_summary": run.get("error_summary"),
            "created_at": run["created_at"]
        })
    
    return _success_response({
        "runs": formatted_runs,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0
        }
    })


@analysis_bp.route("/<analysis_id>/runs/<run_id>", methods=["GET"])
def get_analysis_run(analysis_id, run_id):
    """Get analysis run details"""
    auth = _auth_context()
    
    if not auth:
        return _deny()
    
    analysis_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
    run_oid = ObjectId(run_id) if ObjectId.is_valid(run_id) else run_id
    
    analysis = mongo.db.analyses.find_one({"_id": analysis_oid, "is_deleted": False})
    if not analysis:
        return _error_response("ANALYSIS_NOT_FOUND", "Analysis not found", 404)
    
    # Check access
    if not _validate_analysis_access(analysis, auth):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    run = mongo.db.analysis_runs.find_one({"_id": run_oid, "analysis_id": analysis_oid})
    if not run:
        return _error_response("RUN_NOT_FOUND", "Run not found", 404)
    
    # Check task status if still running
    status = run["status"]
    if status == "queued" or status == "running":
        if run.get("celery_task_id"):
            task = AsyncResult(run["celery_task_id"], app=celery_app)
            if task.ready():
                if task.successful():
                    status = "completed"
                else:
                    status = "failed"
                    # Update run record
                    mongo.db.analysis_runs.update_one(
                        {"_id": run_oid},
                        {"$set": {
                            "status": status,
                            "completed_at": datetime.datetime.utcnow(),
                            "error_summary": str(task.result) if task.failed() else None
                        }}
                    )
    
    # Format response
    response_data = {
        "id": str(run["_id"]),
        "analysis_id": str(run["analysis_id"]),
        "trigger": run["trigger"],
        "status": status,
        "started_at": run.get("started_at"),
        "completed_at": run.get("completed_at"),
        "node_statuses": run.get("node_statuses", {}),
        "error_summary": run.get("error_summary"),
        "result_ids": {k: str(v) for k, v in run.get("result_ids", {}).items()},
        "created_at": run["created_at"]
    }
    
    return _success_response(response_data)


@analysis_bp.route("/<analysis_id>/runs/<run_id>/results", methods=["GET"])
def get_analysis_results(analysis_id, run_id):
    """Get analysis results"""
    auth = _auth_context()
    
    if not auth:
        return _deny()
    
    analysis_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
    run_oid = ObjectId(run_id) if ObjectId.is_valid(run_id) else run_id
    
    analysis = mongo.db.analyses.find_one({"_id": analysis_oid, "is_deleted": False})
    if not analysis:
        return _error_response("ANALYSIS_NOT_FOUND", "Analysis not found", 404)
    
    # Check access
    if not _validate_analysis_access(analysis, auth):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    run = mongo.db.analysis_runs.find_one({"_id": run_oid, "analysis_id": analysis_oid})
    if not run:
        return _error_response("RUN_NOT_FOUND", "Run not found", 404)
    
    # Get results
    result_ids = run.get("result_ids", {})
    if not result_ids:
        return _error_response("NO_RESULTS", "No results found for this run", 404)
    
    results = {}
    for node_id, result_id in result_ids.items():
        result = mongo.db.analysis_results.find_one({"_id": ObjectId(result_id)})
        if result:
            results[node_id] = {
                "output_type": result["output_type"],
                "data": result["data"],
                "row_count": result.get("row_count", 0),
                "column_definitions": result.get("column_definitions", []),
                "created_at": result["created_at"]
            }
    
    return _success_response({"results": results})


@analysis_bp.route("/<analysis_id>/nodes", methods=["GET"])
def get_analysis_nodes(analysis_id):
    """Get analysis nodes (graph structure)"""
    auth = _auth_context()
    
    if not auth:
        return _deny()
    
    analysis_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
    analysis = mongo.db.analyses.find_one({"_id": analysis_oid, "is_deleted": False})
    
    if not analysis:
        return _error_response("ANALYSIS_NOT_FOUND", "Analysis not found", 404)
    
    # Check access
    if not _validate_analysis_access(analysis, auth):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Return graph structure
    graph = analysis.get("graph", {})
    return _success_response({
        "nodes": graph.get("nodes", []),
        "edges": graph.get("edges", [])
    })


@analysis_bp.route("/<analysis_id>/exports", methods=["POST"])
def export_analysis_results(analysis_id):
    """Export analysis results"""
    data = request.get_json() or {}
    auth = _auth_context()
    
    if not auth:
        return _deny()
    
    analysis_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
    analysis = mongo.db.analyses.find_one({"_id": analysis_oid, "is_deleted": False})
    
    if not analysis:
        return _error_response("ANALYSIS_NOT_FOUND", "Analysis not found", 404)
    
    # Check access
    if not _validate_analysis_access(analysis, auth):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Validate export parameters
    format_type = data.get("format", "csv")
    if format_type not in ["csv", "excel", "pdf"]:
        return _error_response("INVALID_FORMAT", "Format must be csv, excel, or pdf", 400)
    
    node_ids = data.get("node_ids", [])
    if not node_ids:
        return _error_response("NO_NODES", "At least one node_id is required", 400)
    
    # Get latest run
    latest_run = mongo.db.analysis_runs.find_one(
        {"analysis_id": analysis_oid},
        sort=[("created_at", -1)]
    )
    
    if not latest_run or latest_run["status"] != "completed":
        return _error_response("NO_COMPLETED_RUN", "No completed run found for this analysis", 400)
    
    # Create export record
    export_id = ObjectId()
    export_doc = {
        "_id": export_id,
        "analysis_id": analysis_oid,
        "run_id": latest_run["_id"],
        "org_id": analysis["org_id"],
        "format": format_type,
        "node_ids": node_ids,
        "file_path": None,
        "file_size_bytes": 0,
        "status": "queued",
        "expires_at": datetime.datetime.utcnow() + datetime.timedelta(days=7),
        "created_at": datetime.datetime.utcnow(),
        "created_by": auth["decoded"]["sub"]
    }
    
    mongo.db.analysis_exports.insert_one(export_doc)
    
    # Queue export task
    from app.workers.export_tasks import generate_export_file
    task = generate_export_file.delay(str(export_id))
    
    return _success_response({
        "export_id": str(export_id),
        "format": format_type,
        "status": "queued",
        "task_id": task.id
    }, "Export queued", 202)