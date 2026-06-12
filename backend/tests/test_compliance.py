import pytest
from bson import ObjectId
import datetime
from app.services.compliance_service import is_resource_held

def test_compliance_service_is_held(db):
    org_id = ObjectId()
    form_id = ObjectId()
    project_id = ObjectId()
    response_id = ObjectId()
    
    # Insert test data
    db.forms.insert_one({
        "_id": form_id,
        "org_id": org_id,
        "name": "Gdpr Audit Form",
        "is_deleted": False,
        "project_id": project_id
    })
    db.responses.insert_one({
        "_id": response_id,
        "form_id": form_id,
        "is_deleted": False
    })
    
    # 1. No holds initially
    assert not is_resource_held("form", form_id)
    assert not is_resource_held("project", project_id)
    assert not is_resource_held("response", response_id)
    
    # 2. Add legal hold on project
    hold_id = db.legal_holds.insert_one({
        "org_id": org_id,
        "name": "GDPR Project Legal Hold",
        "description": "GPDR hold description",
        "target_type": "project",
        "target_ids": [project_id],
        "is_active": True,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "created_by": ObjectId()
    }).inserted_id
    
    # Verify hold propagates to form and response
    assert is_resource_held("project", project_id)
    assert is_resource_held("form", form_id)
    assert is_resource_held("response", response_id)
    
    # 3. Deactivate hold
    db.legal_holds.update_one({"_id": hold_id}, {"$set": {"is_active": False}})
    assert not is_resource_held("form", form_id)
    assert not is_resource_held("response", response_id)


def test_delete_endpoints_compliance_block(client, db):
    org_id = ObjectId()
    form_id = ObjectId()
    project_id = ObjectId()
    response_id = ObjectId()
    
    db.forms.insert_one({
        "_id": form_id,
        "org_id": org_id,
        "name": "Gdpr Audit Form",
        "is_deleted": False,
        "project_id": project_id
    })
    db.responses.insert_one({
        "_id": response_id,
        "form_id": form_id,
        "is_deleted": False
    })
    
    # Set active legal hold on the form
    db.legal_holds.insert_one({
        "org_id": org_id,
        "name": "GDPR Legal Hold",
        "description": "GPDR hold description",
        "target_type": "form",
        "target_ids": [form_id],
        "is_active": True,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "created_by": ObjectId()
    })
    
    # Try to delete form via route -> should fail with 409
    res = client.delete(f"/api/internal/v1/forms/{form_id}")
    assert res.status_code == 409
    assert res.get_json()["code"] == "LEGAL_HOLD_ACTIVE"
    
    # Try to delete response via route -> should fail with 409 (since form is held)
    res_resp = client.delete(f"/api/internal/v1/forms/responses/{response_id}")
    assert res_resp.status_code == 409
    assert res_resp.get_json()["code"] == "LEGAL_HOLD_ACTIVE"
    
    # Deactivate the hold
    db.legal_holds.update_many({}, {"$set": {"is_active": False}})
    
    # Try to delete form -> should succeed
    res = client.delete(f"/api/internal/v1/forms/{form_id}")
    assert res.status_code == 200
    assert db.forms.find_one({"_id": form_id})["is_deleted"] is True
