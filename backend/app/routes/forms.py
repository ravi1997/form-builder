from flask import Blueprint, request, jsonify
from bson import ObjectId
from app.extensions import mongo
from app.engines.form_engine import create_commit, create_branch, three_way_merge
import datetime

forms_bp = Blueprint("forms", __name__, url_prefix="/api/internal/v1/forms")

@forms_bp.route("", methods=["POST"])
def create_form():
    data = request.get_json() or {}
    name = data.get("name")
    org_id = data.get("org_id")
    project_id = data.get("project_id")
    author_id = data.get("author_id")
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
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "author_id is required."
        }), 400

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
    schema = data.get("schema")
    
    if schema is None:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "Schema is required."
        }), 400
    if not author_id:
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "author_id is required."
        }), 400
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
