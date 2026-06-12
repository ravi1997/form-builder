from flask import Blueprint, request, jsonify, current_app, Response
from bson import ObjectId
import datetime
import json
from functools import wraps

from app.extensions import mongo, limiter
from app.services.auth_service import verify_api_key, decode_request_bearer_token

api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


def _api_key_required(f):
    """Decorator to require valid API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if not api_key:
            return jsonify({
                "status": "error",
                "code": "API_KEY_REQUIRED",
                "message": "API key is required"
            }), 401
        
        api_key_doc = verify_api_key(api_key)
        if not api_key_doc:
            return jsonify({
                "status": "error",
                "code": "INVALID_API_KEY",
                "message": "Invalid API key"
            }), 401
        
        if api_key_doc.get("status") != "active":
            return jsonify({
                "status": "error",
                "code": "API_KEY_INACTIVE",
                "message": "API key is inactive"
            }), 401
        
        # Add API key info to request context
        request.api_key = api_key_doc
        return f(*args, **kwargs)
    return decorated_function


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


@api_v1_bp.route("/health", methods=["GET"])
def health_check():
    """Public health check endpoint"""
    return _success_response({
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.datetime.utcnow().isoformat()
    })


@api_v1_bp.route("/forms", methods=["GET"])
@_api_key_required
@limiter.limit("60 per minute")
def list_forms():
    """List accessible forms"""
    api_key = request.api_key
    org_id = api_key.get("org_id")
    
    # Build query
    query = {
        "is_deleted": False,
        "production_branch": {"$ne": None}
    }
    
    # Filter by org if specified
    if org_id:
        query["org_id"] = ObjectId(org_id)
    
    # Get forms
    forms = list(mongo.db.forms.find(query)
        .sort("created_at", -1)
        .limit(100))  # Limit to prevent large responses
    
    # Format response
    formatted_forms = []
    for form in forms:
        # Get production commit
        production_commit_id = form.get("branches", {}).get(form.get("production_branch"))
        if not production_commit_id:
            continue
            
        commit = mongo.db.form_commits.find_one({
            "form_id": form["_id"],
            "commit_id": production_commit_id
        })
        
        if not commit:
            continue
        
        # Check access permissions
        access_config = commit.get("schema", {}).get("access", {})
        access_type = access_config.get("type", "public")
        
        # Skip if not public and API key doesn't match org
        if access_type != "public" and org_id and str(form.get("org_id")) != str(org_id):
            continue
        
        formatted_forms.append({
            "id": str(form["_id"]),
            "name": form["name"],
            "description": form.get("description", ""),
            "org_id": str(form["org_id"]),
            "project_id": str(form["project_id"]),
            "access_type": access_type,
            "created_at": form["created_at"],
            "updated_at": form["updated_at"]
        })
    
    return _success_response({"forms": formatted_forms})


@api_v1_bp.route("/forms/<form_id>", methods=["GET"])
@_api_key_required
@limiter.limit("60 per minute")
def get_form(form_id):
    """Get form details"""
    api_key = request.api_key
    org_id = api_key.get("org_id")
    
    form_oid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    form = mongo.db.forms.find_one({
        "_id": form_oid,
        "is_deleted": False,
        "production_branch": {"$ne": None}
    })
    
    if not form:
        return _error_response("FORM_NOT_FOUND", "Form not found", 404)
    
    # Get production commit
    production_commit_id = form.get("branches", {}).get(form.get("production_branch"))
    if not production_commit_id:
        return _error_response("FORM_NOT_PUBLISHED", "Form is not published", 400)
    
    commit = mongo.db.form_commits.find_one({
        "form_id": form["_id"],
        "commit_id": production_commit_id
    })
    
    if not commit:
        return _error_response("FORM_COMMIT_NOT_FOUND", "Form commit not found", 404)
    
    # Check access permissions
    access_config = commit.get("schema", {}).get("access", {})
    access_type = access_config.get("type", "public")
    
    # Check if access is allowed
    if access_type != "public":
        if not org_id or str(form.get("org_id")) != str(org_id):
            return _error_response("ACCESS_DENIED", "Access denied", 403)
    
    # Format response (exclude sensitive data)
    schema = commit.get("schema", {})
    response_data = {
        "id": str(form["_id"]),
        "name": form["name"],
        "description": form.get("description", ""),
        "org_id": str(form["org_id"]),
        "project_id": str(form["project_id"]),
        "ui": schema.get("ui", {}),
        "settings": {
            "allow_multiple_submissions": schema.get("settings", {}).get("allow_multiple_submissions", False),
            "require_login": schema.get("settings", {}).get("require_login", False),
            "expires_at": schema.get("settings", {}).get("expires_at")
        },
        "sections": schema.get("sections", []),
        "created_at": form["created_at"],
        "updated_at": form["updated_at"]
    }
    
    return _success_response(response_data)


@api_v1_bp.route("/forms/<form_id>/responses", methods=["POST"])
@_api_key_required
@limiter.limit("100 per minute")
def submit_form_response(form_id):
    """Submit a form response"""
    api_key = request.api_key
    org_id = api_key.get("org_id")
    
    form_oid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    form = mongo.db.forms.find_one({
        "_id": form_oid,
        "is_deleted": False,
        "production_branch": {"$ne": None}
    })
    
    if not form:
        return _error_response("FORM_NOT_FOUND", "Form not found", 404)
    
    # Get production commit
    production_commit_id = form.get("branches", {}).get(form.get("production_branch"))
    if not production_commit_id:
        return _error_response("FORM_NOT_PUBLISHED", "Form is not published", 400)
    
    commit = mongo.db.form_commits.find_one({
        "form_id": form["_id"],
        "commit_id": production_commit_id
    })
    
    if not commit:
        return _error_response("FORM_COMMIT_NOT_FOUND", "Form commit not found", 404)
    
    # Check access permissions
    access_config = commit.get("schema", {}).get("access", {})
    access_type = access_config.get("type", "public")
    
    # Check if access is allowed
    if access_type != "public":
        if not org_id or str(form.get("org_id")) != str(org_id):
            return _error_response("ACCESS_DENIED", "Access denied", 403)
    
    # Check form settings
    settings = commit.get("schema", {}).get("settings", {})
    
    # Check if expired
    expires_at = settings.get("expires_at")
    if expires_at and datetime.datetime.utcnow() > datetime.datetime.fromisoformat(expires_at.replace('Z', '+00:00')):
        return _error_response("FORM_EXPIRED", "Form has expired", 400)
    
    # Check response limit
    max_responses = settings.get("max_responses")
    if max_responses:
        response_count = mongo.db.form_responses.count_documents({
            "form_id": form["_id"],
            "status": "submitted"
        })
        if response_count >= max_responses:
            return _error_response("RESPONSE_LIMIT_REACHED", "Maximum response limit reached", 400)
    
    # Get and validate response data
    data = request.get_json() or {}
    answers = data.get("answers", {})
    
    if not isinstance(answers, dict):
        return _error_response("INVALID_ANSWERS", "Answers must be an object", 400)
    
    # Create response document
    response_id = ObjectId()
    now = datetime.datetime.utcnow()
    
    response_doc = {
        "_id": response_id,
        "form_id": form["_id"],
        "commit_id": production_commit_id,
        "org_id": form["org_id"],
        "project_id": form["project_id"],
        "respondent_id": None,  # Anonymous submission
        "respondent_email": data.get("respondent_email"),
        "session_id": data.get("session_id"),
        "status": "submitted",
        "is_anonymous": True,
        "is_legacy": False,
        "submission_number": 0,  # Will be updated below
        "answers": {},
        "repeat_groups": {},
        "metadata": {
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", ""),
            "platform": "api",
            "started_at": data.get("started_at", now.isoformat()),
            "completed_at": now.isoformat(),
            "time_taken_seconds": data.get("time_taken_seconds", 0),
            "offline_submitted": False
        },
        "edit_history": [],
        "created_at": now,
        "updated_at": now,
        "submitted_at": now,
        "is_deleted": False,
        "deleted_at": None
    }
    
    # Get submission number
    last_response = mongo.db.form_responses.find_one(
        {"form_id": form["_id"]},
        sort=[("submission_number", -1)]
    )
    response_doc["submission_number"] = (last_response.get("submission_number", 0) + 1) if last_response else 1
    
    # Process answers
    sections = commit.get("schema", {}).get("sections", [])
    for section in sections:
        process_section_answers(section, answers, response_doc)
    
    # Insert response
    mongo.db.form_responses.insert_one(response_doc)
    
    # Trigger webhooks if configured
    webhook_configs = commit.get("schema", {}).get("webhook_configs", [])
    if webhook_configs:
        # This would be implemented in notification service
        pass
    
    return _success_response({
        "response_id": str(response_id),
        "submission_number": response_doc["submission_number"],
        "submitted_at": now.isoformat()
    }, "Response submitted successfully", 201)


def process_section_answers(section, answers, response_doc, section_iteration=0):
    """Process answers for a section and its subsections"""
    section_id = section.get("id")
    
    # Process subsections
    for subsection in section.get("sub_sections", []):
        subsection_id = subsection.get("id")
        
        # Check if subsection is repeatable and has multiple iterations
        subsection_answers = answers.get(subsection_id)
        if isinstance(subsection_answers, list):
            # Multiple iterations
            for iteration, iteration_answers in enumerate(subsection_answers):
                process_subsection_answers(subsection, iteration_answers, response_doc, iteration)
        else:
            # Single iteration
            process_subsection_answers(subsection, subsection_answers or {}, response_doc, 0)


def process_subsection_answers(subsection, answers, response_doc, iteration=0):
    """Process answers for a subsection"""
    subsection_id = subsection.get("id")
    
    # Process questions
    for question in subsection.get("questions", []):
        question_id = question.get("id")
        answer_value = answers.get(question_id)
        
        if answer_value is not None:
            response_doc["answers"][question_id] = {
                "value": answer_value,
                "display_value": str(answer_value),
                "file_ids": [],
                "answered_at": datetime.datetime.utcnow().isoformat(),
                "iteration_index": iteration
            }


@api_v1_bp.route("/forms/<form_id>/responses", methods=["GET"])
@_api_key_required
@limiter.limit("60 per minute")
def list_form_responses(form_id):
    """List form responses"""
    api_key = request.api_key
    org_id = api_key.get("org_id")
    
    form_oid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    form = mongo.db.forms.find_one({
        "_id": form_oid,
        "is_deleted": False
    })
    
    if not form:
        return _error_response("FORM_NOT_FOUND", "Form not found", 404)
    
    # Check org access
    if org_id and str(form.get("org_id")) != str(org_id):
        return _error_response("ACCESS_DENIED", "Access denied", 403)
    
    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)  # Max 100 per page
    status_filter = request.args.get("status", "submitted")
    
    # Build query
    query = {
        "form_id": form["_id"],
        "status": status_filter,
        "is_deleted": False
    }
    
    # Get responses
    total = mongo.db.form_responses.count_documents(query)
    responses = list(mongo.db.form_responses.find(query)
        .sort("submitted_at", -1)
        .skip((page - 1) * per_page)
        .limit(per_page))
    
    # Format response
    formatted_responses = []
    for response in responses:
        formatted_responses.append({
            "id": str(response["_id"]),
            "form_id": str(response["form_id"]),
            "submission_number": response["submission_number"],
            "status": response["status"],
            "respondent_email": response.get("respondent_email"),
            "submitted_at": response["submitted_at"],
            "metadata": response.get("metadata", {})
        })
    
    return _success_response({
        "responses": formatted_responses,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page if total > 0 else 0
        }
    })


@api_v1_bp.route("/forms/<form_id>/responses/<response_id>", methods=["GET"])
@_api_key_required
@limiter.limit("60 per minute")
def get_form_response(form_id, response_id):
    """Get a specific form response"""
    api_key = request.api_key
    org_id = api_key.get("org_id")
    
    form_oid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    response_oid = ObjectId(response_id) if ObjectId.is_valid(response_id) else response_id
    
    form = mongo.db.forms.find_one({
        "_id": form_oid,
        "is_deleted": False
    })
    
    if not form:
        return _error_response("FORM_NOT_FOUND", "Form not found", 404)
    
    # Check org access
    if org_id and str(form.get("org_id")) != str(org_id):
        return _error_response("ACCESS_DENIED", "Access denied", 403)
    
    response = mongo.db.form_responses.find_one({
        "_id": response_oid,
        "form_id": form["_id"],
        "is_deleted": False
    })
    
    if not response:
        return _error_response("RESPONSE_NOT_FOUND", "Response not found", 404)
    
    # Format response
    response_data = {
        "id": str(response["_id"]),
        "form_id": str(response["form_id"]),
        "submission_number": response["submission_number"],
        "status": response["status"],
        "respondent_email": response.get("respondent_email"),
        "answers": response.get("answers", {}),
        "repeat_groups": response.get("repeat_groups", {}),
        "metadata": response.get("metadata", {}),
        "submitted_at": response["submitted_at"]
    }
    
    return _success_response(response_data)


@api_v1_bp.route("/analyses", methods=["GET"])
@_api_key_required
@limiter.limit("60 per minute")
def list_analyses():
    """List accessible analyses"""
    api_key = request.api_key
    org_id = api_key.get("org_id")
    
    # Build query
    query = {
        "is_deleted": False
    }
    
    # Filter by org if specified
    if org_id:
        query["org_id"] = ObjectId(org_id)
    
    # Get analyses
    analyses = list(mongo.db.analyses.find(query)
        .sort("created_at", -1)
        .limit(50))
    
    # Format response
    formatted_analyses = []
    for analysis in analyses:
        formatted_analyses.append({
            "id": str(analysis["_id"]),
            "name": analysis["name"],
            "description": analysis.get("description", ""),
            "org_id": str(analysis["org_id"]),
            "project_id": str(analysis["project_id"]),
            "status": analysis["status"],
            "created_at": analysis["created_at"],
            "updated_at": analysis["updated_at"]
        })
    
    return _success_response({"analyses": formatted_analyses})


@api_v1_bp.route("/analyses/<analysis_id>/results", methods=["GET"])
@_api_key_required
@limiter.limit("60 per minute")
def get_analysis_results(analysis_id):
    """Get latest analysis results"""
    api_key = request.api_key
    org_id = api_key.get("org_id")
    
    analysis_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
    analysis = mongo.db.analyses.find_one({
        "_id": analysis_oid,
        "is_deleted": False
    })
    
    if not analysis:
        return _error_response("ANALYSIS_NOT_FOUND", "Analysis not found", 404)
    
    # Check org access
    if org_id and str(analysis.get("org_id")) != str(org_id):
        return _error_response("ACCESS_DENIED", "Access denied", 403)
    
    # Get latest completed run
    latest_run = mongo.db.analysis_runs.find_one(
        {
            "analysis_id": analysis["_id"],
            "status": "completed"
        },
        sort=[("created_at", -1)]
    )
    
    if not latest_run:
        return _error_response("NO_RESULTS", "No completed analysis run found", 404)
    
    # Get results
    result_ids = latest_run.get("result_ids", {})
    if not result_ids:
        return _error_response("NO_RESULTS", "No results found for this analysis", 404)
    
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
    
    return _success_response({
        "analysis_id": analysis_id,
        "run_id": str(latest_run["_id"]),
        "results": results,
        "completed_at": latest_run.get("completed_at")
    })


@api_v1_bp.route("/dashboards/<dashboard_id>", methods=["GET"])
@_api_key_required
@limiter.limit("60 per minute")
def get_dashboard(dashboard_id):
    """Get dashboard details"""
    api_key = request.api_key
    org_id = api_key.get("org_id")
    
    dashboard_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    dashboard = mongo.db.dashboards.find_one({
        "_id": dashboard_oid,
        "is_deleted": False
    })
    
    if not dashboard:
        return _error_response("DASHBOARD_NOT_FOUND", "Dashboard not found", 404)
    
    # Check access
    if dashboard.get("is_public"):
        # Public dashboard - anyone can access
        pass
    elif org_id and str(dashboard.get("org_id")) == str(org_id):
        # Org access
        pass
    else:
        return _error_response("ACCESS_DENIED", "Access denied", 403)
    
    # Format response
    response_data = {
        "id": str(dashboard["_id"]),
        "name": dashboard["name"],
        "description": dashboard.get("description", ""),
        "org_id": str(dashboard["org_id"]),
        "project_id": str(dashboard["project_id"]),
        "is_public": dashboard.get("is_public", False),
        "canvas": dashboard.get("canvas", {}),
        "settings": dashboard.get("settings", {}),
        "created_at": dashboard["created_at"],
        "updated_at": dashboard["updated_at"]
    }
    
    return _success_response(response_data)


@api_v1_bp.route("/dashboards/<dashboard_id>/data", methods=["GET"])
@_api_key_required
@limiter.limit("60 per minute")
def get_dashboard_data(dashboard_id):
    """Get dashboard data"""
    api_key = request.api_key
    org_id = api_key.get("org_id")
    
    dashboard_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
    dashboard = mongo.db.dashboards.find_one({
        "_id": dashboard_oid,
        "is_deleted": False
    })
    
    if not dashboard:
        return _error_response("DASHBOARD_NOT_FOUND", "Dashboard not found", 404)
    
    # Check access
    if dashboard.get("is_public"):
        # Public dashboard - anyone can access
        pass
    elif org_id and str(dashboard.get("org_id")) == str(org_id):
        # Org access
        pass
    else:
        return _error_response("ACCESS_DENIED", "Access denied", 403)
    
    # Get filter state
    filter_state_raw = request.args.get("filter_state")
    filter_state = {}
    if filter_state_raw:
        try:
            filter_state = json.loads(filter_state_raw)
        except Exception:
            return _error_response("INVALID_FILTER_STATE", "Invalid filter_state JSON", 400)
    
    # Resolve widget data (this would use dashboard_service)
    # For now, return empty data
    widget_data = {}
    
    return _success_response({
        "dashboard_id": dashboard_id,
        "canvas": dashboard.get("canvas", {}),
        "widget_data": widget_data
    })