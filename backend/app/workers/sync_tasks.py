"""
Sync Tasks - Celery tasks for data synchronization and offline operations
Handles offline sync, conflict resolution, and data consistency.
"""

import os
import json
import datetime
from celery import Celery
from bson import ObjectId
from typing import Dict, Any, List, Optional

from app.extensions import mongo
from app.services.sync_service import (
    resolve_sync_conflict, generate_sync_patch, apply_sync_patch
)

# Get Celery app from main worker
from .celery_config import get_celery_app
celery_app = get_celery_app()


def _utcnow_iso():
    """Get current UTC datetime in ISO format."""
    return datetime.datetime.utcnow().isoformat()


def _to_object_id(value):
    """Convert string to ObjectId if valid."""
    if isinstance(value, ObjectId):
        return value
    if ObjectId.is_valid(str(value)):
        return ObjectId(str(value))
    raise ValueError(f"Invalid ObjectId: {value}")


def _safe_result_payload(status, error=None, **extra):
    """Create a standardized result payload."""
    payload = {"status": status, "error": error}
    payload.update(extra)
    return payload


@celery_app.task(
    name="app.workers.sync_tasks.process_offline_sync_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60
)
def process_offline_sync_task(self, user_id: str, sync_data: Dict[str, Any]):
    """
    Process offline synchronization data from client.
    """
    try:
        user_oid = _to_object_id(user_id)
        
        # Validate sync data structure
        if not isinstance(sync_data, dict):
            raise ValueError("Invalid sync data format")
        
        sync_metadata = sync_data.get("metadata", {})
        changes = sync_data.get("changes", [])
        
        if not changes:
            return _safe_result_payload(
                "completed",
                message="No changes to sync",
                changes_count=0
            )
        
        # Process each change
        processed_changes = []
        conflicts = []
        
        for change in changes:
            change_result = _process_sync_change(user_oid, change)
            
            if change_result.get("status") == "conflict":
                conflicts.append(change_result)
            else:
                processed_changes.append(change_result)
        
        # Update user's last sync timestamp
        mongo.db.users.update_one(
            {"_id": user_oid},
            {"$set": {
                "last_sync_at": _utcnow_iso(),
                "updated_at": _utcnow_iso()
            }}
        )
        
        return _safe_result_payload(
            "completed" if not conflicts else "partial",
            changes_count=len(processed_changes),
            conflicts_count=len(conflicts),
            conflicts=conflicts if conflicts else None
        )
        
    except Exception as e:
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        
        return _safe_result_payload("failed", str(e))


def _process_sync_change(user_oid: ObjectId, change: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single sync change."""
    entity_type = change.get("entity_type")
    entity_id = change.get("entity_id")
    operation = change.get("operation")  # create, update, delete
    data = change.get("data", {})
    client_version = change.get("client_version")
    server_version = change.get("server_version")
    
    if not all([entity_type, entity_id, operation]):
        return {
            "status": "error",
            "error": "Missing required sync change fields",
            "entity_type": entity_type,
            "entity_id": entity_id
        }
    
    # Check for conflicts
    if operation in ["update", "delete"] and server_version:
        current_entity = _get_entity(entity_type, entity_id)
        
        if current_entity:
            current_version = current_entity.get("_version", 0)
            if current_version > server_version:
                # Conflict: entity was modified on server after client version
                conflict_result = resolve_sync_conflict(
                    entity_type, entity_id, data, current_entity
                )
                
                return {
                    "status": "conflict",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "conflict_type": "version_conflict",
                    "client_data": data,
                    "server_data": current_entity,
                    "resolution_options": conflict_result.get("options", [])
                }
    
    # Apply the change
    try:
        if operation == "create":
            result = _create_entity(entity_type, data, user_oid)
        elif operation == "update":
            result = _update_entity(entity_type, entity_id, data, user_oid, client_version)
        elif operation == "delete":
            result = _delete_entity(entity_type, entity_id, user_oid, server_version)
        else:
            raise ValueError(f"Invalid operation: {operation}")
        
        return {
            "status": "success",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "operation": operation,
            "result": result
        }
        
    except Exception as e:
        return {
            "status": "error",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "operation": operation,
            "error": str(e)
        }


def _get_entity(entity_type: str, entity_id: str) -> Optional[Dict]:
    """Get entity by type and ID."""
    entity_oid = _to_object_id(entity_id)
    
    if entity_type == "form_response":
        return mongo.db.form_responses.find_one({"_id": entity_oid})
    elif entity_type == "response_draft":
        return mongo.db.response_drafts.find_one({"_id": entity_oid})
    elif entity_type == "user_profile":
        return mongo.db.users.find_one(
            {"_id": entity_oid},
            {"password_hash": 0, "two_factor_secret": 0}  # Exclude sensitive data
        )
    
    return None


def _create_entity(entity_type: str, data: Dict, user_oid: ObjectId) -> Dict:
    """Create a new entity."""
    now = _utcnow_iso()
    
    if entity_type == "form_response":
        # Validate required fields
        required_fields = ["form_id", "commit_id", "org_id"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        # Create response
        response_data = {
            "form_id": _to_object_id(data["form_id"]),
            "commit_id": data["commit_id"],
            "org_id": _to_object_id(data["org_id"]),
            "project_id": _to_object_id(data.get("project_id")),
            "respondent_id": user_oid,
            "answers": data.get("answers", {}),
            "metadata": data.get("metadata", {}),
            "status": "draft",
            "is_anonymous": False,
            "is_legacy": False,
            "created_at": now,
            "updated_at": now,
            "created_by": user_oid,
            "is_deleted": False
        }
        
        result = mongo.db.form_responses.insert_one(response_data)
        return {"inserted_id": str(result.inserted_id)}
    
    elif entity_type == "response_draft":
        # Create draft
        draft_data = {
            "form_id": _to_object_id(data["form_id"]),
            "commit_id": data["commit_id"],
            "org_id": _to_object_id(data["org_id"]),
            "respondent_id": user_oid,
            "partial_answers": data.get("partial_answers", {}),
            "last_saved_at": now,
            "expires_at": datetime.datetime.utcnow() + datetime.timedelta(days=30),
            "created_at": now,
            "updated_at": now
        }
        
        result = mongo.db.response_drafts.insert_one(draft_data)
        return {"inserted_id": str(result.inserted_id)}
    
    else:
        raise ValueError(f"Cannot create entity type: {entity_type}")


def _update_entity(entity_type: str, entity_id: str, data: Dict, 
                  user_oid: ObjectId, client_version: int) -> Dict:
    """Update an existing entity."""
    entity_oid = _to_object_id(entity_id)
    now = _utcnow_iso()
    
    # Increment version
    update_data = data.copy()
    update_data["updated_at"] = now
    update_data["_version"] = client_version + 1
    
    if entity_type == "form_response":
        result = mongo.db.form_responses.update_one(
            {"_id": entity_oid, "respondent_id": user_oid},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise ValueError("Response not found or access denied")
        
        return {"modified_count": result.modified_count}
    
    elif entity_type == "response_draft":
        result = mongo.db.response_drafts.update_one(
            {"_id": entity_oid, "respondent_id": user_oid},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise ValueError("Draft not found or access denied")
        
        return {"modified_count": result.modified_count}
    
    else:
        raise ValueError(f"Cannot update entity type: {entity_type}")


def _delete_entity(entity_type: str, entity_id: str, 
                  user_oid: ObjectId, server_version: int) -> Dict:
    """Delete an entity (soft delete)."""
    entity_oid = _to_object_id(entity_id)
    now = _utcnow_iso()
    
    if entity_type == "form_response":
        result = mongo.db.form_responses.update_one(
            {"_id": entity_oid, "respondent_id": user_oid},
            {"$set": {
                "is_deleted": True,
                "deleted_at": now,
                "updated_at": now,
                "_version": server_version + 1
            }}
        )
        
        if result.matched_count == 0:
            raise ValueError("Response not found or access denied")
        
        return {"deleted_count": result.modified_count}
    
    elif entity_type == "response_draft":
        result = mongo.db.response_drafts.delete_one({
            "_id": entity_oid,
            "respondent_id": user_oid
        })
        
        if result.deleted_count == 0:
            raise ValueError("Draft not found or access denied")
        
        return {"deleted_count": result.deleted_count}
    
    else:
        raise ValueError(f"Cannot delete entity type: {entity_type}")


@celery_app.task(name="app.workers.sync_tasks.generate_sync_data_task")
def generate_sync_data_task(user_id: str, last_sync_version: Optional[int] = None):
    """
    Generate sync data for a user since their last sync.
    """
    try:
        user_oid = _to_object_id(user_id)
        
        # Get user's orgs and projects
        user_orgs = list(mongo.db.org_memberships.find(
            {"user_id": user_oid, "status": "active"},
            {"org_id": 1}
        ))
        
        org_ids = [membership["org_id"] for membership in user_orgs]
        
        # Get user's projects
        user_projects = list(mongo.db.project_members.find(
            {"user_id": user_oid},
            {"project_id": 1}
        ))
        
        project_ids = [membership["project_id"] for membership in user_projects]
        
        # Generate sync data
        sync_data = {
            "metadata": {
                "generated_at": _utcnow_iso(),
                "user_id": user_id,
                "org_count": len(org_ids),
                "project_count": len(project_ids)
            },
            "changes": []
        }
        
        # Get form schemas (for offline access)
        forms_query = {
            "org_id": {"$in": org_ids},
            "is_deleted": {"$ne": True}
        }
        
        if project_ids:
            forms_query["project_id"] = {"$in": project_ids}
        
        forms = list(mongo.db.forms.find(forms_query))
        
        for form in forms:
            # Get production branch commit
            production_branch = form.get("production_branch", "main")
            commit_id = form.get("branches", {}).get(production_branch)
            
            if commit_id:
                form_commit = mongo.db.form_commits.find_one({
                    "form_id": form["_id"],
                    "commit_id": commit_id
                })
                
                if form_commit:
                    sync_data["changes"].append({
                        "entity_type": "form_schema",
                        "entity_id": str(form["_id"]),
                        "operation": "update",
                        "data": {
                            "form_id": str(form["_id"]),
                            "name": form.get("name"),
                            "commit_id": commit_id,
                            "schema": form_commit.get("schema", {}),
                            "_version": form.get("_version", 0)
                        }
                    })
        
        # Get user's own responses and drafts
        user_responses = list(mongo.db.form_responses.find({
            "respondent_id": user_oid,
            "is_deleted": {"$ne": True}
        }))
        
        for response in user_responses:
            sync_data["changes"].append({
                "entity_type": "form_response",
                "entity_id": str(response["_id"]),
                "operation": "update",
                "data": {
                    "form_id": str(response["form_id"]),
                    "commit_id": response.get("commit_id"),
                    "answers": response.get("answers", {}),
                    "status": response.get("status"),
                    "metadata": response.get("metadata", {}),
                    "_version": response.get("_version", 0)
                }
            })
        
        user_drafts = list(mongo.db.response_drafts.find({
            "respondent_id": user_oid
        }))
        
        for draft in user_drafts:
            sync_data["changes"].append({
                "entity_type": "response_draft",
                "entity_id": str(draft["_id"]),
                "operation": "update",
                "data": {
                    "form_id": str(draft["form_id"]),
                    "commit_id": draft.get("commit_id"),
                    "partial_answers": draft.get("partial_answers", {}),
                    "_version": draft.get("_version", 0)
                }
            })
        
        return _safe_result_payload(
            "completed",
            sync_data=sync_data,
            changes_count=len(sync_data["changes"])
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


@celery_app.task(name="app.workers.sync_tasks.resolve_sync_conflict_task")
def resolve_sync_conflict_task(user_id: str, conflict_id: str, 
                              resolution: Dict[str, Any]):
    """
    Resolve a sync conflict with user-provided resolution.
    """
    try:
        user_oid = _to_object_id(user_id)
        conflict_oid = _to_object_id(conflict_id)
        
        # Get conflict details
        conflict = mongo.db.sync_conflicts.find_one({
            "_id": conflict_oid,
            "user_id": user_oid
        })
        
        if not conflict:
            raise ValueError(f"Conflict {conflict_id} not found")
        
        # Apply resolution
        resolution_type = resolution.get("type")
        entity_type = conflict.get("entity_type")
        entity_id = conflict.get("entity_id")
        
        if resolution_type == "use_client":
            # Use client data
            client_data = conflict.get("client_data")
            if entity_type == "form_response":
                mongo.db.form_responses.update_one(
                    {"_id": _to_object_id(entity_id), "respondent_id": user_oid},
                    {"$set": {
                        **client_data,
                        "updated_at": _utcnow_iso(),
                        "_version": conflict.get("server_version", 0) + 1
                    }}
                )
        
        elif resolution_type == "use_server":
            # Keep server data (no action needed)
            pass
        
        elif resolution_type == "merge":
            # Merge client and server data
            merged_data = resolve_sync_conflict(
                entity_type, entity_id, 
                conflict.get("client_data"), 
                conflict.get("server_data")
            )
            
            if entity_type == "form_response":
                mongo.db.form_responses.update_one(
                    {"_id": _to_object_id(entity_id), "respondent_id": user_oid},
                    {"$set": {
                        **merged_data,
                        "updated_at": _utcnow_iso(),
                        "_version": conflict.get("server_version", 0) + 1
                    }}
                )
        
        else:
            raise ValueError(f"Invalid resolution type: {resolution_type}")
        
        # Mark conflict as resolved
        mongo.db.sync_conflicts.update_one(
            {"_id": conflict_oid},
            {"$set": {
                "status": "resolved",
                "resolution": resolution,
                "resolved_at": _utcnow_iso(),
                "resolved_by": user_oid
            }}
        )
        
        return _safe_result_payload(
            "completed",
            conflict_id=conflict_id,
            resolution_type=resolution_type
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))