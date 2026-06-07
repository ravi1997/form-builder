# 04 — Authentication, Authorisation & Access Control

> **Authoritative Reference**: This document derives from `CONTEXT.md` §6 (Auth System), §5.2 (Identity & Access Collections), §12 (Security Policies), and §13 (Data Policies). All implementations MUST match the schemas and rules defined here.

---

## Table of Contents

1. [Role Hierarchy](#1-role-hierarchy)
2. [JWT Structure](#2-jwt-structure)
3. [Auth Flow Diagrams](#3-auth-flow-diagrams)
4. [Refresh Token Rotation](#4-refresh-token-rotation)
5. [Multi-Org Membership](#5-multi-org-membership)
6. [Role Inheritance Rules](#6-role-inheritance-rules)
7. [ABAC Evaluation Algorithm](#7-abac-evaluation-algorithm)
8. [Permission Matrix](#8-permission-matrix)
9. [Question & Option Visibility Evaluation](#9-question--option-visibility-evaluation)
10. [Skip Logic Evaluation](#10-skip-logic-evaluation)
11. [Form-Level Access Policies](#11-form-level-access-policies)
12. [API Key Scopes](#12-api-key-scopes)
13. [OAuth 2.0 Flows](#13-oauth-20-flows)
14. [Password Policies](#14-password-policies)
15. [Session Management](#15-session-management)
16. [Admin Approval Workflow](#16-admin-approval-workflow)
17. [Group Membership Resolution](#17-group-membership-resolution)
18. [External Collaborator Access](#18-external-collaborator-access)

---

## 1. Role Hierarchy

### 1.1 Complete Role Hierarchy Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    SYSTEM LEVEL                         │
│                                                         │
│  super_admin  ← Single user, platform-wide authority   │
│       │         Bypasses ALL org/project checks         │
│       │         Set via seed.py, stored in users.system_role
└───────┼─────────────────────────────────────────────────┘
        │
        ▼  (manages organisations)
┌─────────────────────────────────────────────────────────┐
│                ORGANISATION LEVEL                       │
│     (stored in org_memberships.role per org_id)        │
│                                                         │
│  org_admin                                              │
│       │   ← Manages members, settings, projects        │
│       │   ← Can invite/suspend/remove members          │
│       │   ← Full project CRUD within org               │
│       │   ← Access all forms and responses in org      │
│       ▼                                                 │
│  org_editor                                             │
│       │   ← Creates/edits forms and analyses           │
│       │   ← Cannot manage members                      │
│       │   ← Can see all responses                      │
│       ▼                                                 │
│  org_analyst                                            │
│       │   ← Read-only on forms and projects            │
│       │   ← Full access to Analysis Coder              │
│       │   ← Can read responses, cannot edit forms      │
│       ▼                                                 │
│  org_viewer                                             │
│           ← Read-only on all org resources             │
│           ← Cannot create or modify anything           │
└───────┬─────────────────────────────────────────────────┘
        │  (org role determines baseline project access)
        ▼
┌─────────────────────────────────────────────────────────┐
│                  PROJECT LEVEL                          │
│     (stored in project_members.role per project_id)    │
│     Project roles OVERRIDE org roles for that project  │
│                                                         │
│  project_owner                                          │
│       │   ← Manages project settings and membership    │
│       │   ← Full CRUD on forms, analyses, dashboards   │
│       │   ← Can transfer project ownership             │
│       ▼                                                 │
│  project_editor                                         │
│       │   ← Creates/edits forms, analyses, dashboards  │
│       │   ← Cannot manage project membership           │
│       ▼                                                 │
│  project_analyst                                        │
│       │   ← Can run analyses, view all responses       │
│       │   ← Read-only on forms                         │
│       ▼                                                 │
│  project_viewer                                         │
│           ← Read-only on all project resources         │
└───────┬─────────────────────────────────────────────────┘
        │  (project role governs form access baseline)
        ▼
┌─────────────────────────────────────────────────────────┐
│               FORM ACCESS LEVEL                         │
│     (stored in form_commits[].schema.access)           │
│                                                         │
│  type: public    ← Anyone (anonymous allowed)          │
│  type: org       ← Any authenticated org member        │
│  type: groups    ← Only members of allowed_group_ids   │
│  type: users     ← Only allowed_user_ids               │
└───────┬─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│            FIELD / QUESTION VISIBILITY                  │
│     (evaluated at render time per question)             │
│                                                         │
│  role condition  ← Shown only to specific roles        │
│  group condition ← Shown only to specific groups       │
│  answer condition← Shown only when answer matches      │
│  always_visible  ← Always shown                        │
│  always_hidden   ← Never shown (archived questions)    │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Role Enum Values

| Context       | Enum Values                                                      | Collection          | Field |
|---------------|------------------------------------------------------------------|---------------------|-------|
| System        | `super_admin`, `user`                                            | `users`             | `system_role` |
| Organisation  | `org_admin`, `org_editor`, `org_analyst`, `org_viewer`          | `org_memberships`   | `role` |
| Project       | `project_owner`, `project_editor`, `project_analyst`, `project_viewer` | `project_members` | `role` |

---

## 2. JWT Structure

### 2.1 Access Token Payload

```json
{
  "sub": "64f1a2b3c4d5e6f7a8b9c0d1",
  "email": "doctor@aiims.edu",
  "system_role": "user",
  "orgs": [
    {
      "org_id": "64f1a2b3c4d5e6f7a8b9c0d2",
      "role": "org_admin",
      "status": "active"
    },
    {
      "org_id": "64f1a2b3c4d5e6f7a8b9c0d3",
      "role": "org_viewer",
      "status": "active"
    }
  ],
  "iat": 1749292800,
  "exp": 1749293700
}
```

### 2.2 Field Definitions

| Field         | Type             | Description |
|---------------|------------------|-------------|
| `sub`         | `string`         | MongoDB ObjectId of the user (stringified). Used as the primary user identifier in all permission checks. |
| `email`       | `string`         | User's verified email address. Informational only; do NOT use for permission checks. |
| `system_role` | `enum`           | Either `"super_admin"` or `"user"`. `super_admin` bypasses all other checks. Sourced from `users.system_role`. |
| `orgs`        | `array[OrgClaim]`| All org memberships for this user at time of token issuance. |
| `orgs[].org_id` | `string`       | MongoDB ObjectId of the organisation (stringified). |
| `orgs[].role` | `enum`           | One of `org_admin`, `org_editor`, `org_analyst`, `org_viewer`. |
| `orgs[].status` | `enum`         | One of `active`, `suspended`, `pending`. Only `active` memberships grant access. |
| `iat`         | `integer`        | Issued-at time (Unix timestamp, UTC). |
| `exp`         | `integer`        | Expiry time (Unix timestamp, UTC). `iat + 900` (15 minutes). |

### 2.3 Token Properties

| Property                | Value |
|-------------------------|-------|
| Algorithm               | `HS256` (HMAC-SHA256) |
| Library                 | `python-jose` |
| Access Token TTL        | **15 minutes** (`exp = iat + 900`) |
| Refresh Token TTL       | **30 days** (stored in `sessions` collection, MongoDB TTL index) |
| Secret Key Source       | `JWT_SECRET_KEY` in `.env` |
| Token Format            | Standard JWT (Header.Payload.Signature) |
| Project roles in token  | **NOT included** — project membership is checked against MongoDB at request time, not from JWT |

> **Implementation Note**: Project-level roles are **not** embedded in the JWT because a user may belong to many projects and the token would become too large. Project membership is always resolved by querying `project_members` at request time, using `sub` from the JWT.

### 2.4 Token Headers

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

### 2.5 Token Validation Steps

The backend MUST validate tokens in this exact order:

1. Verify the JWT signature using `JWT_SECRET_KEY`.
2. Confirm `alg` is `HS256` — reject tokens with any other algorithm (prevent algorithm confusion attacks).
3. Confirm `exp > now` (token is not expired).
4. Confirm `sub` exists in the `users` collection with `status = "active"` and `is_deleted = false`.
5. Extract `system_role`, `orgs` from payload for further permission evaluation.

---

## 3. Auth Flow Diagrams

### 3.1 Registration → Admin Approval → Login Flow

```
User                         Backend (Flask)                    super_admin
 │                                │                                  │
 │  POST /api/auth/register       │                                  │
 │  { email, password,            │                                  │
 │    full_name, org_code? }      │                                  │
 │ ─────────────────────────────► │                                  │
 │                                │  1. Validate input               │
 │                                │  2. Check email uniqueness       │
 │                                │  3. Hash password (bcrypt, c=12) │
 │                                │  4. Create user record:          │
 │                                │     status = "pending_approval"  │
 │                                │     email_verified = false       │
 │                                │  5. Send email verification link │
 │                                │     (JWT token, TTL 24h)         │
 │ ◄─────────────────────────────  │                                  │
 │  201 { message: "Check email"} │                                  │
 │                                │                                  │
 │  GET /api/auth/verify-email    │                                  │
 │  ?token=<jwt>                  │                                  │
 │ ─────────────────────────────► │                                  │
 │                                │  6. Validate token               │
 │                                │  7. Set email_verified = true    │
 │                                │  8. Notify super_admin:          │
 │                                │     "New user awaiting approval" │
 │ ◄─────────────────────────────  │    ─────────────────────────────►
 │  200 { message: "Verified" }   │                                  │
 │                                │                    (Admin reviews │
 │                                │                     in admin panel│
 │                                │                     and approves) │
 │                                │                                  │
 │                                │  POST /api/admin/users/{id}/     │
 │                                │  approve                         │
 │                                │ ◄────────────────────────────────│
 │                                │  9. Set status = "active"        │
 │                                │  10. Set approved_at, approved_by│
 │                                │  11. Send "Account Approved"     │
 │                                │      email to user               │
 │ ◄─── Email: "You're approved"──│                                  │
 │                                │                                  │
 │  POST /api/auth/login          │                                  │
 │  { email, password }           │                                  │
 │ ─────────────────────────────► │                                  │
 │                                │  12. Validate credentials        │
 │                                │  13. Check status = "active"     │
 │                                │  14. Check failed_login_attempts │
 │                                │  15. Issue access token (15min)  │
 │                                │  16. Issue refresh token (30d)   │
 │                                │  17. Create sessions record      │
 │                                │  18. Update last_login_at        │
 │ ◄─────────────────────────────  │                                  │
 │  200 {                         │                                  │
 │    access_token: "...",        │                                  │
 │    refresh_token: "...",       │                                  │
 │    expires_in: 900,            │                                  │
 │    token_type: "Bearer"        │                                  │
 │  }                             │                                  │
```

### 3.2 Invite Flow

```
org_admin                    Backend (Flask)                    Invitee
    │                               │                              │
    │  POST /api/orgs/{id}/invite   │                              │
    │  { email, role,               │                              │
    │    project_id? }              │                              │
    │ ─────────────────────────────►│                              │
    │                               │  1. Validate org_admin role  │
    │                               │  2. Generate invitation JWT  │
    │                               │     (one-time use, TTL 7d)   │
    │                               │  3. Create invitations doc:  │
    │                               │     status = "pending"       │
    │                               │     expires_at = now + 7d    │
    │                               │  4. Send invite email with   │
    │                               │     magic link               │
    │                               │──────────────────────────────►
    │ ◄─────────────────────────────│  Email: "You're invited"     │
    │  201 { invitation_id }        │                              │
    │                               │                              │
    │                               │  POST /api/auth/             │
    │                               │  accept-invite/{token}       │
    │                               │◄─────────────────────────────│
    │                               │  5. Validate token signature │
    │                               │  6. Check expires_at > now   │
    │                               │  7. Check status = "pending" │
    │                               │  8a. If user exists:         │
    │                               │      Add org_membership      │
    │                               │  8b. If new user:            │
    │                               │      Create user (status=    │
    │                               │      "active", skip approval)│
    │                               │      Create org_membership   │
    │                               │  9. Set invitation           │
    │                               │     status = "accepted"      │
    │                               │  10. accepted_at = now()     │
    │                               │  11. Issue tokens            │
    │                               │──────────────────────────────►
    │                               │  200 { access_token,         │
    │                               │        refresh_token }       │
```

> **Invite TTL rules**:
> - Invitation token: **7 days** from creation. Stored as `expires_at` in `invitations` collection with a MongoDB TTL index.
> - If the invitee tries to use an expired token: return `410 Gone` with error code `INVITATION_EXPIRED`.
> - A revoked invitation (`status = "revoked"`) returns `410 Gone` with error code `INVITATION_REVOKED`.
> - Each invitation token is single-use: once `status` becomes `"accepted"`, subsequent requests with the same token are rejected.

---

## 4. Refresh Token Rotation

### 4.1 Strategy

The platform uses **single-use rotating refresh tokens**. Every time a client uses a refresh token, a new access token AND a new refresh token are issued. The old refresh token is immediately invalidated.

```
Client                           Backend
  │                                │
  │  POST /api/auth/refresh        │
  │  { refresh_token: "old_rt" }   │
  │ ──────────────────────────────►│
  │                                │  1. Hash incoming refresh_token
  │                                │     using SHA-256
  │                                │  2. Query sessions collection:
  │                                │     { refresh_token_hash: hash,
  │                                │       expires_at: { $gt: now } }
  │                                │  3. If NOT found: return 401
  │                                │     (token reuse attack — force
  │                                │      full logout of all sessions
  │                                │      for this user)
  │                                │  4. Delete old sessions record
  │                                │  5. Generate new refresh_token
  │                                │  6. Hash new refresh_token
  │                                │  7. Create new sessions record:
  │                                │     { user_id, refresh_token_hash,
  │                                │       device_info, ip_address,
  │                                │       expires_at: now + 30d }
  │                                │  8. Re-query fresh org memberships
  │                                │     from org_memberships collection
  │                                │  9. Issue new access_token (15min)
  │                                │     with fresh org claims
  │ ◄──────────────────────────────│
  │  200 {                         │
  │    access_token: "new_at",     │
  │    refresh_token: "new_rt",    │
  │    expires_in: 900             │
  │  }                             │
```

### 4.2 Token Reuse Detection (Security)

If an already-consumed refresh token is presented again (i.e., `refresh_token_hash` not found because the record was deleted on previous rotation), this indicates either:

- A stolen token being replayed, OR
- A client bug submitting the same token twice.

**Response**: Immediately invalidate ALL active sessions for that `user_id` (delete all `sessions` documents with that `user_id`) and return `401 Unauthorized` with error code `REFRESH_TOKEN_REUSE_DETECTED`. The user must log in again. The incident is written to `audit_logs`.

### 4.3 Sessions Collection Schema

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "refresh_token_hash": "SHA-256 hex digest of the raw refresh token string",
  "device_info": {
    "platform": "android|ios|web|windows|macos|linux",
    "user_agent": "string",
    "device_id": "string (client-generated UUID, stored in flutter_secure_storage)"
  },
  "ip_address": "string",
  "expires_at": "ISODate (TTL indexed — MongoDB auto-deletes expired docs)",
  "created_at": "ISODate"
}
```

The raw refresh token is never stored. Only `SHA-256(raw_refresh_token)` is persisted.

---

## 5. Multi-Org Membership

### 5.1 Data Model

A user may belong to **zero or more organisations** simultaneously. Each membership is an independent document in `org_memberships`:

```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "org_id": "ObjectId",
  "role": "org_editor",
  "custom_permissions": [],
  "status": "active",
  "invited_by": "ObjectId",
  "joined_at": "ISODate",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "is_deleted": false,
  "deleted_at": null
}
```

Compound unique index on `(user_id, org_id)` ensures a user has exactly one membership record per org.

### 5.2 JWT Claims for Multi-Org Users

All active, non-suspended org memberships are embedded in the JWT `orgs` array at token issuance time. The JWT payload for a user in two orgs looks like:

```json
{
  "sub": "64f1...",
  "email": "user@aiims.edu",
  "system_role": "user",
  "orgs": [
    { "org_id": "aaaaa", "role": "org_admin",  "status": "active" },
    { "org_id": "bbbbb", "role": "org_viewer", "status": "active" }
  ],
  "iat": 1749292800,
  "exp": 1749293700
}
```

Only memberships with `status = "active"` are included. `pending` and `suspended` memberships are excluded.

### 5.3 How to Extract the Correct Org Role at Request Time

Every API endpoint that operates on an org-scoped resource receives an `org_id` parameter (either in the URL path or request body). The permission check logic is:

```python
def get_user_org_role(token_claims: dict, org_id: str) -> str | None:
    """
    Returns the user's role in the given org from JWT claims,
    or None if the user has no active membership.
    """
    for org_claim in token_claims.get("orgs", []):
        if org_claim["org_id"] == org_id and org_claim["status"] == "active":
            return org_claim["role"]
    return None
```

If `get_user_org_role` returns `None`, the user has no active membership in the requested org and should receive a `403 Forbidden`.

### 5.4 Org Switching (Frontend)

The Flutter client maintains a concept of the **active org** in local state (Riverpod provider). Switching org context in the UI does NOT require a new token — the existing token already contains all org memberships. The frontend simply reads the correct `org_id` entry from the decoded token claims.

If a user is removed from an org between token issuances, the stale claim in the JWT may temporarily allow access until the 15-minute access token expires. Backend endpoints MUST additionally verify membership against the database for sensitive operations (role changes, deletion, admin actions) using the `org_memberships` collection, not just the JWT.

---

## 6. Role Inheritance Rules

### 6.1 Organisation Roles — Capability Breakdown

| Capability | org_admin | org_editor | org_analyst | org_viewer |
|---|:---:|:---:|:---:|:---:|
| View org settings | ✅ | ✅ | ✅ | ✅ |
| Edit org settings | ✅ | ❌ | ❌ | ❌ |
| Invite members | ✅ | ❌ | ❌ | ❌ |
| Suspend/remove members | ✅ | ❌ | ❌ | ❌ |
| View all member list | ✅ | ✅ | ✅ | ✅ |
| Create projects | ✅ | ✅ | ❌ | ❌ |
| Delete projects | ✅ | ❌ | ❌ | ❌ |
| Create forms | ✅ | ✅ | ❌ | ❌ |
| Edit forms | ✅ | ✅ | ❌ | ❌ |
| Publish forms | ✅ | ✅ | ❌ | ❌ |
| Delete forms | ✅ | ❌ | ❌ | ❌ |
| View all form responses | ✅ | ✅ | ✅ | ✅ |
| Export responses | ✅ | ✅ | ✅ | ❌ |
| Create analyses | ✅ | ✅ | ✅ | ❌ |
| Run analyses | ✅ | ✅ | ✅ | ❌ |
| Delete analyses | ✅ | ❌ | ❌ | ❌ |
| Create dashboards | ✅ | ✅ | ✅ | ❌ |
| Edit dashboards | ✅ | ✅ | ✅ | ❌ |
| Manage API keys (own org) | ✅ | ❌ | ❌ | ❌ |
| Manage groups | ✅ | ❌ | ❌ | ❌ |
| Adopt compliance standards | ✅ | ❌ | ❌ | ❌ |
| View audit logs | ✅ | ❌ | ❌ | ❌ |

### 6.2 Project Roles — Capability Breakdown

Project roles are scoped to a single project. When a user has a project role, it overrides (replaces, does not add to) their org role for actions within that specific project.

| Capability | project_owner | project_editor | project_analyst | project_viewer |
|---|:---:|:---:|:---:|:---:|
| Edit project settings | ✅ | ❌ | ❌ | ❌ |
| Manage project members | ✅ | ❌ | ❌ | ❌ |
| Create forms in project | ✅ | ✅ | ❌ | ❌ |
| Edit forms in project | ✅ | ✅ | ❌ | ❌ |
| Publish forms | ✅ | ✅ | ❌ | ❌ |
| Delete forms | ✅ | ❌ | ❌ | ❌ |
| View responses | ✅ | ✅ | ✅ | ✅ |
| Export responses | ✅ | ✅ | ✅ | ❌ |
| Create/run analyses | ✅ | ✅ | ✅ | ❌ |
| Delete analyses | ✅ | ❌ | ❌ | ❌ |
| Create/edit dashboards | ✅ | ✅ | ✅ | ❌ |

### 6.3 Hierarchy Override Rules

1. `super_admin` bypasses all checks. No further evaluation is needed.
2. If a user has an **org role** but no **project role** for a given project, their org role is used to derive project-level access using the mapping in §6.4.
3. If a user has an explicit **project role**, it takes complete precedence over their org role for all actions within that project.
4. An `org_admin` can add themselves to any project within their org with `project_owner` role.

### 6.4 Org-to-Project Role Mapping (when no explicit project role exists)

| Org Role | Effective Project Role |
|---|---|
| `org_admin` | `project_owner` |
| `org_editor` | `project_editor` |
| `org_analyst` | `project_analyst` |
| `org_viewer` | `project_viewer` |

---

## 7. ABAC Evaluation Algorithm

ABAC (Attribute-Based Access Control) is layered on top of the RBAC role hierarchy. The system evaluates multiple dimensions before granting or denying access.

### 7.1 Step-by-Step Permission Check Algorithm

The following pseudocode describes exactly how every permission check works. This MUST be implemented in `backend/app/services/auth_service.py`:

```
FUNCTION check_permission(user_token_claims, action, resource, context):

  STEP 1: Super Admin Bypass
  ─────────────────────────
  IF user_token_claims.system_role == "super_admin":
    RETURN ALLOW
  END IF

  STEP 2: Organisation Membership Check
  ──────────────────────────────────────
  resource_org_id = resource.org_id
  org_role = get_user_org_role(user_token_claims, resource_org_id)

  IF org_role is None:
    # User is not a member of this org at all
    # Unless this is a shared project (see §6.3) or external collaborator (§18)
    GOTO STEP 3 (project check as fallback)
  END IF

  IF org_role is None AND resource is not a project:
    RETURN DENY (403)
  END IF

  STEP 3: Project Membership Check (if resource is project-scoped)
  ─────────────────────────────────────────────────────────────────
  IF resource has project_id:
    project_member = DB.project_members.find_one({
      project_id: resource.project_id,
      user_id: user_token_claims.sub,
      is_deleted: false
    })

    IF project_member EXISTS AND project_member.status == "active":
      effective_role = project_member.role  # Project role takes precedence
    ELSE IF org_role EXISTS:
      effective_role = map_org_to_project_role(org_role)  # §6.4 mapping
    ELSE:
      # Check if project is shared with user's org
      project = DB.projects.find_one(resource.project_id)
      IF user_token_claims has any org_id IN project.shared_org_ids:
        effective_role = "project_viewer"  # Shared orgs get viewer access
      ELSE:
        RETURN DENY (403)
    END IF

    IF action NOT IN allowed_actions_for_role(effective_role):
      RETURN DENY (403)
    END IF
  END IF

  STEP 4: Form-Level Access Policy Check (if resource is a form or response)
  ──────────────────────────────────────────────────────────────────────────
  IF resource is a form_response or form_view:
    form_access = DB.form_commits.find(production_head).schema.access
    evaluate_form_access_policy(form_access, user_token_claims, context)
    # See §11 for full form access policy evaluation rules
  END IF

  STEP 5: Question Visibility Check (at render time only)
  ────────────────────────────────────────────────────────
  # Only relevant during form rendering, not for API data access
  IF context == "form_render":
    FOR EACH question IN form.questions:
      question.visible = evaluate_visibility_rules(
        question.visibility_rules,
        user_token_claims,
        current_answers
      )
      # See §9 for full visibility evaluation rules
    END FOR
  END IF

  RETURN ALLOW
```

### 7.2 `allowed_actions_for_role` Reference Table

See §8 (Permission Matrix) for the complete mapping.

### 7.3 `evaluate_visibility_rules` Algorithm

See §9 (Question & Option Visibility Evaluation).

---

## 8. Permission Matrix

This table covers every action on every resource type, showing which role can perform it. `✅` = allowed, `❌` = denied, `SA` = super_admin only.

### 8.1 User Management Actions

| Action | super_admin | org_admin | org_editor | org_analyst | org_viewer |
|---|:---:|:---:|:---:|:---:|:---:|
| List all platform users | SA | ❌ | ❌ | ❌ | ❌ |
| Approve/reject user registration | SA | ❌ | ❌ | ❌ | ❌ |
| Suspend any user globally | SA | ❌ | ❌ | ❌ | ❌ |
| View own profile | ✅ | ✅ | ✅ | ✅ | ✅ |
| Edit own profile | ✅ | ✅ | ✅ | ✅ | ✅ |
| List org members | ✅ | ✅ | ✅ | ✅ | ✅ |
| Invite user to org | ✅ | ✅ | ❌ | ❌ | ❌ |
| Change member role in org | ✅ | ✅ | ❌ | ❌ | ❌ |
| Suspend member from org | ✅ | ✅ | ❌ | ❌ | ❌ |
| Remove member from org | ✅ | ✅ | ❌ | ❌ | ❌ |

### 8.2 Organisation Actions

| Action | super_admin | org_admin | org_editor | org_analyst | org_viewer |
|---|:---:|:---:|:---:|:---:|:---:|
| Create organisation | SA | ❌ | ❌ | ❌ | ❌ |
| Approve organisation | SA | ❌ | ❌ | ❌ | ❌ |
| Suspend organisation | SA | ❌ | ❌ | ❌ | ❌ |
| Delete organisation | SA | ❌ | ❌ | ❌ | ❌ |
| View org details | ✅ | ✅ | ✅ | ✅ | ✅ |
| Edit org settings | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manage org groups | ✅ | ✅ | ❌ | ❌ | ❌ |
| Adopt compliance standard | ✅ | ✅ | ❌ | ❌ | ❌ |
| View storage quota | ✅ | ✅ | ❌ | ❌ | ❌ |
| Set storage quota | SA | ❌ | ❌ | ❌ | ❌ |
| Create API keys for org | ✅ | ✅ | ❌ | ❌ | ❌ |
| Revoke org API keys | ✅ | ✅ | ❌ | ❌ | ❌ |

### 8.3 Project Actions

| Action | super_admin | project_owner | project_editor | project_analyst | project_viewer |
|---|:---:|:---:|:---:|:---:|:---:|
| Create project (org-level) | ✅ | N/A | N/A | N/A | N/A |
| View project | ✅ | ✅ | ✅ | ✅ | ✅ |
| Edit project settings | ✅ | ✅ | ❌ | ❌ | ❌ |
| Archive project | ✅ | ✅ | ❌ | ❌ | ❌ |
| Delete project | ✅ | ❌ | ❌ | ❌ | ❌ |
| Invite user to project | ✅ | ✅ | ❌ | ❌ | ❌ |
| Change project member role | ✅ | ✅ | ❌ | ❌ | ❌ |
| Remove project member | ✅ | ✅ | ❌ | ❌ | ❌ |

### 8.4 Form Actions

| Action | super_admin | project_owner | project_editor | project_analyst | project_viewer |
|---|:---:|:---:|:---:|:---:|:---:|
| List forms in project | ✅ | ✅ | ✅ | ✅ | ✅ |
| View form (schema) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create form | ✅ | ✅ | ✅ | ❌ | ❌ |
| Edit form (new commit) | ✅ | ✅ | ✅ | ❌ | ❌ |
| Publish form (set production branch) | ✅ | ✅ | ✅ | ❌ | ❌ |
| Create branch | ✅ | ✅ | ✅ | ❌ | ❌ |
| Merge branch | ✅ | ✅ | ✅ | ❌ | ❌ |
| Delete form | ✅ | ✅ | ❌ | ❌ | ❌ |
| View form responses | ✅ | ✅ | ✅ | ✅ | ✅ |
| Export responses (CSV/Excel/PDF) | ✅ | ✅ | ✅ | ✅ | ❌ |
| Delete a response | ✅ | ✅ | ❌ | ❌ | ❌ |
| Configure form webhooks | ✅ | ✅ | ✅ | ❌ | ❌ |
| View form templates | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create form from template | ✅ | ✅ | ✅ | ❌ | ❌ |
| Publish form as template | ✅ | ✅ | ❌ | ❌ | ❌ |

### 8.5 Analysis Actions

| Action | super_admin | project_owner | project_editor | project_analyst | project_viewer |
|---|:---:|:---:|:---:|:---:|:---:|
| List analyses | ✅ | ✅ | ✅ | ✅ | ✅ |
| View analysis (read graph) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create analysis | ✅ | ✅ | ✅ | ✅ | ❌ |
| Edit analysis graph | ✅ | ✅ | ✅ | ✅ | ❌ |
| Run analysis (on-demand) | ✅ | ✅ | ✅ | ✅ | ❌ |
| Delete analysis | ✅ | ✅ | ❌ | ❌ | ❌ |
| Export analysis results | ✅ | ✅ | ✅ | ✅ | ❌ |
| Schedule analysis | ✅ | ✅ | ✅ | ✅ | ❌ |

### 8.6 Dashboard Actions

| Action | super_admin | project_owner | project_editor | project_analyst | project_viewer |
|---|:---:|:---:|:---:|:---:|:---:|
| View dashboard | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create dashboard | ✅ | ✅ | ✅ | ✅ | ❌ |
| Edit dashboard canvas | ✅ | ✅ | ✅ | ✅ | ❌ |
| Delete dashboard | ✅ | ✅ | ❌ | ❌ | ❌ |
| Enable public sharing | ✅ | ✅ | ✅ | ❌ | ❌ |

### 8.7 Plugin & System Actions

| Action | super_admin | org_admin | Others |
|---|:---:|:---:|:---:|
| Install plugin | SA | ❌ | ❌ |
| Suspend/unload plugin | SA | ❌ | ❌ |
| View installed plugins | ✅ | ✅ | ✅ |
| Define compliance standards | SA | ❌ | ❌ |
| View compliance standards | ✅ | ✅ | ✅ |
| Manage system config | SA | ❌ | ❌ |
| View audit logs | SA | ✅ (own org only) | ❌ |
| Archive audit logs | SA | ❌ | ❌ |

---

## 9. Question & Option Visibility Evaluation

### 9.1 VisibilityRules Data Structure

```json
{
  "operator": "AND",
  "conditions": [
    { "type": "role", "roles": ["org_admin", "project_owner"] },
    { "type": "answer", "field_id": "q_001", "operator": "equals", "value": "yes" }
  ]
}
```

If `visibility_rules` is `null` or `conditions` is an empty array, the element is **always visible**.

### 9.2 Condition Types

| Type | Fields | Meaning |
|---|---|---|
| `role` | `roles: [String]` | Visible only if the current user's effective role is in the `roles` list. Roles are checked at both org and project level. |
| `group` | `group_ids: [ObjectId]` | Visible only if the user is a member of at least one of the listed groups. Group membership is resolved per §17. |
| `answer` | `field_id`, `operator`, `value` | Visible only if the referenced field's current answer matches the condition. |
| `always_visible` | (none) | Unconditionally visible. Overrides all other conditions. |
| `always_hidden` | (none) | Unconditionally hidden. Used for archived/deprecated questions retained in schema for response integrity. |

### 9.3 Answer Condition Operators

| Operator | Applicable Types | Description |
|---|---|---|
| `equals` | string, number, boolean | Exact match |
| `not_equals` | string, number, boolean | Not exact match |
| `contains` | string, array | String contains substring OR array contains element |
| `greater_than` | number | Numeric greater than |
| `less_than` | number | Numeric less than |
| `in` | any | Value is in the given array |
| `not_in` | any | Value is not in the given array |
| `is_empty` | any | Value is `null`, `""`, or `[]` |
| `is_not_empty` | any | Value is not `null`, `""`, or `[]` |

### 9.4 Evaluation Order (Critical — Must Follow Exactly)

```
FUNCTION evaluate_visibility(element, user_claims, current_answers) -> bool:

  rules = element.visibility_rules
  IF rules is null OR rules.conditions is empty:
    RETURN true  # Default: visible

  # Step 1: Evaluate each condition independently
  results = []
  FOR EACH condition IN rules.conditions:

    IF condition.type == "always_visible":
      RETURN true  # Short-circuit: immediately visible

    IF condition.type == "always_hidden":
      RETURN false  # Short-circuit: immediately hidden

    IF condition.type == "role":
      effective_role = get_effective_role(user_claims, resource_context)
      results.append(effective_role IN condition.roles)

    IF condition.type == "group":
      user_groups = resolve_group_membership(user_claims.sub, resource_org_id)
      results.append(any(g IN condition.group_ids FOR g IN user_groups))

    IF condition.type == "answer":
      answer_value = current_answers.get(condition.field_id)
      results.append(evaluate_answer_condition(answer_value, condition))

  # Step 2: Apply boolean operator
  IF rules.operator == "AND":
    RETURN all(results)   # All conditions must be true
  ELSE IF rules.operator == "OR":
    RETURN any(results)   # At least one condition must be true
```

### 9.5 Evaluation Order for Role vs. Answer Conditions

1. **Role conditions are evaluated first** (server-side, at token validation time). Fields hidden by role are stripped from the API response entirely — they are NOT sent to the client.
2. **Answer-based conditions are evaluated client-side** (Flutter) at render time. The client already has the full question schema; answer-based visibility is a real-time UI concern.
3. **Group conditions are evaluated server-side** similarly to role conditions.

> **Security note**: Role-hidden fields MUST be excluded from API responses. It is not sufficient to hide them in the UI. The server must strip `always_hidden` and role-restricted fields before returning form schemas to users who lack the required role.

### 9.6 Nested Visibility (Sections and Sub-Sections)

Sections and sub-sections also carry `visibility_rules`. Evaluation order:

1. Evaluate Section visibility. If hidden → all questions in the section are hidden (regardless of their own rules).
2. Evaluate Sub-Section visibility (within a visible section). If hidden → all questions in the sub-section are hidden.
3. Evaluate Question visibility (within a visible sub-section).

---

## 10. Skip Logic Evaluation

### 10.1 SkipLogicDef Structure

```json
{
  "conditions": {
    "operator": "AND",
    "conditions": [
      { "type": "answer", "field_id": "q_003", "operator": "equals", "value": "no" }
    ]
  },
  "jump_to": "section",
  "target_id": "section_004"
}
```

| Field | Type | Description |
|---|---|---|
| `conditions` | `VisibilityRules` | Same condition structure as visibility rules. Evaluated using the same `evaluate_visibility` function. |
| `jump_to` | `enum` | One of: `section`, `sub_section`, `question`, `end` |
| `target_id` | `string` | UUID of the target `section`, `sub_section`, or `question`. Empty/null when `jump_to = "end"`. |

### 10.2 Skip Logic Resolution Algorithm (Client-Side)

Skip logic is evaluated entirely **client-side** in the Flutter form viewer. The algorithm:

```
FUNCTION resolve_next_element(current_element, current_answers, form_schema):

  # Step 1: Check if current element has skip_logic
  IF current_element.skip_logic is NOT null:
    conditions_met = evaluate_visibility(
      { visibility_rules: current_element.skip_logic.conditions },
      user_claims,
      current_answers
    )

    IF conditions_met:
      jump_to = current_element.skip_logic.jump_to
      target_id = current_element.skip_logic.target_id

      IF jump_to == "end":
        RETURN END_OF_FORM

      IF jump_to == "section":
        target = form_schema.find_section(target_id)
        IF target is null:
          LOG_WARNING("Skip logic target not found: " + target_id)
          RETURN next_sequential_element(current_element, form_schema)
        RETURN target

      IF jump_to == "sub_section":
        target = form_schema.find_sub_section(target_id)
        IF target is null:
          LOG_WARNING("Skip logic target not found: " + target_id)
          RETURN next_sequential_element(current_element, form_schema)
        RETURN target

      IF jump_to == "question":
        target = form_schema.find_question(target_id)
        IF target is null:
          LOG_WARNING("Skip logic target not found: " + target_id)
          RETURN next_sequential_element(current_element, form_schema)
        RETURN target

  # Step 2: No skip logic or conditions not met — proceed sequentially
  RETURN next_sequential_element(current_element, form_schema)
```

### 10.3 Rules and Edge Cases

| Edge Case | Behaviour |
|---|---|
| Target element does not exist | Log warning, fall through to next sequential element |
| Target is before current position | Allowed (backwards jump). Flutter must prevent infinite loops by tracking visited elements. |
| Multiple questions have skip logic | Evaluated per question. The first triggered skip wins for that question. |
| Skip logic on a hidden question | Hidden questions do not trigger skip logic (their skip_logic block is ignored). |
| Jump to `end` | Form is treated as complete; submit button becomes available. Questions after the jump point are cleared from answers. |
| Offline mode | Skip logic behaves identically — it is client-side only and requires no network. |

---

## 11. Form-Level Access Policies

Form access is controlled by the `access` object in `form_commits[].schema.access`. This is evaluated **after** org/project role checks and is an additional gate.

### 11.1 Access Object Structure

```json
{
  "type": "public|org|groups|users",
  "allowed_org_ids": ["ObjectId"],
  "allowed_group_ids": ["ObjectId"],
  "allowed_user_ids": ["ObjectId"],
  "allow_anonymous": true
}
```

### 11.2 Access Policy Types

#### `public`
- **Who can access**: Anyone with the link.
- **Authentication required**: No, unless `allow_anonymous: false`.
- **If `allow_anonymous: true`**: No login required. `respondent_id` in response = `null`. `respondent_email` captured if provided.
- **If `allow_anonymous: false`**: Login required. Any authenticated user (even with no org membership) may submit.
- **Enforcement**: The `GET /api/v1/forms/:id` public endpoint serves the form schema without a JWT. Submission `POST /api/v1/forms/:id/responses` is similarly unauthenticated if `allow_anonymous: true`.

#### `org`
- **Who can access**: Any active member of the form's `org_id`.
- **Authentication required**: Yes, JWT must be present.
- **Enforcement**: Extract `org_id` from form record. Check JWT `orgs` array for matching `org_id` with `status: "active"`. If not found → 403.

#### `groups`
- **Who can access**: Members of at least one group in `allowed_group_ids`.
- **Authentication required**: Yes.
- **Enforcement**: Resolve user's group memberships (see §17). Check for intersection with `allowed_group_ids`. If no intersection → 403.

#### `users`
- **Who can access**: Users whose `_id` is in `allowed_user_ids`.
- **Authentication required**: Yes.
- **Enforcement**: Check if `sub` (from JWT) is in `allowed_user_ids`. If not → 403.

### 11.3 Additional Form-Level Guards

These checks apply regardless of access type:

| Check | Condition | Response |
|---|---|---|
| Form expired | `settings.expires_at` is set AND `now > expires_at` | `410 Gone`, code `FORM_EXPIRED` |
| Max responses reached | `settings.max_responses` is set AND `response_count >= max_responses` | `410 Gone`, code `FORM_RESPONSE_CAP_REACHED` |
| Multiple submissions | `settings.allow_multiple_submissions = false` AND user already has a submitted response | `409 Conflict`, code `DUPLICATE_SUBMISSION` |
| Login required | `settings.require_login = true` AND no JWT | `401 Unauthorized` |

### 11.4 Response Edit Policy

Controlled by `settings.response_edit_policy`:

| Value | Behaviour |
|---|---|
| `no_edit` | Submitted responses cannot be edited by anyone. |
| `role_edit` | Only users with a role in `settings.edit_allowed_roles` can edit. |
| `time_window_edit` | Respondent can edit within `settings.edit_time_window_hours` hours of submission. |
| `always_edit` | Respondent can always edit their own submission. |

---

## 12. API Key Scopes

API keys are owned by an org (and a specific user within the org). They provide programmatic access to the public REST API (`/api/v1/`).

### 12.1 Available Scopes

| Scope String | Description | Equivalent User Permission |
|---|---|---|
| `forms:read` | List and read form schemas | `project_viewer` on forms |
| `forms:write` | Create and edit forms | `project_editor` on forms |
| `responses:read` | Read form responses | `project_analyst` on responses |
| `responses:write` | Submit form responses | Any authenticated respondent |
| `analyses:read` | Read analysis graphs and results | `project_analyst` on analyses |
| `analyses:run` | Trigger analysis execution | `project_analyst` on analyses |
| `dashboards:read` | Read dashboard configurations | `project_viewer` on dashboards |
| `users:read` | Read org member list | `org_viewer` on members |
| `admin:read` | Read org settings and audit log | `org_admin` read-only |
| `webhooks:write` | Create/update webhook configs | `project_editor` on webhooks |

### 12.2 API Key Storage

- The raw API key is shown to the user **once** upon creation and then discarded.
- The backend stores `key_hash = SHA-256(raw_key)` in the `api_keys` collection.
- The first 8 characters of the raw key are stored as `key_prefix` for display purposes (e.g., `fbk_a1b2`).
- API keys are prefixed with `fbk_` for easy identification in logs.

### 12.3 API Key Authentication

```
Authorization: ApiKey fbk_a1b2c3d4...
```

OR:

```
X-API-Key: fbk_a1b2c3d4...
```

On receipt:
1. Hash the provided key with SHA-256.
2. Look up `api_keys` by `{ key_hash: hash, status: "active", is_deleted: false }`.
3. Check `expires_at` if set.
4. Check `org_id` matches the requested resource's org.
5. Check requested action is in `scopes`.
6. Increment `usage_count`, update `last_used_at`.
7. Apply `rate_limit_per_hour` using Redis sliding window.

### 12.4 API Key Rate Limiting

Default: 1,000 requests per hour per key (configurable per key via `api_keys.rate_limit_per_hour`). Implemented using Flask-Limiter backed by Redis.

When limit is exceeded: `429 Too Many Requests` with headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: <unix_timestamp>
Retry-After: <seconds>
```

---

## 13. OAuth 2.0 Flows

### 13.1 Supported Grant Types

| Grant Type | Use Case | Collection |
|---|---|---|
| `client_credentials` | Server-to-server (no user context) | `oauth_clients` |
| `authorization_code` | User-facing apps (delegated access) | `oauth_clients` + `oauth_authorization_codes` (ephemeral) |

### 13.2 OAuth Client Registration

OAuth clients are registered by `org_admin` or `super_admin`. Stored in `oauth_clients`:

```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "client_id": "fb_client_a1b2c3d4",
  "client_secret_hash": "SHA-256 of client_secret",
  "name": "My Integration App",
  "redirect_uris": ["https://myapp.example.com/oauth/callback"],
  "scopes": ["forms:read", "responses:write"],
  "grant_types": ["authorization_code", "refresh_token"],
  "status": "active"
}
```

### 13.3 Client Credentials Flow

```
POST /api/v1/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=fb_client_a1b2c3d4
&client_secret=<raw_secret>
&scope=forms:read responses:read
```

Response:
```json
{
  "access_token": "eyJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "forms:read responses:read"
}
```

Notes:
- Client credentials tokens have TTL of **1 hour** (not 15 min like user tokens).
- They carry `org_id` and `scopes` in the payload but no `sub` (no user identity).
- These tokens do NOT have refresh tokens; clients must re-authenticate when expired.

### 13.4 Authorization Code Flow

```
Step 1: Redirect user to authorisation endpoint
GET /api/v1/oauth/authorize
  ?response_type=code
  &client_id=fb_client_a1b2c3d4
  &redirect_uri=https://myapp.example.com/oauth/callback
  &scope=forms:read+responses:write
  &state=random_csrf_string

Step 2: User logs in and approves (Flutter consent screen)

Step 3: Redirect back with code
GET https://myapp.example.com/oauth/callback
  ?code=<auth_code>
  &state=random_csrf_string

Step 4: Exchange code for tokens
POST /api/v1/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code=<auth_code>
&redirect_uri=https://myapp.example.com/oauth/callback
&client_id=fb_client_a1b2c3d4
&client_secret=<raw_secret>
```

- Auth codes are **single-use** and expire in **10 minutes**.
- Auth code + `redirect_uri` are stored in a short-lived Redis key (`oauth:code:{code_hash}`) and deleted on use.
- The resulting access token is a standard JWT with user `sub`, `email`, and the approved scopes.

---

## 14. Password Policies

### 14.1 Complexity Requirements

| Rule | Requirement |
|---|---|
| Minimum length | 8 characters |
| Maximum length | 128 characters |
| Must contain | At least one uppercase letter (A–Z) |
| Must contain | At least one lowercase letter (a–z) |
| Must contain | At least one digit (0–9) |
| Must contain | At least one special character (`!@#$%^&*()_+-=[]{};\':"|,.<>/?`) |
| Disallowed | Passwords matching the top 10,000 common passwords list (checked against bundled wordlist) |
| Disallowed | Password that contains the user's email prefix or display name (case-insensitive substring match) |

### 14.2 ISO 27001 Compliance Mode

When `ISO 27001` compliance standard is active for an org, the following additional rules apply to all members of that org:

| Rule | Requirement |
|---|---|
| Password expiry | Every **90 days**. User is forced to change on next login if expired. |
| Password history | Last **5 passwords** are stored (hashed). Cannot reuse any of them. |
| Forced change on first login | If account was created by invite (org_admin set initial password), user must change on first login. |

### 14.3 Password Hashing

- Algorithm: **bcrypt**
- Cost factor: **12**
- Implementation: `bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))`
- Hash is stored in `users.password_hash`.

### 14.4 Password Reset Flow

```
POST /api/auth/forgot-password
{ "email": "user@aiims.edu" }

→ 200 OK (always, even if email not found — no user enumeration)
→ Celery task: sends reset email with JWT token (TTL 1 hour)

POST /api/auth/reset-password
{ "token": "...", "new_password": "..." }

→ Validate token signature and expiry
→ Validate new password against complexity rules
→ Validate against password history (if ISO 27001 active)
→ Hash new password with bcrypt(cost=12)
→ Update users.password_hash
→ Invalidate all sessions for this user (force re-login on all devices)
→ Write audit_log entry: action="password_reset"
→ 200 OK
```

---

## 15. Session Management

### 15.1 Device Tracking

Each refresh token is associated with a `device_info` object:

```json
{
  "platform": "android",
  "user_agent": "FormBuilder/1.0.0 (Android 14; SM-G998B)",
  "device_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

The `device_id` is a UUID generated by the Flutter client on first launch and stored in `flutter_secure_storage`. It persists across app restarts but is cleared on app uninstall.

A user may have **multiple simultaneous sessions** (e.g., phone + tablet + desktop). Each session is a separate document in the `sessions` collection.

### 15.2 Session Listing

Authenticated users can view their active sessions:

```
GET /api/auth/sessions
Authorization: Bearer <access_token>

Response:
[
  {
    "session_id": "...",
    "device_info": { "platform": "android", "user_agent": "...", "device_id": "..." },
    "ip_address": "10.0.0.5",
    "created_at": "2026-06-01T10:00:00Z",
    "expires_at": "2026-07-01T10:00:00Z",
    "is_current": true
  }
]
```

### 15.3 Force Logout

Administrators (`super_admin` and `org_admin` for their members) can force-logout a user by deleting all their `sessions` records. This takes effect on the next refresh token use (access tokens remain valid until their 15-minute TTL expires).

```
POST /api/admin/users/{user_id}/force-logout
→ DB: sessions.deleteMany({ user_id: user_id })
→ Write audit_log: action="force_logout", actor_id=admin_id
→ 200 OK
```

### 15.4 Logout

```
POST /api/auth/logout
Authorization: Bearer <access_token>
{ "refresh_token": "current_refresh_token" }

→ Hash the refresh_token
→ DB: sessions.deleteOne({ refresh_token_hash: hash })
→ 200 OK
```

The access token remains technically valid until expiry (15 min). There is no server-side access token blacklist. Clients MUST discard the access token from memory on logout.

### 15.5 Refresh Token Rotation (Full Detail)

See §4 for the complete rotation algorithm. Additional considerations:

- On each rotation, the new `sessions` record inherits `device_info` from the old record (no update needed from client).
- If `ip_address` changes between refresh cycles (user changed network), the new IP is recorded in the new session.
- The TTL of the new refresh token is always `now + 30 days` (rolling window, not fixed expiry from first login).

---

## 16. Admin Approval Workflow

### 16.1 User Registration States

```
                    POST /auth/register
                           │
                           ▼
                    ┌─────────────┐
                    │   pending   │ ← email_verified = false
                    │  _approval  │
                    └──────┬──────┘
                           │ POST /auth/verify-email
                           │ (email_verified = true)
                           │ Notify super_admin
                           │
                    ┌──────▼──────┐
                    │   pending   │ ← email_verified = true
                    │  _approval  │   awaiting super_admin action
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           │               │               │
    APPROVE │         REJECT│         (no action,
           ▼               ▼          user re-invited)
    ┌──────────┐    ┌──────────────┐
    │  active  │    │  deactivated │
    └──────────┘    └──────────────┘
```

### 16.2 State Transition Rules

| From State | To State | Trigger | Actor | Side Effects |
|---|---|---|---|---|
| `pending_approval` | `active` | `POST /api/admin/users/{id}/approve` | `super_admin` | Set `approved_at`, `approved_by`. Send "Approved" email. Write audit_log. |
| `pending_approval` | `deactivated` | `POST /api/admin/users/{id}/reject` | `super_admin` | Set `is_deleted = true`, `deleted_at`. Send "Rejected" email (optional, configurable). Write audit_log. |
| `active` | `suspended` | `POST /api/admin/users/{id}/suspend` | `super_admin` or `org_admin` | Invalidate all sessions. JWT claims for this user will fail org status check on next request. Send notification. Write audit_log. |
| `suspended` | `active` | `POST /api/admin/users/{id}/activate` | `super_admin` or `org_admin` | Send notification. Write audit_log. |
| `active` | `deactivated` | `DELETE /api/admin/users/{id}` | `super_admin` | Soft delete: `is_deleted = true`. Invalidate all sessions. Write audit_log. |

### 16.3 Organisation Approval

Similar to user approval, organisations have their own approval workflow:

```
POST /api/admin/organisations  (super_admin creates org)
→ status = "pending_approval"

POST /api/admin/organisations/{id}/approve  (super_admin)
→ status = "active"
→ Notify org creator
→ Write audit_log

POST /api/admin/organisations/{id}/suspend  (super_admin)
→ status = "suspended"
→ All org members get 403 on org-scoped requests
→ Invalidate all sessions of all org members
→ Write audit_log
```

### 16.4 Invited User Bypass

Users who register via an invitation link (see §3.2) **skip the `pending_approval` state**. Their account is created directly with `status = "active"`. This is by design — the org_admin has pre-verified the invitee by choosing to send the invite.

---

## 17. Group Membership Resolution

### 17.1 Group Types

Groups are org-scoped and have two types:

| Type | Description | Members Stored In |
|---|---|---|
| `static` | Fixed list of users manually added/removed | `group_members` collection |
| `dynamic` | Rule-based — members computed at query time | `groups.dynamic_rule` |

### 17.2 Static Group Membership

Static group members are stored in `group_members`:

```json
{
  "_id": "ObjectId",
  "group_id": "ObjectId",
  "user_id": "ObjectId",
  "added_by": "ObjectId",
  "created_at": "ISODate"
}
```

Compound unique index on `(group_id, user_id)`.

### 17.3 Dynamic Group Rule Structure

```json
{
  "field": "role",
  "operator": "equals",
  "value": "org_analyst"
}
```

| Field | Supported Values | Description |
|---|---|---|
| `field` | `role` | Matches users by their `org_memberships.role` |
| `operator` | `equals`, `contains`, `in` | Comparison operator |
| `value` | any | The value to match against |

**Currently supported dynamic rule fields**: `role` only (in Phase 1). Additional fields (e.g., `department`, `location`) may be added via system config in later phases.

### 17.4 Dynamic Group Resolution Algorithm

```python
def resolve_group_members(group: dict, org_id: str) -> list[str]:
    """Returns list of user_ids who are members of the dynamic group."""
    if group["type"] == "static":
        return [gm["user_id"] for gm in db.group_members.find({"group_id": group["_id"]})]

    rule = group["dynamic_rule"]
    if rule["field"] == "role":
        memberships = db.org_memberships.find({
            "org_id": org_id,
            "status": "active",
            "is_deleted": False,
            "role": apply_operator(rule["operator"], rule["value"])
        })
        return [m["user_id"] for m in memberships]

    return []  # Unsupported field — empty set (fail-safe)
```

### 17.5 Group Membership Caching

Dynamic group resolution is **not cached in Phase 1**. Every visibility check requiring group membership performs a MongoDB query. For Phase 5+, Redis caching with a 60-second TTL may be introduced.

### 17.6 User's Full Group Set (for permission checks)

```python
def get_user_groups(user_id: str, org_id: str) -> list[str]:
    """Returns list of group_ids the user belongs to."""
    result = []
    all_groups = db.groups.find({"org_id": org_id, "is_deleted": False})
    for group in all_groups:
        members = resolve_group_members(group, org_id)
        if user_id in members:
            result.append(str(group["_id"]))
    return result
```

---

## 18. External Collaborator Access

### 18.1 Definition

An **external collaborator** is a user who:
- Has a registered and approved platform account, AND
- Is added to a **specific project** via a project-level invitation, AND
- Is NOT a member of the project's owner org.

This allows, for example, a research partner from another institution to collaborate on a specific project without being granted broad org-level access.

### 18.2 Prerequisites

External collaborators are only permitted if the org has `settings.allow_external_collaborators = true`.

### 18.3 How It Works

1. `project_owner` (or `org_admin`) invites the external user's email to the project.
2. If the user already has an account: an `invitations` record is created with `project_id` set and `org_id` left as the project's owner org.
3. If the user does not have an account: they register normally, go through admin approval, then accept the invitation.
4. On invitation acceptance: a `project_members` record is created with the external user's `user_id` and the specified role.
5. The user's JWT `orgs` array does NOT include the project's owner org — they have no org-level access.

### 18.4 Access Scope of External Collaborators

| Capability | External Collaborator |
|---|---|
| Access org settings | ❌ Never |
| List org members | ❌ Never |
| Access other projects in the org | ❌ Never |
| Access the specific project they're invited to | ✅ (per their project_role) |
| Submit to forms in their project | ✅ (if form access policy allows) |
| View responses in their project | Depends on `project_role` |
| Access org audit logs | ❌ Never |

### 18.5 Project-Level Permission Resolution for External Collaborators

Since external collaborators have no org-level JWT claim for the project's org, the ABAC algorithm in §7.1 falls through to the explicit `project_members` check. The algorithm handles this:

```python
# In STEP 3 of §7.1:
project_member = db.project_members.find_one({
    "project_id": resource.project_id,
    "user_id": user_claims["sub"],
    "is_deleted": False
})
if project_member:
    effective_role = project_member["role"]
    # Proceed with project-role-based checks
```

External collaborators are therefore fully supported by the same ABAC evaluation — no special-case code is needed beyond the existing project member lookup.

---

*End of 04_AUTH_AND_ROLES.md*
