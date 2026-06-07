# 11 — Notification System

> **Authoritative Reference**: See `CONTEXT.md §11` for the canonical event list, API endpoints, retry policy, and template variable list. This document expands on every aspect of the notification system with full implementation detail.

---

## Table of Contents

1. [Notification Channels Overview](#1-notification-channels-overview)
2. [Email Channel — API Integration](#2-email-channel--api-integration)
3. [SMS Channel — API Integration](#3-sms-channel--api-integration)
4. [Push Notification Channel](#4-push-notification-channel)
5. [In-App Notification Channel](#5-in-app-notification-channel)
6. [Webhook Channel](#6-webhook-channel)
7. [Notification Template System](#7-notification-template-system)
8. [Notification Rules](#8-notification-rules)
9. [Custom Notification Rules for Forms](#9-custom-notification-rules-for-forms)
10. [Rule Evaluation Algorithm](#10-rule-evaluation-algorithm)
11. [Celery Task Architecture](#11-celery-task-architecture)
12. [Retry Policy](#12-retry-policy)
13. [Notification Event Taxonomy](#13-notification-event-taxonomy)
14. [Notification Preferences](#14-notification-preferences)
15. [Notification Archive](#15-notification-archive)

---

## 1. Notification Channels Overview

The platform supports five notification channels. Each channel has a distinct delivery mechanism, auth strategy, and retry behaviour. A single notification rule may target one or more channels simultaneously.

| Channel  | Delivery Mechanism          | Auth Method            | Async?  | Retry? |
|----------|-----------------------------|------------------------|---------|--------|
| `email`  | HTTP POST to AIIMS Email API | Bearer token in header | Yes (Celery) | Yes (3 attempts) |
| `sms`    | HTTP POST to AIIMS SMS API   | Bearer token in header | Yes (Celery) | Yes (3 attempts) |
| `push`   | FCM (Android), APNs (iOS), Web Push | Service account / VAPID | Yes (Celery) | Yes (3 attempts) |
| `in_app` | WebSocket + persisted in DB  | JWT (user already authenticated) | Yes (socket) | N/A (DB-backed) |
| `webhook` | HTTP POST to caller-supplied URL | HMAC-SHA256 signature header | Yes (Celery) | Yes (3 attempts) |

All channel deliveries are dispatched by Celery workers (never synchronously in the Flask request cycle). The only exception is `in_app` socket emit, which is non-blocking and fire-and-forget via Flask-SocketIO's `emit()`.

---

## 2. Email Channel — API Integration

### 2.1 Endpoint

```
POST https://rpcapplication.aiims.edu/services/api/v1/mail/single
```

This URL is stored in `system_config` collection under key `email_api_url`. The bearer token is stored under key `email_api_token`. **Never** hardcode either value — always read from `system_config` at task execution time.

### 2.2 Request Structure

```http
POST /services/api/v1/mail/single HTTP/1.1
Host: rpcapplication.aiims.edu
Authorization: Bearer <email_api_token>
Content-Type: application/json
Accept: application/json
```

```json
{
  "to": "recipient@example.com",
  "subject": "Your form response has been received",
  "body_html": "<html><body><p>Dear John,</p>...</body></html>",
  "body_text": "Dear John, Your form response has been received.",
  "from_name": "Form Builder Platform",
  "from_email": "noreply@aiims.edu",
  "reply_to": null,
  "metadata": {
    "notification_log_id": "64f2c3d1a2b3c4d5e6f70001",
    "event_type": "response.submitted",
    "org_id": "64f2c3d1a2b3c4d5e6f70002"
  }
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `to` | string | Yes | Recipient email address (single recipient per call) |
| `subject` | string | Yes | Email subject line (rendered template, max 255 chars) |
| `body_html` | string | Yes | HTML body (rendered from template) |
| `body_text` | string | Yes | Plain text fallback (always provided) |
| `from_name` | string | Yes | Sender display name from `system_config.smtp_from_name` |
| `from_email` | string | Yes | Sender address from `system_config.smtp_from_email` |
| `reply_to` | string \| null | No | Optional reply-to address |
| `metadata` | object | No | Opaque metadata passed to the mail service for tracing |

> **Multiple recipients**: Send one HTTP call per recipient. Never batch multiple addresses in a single call — the AIIMS API expects a single `to` address.

### 2.3 Success Response

```json
{
  "status": "queued",
  "message_id": "aiims-mail-abc123"
}
```

HTTP status `200` or `202` is treated as success. Store `message_id` in `notification_log.provider_response`.

### 2.4 Error Response

```json
{
  "status": "error",
  "code": "INVALID_RECIPIENT",
  "message": "The recipient address is invalid."
}
```

Any HTTP status `4xx` or `5xx`, or a non-JSON response body, is treated as a delivery failure. The Celery task records the raw `status_code` and `response_body` in `notification_log.provider_response` and schedules a retry.

### 2.5 Implementation Location

- **Service**: `backend/app/services/notification_service.py` → `send_email(recipient_email, subject, body_html, body_text, log_id)`
- **Worker**: `backend/app/workers/notification_tasks.py` → `send_email_task`
- **Config load**: `notification_service._get_email_config()` reads `system_config` from MongoDB at runtime

### 2.6 Timeout and Connection

- Connection timeout: 10 seconds
- Read timeout: 30 seconds
- Library: `requests` with explicit `timeout=(10, 30)` tuple
- SSL verification: `verify=True` always (server cert must be valid)

### 2.7 Fallback Behaviour

If all 3 attempts fail:
1. `notification_log.status` is set to `failed`
2. A new in-app notification is created for every `super_admin` user informing them of the delivery failure
3. The failure is also written to the audit log as `action: notification.email.failed`
4. No further automatic retries occur for this log entry

---

## 3. SMS Channel — API Integration

### 3.1 Endpoint

```
POST https://rpcapplication.aiims.edu/services/api/v1/sms/single
```

Stored in `system_config.sms_api_url`. Token in `system_config.sms_api_token`.

### 3.2 Request Structure

```http
POST /services/api/v1/sms/single HTTP/1.1
Host: rpcapplication.aiims.edu
Authorization: Bearer <sms_api_token>
Content-Type: application/json
Accept: application/json
```

```json
{
  "to": "+911234567890",
  "message": "Your form \"Patient Survey\" has received 100 responses.",
  "metadata": {
    "notification_log_id": "64f2c3d1a2b3c4d5e6f70003",
    "event_type": "response.submitted",
    "org_id": "64f2c3d1a2b3c4d5e6f70002"
  }
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `to` | string | Yes | Recipient phone number in E.164 format (`+91XXXXXXXXXX`) |
| `message` | string | Yes | SMS body text (rendered from template, max 160 chars for single SMS, up to 480 for multi-part) |
| `metadata` | object | No | Opaque metadata for tracing |

> **Phone number format**: Always use E.164 format. Pull from `users.phone`. If the user's phone is not verified (`users.phone_verified = false`) or not set, skip SMS delivery for that recipient and log a warning.

> **Message length**: The SMS template renderer must produce a message ≤ 160 characters for guaranteed single-segment delivery. If the rendered message exceeds 160 characters, it is sent as-is (the AIIMS gateway handles concatenation). Keep templates concise.

### 3.3 Success Response

```json
{
  "status": "sent",
  "sms_id": "aiims-sms-xyz789"
}
```

HTTP `200` or `202`. Store `sms_id` in `notification_log.provider_response`.

### 3.4 Error Response and Fallback

Same pattern as email: `4xx`/`5xx` → retry up to 3 times → mark `failed` → notify `super_admin` in-app. Additionally, if the error code from the provider is `INVALID_NUMBER`, do not retry (non-retriable error) — mark `failed` immediately.

### 3.5 Non-Retriable SMS Error Codes

| Provider Code | Meaning | Action |
|---------------|---------|--------|
| `INVALID_NUMBER` | Phone number is malformed | Mark `failed` immediately, no retry |
| `BLACKLISTED` | Number on DND registry | Mark `failed` immediately, no retry |
| `DUPLICATE_MESSAGE` | Exact duplicate sent too recently | Mark `failed` immediately, no retry |

For all other errors (network, `5xx`, timeouts), the standard 3-attempt retry applies.

---

## 4. Push Notification Channel

### 4.1 Device Token Registration

When a user installs the Flutter app and grants notification permission, the device token is registered with the backend.

#### Registration Endpoint

```
POST /api/internal/v1/notifications/device-token
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "token": "fcm_or_apns_or_web_push_token_string",
  "platform": "android"
}
```

**`platform` enum values**: `android`, `ios`, `web`

The backend stores this in `users.device_tokens`:

```json
{
  "token": "fcm_token_string",
  "platform": "android",
  "created_at": "2025-01-01T00:00:00Z"
}
```

- If the token already exists for the user, it is not duplicated (upsert by token value).
- A single user may have multiple device tokens (multiple devices / platforms).
- Stale tokens (returning `registration_not_found` from FCM/APNs) are removed automatically when push delivery fails with that specific error.

#### Token Deregistration Endpoint

```
DELETE /api/internal/v1/notifications/device-token
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "token": "fcm_or_apns_or_web_push_token_string"
}
```

Called by the Flutter app on logout or when the user disables push notifications in the app settings.

---

### 4.2 Android — FCM (Firebase Cloud Messaging)

**Library**: `google-auth` + `requests` (using the FCM v1 HTTP API via OAuth2 service account)

**Endpoint**: `POST https://fcm.googleapis.com/v1/projects/{FCM_PROJECT_ID}/messages:send`

**Auth**: OAuth2 Bearer token generated from the Firebase service account JSON key (stored in `.env` as `FCM_SERVICE_ACCOUNT_JSON`).

**Request payload**:

```json
{
  "message": {
    "token": "device_fcm_token",
    "notification": {
      "title": "New form response received",
      "body": "\"Patient Survey\" has a new response."
    },
    "data": {
      "event_type": "response.submitted",
      "entity_id": "64f2c3d1a2b3c4d5e6f70010",
      "notification_id": "64f2c3d1a2b3c4d5e6f70011",
      "click_action": "OPEN_FORM_RESPONSES"
    },
    "android": {
      "priority": "high",
      "notification": {
        "channel_id": "form_builder_default",
        "click_action": "FLUTTER_NOTIFICATION_CLICK"
      }
    }
  }
}
```

- `data` fields are always strings (FCM requirement).
- The Flutter app reads `event_type` and `entity_id` from `data` to navigate on tap.
- Android notification channel ID `form_builder_default` is registered in the Flutter app with default importance.

---

### 4.3 iOS — APNs (Apple Push Notification service)

**Library**: `httpx` with HTTP/2 support (APNs requires HTTP/2). Use the `apns2` or `aioapns` Python library.

**Endpoint**: 
- Production: `https://api.push.apple.com/3/device/{device_token}`
- Sandbox: `https://api.sandbox.push.apple.com/3/device/{device_token}`

**Auth**: JWT signed with the APNs auth key (`.p8` file), stored as `APNS_AUTH_KEY` in `.env`.

**Required `.env` variables for APNs:**

```
APNS_AUTH_KEY=/run/secrets/apns_auth_key.p8
APNS_KEY_ID=XXXXXXXXXX
APNS_TEAM_ID=YYYYYYYYYY
APNS_BUNDLE_ID=edu.aiims.formbuilder
APNS_USE_SANDBOX=false
```

**Request headers**:

```
:method: POST
:path: /3/device/{device_token}
:scheme: https
authorization: bearer <jwt>
apns-topic: edu.aiims.formbuilder
apns-push-type: alert
apns-priority: 10
apns-expiration: 0
```

**Request body**:

```json
{
  "aps": {
    "alert": {
      "title": "New form response received",
      "body": "\"Patient Survey\" has a new response."
    },
    "badge": 1,
    "sound": "default",
    "mutable-content": 1
  },
  "event_type": "response.submitted",
  "entity_id": "64f2c3d1a2b3c4d5e6f70010",
  "notification_id": "64f2c3d1a2b3c4d5e6f70011"
}
```

---

### 4.4 Web — Web Push

**Library**: `pywebpush`

**VAPID keys**: Generated once and stored as `VAPID_PRIVATE_KEY` and `VAPID_PUBLIC_KEY` in `.env`. The Flutter web app fetches the public key from:

```
GET /api/internal/v1/notifications/vapid-public-key
```

The browser's `ServiceWorkerRegistration.pushManager.subscribe()` call uses this key to create a push subscription object, which is then POSTed to the device token registration endpoint with `"platform": "web"` and `"token": <serialized subscription JSON>`.

**Sending**:

```python
from pywebpush import webpush, WebPushException

webpush(
    subscription_info=json.loads(device_token),  # the token IS the subscription JSON
    data=json.dumps({
        "title": "New form response received",
        "body": "\"Patient Survey\" has a new response.",
        "icon": "/icons/icon-192.png",
        "badge": "/icons/badge-72.png",
        "data": {
            "event_type": "response.submitted",
            "entity_id": "64f2c3d1a2b3c4d5e6f70010",
            "notification_id": "64f2c3d1a2b3c4d5e6f70011",
            "url": "/forms/64f2c3d1a2b3c4d5e6f70010/responses"
        }
    }),
    vapid_private_key=settings.VAPID_PRIVATE_KEY,
    vapid_claims={"sub": "mailto:admin@aiims.edu"},
)
```

---

### 4.5 Push Delivery Logic

For each recipient, iterate over `users.device_tokens`:

```python
for device_token_entry in user["device_tokens"]:
    platform = device_token_entry["platform"]
    token = device_token_entry["token"]
    if platform == "android":
        send_fcm(token, title, body, data)
    elif platform == "ios":
        send_apns(token, title, body, data)
    elif platform == "web":
        send_web_push(token, title, body, data)
```

Each send is attempted independently. Failure on one device does not block delivery to other devices.

---

## 5. In-App Notification Channel

### 5.1 Architecture

In-app notifications use two mechanisms together:

1. **Persistence**: The notification is always written to the `notification_log` collection with `channel: "in_app"` and `status: "sent"` once the socket emit completes (or unconditionally — the DB record is the source of truth for the notification centre).
2. **Real-time delivery**: Flask-SocketIO emits an event to the recipient's active socket session immediately after the DB record is created.

### 5.2 Socket Event

**Event name emitted from server**: `notification.new`

**Payload**:

```json
{
  "notification_id": "64f2c3d1a2b3c4d5e6f70020",
  "event_type": "response.submitted",
  "title": "New form response",
  "body": "\"Patient Survey\" has received a new response from John Doe.",
  "action_url": "/forms/64f2c3d1a2b3c4d5e6f70010/responses",
  "is_read": false,
  "created_at": "2025-01-15T10:30:00Z",
  "metadata": {
    "form_id": "64f2c3d1a2b3c4d5e6f70010",
    "response_id": "64f2c3d1a2b3c4d5e6f70025"
  }
}
```

**Room naming convention**: Each authenticated user joins a Socket.IO room named `user:{user_id}` on connection. In-app notifications are emitted to this room:

```python
# In notification_engine.py
from app.extensions import socketio

socketio.emit(
    "notification.new",
    payload,
    room=f"user:{recipient_id}",
    namespace="/notifications"
)
```

If the user is not online (room is empty), the emit is a no-op — the notification will be fetched via REST when the user opens the app.

### 5.3 Notification Log Structure (in_app)

The `notification_log` collection document for an in-app notification:

```json
{
  "_id": "64f2c3d1a2b3c4d5e6f70020",
  "rule_id": "64f2c3d1a2b3c4d5e6f70030",
  "org_id": "64f2c3d1a2b3c4d5e6f70002",
  "event_type": "response.submitted",
  "recipient_id": "64f2c3d1a2b3c4d5e6f70040",
  "channel": "in_app",
  "status": "sent",
  "attempt_count": 1,
  "max_attempts": 1,
  "next_retry_at": null,
  "provider_response": null,
  "title": "New form response",
  "body": "\"Patient Survey\" has received a new response from John Doe.",
  "action_url": "/forms/64f2c3d1a2b3c4d5e6f70010/responses",
  "is_read": false,
  "read_at": null,
  "metadata": {
    "form_id": "64f2c3d1a2b3c4d5e6f70010",
    "response_id": "64f2c3d1a2b3c4d5e6f70025"
  },
  "created_at": "2025-01-15T10:30:00Z",
  "last_attempt_at": "2025-01-15T10:30:00Z"
}
```

> **Note**: `notification_log` includes `title`, `body`, `action_url`, `is_read`, `read_at`, and `metadata` fields for in-app channel documents only. These are additional fields not present in email/SMS log entries.

### 5.4 Bell Icon and Notification Centre

#### Unread Count Endpoint

```
GET /api/internal/v1/notifications/unread-count
Authorization: Bearer <access_token>
```

Response:

```json
{
  "unread_count": 7
}
```

Implementation: `db.notification_log.count_documents({"recipient_id": user_id, "channel": "in_app", "is_read": false})`

The Flutter app polls this endpoint every 60 seconds when the app is in foreground and also receives real-time updates via the `notification.count_updated` socket event.

#### Notification Centre List Endpoint

```
GET /api/internal/v1/notifications?page=1&limit=20&filter=unread
Authorization: Bearer <access_token>
```

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-indexed) |
| `limit` | integer | 20 | Items per page (max 100) |
| `filter` | string | `all` | `all`, `unread`, `read` |

Response:

```json
{
  "notifications": [
    {
      "notification_id": "64f2c3d1a2b3c4d5e6f70020",
      "event_type": "response.submitted",
      "title": "New form response",
      "body": "\"Patient Survey\" has received a new response.",
      "action_url": "/forms/64f2c3d1a2b3c4d5e6f70010/responses",
      "is_read": false,
      "created_at": "2025-01-15T10:30:00Z",
      "metadata": {}
    }
  ],
  "total": 42,
  "page": 1,
  "limit": 20,
  "unread_count": 7
}
```

---

## 6. Webhook Channel

### 6.1 Webhook Config Schema

Webhook configurations live in two places:
1. **Form-level webhooks**: Embedded in `form_commits.schema.webhook_configs` (per-form, managed by form owner)
2. **Global org-level webhooks**: In the `webhook_configs` collection (managed by org_admin)

**`webhook_configs` collection document:**

```json
{
  "_id": "64f2c3d1a2b3c4d5e6f70050",
  "org_id": "64f2c3d1a2b3c4d5e6f70002",
  "form_id": null,
  "project_id": null,
  "name": "Slack Alerts",
  "url": "https://hooks.slack.com/services/T00000000/B00000000/XXXX",
  "secret": "wh_secret_abc123",
  "events": ["response.submitted", "form.published"],
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z",
  "created_by": "64f2c3d1a2b3c4d5e6f70040",
  "org_id": "64f2c3d1a2b3c4d5e6f70002",
  "is_deleted": false,
  "deleted_at": null
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `url` | string | HTTPS URL of the webhook endpoint (must start with `https://`) |
| `secret` | string | HMAC signing secret (stored in plaintext in DB, treated as sensitive — never returned in API responses) |
| `events` | array[string] | List of event types this webhook subscribes to (see §13 for full list) |
| `is_active` | boolean | When false, webhook is skipped even if matching event fires |
| `form_id` | ObjectId \| null | If set, webhook only fires for this specific form's events |
| `project_id` | ObjectId \| null | If set, webhook fires for all forms in this project |

### 6.2 HMAC Signature Computation

Every webhook delivery includes a signature header for the receiver to verify authenticity.

**Algorithm**: HMAC-SHA256 over the raw request body bytes.

**Header name**: `X-FormBuilder-Signature`

**Format**: `sha256=<hex_digest>`

**Python implementation:**

```python
import hmac
import hashlib

def compute_webhook_signature(secret: str, payload_bytes: bytes) -> str:
    """
    Compute HMAC-SHA256 signature for webhook payload.
    
    Args:
        secret: The webhook config's secret string
        payload_bytes: Raw JSON bytes of the request body (before any decoding)
    
    Returns:
        Signature string in format 'sha256=<hex_digest>'
    """
    mac = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload_bytes,
        digestmod=hashlib.sha256
    )
    return f"sha256={mac.hexdigest()}"
```

**Receiver verification (documentation for webhook consumers):**

```python
import hmac
import hashlib

def verify_signature(secret: str, payload_bytes: bytes, signature_header: str) -> bool:
    expected = compute_webhook_signature(secret, payload_bytes)
    return hmac.compare_digest(expected, signature_header)
```

> **Security note**: Always use `hmac.compare_digest` (constant-time comparison) to prevent timing attacks.

### 6.3 Webhook Delivery HTTP Request

```http
POST <webhook_url> HTTP/1.1
Content-Type: application/json
X-FormBuilder-Signature: sha256=<hex_digest>
X-FormBuilder-Event: response.submitted
X-FormBuilder-Delivery: 64f2c3d1a2b3c4d5e6f70060
X-FormBuilder-Timestamp: 2025-01-15T10:30:00Z
User-Agent: FormBuilderWebhook/1.0
```

```json
{
  "id": "64f2c3d1a2b3c4d5e6f70060",
  "event_type": "response.submitted",
  "timestamp": "2025-01-15T10:30:00Z",
  "org_id": "64f2c3d1a2b3c4d5e6f70002",
  "data": {
    "response_id": "64f2c3d1a2b3c4d5e6f70025",
    "form_id": "64f2c3d1a2b3c4d5e6f70010",
    "form_name": "Patient Survey",
    "commit_id": "a1b2c3d4e5f6",
    "submission_number": 42,
    "respondent_id": "64f2c3d1a2b3c4d5e6f70040",
    "is_anonymous": false,
    "submitted_at": "2025-01-15T10:29:58Z"
  }
}
```

**Header descriptions:**

| Header | Description |
|--------|-------------|
| `X-FormBuilder-Signature` | HMAC-SHA256 of the raw JSON body bytes |
| `X-FormBuilder-Event` | The event type string |
| `X-FormBuilder-Delivery` | The `webhook_delivery_log._id` (for idempotency) |
| `X-FormBuilder-Timestamp` | ISO8601 timestamp of when the event occurred |

### 6.4 Webhook Payload Format Per Event Type

See §13 for the complete list. Each event's payload `data` field contains event-specific fields. The envelope (`id`, `event_type`, `timestamp`, `org_id`) is always present.

### 6.5 Webhook Delivery Log Schema

```json
{
  "_id": "64f2c3d1a2b3c4d5e6f70060",
  "webhook_config_id": "64f2c3d1a2b3c4d5e6f70050",
  "org_id": "64f2c3d1a2b3c4d5e6f70002",
  "event_type": "response.submitted",
  "payload": { ... },
  "status": "delivered",
  "http_status_code": 200,
  "response_body": "OK",
  "attempt_count": 1,
  "next_retry_at": null,
  "delivered_at": "2025-01-15T10:30:01Z",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**`status` enum values:**

| Status | Description |
|--------|-------------|
| `queued` | Task created, not yet sent |
| `delivered` | HTTP call succeeded (2xx response received) |
| `failed` | All retry attempts exhausted |
| `retrying` | Failed at least once, scheduled for retry |

### 6.6 Webhook Retry Policy

Identical to the email/SMS retry policy:
- Attempt 1: immediate
- Attempt 2: 1 minute after failure
- Attempt 3: 5 minutes after attempt 2
- After attempt 3 fails: mark `failed`, fire a `webhook.failed` notification event (which can itself trigger in-app or email alerts)

**Success criteria**: HTTP status `2xx` within the read timeout (30 seconds). Any other status, timeout, or connection error counts as failure.

**Non-retriable conditions**: None for webhooks — always attempt all 3 times unless the URL is unreachable (DNS failure), in which case all 3 retries still execute.

### 6.7 Webhook Test Endpoint

Form owners and org_admins can trigger a test delivery to verify their webhook endpoint is working.

```
POST /api/internal/v1/webhooks/{webhook_config_id}/test
Authorization: Bearer <access_token>
Content-Type: application/json
```

Request body: empty `{}` — uses a synthetic test payload.

**Test payload sent to the webhook URL:**

```json
{
  "id": "test-delivery-00000000",
  "event_type": "webhook.test",
  "timestamp": "2025-01-15T10:30:00Z",
  "org_id": "64f2c3d1a2b3c4d5e6f70002",
  "data": {
    "message": "This is a test webhook delivery from Form Builder Platform.",
    "webhook_config_id": "64f2c3d1a2b3c4d5e6f70050",
    "webhook_name": "Slack Alerts"
  }
}
```

The test delivery is NOT retried — it is a single synchronous (or near-synchronous Celery) attempt. A `webhook_delivery_log` record is created with `event_type: "webhook.test"`.

**Response on success:**

```json
{
  "status": "delivered",
  "http_status_code": 200,
  "response_body": "OK",
  "delivery_log_id": "64f2c3d1a2b3c4d5e6f70065"
}
```

**Response on failure:**

```json
{
  "status": "failed",
  "http_status_code": 404,
  "response_body": "Not Found",
  "delivery_log_id": "64f2c3d1a2b3c4d5e6f70065"
}
```

---

## 7. Notification Template System

### 7.1 Template Storage

Templates are stored in the `notification_templates` collection. Two tiers:

1. **System templates** (`org_id: null`, `is_system: true`): Provided by the platform. Cannot be deleted. Org-admins may not modify them directly but can create org-level overrides.
2. **Org-level templates** (`org_id: <org_id>`, `is_system: false`): Created by org_admin. Override system templates for the same `event_type` when rendering notifications for that org.

### 7.2 Template Structure

```json
{
  "_id": "64f2c3d1a2b3c4d5e6f70070",
  "org_id": null,
  "name": "Response Submitted — Default",
  "event_type": "response.submitted",
  "channels": {
    "email": {
      "subject": "New response received for {{form_name}}",
      "body_html": "<html><body><p>Dear {{user_name}},</p><p>A new response has been submitted to <strong>{{form_name}}</strong>.</p><p><a href=\"{{action_url}}\">View Response</a></p></body></html>",
      "body_text": "Dear {{user_name}},\n\nA new response has been submitted to {{form_name}}.\n\nView Response: {{action_url}}"
    },
    "sms": {
      "message": "New response to {{form_name}}. Total: {{response_count}}. {{action_url}}"
    },
    "in_app": {
      "title": "New response to {{form_name}}",
      "body": "{{actor_name}} submitted a response to {{form_name}}."
    }
  },
  "variables": [
    { "key": "form_name", "description": "Name of the form", "example": "Patient Survey" },
    { "key": "user_name", "description": "Recipient's full name", "example": "Dr. Smith" },
    { "key": "response_count", "description": "Total response count for the form", "example": "42" },
    { "key": "action_url", "description": "Deep link URL for the notification action", "example": "https://platform.aiims.edu/forms/abc/responses" }
  ],
  "is_system": true,
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z",
  "created_by": null
}
```

### 7.3 Template Variable List

All templates have access to the following standard variables. Event-specific variables are documented in §13.

| Variable | Type | Source | Description |
|----------|------|--------|-------------|
| `{{user_name}}` | string | `users.full_name` of recipient | Recipient's full name |
| `{{user_email}}` | string | `users.email` of recipient | Recipient's email address |
| `{{org_name}}` | string | `organisations.name` | Organisation display name |
| `{{project_name}}` | string | `projects.name` | Project display name (empty string if not applicable) |
| `{{form_name}}` | string | `forms.name` | Form display name (empty string if not applicable) |
| `{{response_count}}` | integer | Counted from `form_responses` | Total submitted response count for the form |
| `{{action_url}}` | string | Constructed by `notification_engine` | Deep link URL relevant to the event |
| `{{timestamp}}` | string | Event timestamp | ISO8601 formatted event time (e.g., `2025-01-15 10:30 UTC`) |
| `{{actor_name}}` | string | `users.full_name` of actor | Name of the user who triggered the event |
| `{{entity_type}}` | string | Event payload | Type of entity involved (`form`, `response`, `analysis`, etc.) |
| `{{entity_name}}` | string | Event payload | Name of the entity involved |
| `{{platform_name}}` | string | `system_config.platform_name` | Platform display name |

### 7.4 Jinja2-Style Template Rendering

The template engine uses Python's `jinja2` library for rendering. Templates use `{{variable}}` syntax (double curly braces), consistent with Jinja2 defaults.

```python
from jinja2 import Environment, BaseLoader, select_autoescape

_env = Environment(
    loader=BaseLoader(),
    autoescape=select_autoescape(["html"]),  # autoescaping for html templates only
    undefined=jinja2.Undefined,  # undefined variables render as empty string
)

def render_template(template_str: str, context: dict) -> str:
    """Render a Jinja2 template string with the given context."""
    tmpl = _env.from_string(template_str)
    return tmpl.render(**context)
```

> **Autoescaping**: HTML body templates have autoescaping enabled. SMS and in-app `message`/`body` templates have autoescaping **disabled** (plain text). Subject lines have autoescaping disabled.

> **Undefined variables**: Jinja2 is configured with `Undefined` (silent) — missing variables render as empty string, not an error. This prevents template rendering from crashing if a variable is not applicable for a specific event.

### 7.5 Template Lookup Order (Custom Templates Per Org)

When rendering a notification for event `E` in org `O`:

1. Query `notification_templates` where `event_type = E AND org_id = O AND is_active = true`
2. If found → use org-level template
3. If not found → query `notification_templates` where `event_type = E AND org_id = null AND is_active = true`
4. If not found → use hardcoded fallback template (a plain text message)

```python
def get_template(event_type: str, org_id: str) -> dict:
    """Fetch the most specific active template for the given event and org."""
    # Try org-specific template first
    template = db.notification_templates.find_one({
        "event_type": event_type,
        "org_id": ObjectId(org_id),
        "is_active": True
    })
    if template:
        return template
    # Fall back to system template
    template = db.notification_templates.find_one({
        "event_type": event_type,
        "org_id": None,
        "is_active": True
    })
    return template
```

---

## 8. Notification Rules

### 8.1 Notification Rule Document Structure

```json
{
  "_id": "64f2c3d1a2b3c4d5e6f70080",
  "org_id": "64f2c3d1a2b3c4d5e6f70002",
  "project_id": null,
  "form_id": "64f2c3d1a2b3c4d5e6f70010",
  "name": "Alert on 100 responses",
  "event_type": "response.submitted",
  "trigger_conditions": [
    {
      "type": "answer",
      "field_id": "response_count",
      "operator": "equals",
      "value": 100
    }
  ],
  "channels": ["email", "in_app"],
  "recipient_type": "form_owner",
  "recipient_ids": [],
  "template_id": "64f2c3d1a2b3c4d5e6f70070",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z",
  "created_by": "64f2c3d1a2b3c4d5e6f70040",
  "org_id": "64f2c3d1a2b3c4d5e6f70002",
  "is_deleted": false,
  "deleted_at": null
}
```

### 8.2 Trigger Condition Types

The `trigger_conditions` array uses the same `Condition` union type as form visibility rules (see `CONTEXT.md §5.5`). For notifications, the following condition types are applicable:

| Condition Type | `type` Value | Key Fields | Description |
|----------------|-------------|------------|-------------|
| Answer condition | `"answer"` | `field_id`, `operator`, `value` | Checks a value in the event payload (e.g., `response_count = 100`) |
| Role condition | `"role"` | `roles: [String]` | Fires only if the actor has one of the specified roles |
| Always fire | `"always_visible"` | — | No conditions — fire on every matching event |

> **Important**: For notification rules, `field_id` in the `answer` condition refers to a field in the **event payload** (not a form question ID). Available fields per event type are documented in §13.

**`operator` enum values**: `equals`, `not_equals`, `contains`, `greater_than`, `less_than`, `in`, `not_in`, `is_empty`, `is_not_empty`

### 8.3 Recipient Resolution

| `recipient_type` | Resolution Logic |
|------------------|-----------------|
| `form_owner` | The `created_by` user of the form document |
| `specific_users` | Use `recipient_ids` list of user ObjectIds directly |
| `role` | All users in the org with the role stored in `recipient_ids[0]` (e.g., `"org_admin"`) |
| `group` | All members of the group with ID in `recipient_ids[0]` |
| `respondent` | The user who submitted the response (from `form_responses.respondent_id`) — only valid for `response.submitted` and `response.edited` events |

### 8.4 Rule Scoping

Rules are evaluated for a given event based on their scope:

| Rule Field | Scope |
|------------|-------|
| `form_id` set | Rule applies only to events for that specific form |
| `project_id` set, `form_id` null | Rule applies to events for all forms in that project |
| Both null, `org_id` set | Rule applies to all events of that `event_type` across the org |

---

## 9. Custom Notification Rules for Forms

### 9.1 Form Owner Rule Configuration UI

Form owners (users with `project_owner` or `project_editor` role, or the `created_by` user of the form) can configure custom notification rules for their form through the Form Settings panel in the Flutter app.

**Rules management endpoint:**

```
GET    /api/internal/v1/forms/{form_id}/notification-rules
POST   /api/internal/v1/forms/{form_id}/notification-rules
PUT    /api/internal/v1/forms/{form_id}/notification-rules/{rule_id}
DELETE /api/internal/v1/forms/{form_id}/notification-rules/{rule_id}
```

### 9.2 Example: Alert When response_count Equals 100

```json
POST /api/internal/v1/forms/64f2c3d1a2b3c4d5e6f70010/notification-rules

{
  "name": "Milestone: 100 responses",
  "event_type": "response.submitted",
  "trigger_conditions": [
    {
      "type": "answer",
      "field_id": "response_count",
      "operator": "equals",
      "value": 100
    }
  ],
  "channels": ["email", "in_app"],
  "recipient_type": "form_owner",
  "recipient_ids": [],
  "template_id": null
}
```

When `template_id` is null, the system uses the default system template for the `event_type`.

### 9.3 Example: Alert When Specific Answer Has a Specific Value

This rule fires when a response is submitted where question `q_001` (a radio group) has value `"critical"`.

```json
POST /api/internal/v1/forms/64f2c3d1a2b3c4d5e6f70010/notification-rules

{
  "name": "Critical triage alert",
  "event_type": "response.submitted",
  "trigger_conditions": [
    {
      "type": "answer",
      "field_id": "answers.q_001.value",
      "operator": "equals",
      "value": "critical"
    }
  ],
  "channels": ["email", "sms", "in_app"],
  "recipient_type": "specific_users",
  "recipient_ids": ["64f2c3d1a2b3c4d5e6f70040", "64f2c3d1a2b3c4d5e6f70041"],
  "template_id": "64f2c3d1a2b3c4d5e6f70075"
}
```

For answer-specific conditions, `field_id` uses dot-notation path into the event payload. For `response.submitted`, the full response document is available in the payload, so `answers.q_001.value` traverses `payload.data.answers["q_001"]["value"]`.

### 9.4 Condition Evaluation for Custom Rules

The notification engine evaluates `trigger_conditions` using the same logic as form visibility rules (AND/OR operators). When no `operator` wrapping is specified at the rule level, conditions are evaluated as AND (all must pass).

For the full evaluation algorithm, see §10.

---

## 10. Rule Evaluation Algorithm

### 10.1 Trigger

After every event-producing action (form response submitted, analysis run completed, etc.), the relevant service calls:

```python
notification_engine.fire_event(
    event_type="response.submitted",
    org_id="64f2c3d1a2b3c4d5e6f70002",
    payload={
        "response_id": "...",
        "form_id": "...",
        "form_name": "Patient Survey",
        "response_count": 100,
        "answers": { ... },
        ...
    }
)
```

`fire_event()` does NOT evaluate rules synchronously. It enqueues a Celery task:

```python
from app.workers.notification_tasks import evaluate_notification_rules

evaluate_notification_rules.apply_async(
    args=[event_type, org_id, payload],
    queue="notifications",
    priority=5
)
```

### 10.2 Celery Task: `evaluate_notification_rules`

**File**: `backend/app/workers/notification_tasks.py`

**Full algorithm:**

```
1. Fetch all active notification rules matching the event:
   - notification_rules WHERE:
     - event_type = <event_type>
     - is_active = true
     - is_deleted = false
     - org_id = <org_id>
     - (form_id is null OR form_id = payload["form_id"])
     - (project_id is null OR project_id = payload["project_id"])

2. For each rule:
   a. Evaluate trigger_conditions:
      - If conditions list is empty → always matches
      - Else: evaluate each Condition against the event payload
        - "answer" condition: resolve field_id as dot-notation path into payload
          and compare value using operator
        - "role" condition: check actor's role in the event context
        - "always_visible" condition: always True
      - AND all condition results together (default operator)
   b. If conditions DO NOT match → skip this rule
   c. If conditions match:
      - Resolve recipients (see §8.3)
      - For each recipient:
        - Check recipient's notification_preferences for each channel
        - For each allowed channel in rule.channels:
          - Create notification_log document with status="queued"
          - Enqueue channel-specific delivery task

3. Return number of rules evaluated and notifications queued
```

### 10.3 Condition Evaluation: `evaluate_condition(condition, payload)`

```python
def evaluate_condition(condition: dict, payload: dict) -> bool:
    ctype = condition["type"]
    
    if ctype == "always_visible":
        return True
    
    if ctype == "answer":
        field_value = get_nested(payload, condition["field_id"])  # dot-notation resolver
        return compare(field_value, condition["operator"], condition["value"])
    
    if ctype == "role":
        actor_role = payload.get("actor_role")
        return actor_role in condition["roles"]
    
    return False

def get_nested(obj: dict, path: str) -> Any:
    """Resolve dot-notation path in nested dict. Returns None if path missing."""
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current

def compare(value: Any, operator: str, target: Any) -> bool:
    ops = {
        "equals": lambda v, t: v == t,
        "not_equals": lambda v, t: v != t,
        "contains": lambda v, t: t in str(v) if v is not None else False,
        "greater_than": lambda v, t: v > t if v is not None else False,
        "less_than": lambda v, t: v < t if v is not None else False,
        "in": lambda v, t: v in t if isinstance(t, list) else False,
        "not_in": lambda v, t: v not in t if isinstance(t, list) else True,
        "is_empty": lambda v, t: v is None or v == "" or v == [],
        "is_not_empty": lambda v, t: v is not None and v != "" and v != [],
    }
    fn = ops.get(operator)
    return fn(value, target) if fn else False
```

---

## 11. Celery Task Architecture

### 11.1 Task File

**Location**: `backend/app/workers/notification_tasks.py`

### 11.2 Task Definitions

| Task Name | Queue | Priority | Description |
|-----------|-------|----------|-------------|
| `notifications.evaluate_rules` | `notifications` | 5 (normal) | Evaluates all matching rules and enqueues delivery tasks |
| `notifications.send_email` | `notifications` | 5 (normal) | Sends a single email via AIIMS API |
| `notifications.send_sms` | `notifications` | 5 (normal) | Sends a single SMS via AIIMS API |
| `notifications.send_push` | `notifications` | 7 (high) | Sends push notification to all user devices |
| `notifications.send_in_app` | `notifications` | 9 (critical) | Persists in-app notification + emits socket event |
| `notifications.deliver_webhook` | `webhooks` | 5 (normal) | Delivers a webhook payload to the configured URL |
| `notifications.retry_failed` | `maintenance` | 3 (low) | Periodic task that retries `retrying` status entries past their `next_retry_at` |

> **Priority values**: Higher number = higher priority in Celery. Range: 0 (lowest) to 9 (highest).

### 11.3 Celery Queue Configuration

```python
# celery_worker.py
from kombu import Queue

CELERY_TASK_QUEUES = [
    Queue("notifications", routing_key="notifications"),
    Queue("webhooks", routing_key="webhooks"),
    Queue("analysis", routing_key="analysis"),
    Queue("export", routing_key="export"),
    Queue("maintenance", routing_key="maintenance"),
]

CELERY_TASK_DEFAULT_QUEUE = "default"
```

Workers can be started with queue affinity:

```bash
# Notification-focused worker
celery -A celery_worker worker --queues notifications,webhooks --concurrency 4

# Analysis-focused worker
celery -A celery_worker worker --queues analysis,export --concurrency 2
```

### 11.4 Task Implementation Pattern

All notification tasks must be idempotent — running them twice should not double-deliver. The `notification_log._id` is passed as a task argument and used for deduplication:

```python
@celery_app.task(
    name="notifications.send_email",
    bind=True,
    max_retries=0,  # retry logic is handled manually via next_retry_at
    queue="notifications",
    acks_late=True,
    reject_on_worker_lost=True,
)
def send_email_task(self, notification_log_id: str) -> dict:
    """
    Send email for a single notification_log entry.
    Idempotent: checks log status before sending.
    """
    log = db.notification_log.find_one({"_id": ObjectId(notification_log_id)})
    if not log:
        return {"status": "not_found"}
    if log["status"] == "sent":
        return {"status": "already_sent"}  # idempotency guard
    
    # ... build and send email
    # ... update notification_log on success/failure
```

---

## 12. Retry Policy

### 12.1 Policy Details

| Attempt | Delay Before This Attempt | Condition |
|---------|--------------------------|-----------|
| 1 | Immediate (< 5 seconds after event) | Always |
| 2 | 1 minute after attempt 1 failure | Only if attempt 1 failed |
| 3 | 5 minutes after attempt 2 failure | Only if attempt 2 failed |
| Post-failure | No more retries | `status` → `"failed"` |

The total backoff schedule: **1 min → 5 min → mark failed** (cumulative: attempt 1 immediate, attempt 2 at T+1min, attempt 3 at T+6min).

### 12.2 Retry Implementation

Retries are NOT implemented via Celery's built-in `self.retry()`. Instead, the retry is implemented via a periodic Celery Beat task that polls `notification_log` for entries where:

```python
{
    "status": "retrying",
    "next_retry_at": { "$lte": datetime.utcnow() },
    "attempt_count": { "$lt": 3 }
}
```

This approach:
- Survives worker restarts (state is in MongoDB, not in memory)
- Allows monitoring of pending retries via DB query
- Enables super_admin to manually trigger a retry via admin panel

**Setting retry schedule on failure:**

```python
def schedule_retry(log_id: str, attempt_count: int):
    backoff_minutes = [1, 5]  # attempt 2 = 1min, attempt 3 = 5min
    if attempt_count >= 3:
        # No more retries
        db.notification_log.update_one(
            {"_id": ObjectId(log_id)},
            {"$set": {"status": "failed"}}
        )
        notify_super_admin_of_failure(log_id)
    else:
        delay = backoff_minutes[attempt_count - 1]
        next_retry = datetime.utcnow() + timedelta(minutes=delay)
        db.notification_log.update_one(
            {"_id": ObjectId(log_id)},
            {"$set": {
                "status": "retrying",
                "next_retry_at": next_retry,
                "attempt_count": attempt_count
            }}
        )
```

### 12.3 After 3 Failures

When all 3 attempts are exhausted:

1. `notification_log.status` → `"failed"`
2. `notification_log.next_retry_at` → `null`
3. An in-app notification is sent to all `super_admin` users (using the in-app channel, which does not use the retry mechanism itself):
   - Title: `"Notification delivery failed"`
   - Body: `"Failed to deliver {channel} notification for event {event_type} to {recipient_email} after 3 attempts. Log ID: {log_id}"`
4. An `audit_log` entry is written with `action: "notification.delivery.failed"`.

---

## 13. Notification Event Taxonomy

### 13.1 Complete Event List with Payload Schemas

---

#### `response.submitted`

Fired when a form response is submitted (not draft save).

```json
{
  "event_type": "response.submitted",
  "org_id": "...",
  "project_id": "...",
  "form_id": "...",
  "form_name": "Patient Survey",
  "response_id": "...",
  "commit_id": "a1b2c3d4",
  "submission_number": 42,
  "response_count": 42,
  "respondent_id": "...",
  "respondent_name": "John Doe",
  "respondent_email": "john@example.com",
  "is_anonymous": false,
  "submitted_at": "2025-01-15T10:30:00Z",
  "answers": {
    "q_001": { "value": "critical", "display_value": "Critical" },
    "q_002": { "value": 38.5, "display_value": "38.5" }
  },
  "actor_role": "org_viewer",
  "actor_name": "John Doe"
}
```

---

#### `response.edited`

Fired when a submitted response is edited by the respondent or an authorized user.

```json
{
  "event_type": "response.edited",
  "org_id": "...",
  "form_id": "...",
  "form_name": "Patient Survey",
  "response_id": "...",
  "edited_by_id": "...",
  "edited_by_name": "Dr. Smith",
  "edited_at": "2025-01-15T11:00:00Z",
  "changed_fields": ["q_001", "q_003"],
  "actor_name": "Dr. Smith",
  "actor_role": "org_editor"
}
```

---

#### `form.published`

Fired when a form is published (production branch updated).

```json
{
  "event_type": "form.published",
  "org_id": "...",
  "project_id": "...",
  "form_id": "...",
  "form_name": "Patient Survey",
  "commit_id": "a1b2c3d4",
  "branch": "main",
  "published_by_id": "...",
  "published_by_name": "Dr. Smith",
  "published_at": "2025-01-15T09:00:00Z",
  "actor_name": "Dr. Smith",
  "actor_role": "project_editor"
}
```

---

#### `form.version_changed`

Fired when a new commit is created on any branch.

```json
{
  "event_type": "form.version_changed",
  "org_id": "...",
  "form_id": "...",
  "form_name": "Patient Survey",
  "branch": "feature/new-questions",
  "commit_id": "b2c3d4e5",
  "parent_commit_id": "a1b2c3d4",
  "commit_message": "Added age and gender questions",
  "committed_by_name": "Dr. Smith",
  "committed_at": "2025-01-15T08:00:00Z",
  "actor_name": "Dr. Smith",
  "actor_role": "org_editor"
}
```

---

#### `collaboration.conflict`

Fired when a merge conflict is detected during branch merge.

```json
{
  "event_type": "collaboration.conflict",
  "org_id": "...",
  "form_id": "...",
  "form_name": "Patient Survey",
  "branch_name": "feature/new-questions",
  "base_commit_id": "a1b2c3d4",
  "their_commit_id": "c3d4e5f6",
  "conflict_fields": ["sections.0.questions.2.label", "settings.expires_at"],
  "detected_at": "2025-01-15T09:30:00Z",
  "actor_name": "Dr. Jones",
  "actor_role": "org_editor"
}
```

---

#### `analysis.run_completed`

Fired when an analysis run finishes successfully.

```json
{
  "event_type": "analysis.run_completed",
  "org_id": "...",
  "project_id": "...",
  "analysis_id": "...",
  "analysis_name": "Monthly Patient Stats",
  "run_id": "...",
  "trigger": "scheduled",
  "started_at": "2025-01-15T00:00:00Z",
  "completed_at": "2025-01-15T00:01:30Z",
  "duration_seconds": 90,
  "node_count": 12,
  "actor_name": "Scheduler",
  "actor_role": "system"
}
```

---

#### `analysis.run_failed`

Fired when an analysis run fails (all retries exhausted or unrecoverable error).

```json
{
  "event_type": "analysis.run_failed",
  "org_id": "...",
  "analysis_id": "...",
  "analysis_name": "Monthly Patient Stats",
  "run_id": "...",
  "trigger": "on_demand",
  "failed_node_ids": ["node_005"],
  "error_summary": "Division by zero in calculate_column node",
  "failed_at": "2025-01-15T10:05:00Z",
  "actor_name": "Dr. Smith",
  "actor_role": "org_analyst"
}
```

---

#### `invite.accepted`

Fired when a user accepts an invitation to join an org or project.

```json
{
  "event_type": "invite.accepted",
  "org_id": "...",
  "project_id": null,
  "invited_email": "newuser@example.com",
  "invited_user_id": "...",
  "invited_user_name": "Dr. Patel",
  "inviter_id": "...",
  "inviter_name": "Dr. Smith",
  "role": "org_editor",
  "accepted_at": "2025-01-15T10:00:00Z",
  "actor_name": "Dr. Patel",
  "actor_role": "org_editor"
}
```

---

#### `user.approved`

Fired when a super_admin approves a pending user registration.

```json
{
  "event_type": "user.approved",
  "org_id": null,
  "user_id": "...",
  "user_name": "Dr. Patel",
  "user_email": "drpatel@aiims.edu",
  "approved_by_id": "...",
  "approved_by_name": "Admin",
  "approved_at": "2025-01-15T10:00:00Z",
  "actor_name": "Admin",
  "actor_role": "super_admin"
}
```

---

#### `user.suspended`

Fired when a super_admin or org_admin suspends a user.

```json
{
  "event_type": "user.suspended",
  "org_id": "...",
  "user_id": "...",
  "user_name": "Dr. Patel",
  "user_email": "drpatel@aiims.edu",
  "suspended_by_id": "...",
  "suspended_by_name": "Org Admin",
  "reason": "Policy violation",
  "suspended_at": "2025-01-15T10:00:00Z",
  "actor_name": "Org Admin",
  "actor_role": "org_admin"
}
```

---

#### `quota.warning_80`

Fired when an org's storage reaches 80% of quota.

```json
{
  "event_type": "quota.warning_80",
  "org_id": "...",
  "org_name": "Department of Medicine",
  "quota_bytes": 10737418240,
  "used_bytes": 8589934592,
  "percentage_used": 80.0,
  "timestamp": "2025-01-15T02:00:00Z",
  "actor_name": "System",
  "actor_role": "system"
}
```

---

#### `quota.warning_90`

Same structure as `quota.warning_80`, with `percentage_used: 90.x`.

---

#### `quota.exceeded`

Same structure as `quota.warning_80`, with `percentage_used: >= 100.0`. Additionally:

```json
{
  "file_uploads_blocked": true,
  "form_submissions_blocked": false
}
```

---

#### `plugin.installed`

Fired when an admin installs a new plugin.

```json
{
  "event_type": "plugin.installed",
  "org_id": null,
  "plugin_id": "my-custom-field",
  "plugin_name": "Custom Diagnosis Field",
  "plugin_version": "1.2.0",
  "installed_by_id": "...",
  "installed_by_name": "Super Admin",
  "installed_at": "2025-01-15T10:00:00Z",
  "actor_name": "Super Admin",
  "actor_role": "super_admin"
}
```

---

#### `plugin.error`

Fired when a plugin raises an unhandled exception during execution.

```json
{
  "event_type": "plugin.error",
  "org_id": "...",
  "plugin_id": "my-custom-field",
  "plugin_name": "Custom Diagnosis Field",
  "error_message": "TimeoutError: Handler did not respond within 30s",
  "context": { "form_id": "...", "question_id": "q_001" },
  "occurred_at": "2025-01-15T10:30:00Z",
  "actor_name": "System",
  "actor_role": "system"
}
```

---

#### `webhook.failed`

Fired when a webhook delivery exhausts all retries.

```json
{
  "event_type": "webhook.failed",
  "org_id": "...",
  "webhook_config_id": "...",
  "webhook_name": "Slack Alerts",
  "webhook_url": "https://hooks.slack.com/...",
  "failed_event_type": "response.submitted",
  "delivery_log_id": "...",
  "attempt_count": 3,
  "last_http_status": 503,
  "failed_at": "2025-01-15T10:36:00Z",
  "actor_name": "System",
  "actor_role": "system"
}
```

---

#### `scheduled_analysis.completed`

Same as `analysis.run_completed` but `trigger` is always `"scheduled"`. Used for a distinct notification rule targeting scheduled-only runs.

---

## 14. Notification Preferences

### 14.1 User Preference Storage

Each user's notification preferences are stored in `users.notification_preferences`:

```json
{
  "email": true,
  "sms": false,
  "push": true,
  "in_app": true
}
```

### 14.2 Preference Enforcement

During recipient resolution in the rule evaluation algorithm (§10.2), the notification engine checks preferences before creating a `notification_log` entry:

```python
def should_deliver(user: dict, channel: str) -> bool:
    """Return True if the user has enabled this channel in their preferences."""
    prefs = user.get("notification_preferences", {})
    return prefs.get(channel, True)  # default True if preference not set
```

If `should_deliver()` returns `False`, no `notification_log` entry is created for that recipient + channel combination. The skipped channel is logged at DEBUG level.

**Exception**: Certain system-critical notifications bypass preferences:

| Event Type | Bypasses Preferences? |
|------------|----------------------|
| `user.approved` | Yes (always in_app + email) |
| `user.suspended` | Yes (always in_app + email) |
| `quota.exceeded` | Yes (always in_app + email) |
| All other events | No (preferences respected) |

### 14.3 Preference Update Endpoint

```
PUT /api/internal/v1/me/notification-preferences
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "email": true,
  "sms": false,
  "push": true,
  "in_app": true
}
```

Response: `200 OK` with updated user document (notification_preferences field only).

---

## 15. Notification Archive

### 15.1 Retention

In-app notifications (`notification_log` with `channel: "in_app"`) are retained indefinitely unless the super_admin configures a retention policy via `system_config`. The maintenance Celery task (nightly) handles purging if configured:

```
system_config key: in_app_notification_retention_days
value: integer (days), null = retain forever (default)
```

Notifications past the retention window are hard-deleted (not soft-deleted — `is_read` status is irrelevant after retention).

Email, SMS, push channel `notification_log` entries are retained indefinitely for audit purposes and are not pruned by the maintenance task.

### 15.2 Search

```
GET /api/internal/v1/notifications?search=<query>&event_type=response.submitted
```

Search is case-insensitive substring match on `title` and `body` fields. No Elasticsearch is used for notification search — MongoDB `$regex` is sufficient given the expected volume.

### 15.3 Mark as Read

#### Mark Single Notification as Read

```
PATCH /api/internal/v1/notifications/{notification_id}/read
Authorization: Bearer <access_token>
```

No request body. Sets `is_read: true` and `read_at: <now>` on the `notification_log` entry. Returns `204 No Content`.

**Authorization**: The recipient_id of the log entry must match the authenticated user's ID. Otherwise returns `403 Forbidden`.

#### Mark All as Read

```
POST /api/internal/v1/notifications/mark-all-read
Authorization: Bearer <access_token>
```

No request body. Updates all `notification_log` entries where:
- `recipient_id = authenticated_user_id`
- `channel = "in_app"`
- `is_read = false`

Sets `is_read: true` and `read_at: <now>` on all matching documents. Returns `204 No Content`.

After marking all as read, a `notification.count_updated` socket event is emitted to the user's room with `unread_count: 0`.

### 15.4 Delete Notification

Users can delete individual in-app notifications from their notification centre:

```
DELETE /api/internal/v1/notifications/{notification_id}
Authorization: Bearer <access_token>
```

Hard-deletes the `notification_log` entry (no soft delete — these are not auditable entities from the user's perspective). Authorization: same as mark-as-read. Returns `204 No Content`.

---

*End of Notification System Documentation*
