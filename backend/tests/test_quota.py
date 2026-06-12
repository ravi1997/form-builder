import datetime

from bson import ObjectId


def test_form_creation_blocked_when_quota_exceeded(client, db):
    org_id = ObjectId()
    project_id = ObjectId()
    db.storage_quotas.insert_one(
        {
            "_id": ObjectId(),
            "org_id": org_id,
            "quota_bytes": 1,
            "warning_threshold": 0.8,
            "used_bytes": {"files": 0, "database": 1, "total": 1},
            "last_calculated_at": datetime.datetime.utcnow(),
        }
    )
    res = client.post(
        "/api/internal/v1/forms",
        json={
            "name": "Blocked Form",
            "org_id": str(org_id),
            "project_id": str(project_id),
            "author_id": str(ObjectId()),
        },
    )
    assert res.status_code == 403
    assert res.get_json()["code"] == "QUOTA_EXCEEDED"
