import datetime
import hashlib
import hmac
import json
from typing import Any

import requests
from bson import ObjectId
from flask import current_app

from app.extensions import mongo, redis_client


def _now():
    return datetime.datetime.utcnow()


def _oid(value):
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    if ObjectId.is_valid(str(value)):
        return ObjectId(str(value))
    return value


def _serialize(doc):
    if not doc:
        return doc
    if isinstance(doc, list):
        return [_serialize(item) for item in doc]
    if isinstance(doc, dict):
        out = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                out[key] = str(value)
            elif isinstance(value, datetime.datetime):
                out[key] = value.isoformat()
            else:
                out[key] = value
        return out
    return doc


def _get_system_config(key: str, default=None):
    doc = mongo.db.system_config.find_one({"key": key})
    if not doc:
        return default
    return doc.get("value", default)


def _upsert_log(payload: dict[str, Any]) -> dict[str, Any]:
    payload = dict(payload)
    payload.setdefault("created_at", _now())
    payload.setdefault("last_attempt_at", _now())
    payload.setdefault("attempt_count", 1)
    payload.setdefault("max_attempts", 1)
    payload.setdefault("status", "sent")
    payload.setdefault("is_read", False)
    payload.setdefault("read_at", None)
    result = mongo.db.notification_log.insert_one(payload)
    payload["_id"] = result.inserted_id
    return payload


def create_in_app_notification(
    *,
    org_id,
    recipient_id,
    event_type,
    title,
    body,
    action_url=None,
    rule_id=None,
    metadata=None,
):
    doc = _upsert_log(
        {
            "org_id": _oid(org_id),
            "rule_id": _oid(rule_id),
            "event_type": event_type,
            "recipient_id": _oid(recipient_id),
            "channel": "in_app",
            "status": "sent",
            "attempt_count": 1,
            "max_attempts": 1,
            "next_retry_at": None,
            "provider_response": None,
            "title": title,
            "body": body,
            "action_url": action_url,
            "is_read": False,
            "read_at": None,
            "metadata": metadata or {},
            "last_attempt_at": _now(),
        }
    )
    return _serialize(doc)


def register_device_token(user_id, token, platform):
    user_oid = _oid(user_id)
    token_entry = {"token": token, "platform": platform, "created_at": _now()}
    mongo.db.users.update_one(
        {"_id": user_oid, "is_deleted": False},
        {"$pull": {"device_tokens": {"token": token}}, "$push": {"device_tokens": token_entry}},
    )
    return token_entry


def deregister_device_token(user_id, token):
    user_oid = _oid(user_id)
    mongo.db.users.update_one(
        {"_id": user_oid, "is_deleted": False},
        {"$pull": {"device_tokens": {"token": token}}},
    )


def get_unread_count(user_id):
    return mongo.db.notification_log.count_documents(
        {
            "recipient_id": _oid(user_id),
            "channel": "in_app",
            "is_read": False,
        }
    )


def list_notifications(user_id, page=1, limit=20, filter_state="all"):
    query = {"recipient_id": _oid(user_id), "channel": "in_app"}
    if filter_state == "unread":
        query["is_read"] = False
    elif filter_state == "read":
        query["is_read"] = True
    total = mongo.db.notification_log.count_documents(query)
    cursor = (
        mongo.db.notification_log.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )
    items = []
    for doc in cursor:
        items.append(
            {
                "notification_id": str(doc["_id"]),
                "event_type": doc.get("event_type"),
                "title": doc.get("title"),
                "body": doc.get("body"),
                "action_url": doc.get("action_url"),
                "is_read": doc.get("is_read", False),
                "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                "metadata": doc.get("metadata", {}),
            }
        )
    return {
        "notifications": items,
        "total": total,
        "page": page,
        "limit": limit,
        "unread_count": get_unread_count(user_id),
    }


def mark_notification_read(user_id, notification_id):
    result = mongo.db.notification_log.update_one(
        {
            "_id": _oid(notification_id),
            "recipient_id": _oid(user_id),
            "channel": "in_app",
        },
        {
            "$set": {
                "is_read": True,
                "read_at": _now(),
            }
        },
    )
    return result.modified_count > 0


def mark_all_notifications_read(user_id):
    mongo.db.notification_log.update_many(
        {"recipient_id": _oid(user_id), "channel": "in_app", "is_read": False},
        {"$set": {"is_read": True, "read_at": _now()}},
    )


def get_vapid_public_key():
    return _get_system_config("vapid_public_key", current_app.config.get("VAPID_PUBLIC_KEY"))


def compute_webhook_signature(secret: str, payload_bytes: bytes) -> str:
    mac = hmac.new(secret.encode("utf-8"), payload_bytes, digestmod=hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def get_notification_template(event_type: str, org_id):
    org_oid = _oid(org_id)
    template = mongo.db.notification_templates.find_one(
        {"event_type": event_type, "org_id": org_oid, "is_active": True}
    )
    if template:
        return template
    return mongo.db.notification_templates.find_one(
        {"event_type": event_type, "org_id": None, "is_active": True}
    )


def send_email(recipient_email, subject, body_html, body_text, log_id):
    url = _get_system_config("email_api_url")
    token = _get_system_config("email_api_token")
    from_name = _get_system_config("smtp_from_name", "Form Builder Platform")
    from_email = _get_system_config("smtp_from_email", "noreply@aiims.edu")
    if not url or not token:
        raise RuntimeError("Email API not configured")
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        json={
            "to": recipient_email,
            "subject": subject,
            "body_html": body_html,
            "body_text": body_text,
            "from_name": from_name,
            "from_email": from_email,
            "reply_to": None,
            "metadata": {"notification_log_id": str(log_id)},
        },
        timeout=(10, 30),
        verify=True,
    )
    return response


def send_sms(recipient_phone, message, log_id):
    url = _get_system_config("sms_api_url")
    token = _get_system_config("sms_api_token")
    if not url or not token:
        raise RuntimeError("SMS API not configured")
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        json={
            "to": recipient_phone,
            "message": message,
            "metadata": {"notification_log_id": str(log_id)},
        },
        timeout=(10, 30),
        verify=True,
    )
    return response


def record_delivery_attempt(log_id, status, provider_response=None, next_retry_at=None):
    update = {
        "status": status,
        "provider_response": provider_response,
        "last_attempt_at": _now(),
    }
    if next_retry_at is not None:
        update["next_retry_at"] = next_retry_at
    mongo.db.notification_log.update_one({"_id": _oid(log_id)}, {"$set": update})


def schedule_retry(log_id, delay_seconds):
    retry_at = _now() + datetime.timedelta(seconds=delay_seconds)
    record_delivery_attempt(log_id, "retrying", next_retry_at=retry_at)
    return retry_at


def notify_super_admins_of_failure(event_type, message):
    admins = mongo.db.users.find({"system_role": "super_admin", "is_deleted": False})
    for user in admins:
        create_in_app_notification(
            org_id=None,
            recipient_id=user["_id"],
            event_type=event_type,
            title="Notification delivery failed",
            body=message,
            action_url=None,
            metadata={"severity": "high"},
        )

