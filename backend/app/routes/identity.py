import datetime

from flask import Blueprint, current_app, jsonify, request, redirect
import jwt

from app.extensions import limiter
from app.extensions import mongo, redis_client
from app.services.auth_service import (
    create_api_key,
    create_oauth_authorization_code,
    create_oauth_client,
    exchange_oauth_authorization_code,
    authorize_oauth_consent,
    verify_bearer_token,
    verify_api_key,
    verify_oauth_client,
)

identity_bp = Blueprint("identity", __name__, url_prefix="/api/v1")


def _success(data=None, message=None, status_code=200):
    payload = {"status": "success", "data": data or {}}
    if message:
        payload["message"] = message
    return jsonify(payload), status_code


def _error(code, message, status_code=400):
    return jsonify({"status": "error", "code": code, "message": message}), status_code


def _rate_limit_api_key(raw_key, limit_per_hour):
    if not redis_client:
        return
    key = f"apikey:{raw_key[:12]}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 3600)
    if count > limit_per_hour:
        raise OverflowError("rate limit exceeded")


def _api_key_limit_key():
    data = request.get_json(silent=True) or {}
    raw_key = data.get("api_key") or request.headers.get("X-API-Key") or request.headers.get("Authorization", "").replace("ApiKey", "").strip()
    return raw_key or request.remote_addr


def _api_key_limit_value():
    data = request.get_json(silent=True) or {}
    raw_key = data.get("api_key")
    if not raw_key:
        return "60 per minute"
    try:
        doc = verify_api_key(raw_key, org_id=data.get("org_id"), scope=data.get("scope"))
        limit = int(doc.get("rate_limit_per_hour", 1000))
        return f"{limit} per hour"
    except Exception:
        return "60 per minute"


@identity_bp.route("/api-keys", methods=["POST"])
def create_key():
    data = request.get_json() or {}
    org_id = data.get("org_id")
    user_id = data.get("user_id")
    scopes = data.get("scopes") or []
    name = data.get("name")
    if not org_id or not user_id or not name:
        return _error("BAD_REQUEST", "org_id, user_id and name are required")
    raw_key, doc = create_api_key(org_id, user_id, scopes, name, rate_limit_per_hour=data.get("rate_limit_per_hour", 1000))
    return _success({"api_key": raw_key, "api_key_id": str(doc["_id"])} , "API key created", 201)


@identity_bp.route("/api-keys/verify", methods=["POST"])
@limiter.limit(_api_key_limit_value, key_func=_api_key_limit_key)
def verify_key():
    data = request.get_json() or {}
    raw_key = data.get("api_key")
    if not raw_key:
        return _error("BAD_REQUEST", "api_key is required")
    try:
        doc = verify_api_key(raw_key, org_id=data.get("org_id"), scope=data.get("scope"))
        return _success({"api_key_id": str(doc["_id"]), "org_id": str(doc["org_id"]), "scopes": doc.get("scopes", [])})
    except ValueError as exc:
        return _error("UNAUTHORIZED", str(exc), 401)


@identity_bp.route("/oauth/clients", methods=["POST"])
def create_client():
    data = request.get_json() or {}
    required = ["org_id", "name", "redirect_uris", "scopes", "grant_types"]
    if any(not data.get(key) for key in required):
        return _error("BAD_REQUEST", ", ".join(required) + " are required")
    secret, doc = create_oauth_client(data["org_id"], data["name"], data["redirect_uris"], data["scopes"], data["grant_types"])
    return _success({"client_id": doc["client_id"], "client_secret": secret}, "OAuth client created", 201)


@identity_bp.route("/oauth/token", methods=["POST"])
def oauth_token():
    grant_type = request.form.get("grant_type")
    client_id = request.form.get("client_id")
    client_secret = request.form.get("client_secret")
    if grant_type == "client_credentials":
        scope = request.form.get("scope", "")
        try:
            client_doc = verify_oauth_client(client_id, client_secret)
        except ValueError as exc:
            return _error("UNAUTHORIZED", str(exc), 401)
        token = __import__("app.services.auth_service", fromlist=["issue_client_credentials_token"]).issue_client_credentials_token(client_doc, scope)
        return _success({"access_token": token, "token_type": "Bearer", "expires_in": 3600, "scope": scope})
    if grant_type == "authorization_code":
        code = request.form.get("code")
        redirect_uri = request.form.get("redirect_uri")
        try:
            access_token, scope, _ = exchange_oauth_authorization_code(code, client_id, client_secret, redirect_uri)
            return _success({"access_token": access_token, "token_type": "Bearer", "expires_in": 900, "scope": scope})
        except ValueError as exc:
            return _error("UNAUTHORIZED", str(exc), 401)
    return _error("BAD_REQUEST", "Unsupported grant_type")


@identity_bp.route("/oauth/authorize", methods=["GET", "POST"])
def oauth_authorize():
    response_type = request.args.get("response_type")
    client_id = request.args.get("client_id")
    redirect_uri = request.args.get("redirect_uri")
    scope = request.args.get("scope", "")
    state = request.args.get("state", "")
    if response_type != "code":
        return _error("BAD_REQUEST", "response_type=code required")
    if request.method == "GET":
        return _success({"client_id": client_id, "redirect_uri": redirect_uri, "scope": scope, "state": state, "consent_required": True})
    auth_header = request.headers.get("Authorization", "")
    try:
        user_doc, decoded = verify_bearer_token(auth_header.split(" ", 1)[1]) if auth_header.startswith("Bearer ") else (None, None)
    except Exception:
        return _error("UNAUTHORIZED", "Bearer token required", 401)
    if not user_doc:
        return _error("UNAUTHORIZED", "Bearer token required", 401)
    try:
        code = authorize_oauth_consent(client_id, user_doc, scope, redirect_uri, state=state)
        return _success({"code": code, "state": state})
    except ValueError as exc:
        return _error("FORBIDDEN", str(exc), 403)
