import datetime

from bson import ObjectId


def test_sync_delta_returns_updated_forms_and_tombstones(client, db):
    now = datetime.datetime.utcnow()
    form_id = ObjectId()
    deleted_form_id = ObjectId()

    db.forms.insert_one(
        {
            "_id": form_id,
            "org_id": ObjectId(),
            "project_id": ObjectId(),
            "name": "Patient Intake",
            "description": "Form sync test",
            "schema": {"sections": []},
            "branches": {"main": "commit_1"},
            "production_branch": "main",
            "is_deleted": False,
            "created_at": now,
            "updated_at": now,
        }
    )
    db.forms.insert_one(
        {
            "_id": deleted_form_id,
            "org_id": ObjectId(),
            "project_id": ObjectId(),
            "name": "Deleted Form",
            "description": "",
            "schema": {"sections": []},
            "branches": {"main": "commit_2"},
            "production_branch": "main",
            "is_deleted": True,
            "created_at": now,
            "updated_at": now,
        }
    )
    db.tombstones.insert_one(
        {
            "_id": ObjectId(),
            "org_id": ObjectId(),
            "entity_type": "forms",
            "entity_id": deleted_form_id,
            "deleted_at": now,
        }
    )

    response = client.get("/api/internal/v1/sync")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert len(data["data"]["updated"]) == 1
    assert data["data"]["updated"][0]["id"] == str(form_id)
    assert data["data"]["updated"][0]["schemaJson"] == {"sections": []}
    assert len(data["data"]["tombstones"]) == 1
    assert data["data"]["tombstones"][0]["entity_id"] == str(deleted_form_id)
