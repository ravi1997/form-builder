from flask import Blueprint, current_app, jsonify, request

from app.services.auth_service import decode_request_bearer_token
from app.services.sync_service import get_sync_delta

sync_bp = Blueprint("sync", __name__, url_prefix="/api/internal/v1/sync")


def _require_auth():
    if current_app.config.get("TESTING"):
        return None

    try:
        decode_request_bearer_token(request.headers.get("Authorization", ""))
    except ValueError:
        return jsonify({"status": "error", "code": "UNAUTHORIZED", "message": "Invalid token"}), 401

    return None


@sync_bp.route("", methods=["GET"])
def get_sync():
    auth_response = _require_auth()
    if auth_response is not None:
        return auth_response

    last_synced_at = request.args.get("last_synced_at")
    payload = get_sync_delta(last_synced_at)
    return jsonify(
        {
            "status": "success",
            "data": payload,
        }
    ), 200
