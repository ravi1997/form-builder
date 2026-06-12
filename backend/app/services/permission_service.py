"""
ABAC (Attribute-Based Access Control) Evaluation Engine

This service implements the 6-step ABAC evaluation process as specified in the CONTEXT.md:
1. Check system_role (super_admin bypasses all)
2. Check org membership + role for the resource's org
3. Check project membership + role
4. Check form-level access settings
5. Check question/option visibility_rules (role condition)
6. Evaluate answer-based conditions at render time
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from bson import ObjectId
from app.extensions import mongo
from app.services.auth_service import (
    resolve_org_role,
    get_effective_project_role,
    evaluate_visibility_rules,
    get_user_groups_from_claims_or_db,
    ROLE_ACTIONS,
    ORG_TO_PROJECT_ROLE,
)

logger = logging.getLogger(__name__)


class PermissionEvaluationResult:
    """Result of a permission evaluation."""
    
    def __init__(self, allowed: bool, reason: str = "", effective_role: str = None):
        self.allowed = allowed
        self.reason = reason
        self.effective_role = effective_role
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "effective_role": self.effective_role
        }


class ABACEngine:
    """Attribute-Based Access Control evaluation engine."""
    
    def __init__(self):
        self.role_hierarchy = {
            "super_admin": 100,
            "org_admin": 90,
            "project_owner": 85,
            "org_editor": 80,
            "project_editor": 75,
            "org_analyst": 70,
            "project_analyst": 65,
            "org_viewer": 60,
            "project_viewer": 55,
        }
    
    def evaluate_permission(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any], 
                          action: str, resource: Dict[str, Any], 
                          context: Optional[Dict[str, Any]] = None) -> PermissionEvaluationResult:
        """
        Evaluate permission using the 6-step ABAC process.
        
        Args:
            user_doc: User document from database
            decoded_token: Decoded JWT token
            action: Action to perform (e.g., "edit_form", "view_responses")
            resource: Resource information with type and IDs
            context: Additional context for evaluation
            
        Returns:
            PermissionEvaluationResult with decision and reason
        """
        context = context or {}
        
        # Step 1: Check system_role (super_admin bypasses all)
        result = self._step1_check_system_role(user_doc, decoded_token)
        if result.allowed:
            return result
        
        # Step 2: Check org membership + role for the resource's org
        result = self._step2_check_org_membership(user_doc, decoded_token, resource, action)
        if not result.allowed:
            return result
        
        # Step 3: Check project membership + role
        result = self._step3_check_project_membership(user_doc, decoded_token, resource, action, context)
        if not result.allowed:
            return result
        
        # Step 4: Check form-level access settings
        result = self._step4_check_form_access(user_doc, decoded_token, resource, action, context)
        if not result.allowed:
            return result
        
        # Step 5: Check question/option visibility_rules (role condition)
        result = self._step5_check_visibility_rules(user_doc, decoded_token, resource, action, context)
        if not result.allowed:
            return result
        
        # Step 6: Evaluate answer-based conditions at render time
        result = self._step6_evaluate_answer_conditions(user_doc, decoded_token, resource, action, context)
        
        return result
    
    def _step1_check_system_role(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any]) -> PermissionEvaluationResult:
        """Step 1: Check system_role (super_admin bypasses all)."""
        system_role = user_doc.get("system_role") or decoded_token.get("system_role")
        if system_role == "super_admin":
            logger.debug(f"Super admin access granted for user {user_doc.get('_id')}")
            return PermissionEvaluationResult(
                allowed=True,
                reason="Super admin bypasses all restrictions",
                effective_role="super_admin"
            )
        return PermissionEvaluationResult(allowed=False, reason="Not super admin")
    
    def _step2_check_org_membership(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any], 
                                   resource: Dict[str, Any], action: str) -> PermissionEvaluationResult:
        """Step 2: Check org membership + role for the resource's org."""
        org_id = resource.get("org_id")
        if not org_id:
            # Resource doesn't require org membership
            return PermissionEvaluationResult(allowed=True, reason="No org requirement")
        
        # Check if org exists and is active
        org_doc = mongo.db.organisations.find_one({
            "_id": ObjectId(org_id),
            "is_deleted": False
        })
        if not org_doc:
            return PermissionEvaluationResult(allowed=False, reason="Organization not found")
        
        if org_doc.get("status") == "suspended":
            return PermissionEvaluationResult(allowed=False, reason="Organization suspended")
        
        # Get user's role in this org
        org_role = resolve_org_role(decoded_token, org_id)
        if not org_role:
            return PermissionEvaluationResult(allowed=False, reason="Not member of organization")
        
        # Check if role has required action
        allowed_actions = ROLE_ACTIONS.get(org_role, set())
        if action not in allowed_actions:
            return PermissionEvaluationResult(
                allowed=False,
                reason=f"Role {org_role} does not have permission for {action}",
                effective_role=org_role
            )
        
        logger.debug(f"Org permission granted: {action} for {org_role} in org {org_id}")
        return PermissionEvaluationResult(allowed=True, effective_role=org_role)
    
    def _step3_check_project_membership(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any], 
                                       resource: Dict[str, Any], action: str, 
                                       context: Dict[str, Any]) -> PermissionEvaluationResult:
        """Step 3: Check project membership + role."""
        resource_type = resource.get("type")
        project_id = resource.get("project_id")
        
        if resource_type not in ["project", "form", "analysis", "dashboard"] or not project_id:
            # Resource doesn't require project membership
            return PermissionEvaluationResult(allowed=True, reason="No project requirement")
        
        # Get project document
        project_doc = context.get("project_doc") or mongo.db.projects.find_one({
            "_id": ObjectId(project_id),
            "is_deleted": False
        })
        if not project_doc:
            return PermissionEvaluationResult(allowed=False, reason="Project not found")
        
        if project_doc.get("status") == "suspended":
            return PermissionEvaluationResult(allowed=False, reason="Project suspended")
        
        # Get effective project role
        effective_role = get_effective_project_role(user_doc, decoded_token, project_doc)
        if not effective_role:
            return PermissionEvaluationResult(allowed=False, reason="No project access")
        
        # Check if role has required action
        allowed_actions = ROLE_ACTIONS.get(effective_role, set())
        if action not in allowed_actions:
            return PermissionEvaluationResult(
                allowed=False,
                reason=f"Role {effective_role} does not have permission for {action}",
                effective_role=effective_role
            )
        
        logger.debug(f"Project permission granted: {action} for {effective_role} in project {project_id}")
        return PermissionEvaluationResult(allowed=True, effective_role=effective_role)
    
    def _step4_check_form_access(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any], 
                                resource: Dict[str, Any], action: str, 
                                context: Dict[str, Any]) -> PermissionEvaluationResult:
        """Step 4: Check form-level access settings."""
        resource_type = resource.get("type")
        form_id = resource.get("form_id")
        
        if resource_type not in ["form", "response"] or not form_id:
            # Resource doesn't require form access check
            return PermissionEvaluationResult(allowed=True, reason="No form access requirement")
        
        # Get form access settings
        form_access = resource.get("form_access")
        if not form_access:
            # If no form access provided, try to get from context
            form_doc = context.get("form_doc")
            if form_doc and "schema" in form_doc:
                form_access = form_doc["schema"].get("access", {})
        
        if not form_access:
            # No access restrictions
            return PermissionEvaluationResult(allowed=True, reason="No form access restrictions")
        
        access_type = form_access.get("type")
        
        # Public access
        if access_type == "public":
            return PermissionEvaluationResult(allowed=True, reason="Public form access")
        
        # Org access
        if access_type == "org":
            org_id = resource.get("org_id")
            if resolve_org_role(decoded_token, org_id):
                return PermissionEvaluationResult(allowed=True, reason="Org form access")
            return PermissionEvaluationResult(allowed=False, reason="Not member of form org")
        
        # User access
        if access_type == "users":
            user_id = str(user_doc.get("_id"))
            allowed_users = [str(uid) for uid in form_access.get("allowed_user_ids", [])]
            if user_id in allowed_users:
                return PermissionEvaluationResult(allowed=True, reason="User form access")
            return PermissionEvaluationResult(allowed=False, reason="Not in allowed users list")
        
        # Group access
        if access_type == "groups":
            org_id = resource.get("org_id")
            user_groups = set(get_user_groups_from_claims_or_db(
                decoded_token, org_id, user_doc.get("_id")
            ))
            allowed_groups = {str(gid) for gid in form_access.get("allowed_group_ids", [])}
            if user_groups & allowed_groups:  # Intersection exists
                return PermissionEvaluationResult(allowed=True, reason="Group form access")
            return PermissionEvaluationResult(allowed=False, reason="Not in allowed groups")
        
        # Unknown access type
        return PermissionEvaluationResult(allowed=False, reason="Invalid form access type")
    
    def _step5_check_visibility_rules(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any], 
                                     resource: Dict[str, Any], action: str, 
                                     context: Dict[str, Any]) -> PermissionEvaluationResult:
        """Step 5: Check question/option visibility_rules (role condition)."""
        # This step is primarily for UI rendering and field-level access
        # For now, we'll assume it passes and implement detailed field-level checks separately
        return PermissionEvaluationResult(allowed=True, reason="Visibility rules not applicable")
    
    def _step6_evaluate_answer_conditions(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any], 
                                        resource: Dict[str, Any], action: str, 
                                        context: Dict[str, Any]) -> PermissionEvaluationResult:
        """Step 6: Evaluate answer-based conditions at render time."""
        # This step is for dynamic conditions based on form answers
        # For permission checks, this usually doesn't apply
        return PermissionEvaluationResult(allowed=True, reason="Answer conditions not applicable")


class PermissionService:
    """Centralized permission management service."""
    
    def __init__(self):
        self.abac_engine = ABACEngine()
    
    def check_permission(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any], 
                        action: str, resource: Dict[str, Any], 
                        context: Optional[Dict[str, Any]] = None) -> PermissionEvaluationResult:
        """
        Check if a user has permission to perform an action on a resource.
        
        Args:
            user_doc: User document from database
            decoded_token: Decoded JWT token
            action: Action to perform
            resource: Resource information
            context: Additional context
            
        Returns:
            PermissionEvaluationResult
        """
        return self.abac_engine.evaluate_permission(user_doc, decoded_token, action, resource, context)
    
    def check_field_permission(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any], 
                              action: str, resource: Dict[str, Any], 
                              field_path: str, context: Optional[Dict[str, Any]] = None) -> PermissionEvaluationResult:
        """
        Check field-level permissions.
        
        Args:
            user_doc: User document from database
            decoded_token: Decoded JWT token
            action: Action to perform (read, write, etc.)
            resource: Resource information
            field_path: Path to the field (e.g., "user.email", "form.questions[0].label")
            context: Additional context
            
        Returns:
            PermissionEvaluationResult
        """
        # First check basic permission
        base_result = self.check_permission(user_doc, decoded_token, action, resource, context)
        if not base_result.allowed:
            return base_result
        
        # Field-level checks would go here
        # For now, we'll allow all field access if base permission is granted
        return PermissionEvaluationResult(
            allowed=True,
            reason=f"Field access granted for {field_path}",
            effective_role=base_result.effective_role
        )
    
    def get_user_permissions(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any], 
                            org_id: Optional[str] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all permissions for a user in a given context.
        
        Args:
            user_doc: User document from database
            decoded_token: Decoded JWT token
            org_id: Organization ID context
            project_id: Project ID context
            
        Returns:
            Dictionary of permissions
        """
        permissions = {
            "system_role": user_doc.get("system_role", "user"),
            "org_roles": {},
            "project_roles": {},
            "effective_permissions": set(),
        }
        
        # Get org roles
        if org_id:
            org_role = resolve_org_role(decoded_token, org_id)
            if org_role:
                permissions["org_roles"][str(org_id)] = org_role
                permissions["effective_permissions"].update(ROLE_ACTIONS.get(org_role, set()))
        
        # Get project roles
        if project_id:
            project_doc = mongo.db.projects.find_one({
                "_id": ObjectId(project_id),
                "is_deleted": False
            })
            if project_doc:
                project_role = get_effective_project_role(user_doc, decoded_token, project_doc)
                if project_role:
                    permissions["project_roles"][str(project_id)] = project_role
                    permissions["effective_permissions"].update(ROLE_ACTIONS.get(project_role, set()))
        
        # Convert set to list for JSON serialization
        permissions["effective_permissions"] = list(permissions["effective_permissions"])
        
        return permissions
    
    def can_edit_resource(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any], 
                         resource: Dict[str, Any]) -> bool:
        """Check if user can edit a resource."""
        edit_actions = ["edit_form", "edit_project", "edit_org", "edit_analysis", "edit_dashboard"]
        
        for action in edit_actions:
            result = self.check_permission(user_doc, decoded_token, action, resource)
            if result.allowed:
                return True
        
        return False
    
    def can_delete_resource(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any], 
                           resource: Dict[str, Any]) -> bool:
        """Check if user can delete a resource."""
        delete_actions = ["delete_form", "delete_project", "delete_org", "delete_analysis", "delete_dashboard"]
        
        for action in delete_actions:
            result = self.check_permission(user_doc, decoded_token, action, resource)
            if result.allowed:
                return True
        
        return False
    
    def can_view_resource(self, user_doc: Dict[str, Any], decoded_token: Dict[str, Any], 
                         resource: Dict[str, Any]) -> bool:
        """Check if user can view a resource."""
        view_actions = ["view_form", "view_project", "view_org", "view_analysis", "view_dashboard", "view_responses"]
        
        for action in view_actions:
            result = self.check_permission(user_doc, decoded_token, action, resource)
            if result.allowed:
                return True
        
        return False


# Global instance
permission_service = PermissionService()