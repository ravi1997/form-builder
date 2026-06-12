from typing import List, Optional, Dict, Any, Union
from bson import ObjectId
from datetime import datetime
import uuid

from app.extensions import mongo
from app.models.form_models import (
    Form, FormCommit, FormSchema, FormTemplate, FormResponse, ResponseDraft,
    PendingMerge, EditSession, BranchCreateRequest, BranchDeleteRequest,
    MergeRequest, TagCreateRequest, PublishRequest, MergeConflictResolution,
    FormCommitResponse, FormBranchResponse, FormDiffResponse, MergeResponse
)
from app.engines.form_engine import (
    create_commit, create_branch, delete_branch, list_branches,
    create_tag, delete_tag, list_tags, publish_branch, get_commit_history,
    get_commit_diff, three_way_merge, resolve_merge_conflict,
    get_pending_merges, abandon_merge_conflict, find_common_ancestor
)
from app.services.auth_service import user_has_access_to_resource, check_permission
from app.services.quota_service import enforce_org_quota


class FormService:
    """Service layer for form operations including versioning."""
    
    @staticmethod
    def create_form(org_id: str, project_id: str, name: str, description: str = "",
                   created_by: str, template_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new form with initial main branch."""
        
        # Check permissions and quotas
        enforce_org_quota(org_id, "forms")
        
        # Convert IDs to ObjectId
        org_oid = ObjectId(org_id) if isinstance(org_id, str) else org_id
        project_oid = ObjectId(project_id) if isinstance(project_id, str) else project_id
        creator_oid = ObjectId(created_by) if isinstance(created_by, str) else created_by
        
        # Create initial schema
        initial_schema = FormSchema()
        
        # If template is provided, use template schema
        if template_id:
            template = mongo.db.form_templates.find_one({
                "_id": ObjectId(template_id),
                "is_deleted": False
            })
            if not template:
                raise ValueError(f"Template {template_id} not found")
            initial_schema = FormSchema(**template["schema"])
        
        # Create form document
        form_data = {
            "org_id": org_oid,
            "project_id": project_oid,
            "name": name,
            "description": description,
            "branches": {},
            "production_branch": "main",
            "tags": {},
            "template_id": ObjectId(template_id) if template_id else None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": creator_oid,
            "is_deleted": False
        }
        
        result = mongo.db.forms.insert_one(form_data)
        form_id = result.inserted_id
        
        # Create initial commit
        initial_commit = create_commit(
            form_id=form_id,
            schema=initial_schema.dict(),
            author_id=creator_oid,
            message="Initial form creation",
            branch="main"
        )
        
        # Update form with main branch
        mongo.db.forms.update_one(
            {"_id": form_id},
            {
                "$set": {
                    "branches.main": initial_commit["commit_id"],
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update template usage count
        if template_id:
            mongo.db.form_templates.update_one(
                {"_id": ObjectId(template_id)},
                {"$inc": {"usage_count": 1}}
            )
        
        return {
            "form_id": str(form_id),
            "name": name,
            "initial_commit_id": initial_commit["commit_id"],
            "status": "created"
        }
    
    @staticmethod
    def get_form(form_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get form details with versioning info."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            return None
        
        # Check user access
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Get production commit
        production_branch = form.get("production_branch", "main")
        branches = form.get("branches", {})
        production_commit_id = branches.get(production_branch)
        
        production_commit = None
        if production_commit_id:
            production_commit = mongo.db.form_commits.find_one({
                "form_id": form_oid,
                "commit_id": production_commit_id
            })
        
        result = {
            "form_id": str(form["_id"]),
            "name": form["name"],
            "description": form.get("description", ""),
            "org_id": str(form["org_id"]),
            "project_id": str(form["project_id"]),
            "branches": branches,
            "production_branch": production_branch,
            "tags": form.get("tags", {}),
            "template_id": str(form["template_id"]) if form.get("template_id") else None,
            "created_at": form["created_at"],
            "updated_at": form["updated_at"],
            "created_by": str(form["created_by"]),
            "production_commit": production_commit["schema"] if production_commit else None,
            "production_commit_id": production_commit_id
        }
        
        return result
    
    @staticmethod
    def update_form_schema(form_id: str, schema: Dict[str, Any], user_id: str,
                          message: str = "Update form schema", branch: str = "main") -> Dict[str, Any]:
        """Update form schema by creating a new commit."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Validate schema
        try:
            form_schema = FormSchema(**schema)
        except Exception as e:
            raise ValueError(f"Invalid schema: {str(e)}")
        
        # Create new commit
        new_commit = create_commit(
            form_id=form_oid,
            schema=form_schema.dict(),
            author_id=user_oid,
            message=message,
            branch=branch
        )
        
        return {
            "form_id": form_id,
            "commit_id": new_commit["commit_id"],
            "branch": branch,
            "message": message,
            "status": "updated"
        }
    
    @staticmethod
    def create_form_branch(form_id: str, branch_data: BranchCreateRequest, user_id: str) -> Dict[str, Any]:
        """Create a new branch for a form."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Create branch
        result = create_branch(
            form_id=form_oid,
            name=branch_data.name,
            from_commit_id=branch_data.from_commit_id
        )
        
        return {
            "form_id": form_id,
            "branch": result,
            "status": "created"
        }
    
    @staticmethod
    def delete_form_branch(form_id: str, branch_data: BranchDeleteRequest, user_id: str) -> Dict[str, Any]:
        """Delete a branch from a form."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Check user permissions (only form owner or admin can delete branches)
        if form["created_by"] != user_oid:
            user = mongo.db.users.find_one({"_id": user_oid})
            if not user or user.get("system_role") != "super_admin":
                raise ValueError("Only form owner or admin can delete branches")
        
        # Delete branch
        result = delete_branch(form_oid, branch_data.branch_name)
        
        return {
            "form_id": form_id,
            "branch_name": branch_data.branch_name,
            "status": "deleted"
        }
    
    @staticmethod
    def list_form_branches(form_id: str, user_id: str) -> List[Dict[str, Any]]:
        """List all branches for a form."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # List branches
        branches = list_branches(form_oid)
        
        return branches
    
    @staticmethod
    def merge_form_branches(form_id: str, merge_data: MergeRequest, user_id: str) -> Dict[str, Any]:
        """Merge one branch into another."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Perform merge
        message = merge_data.message or f"Merge {merge_data.source_branch} into {merge_data.target_branch}"
        result = three_way_merge(
            form_id=form_oid,
            source_branch=merge_data.source_branch,
            target_branch=merge_data.target_branch,
            author_id=user_oid
        )
        
        return {
            "form_id": form_id,
            "source_branch": merge_data.source_branch,
            "target_branch": merge_data.target_branch,
            "result": result
        }
    
    @staticmethod
    def create_form_tag(form_id: str, tag_data: TagCreateRequest, user_id: str) -> Dict[str, Any]:
        """Create a tag for a form commit."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Create tag
        result = create_tag(
            form_id=form_oid,
            tag_name=tag_data.tag_name,
            commit_id=tag_data.commit_id,
            message=tag_data.message
        )
        
        return {
            "form_id": form_id,
            "tag": result,
            "status": "created"
        }
    
    @staticmethod
    def delete_form_tag(form_id: str, tag_name: str, user_id: str) -> Dict[str, Any]:
        """Delete a tag from a form."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Check user permissions
        user = mongo.db.users.find_one({"_id": user_oid})
        if not user or user.get("system_role") != "super_admin":
            raise ValueError("Only admin can delete tags")
        
        # Delete tag
        result = delete_tag(form_oid, tag_name)
        
        return {
            "form_id": form_id,
            "tag_name": tag_name,
            "status": "deleted"
        }
    
    @staticmethod
    def list_form_tags(form_id: str, user_id: str) -> List[Dict[str, Any]]:
        """List all tags for a form."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # List tags
        tags = list_tags(form_oid)
        
        return tags
    
    @staticmethod
    def publish_form_branch(form_id: str, publish_data: PublishRequest, user_id: str) -> Dict[str, Any]:
        """Publish a branch to production."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Check user permissions (only form owner or admin can publish)
        if form["created_by"] != user_oid:
            user = mongo.db.users.find_one({"_id": user_oid})
            if not user or user.get("system_role") != "super_admin":
                raise ValueError("Only form owner or admin can publish branches")
        
        # Publish branch
        result = publish_branch(
            form_id=form_oid,
            branch_name=publish_data.branch_name,
            author_id=user_oid,
            message=publish_data.message
        )
        
        return {
            "form_id": form_id,
            "publication": result,
            "status": "published"
        }
    
    @staticmethod
    def get_form_commit_history(form_id: str, user_id: str, branch: Optional[str] = None,
                               limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
        """Get commit history for a form."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Get commit history
        commits = get_commit_history(form_oid, branch, limit, skip)
        
        return commits
    
    @staticmethod
    def get_form_commit_diff(form_id: str, commit_a_id: str, commit_b_id: str, user_id: str) -> Dict[str, Any]:
        """Get the differences between two commits."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Get commit diff
        diff = get_commit_diff(form_oid, commit_a_id, commit_b_id)
        
        return diff
    
    @staticmethod
    def get_pending_merges(form_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get all pending merges for a form."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Get pending merges
        pending_merges = get_pending_merges(form_oid)
        
        return pending_merges
    
    @staticmethod
    def resolve_merge_conflict(form_id: str, resolution_data: MergeConflictResolution, user_id: str) -> Dict[str, Any]:
        """Resolve a merge conflict."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Resolve merge conflict
        result = resolve_merge_conflict(
            form_id=form_oid,
            pending_merge_id=resolution_data.pending_merge_id,
            resolved_fields=resolution_data.resolved_fields,
            resolver_id=user_oid
        )
        
        return {
            "form_id": form_id,
            "resolution": result,
            "status": "resolved"
        }
    
    @staticmethod
    def abandon_merge_conflict(form_id: str, pending_merge_id: str, user_id: str) -> Dict[str, Any]:
        """Abandon a pending merge conflict."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        pmid = ObjectId(pending_merge_id) if isinstance(pending_merge_id, str) else pending_merge_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Abandon merge conflict
        result = abandon_merge_conflict(form_oid, pmid, user_oid)
        
        return {
            "form_id": form_id,
            "abandonment": result,
            "status": "abandoned"
        }
    
    @staticmethod
    def delete_form(form_id: str, user_id: str) -> Dict[str, Any]:
        """Soft delete a form."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
        
        # Check form exists and user has access
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if not user_has_access_to_resource(user_oid, form["org_id"], "form", form_oid):
            raise ValueError("Access denied")
        
        # Check user permissions (only form owner or admin can delete)
        if form["created_by"] != user_oid:
            user = mongo.db.users.find_one({"_id": user_oid})
            if not user or user.get("system_role") != "super_admin":
                raise ValueError("Only form owner or admin can delete forms")
        
        # Soft delete form
        mongo.db.forms.update_one(
            {"_id": form_oid},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "form_id": form_id,
            "status": "deleted"
        }
    
    @staticmethod
    def list_forms(org_id: str, project_id: Optional[str] = None, user_id: Optional[str] = None,
                   limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
        """List forms with filtering and pagination."""
        
        org_oid = ObjectId(org_id) if isinstance(org_id, str) else org_id
        
        # Build query
        query = {"org_id": org_oid, "is_deleted": False}
        
        if project_id:
            query["project_id"] = ObjectId(project_id) if isinstance(project_id, str) else project_id
        
        if user_id:
            user_oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
            # Only show forms user has access to
            forms = list(mongo.db.forms.find(query)
                         .sort("updated_at", -1)
                         .skip(skip)
                         .limit(limit))
            
            # Filter by user access (simplified - should use proper access control)
            accessible_forms = []
            for form in forms:
                if user_has_access_to_resource(user_oid, form["org_id"], "form", form["_id"]):
                    accessible_forms.append(form)
            
            forms = accessible_forms
        else:
            forms = list(mongo.db.forms.find(query)
                         .sort("updated_at", -1)
                         .skip(skip)
                         .limit(limit))
        
        # Format results
        result = []
        for form in forms:
            result.append({
                "form_id": str(form["_id"]),
                "name": form["name"],
                "description": form.get("description", ""),
                "org_id": str(form["org_id"]),
                "project_id": str(form["project_id"]),
                "production_branch": form.get("production_branch", "main"),
                "created_at": form["created_at"],
                "updated_at": form["updated_at"],
                "created_by": str(form["created_by"])
            })
        
        return result