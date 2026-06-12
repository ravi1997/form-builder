import datetime
import hashlib
import os
import re
import secrets
from typing import Any, Optional, Dict, List
import logging

import bcrypt
import jwt
from bson import ObjectId
from flask import current_app, has_app_context

from app.extensions import mongo
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)


ACCESS_TOKEN_TTL_SECONDS = 900
REFRESH_TOKEN_TTL_DAYS = 30
EMAIL_VERIFICATION_TTL_HOURS = 24
PASSWORD_RESET_TTL_HOURS = 1
INVITATION_TTL_DAYS = 7
COMMON_PASSWORDS = {
    "password",
    "password1",
    "password123",
    "admin123",
    "qwerty123",
}
PASSWORD_HISTORY_COUNT = 5
PASSWORD_RESET_TOKEN_COLLECTION = "password_reset_tokens"
ORG_ROLES = {"org_admin", "org_editor", "org_analyst", "org_viewer"}
PROJECT_ROLES = {"project_owner", "project_editor", "project_analyst", "project_viewer"}
USER_ROLES = {"super_admin", "user"}

ORG_TO_PROJECT_ROLE = {
    "org_admin": "project_owner",
    "org_editor": "project_editor",
    "org_analyst": "project_analyst",
    "org_viewer": "project_viewer",
}

ROLE_ACTIONS = {
    "project_owner": {"edit_project", "manage_project_members", "create_form", "edit_form", "publish_form", "create_branch", "merge_branch", "delete_form", "view_responses", "export_responses", "create_analysis", "run_analysis", "delete_analysis", "create_dashboard", "edit_dashboard", "delete_dashboard"},
    "project_editor": {"create_form", "edit_form", "publish_form", "create_branch", "merge_branch", "view_responses", "export_responses", "create_analysis", "run_analysis", "create_dashboard", "edit_dashboard"},
    "project_analyst": {"view_responses", "export_responses", "create_analysis", "run_analysis", "create_dashboard", "edit_dashboard"},
    "project_viewer": {"view_responses"},
    "org_admin": {"invite_member", "change_member_role", "suspend_member", "remove_member", "edit_org_settings", "manage_org_groups", "adopt_compliance", "view_audit_logs", "create_project", "delete_project", "create_form", "edit_form", "publish_form", "delete_form", "view_responses", "export_responses", "create_analysis", "run_analysis", "delete_analysis", "create_dashboard", "edit_dashboard", "manage_api_keys", "create_project_api_key"},
    "org_editor": {"create_project", "create_form", "edit_form", "publish_form", "view_responses", "export_responses", "create_analysis", "run_analysis", "create_dashboard", "edit_dashboard"},
    "org_analyst": {"view_responses", "export_responses", "create_analysis", "run_analysis", "create_dashboard", "edit_dashboard"},
    "org_viewer": {"view_responses"},
}


def _now():
    return datetime.datetime.utcnow()


def _oid(value):
    if isinstance(value, ObjectId):
        return value
    if value and ObjectId.is_valid(str(value)):
        return ObjectId(str(value))
    return value


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def hash_password(password: str) -> str:
    return _hash_password(password)


def _verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def validate_password_policy(password: str, email: str = "", display_name: str = ""):
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(password) > 128:
        raise ValueError("Password must be at most 128 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"|,.<>/?]", password):
        raise ValueError("Password must contain at least one special character")
    if password.lower() in COMMON_PASSWORDS:
        raise ValueError("Password is too common")
    email_prefix = (email or "").split("@", 1)[0].lower()
    if email_prefix and email_prefix in password.lower():
        raise ValueError("Password may not contain the email prefix")
    if display_name and display_name.lower() in password.lower():
        raise ValueError("Password may not contain the display name")


def _password_history_matches(user_doc, new_password: str) -> bool:
    password_history = user_doc.get("password_history", [])[-PASSWORD_HISTORY_COUNT:]
    for hashed in password_history:
        try:
            if bcrypt.checkpw(new_password.encode("utf-8"), hashed.encode("utf-8")):
                return True
        except Exception:
            continue
    return False


def rotate_user_password(user_doc, new_password: str):
    validate_password_policy(new_password, email=user_doc.get("email", ""), display_name=user_doc.get("display_name", ""))
    if _password_history_matches(user_doc, new_password):
        raise ValueError("Password reuse is not allowed")
    current_hash = user_doc.get("password_hash")
    new_hash = _hash_password(new_password)
    history = list(user_doc.get("password_history", []))
    if current_hash:
        history.append(current_hash)
    history = history[-PASSWORD_HISTORY_COUNT:]
    mongo.db.users.update_one(
        {"_id": user_doc["_id"]},
        {
            "$set": {
                "password_hash": new_hash,
                "password_history": history,
                "password_changed_at": _now(),
                "updated_at": _now(),
            }
        },
    )
    revoke_all_sessions_for_user(user_doc["_id"])
    return new_hash


def _refresh_token_hash(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def _jwt_secret() -> str:
    if has_app_context() and current_app.config.get("JWT_SECRET_KEY"):
        return current_app.config["JWT_SECRET_KEY"]
    return os.environ.get("JWT_SECRET_KEY", "jwt-secret-key-change-in-prod")


def evaluate_dynamic_rule_condition(cond: dict, candidate: dict) -> bool:
    field = cond.get("field")
    operator = cond.get("operator", "equals")
    value = cond.get("value")
    if not field:
        return False
    candidate_val = candidate.get(field, "")
    
    # Standardize type for string comparisons
    c_val_str = str(candidate_val) if candidate_val is not None else ""
    val_str = str(value) if value is not None else ""
    
    if operator in ("equals", "eq"):
        return c_val_str == val_str
    elif operator in ("not_equals", "ne"):
        return c_val_str != val_str
    elif operator == "contains":
        return val_str.lower() in c_val_str.lower()
    elif operator == "starts_with":
        return c_val_str.lower().startswith(val_str.lower())
    elif operator == "ends_with":
        return c_val_str.lower().endswith(val_str.lower())
    elif operator == "in":
        if isinstance(value, list):
            return candidate_val in value
        return candidate_val in [x.strip() for x in val_str.split(",")]
    return False


def evaluate_dynamic_rule(r: dict, candidate: dict) -> bool:
    if not isinstance(r, dict):
        return False
    if "logical_operator" in r or "conditions" in r:
        op = r.get("logical_operator", "AND").upper()
        conditions = r.get("conditions", [])
        if not conditions:
            return op == "AND"
        if op == "AND":
            return all(evaluate_dynamic_rule(cond, candidate) for cond in conditions)
        elif op == "OR":
            return any(evaluate_dynamic_rule(cond, candidate) for cond in conditions)
        elif op == "NOT":
            return not evaluate_dynamic_rule(conditions[0] if conditions else {}, candidate)
        return False
    else:
        return evaluate_dynamic_rule_condition(r, candidate)


def is_user_in_group(user_doc, membership, group):
    if not user_doc or not group:
        return False
    if group.get("type") == "static":
        return mongo.db.group_members.find_one({
            "group_id": _oid(group["_id"]),
            "user_id": _oid(user_doc["_id"]),
            "is_deleted": False
        }) is not None
    elif group.get("type") == "dynamic":
        if not membership:
            return False
        candidate = {
            "role": membership.get("role"),
            "membership_status": membership.get("status"),
            "email": user_doc.get("email"),
            "full_name": user_doc.get("full_name"),
            "status": user_doc.get("status")
        }
        return evaluate_dynamic_rule(group.get("dynamic_rule") or {}, candidate)
    return False


def _active_org_claims(user_id):
    user_doc = mongo.db.users.find_one({"_id": _oid(user_id), "is_deleted": False})
    if not user_doc:
        return []
    memberships = mongo.db.org_memberships.find(
        {"user_id": _oid(user_id), "is_deleted": False, "status": "active"}
    )
    claims = []
    for membership in memberships:
        org_id = membership.get("org_id")
        groups = mongo.db.groups.find({"org_id": _oid(org_id), "is_deleted": False})
        group_ids = []
        for group in groups:
            if is_user_in_group(user_doc, membership, group):
                group_ids.append(str(group["_id"]))
        claims.append(
            {
                "org_id": str(org_id),
                "role": membership.get("role", "org_viewer"),
                "status": membership.get("status", "active"),
                "group_ids": group_ids,
            }
        )
    return claims


def build_access_token(user_doc):
    now = int(_now().timestamp())
    payload = {
        "sub": str(user_doc["_id"]),
        "email": user_doc.get("email"),
        "system_role": user_doc.get("system_role", "user"),
        "orgs": _active_org_claims(user_doc["_id"]),
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def build_refresh_token(user_doc, device_info=None, ip_address=None):
    now = _now()
    raw = f"{user_doc['_id']}:{now.isoformat()}:{os.urandom(16).hex()}"
    refresh_token = hashlib.sha256(raw.encode("utf-8")).hexdigest() + "." + os.urandom(16).hex()
    refresh_hash = _refresh_token_hash(refresh_token)
    expires_at = now + datetime.timedelta(days=REFRESH_TOKEN_TTL_DAYS)
    mongo.db.sessions.insert_one(
        {
            "_id": ObjectId(),
            "user_id": _oid(user_doc["_id"]),
            "refresh_token_hash": refresh_hash,
            "device_info": device_info or {},
            "ip_address": ip_address,
            "created_at": now,
            "expires_at": expires_at,
            "last_used_at": None,
            "is_deleted": False,
        }
    )
    return refresh_token


def register_user(email: str, password: str, full_name: str, ip_address: str = None):
    """Register a new user with audit logging"""
    existing = mongo.db.users.find_one({"email": email.lower(), "is_deleted": False})
    if existing:
        raise ValueError("Email already exists")
    
    validate_password_policy(password, email=email, display_name=full_name)

    user_doc = {
        "_id": ObjectId(),
        "email": email.lower(),
        "password_hash": _hash_password(password),
        "full_name": full_name,
        "display_name": full_name,
        "avatar_url": None,
        "phone": None,
        "status": "pending_approval",
        "system_role": "user",
        "email_verified": False,
        "phone_verified": False,
        "last_login_at": None,
        "login_count": 0,
        "failed_login_attempts": 0,
        "locked_until": None,
        "two_factor_enabled": False,
        "two_factor_secret": None,
        "notification_preferences": {
            "email": True,
            "sms": True,
            "push": True,
            "in_app": True,
        },
        "device_tokens": [],
        "created_at": _now(),
        "updated_at": _now(),
        "approved_at": None,
        "approved_by": None,
        "is_deleted": False,
        "deleted_at": None,
    }
    
    result = mongo.db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id
    
    # Log audit event
    try:
        audit_service.log_action(
            entity_type="user",
            entity_id=user_doc["_id"],
            action="register",
            actor_id=user_doc["_id"],
            actor_role="user",
            before={},
            after={"email": email.lower(), "full_name": full_name, "status": "pending_approval"},
            ip_address=ip_address
        )
    except Exception as e:
        # Don't fail registration if audit logging fails
        logger.error(f"Failed to log user registration audit event: {e}")
    
    return user_doc


def login_user(email: str, password: str, device_info=None, ip_address=None):
    """Login user with audit logging and security checks"""
    user_doc = mongo.db.users.find_one({"email": email.lower(), "is_deleted": False})
    if not user_doc:
        # Log failed login attempt
        try:
            audit_service.log_action(
                entity_type="user",
                entity_id=ObjectId(),
                action="login_failed",
                actor_id=ObjectId(),
                actor_role="anonymous",
                before={},
                after={"email": email.lower(), "reason": "user_not_found"},
                ip_address=ip_address
            )
        except Exception as e:
            logger.error(f"Failed to log failed login audit event: {e}")
        raise ValueError("Invalid credentials")
    
    # Check if user is active
    if user_doc.get("status") != "active":
        try:
            audit_service.log_action(
                entity_type="user",
                entity_id=user_doc["_id"],
                action="login_failed",
                actor_id=user_doc["_id"],
                actor_role=user_doc.get("system_role", "user"),
                before={},
                after={"email": email.lower(), "reason": f"user_status_{user_doc.get('status')}"},
                ip_address=ip_address
            )
        except Exception as e:
            logger.error(f"Failed to log failed login audit event: {e}")
        raise ValueError("User is not active")
    
    # Check if account is locked
    if user_doc.get("locked_until") and user_doc["locked_until"] > _now():
        try:
            audit_service.log_action(
                entity_type="user",
                entity_id=user_doc["_id"],
                action="login_failed",
                actor_id=user_doc["_id"],
                actor_role=user_doc.get("system_role", "user"),
                before={},
                after={"email": email.lower(), "reason": "account_locked"},
                ip_address=ip_address
            )
        except Exception as e:
            logger.error(f"Failed to log failed login audit event: {e}")
        raise ValueError("Account is temporarily locked")
    
    # Verify password
    if not _verify_password(password, user_doc.get("password_hash", "")):
        # Increment failed login attempts
        mongo.db.users.update_one(
            {"_id": user_doc["_id"]},
            {"$inc": {"failed_login_attempts": 1}}
        )
        
        # Lock account if too many failed attempts
        failed_attempts = user_doc.get("failed_login_attempts", 0) + 1
        if failed_attempts >= 5:
            lock_until = _now() + datetime.timedelta(minutes=15)
            mongo.db.users.update_one(
                {"_id": user_doc["_id"]},
                {
                    "$set": {
                        "locked_until": lock_until,
                        "failed_login_attempts": failed_attempts
                    }
                }
            )
        
        # Log failed login
        try:
            audit_service.log_action(
                entity_type="user",
                entity_id=user_doc["_id"],
                action="login_failed",
                actor_id=user_doc["_id"],
                actor_role=user_doc.get("system_role", "user"),
                before={},
                after={"email": email.lower(), "reason": "invalid_password"},
                ip_address=ip_address
            )
        except Exception as e:
            logger.error(f"Failed to log failed login audit event: {e}")
        
        raise ValueError("Invalid credentials")

    # Reset failed login attempts on successful login
    mongo.db.users.update_one(
        {"_id": user_doc["_id"]},
        {
            "$set": {
                "failed_login_attempts": 0,
                "locked_until": None
            }
        }
    )

    access_token = build_access_token(user_doc)
    refresh_token = build_refresh_token(user_doc, device_info=device_info, ip_address=ip_address)
    
    # Update user login info
    mongo.db.users.update_one(
        {"_id": user_doc["_id"]},
        {
            "$set": {
                "last_login_at": _now(),
                "updated_at": _now(),
            },
            "$inc": {"login_count": 1},
        },
    )
    
    # Log successful login
    try:
        audit_service.log_action(
            entity_type="user",
            entity_id=user_doc["_id"],
            action="login",
            actor_id=user_doc["_id"],
            actor_role=user_doc.get("system_role", "user"),
            before={},
            after={"email": email.lower(), "login_count": user_doc.get("login_count", 0) + 1},
            ip_address=ip_address,
            user_agent=device_info.get("user_agent") if device_info else None
        )
    except Exception as e:
        logger.error(f"Failed to log login audit event: {e}")
    
    return access_token, refresh_token, user_doc


def refresh_access_token(refresh_token: str, ip_address=None):
    refresh_hash = _refresh_token_hash(refresh_token)
    session_doc = mongo.db.sessions.find_one({"refresh_token_hash": refresh_hash, "is_deleted": False})
    if not session_doc:
        if refresh_hash:
            stale_session = mongo.db.sessions.find_one({"refresh_token_hash": refresh_hash})
            if stale_session:
                revoke_all_sessions_for_user(stale_session.get("user_id"))
                raise PermissionError("REFRESH_TOKEN_REUSE_DETECTED")
        raise ValueError("Invalid refresh token")
    if session_doc.get("expires_at") and session_doc["expires_at"] < _now():
        raise ValueError("Refresh token expired")

    user_doc = mongo.db.users.find_one({"_id": _oid(session_doc["user_id"]), "is_deleted": False})
    if not user_doc or user_doc.get("status") != "active":
        raise ValueError("Invalid refresh token")

    new_access_token = build_access_token(user_doc)
    new_refresh_token = build_refresh_token(user_doc, device_info=session_doc.get("device_info"), ip_address=ip_address or session_doc.get("ip_address"))

    mongo.db.sessions.update_one(
        {"_id": session_doc["_id"]},
        {
            "$set": {
                "is_deleted": True,
                "deleted_at": _now(),
                "revoked_at": _now(),
                "revoked_reason": "rotated",
            }
        },
    )
    return new_access_token, new_refresh_token


def verify_bearer_token(token: str):
    decoded = jwt.decode(token, _jwt_secret(), algorithms=["HS256"], options={"verify_exp": False})
    if not decoded.get("sub") or not decoded.get("email"):
        raise ValueError("Invalid token")
    if decoded.get("exp", 0) < int(_now().timestamp()):
        raise ValueError("Token expired")

    user_doc = mongo.db.users.find_one({"_id": _oid(decoded.get("sub")), "is_deleted": False})
    if not user_doc or user_doc.get("status") != "active":
        raise ValueError("Invalid token")
    return user_doc, decoded


def decode_request_bearer_token(auth_header: str):
    if not auth_header.startswith("Bearer "):
        raise ValueError("Bearer token required")
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise ValueError("Bearer token required")
    return verify_bearer_token(token)


def resolve_org_role(decoded_token: dict[str, Any], org_id):
    org_oid = str(org_id)
    for claim in decoded_token.get("orgs", []):
        if str(claim.get("org_id")) == org_oid and claim.get("status") == "active":
            return claim.get("role")
    return None


def get_effective_project_role(user_doc, decoded_token: dict[str, Any], project_doc):
    if user_doc.get("system_role") == "super_admin":
        return "project_owner"
    project_membership = mongo.db.project_members.find_one(
        {"project_id": project_doc["_id"], "user_id": _oid(user_doc["_id"]), "is_deleted": False}
    )
    if project_membership and project_membership.get("status", "active") == "active":
        return project_membership.get("role")
    org_role = resolve_org_role(decoded_token, project_doc.get("org_id"))
    if org_role:
        return ORG_TO_PROJECT_ROLE.get(org_role)
    if project_doc.get("shared_org_ids"):
        user_org_ids = {claim.get("org_id") for claim in decoded_token.get("orgs", []) if claim.get("status") == "active"}
        if any(str(org_id) in user_org_ids for org_id in project_doc.get("shared_org_ids", [])):
            return "project_viewer"
    return None


def check_permission(user_doc, decoded_token: dict[str, Any], action: str, resource: dict, context: str | None = None):
    """
    Comprehensive ABAC (Attribute-Based Access Control) evaluation
    
    Evaluation Order:
    1. Check system_role (super_admin bypasses all)
    2. Check org membership + role for the resource's org
    3. Check project membership + role
    4. Check form-level access settings
    5. Check question/option visibility_rules (role condition)
    6. Evaluate answer-based conditions at render time
    """
    system_role = user_doc.get("system_role") if user_doc else None
    if system_role == "super_admin" or decoded_token.get("system_role") == "super_admin":
        return True
    
    resource_type = resource.get("type")
    org_id = resource.get("org_id")
    project_id = resource.get("project_id")
    
    # Step 2: Check org membership and status
    if org_id is not None:
        org_doc = mongo.db.organisations.find_one({"_id": _oid(org_id), "is_deleted": False})
        if org_doc and org_doc.get("status") == "suspended":
            return False
    
    # Step 3: Check project-level access if applicable
    if resource_type == "project" or project_id is not None:
        project_doc = resource.get("project_doc") or mongo.db.projects.find_one({"_id": _oid(project_id), "is_deleted": False})
        if not project_doc:
            return False
        if project_doc.get("status") == "suspended":
            return False
        
        effective_role = get_effective_project_role(user_doc, decoded_token, project_doc)
        if not effective_role:
            return False
        
        # Check if action is allowed for this role
        allowed_actions = ROLE_ACTIONS.get(effective_role, set())
        if action not in allowed_actions:
            return False
        
        # Additional project-specific checks
        if resource_type == "form":
            form_access = resource.get("form_access")
            if form_access and not _check_form_access(form_access, decoded_token, org_id):
                return False
        
        return True
    
    # Step 4: Check org-level access
    if resource_type == "org":
        org_role = resolve_org_role(decoded_token, org_id)
        if not org_role:
            return False
        
        allowed_actions = ROLE_ACTIONS.get(org_role, set())
        return action in allowed_actions
    
    # Step 5: Check user-level access
    if resource_type == "user":
        target_user_id = resource.get("user_id")
        user_id = user_doc.get("_id") if user_doc else ObjectId(decoded_token.get("sub"))
        
        # Users can always view/edit their own profile
        if str(target_user_id) == str(user_id):
            return action in {"view_own_profile", "edit_own_profile"}
        
        # Other user actions require org_admin role
        org_role = resolve_org_role(decoded_token, org_id)
        if org_role == "org_admin":
            return action in ROLE_ACTIONS.get("org_admin", set())
        
        return False
    
    # Default deny
    return False


def _check_form_access(form_access: dict, decoded_token: dict, org_id: Optional[str]) -> bool:
    """Check form-level access settings"""
    access_type = form_access.get("type")
    
    if access_type == "public":
        return True
    
    if access_type == "org":
        return resolve_org_role(decoded_token, org_id) is not None
    
    if access_type == "users":
        user_id = decoded_token.get("sub")
        allowed_user_ids = form_access.get("allowed_user_ids", [])
        return str(user_id) in {str(uid) for uid in allowed_user_ids}
    
    if access_type == "groups":
        user_groups = get_user_groups_from_claims_or_db(decoded_token, org_id, decoded_token.get("sub"))
        allowed_groups = form_access.get("allowed_group_ids", [])
        return any(str(group_id) in {str(gid) for gid in allowed_groups} for group_id in user_groups)
    
    return False


def evaluate_visibility_rules(element: dict, decoded_token: dict[str, Any], current_answers=None, resource_org_id=None, resource_context=None):
    """
    Evaluate visibility rules for form elements
    
    Supports:
    - Role-based visibility
    - Group-based visibility  
    - Answer-based conditional visibility
    - Always visible/hidden flags
    """
    rules = element.get("visibility_rules")
    current_answers = current_answers or {}
    
    if not rules or not rules.get("conditions"):
        return True
    
    results = []
    for condition in rules.get("conditions", []):
        ctype = condition.get("type")
        
        if ctype == "always_visible":
            return True
        
        if ctype == "always_hidden":
            return False
        
        if ctype == "role":
            effective_role = None
            if resource_context and resource_context.get("project_doc"):
                effective_role = get_effective_project_role(resource_context.get("user_doc"), decoded_token, resource_context["project_doc"])
            elif resource_org_id is not None:
                effective_role = resolve_org_role(decoded_token, resource_org_id)
            
            allowed_roles = condition.get("roles", [])
            results.append(effective_role in allowed_roles)
        
        elif ctype == "group":
            user_groups = get_user_groups_from_claims_or_db(decoded_token, resource_org_id, decoded_token.get("sub") if decoded_token else None)
            allowed_groups = condition.get("group_ids", [])
            results.append(any(str(group_id) in {str(gid) for gid in allowed_groups} for group_id in user_groups))
        
        elif ctype == "answer":
            field_id = condition.get("field_id")
            answer_value = current_answers.get(field_id)
            results.append(evaluate_answer_condition(answer_value, condition))
    
    # Evaluate conditions with logical operator
    operator = rules.get("operator", "AND")
    if operator == "OR":
        return any(results)
    return all(results)


def evaluate_answer_condition(answer_value, condition: dict[str, Any]):
    """Evaluate answer-based conditions for visibility rules"""
    operator = condition.get("operator")
    value = condition.get("value")
    
    if operator == "equals":
        return answer_value == value
    if operator == "not_equals":
        return answer_value != value
    if operator == "contains":
        if isinstance(answer_value, str):
            return str(value) in answer_value
        if isinstance(answer_value, list):
            return value in answer_value
        return False
    if operator == "greater_than":
        return answer_value is not None and answer_value > value
    if operator == "less_than":
        return answer_value is not None and answer_value < value
    if operator == "in":
        return answer_value in (value or [])
    if operator == "not_in":
        return answer_value not in (value or [])
    if operator == "is_empty":
        return answer_value in (None, "", [])
    if operator == "is_not_empty":
        return answer_value not in (None, "", [])
    return False


def user_has_access_to_resource(user_doc, decoded_token, resource: dict, action: str, current_answers=None, context=None):
    """
    Comprehensive resource access check combining permission and visibility rules
    """
    # Step 1: Check basic permissions
    if not check_permission(user_doc, decoded_token, action, resource, context=context):
        return False
    
    # Step 2: Check resource-specific access rules
    resource_type = resource.get("type")
    if resource_type in {"form", "response"}:
        form_access = resource.get("form_access")
        if form_access:
            if not _check_form_access(form_access, decoded_token, resource.get("org_id")):
                return False
    
    return True


def get_user_groups_from_claims_or_db(decoded_token, org_id, user_id):
    """Get user groups from JWT claims or fallback to database"""
    if decoded_token and "orgs" in decoded_token:
        org_oid_str = str(org_id)
        for claim in decoded_token["orgs"]:
            if str(claim.get("org_id")) == org_oid_str and claim.get("status") == "active":
                if "group_ids" in claim:
                    return claim["group_ids"]
    
    # Fallback to database query
    return get_user_groups(str(user_id) if user_id else decoded_token.get("sub") if decoded_token else None, str(org_id))


def evaluate_visibility_rules(element: dict, decoded_token: dict[str, Any], current_answers=None, resource_org_id=None, resource_context=None):
    """
    Evaluate visibility rules for form elements
    
    Supports:
    - Role-based visibility
    - Group-based visibility  
    - Answer-based conditional visibility
    - Always visible/hidden flags
    """
    rules = element.get("visibility_rules")
    current_answers = current_answers or {}
    
    if not rules or not rules.get("conditions"):
        return True
    
    results = []
    for condition in rules.get("conditions", []):
        ctype = condition.get("type")
        
        if ctype == "always_visible":
            return True
        
        if ctype == "always_hidden":
            return False
        
        if ctype == "role":
            effective_role = None
            if resource_context and resource_context.get("project_doc"):
                effective_role = get_effective_project_role(resource_context.get("user_doc"), decoded_token, resource_context["project_doc"])
            elif resource_org_id is not None:
                effective_role = resolve_org_role(decoded_token, resource_org_id)
            
            allowed_roles = condition.get("roles", [])
            results.append(effective_role in allowed_roles)
        
        elif ctype == "group":
            user_groups = get_user_groups_from_claims_or_db(decoded_token, resource_org_id, decoded_token.get("sub") if decoded_token else None)
            allowed_groups = condition.get("group_ids", [])
            results.append(any(str(group_id) in {str(gid) for gid in allowed_groups} for group_id in user_groups))
        
        elif ctype == "answer":
            field_id = condition.get("field_id")
            answer_value = current_answers.get(field_id)
            results.append(evaluate_answer_condition(answer_value, condition))
    
    # Evaluate conditions with logical operator
    operator = rules.get("operator", "AND")
    if operator == "OR":
        return any(results)
    return all(results)


def user_has_access_to_resource(user_doc, decoded_token, resource: dict, action: str, current_answers=None, context=None):
    """
    Comprehensive resource access check combining permission and visibility rules
    """
    # Step 1: Check basic permissions
    if not check_permission(user_doc, decoded_token, action, resource, context=context):
        return False
    
    # Step 2: Check resource-specific access rules
    resource_type = resource.get("type")
    if resource_type in {"form", "response"}:
        form_access = resource.get("form_access")
        if form_access:
            if not _check_form_access(form_access, decoded_token, resource.get("org_id")):
                return False
    
    return True


def get_user_groups(user_id: str, org_id: str):
    result = []
    groups = mongo.db.groups.find({"org_id": _oid(org_id), "is_deleted": False})
    for group in groups:
        members = resolve_group_members(group, org_id)
        if str(user_id) in {str(member_id) for member_id in members}:
            result.append(str(group["_id"]))
    return result


def resolve_group_members(group: dict, org_id: str):
    if group.get("type") == "static":
        return [str(gm.get("user_id")) for gm in mongo.db.group_members.find({"group_id": group["_id"], "is_deleted": False})]
    
    rule = group.get("dynamic_rule") or {}
    if group.get("type") == "dynamic":
        memberships = list(mongo.db.org_memberships.find({
            "org_id": _oid(org_id),
            "status": "active",
            "is_deleted": False,
        }))
        if not memberships:
            return []
        
        user_ids = [m["user_id"] for m in memberships]
        users_cursor = mongo.db.users.find({"_id": {"$in": user_ids}})
        users_map = {str(u["_id"]): u for u in users_cursor}
        
        matched_users = []
        for m in memberships:
            uid_str = str(m["user_id"])
            user = users_map.get(uid_str) or {}
            candidate = {
                "role": m.get("role"),
                "membership_status": m.get("status"),
                "email": user.get("email"),
                "full_name": user.get("full_name"),
                "status": user.get("status"),
            }
            if evaluate_dynamic_rule(rule, candidate):
                matched_users.append(uid_str)
        return matched_users
    return []



def generate_email_verification_token(user_doc):
    now = int(_now().timestamp())
    payload = {"sub": str(user_doc["_id"]), "purpose": "verify_email", "iat": now, "exp": now + EMAIL_VERIFICATION_TTL_HOURS * 3600}
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def generate_password_reset_token(user_doc):
    now = int(_now().timestamp())
    payload = {"sub": str(user_doc["_id"]), "purpose": "password_reset", "iat": now, "exp": now + PASSWORD_RESET_TTL_HOURS * 3600}
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def verify_email_token(token: str):
    decoded = jwt.decode(token, _jwt_secret(), algorithms=["HS256"], options={"verify_exp": False})
    if decoded.get("purpose") != "verify_email":
        raise ValueError("Invalid verification token")
    if decoded.get("exp", 0) < int(_now().timestamp()):
        raise ValueError("Verification token expired")
    return decoded


def verify_password_reset_token(token: str):
    decoded = jwt.decode(token, _jwt_secret(), algorithms=["HS256"], options={"verify_exp": False})
    if decoded.get("purpose") != "password_reset":
        raise ValueError("Invalid reset token")
    if decoded.get("exp", 0) < int(_now().timestamp()):
        raise ValueError("Reset token expired")
    return decoded


def revoke_all_sessions_for_user(user_id):
    mongo.db.sessions.update_many(
        {"user_id": _oid(user_id), "is_deleted": False},
        {"$set": {"is_deleted": True, "deleted_at": _now(), "revoked_at": _now(), "revoked_reason": "force_logout"}},
    )


def list_active_sessions(user_id):
    sessions = mongo.db.sessions.find({"user_id": _oid(user_id), "is_deleted": False})
    return [
        {
            "session_id": str(session["_id"]),
            "device_info": session.get("device_info", {}),
            "ip_address": session.get("ip_address"),
            "created_at": session.get("created_at"),
            "expires_at": session.get("expires_at"),
        }
        for session in sessions
    ]


def logout_refresh_token(refresh_token: str):
    refresh_hash = _refresh_token_hash(refresh_token)
    mongo.db.sessions.update_one(
        {"refresh_token_hash": refresh_hash, "is_deleted": False},
        {"$set": {"is_deleted": True, "deleted_at": _now(), "revoked_at": _now(), "revoked_reason": "logout"}},
    )


def initiate_user_from_invitation(email: str, full_name: str, password: str, invitation_doc: dict):
    user_doc = mongo.db.users.find_one({"email": email.lower(), "is_deleted": False})
    validate_invitation_policy(invitation_doc)
    if user_doc is None:
        validate_password_policy(password, email=email, display_name=full_name)
        user_doc = register_user(email, password, full_name)
        mongo.db.users.update_one({"_id": user_doc["_id"]}, {"$set": {"status": "active", "approved_at": _now()}})
        user_doc = mongo.db.users.find_one({"_id": user_doc["_id"]})
    org_id = invitation_doc.get("org_id")
    project_id = invitation_doc.get("project_id")
    role = invitation_doc.get("role", "org_viewer" if not project_id else "project_viewer")
    if project_id:
        mongo.db.project_members.update_one(
            {"project_id": _oid(project_id), "user_id": user_doc["_id"]},
            {"$set": {"project_id": _oid(project_id), "user_id": user_doc["_id"], "role": role, "status": "active", "is_deleted": False, "updated_at": _now()}},
            upsert=True,
        )
    else:
        mongo.db.org_memberships.update_one(
            {"org_id": _oid(org_id), "user_id": user_doc["_id"]},
            {"$set": {"org_id": _oid(org_id), "user_id": user_doc["_id"], "role": role, "status": "active", "is_deleted": False, "updated_at": _now()}},
            upsert=True,
        )
    mongo.db.invitations.update_one({"_id": invitation_doc["_id"]}, {"$set": {"status": "accepted", "accepted_at": _now(), "updated_at": _now()}})
    access_token = build_access_token(user_doc)
    refresh_token = build_refresh_token(user_doc)
    return access_token, refresh_token, user_doc


def create_api_key(org_id, user_id, scopes, name, rate_limit_per_hour=1000):
    raw_key = "fbk_" + secrets.token_hex(24)
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    now = _now()
    doc = {
        "_id": ObjectId(),
        "org_id": _oid(org_id),
        "user_id": _oid(user_id),
        "name": name,
        "key_prefix": raw_key[:8],
        "key_hash": key_hash,
        "scopes": scopes,
        "status": "active",
        "rate_limit_per_hour": rate_limit_per_hour,
        "usage_count": 0,
        "last_used_at": None,
        "created_at": now,
        "updated_at": now,
        "is_deleted": False,
    }
    mongo.db.api_keys.insert_one(doc)
    return raw_key, doc


def verify_api_key(raw_key: str, org_id=None, scope=None):
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    doc = mongo.db.api_keys.find_one({"key_hash": key_hash, "status": "active", "is_deleted": False})
    if not doc:
        raise ValueError("Invalid API key")
    if org_id is not None and str(doc.get("org_id")) != str(org_id):
        raise ValueError("Invalid API key")
    if scope and scope not in doc.get("scopes", []):
        raise ValueError("Insufficient scope")
    mongo.db.api_keys.update_one({"_id": doc["_id"]}, {"$inc": {"usage_count": 1}, "$set": {"last_used_at": _now(), "updated_at": _now()}})
    return doc


def api_key_rate_limit_key(raw_key: str):
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def api_key_rate_limit_string(api_key_doc):
    limit = api_key_doc.get("rate_limit_per_hour", 1000)
    return f"{limit} per hour"


def api_key_rate_limit_usage(api_key_doc):
    return {
        "limit_per_hour": api_key_doc.get("rate_limit_per_hour", 1000),
        "usage_count": api_key_doc.get("usage_count", 0),
    }


def create_oauth_client(org_id, name, redirect_uris, scopes, grant_types, client_secret=None):
    client_id = "fb_client_" + secrets.token_hex(8)
    secret = client_secret or secrets.token_hex(24)
    doc = {
        "_id": ObjectId(),
        "org_id": _oid(org_id),
        "client_id": client_id,
        "client_secret_hash": hashlib.sha256(secret.encode("utf-8")).hexdigest(),
        "name": name,
        "redirect_uris": redirect_uris,
        "scopes": scopes,
        "grant_types": grant_types,
        "status": "active",
        "created_at": _now(),
        "updated_at": _now(),
        "is_deleted": False,
    }
    mongo.db.oauth_clients.insert_one(doc)
    return secret, doc


def verify_oauth_client(client_id: str, client_secret: str):
    doc = mongo.db.oauth_clients.find_one({"client_id": client_id, "status": "active", "is_deleted": False})
    if not doc:
        raise ValueError("Invalid oauth client")
    if doc.get("client_secret_hash") != hashlib.sha256(client_secret.encode("utf-8")).hexdigest():
        raise ValueError("Invalid oauth client")
    return doc


def issue_client_credentials_token(client_doc, scope: str):
    now = int(_now().timestamp())
    payload = {
        "client_id": client_doc.get("client_id"),
        "org_id": str(client_doc.get("org_id")),
        "scopes": scope.split(),
        "iat": now,
        "exp": now + 3600,
        "grant_type": "client_credentials",
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def create_oauth_authorization_code(client_doc, user_doc, scope: str, redirect_uri: str, state: str = ""):
    code = secrets.token_urlsafe(24)
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    mongo.db.oauth_authorization_codes.insert_one(
        {
            "_id": ObjectId(),
            "code_hash": code_hash,
            "client_id": client_doc["client_id"],
            "user_id": user_doc["_id"],
            "scope": scope,
            "redirect_uri": redirect_uri,
            "state": state,
            "created_at": _now(),
            "expires_at": _now() + datetime.timedelta(minutes=10),
            "is_deleted": False,
        }
    )
    return code


def exchange_oauth_authorization_code(code: str, client_id: str, client_secret: str, redirect_uri: str):
    client_doc = verify_oauth_client(client_id, client_secret)
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    code_doc = mongo.db.oauth_authorization_codes.find_one({"code_hash": code_hash, "is_deleted": False})
    if not code_doc:
        raise ValueError("Invalid authorization code")
    if code_doc.get("expires_at") and code_doc["expires_at"] < _now():
        raise ValueError("Authorization code expired")
    if code_doc.get("redirect_uri") != redirect_uri:
        raise ValueError("Invalid redirect uri")
    user_doc = mongo.db.users.find_one({"_id": _oid(code_doc["user_id"]), "is_deleted": False})
    access_token = build_access_token(user_doc)
    mongo.db.oauth_authorization_codes.update_one({"_id": code_doc["_id"]}, {"$set": {"is_deleted": True, "consumed_at": _now()}})
    return access_token, code_doc.get("scope", ""), client_doc


def list_org_members(org_id):
    members = mongo.db.org_memberships.find({"org_id": _oid(org_id), "is_deleted": False})
    return [
        {
            "_id": str(member["_id"]),
            "user_id": str(member["user_id"]),
            "org_id": str(member["org_id"]),
            "role": member.get("role"),
            "status": member.get("status"),
        }
        for member in members
    ]


def upsert_org_membership(org_id, user_id, role, status="active", invited_by=None):
    doc = {
        "org_id": _oid(org_id),
        "user_id": _oid(user_id),
        "role": role,
        "custom_permissions": [],
        "status": status,
        "invited_by": _oid(invited_by) if invited_by else None,
        "joined_at": _now(),
        "created_at": _now(),
        "updated_at": _now(),
        "is_deleted": False,
        "deleted_at": None,
    }
    mongo.db.org_memberships.update_one(
        {"org_id": doc["org_id"], "user_id": doc["user_id"]},
        {"$set": doc},
        upsert=True,
    )
    return mongo.db.org_memberships.find_one({"org_id": doc["org_id"], "user_id": doc["user_id"]})


def upsert_project_membership(project_id, user_id, role, status="active", invited_by=None):
    doc = {
        "project_id": _oid(project_id),
        "user_id": _oid(user_id),
        "role": role,
        "status": status,
        "invited_by": _oid(invited_by) if invited_by else None,
        "joined_at": _now(),
        "created_at": _now(),
        "updated_at": _now(),
        "is_deleted": False,
        "deleted_at": None,
    }
    mongo.db.project_members.update_one(
        {"project_id": doc["project_id"], "user_id": doc["user_id"]},
        {"$set": doc},
        upsert=True,
    )
    return mongo.db.project_members.find_one({"project_id": doc["project_id"], "user_id": doc["user_id"]})


def list_project_members(project_id):
    members = mongo.db.project_members.find({"project_id": _oid(project_id), "is_deleted": False})
    return [
        {
            "_id": str(member["_id"]),
            "user_id": str(member["user_id"]),
            "project_id": str(member["project_id"]),
            "role": member.get("role"),
            "status": member.get("status"),
        }
        for member in members
    ]


def list_groups(org_id):
    groups = mongo.db.groups.find({"org_id": _oid(org_id), "is_deleted": False})
    return [
        {
            "_id": str(group["_id"]),
            "org_id": str(group["org_id"]),
            "name": group.get("name"),
            "type": group.get("type"),
            "dynamic_rule": group.get("dynamic_rule"),
        }
        for group in groups
    ]


def create_group(org_id, name, group_type="static", dynamic_rule=None):
    doc = {
        "_id": ObjectId(),
        "org_id": _oid(org_id),
        "name": name,
        "type": group_type,
        "dynamic_rule": dynamic_rule,
        "created_at": _now(),
        "updated_at": _now(),
        "is_deleted": False,
    }
    mongo.db.groups.insert_one(doc)
    return doc


def add_group_member(group_id, user_id, added_by=None):
    doc = {
        "_id": ObjectId(),
        "group_id": _oid(group_id),
        "user_id": _oid(user_id),
        "added_by": _oid(added_by) if added_by else None,
        "created_at": _now(),
        "is_deleted": False,
    }
    mongo.db.group_members.update_one(
        {"group_id": doc["group_id"], "user_id": doc["user_id"]},
        {"$set": doc},
        upsert=True,
    )
    return doc


def remove_group_member(group_id, user_id):
    mongo.db.group_members.update_one(
        {"group_id": _oid(group_id), "user_id": _oid(user_id)},
        {"$set": {"is_deleted": True}}
    )


def create_org_invitation(org_id, email, role, project_id=None, invited_by=None, expires_at=None):
    token = secrets.token_urlsafe(32)
    doc = {
        "_id": ObjectId(),
        "org_id": _oid(org_id),
        "project_id": _oid(project_id) if project_id else None,
        "email": email.lower(),
        "role": role,
        "token": token,
        "status": "pending",
        "invited_by": _oid(invited_by) if invited_by else None,
        "expires_at": expires_at or (_now() + datetime.timedelta(days=INVITATION_TTL_DAYS)),
        "created_at": _now(),
        "updated_at": _now(),
        "accepted_at": None,
        "is_deleted": False,
    }
    mongo.db.invitations.insert_one(doc)
    return doc


def accept_org_invitation(token: str, email: str, full_name: str, password: str):
    invitation = mongo.db.invitations.find_one({"token": token, "is_deleted": False})
    if not invitation:
        raise ValueError("Invitation not found")
    if invitation.get("status") == "revoked":
        raise ValueError("Invitation revoked")
    if invitation.get("status") == "accepted":
        raise ValueError("Invitation already accepted")
    if invitation.get("expires_at") and invitation["expires_at"] < _now():
        raise ValueError("Invitation expired")
    return initiate_user_from_invitation(email, full_name, password, invitation)


def create_collaborator_invitation(org_id, project_id, email, role, invited_by=None):
    org = mongo.db.organisations.find_one({"_id": _oid(org_id), "is_deleted": False})
    project = mongo.db.projects.find_one({"_id": _oid(project_id), "is_deleted": False})
    if not org or not project:
        raise ValueError("Org or project not found")
    settings = org.get("settings") or {}
    if not settings.get("allow_external_collaborators", False):
        raise ValueError("External collaborators are not allowed")
    return create_org_invitation(org_id, email, role, project_id=project_id, invited_by=invited_by)


def validate_invitation_policy(invitation_doc, user_doc=None):
    if invitation_doc.get("status") == "revoked":
        raise ValueError("Invitation revoked")
    if invitation_doc.get("status") == "accepted":
        raise ValueError("Invitation already accepted")
    if invitation_doc.get("expires_at") and invitation_doc["expires_at"] < _now():
        raise ValueError("Invitation expired")
    if invitation_doc.get("project_id") and user_doc:
        project = mongo.db.projects.find_one({"_id": _oid(invitation_doc["project_id"]), "is_deleted": False})
        if not project:
            raise ValueError("Project not found")
        if project.get("status") == "suspended":
            raise ValueError("Project suspended")
        org_role = resolve_org_role({"orgs": invitation_doc.get("org_claims", [])}, invitation_doc.get("org_id"))
        if org_role and org_role == "org_viewer" and invitation_doc.get("role") not in {"project_viewer"}:
            raise ValueError("Invitation role exceeds collaborator scope")
    return True


def accept_collaborator_invitation(token: str, email: str, full_name: str, password: str):
    invitation = mongo.db.invitations.find_one({"token": token, "is_deleted": False})
    if not invitation:
        raise ValueError("Invitation not found")
    return initiate_user_from_invitation(email, full_name, password, invitation)


def set_org_status(org_id, status):
    mongo.db.organisations.update_one({"_id": _oid(org_id)}, {"$set": {"status": status, "updated_at": _now()}})
    org_memberships = mongo.db.org_memberships.find({"org_id": _oid(org_id), "is_deleted": False})
    member_ids = [membership.get("user_id") for membership in org_memberships]
    return member_ids


def revoke_api_key(raw_key: str):
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    mongo.db.api_keys.update_one({"key_hash": key_hash}, {"$set": {"status": "revoked", "updated_at": _now(), "is_deleted": True}})


def rotate_api_key(raw_key: str):
    doc = verify_api_key(raw_key)
    mongo.db.api_keys.update_one({"_id": doc["_id"]}, {"$set": {"status": "rotated", "updated_at": _now(), "is_deleted": True}})
    new_raw, new_doc = create_api_key(doc["org_id"], doc["user_id"], doc.get("scopes", []), doc.get("name", "rotated key"), doc.get("rate_limit_per_hour", 1000))
    return new_raw, new_doc


def authorize_oauth_consent(client_id: str, user_doc, scope: str, redirect_uri: str, state: str = ""):
    client_doc = mongo.db.oauth_clients.find_one({"client_id": client_id, "status": "active", "is_deleted": False})
    if not client_doc:
        raise ValueError("Invalid oauth client")
    if redirect_uri not in client_doc.get("redirect_uris", []):
        raise ValueError("Invalid redirect uri")
    approved_scopes = [s for s in scope.split() if s in client_doc.get("scopes", [])]
    if not approved_scopes:
        raise ValueError("No permitted scopes")
    code = create_oauth_authorization_code(client_doc, user_doc, " ".join(approved_scopes), redirect_uri, state=state)
    return code
