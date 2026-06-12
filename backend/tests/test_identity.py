from bson import ObjectId
from app.extensions import mongo
from app.services.auth_service import hash_password


def test_api_key_create_and_verify(client):
    res = client.post(
        "/api/v1/api-keys",
        json={
            "org_id": str(ObjectId()),
            "user_id": str(ObjectId()),
            "name": "CI Key",
            "scopes": ["forms:read", "responses:read"],
        },
    )
    assert res.status_code == 201
    api_key = res.get_json()["data"]["api_key"]
    verify = client.post("/api/v1/api-keys/verify", json={"api_key": api_key, "scope": "forms:read"})
    assert verify.status_code == 200


def test_oauth_client_credentials_token(client):
    client_res = client.post(
        "/api/v1/oauth/clients",
        json={
            "org_id": str(ObjectId()),
            "name": "Integration App",
            "redirect_uris": ["https://example.com/callback"],
            "scopes": ["forms:read"],
            "grant_types": ["client_credentials"],
        },
    )
    assert client_res.status_code == 201
    payload = client_res.get_json()["data"]
    token_res = client.post(
        "/api/v1/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": payload["client_id"],
            "client_secret": payload["client_secret"],
            "scope": "forms:read",
        },
    )
    assert token_res.status_code == 200
    assert token_res.get_json()["data"]["token_type"] == "Bearer"


def test_api_key_rotate_and_revoke(client):
    create_res = client.post(
        "/api/v1/api-keys",
        json={
            "org_id": str(ObjectId()),
            "user_id": str(ObjectId()),
            "name": "Rotate Key",
            "scopes": ["forms:read"],
        },
    )
    api_key = create_res.get_json()["data"]["api_key"]
    rotate_res = client.post("/api/admin/api-keys/rotate", json={"api_key": api_key})
    assert rotate_res.status_code == 200
    revoke_res = client.post("/api/admin/api-keys/revoke", json={"api_key": api_key})
    assert revoke_res.status_code == 200


def test_api_key_rate_limit_enforced(client):
    create_res = client.post(
        "/api/v1/api-keys",
        json={
            "org_id": str(ObjectId()),
            "user_id": str(ObjectId()),
            "name": "Limited Key",
            "scopes": ["forms:read"],
            "rate_limit_per_hour": 1,
        },
    )
    api_key = create_res.get_json()["data"]["api_key"]
    first = client.post("/api/v1/api-keys/verify", json={"api_key": api_key, "scope": "forms:read"})
    second = client.post("/api/v1/api-keys/verify", json={"api_key": api_key, "scope": "forms:read"})
    assert first.status_code == 200
    assert second.status_code == 429


def test_oauth_authorize_and_token_exchange(client, db):
    db.users.insert_one({"_id": ObjectId(), "email": "oauth@example.com", "password_hash": hash_password("Password123!"), "display_name": "OAuth User", "status": "active", "system_role": "user", "is_deleted": False})
    login = client.post("/api/auth/login", json={"email": "oauth@example.com", "password": "Password123!"})
    assert login.status_code == 200
    client_res = client.post(
        "/api/v1/oauth/clients",
        json={
            "org_id": str(ObjectId()),
            "name": "Consent App",
            "redirect_uris": ["https://example.com/callback"],
            "scopes": ["forms:read"],
            "grant_types": ["authorization_code"],
        },
    )
    data = client_res.get_json()["data"]
    auth_get = client.get(
        "/api/v1/oauth/authorize",
        query_string={
            "response_type": "code",
            "client_id": data["client_id"],
            "redirect_uri": "https://example.com/callback",
            "scope": "forms:read",
            "state": "abc",
        },
    )
    assert auth_get.status_code == 200
    auth_post = client.post(
        "/api/v1/oauth/authorize",
        query_string={
            "response_type": "code",
            "client_id": data["client_id"],
            "redirect_uri": "https://example.com/callback",
            "scope": "forms:read",
            "state": "abc",
        },
        headers={"Authorization": f"Bearer {login.get_json()['data']['access_token']}"},
    )
    assert auth_post.status_code == 200
    code = auth_post.get_json()["data"]["code"]
    token_res = client.post(
        "/api/v1/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://example.com/callback",
            "client_id": data["client_id"],
            "client_secret": data["client_secret"],
        },
    )
    assert token_res.status_code == 200


def test_org_membership_management_route(client):
    admin = mongo.db.users.insert_one({"_id": ObjectId(), "email": "admin@example.com", "display_name": "Admin", "status": "active", "system_role": "super_admin", "is_deleted": False, "password_hash": hash_password("Password123!")}).inserted_id
    login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "Password123!"})
    if login.status_code != 200:
        login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "Password123!"})
    org_id = ObjectId()
    res = client.post(
        f"/api/admin/orgs/{org_id}/members",
        headers={"Authorization": f"Bearer {login.get_json()['data']['access_token']}"},
        json={"user_id": str(ObjectId()), "role": "org_editor"},
    )
    assert res.status_code in {200, 201}


def test_external_collaborator_invitation_and_access(client, db):
    owner = db.users.insert_one({"_id": ObjectId(), "email": "owner@example.com", "password_hash": hash_password("Password123!"), "display_name": "Owner", "status": "active", "system_role": "super_admin", "is_deleted": False}).inserted_id
    db.organisations.insert_one({"_id": ObjectId(), "name": "Research Org", "status": "active", "settings": {"allow_external_collaborators": True}, "is_deleted": False})
    org = db.organisations.find_one({"name": "Research Org"})
    project_id = ObjectId()
    db.projects.insert_one({"_id": project_id, "org_id": org["_id"], "name": "Shared Project", "status": "active", "shared_org_ids": [], "is_deleted": False})
    login = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "Password123!"})
    assert login.status_code == 200
    invite = client.post(
        f"/api/admin/orgs/{org['_id']}/invite",
        headers={"Authorization": f"Bearer {login.get_json()['data']['access_token']}"},
        json={"email": "collab@example.com", "role": "project_viewer", "project_id": str(project_id)},
    )
    assert invite.status_code == 201
    token = invite.get_json()["data"]["token"]
    accept = client.post(f"/api/auth/accept-invite/{token}", json={"email": "collab@example.com", "password": "Password123!", "full_name": "Collab"})
    assert accept.status_code == 200
    user = db.users.find_one({"email": "collab@example.com"})
    assert db.project_members.find_one({"user_id": user["_id"], "project_id": project_id}) is not None


def test_external_collaborator_invite_rejected_when_disabled(client, db):
    owner = db.users.insert_one({"_id": ObjectId(), "email": "owner2@example.com", "password_hash": hash_password("Password123!"), "display_name": "Owner", "status": "active", "system_role": "super_admin", "is_deleted": False}).inserted_id
    db.organisations.insert_one({"_id": ObjectId(), "name": "Closed Org", "status": "active", "settings": {"allow_external_collaborators": False}, "is_deleted": False})
    org = db.organisations.find_one({"name": "Closed Org"})
    project_id = ObjectId()
    db.projects.insert_one({"_id": project_id, "org_id": org["_id"], "name": "Closed Project", "status": "active", "shared_org_ids": [], "is_deleted": False})
    login = client.post("/api/auth/login", json={"email": "owner2@example.com", "password": "Password123!"})
    invite = client.post(
        f"/api/admin/orgs/{org['_id']}/invite",
        headers={"Authorization": f"Bearer {login.get_json()['data']['access_token']}"},
        json={"email": "collab2@example.com", "role": "project_viewer", "project_id": str(project_id)},
    )
    assert invite.status_code in {400, 403}
