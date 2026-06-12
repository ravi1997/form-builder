# 03 — API Specification

This document defines the REST API endpoints exposed by the backend services of the Form Builder Platform. All route blueprints, request serializers, parameter parsers, and response definitions MUST conform to this spec.

---

## 1. Global System Conventions

### 1.1 HTTP Status Codes
* **200 OK**: Request completed successfully.
* **201 Created**: Resource created successfully.
* **202 Accepted**: Task queued for background processing (e.g. analysis runs, file exports).
* **400 Bad Request**: Validation failed or missing parameters.
* **401 Unauthorized**: Missing or expired JWT / API key.
* **403 Forbidden**: Role-hierarchy or ABAC checks failed (user does not belong to organization or lacks scopes).
* **404 Not Found**: Target resource does not exist or is soft-deleted.
* **409 Conflict**: Version mismatch or branch merge conflicts.
* **429 Too Many Requests**: Rate limits exceeded.

### 1.2 Common Envelope Structures

#### Success Response
```json
{
  "status": "success",
  "data": {}
}
```

#### Error Response
```json
{
  "status": "error",
  "code": "ERROR_CODE",
  "message": "Human-readable description of error.",
  "details": {}
}
```

---

## 2. Authentication Route Group (`/api/auth/*`)

### `POST /api/auth/register`
* **Description**: Submit a user registration form.
* **Auth Requirement**: Public
* **Request Body**:
```json
{
  "email": "dr.ravi@aiims.edu",
  "password": "Password123!",
  "full_name": "Ravi Kumar"
}
```
* **Response (201 Created)**:
```json
{
  "status": "success",
  "message": "User registered successfully. Pending administrator approval."
}
```

### `POST /api/auth/login`
* **Description**: Authenticate using username and password. Returns JWT access and refresh tokens.
* **Auth Requirement**: Public
* **Request Body**:
```json
{
  "email": "dr.ravi@aiims.edu",
  "password": "Password123!"
}
```
* **Response (200 OK)**:
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "a1f9b2c3...",
    "token_type": "Bearer",
    "expires_in": 3600
  }
}
```

### `POST /api/auth/refresh`
* **Description**: Issue a new access token using a refresh token (implementing token rotation).
* **Auth Requirement**: Public (Refresh token sent in body)
* **Request Body**:
```json
{
  "refresh_token": "a1f9b2c3..."
}
```
* **Response (200 OK)**:
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "z9y8x7w6...",
    "expires_in": 3600
  }
}
```

---

## 3. Organizations Route Group (`/api/internal/v1/orgs/*`)

### `GET /api/internal/v1/orgs`
* **Description**: Fetch all organizations the logged-in user belongs to.
* **Auth Requirement**: JWT Access Token
* **Response (200 OK)**:
```json
{
  "status": "success",
  "data": [
    {
      "org_id": "603d4a259c6b8c2c5c994510",
      "name": "AIIMS New Delhi",
      "slug": "aiims-delhi",
      "role": "org_admin"
    }
  ]
}
```

### `POST /api/internal/v1/orgs`
* **Description**: Create a new organization or sub-department.
* **Auth Requirement**: JWT Access Token (requires system `super_admin` or parent `org_admin` permissions)
* **Request Body**:
```json
{
  "name": "Department of Cardiology",
  "parent_org_id": "603d4a259c6b8c2c5c994510",
  "org_type": "department"
}
```
* **Response (201 Created)**:
```json
{
  "status": "success",
  "data": {
    "org_id": "603d4a259c6b8c2c5c994515",
    "name": "Department of Cardiology",
    "slug": "department-of-cardiology",
    "parent_org_id": "603d4a259c6b8c2c5c994510"
  }
}
```

---

## 4. Form Management Route Group (`/api/internal/v1/forms/*`)

### `GET /api/internal/v1/forms`
* **Description**: Fetch forms list.
* **Auth Requirement**: JWT Access Token
* **Query Parameters**:
  - `project_id`: ObjectId (Filter forms inside project context)
* **Response (200 OK)**:
```json
{
  "status": "success",
  "data": [
    {
      "form_id": "603d4a259c6b8c2c5c994550",
      "name": "Patient Screening Form",
      "production_branch": "main",
      "updated_at": "2026-06-07T10:00:00Z"
    }
  ]
}
```

### `POST /api/internal/v1/forms`
* **Description**: Create a form configuration.
* **Auth Requirement**: JWT Access Token (requires role: `org_editor` or above)
* **Request Body**:
```json
{
  "project_id": "603d4a259c6b8c2c5c994520",
  "name": "Patient Registration",
  "description": "Standard registration form for clinical outpatient checkups."
}
```
* **Response (201 Created)**:
```json
{
  "status": "success",
  "data": {
    "form_id": "603d4a259c6b8c2c5c994550",
    "name": "Patient Registration",
    "branches": {
      "main": "init_commit_hash"
    }
  }
}
```

### `POST /api/internal/v1/forms/<form_id>/commits`
* **Description**: Commit schema modifications to the development branch (equivalent to a Git commit).
* **Auth Requirement**: JWT Access Token (requires role: `org_editor` or above)
* **Request Body**:
```json
{
  "branch": "main",
  "parent_id": "previous_commit_hash",
  "message": "Added Blood Pressure input component",
  "schema": {
    "ui": {
      "theme": {},
      "layout": "single_page"
    },
    "access": {
      "type": "org",
      "allow_anonymous": false
    },
    "sections": []
  }
}
```
* **Response (200 OK)**:
```json
{
  "status": "success",
  "data": {
    "commit_id": "new_commit_sha_hash",
    "timestamp": "2026-06-07T10:15:00Z"
  }
}
```

### `GET /api/internal/v1/forms/<form_id>/history`
* **Description**: Search prior submitted responses for a keyed value entered in a searchable question. This is the "History" lookup action, not an audit timeline.
* **Auth Requirement**: JWT Access Token
* **Query Parameters**:
  - `question_id`: ObjectId or question UUID (required)
  - `primary_value`: string (required)
  - `match_mode`: `exact` or `normalized` (optional, defaults to the form/question setting)
  - `limit`: integer (optional, defaults to the form-level max)
  - `cursor`: string (optional, for pagination)
  - `include_archived`: boolean (optional, admin-only)
* **Response (200 OK)**:
```json
{
  "status": "success",
  "data": {
    "lookup": {
      "form_id": "603d4a259c6b8c2c5c994550",
      "question_id": "q_patient_id",
      "primary_value": "PAT-10293",
      "match_mode": "normalized"
    },
    "count": 3,
    "next_cursor": null,
    "results": [
      {
        "response_id": "603d4a259c6b8c2c5c99450a",
        "submission_number": 435,
        "submitted_at": "2026-06-07T10:15:00Z",
        "status": "submitted",
        "summary": {
          "q_patient_name": "Jane Doe",
          "q_visit_date": "2026-06-07",
          "q_department": "Cardiology"
        },
        "can_open": true
      }
    ]
  }
}
```

---

## 5. Analysis Route Group (`/api/internal/v1/analysis/*`)

### `POST /api/internal/v1/analysis/<analysis_id>/run`
* **Description**: Execute DAG analysis nodes.
* **Auth Requirement**: JWT Access Token
* **Request Body**:
```json
{
  "trigger_mode": "manual"
}
```
* **Response (202 Accepted)**:
```json
{
  "status": "success",
  "data": {
    "run_id": "603d4a259c6b8c2c5c994599",
    "status": "queued"
  }
}
```

---

## 6. Public integration REST API (`/api/v1/*`)

Endpoints protected by static key validation. Headers require `X-API-Key`.

### `POST /api/v1/forms/<form_id>/responses`
* **Description**: Submit form response dataset entries externally.
* **Auth Requirement**: API Key Header (`X-API-Key`)
* **Request Body**:
```json
{
  "commit_id": "production_commit_hash",
  "answers": {
    "question_uuid_1": {
      "value": "Dr. Ravi",
      "display_value": "Dr. Ravi"
    },
    "question_uuid_2": {
      "value": 45,
      "display_value": "45"
    }
  }
}
```
* **Response (201 Created)**:
```json
{
  "status": "success",
  "data": {
    "response_id": "603d4a259c6b8c2c5c99450a",
    "submission_number": 435,
    "status": "submitted"
  }
}
```
