import pytest
import datetime
from bson import ObjectId
from app.services.compliance_service import is_resource_held, create_legal_hold, list_legal_holds, toggle_legal_hold
from app.services.quota_service import calculate_organization_quota, enforce_org_quota, get_storage_quota
def test_tier1_quota_calculation_updates_db(db):
    org_id = ObjectId()
    
    # Seed storage quota config
    db.storage_quotas.insert_one({
        "org_id": org_id,
        "quota_bytes": 10000,
        "warning_threshold": 0.8,
        "used_bytes": {"files": 0, "database": 0, "total": 0},
        "last_calculated_at": datetime.datetime.utcnow()
    })
    
    # Calculate organization quota (calls dbstats and checks uploads folder size)
    doc = calculate_organization_quota(org_id)
    
    assert doc["org_id"] == org_id
    assert "used_bytes" in doc
    assert "total" in doc["used_bytes"]
    
    # Verify DB has been updated
    db_doc = db.storage_quotas.find_one({"org_id": org_id})
    assert db_doc is not None
    assert db_doc["used_bytes"]["total"] == doc["used_bytes"]["total"]


def test_tier1_warning_threshold_flagging(db):
    org_id = ObjectId()
    
    # Quota is 1000 bytes, used total is 850 bytes (85%)
    db.storage_quotas.insert_one({
        "org_id": org_id,
        "quota_bytes": 1000,
        "warning_threshold": 0.8,
        "used_bytes": {"files": 400, "database": 450, "total": 850},
        "last_calculated_at": datetime.datetime.utcnow()
    })
    
    quota_doc = get_storage_quota(org_id)
    used = quota_doc["used_bytes"]["total"]
    quota_limit = quota_doc["quota_bytes"]
    threshold = quota_doc["warning_threshold"]
    
    # Check if used bytes exceeds the 80% threshold
    assert used >= quota_limit * threshold


def test_tier1_block_form_creation_when_quota_full(client, db, get_auth_headers):
    org_id = ObjectId()
    project_id = ObjectId()
    
    # Seed user for auth
    user_id = ObjectId()
    user_doc = {
        "_id": user_id,
        "email": "admin@company.com",
        "system_role": "user",
        "status": "active",
        "is_deleted": False
    }
    db.users.insert_one(user_doc)
    db.org_memberships.insert_one({
        "user_id": user_id,
        "org_id": org_id,
        "role": "org_admin",
        "status": "active",
        "is_deleted": False
    })
    
    headers = get_auth_headers(user_doc)
    
    # Seed full quota
    db.storage_quotas.insert_one({
        "org_id": org_id,
        "quota_bytes": 1000,
        "warning_threshold": 0.8,
        "used_bytes": {"files": 500, "database": 500, "total": 1000},
        "last_calculated_at": datetime.datetime.utcnow()
    })
    
    # Try to create form -> should fail with 403 QUOTA_EXCEEDED
    res = client.post(
        "/api/internal/v1/forms",
        json={
            "name": "Blocked E2E Form",
            "org_id": str(org_id),
            "project_id": str(project_id),
            "author_id": str(user_id)
        },
        headers=headers
    )
    
    assert res.status_code == 403
    assert res.get_json()["code"] == "QUOTA_EXCEEDED"


def test_tier1_create_and_toggle_compliance_holds_via_route(client, db, get_auth_headers):
    org_id = ObjectId()
    form_id = ObjectId()
    
    user_id = ObjectId()
    user_doc = {
        "_id": user_id,
        "email": "compliance@company.com",
        "system_role": "user",
        "status": "active",
        "is_deleted": False
    }
    db.users.insert_one(user_doc)
    db.org_memberships.insert_one({
        "user_id": user_id,
        "org_id": org_id,
        "role": "org_admin",
        "status": "active",
        "is_deleted": False
    })
    
    headers = get_auth_headers(user_doc)
    
    # Create legal hold via POST route
    res = client.post(
        f"/api/orgs/{org_id}/compliance/holds",
        json={
            "name": "GDPR Hold",
            "description": "GDPR Compliance Hold",
            "target_type": "form",
            "target_ids": [str(form_id)]
        },
        headers=headers
    )
    
    assert res.status_code == 201
    hold_data = res.get_json()["data"]
    hold_id = hold_data["_id"]
    assert hold_data["is_active"] is True
    
    # Verify hold is active in DB
    db_hold = db.legal_holds.find_one({"_id": ObjectId(hold_id)})
    assert db_hold["is_active"] is True
    
    # Toggle hold off via PUT route
    res_put = client.put(
        f"/api/compliance/holds/{hold_id}",
        json={"is_active": False},
        headers=headers
    )
    
    assert res_put.status_code == 200
    db_hold = db.legal_holds.find_one({"_id": ObjectId(hold_id)})
    assert db_hold["is_active"] is False


def test_tier1_block_deletion_of_held_resources(client, db, get_auth_headers):
    org_id = ObjectId()
    project_id = ObjectId()
    form_id = ObjectId()
    
    user_id = ObjectId()
    user_doc = {
        "_id": user_id,
        "email": "admin@company.com",
        "system_role": "user",
        "status": "active",
        "is_deleted": False
    }
    db.users.insert_one(user_doc)
    db.org_memberships.insert_one({
        "user_id": user_id,
        "org_id": org_id,
        "role": "org_admin",
        "status": "active",
        "is_deleted": False
    })
    
    headers = get_auth_headers(user_doc)
    
    db.projects.insert_one({"_id": project_id, "org_id": org_id, "is_deleted": False})
    db.forms.insert_one({
        "_id": form_id,
        "org_id": org_id,
        "project_id": project_id,
        "is_deleted": False
    })
    
    # Apply legal hold to form
    create_legal_hold(org_id, "Form Hold", "Hold desc", "form", [form_id], user_id)
    
    # Try deleting form -> should block with 409
    res = client.delete(f"/api/internal/v1/forms/{form_id}", headers=headers)
    assert res.status_code == 409
    assert res.get_json()["code"] == "LEGAL_HOLD_ACTIVE"


def test_tier2_quota_boundary_check(db):
    org_id = ObjectId()
    
    # Used 999 bytes out of 1000 bytes (1 byte left)
    db.storage_quotas.insert_one({
        "org_id": org_id,
        "quota_bytes": 1000,
        "warning_threshold": 0.8,
        "used_bytes": {"files": 500, "database": 499, "total": 999},
        "last_calculated_at": datetime.datetime.utcnow()
    })
    
    # 0 requested bytes -> should succeed
    enforce_org_quota(org_id, requested_bytes=0)
    
    # 1 requested byte -> should exceed (since used + 1 = 1000 >= 1000 quota limit)
    with pytest.raises(ValueError) as exc:
        enforce_org_quota(org_id, requested_bytes=1)
    assert "quota exceeded" in str(exc.value).lower()


def test_tier2_deletion_propagation_blocking(client, db, get_auth_headers):
    org_id = ObjectId()
    project_id = ObjectId()
    form_id = ObjectId()
    response_id = ObjectId()
    
    user_id = ObjectId()
    user_doc = {
        "_id": user_id,
        "email": "admin@company.com",
        "system_role": "user",
        "status": "active",
        "is_deleted": False
    }
    db.users.insert_one(user_doc)
    db.org_memberships.insert_one({
        "user_id": user_id,
        "org_id": org_id,
        "role": "org_admin",
        "status": "active",
        "is_deleted": False
    })
    
    headers = get_auth_headers(user_doc)
    
    db.projects.insert_one({"_id": project_id, "org_id": org_id, "is_deleted": False})
    db.forms.insert_one({
        "_id": form_id,
        "org_id": org_id,
        "project_id": project_id,
        "is_deleted": False
    })
    db.responses.insert_one({
        "_id": response_id,
        "form_id": form_id,
        "is_deleted": False
    })
    
    # Place project on hold
    create_legal_hold(org_id, "Project Hold", "Hold desc", "project", [project_id], user_id)
    
    # Try deleting child response -> should fail because project hold propagates to child form and response
    res = client.delete(f"/api/internal/v1/forms/responses/{response_id}", headers=headers)
    assert res.status_code == 409
    assert res.get_json()["code"] == "LEGAL_HOLD_ACTIVE"


def test_tier2_toggle_hold_off_restores_delete(client, db, get_auth_headers):
    org_id = ObjectId()
    project_id = ObjectId()
    form_id = ObjectId()
    
    user_id = ObjectId()
    user_doc = {
        "_id": user_id,
        "email": "admin@company.com",
        "system_role": "user",
        "status": "active",
        "is_deleted": False
    }
    db.users.insert_one(user_doc)
    db.org_memberships.insert_one({
        "user_id": user_id,
        "org_id": org_id,
        "role": "org_admin",
        "status": "active",
        "is_deleted": False
    })
    
    headers = get_auth_headers(user_doc)
    
    db.projects.insert_one({"_id": project_id, "org_id": org_id, "is_deleted": False})
    db.forms.insert_one({
        "_id": form_id,
        "org_id": org_id,
        "project_id": project_id,
        "is_deleted": False
    })
    
    hold = create_legal_hold(org_id, "Form Hold", "Hold desc", "form", [form_id], user_id)
    
    # Verify blocked
    res = client.delete(f"/api/internal/v1/forms/{form_id}", headers=headers)
    assert res.status_code == 409
    
    # Release hold
    toggle_legal_hold(hold["_id"], False)
    
    # Try deleting again -> should succeed
    res2 = client.delete(f"/api/internal/v1/forms/{form_id}", headers=headers)
    assert res2.status_code == 200
    assert db.forms.find_one({"_id": form_id})["is_deleted"] is True


def test_tier2_hold_nonexistent_ids_graceful(db):
    # Testing that check handles non-existent IDs safely
    nonexistent_id = ObjectId()
    assert is_resource_held("form", nonexistent_id) is False
    assert is_resource_held("project", nonexistent_id) is False
    assert is_resource_held("response", nonexistent_id) is False


def test_tier2_restrict_compliance_access_to_org_admin(client, db, get_auth_headers):
    org_id = ObjectId()
    
    # Standard user without compliance permissions (role = org_viewer)
    user_viewer = {
        "_id": ObjectId(),
        "email": "viewer@company.com",
        "system_role": "user",
        "status": "active",
        "is_deleted": False
    }
    db.users.insert_one(user_viewer)
    db.org_memberships.insert_one({
        "user_id": user_viewer["_id"],
        "org_id": org_id,
        "role": "org_viewer",
        "status": "active",
        "is_deleted": False
    })
    headers_viewer = get_auth_headers(user_viewer)
    
    # Admin user (role = org_admin)
    user_admin = {
        "_id": ObjectId(),
        "email": "admin@company.com",
        "system_role": "user",
        "status": "active",
        "is_deleted": False
    }
    db.users.insert_one(user_admin)
    db.org_memberships.insert_one({
        "user_id": user_admin["_id"],
        "org_id": org_id,
        "role": "org_admin",
        "status": "active",
        "is_deleted": False
    })
    headers_admin = get_auth_headers(user_admin)
    
    # Normal viewer gets 403 on holds GET
    res_viewer_get = client.get(f"/api/orgs/{org_id}/compliance/holds", headers=headers_viewer)
    assert res_viewer_get.status_code == 403
    
    # Normal viewer gets 403 on holds POST
    res_viewer_post = client.post(
        f"/api/orgs/{org_id}/compliance/holds",
        json={"name": "Viewer Hold", "target_type": "form", "target_ids": []},
        headers=headers_viewer
    )
    assert res_viewer_post.status_code == 403
    
    # Admin succeeds on GET
    res_admin_get = client.get(f"/api/orgs/{org_id}/compliance/holds", headers=headers_admin)
    assert res_admin_get.status_code == 200


def test_tier3_f2_x_f3_upload_quota_enforcement(db):
    org_id = ObjectId()
    
    # 500 bytes used out of 1000 bytes (500 bytes left)
    db.storage_quotas.insert_one({
        "org_id": org_id,
        "quota_bytes": 1000,
        "warning_threshold": 0.8,
        "used_bytes": {"files": 200, "database": 300, "total": 500},
        "last_calculated_at": datetime.datetime.utcnow()
    })
    
    # Simulate calculating a 400 bytes file upload size -> should succeed
    enforce_org_quota(org_id, requested_bytes=400)
    
    # Simulate calculating a 600 bytes file upload size -> should fail
    with pytest.raises(ValueError) as exc:
        enforce_org_quota(org_id, requested_bytes=600)
    assert "quota exceeded" in str(exc.value).lower()
