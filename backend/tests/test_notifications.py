import datetime

from bson import ObjectId
from app.services.auth_service import hash_password


def test_notifications_registration_and_archive_endpoints(client, db):
    user_id = ObjectId()
    db.users.insert_one(
        {
            "_id": user_id,
            "email": "doctor@aiims.edu",
            "password_hash": hash_password("Password123!"),
            "status": "active",
            "system_role": "user",
            "is_deleted": False,
            "device_tokens": [],
        }
    )
    db.notification_log.insert_one(
        {
            "_id": ObjectId(),
            "org_id": ObjectId(),
            "recipient_id": user_id,
            "event_type": "response.submitted",
            "channel": "in_app",
            "status": "sent",
            "attempt_count": 1,
            "max_attempts": 1,
            "next_retry_at": None,
            "provider_response": None,
            "title": "New response",
            "body": "A response was submitted.",
            "action_url": "/forms/abc/responses",
            "is_read": False,
            "read_at": None,
            "metadata": {},
            "created_at": datetime.datetime.utcnow(),
            "last_attempt_at": datetime.datetime.utcnow(),
        }
    )

    token = client.post("/api/auth/login", json={"email": "doctor@aiims.edu", "password": "Password123!"}).get_json()["data"]["access_token"]
    res = client.post(
        "/api/internal/v1/notifications/device-token",
        json={"token": "abc", "platform": "android"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200

    res = client.get(
        "/api/internal/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["unread_count"] == 1

    res = client.get(
        "/api/internal/v1/notifications?page=1&limit=20&filter=unread",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert len(res.get_json()["data"]["notifications"]) == 1
