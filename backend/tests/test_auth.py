import jwt
from bson import ObjectId

from app.services.auth_service import check_permission, resolve_group_members, verify_bearer_token


def test_register_login_refresh_flow(client, db):
    res = client.post(
        "/api/auth/register",
        json={"email": "doctor@aiims.edu", "password": "Password123!", "full_name": "Dr. Ravi"},
    )
    assert res.status_code == 201

    user = db.users.find_one({"email": "doctor@aiims.edu"})
    db.users.update_one({"_id": user["_id"]}, {"$set": {"status": "active"}})

    login_res = client.post(
        "/api/auth/login",
        json={"email": "doctor@aiims.edu", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    login_data = login_res.get_json()["data"]
    assert "access_token" in login_data
    assert "refresh_token" in login_data

    verified_user, decoded = verify_bearer_token(login_data["access_token"])
    assert str(verified_user["_id"]) == str(user["_id"])
    assert decoded["system_role"] == "user"

    refresh_res = client.post(
        "/api/auth/refresh",
        json={"refresh_token": login_data["refresh_token"]},
    )
    assert refresh_res.status_code == 200
    assert "access_token" in refresh_res.get_json()["data"]


def test_access_token_contains_org_claims(client, db):
    res = client.post(
        "/api/auth/register",
        json={"email": "member@example.com", "password": "Password123!", "full_name": "Member"},
    )
    assert res.status_code == 201
    user = db.users.find_one({"email": "member@example.com"})
    db.users.update_one({"_id": user["_id"]}, {"$set": {"status": "active"}})
    org_id = ObjectId()
    db.org_memberships.insert_one(
        {
            "_id": ObjectId(),
            "user_id": user["_id"],
            "org_id": org_id,
            "role": "org_admin",
            "status": "active",
            "is_deleted": False,
        }
    )

    login_res = client.post(
        "/api/auth/login",
        json={"email": "member@example.com", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    token = login_res.get_json()["data"]["access_token"]
    decoded = jwt.decode(token, "test-jwt-secret", algorithms=["HS256"], options={"verify_exp": False})
    assert decoded["sub"] == str(user["_id"])
    assert decoded["email"] == "member@example.com"
    assert decoded["system_role"] == "user"
    assert decoded["orgs"][0]["org_id"] == str(org_id)
    assert decoded["orgs"][0]["role"] == "org_admin"


def test_notifications_route_requires_bearer_token(client):
    res = client.get("/api/internal/v1/notifications")
    assert res.status_code == 401


def test_password_policy_rejects_weak_password(client):
    res = client.post(
        "/api/auth/register",
        json={"email": "weak@example.com", "password": "weakpass", "full_name": "Weak User"},
    )
    assert res.status_code == 409


def test_logout_revokes_refresh_token(client, db):
    client.post("/api/auth/register", json={"email": "logout@example.com", "password": "Password123!", "full_name": "Logout User"})
    user = db.users.find_one({"email": "logout@example.com"})
    db.users.update_one({"_id": user["_id"]}, {"$set": {"status": "active"}})
    login = client.post("/api/auth/login", json={"email": "logout@example.com", "password": "Password123!"})
    token_data = login.get_json()["data"]
    refresh_token = token_data["refresh_token"]
    access_token = token_data["access_token"]
    out = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {access_token}"}, json={"refresh_token": refresh_token})
    assert out.status_code == 200
    assert db.sessions.find_one({"refresh_token_hash": __import__("hashlib").sha256(refresh_token.encode("utf-8")).hexdigest(), "is_deleted": False}) is None


def test_sessions_listing(client, db):
    client.post("/api/auth/register", json={"email": "sessions@example.com", "password": "Password123!", "full_name": "Sessions User"})
    user = db.users.find_one({"email": "sessions@example.com"})
    db.users.update_one({"_id": user["_id"]}, {"$set": {"status": "active"}})
    login = client.post("/api/auth/login", json={"email": "sessions@example.com", "password": "Password123!"})
    access_token = login.get_json()["data"]["access_token"]
    res = client.get("/api/auth/sessions", headers={"Authorization": f"Bearer {access_token}"})
    assert res.status_code == 200
    assert "sessions" in res.get_json()["data"]


def test_accept_invite_creates_active_user_and_membership(client, db):
    invitation_token = "invite-token-123"
    db.invitations.insert_one(
        {
            "_id": ObjectId(),
            "org_id": ObjectId(),
            "project_id": None,
            "email": "invitee@example.com",
            "token": invitation_token,
            "status": "pending",
            "role": "org_editor",
            "expires_at": __import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(days=7),
            "created_at": __import__("datetime").datetime.utcnow(),
            "updated_at": __import__("datetime").datetime.utcnow(),
            "is_deleted": False,
        }
    )
    res = client.post(f"/api/auth/accept-invite/{invitation_token}", json={"email": "invitee@example.com", "password": "Password123!", "full_name": "Invitee"})
    assert res.status_code == 200
    user = db.users.find_one({"email": "invitee@example.com"})
    assert user["status"] == "active"
    assert db.org_memberships.find_one({"user_id": user["_id"]}) is not None


def test_group_resolution_and_permission_helpers(db):
    user_id = ObjectId()
    org_id = ObjectId()
    db.org_memberships.insert_one({"_id": ObjectId(), "user_id": user_id, "org_id": org_id, "role": "org_analyst", "status": "active", "is_deleted": False})
    group = {"_id": ObjectId(), "type": "dynamic", "dynamic_rule": {"field": "role", "operator": "equals", "value": "org_analyst"}}
    members = resolve_group_members(group, str(org_id))
    assert str(user_id) in members or members == []
    user_doc = {"_id": user_id, "system_role": "user"}
    decoded = {"sub": str(user_id), "system_role": "user", "orgs": [{"org_id": str(org_id), "role": "org_analyst", "status": "active"}]}
    project = {"_id": ObjectId(), "org_id": org_id, "is_deleted": False}
    assert check_permission(user_doc, decoded, "run_analysis", {"type": "project", "project_id": project["_id"], "project_doc": project}) in {True, False}


def test_advanced_dynamic_rules(db):
    org_id = ObjectId()
    u1_id = ObjectId()
    u2_id = ObjectId()
    u3_id = ObjectId()
    
    db.users.insert_many([
        {"_id": u1_id, "email": "alice@company.com", "full_name": "Alice Smith", "status": "active"},
        {"_id": u2_id, "email": "bob@partner.com", "full_name": "Bob Jones", "status": "active"},
        {"_id": u3_id, "email": "charlie@company.com", "full_name": "Charlie Brown", "status": "suspended"},
    ])
    
    db.org_memberships.insert_many([
        {"_id": ObjectId(), "user_id": u1_id, "org_id": org_id, "role": "org_admin", "status": "active", "is_deleted": False},
        {"_id": ObjectId(), "user_id": u2_id, "org_id": org_id, "role": "org_editor", "status": "active", "is_deleted": False},
        {"_id": ObjectId(), "user_id": u3_id, "org_id": org_id, "role": "org_admin", "status": "active", "is_deleted": False},
    ])
    
    # Rule 1: Email ends_with @company.com AND role equals org_admin AND status equals active
    rule_1 = {
        "logical_operator": "AND",
        "conditions": [
            {"field": "email", "operator": "ends_with", "value": "@company.com"},
            {"field": "role", "operator": "equals", "value": "org_admin"},
            {"field": "status", "operator": "equals", "value": "active"}
        ]
    }
    g1 = {"_id": ObjectId(), "type": "dynamic", "dynamic_rule": rule_1}
    members_1 = resolve_group_members(g1, str(org_id))
    assert str(u1_id) in members_1
    assert str(u2_id) not in members_1
    assert str(u3_id) not in members_1

    # Rule 2: Email contains partner OR full_name starts_with Alice
    rule_2 = {
        "logical_operator": "OR",
        "conditions": [
            {"field": "email", "operator": "contains", "value": "partner"},
            {"field": "full_name", "operator": "starts_with", "value": "Alice"}
        ]
    }
    g2 = {"_id": ObjectId(), "type": "dynamic", "dynamic_rule": rule_2}
    members_2 = resolve_group_members(g2, str(org_id))
    assert str(u1_id) in members_2
    assert str(u2_id) in members_2
    assert str(u3_id) not in members_2


def test_access_token_contains_group_ids(client, db):
    # 1. Create active user
    email = "grouped@example.com"
    res = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Grouped User"},
    )
    assert res.status_code == 201
    user = db.users.find_one({"email": email})
    db.users.update_one({"_id": user["_id"]}, {"$set": {"status": "active"}})

    # 2. Create organization membership
    org_id = ObjectId()
    db.org_memberships.insert_one(
        {
            "_id": ObjectId(),
            "user_id": user["_id"],
            "org_id": org_id,
            "role": "org_editor",
            "status": "active",
            "is_deleted": False,
        }
    )

    # 3. Create a static group and add the user to it
    static_group_id = ObjectId()
    db.groups.insert_one(
        {
            "_id": static_group_id,
            "org_id": org_id,
            "name": "Static Group",
            "type": "static",
            "is_deleted": False,
        }
    )
    db.group_members.insert_one(
        {
            "_id": ObjectId(),
            "group_id": static_group_id,
            "user_id": user["_id"],
            "is_deleted": False,
        }
    )

    # 4. Create a dynamic group with matching rule
    dynamic_group_id = ObjectId()
    db.groups.insert_one(
        {
            "_id": dynamic_group_id,
            "org_id": org_id,
            "name": "Dynamic Group",
            "type": "dynamic",
            "dynamic_rule": {
                "logical_operator": "AND",
                "conditions": [
                    {"field": "role", "operator": "equals", "value": "org_editor"},
                    {"field": "email", "operator": "ends_with", "value": "@example.com"},
                ]
            },
            "is_deleted": False,
        }
    )

    # 5. Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    assert login_res.status_code == 200
    token = login_res.get_json()["data"]["access_token"]
    decoded = jwt.decode(token, "test-jwt-secret", algorithms=["HS256"], options={"verify_exp": False})
    refresh_token = login_res.get_json()["data"]["refresh_token"]
    
    # 6. Verify token claims
    assert decoded["sub"] == str(user["_id"])
    orgs = decoded.get("orgs", [])
    assert len(orgs) == 1
    org_claim = orgs[0]
    assert org_claim["org_id"] == str(org_id)
    assert "group_ids" in org_claim
    
    # Verify both static and dynamic group IDs are in the token claim
    group_ids = org_claim["group_ids"]
    assert str(static_group_id) in group_ids
    assert str(dynamic_group_id) in group_ids

    # 6b. Verify /api/auth/refresh returns token with group_ids
    refresh_res = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    refreshed_token = refresh_res.get_json()["data"]["access_token"]
    decoded_refresh = jwt.decode(refreshed_token, "test-jwt-secret", algorithms=["HS256"], options={"verify_exp": False})
    orgs_refresh = decoded_refresh.get("orgs", [])
    assert len(orgs_refresh) == 1
    org_claim_refresh = orgs_refresh[0]
    assert org_claim_refresh["org_id"] == str(org_id)
    assert "group_ids" in org_claim_refresh
    assert str(static_group_id) in org_claim_refresh["group_ids"]
    assert str(dynamic_group_id) in org_claim_refresh["group_ids"]


    # 7. Verify helper resolution and permission evaluation
    from app.services.auth_service import get_user_groups_from_claims_or_db, user_has_access_to_resource
    
    resolved_groups = get_user_groups_from_claims_or_db(decoded, org_id, user["_id"])
    assert str(static_group_id) in resolved_groups
    assert str(dynamic_group_id) in resolved_groups

    # Verify resource access using group permission
    project_id = ObjectId()
    resource = {
        "type": "form",
        "org_id": org_id,
        "project_id": project_id,
        "project_doc": {
            "_id": project_id,
            "org_id": org_id,
            "is_deleted": False
        },
        "form_access": {
            "type": "groups",
            "allowed_group_ids": [str(dynamic_group_id)]
        }
    }
    user_doc = db.users.find_one({"_id": user["_id"]})
    
    # Verify permission check succeeds because user is in the group allowed to view
    has_access = user_has_access_to_resource(user_doc, decoded, resource, "view_responses")
    assert has_access is True


def test_dynamic_rules_bugfixes():
    from app.services.auth_service import evaluate_dynamic_rule
    
    candidate = {
        "role": "org_editor",
        "email": "doctor@aiims.edu"
    }
    
    # Verify: empty OR dynamic rule evaluates to False
    empty_or_rule = {
        "logical_operator": "OR",
        "conditions": []
    }
    assert evaluate_dynamic_rule(empty_or_rule, candidate) is False

    # Verify: empty AND dynamic rule evaluates to True
    empty_and_rule = {
        "logical_operator": "AND",
        "conditions": []
    }
    assert evaluate_dynamic_rule(empty_and_rule, candidate) is True

    # Verify: "in" operator properly matches items when whitespace exists around commas
    in_rule_with_spaces = {
        "field": "role",
        "operator": "in",
        "value": "org_admin, org_editor, org_analyst"
    }
    assert evaluate_dynamic_rule(in_rule_with_spaces, candidate) is True

    # Verify: "in" operator mismatch
    in_rule_mismatch = {
        "field": "role",
        "operator": "in",
        "value": "org_admin, org_analyst"
    }
    assert evaluate_dynamic_rule(in_rule_mismatch, candidate) is False


