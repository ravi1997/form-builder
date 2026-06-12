import datetime
import json

from app.extensions import mongo
from app.services.notification_service import (
    create_in_app_notification,
    notify_super_admins_of_failure,
    record_delivery_attempt,
    schedule_retry,
    send_email,
    send_sms,
)

# Get Celery app from shared config
from .celery_config import get_celery_app
celery_app = get_celery_app()


def _get_notification_log(log_id):
    return mongo.db.notification_log.find_one({"_id": log_id})


@celery_app.task(name="app.workers.notification_tasks.send_email_task")
def send_email_task(log_id, recipient_email, subject, body_html, body_text):
    log = _get_notification_log(log_id)
    if not log:
        return {"status": "failed", "error": "notification_log not found"}
    try:
        response = send_email(recipient_email, subject, body_html, body_text, log_id)
        provider_response = {"status_code": response.status_code, "response_body": response.text}
        try:
            provider_json = response.json()
            provider_response["provider_json"] = provider_json
        except Exception:
            provider_json = None
        if response.status_code in (200, 202):
            if provider_json and isinstance(provider_json, dict):
                provider_response["message_id"] = provider_json.get("message_id")
            record_delivery_attempt(log_id, "delivered", provider_response=provider_response)
            return {"status": "delivered"}
        record_delivery_attempt(log_id, "retrying", provider_response=provider_response)
        schedule_retry(log_id, 60)
        return {"status": "retrying"}
    except Exception as exc:
        record_delivery_attempt(log_id, "retrying", provider_response={"error": str(exc)})
        schedule_retry(log_id, 60)
        return {"status": "retrying", "error": str(exc)}


@celery_app.task(name="app.workers.notification_tasks.send_sms_task")
def send_sms_task(log_id, recipient_phone, message):
    log = _get_notification_log(log_id)
    if not log:
        return {"status": "failed", "error": "notification_log not found"}
    try:
        response = send_sms(recipient_phone, message, log_id)
        provider_response = {"status_code": response.status_code, "response_body": response.text}
        try:
            provider_json = response.json()
            provider_response["provider_json"] = provider_json
        except Exception:
            provider_json = None
        if response.status_code in (200, 202):
            if provider_json and isinstance(provider_json, dict):
                provider_response["sms_id"] = provider_json.get("sms_id")
            record_delivery_attempt(log_id, "delivered", provider_response=provider_response)
            return {"status": "delivered"}
        code = None
        if provider_json and isinstance(provider_json, dict):
            code = provider_json.get("code")
        if code in {"INVALID_NUMBER", "BLACKLISTED", "DUPLICATE_MESSAGE"}:
            record_delivery_attempt(log_id, "failed", provider_response=provider_response)
            notify_super_admins_of_failure(
                "notification.sms.failed",
                f"SMS notification log {log_id} failed with non-retriable error.",
            )
            return {"status": "failed"}
        record_delivery_attempt(log_id, "retrying", provider_response=provider_response)
        schedule_retry(log_id, 60)
        return {"status": "retrying"}
    except Exception as exc:
        record_delivery_attempt(log_id, "retrying", provider_response={"error": str(exc)})
        schedule_retry(log_id, 60)
        return {"status": "retrying", "error": str(exc)}

