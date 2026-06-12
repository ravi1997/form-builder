"""
Field-Level Permissions System

This system provides granular access control at the field level within documents.
It extends the ABAC system to control access to specific fields based on user roles,
groups, and other attributes.
"""

import logging
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum

from bson import ObjectId
from app.services.auth_service import resolve_org_role, get_user_groups_from_claims_or_db
from app.services.permission_service import PermissionEvaluationResult

logger = logging.getLogger(__name__)


class FieldPermission(str, Enum):
    """Field permission types."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    VIEW = "view"  # For sensitive fields (show but mask)
    HIDDEN = "hidden"  # Completely hide field


class FieldAccessLevel(str, Enum):
    """Field access levels."""
    PUBLIC = "public"  # Everyone can access
    ORG_ADMIN = "org_admin"  # Only organization admins
    PROJECT_OWNER = "project_owner"  # Only project owners
    ROLE_BASED = "role_based"  # Based on specific roles
    GROUP_BASED = "group_based"  # Based on group membership
    CUSTOM = "custom"  # Custom rules


class FieldPermissionRule:
    """Rule for field-level permissions."""
    
    def __init__(self, field_path: str, access_level: FieldAccessLevel, 
                 permissions: Set[FieldPermission], 
                 roles: Optional[List[str]] = None,
                 groups: Optional[List[str]] = None,
                 custom_condition: Optional[Dict[str, Any]] = None):
        self.field_path = field_path
        self.access_level = access_level
        self.permissions = permissions
        self.roles = roles or []
        self.groups = groups or []
        self.custom_condition = custom_condition or {}


class FieldPermissionEngine:
    """Engine for evaluating field-level permissions."""
    
    def __init__(self):
        self.field_rules: Dict[str, List[FieldPermissionRule]] = {}
        self.default_permissions = {
            "public_fields": ["id", "created_at", "updated_at"],
            "protected_fields": ["password_hash", "two_factor_secret"],
            "sensitive_fields": ["email", "phone", "ip_address"]
        }
    
    def add_field_rule(self, rule: FieldPermissionRule):
        """Add a field permission rule."""
        if rule.field_path not in self.field_rules:
            self.field_rules[rule.field_path] = []
        self.field_rules[rule.field_path].append(rule)
    
    def evaluate_field_permission(self, user_doc: Dict[str, Any], 
                                decoded_token: Dict[str, Any],
                                field_path: str, 
                                permission: FieldPermission,
                                resource: Dict[str, Any] = None,
                                context: Dict[str, Any] = None) -> PermissionEvaluationResult:
        """
        Evaluate field-level permission.
        
        Args:
            user_doc: User document
            decoded_token: Decoded JWT token
            field_path: Path to the field (e.g., "user.email", "form.questions[0].label")
            permission: Permission to check
            resource: Resource context
            context: Additional context
            
        Returns:
            Permission evaluation result
        """
        context = context or {}
        resource = resource or {}
        
        # Check default permissions first
        if self._check_default_permissions(field_path, permission, user_doc):
            return PermissionEvaluationResult(
                allowed=True,
                reason=f"Default permission granted for {field_path}"
            )
        
        # Check field-specific rules
        rules = self.field_rules.get(field_path, [])
        for rule in rules:
            if permission not in rule.permissions:
                continue
                
            result = self._evaluate_field_rule(rule, user_doc, decoded_token, resource, context)
            if result.allowed:
                return result
        
        # If no rules match, deny access
        return PermissionEvaluationResult(
            allowed=False,
            reason=f"No permission rule found for {field_path}"
        )
    
    def _check_default_permissions(self, field_path: str, permission: FieldPermission, 
                                 user_doc: Dict[str, Any]) -> bool:
        """Check default field permissions."""
        # Public fields are always readable
        if (permission == FieldPermission.READ and 
            field_path in self.default_permissions["public_fields"]):
            return True
        
        # Protected fields are never accessible
        if field_path in self.default_permissions["protected_fields"]:
            return False
        
        # Sensitive fields require special handling
        if field_path in self.default_permissions["sensitive_fields"]:
            # Only allow view permission for sensitive fields
            return permission == FieldPermission.VIEW
        
        return False
    
    def _evaluate_field_rule(self, rule: FieldPermissionRule, user_doc: Dict[str, Any],
                           decoded_token: Dict[str, Any], resource: Dict[str, Any],
                           context: Dict[str, Any]) -> PermissionEvaluationResult:
        """Evaluate a single field permission rule."""
        
        # Check access level
        if rule.access_level == FieldAccessLevel.PUBLIC:
            return PermissionEvaluationResult(
                allowed=True,
                reason=f"Public access granted for {rule.field_path}"
            )
        
        # Check org admin access
        if rule.access_level == FieldAccessLevel.ORG_ADMIN:
            org_id = resource.get("org_id") or context.get("org_id")
            if org_id:
                org_role = resolve_org_role(decoded_token, org_id)
                if org_role == "org_admin":
                    return PermissionEvaluationResult(
                        allowed=True,
                        reason=f"Org admin access granted for {rule.field_path}",
                        effective_role="org_admin"
                    )
            return PermissionEvaluationResult(
                allowed=False,
                reason=f"Org admin access required for {rule.field_path}"
            )
        
        # Check project owner access
        if rule.access_level == FieldAccessLevel.PROJECT_OWNER:
            project_id = resource.get("project_id") or context.get("project_id")
            if project_id:
                project_doc = context.get("project_doc")
                if not project_doc:
                    from app.services.auth_service import get_effective_project_role
                    # Try to get project from database
                    from app.extensions import mongo
                    project_doc = mongo.db.projects.find_one({
                        "_id": ObjectId(project_id),
                        "is_deleted": False
                    })
                
                if project_doc:
                    effective_role = get_effective_project_role(user_doc, decoded_token, project_doc)
                    if effective_role == "project_owner":
                        return PermissionEvaluationResult(
                            allowed=True,
                            reason=f"Project owner access granted for {rule.field_path}",
                            effective_role="project_owner"
                        )
            
            return PermissionEvaluationResult(
                allowed=False,
                reason=f"Project owner access required for {rule.field_path}"
            )
        
        # Check role-based access
        if rule.access_level == FieldAccessLevel.ROLE_BASED and rule.roles:
            system_role = user_doc.get("system_role") or decoded_token.get("system_role")
            if system_role in rule.roles:
                return PermissionEvaluationResult(
                    allowed=True,
                    reason=f"Role-based access granted for {rule.field_path}",
                    effective_role=system_role
                )
            
            # Check org roles
            org_id = resource.get("org_id") or context.get("org_id")
            if org_id:
                org_role = resolve_org_role(decoded_token, org_id)
                if org_role in rule.roles:
                    return PermissionEvaluationResult(
                        allowed=True,
                        reason=f"Role-based access granted for {rule.field_path}",
                        effective_role=org_role
                    )
            
            return PermissionEvaluationResult(
                allowed=False,
                reason=f"Required role not found for {rule.field_path}"
            )
        
        # Check group-based access
        if rule.access_level == FieldAccessLevel.GROUP_BASED and rule.groups:
            org_id = resource.get("org_id") or context.get("org_id")
            if org_id:
                user_groups = set(get_user_groups_from_claims_or_db(
                    decoded_token, org_id, user_doc.get("_id")
                ))
                required_groups = set(rule.groups)
                
                if user_groups & required_groups:  # Intersection exists
                    return PermissionEvaluationResult(
                        allowed=True,
                        reason=f"Group-based access granted for {rule.field_path}"
                    )
            
            return PermissionEvaluationResult(
                allowed=False,
                reason=f"Required group membership not found for {rule.field_path}"
            )
        
        # Check custom condition
        if rule.access_level == FieldAccessLevel.CUSTOM and rule.custom_condition:
            if self._evaluate_custom_condition(rule.custom_condition, user_doc, decoded_token, context):
                return PermissionEvaluationResult(
                    allowed=True,
                    reason=f"Custom condition granted for {rule.field_path}"
                )
            
            return PermissionEvaluationResult(
                allowed=False,
                reason=f"Custom condition not met for {rule.field_path}"
            )
        
        return PermissionEvaluationResult(
            allowed=False,
            reason=f"Invalid access level for {rule.field_path}"
        )
    
    def _evaluate_custom_condition(self, condition: Dict[str, Any], user_doc: Dict[str, Any],
                                 decoded_token: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate custom condition for field access."""
        # This is a simple implementation - can be extended with more complex logic
        condition_type = condition.get("type")
        
        if condition_type == "user_attribute":
            attr_name = condition.get("attribute")
            expected_value = condition.get("value")
            actual_value = user_doc.get(attr_name)
            return actual_value == expected_value
        
        elif condition_type == "token_claim":
            claim_name = condition.get("claim")
            expected_value = condition.get("value")
            actual_value = decoded_token.get(claim_name)
            return actual_value == expected_value
        
        elif condition_type == "context":
            context_key = condition.get("key")
            expected_value = condition.get("value")
            actual_value = context.get(context_key)
            return actual_value == expected_value
        
        return False
    
    def filter_document_fields(self, user_doc: Dict[str, Any], 
                              decoded_token: Dict[str, Any],
                              document: Dict[str, Any], 
                              permission: FieldPermission,
                              resource: Dict[str, Any] = None,
                              context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Filter a document based on field permissions.
        
        Args:
            user_doc: User document
            decoded_token: Decoded JWT token
            document: Document to filter
            permission: Permission to check
            resource: Resource context
            context: Additional context
            
        Returns:
            Filtered document
        """
        if not isinstance(document, dict):
            return document
        
        filtered_doc = {}
        context = context or {}
        resource = resource or {}
        
        for field_path, field_value in document.items():
            # Skip protected fields
            if field_path in self.default_permissions["protected_fields"]:
                continue
            
            # Check field permission
            result = self.evaluate_field_permission(
                user_doc, decoded_token, field_path, permission, resource, context
            )
            
            if result.allowed:
                if field_path in self.default_permissions["sensitive_fields"] and permission == FieldPermission.VIEW:
                    # Mask sensitive fields
                    filtered_doc[field_path] = "***MASKED***"
                else:
                    # Recursively filter nested objects
                    if isinstance(field_value, dict):
                        filtered_doc[field_path] = self.filter_document_fields(
                            user_doc, decoded_token, field_value, permission, resource, context
                        )
                    elif isinstance(field_value, list):
                        filtered_doc[field_path] = [
                            self.filter_document_fields(
                                user_doc, decoded_token, item, permission, resource, context
                            ) if isinstance(item, dict) else item
                            for item in field_value
                        ]
                    else:
                        filtered_doc[field_path] = field_value
        
        return filtered_doc
    
    def get_accessible_fields(self, user_doc: Dict[str, Any], 
                             decoded_token: Dict[str, Any],
                             field_paths: List[str], 
                             permission: FieldPermission,
                             resource: Dict[str, Any] = None,
                             context: Dict[str, Any] = None) -> List[str]:
        """
        Get list of accessible fields for a user.
        
        Args:
            user_doc: User document
            decoded_token: Decoded JWT token
            field_paths: List of field paths to check
            permission: Permission to check
            resource: Resource context
            context: Additional context
            
        Returns:
            List of accessible field paths
        """
        accessible_fields = []
        context = context or {}
        resource = resource or {}
        
        for field_path in field_paths:
            result = self.evaluate_field_permission(
                user_doc, decoded_token, field_path, permission, resource, context
            )
            if result.allowed:
                accessible_fields.append(field_path)
        
        return accessible_fields


class FieldPermissionService:
    """Service for managing field-level permissions."""
    
    def __init__(self):
        self.engine = FieldPermissionEngine()
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default field permission rules."""
        # User document field rules
        user_field_rules = [
            FieldPermissionRule(
                field_path="password_hash",
                access_level=FieldAccessLevel.CUSTOM,
                permissions={FieldPermission.HIDDEN},
                custom_condition={"type": "always_false"}
            ),
            FieldPermissionRule(
                field_path="two_factor_secret",
                access_level=FieldAccessLevel.CUSTOM,
                permissions={FieldPermission.HIDDEN},
                custom_condition={"type": "always_false"}
            ),
            FieldPermissionRule(
                field_path="email",
                access_level=FieldAccessLevel.ROLE_BASED,
                permissions={FieldPermission.READ, FieldPermission.VIEW},
                roles=["super_admin", "org_admin"]
            ),
            FieldPermissionRule(
                field_path="phone",
                access_level=FieldAccessLevel.ROLE_BASED,
                permissions={FieldPermission.READ, FieldPermission.VIEW},
                roles=["super_admin", "org_admin"]
            ),
        ]
        
        for rule in user_field_rules:
            self.engine.add_field_rule(rule)
    
    def check_field_permission(self, user_doc: Dict[str, Any], 
                              decoded_token: Dict[str, Any],
                              field_path: str, 
                              permission: FieldPermission,
                              resource: Dict[str, Any] = None,
                              context: Dict[str, Any] = None) -> PermissionEvaluationResult:
        """Check field permission."""
        return self.engine.evaluate_field_permission(
            user_doc, decoded_token, field_path, permission, resource, context
        )
    
    def filter_sensitive_fields(self, user_doc: Dict[str, Any], 
                              decoded_token: Dict[str, Any],
                              document: Dict[str, Any], 
                              resource: Dict[str, Any] = None,
                              context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Filter sensitive fields from a document."""
        return self.engine.filter_document_fields(
            user_doc, decoded_token, document, FieldPermission.READ, resource, context
        )
    
    def get_readable_fields(self, user_doc: Dict[str, Any], 
                           decoded_token: Dict[str, Any],
                           field_paths: List[str], 
                           resource: Dict[str, Any] = None,
                           context: Dict[str, Any] = None) -> List[str]:
        """Get list of readable fields."""
        return self.engine.get_accessible_fields(
            user_doc, decoded_token, field_paths, FieldPermission.READ, resource, context
        )
    
    def get_writable_fields(self, user_doc: Dict[str, Any], 
                           decoded_token: Dict[str, Any],
                           field_paths: List[str], 
                           resource: Dict[str, Any] = None,
                           context: Dict[str, Any] = None) -> List[str]:
        """Get list of writable fields."""
        return self.engine.get_accessible_fields(
            user_doc, decoded_token, field_paths, FieldPermission.WRITE, resource, context
        )


# Global instance
field_permission_service = FieldPermissionService()