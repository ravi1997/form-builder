from typing import List, Dict, Any, Optional, Union
from bson import ObjectId
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

from app.extensions import mongo
from app.models.form_models import (
    PendingMerge, MergeConflictResolution, FormCommitResponse, FormDiffResponse
)
from app.services.form_service import FormService
from app.engines.form_engine import (
    get_commit_diff, get_pending_merges, resolve_merge_conflict,
    abandon_merge_conflict, find_common_ancestor
)


class MergeConflictResolver:
    """Service for handling merge conflict resolution UI components."""
    
    @staticmethod
    def get_merge_conflict_details(form_id: str, pending_merge_id: str, user_id: str) -> Dict[str, Any]:
        """Get detailed information about a merge conflict for UI rendering."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        pmid = ObjectId(pending_merge_id) if isinstance(pending_merge_id, str) else pending_merge_id
        
        # Get pending merge details
        pending_merge = mongo.db.pending_merges.find_one({
            "_id": pmid,
            "form_id": form_oid,
            "status": "pending"
        })
        
        if not pending_merge:
            raise ValueError(f"Pending merge {pending_merge_id} not found")
        
        # Get form details
        form = mongo.db.forms.find_one({
            "_id": form_oid,
            "is_deleted": False
        })
        
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        # Get commits involved
        base_commit_id = pending_merge["base_commit_id"]
        their_commit_id = pending_merge["their_commit_id"]
        target_branch = pending_merge["branch_name"]
        
        # Get target branch head
        target_commit_id = form["branches"][target_branch]
        
        base_commit = mongo.db.form_commits.find_one({
            "form_id": form_oid,
            "commit_id": base_commit_id
        })
        
        their_commit = mongo.db.form_commits.find_one({
            "form_id": form_oid,
            "commit_id": their_commit_id
        })
        
        target_commit = mongo.db.form_commits.find_one({
            "form_id": form_oid,
            "commit_id": target_commit_id
        })
        
        if not base_commit or not their_commit or not target_commit:
            raise ValueError("Failed to retrieve commit details")
        
        # Get diff between base and their changes
        base_their_diff = get_commit_diff(form_oid, base_commit_id, their_commit_id)
        
        # Get diff between base and target changes
        base_target_diff = get_commit_diff(form_oid, base_commit_id, target_commit_id)
        
        # Build conflict resolution UI data
        conflict_data = {
            "pending_merge_id": pending_merge_id,
            "form_id": form_id,
            "form_name": form["name"],
            "target_branch": target_branch,
            "source_commit": {
                "commit_id": their_commit_id,
                "message": their_commit["message"],
                "author_id": str(their_commit["author_id"]),
                "timestamp": their_commit["timestamp"]
            },
            "target_commit": {
                "commit_id": target_commit_id,
                "message": target_commit["message"],
                "author_id": str(target_commit["author_id"]),
                "timestamp": target_commit["timestamp"]
            },
            "base_commit": {
                "commit_id": base_commit_id,
                "message": base_commit["message"],
                "author_id": str(base_commit["author_id"]),
                "timestamp": base_commit["timestamp"]
            },
            "conflict_fields": pending_merge["conflict_fields"],
            "our_changes": pending_merge["our_changes"],
            "conflicts": []
        }
        
        # Build detailed conflict information for each field
        for field_path in pending_merge["conflict_fields"]:
            conflict_detail = MergeConflictResolver._build_conflict_detail(
                field_path, base_commit["schema"], target_commit["schema"], their_commit["schema"]
            )
            conflict_data["conflicts"].append(conflict_detail)
        
        return conflict_data
    
    @staticmethod
    def _build_conflict_detail(field_path: str, base_schema: Dict, target_schema: Dict, their_schema: Dict) -> Dict[str, Any]:
        """Build detailed conflict information for a specific field."""
        
        # Navigate the schema to get the conflicting values
        base_value = MergeConflictResolver._get_nested_value(base_schema, field_path)
        target_value = MergeConflictResolver._get_nested_value(target_schema, field_path)
        their_value = MergeConflictResolver._get_nested_value(their_schema, field_path)
        
        # Determine conflict type
        conflict_type = "modification"
        if base_value is not None and target_value is None and their_value is not None:
            conflict_type = "deletion_vs_modification"
        elif base_value is not None and target_value is not None and their_value is None:
            conflict_type = "modification_vs_deletion"
        elif base_value is None and target_value is not None and their_value is not None:
            conflict_type = "addition_conflict"
        
        return {
            "field_path": field_path,
            "conflict_type": conflict_type,
            "base_value": base_value,
            "target_value": target_value,
            "their_value": their_value,
            "field_type": MergeConflictResolver._get_field_type(their_value or target_value or base_value),
            "suggestions": MergeConflictResolver._get_resolution_suggestions(
                conflict_type, base_value, target_value, their_value
            )
        }
    
    @staticmethod
    def _get_nested_value(schema: Dict, field_path: str) -> Any:
        """Get a nested value from schema using dot notation."""
        if not field_path:
            return None
        
        parts = field_path.split(".")
        current = schema
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    @staticmethod
    def _get_field_type(value: Any) -> str:
        """Determine the type of a field value."""
        if value is None:
            return "null"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "unknown"
    
    @staticmethod
    def _get_resolution_suggestions(conflict_type: str, base_value: Any, target_value: Any, their_value: Any) -> List[Dict[str, Any]]:
        """Get resolution suggestions for a conflict."""
        suggestions = []
        
        if conflict_type == "modification":
            suggestions.extend([
                {
                    "type": "use_target",
                    "label": "Use Target Version",
                    "description": "Keep the changes from the target branch",
                    "value": target_value
                },
                {
                    "type": "use_their",
                    "label": "Use Their Version",
                    "description": "Use the changes from the source branch",
                    "value": their_value
                },
                {
                    "type": "use_base",
                    "label": "Use Base Version",
                    "description": "Revert to the original base version",
                    "value": base_value
                }
            ])
        elif conflict_type == "deletion_vs_modification":
            suggestions.extend([
                {
                    "type": "keep_deletion",
                    "label": "Keep Deletion",
                    "description": "Remove the field (target branch)",
                    "value": None
                },
                {
                    "type": "keep_modification",
                    "label": "Keep Modification",
                    "description": "Keep the modified field (source branch)",
                    "value": their_value
                }
            ])
        elif conflict_type == "modification_vs_deletion":
            suggestions.extend([
                {
                    "type": "keep_modification",
                    "label": "Keep Modification",
                    "description": "Keep the modified field (target branch)",
                    "value": target_value
                },
                {
                    "type": "keep_deletion",
                    "label": "Keep Deletion",
                    "description": "Remove the field (source branch)",
                    "value": None
                }
            ])
        elif conflict_type == "addition_conflict":
            suggestions.extend([
                {
                    "type": "use_target",
                    "label": "Use Target Addition",
                    "description": "Keep the addition from target branch",
                    "value": target_value
                },
                {
                    "type": "use_their",
                    "label": "Use Their Addition",
                    "description": "Keep the addition from source branch",
                    "value": their_value
                },
                {
                    "type": "use_both",
                    "label": "Use Both",
                    "description": "Keep both additions (if applicable)",
                    "value": [target_value, their_value]
                }
            ])
        
        # Add manual option
        suggestions.append({
            "type": "manual",
            "label": "Manual Edit",
            "description": "Manually specify the resolved value",
            "value": None
        })
        
        return suggestions
    
    @staticmethod
    def preview_resolution(form_id: str, pending_merge_id: str, resolved_fields: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """Preview the result of a merge resolution without applying it."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        pmid = ObjectId(pending_merge_id) if isinstance(pending_merge_id, str) else pending_merge_id
        
        # Get pending merge details
        pending_merge = mongo.db.pending_merges.find_one({
            "_id": pmid,
            "form_id": form_oid,
            "status": "pending"
        })
        
        if not pending_merge:
            raise ValueError(f"Pending merge {pending_merge_id} not found")
        
        # Get commits involved
        base_commit_id = pending_merge["base_commit_id"]
        their_commit_id = pending_merge["their_commit_id"]
        target_branch = pending_merge["branch_name"]
        
        # Get target branch head
        form = mongo.db.forms.find_one({"_id": form_oid})
        target_commit_id = form["branches"][target_branch]
        
        # Get commit schemas
        base_commit = mongo.db.form_commits.find_one({
            "form_id": form_oid,
            "commit_id": base_commit_id
        })
        
        their_commit = mongo.db.form_commits.find_one({
            "form_id": form_oid,
            "commit_id": their_commit_id
        })
        
        target_commit = mongo.db.form_commits.find_one({
            "form_id": form_oid,
            "commit_id": target_commit_id
        })
        
        # Start with their schema and apply resolved fields
        preview_schema = dict(their_commit["schema"])
        
        # Apply resolved fields
        for field_path, resolved_value in resolved_fields.items():
            MergeConflictResolver._set_nested_value(preview_schema, field_path, resolved_value)
        
        # Calculate what would change
        preview_diff = get_commit_diff(form_oid, target_commit_id, their_commit_id)
        
        return {
            "pending_merge_id": pending_merge_id,
            "preview_schema": preview_schema,
            "changes_applied": len(resolved_fields),
            "remaining_conflicts": len(pending_merge["conflict_fields"]) - len(resolved_fields),
            "diff_summary": preview_diff
        }
    
    @staticmethod
    def _set_nested_value(schema: Dict, field_path: str, value: Any) -> None:
        """Set a nested value in schema using dot notation."""
        if not field_path:
            return
        
        parts = field_path.split(".")
        current = schema
        
        # Navigate to the parent of the target field
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the value
        if value is None:
            # Remove the field if value is None
            if parts[-1] in current:
                del current[parts[-1]]
        else:
            current[parts[-1]] = value
    
    @staticmethod
    def get_merge_conflict_statistics(form_id: str, user_id: str) -> Dict[str, Any]:
        """Get statistics about merge conflicts for a form."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        
        # Get all pending merges
        pending_merges = get_pending_merges(form_oid)
        
        # Calculate statistics
        total_conflicts = len(pending_merges)
        total_conflict_fields = sum(len(pm["conflict_fields"]) for pm in pending_merges)
        
        # Group conflicts by type
        conflict_types = {}
        for pm in pending_merges:
            form = mongo.db.forms.find_one({"_id": pm["form_id"]})
            if form:
                base_commit = mongo.db.form_commits.find_one({
                    "form_id": pm["form_id"],
                    "commit_id": pm["base_commit_id"]
                })
                target_commit = mongo.db.form_commits.find_one({
                    "form_id": pm["form_id"],
                    "commit_id": form["branches"][pm["branch_name"]]
                })
                their_commit = mongo.db.form_commits.find_one({
                    "form_id": pm["form_id"],
                    "commit_id": pm["their_commit_id"]
                })
                
                if base_commit and target_commit and their_commit:
                    for field_path in pm["conflict_fields"]:
                        conflict_type = MergeConflictResolver._determine_conflict_type(
                            field_path, base_commit["schema"], target_commit["schema"], their_commit["schema"]
                        )
                        conflict_types[conflict_type] = conflict_types.get(conflict_type, 0) + 1
        
        return {
            "form_id": form_id,
            "total_pending_merges": total_conflicts,
            "total_conflict_fields": total_conflict_fields,
            "conflict_types": conflict_types,
            "oldest_conflict": min((pm["created_at"] for pm in pending_merges), default=None),
            "newest_conflict": max((pm["created_at"] for pm in pending_merges), default=None)
        }
    
    @staticmethod
    def _determine_conflict_type(field_path: str, base_schema: Dict, target_schema: Dict, their_schema: Dict) -> str:
        """Determine the type of conflict for a field."""
        
        base_value = MergeConflictResolver._get_nested_value(base_schema, field_path)
        target_value = MergeConflictResolver._get_nested_value(target_schema, field_path)
        their_value = MergeConflictResolver._get_nested_value(their_schema, field_path)
        
        if base_value is not None and target_value is None and their_value is not None:
            return "deletion_vs_modification"
        elif base_value is not None and target_value is not None and their_value is None:
            return "modification_vs_deletion"
        elif base_value is None and target_value is not None and their_value is not None:
            return "addition_conflict"
        else:
            return "modification"
    
    @staticmethod
    def bulk_resolve_conflicts(form_id: str, resolution_strategy: str, user_id: str) -> Dict[str, Any]:
        """Bulk resolve conflicts using a specific strategy."""
        
        form_oid = ObjectId(form_id) if isinstance(form_id, str) else form_id
        
        # Get all pending merges
        pending_merges = get_pending_merges(form_oid)
        
        resolved_count = 0
        failed_count = 0
        
        for pm in pending_merges:
            try:
                # Build resolved fields based on strategy
                resolved_fields = {}
                
                if resolution_strategy == "use_target":
                    # Use target version for all conflicts
                    form = mongo.db.forms.find_one({"_id": pm["form_id"]})
                    target_commit_id = form["branches"][pm["branch_name"]]
                    target_commit = mongo.db.form_commits.find_one({
                        "form_id": pm["form_id"],
                        "commit_id": target_commit_id
                    })
                    
                    for field_path in pm["conflict_fields"]:
                        resolved_fields[field_path] = MergeConflictResolver._get_nested_value(
                            target_commit["schema"], field_path
                        )
                
                elif resolution_strategy == "use_their":
                    # Use their version for all conflicts
                    their_commit = mongo.db.form_commits.find_one({
                        "form_id": pm["form_id"],
                        "commit_id": pm["their_commit_id"]
                    })
                    
                    for field_path in pm["conflict_fields"]:
                        resolved_fields[field_path] = MergeConflictResolver._get_nested_value(
                            their_commit["schema"], field_path
                        )
                
                elif resolution_strategy == "use_base":
                    # Use base version for all conflicts
                    base_commit = mongo.db.form_commits.find_one({
                        "form_id": pm["form_id"],
                        "commit_id": pm["base_commit_id"]
                    })
                    
                    for field_path in pm["conflict_fields"]:
                        resolved_fields[field_path] = MergeConflictResolver._get_nested_value(
                            base_commit["schema"], field_path
                        )
                
                else:
                    raise ValueError(f"Unknown resolution strategy: {resolution_strategy}")
                
                # Resolve the conflict
                resolution_data = MergeConflictResolution(
                    pending_merge_id=pm["_id"],
                    resolved_fields=resolved_fields,
                    resolution_strategy=resolution_strategy
                )
                
                result = resolve_merge_conflict(
                    form_id=form_oid,
                    resolution_data=resolution_data,
                    user_id=user_id
                )
                
                resolved_count += 1
                
            except Exception as e:
                logger.error(f"Failed to bulk resolve conflict {pm['_id']}: {str(e)}")
                failed_count += 1
        
        return {
            "form_id": form_id,
            "resolution_strategy": resolution_strategy,
            "resolved_count": resolved_count,
            "failed_count": failed_count,
            "total_processed": resolved_count + failed_count
        }