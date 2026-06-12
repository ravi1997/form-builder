import datetime

from flask import Blueprint, current_app, jsonify, request
from bson import ObjectId

from app.extensions import mongo
from app.services.auth_service import (
    build_access_token,
    check_permission,
    decode_request_bearer_token,
    generate_email_verification_token,
    generate_password_reset_token,
    create_org_invitation,
    create_group,
    add_group_member,
    remove_group_member,
    list_groups,
    list_org_members,
    list_project_members,
    create_collaborator_invitation,
    set_org_status,
    upsert_org_membership,
    upsert_project_membership,
    initiate_user_from_invitation,
    list_active_sessions,
    login_user,
    logout_refresh_token,
    refresh_access_token,
    register_user,
    revoke_all_sessions_for_user,
    validate_password_policy,
    rotate_user_password,
    verify_bearer_token,
    verify_email_token,
    verify_password_reset_token,
    hash_password,
    authorize_oauth_consent,
    rotate_api_key,
    revoke_api_key,
)
from app.utils.security import log_security_event

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
admin_bp = Blueprint("admin_auth", __name__, url_prefix="/api/admin")


def _success(data=None, message=None, status_code=200):
    payload = {"status": "success", "data": data or {}}
    if message:
        payload["message"] = message
    return jsonify(payload), status_code


def _error(code, message, status_code=400):
    return jsonify({"status": "error", "code": code, "message": message}), status_code


def _request_bearer():
    auth_header = request.headers.get("Authorization", "")
    try:
        return decode_request_bearer_token(auth_header)
    except ValueError as exc:
        return None, str(exc)


def _require_user():
    user_doc, decoded_or_error = _request_bearer()
    if not user_doc:
        return None, _error("UNAUTHORIZED", decoded_or_error, 401)
    return (user_doc, decoded_or_error), None


def _require_admin_org_action(org_id):
    user_ctx, err = _require_user()
    if err:
        return None, err
    user_doc, decoded = user_ctx
    if decoded.get("system_role") == "super_admin":
        return (user_doc, decoded), None
    if not check_permission(user_doc, decoded, "edit_org_settings", {"type": "org", "org_id": org_id}):
        return None, _error("FORBIDDEN", "Forbidden", 403)
    return (user_doc, decoded), None


def _client_meta():
    return {
        "platform": request.headers.get("X-Device-Platform"),
        "user_agent": request.headers.get("User-Agent"),
        "device_id": request.headers.get("X-Device-Id"),
    }


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    full_name = data.get("full_name")
    if not email or not password or not full_name:
        return _error("BAD_REQUEST", "email, password and full_name are required")
    try:
        validate_password_policy(password, email=email, display_name=full_name)
        user = register_user(email, password, full_name)
        verification_token = generate_email_verification_token(user)
        mongo.db.invitations.insert_one(
            {
                "_id": ObjectId(),
                "org_id": None,
                "project_id": None,
                "email": email.lower(),
                "token": verification_token,
                "status": "pending",
                "role": None,
                "expires_at": datetime.datetime.utcnow() + datetime.timedelta(days=1),
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow(),
                "is_deleted": False,
            }
        )
        return _success({"user_id": str(user["_id"]), "verification_token": verification_token}, "User registered successfully. Pending administrator approval.", 201)
    except ValueError as exc:
        return _error("CONFLICT", str(exc), 409)


@auth_bp.route("/verify-email", methods=["GET"])
def verify_email():
    token = request.args.get("token")
    if not token:
        return _error("BAD_REQUEST", "token is required")
    try:
        decoded = verify_email_token(token)
        user_id = decoded["sub"]
        mongo.db.users.update_one({"_id": ObjectId(user_id), "is_deleted": False}, {"$set": {"email_verified": True, "updated_at": datetime.datetime.utcnow()}})
        return _success(message="Email verified")
    except Exception as exc:
        return _error("UNAUTHORIZED", str(exc), 401)


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        log_security_event(
            event_type="login_failed",
            details="Missing email or password",
            ip_address=request.headers.get("X-Forwarded-For") or request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )
        return _error("BAD_REQUEST", "email and password are required")
    
    try:
        access_token, refresh_token, user_doc = login_user(
            email, 
            password, 
            device_info=_client_meta(), 
            ip_address=request.headers.get("X-Forwarded-For") or request.remote_addr
        )
        
        log_security_event(
            event_type="login_success",
            details=f"User logged in successfully: {email}",
            ip_address=request.headers.get("X-Forwarded-For") or request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            user_id=str(user_doc["_id"])
        )
        
        return _success({
            "access_token": access_token, 
            "refresh_token": refresh_token, 
            "token_type": "Bearer", 
            "expires_in": 900
        })
    except ValueError as exc:
        log_security_event(
            event_type="login_failed",
            details=f"Invalid credentials for {email}: {str(exc)}",
            ip_address=request.headers.get("X-Forwarded-For") or request.remote_addr,
            user_agent=request.headers.get("User-Agent")
        )
        return _error("UNAUTHORIZED", str(exc), 401)


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    data = request.get_json() or {}
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        return _error("BAD_REQUEST", "refresh_token is required")
    try:
        access_token, new_refresh_token = refresh_access_token(refresh_token, ip_address=request.headers.get("X-Forwarded-For") or request.remote_addr)
        return _success({"access_token": access_token, "refresh_token": new_refresh_token, "token_type": "Bearer", "expires_in": 900})
    except PermissionError as exc:
        return _error("REFRESH_TOKEN_REUSE_DETECTED", str(exc), 401)
    except ValueError as exc:
        return _error("UNAUTHORIZED", str(exc), 401)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    user_ctx, err = _require_user()
    if err:
        return err
    data = request.get_json() or {}
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        log_security_event(
            event_type="logout_failed",
            details="Missing refresh token",
            ip_address=request.headers.get("X-Forwarded-For") or request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            user_id=str(user_ctx[0]["_id"])
        )
        return _error("BAD_REQUEST", "refresh_token is required")
    
    logout_refresh_token(refresh_token)
    
    log_security_event(
        event_type="logout_success",
        details="User logged out successfully",
        ip_address=request.headers.get("X-Forwarded-For") or request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
        user_id=str(user_ctx[0]["_id"])
    )
    
    return _success(message="Logged out")


@auth_bp.route("/sessions", methods=["GET"])
def sessions():
    user_ctx, err = _require_user()
    if err:
        return err
    user_doc, decoded = user_ctx
    sessions = list_active_sessions(user_doc["_id"])
    current_refresh_hash = request.args.get("current_refresh_hash")
    for session in sessions:
        session["is_current"] = bool(current_refresh_hash and current_refresh_hash == session.get("session_id"))
    return _success({"sessions": sessions})


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json() or {}
    email = (data.get("email") or "").lower()
    user = mongo.db.users.find_one({"email": email, "is_deleted": False})
    if user:
        token = generate_password_reset_token(user)
        mongo.db.password_reset_tokens.insert_one(
            {
                "_id": ObjectId(),
                "user_id": user["_id"],
                "token": token,
                "expires_at": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
                "created_at": datetime.datetime.utcnow(),
                "is_deleted": False,
            }
        )
    return _success(message="If the account exists, password reset instructions have been sent.")


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json() or {}
    token = data.get("token")
    new_password = data.get("new_password")
    if not token or not new_password:
        return _error("BAD_REQUEST", "token and new_password are required")
    try:
        decoded = verify_password_reset_token(token)
        user = mongo.db.users.find_one({"_id": ObjectId(decoded["sub"]), "is_deleted": False})
        if not user:
            raise ValueError("Invalid reset token")
        rotate_user_password(user, new_password)
        mongo.db.audit_logs.insert_one({"_id": ObjectId(), "entity_type": "user", "entity_id": user["_id"], "action": "password_reset", "actor_id": user["_id"], "timestamp": datetime.datetime.utcnow(), "is_deleted": False})
        return _success(message="Password reset successfully")
    except ValueError as exc:
        return _error("UNAUTHORIZED", str(exc), 401)


@auth_bp.route("/accept-invite/<token>", methods=["POST"])
def accept_invite(token):
    data = request.get_json() or {}
    email = data.get("email")
    full_name = data.get("full_name")
    password = data.get("password")
    if not email or not full_name or not password:
        return _error("BAD_REQUEST", "email, full_name and password are required")
    invitation = mongo.db.invitations.find_one({"token": token, "is_deleted": False})
    if not invitation:
        return _error("INVITATION_NOT_FOUND", "Invitation not found", 404)
    if invitation.get("status") == "revoked":
        return _error("INVITATION_REVOKED", "Invitation revoked", 410)
    if invitation.get("status") == "accepted":
        return _error("INVITATION_ALREADY_USED", "Invitation already accepted", 410)
    if invitation.get("expires_at") and invitation["expires_at"] < datetime.datetime.utcnow():
        return _error("INVITATION_EXPIRED", "Invitation expired", 410)
    access_token, refresh_token, user = initiate_user_from_invitation(email, full_name, password, invitation)
    return _success({"access_token": access_token, "refresh_token": refresh_token, "token_type": "Bearer", "expires_in": 900})


@admin_bp.route("/users/<user_id>/approve", methods=["POST"])
def approve_user(user_id):
    actor_ctx, err = _require_user()
    if err:
        return err
    actor_user, actor_decoded = actor_ctx
    if actor_decoded.get("system_role") != "super_admin":
        return _error("FORBIDDEN", "super_admin required", 403)
    user = mongo.db.users.find_one({"_id": ObjectId(user_id), "is_deleted": False})
    if not user:
        return _error("NOT_FOUND", "User not found", 404)
    mongo.db.users.update_one({"_id": user["_id"]}, {"$set": {"status": "active", "approved_at": datetime.datetime.utcnow(), "approved_by": actor_user["_id"], "updated_at": datetime.datetime.utcnow()}})
    return _success(message="User approved")


@admin_bp.route("/users/<user_id>/reject", methods=["POST"])
def reject_user(user_id):
    actor_ctx, err = _require_user()
    if err:
        return err
    actor_user, actor_decoded = actor_ctx
    if actor_decoded.get("system_role") != "super_admin":
        return _error("FORBIDDEN", "super_admin required", 403)
    user = mongo.db.users.find_one({"_id": ObjectId(user_id), "is_deleted": False})
    if not user:
        return _error("NOT_FOUND", "User not found", 404)
    mongo.db.users.update_one({"_id": user["_id"]}, {"$set": {"status": "deactivated", "is_deleted": True, "deleted_at": datetime.datetime.utcnow(), "updated_at": datetime.datetime.utcnow()}})
    revoke_all_sessions_for_user(user["_id"])
    return _success(message="User rejected")


@admin_bp.route("/users/<user_id>/force-logout", methods=["POST"])
def force_logout(user_id):
    actor_ctx, err = _require_user()
    if err:
        return err
    actor_user, actor_decoded = actor_ctx
    if actor_decoded.get("system_role") != "super_admin":
        return _error("FORBIDDEN", "super_admin required", 403)
    revoke_all_sessions_for_user(user_id)
    return _success(message="User sessions revoked")


@auth_bp.route("/me", methods=["GET"])
def me():
    """Alias for /whoami endpoint as specified in CONTEXT.md"""
    return whoami()


@auth_bp.route("/whoami", methods=["GET"])
def whoami():
    user_ctx, err = _require_user()
    if err:
        return err
    user_doc, decoded = user_ctx
    
    # Get comprehensive user information
    user_info = {
        "user_id": str(user_doc["_id"]),
        "email": user_doc.get("email"),
        "full_name": user_doc.get("full_name"),
        "display_name": user_doc.get("display_name"),
        "avatar_url": user_doc.get("avatar_url"),
        "system_role": decoded.get("system_role"),
        "status": user_doc.get("status"),
        "email_verified": user_doc.get("email_verified", False),
        "phone_verified": user_doc.get("phone_verified", False),
        "two_factor_enabled": user_doc.get("two_factor_enabled", False),
        "last_login_at": user_doc.get("last_login_at"),
        "login_count": user_doc.get("login_count", 0),
        "created_at": user_doc.get("created_at"),
        "updated_at": user_doc.get("updated_at"),
        "orgs": decoded.get("orgs", []),
        "notification_preferences": user_doc.get("notification_preferences", {}),
    }
    
    return _success(user_info)


@admin_bp.route("/orgs/<org_id>/members", methods=["GET"])
def list_members(org_id):
    ctx, err = _require_admin_org_action(org_id)
    if err:
        return err
    return _success({"members": list_org_members(org_id)})


@admin_bp.route("/orgs/<org_id>/members", methods=["POST"])
def upsert_member(org_id):
    ctx, err = _require_admin_org_action(org_id)
    if err:
        return err
    data = request.get_json() or {}
    user_id = data.get("user_id")
    role = data.get("role")
    if not user_id or not role:
        return _error("BAD_REQUEST", "user_id and role are required")
    member = upsert_org_membership(org_id, user_id, role, status=data.get("status", "active"), invited_by=ctx[0]["_id"])
    return _success({"member_id": str(member["_id"])}, "Membership saved", 201)


@admin_bp.route("/orgs/<org_id>/members/<user_id>", methods=["PATCH"])
def update_member(org_id, user_id):
    ctx, err = _require_admin_org_action(org_id)
    if err:
        return err
    data = request.get_json() or {}
    member = upsert_org_membership(org_id, user_id, data.get("role", "org_viewer"), status=data.get("status", "active"), invited_by=ctx[0]["_id"])
    return _success({"member_id": str(member["_id"])})


@admin_bp.route("/orgs/<org_id>/members/<user_id>", methods=["DELETE"])
def delete_member(org_id, user_id):
    ctx, err = _require_admin_org_action(org_id)
    if err:
        return err
    mongo.db.org_memberships.update_one({"org_id": ObjectId(org_id), "user_id": ObjectId(user_id)}, {"$set": {"is_deleted": True, "deleted_at": datetime.datetime.utcnow(), "updated_at": datetime.datetime.utcnow()}})
    return _success(message="Member removed")


@admin_bp.route("/orgs/<org_id>/invite", methods=["POST"])
def invite_member(org_id):
    ctx, err = _require_admin_org_action(org_id)
    if err:
        return err
    data = request.get_json() or {}
    if not data.get("email") or not data.get("role"):
        return _error("BAD_REQUEST", "email and role are required")
    project_id = data.get("project_id")
    try:
        if project_id:
            invitation = create_collaborator_invitation(org_id, project_id, data["email"], data["role"], invited_by=ctx[0]["_id"])
        else:
            invitation = create_org_invitation(org_id, data["email"], data["role"], invited_by=ctx[0]["_id"])
    except ValueError as exc:
        return _error("FORBIDDEN", str(exc), 403)
    return _success({"invitation_id": str(invitation["_id"]), "token": invitation["token"]}, "Invitation created", 201)


@admin_bp.route("/orgs/<org_id>/groups", methods=["GET"])
def get_groups(org_id):
    ctx, err = _require_admin_org_action(org_id)
    if err:
        return err
    return _success({"groups": list_groups(org_id)})


@admin_bp.route("/orgs/<org_id>/groups", methods=["POST"])
def create_group_route(org_id):
    ctx, err = _require_admin_org_action(org_id)
    if err:
        return err
    data = request.get_json() or {}
    if not data.get("name"):
        return _error("BAD_REQUEST", "name is required")
    group = create_group(org_id, data["name"], group_type=data.get("type", "static"), dynamic_rule=data.get("dynamic_rule"))
    return _success({"group_id": str(group["_id"])}, "Group created", 201)


@admin_bp.route("/groups/<group_id>/members", methods=["POST"])
def add_group_member_route(group_id):
    data = request.get_json() or {}
    if not data.get("user_id"):
        return _error("BAD_REQUEST", "user_id is required")
    add_group_member(group_id, data["user_id"], added_by=None)
    return _success(message="Member added")


@admin_bp.route("/groups/<group_id>/members/<user_id>", methods=["DELETE"])
def remove_group_member_route(group_id, user_id):
    remove_group_member(group_id, user_id)
    return _success(message="Member removed")


@admin_bp.route("/orgs/<org_id>/approve", methods=["POST"])
def approve_org(org_id):
    ctx, err = _require_user()
    if err:
        return err
    user_doc, decoded = ctx
    if decoded.get("system_role") != "super_admin":
        return _error("FORBIDDEN", "super_admin required", 403)
    member_ids = set_org_status(org_id, "active")
    revoke_all_sessions_for_user(user_doc["_id"])
    return _success({"member_count": len(member_ids)}, "Organisation approved")


@admin_bp.route("/orgs/<org_id>/suspend", methods=["POST"])
def suspend_org(org_id):
    ctx, err = _require_user()
    if err:
        return err
    user_doc, decoded = ctx
    if decoded.get("system_role") != "super_admin":
        return _error("FORBIDDEN", "super_admin required", 403)
    member_ids = set_org_status(org_id, "suspended")
    for member_id in member_ids:
        revoke_all_sessions_for_user(member_id)
    return _success({"member_count": len(member_ids)}, "Organisation suspended")


@admin_bp.route("/orgs/<org_id>/activate", methods=["POST"])
def activate_org(org_id):
    ctx, err = _require_user()
    if err:
        return err
    user_doc, decoded = ctx
    if decoded.get("system_role") != "super_admin":
        return _error("FORBIDDEN", "super_admin required", 403)
    set_org_status(org_id, "active")
    return _success(message="Organisation activated")


@admin_bp.route("/projects/<project_id>/members", methods=["GET"])
def list_project_members_route(project_id):
    return _success({"members": list_project_members(project_id)})


@admin_bp.route("/projects/<project_id>/members", methods=["POST"])
def add_project_member_route(project_id):
    data = request.get_json() or {}
    if not data.get("user_id") or not data.get("role"):
        return _error("BAD_REQUEST", "user_id and role are required")
    member = upsert_project_membership(project_id, data["user_id"], data["role"], status=data.get("status", "active"), invited_by=data.get("invited_by"))
    return _success({"member_id": str(member["_id"])}, "Project membership saved", 201)


@admin_bp.route("/projects/<project_id>/members/<user_id>", methods=["PATCH"])
def update_project_member(project_id, user_id):
    data = request.get_json() or {}
    member = upsert_project_membership(project_id, user_id, data.get("role", "project_viewer"), status=data.get("status", "active"), invited_by=data.get("invited_by"))
    return _success({"member_id": str(member["_id"])})


@admin_bp.route("/projects/<project_id>/members/<user_id>", methods=["DELETE"])
def delete_project_member(project_id, user_id):
    mongo.db.project_members.update_one({"project_id": ObjectId(project_id), "user_id": ObjectId(user_id)}, {"$set": {"is_deleted": True, "deleted_at": datetime.datetime.utcnow(), "updated_at": datetime.datetime.utcnow()}})
    return _success(message="Project member removed")


@admin_bp.route("/api-keys/rotate", methods=["POST"])
def rotate_key():
    data = request.get_json() or {}
    raw_key = data.get("api_key")
    if not raw_key:
        return _error("BAD_REQUEST", "api_key is required")
    new_raw, new_doc = rotate_api_key(raw_key)
    return _success({"api_key": new_raw, "api_key_id": str(new_doc["_id"])}, "API key rotated")


@admin_bp.route("/api-keys/revoke", methods=["POST"])
def revoke_key():
    data = request.get_json() or {}
    raw_key = data.get("api_key")
    if not raw_key:
        return _error("BAD_REQUEST", "api_key is required")
    revoke_api_key(raw_key)
    return _success(message="API key revoked")


@auth_bp.route("/check-permission", methods=["POST"])
def check_permission_route():
    """Check if current user has permission to perform an action."""
    user_ctx, err = _require_user()
    if err:
        return err
    
    user_doc, decoded = user_ctx
    data = request.get_json() or {}
    
    action = data.get("action")
    resource_type = data.get("resource_type")
    resource_id = data.get("resource_id")
    
    if not action or not resource_type:
        return _error("BAD_REQUEST", "action and resource_type are required")
    
    # Build resource context
    resource = {"type": resource_type}
    if resource_id:
        resource["resource_id"] = resource_id
    
    # Add org_id and project_id if provided
    if "org_id" in data:
        resource["org_id"] = data["org_id"]
    if "project_id" in data:
        resource["project_id"] = data["project_id"]
    
    from app.services.permission_service import permission_service
    
    try:
        result = permission_service.check_permission(user_doc, decoded, action, resource)
        return _success({
            "allowed": result.allowed,
            "reason": result.reason,
            "effective_role": result.effective_role
        })
    except Exception as e:
        log_security_event(
            event_type="permission_check_error",
            details=f"Error checking permission: {str(e)}",
            ip_address=request.headers.get("X-Forwarded-For") or request.remote_addr,
            user_agent=request.headers.get("User-Agent"),
            user_id=str(user_doc["_id"])
        )
        return _error("INTERNAL_ERROR", "Error checking permission", 500)
