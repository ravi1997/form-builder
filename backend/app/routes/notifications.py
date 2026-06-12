from flask import Blueprint, jsonify, request
from bson import ObjectId

from app.extensions import mongo
from app.services.auth_service import decode_request_bearer_token
from app.services.notification_service import (
    deregister_device_token,
    get_notification_template,
    get_unread_count,
    get_vapid_public_key,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    register_device_token,
)

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/internal/v1/notifications")


def _current_user_id():
    try:
        _, decoded = decode_request_bearer_token(request.headers.get("Authorization", ""))
        return decoded.get("sub") or decoded.get("user_id")
    except ValueError:
        return None


@notifications_bp.route("/device-token", methods=["POST"])
def register_token():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"status": "error", "code": "UNAUTHORIZED", "message": "Unauthorized"}), 401
    data = request.get_json() or {}
    token = data.get("token")
    platform = data.get("platform")
    if not token or platform not in {"android", "ios", "web"}:
        return jsonify({"status": "error", "code": "BAD_REQUEST", "message": "token and valid platform required"}), 400
    register_device_token(user_id, token, platform)
    return jsonify({"status": "success", "data": {"token": token, "platform": platform}}), 200


@notifications_bp.route("/device-token", methods=["DELETE"])
def remove_token():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"status": "error", "code": "UNAUTHORIZED", "message": "Unauthorized"}), 401
    data = request.get_json() or {}
    token = data.get("token")
    if not token:
        return jsonify({"status": "error", "code": "BAD_REQUEST", "message": "token required"}), 400
    deregister_device_token(user_id, token)
    return jsonify({"status": "success", "data": {"token": token}}), 200


@notifications_bp.route("/vapid-public-key", methods=["GET"])
def vapid_public_key():
    return jsonify({"status": "success", "data": {"public_key": get_vapid_public_key()}}), 200


@notifications_bp.route("/unread-count", methods=["GET"])
def unread_count():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"status": "error", "code": "UNAUTHORIZED", "message": "Unauthorized"}), 401
    return jsonify({"status": "success", "data": {"unread_count": get_unread_count(user_id)}}), 200


@notifications_bp.route("", methods=["GET"])
def list_user_notifications():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"status": "error", "code": "UNAUTHORIZED", "message": "Unauthorized"}), 401
    page = request.args.get("page", 1, type=int)
    limit = min(request.args.get("limit", 20, type=int), 100)
    filter_state = request.args.get("filter", "all")
    data = list_notifications(user_id, page=page, limit=limit, filter_state=filter_state)
    return jsonify({"status": "success", "data": data}), 200


@notifications_bp.route("/<notification_id>/read", methods=["POST"])
def read_notification(notification_id):
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"status": "error", "code": "UNAUTHORIZED", "message": "Unauthorized"}), 401
    if not mark_notification_read(user_id, notification_id):
        return jsonify({"status": "error", "code": "NOT_FOUND", "message": "Notification not found"}), 404
    return jsonify({"status": "success", "data": {"notification_id": notification_id}}), 200


@notifications_bp.route("/read-all", methods=["POST"])
def read_all_notifications():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"status": "error", "code": "UNAUTHORIZED", "message": "Unauthorized"}), 401
    mark_all_notifications_read(user_id)
    return jsonify({"status": "success", "data": {"unread_count": get_unread_count(user_id)}}), 200


@notifications_bp.route("/webhooks/<webhook_config_id>/test", methods=["POST"])
def test_webhook(webhook_config_id):
    config = mongo.db.webhook_configs.find_one({"_id": ObjectId(webhook_config_id), "is_deleted": False})
    if not config:
        return jsonify({"status": "error", "code": "NOT_FOUND", "message": "Webhook not found"}), 404
    template = {
        "id": "test-delivery-00000000",
        "event_type": "webhook.test",
        "timestamp": "2025-01-15T10:30:00Z",
        "org_id": str(config.get("org_id")),
        "data": {
            "message": "This is a test webhook delivery from Form Builder Platform.",
            "webhook_config_id": str(config.get("_id")),
            "webhook_name": config.get("name"),
        },
    }
    return jsonify({"status": "success", "data": template}), 200
