from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
from app.extensions import mongo
from app.engines.form_engine import create_commit, create_branch, three_way_merge
from app.services.quota_service import enforce_org_quota
from app.services.auth_service import decode_request_bearer_token, user_has_access_to_resource, check_permission
from app.services.form_service import FormService
from app.services.merge_conflict_resolver import MergeConflictResolver
from app.models.form_models import (
    BranchCreateRequest, BranchDeleteRequest, MergeRequest, TagCreateRequest, 
    PublishRequest, MergeConflictResolution
)
import datetime

forms_bp = Blueprint("forms", __name__, url_prefix="/api/internal/v1/forms")


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

import re

def validate_custom_css(custom_css):
    if not isinstance(custom_css, str):
        raise ValueError("custom_css must be a string")
    if len(custom_css) > 10000:
        raise ValueError("custom_css exceeds size limit of 10000 characters")
    lower_css = custom_css.lower()
    if "<script" in lower_css or "javascript:" in lower_css or "</script>" in lower_css or "<html" in lower_css or "<body" in lower_css:
        raise ValueError("custom_css contains forbidden HTML/script tags")

def validate_notifications_settings(notifications):
    if not isinstance(notifications, dict):
        raise ValueError("notifications must be an object")
    
    # 1. Email Alerts
    email_alerts = notifications.get("email_alerts")
    if email_alerts is not None:
        if not isinstance(email_alerts, dict):
            raise ValueError("email_alerts must be an object")
        enabled = email_alerts.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("email_alerts.enabled must be a boolean")
        if enabled:
            trigger_event = email_alerts.get("trigger_event", "on_submission")
            if trigger_event not in ["on_submission", "on_first_save"]:
                raise ValueError("email_alerts.trigger_event must be 'on_submission' or 'on_first_save'")
            recipients = email_alerts.get("recipients")
            if not isinstance(recipients, list):
                raise ValueError("email_alerts.recipients must be an array")
            if len(recipients) > 20:
                raise ValueError("email_alerts.recipients cannot contain more than 20 email addresses")
            email_regex = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
            for email in recipients:
                if not isinstance(email, str) or not email_regex.match(email):
                    raise ValueError(f"Invalid email address: {email}")
            if not isinstance(email_alerts.get("include_payload", True), bool):
                raise ValueError("email_alerts.include_payload must be a boolean")
            if not isinstance(email_alerts.get("include_attachments", False), bool):
                raise ValueError("email_alerts.include_attachments must be a boolean")

    # 2. Webhook Delivery
    webhook_delivery = notifications.get("webhook_delivery")
    if webhook_delivery is not None:
        if not isinstance(webhook_delivery, dict):
            raise ValueError("webhook_delivery must be an object")
        enabled = webhook_delivery.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("webhook_delivery.enabled must be a boolean")
        if enabled:
            url = webhook_delivery.get("url")
            if not isinstance(url, str):
                raise ValueError("webhook_delivery.url must be a string")
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError("webhook_delivery.url must use http:// or https:// protocol")
            
            # SSRF check
            parsed_url = url.lower()
            host_match = re.search(r"https?://([^/:]+)", parsed_url)
            if host_match:
                host = host_match.group(1)
                if host == "localhost" or host == "127.0.0.1" or host.endswith(".local"):
                    raise ValueError("webhook_delivery.url cannot point to a local hostname or IP address")
                if host.startswith("192.168.") or host.startswith("10.") or host.startswith("169.254."):
                    raise ValueError("webhook_delivery.url cannot point to a private IP address")
                if host.startswith("172."):
                    parts = host.split(".")
                    if len(parts) >= 2 and parts[1].isdigit():
                        second_octet = int(parts[1])
                        if 16 <= second_octet <= 31:
                            raise ValueError("webhook_delivery.url cannot point to a private IP address")
            
            secret = webhook_delivery.get("secret")
            if secret is not None:
                if not isinstance(secret, str):
                    raise ValueError("webhook_delivery.secret must be a string")
                if len(secret) > 128:
                    raise ValueError("webhook_delivery.secret cannot exceed 128 characters")
            
            content_type = webhook_delivery.get("content_type", "application/json")
            if content_type not in ["application/json", "application/x-www-form-urlencoded"]:
                raise ValueError("webhook_delivery.content_type must be 'application/json' or 'application/x-www-form-urlencoded'")

    # 3. Internal Recipients
    internal_recipients = notifications.get("internal_recipients")
    if internal_recipients is not None:
        if not isinstance(internal_recipients, dict):
            raise ValueError("internal_recipients must be an object")
        enabled = internal_recipients.get("enabled", False)
        if not isinstance(enabled, bool):
            raise ValueError("internal_recipients.enabled must be a boolean")
        if enabled:
            user_ids = internal_recipients.get("user_ids")
            if not isinstance(user_ids, list):
                raise ValueError("internal_recipients.user_ids must be an array")
            for uid in user_ids:
                if not isinstance(uid, str) or not re.match(r"^[0-9a-fA-F]{24}$", uid):
                    raise ValueError(f"Invalid user_id format: {uid}")
            
            team_ids = internal_recipients.get("team_ids")
            if not isinstance(team_ids, list):
                raise ValueError("internal_recipients.team_ids must be an array")
            for tid in team_ids:
                if not isinstance(tid, str):
                    raise ValueError("internal_recipients.team_ids must contain only strings")

    # 4. Failure Handling
    failure_handling = notifications.get("failure_handling")
    if failure_handling is not None:
        if not isinstance(failure_handling, dict):
            raise ValueError("failure_handling must be an object")
        retry_attempts = failure_handling.get("retry_attempts", 3)
        if not isinstance(retry_attempts, int) or not (0 <= retry_attempts <= 5):
            raise ValueError("failure_handling.retry_attempts must be an integer between 0 and 5")
        if not isinstance(failure_handling.get("alert_owner_on_failure", True), bool):
            raise ValueError("failure_handling.alert_owner_on_failure must be a boolean")

def validate_analytics_settings(analytics):
    if not isinstance(analytics, dict):
        raise ValueError("analytics settings must be an object")
    
    enabled = analytics.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError("analytics.enabled must be a boolean")
        
    start_event_type = analytics.get("start_event_type", "first_interaction")
    if start_event_type not in ["form_load", "first_interaction", "first_input"]:
        raise ValueError("analytics.start_event_type must be 'form_load', 'first_interaction', or 'first_input'")
        
    end_event_type = analytics.get("end_event_type", "submit_success")
    if end_event_type not in ["submit_success", "submit_attempt"]:
        raise ValueError("analytics.end_event_type must be 'submit_success' or 'submit_attempt'")
        
    drop_off_enabled = analytics.get("drop_off_enabled", True)
    if not isinstance(drop_off_enabled, bool):
        raise ValueError("analytics.drop_off_enabled must be a boolean")
        
    timing_enabled = analytics.get("timing_enabled", True)
    if not isinstance(timing_enabled, bool):
        raise ValueError("analytics.timing_enabled must be a boolean")
        
    utm_capture_enabled = analytics.get("utm_capture_enabled", True)
    if not isinstance(utm_capture_enabled, bool):
        raise ValueError("analytics.utm_capture_enabled must be a boolean")

@forms_bp.route("/presets", methods=["GET"])
def get_presets():
    presets = [
        {
            "id": "sleek_dark",
            "name": "Sleek Dark",
            "description": "A premium, high-contrast dark theme.",
            "tokens": {
                "primary_color": "#BB86FC",
                "background_color": "#121212",
                "font_family": "Inter",
                "border_radius": 8,
                "input_style": "filled"
            },
            "branding": {},
            "custom_css": "/* Sleek Dark Presets */\n.form-container {\n  background-color: #121212;\n  color: #FFFFFF;\n}\n.form-input {\n  background-color: #1E1E1E;\n  color: #FFFFFF;\n  border-color: #BB86FC;\n}"
        },
        {
            "id": "glassmorphism",
            "name": "Glassmorphism",
            "description": "Modern frosted-glass look with soft backgrounds.",
            "tokens": {
                "primary_color": "#E91E63",
                "background_color": "#F0F3F6",
                "font_family": "Outfit",
                "border_radius": 16,
                "input_style": "outlined"
            },
            "branding": {},
            "custom_css": "/* Glassmorphism Presets */\n.form-container {\n  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n}\n.form-card {\n  background: rgba(255, 255, 255, 0.25);\n  backdrop-filter: blur(4px);\n  -webkit-backdrop-filter: blur(4px);\n  border: 1px solid rgba(255, 255, 255, 0.18);\n  border-radius: 16px;\n}"
        },
        {
            "id": "warm_professional",
            "name": "Warm Professional",
            "description": "Clean, corporate styles with warm amber tones.",
            "tokens": {
                "primary_color": "#FF9800",
                "background_color": "#FFFDE7",
                "font_family": "Roboto",
                "border_radius": 4,
                "input_style": "outlined"
            },
            "branding": {},
            "custom_css": "/* Warm Professional Presets */\n.form-container {\n  background-color: #FFFDE7;\n  color: #3E2723;\n}\n.form-input {\n  border-color: #FF9800;\n}"
        }
    ]
    return jsonify({
        "status": "success",
        "data": presets
    }), 200

@forms_bp.route("", methods=["POST"])
def create_form():
    data = request.get_json() or {}
    name = data.get("name")
    org_id = data.get("org_id")
    project_id = data.get("project_id")
    author_id = data.get("author_id")
    auth = _auth_context()
    if not name:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "Form name is required."
        }), 400
    if not org_id:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "org_id is required."
        }), 400
    if not project_id:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "project_id is required."
        }), 400
    if not author_id:
        if not auth:
            return _deny()
        author_id = auth["decoded"].get("sub")
    elif auth and str(author_id) != str(auth["decoded"].get("sub")) and auth["decoded"].get("system_role") != "super_admin":
        return _deny("FORBIDDEN", "Forbidden", 403)

    if auth:
        resource = {"type": "org", "org_id": org_id}
        if not user_has_access_to_resource(auth["user_doc"], auth["decoded"], resource, "create_form"):
            return _deny("FORBIDDEN", "Forbidden", 403)

    try:
        enforce_org_quota(org_id)
    except ValueError as exc:
        return jsonify({
            "status": "error",
            "code": "QUOTA_EXCEEDED",
            "message": str(exc)
        }), 403

    description = data.get("description", "")
    form_id = ObjectId()
    now = datetime.datetime.utcnow()
    org_value = ObjectId(org_id) if ObjectId.is_valid(org_id) else org_id
    project_value = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
    author_value = ObjectId(author_id) if ObjectId.is_valid(author_id) else author_id

    # Create form document
    form_doc = {
        "_id": form_id,
        "org_id": org_value,
        "project_id": project_value,
        "name": name,
        "description": description,
        "branches": {},
        "production_branch": "main",
        "tags": {},
        "template_id": None,
        "created_by": author_value,
        "deleted_at": None,
        "is_deleted": False,
        "created_at": now,
        "updated_at": now
    }

    mongo.db.forms.insert_one(form_doc)

    # Create initial commit on main
    init_schema = {
        "ui": {
            "theme": {
                "primary_color": "#2196F3",
                "background_color": "#FFFFFF",
                "font_family": "Roboto",
                "font_size_base": 14,
                "border_radius": 8,
                "input_style": "outlined"
            },
            "layout": "single_page",
            "cover_page": {
                "enabled": False,
                "title": name,
                "description": "",
                "image_url": None,
                "button_label": "Start"
            },
            "thank_you_page": {
                "enabled": False,
                "title": "Thank you",
                "message": "",
                "show_response_id": False,
                "redirect_url": None,
                "redirect_delay_seconds": None
            }
        },
        "access": {
            "type": "public",
            "allowed_org_ids": [],
            "allowed_group_ids": [],
            "allowed_user_ids": [],
            "allow_anonymous": True
        },
        "settings": {},
        "sections": []
    }
    
    commit = create_commit(
        form_id=form_id,
        schema=init_schema,
        author_id=author_id,
        message="Initial commit",
        branch="main",
        parent_ids=[]
    )
    mongo.db.forms.update_one(
        {"_id": form_id, "is_deleted": False},
        {"$set": {"branches.main": commit["commit_id"], "updated_at": datetime.datetime.utcnow()}}
    )
    
    return jsonify({
        "status": "success",
        "message": "Form created successfully.",
        "data": {
            "form_id": str(form_id),
            "name": name,
            "branches": {
                "main": commit["commit_id"]
            }
        }
    }), 201

@forms_bp.route("/<form_id>/commits", methods=["POST"])
def commit_schema(form_id):
    fid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        return jsonify({
            "status": "error",
            "code": "NOT_FOUND",
            "message": "Form not found."
        }), 404
        
    data = request.get_json() or {}
    branch = data.get("branch", "main")
    parent_id = data.get("parent_id")
    message = data.get("message", "Schema update")
    author_id = data.get("author_id")
    auth = _auth_context()
    schema = data.get("schema")
    
    if schema is None:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "Schema is required."
        }), 400
        
    if isinstance(schema, dict) and "ui" in schema:
        ui = schema.get("ui")
        if isinstance(ui, dict) and "theme" in ui:
            theme = ui.get("theme")
            if isinstance(theme, dict) and "custom_css" in theme:
                try:
                    validate_custom_css(theme["custom_css"])
                except ValueError as e:
                    return jsonify({
                        "status": "error",
                        "code": "BAD_REQUEST",
                        "message": str(e)
                    }), 400
    if isinstance(schema, dict) and "settings" in schema:
        settings = schema.get("settings")
        if isinstance(settings, dict) and "notifications" in settings:
            try:
                validate_notifications_settings(settings["notifications"])
            except ValueError as e:
                return jsonify({
                    "status": "error",
                    "code": "BAD_REQUEST",
                    "message": str(e)
                }), 400
        if isinstance(settings, dict) and "analytics" in settings:
            try:
                validate_analytics_settings(settings["analytics"])
            except ValueError as e:
                return jsonify({
                    "status": "error",
                    "code": "BAD_REQUEST",
                    "message": str(e)
                }), 400
    if not author_id:
        if not auth:
            return _deny()
        author_id = auth["decoded"].get("sub")
    if auth and not user_has_access_to_resource(auth["user_doc"], auth["decoded"], {"type": "project", "project_id": form.get("project_id"), "org_id": form.get("org_id"), "project_doc": mongo.db.projects.find_one({"_id": form.get("project_id"), "is_deleted": False})}, "edit_form"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    if "branches" not in form or branch not in form["branches"]:
        return jsonify({
            "status": "error",
            "code": "BRANCH_NOT_FOUND",
            "message": f"Branch {branch} not found."
        }), 404
        
    # Resolve parent_ids
    parent_ids = []
    if parent_id:
        parent_ids = [parent_id]
    else:
        branch_head = form["branches"].get(branch)
        if branch_head:
            parent_ids = [branch_head]
        
    commit = create_commit(
        form_id=fid,
        schema=schema,
        author_id=author_id,
        message=message,
        branch=branch,
        parent_ids=parent_ids
    )
    
    return jsonify({
        "status": "success",
        "message": "Commit created successfully.",
        "data": {
            "commit_id": commit["commit_id"],
            "timestamp": commit["timestamp"]
        }
    }), 200













@forms_bp.route("/<form_id>", methods=["DELETE"])
def delete_form(form_id):
    auth = _auth_context()
    fid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        return jsonify({"error": "Form not found"}), 404
        
    if auth and not user_has_access_to_resource(auth["user_doc"], auth["decoded"], {"type": "project", "project_id": form.get("project_id"), "org_id": form.get("org_id"), "project_doc": mongo.db.projects.find_one({"_id": form.get("project_id"), "is_deleted": False})}, "delete_form"):
        return _deny("FORBIDDEN", "Forbidden", 403)
        
    # Check compliance legal hold
    from app.services.compliance_service import is_resource_held
    if is_resource_held("form", fid):
        return jsonify({"code": "LEGAL_HOLD_ACTIVE", "error": "This form cannot be deleted due to an active compliance legal hold."}), 409
        
    mongo.db.forms.update_one({"_id": fid}, {"$set": {"is_deleted": True, "deleted_at": datetime.datetime.utcnow().isoformat()}})
    return jsonify({"message": "Form deleted successfully"}), 200


@forms_bp.route("/responses/<response_id>", methods=["DELETE"])
def delete_response(response_id):
    auth = _auth_context()
    rid = ObjectId(response_id) if ObjectId.is_valid(response_id) else response_id
    
    # Check compliance legal hold
    from app.services.compliance_service import is_resource_held
    if is_resource_held("response", rid):
        return jsonify({"code": "LEGAL_HOLD_ACTIVE", "error": "This response cannot be deleted due to an active compliance legal hold."}), 409
        
    mongo.db.responses.update_one({"_id": rid}, {"$set": {"is_deleted": True, "deleted_at": datetime.datetime.utcnow().isoformat()}})
    return jsonify({"message": "Response deleted successfully"}), 200


@forms_bp.route("/<form_id>/commits", methods=["GET"])
def list_commits(form_id):
    """List all commits for a form"""
    fid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        return jsonify({
            "status": "error",
            "code": "NOT_FOUND",
            "message": "Form not found."
        }), 404
        
    auth = _auth_context()
    if auth and not user_has_access_to_resource(auth["user_doc"], auth["decoded"], {"type": "project", "project_id": form.get("project_id"), "org_id": form.get("org_id"), "project_doc": mongo.db.projects.find_one({"_id": form.get("project_id"), "is_deleted": False})}, "read_form"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Get query parameters
    branch = request.args.get("branch")
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    
    # Build query
    query = {"form_id": fid}
    if branch:
        query["branch"] = branch
    
    # Get commits
    total = mongo.db.form_commits.count_documents(query)
    commits = list(mongo.db.form_commits.find(query)
        .sort("timestamp", -1)
        .skip((page - 1) * per_page)
        .limit(per_page))
    
    # Format response
    formatted_commits = []
    for commit in commits:
        formatted_commits.append({
            "commit_id": commit["commit_id"],
            "branch": commit["branch"],
            "tag": commit.get("tag"),
            "message": commit["message"],
            "author_id": str(commit["author_id"]),
            "timestamp": commit["timestamp"],
            "parent_ids": commit.get("parent_ids", [])
        })
    
    return jsonify({
        "status": "success",
        "data": {
            "commits": formatted_commits,
            "pagination": {
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page if total > 0 else 0
            }
        }
    }), 200


@forms_bp.route("/<form_id>/diff", methods=["GET"])
def get_form_diff(form_id):
    """Get diff between two commits"""
    fid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        return jsonify({
            "status": "error",
            "code": "NOT_FOUND",
            "message": "Form not found."
        }), 404
        
    auth = _auth_context()
    if auth and not user_has_access_to_resource(auth["user_doc"], auth["decoded"], {"type": "project", "project_id": form.get("project_id"), "org_id": form.get("org_id"), "project_doc": mongo.db.projects.find_one({"_id": form.get("project_id"), "is_deleted": False})}, "read_form"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Get query parameters
    from_commit_id = request.args.get("from_commit")
    to_commit_id = request.args.get("to_commit")
    
    if not from_commit_id or not to_commit_id:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "Both from_commit and to_commit are required."
        }), 400
    
    # Get commits
    from_commit = mongo.db.form_commits.find_one({
        "form_id": fid,
        "commit_id": from_commit_id
    })
    
    to_commit = mongo.db.form_commits.find_one({
        "form_id": fid,
        "commit_id": to_commit_id
    })
    
    if not from_commit or not to_commit:
        return jsonify({
            "status": "error",
            "code": "COMMIT_NOT_FOUND",
            "message": "One or both commits not found."
        }), 404
    
    # Generate diff
    from_schema = from_commit.get("schema", {})
    to_schema = to_commit.get("schema", {})
    
    diff = generate_schema_diff(from_schema, to_schema)
    
    return jsonify({
        "status": "success",
        "data": {
            "from_commit": from_commit_id,
            "to_commit": to_commit_id,
            "diff": diff
        }
    }), 200


def generate_schema_diff(schema1, schema2):
    """Generate diff between two form schemas"""
    diff = {
        "added": [],
        "removed": [],
        "modified": [],
        "unchanged": []
    }
    
    # Compare UI settings
    ui1 = schema1.get("ui", {})
    ui2 = schema2.get("ui", {})
    
    if ui1 != ui2:
        diff["modified"].append({
            "path": "ui",
            "type": "ui_settings",
            "old_value": ui1,
            "new_value": ui2
        })
    
    # Compare sections
    sections1 = schema1.get("sections", [])
    sections2 = schema2.get("sections", [])
    
    # Simple comparison by section ID
    section_ids1 = {s.get("id") for s in sections1}
    section_ids2 = {s.get("id") for s in sections2}
    
    # Added sections
    for section_id in section_ids2 - section_ids1:
        section = next((s for s in sections2 if s.get("id") == section_id), None)
        if section:
            diff["added"].append({
                "path": f"sections[{section_id}]",
                "type": "section",
                "value": section
            })
    
    # Removed sections
    for section_id in section_ids1 - section_ids2:
        section = next((s for s in sections1 if s.get("id") == section_id), None)
        if section:
            diff["removed"].append({
                "path": f"sections[{section_id}]",
                "type": "section",
                "value": section
            })
    
    # Compare common sections
    for section_id in section_ids1 & section_ids2:
        section1 = next((s for s in sections1 if s.get("id") == section_id), None)
        section2 = next((s for s in sections2 if s.get("id") == section_id), None)
        
        if section1 and section2:
            section_diff = compare_sections(section1, section2, f"sections[{section_id}]")
            diff["modified"].extend(section_diff)
    
    return diff


def compare_sections(section1, section2, path_prefix=""):
    """Compare two sections and return differences"""
    diff = []
    
    # Compare basic properties
    if section1.get("title") != section2.get("title"):
        diff.append({
            "path": f"{path_prefix}.title",
            "type": "section_property",
            "old_value": section1.get("title"),
            "new_value": section2.get("title")
        })
    
    if section1.get("description") != section2.get("description"):
        diff.append({
            "path": f"{path_prefix}.description",
            "type": "section_property",
            "old_value": section1.get("description"),
            "new_value": section2.get("description")
        })
    
    # Compare subsections
    subsections1 = section1.get("sub_sections", [])
    subsections2 = section2.get("sub_sections", [])
    
    subsection_ids1 = {s.get("id") for s in subsections1}
    subsection_ids2 = {s.get("id") for s in subsections2}
    
    # Added subsections
    for subsection_id in subsection_ids2 - subsection_ids1:
        subsection = next((s for s in subsections2 if s.get("id") == subsection_id), None)
        if subsection:
            diff.append({
                "path": f"{path_prefix}.sub_sections[{subsection_id}]",
                "type": "subsection",
                "value": subsection
            })
    
    # Removed subsections
    for subsection_id in subsection_ids1 - subsection_ids2:
        subsection = next((s for s in subsections1 if s.get("id") == subsection_id), None)
        if subsection:
            diff.append({
                "path": f"{path_prefix}.sub_sections[{subsection_id}]",
                "type": "subsection",
                "value": subsection
            })
    
    # Compare common subsections
    for subsection_id in subsection_ids1 & subsection_ids2:
        subsection1 = next((s for s in subsections1 if s.get("id") == subsection_id), None)
        subsection2 = next((s for s in subsections2 if s.get("id") == subsection_id), None)
        
        if subsection1 and subsection2:
            subsection_diff = compare_subsections(subsection1, subsection2, f"{path_prefix}.sub_sections[{subsection_id}]")
            diff.extend(subsection_diff)
    
    return diff


def compare_subsections(subsection1, subsection2, path_prefix=""):
    """Compare two subsections and return differences"""
    diff = []
    
    # Compare basic properties
    if subsection1.get("title") != subsection2.get("title"):
        diff.append({
            "path": f"{path_prefix}.title",
            "type": "subsection_property",
            "old_value": subsection1.get("title"),
            "new_value": subsection2.get("title")
        })
    
    # Compare questions
    questions1 = subsection1.get("questions", [])
    questions2 = subsection2.get("questions", [])
    
    question_ids1 = {q.get("id") for q in questions1}
    question_ids2 = {q.get("id") for q in questions2}
    
    # Added questions
    for question_id in question_ids2 - question_ids1:
        question = next((q for q in questions2 if q.get("id") == question_id), None)
        if question:
            diff.append({
                "path": f"{path_prefix}.questions[{question_id}]",
                "type": "question",
                "value": question
            })
    
    # Removed questions
    for question_id in question_ids1 - question_ids2:
        question = next((q for q in questions1 if q.get("id") == question_id), None)
        if question:
            diff.append({
                "path": f"{path_prefix}.questions[{question_id}]",
                "type": "question",
                "value": question
            })
    
    # Compare common questions
    for question_id in question_ids1 & question_ids2:
        question1 = next((q for q in questions1 if q.get("id") == question_id), None)
        question2 = next((q for q in questions2 if q.get("id") == question_id), None)
        
        if question1 and question2:
            question_diff = compare_questions(question1, question2, f"{path_prefix}.questions[{question_id}]")
            diff.extend(question_diff)
    
    return diff


def compare_questions(question1, question2, path_prefix=""):
    """Compare two questions and return differences"""
    diff = []
    
    # Compare basic properties
    properties_to_compare = ["label", "description", "type", "required"]
    for prop in properties_to_compare:
        if question1.get(prop) != question2.get(prop):
            diff.append({
                "path": f"{path_prefix}.{prop}",
                "type": "question_property",
                "old_value": question1.get(prop),
                "new_value": question2.get(prop)
            })
    
    # Compare properties
    props1 = question1.get("properties", {})
    props2 = question2.get("properties", {})
    
    if props1 != props2:
        diff.append({
            "path": f"{path_prefix}.properties",
            "type": "question_properties",
            "old_value": props1,
            "new_value": props2
        })
    
    return diff


@forms_bp.route("", methods=["GET"])
def list_forms():
    """List forms with filtering and pagination."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    org_id = request.args.get("org_id")
    project_id = request.args.get("project_id")
    limit = int(request.args.get("limit", 50))
    skip = int(request.args.get("skip", 0))
    
    if not org_id:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "org_id is required."
        }), 400
    
    try:
        forms = FormService.list_forms(
            org_id=org_id,
            project_id=project_id,
            user_id=auth["decoded"]["sub"],
            limit=limit,
            skip=skip
        )
        
        return jsonify({
            "status": "success",
            "data": forms
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>", methods=["GET"])
def get_form(form_id):
    """Get form details with versioning info."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    try:
        form = FormService.get_form(form_id, auth["decoded"]["sub"])
        if not form:
            return jsonify({
                "status": "error",
                "code": "NOT_FOUND",
                "message": "Form not found."
            }), 404
        
        return jsonify({
            "status": "success",
            "data": form
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/branches", methods=["GET"])
def list_form_branches(form_id):
    """List all branches for a form."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    try:
        branches = FormService.list_form_branches(form_id, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": branches
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/branches", methods=["POST"])
def create_form_branch(form_id):
    """Create a new branch for a form."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    data = request.get_json() or {}
    try:
        branch_request = BranchCreateRequest(**data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": f"Invalid request data: {str(e)}"
        }), 400
    
    try:
        result = FormService.create_form_branch(form_id, branch_request, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": result
        }), 201
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/branches/<branch_name>", methods=["DELETE"])
def delete_form_branch(form_id, branch_name):
    """Delete a branch from a form."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    try:
        branch_request = BranchDeleteRequest(branch_name=branch_name)
        result = FormService.delete_form_branch(form_id, branch_request, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": result
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/merge", methods=["POST"])
def merge_form_branches(form_id):
    """Merge one branch into another."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    data = request.get_json() or {}
    try:
        merge_request = MergeRequest(**data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": f"Invalid request data: {str(e)}"
        }), 400
    
    try:
        result = FormService.merge_form_branches(form_id, merge_request, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": result
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/tags", methods=["POST"])
def create_form_tag(form_id):
    """Create a tag for a form commit."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    data = request.get_json() or {}
    try:
        tag_request = TagCreateRequest(**data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": f"Invalid request data: {str(e)}"
        }), 400
    
    try:
        result = FormService.create_form_tag(form_id, tag_request, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": result
        }), 201
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/tags/<tag_name>", methods=["DELETE"])
def delete_form_tag(form_id, tag_name):
    """Delete a tag from a form."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    try:
        result = FormService.delete_form_tag(form_id, tag_name, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": result
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/tags", methods=["GET"])
def list_form_tags(form_id):
    """List all tags for a form."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    try:
        tags = FormService.list_form_tags(form_id, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": tags
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/publish", methods=["POST"])
def publish_form_branch(form_id):
    """Publish a branch to production."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    data = request.get_json() or {}
    try:
        publish_request = PublishRequest(**data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": f"Invalid request data: {str(e)}"
        }), 400
    
    try:
        result = FormService.publish_form_branch(form_id, publish_request, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": result
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/commits", methods=["GET"])
def get_form_commit_history(form_id):
    """Get commit history for a form."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    branch = request.args.get("branch")
    limit = int(request.args.get("limit", 50))
    skip = int(request.args.get("skip", 0))
    
    try:
        commits = FormService.get_form_commit_history(
            form_id, auth["decoded"]["sub"], branch, limit, skip
        )
        return jsonify({
            "status": "success",
            "data": commits
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/commits/<commit_a_id>/diff/<commit_b_id>", methods=["GET"])
def get_form_commit_diff(form_id, commit_a_id, commit_b_id):
    """Get the differences between two commits."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    try:
        diff = FormService.get_form_commit_diff(form_id, commit_a_id, commit_b_id, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": diff
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/merges/pending", methods=["GET"])
def get_pending_merges(form_id):
    """Get all pending merges for a form."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    try:
        pending_merges = FormService.get_pending_merges(form_id, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": pending_merges
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/merges/resolve", methods=["POST"])
def resolve_merge_conflict(form_id):
    """Resolve a merge conflict."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    data = request.get_json() or {}
    try:
        resolution_data = MergeConflictResolution(**data)
    except Exception as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": f"Invalid request data: {str(e)}"
        }), 400
    
    try:
        result = FormService.resolve_merge_conflict(form_id, resolution_data, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": result
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/merges/<pending_merge_id>/abandon", methods=["POST"])
def abandon_merge_conflict(form_id, pending_merge_id):
    """Abandon a pending merge conflict."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    try:
        result = FormService.abandon_merge_conflict(form_id, pending_merge_id, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": result
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/merges/<pending_merge_id>/details", methods=["GET"])
def get_merge_conflict_details(form_id, pending_merge_id):
    """Get detailed information about a merge conflict for UI rendering."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    try:
        conflict_details = MergeConflictResolver.get_merge_conflict_details(
            form_id, pending_merge_id, auth["decoded"]["sub"]
        )
        return jsonify({
            "status": "success",
            "data": conflict_details
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/merges/<pending_merge_id>/preview", methods=["POST"])
def preview_merge_resolution(form_id, pending_merge_id):
    """Preview the result of a merge resolution without applying it."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    data = request.get_json() or {}
    resolved_fields = data.get("resolved_fields", {})
    
    try:
        preview = MergeConflictResolver.preview_resolution(
            form_id, pending_merge_id, resolved_fields, auth["decoded"]["sub"]
        )
        return jsonify({
            "status": "success",
            "data": preview
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/merges/statistics", methods=["GET"])
def get_merge_conflict_statistics(form_id):
    """Get statistics about merge conflicts for a form."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    try:
        stats = MergeConflictResolver.get_merge_conflict_statistics(form_id, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": stats
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>/merges/bulk-resolve", methods=["POST"])
def bulk_resolve_merge_conflicts(form_id):
    """Bulk resolve conflicts using a specific strategy."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    data = request.get_json() or {}
    resolution_strategy = data.get("resolution_strategy")
    
    if not resolution_strategy:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "resolution_strategy is required."
        }), 400
    
    if resolution_strategy not in ["use_target", "use_their", "use_base"]:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "resolution_strategy must be one of: use_target, use_their, use_base"
        }), 400
    
    try:
        result = MergeConflictResolver.bulk_resolve_conflicts(
            form_id, resolution_strategy, auth["decoded"]["sub"]
        )
        return jsonify({
            "status": "success",
            "data": result
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400, pending_merge_id):
    """Abandon a pending merge conflict."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    try:
        result = FormService.abandon_merge_conflict(form_id, pending_merge_id, auth["decoded"]["sub"])
        return jsonify({
            "status": "success",
            "data": result
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400


@forms_bp.route("/<form_id>", methods=["PUT"])
def update_form_schema(form_id):
    """Update form schema by creating a new commit."""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    data = request.get_json() or {}
    schema = data.get("schema")
    message = data.get("message", "Update form schema")
    branch = data.get("branch", "main")
    
    if not schema:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "Schema is required."
        }), 400
    
    try:
        result = FormService.update_form_schema(form_id, schema, auth["decoded"]["sub"], message, branch)
        return jsonify({
            "status": "success",
            "data": result
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400

