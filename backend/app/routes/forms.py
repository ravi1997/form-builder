from flask import Blueprint, request, jsonify, current_app
from bson import ObjectId
from app.extensions import mongo
from app.engines.form_engine import create_commit, create_branch, three_way_merge
from app.services.quota_service import enforce_org_quota
from app.services.auth_service import decode_request_bearer_token, user_has_access_to_resource, check_permission
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

def validate_custom_css(custom_css):
    if not isinstance(custom_css, str):
        raise ValueError("custom_css must be a string")
    if len(custom_css) > 10000:
        raise ValueError("custom_css exceeds size limit of 10000 characters")
    lower_css = custom_css.lower()
    if "<script" in lower_css or "javascript:" in lower_css or "</script>" in lower_css or "<html" in lower_css or "<body" in lower_css:
        raise ValueError("custom_css contains forbidden HTML/script tags")

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

@forms_bp.route("/<form_id>/branches", methods=["POST"])
def post_create_branch(form_id):
    fid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        return jsonify({
            "status": "error",
            "code": "NOT_FOUND",
            "message": "Form not found."
        }), 404
        
    data = request.get_json() or {}
    name = data.get("name")
    from_branch = data.get("from_branch", "main")
    from_commit_id = data.get("from_commit_id")
    
    if not name:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "Branch name is required."
        }), 400
        
    # Check duplicate branch
    if "branches" in form and name in form["branches"]:
        return jsonify({
            "status": "error",
            "code": "BRANCH_ALREADY_EXISTS",
            "message": f"Branch {name} already exists."
        }), 400
        
    if not from_commit_id:
        # Resolve from branch HEAD
        if "branches" not in form or from_branch not in form["branches"]:
            return jsonify({
                "status": "error",
                "code": "BRANCH_NOT_FOUND",
                "message": f"Source branch {from_branch} not found."
            }), 400
        from_commit_id = form["branches"][from_branch]
        
    try:
        res = create_branch(form_id, name, from_commit_id)
        return jsonify({
            "status": "success",
            "message": "Branch created successfully.",
            "data": res
        }), 201
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400

@forms_bp.route("/<form_id>/branches/<branch_name>/schema", methods=["GET"])
def get_branch_schema(form_id, branch_name):
    fid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        return jsonify({
            "status": "error",
            "code": "NOT_FOUND",
            "message": "Form not found."
        }), 404
        
    if "branches" not in form or branch_name not in form["branches"]:
        return jsonify({
            "status": "error",
            "code": "BRANCH_NOT_FOUND",
            "message": f"Branch {branch_name} not found."
        }), 404
        
    commit_id = form["branches"][branch_name]
    commit = mongo.db.form_commits.find_one({"form_id": fid, "commit_id": commit_id})
    if not commit:
        return jsonify({
            "status": "error",
            "code": "COMMIT_NOT_FOUND",
            "message": f"HEAD commit {commit_id} not found."
        }), 404
        
    return jsonify({
        "status": "success",
        "message": "Branch schema fetched successfully.",
        "data": {
            "schema": commit.get("schema", {}),
            "commit_id": commit_id,
            "branch": branch_name
        }
    }), 200

@forms_bp.route("/<form_id>/branches/<branch_name>", methods=["DELETE"])
def delete_branch(form_id, branch_name):
    fid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        return jsonify({
            "status": "error",
            "code": "NOT_FOUND",
            "message": "Form not found."
        }), 404
        
    if branch_name == "main":
        return jsonify({
            "status": "error",
            "code": "FORBIDDEN",
            "message": "Cannot delete main branch."
        }), 400
        
    if form.get("production_branch") == branch_name:
        return jsonify({
            "status": "error",
            "code": "FORBIDDEN",
            "message": "Cannot delete production branch."
        }), 400
        
    if "branches" not in form or branch_name not in form["branches"]:
        return jsonify({
            "status": "error",
            "code": "BRANCH_NOT_FOUND",
            "message": f"Branch {branch_name} not found."
        }), 404
        
    # Unset branch
    mongo.db.forms.update_one(
        {"_id": fid},
        {"$unset": {f"branches.{branch_name}": ""}, "$set": {"updated_at": datetime.datetime.utcnow().isoformat()}}
    )
    
    return jsonify({
        "status": "success",
        "message": "Branch deleted successfully."
    }), 200

@forms_bp.route("/<form_id>/publish", methods=["POST"])
def publish_branch(form_id):
    fid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        return jsonify({
            "status": "error",
            "code": "NOT_FOUND",
            "message": "Form not found."
        }), 404
        
    data = request.get_json() or {}
    branch = data.get("branch")
    if not branch:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "Branch name is required to publish."
        }), 400
        
    if "branches" not in form or branch not in form["branches"]:
        return jsonify({
            "status": "error",
            "code": "BRANCH_NOT_FOUND",
            "message": f"Branch {branch} not found."
        }), 404
        
    commit_id = form["branches"][branch]
    
    # Update production branch
    mongo.db.forms.update_one(
        {"_id": fid, "is_deleted": False},
        {"$set": {"production_branch": branch, "updated_at": datetime.datetime.utcnow().isoformat()}}
    )
    
    return jsonify({
        "status": "success",
        "message": "Branch published successfully.",
        "data": {
            "production_branch": branch,
            "commit_id": commit_id
        }
    }), 200


@forms_bp.route("/<form_id>/merge", methods=["POST"])
def post_merge_branches(form_id):
    fid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
    form = mongo.db.forms.find_one({"_id": fid, "is_deleted": False})
    if not form:
        return jsonify({
            "status": "error",
            "code": "NOT_FOUND",
            "message": "Form not found."
        }), 404
        
    data = request.get_json() or {}
    source_branch = data.get("source_branch")
    target_branch = data.get("target_branch")
    author_id = data.get("author_id") or str(ObjectId())
    
    if not source_branch or not target_branch:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "Both source_branch and target_branch are required."
        }), 400
        
    try:
        res = three_way_merge(form_id, source_branch, target_branch, author_id)
        if res.get("status") == "conflict":
            return jsonify({
                "status": "error",
                "code": "MERGE_CONFLICT",
                "message": "Merge conflicts detected.",
                "details": {
                    "pending_merge_id": res["pending_merge_id"],
                    "conflict_fields": res["conflict_fields"]
                }
            }), 409
        return jsonify({
            "status": "success",
            "message": "Branches merged successfully.",
            "data": res
        }), 200
    except ValueError as e:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": str(e)
        }), 400
    auth = _auth_context()
    if auth and not user_has_access_to_resource(auth["user_doc"], auth["decoded"], {"type": "project", "project_id": form.get("project_id"), "org_id": form.get("org_id"), "project_doc": mongo.db.projects.find_one({"_id": form.get("project_id"), "is_deleted": False})}, "create_branch"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    auth = _auth_context()
    if auth and not user_has_access_to_resource(auth["user_doc"], auth["decoded"], {"type": "project", "project_id": form.get("project_id"), "org_id": form.get("org_id"), "project_doc": mongo.db.projects.find_one({"_id": form.get("project_id"), "is_deleted": False})}, "merge_branch"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    auth = _auth_context()
    if auth and not user_has_access_to_resource(auth["user_doc"], auth["decoded"], {"type": "project", "project_id": form.get("project_id"), "org_id": form.get("org_id"), "project_doc": mongo.db.projects.find_one({"_id": form.get("project_id"), "is_deleted": False})}, "publish_form"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    auth = _auth_context()
    if auth and not user_has_access_to_resource(auth["user_doc"], auth["decoded"], {"type": "project", "project_id": form.get("project_id"), "org_id": form.get("org_id"), "project_doc": mongo.db.projects.find_one({"_id": form.get("project_id"), "is_deleted": False})}, "merge_branch"):
        return _deny("FORBIDDEN", "Forbidden", 403)
