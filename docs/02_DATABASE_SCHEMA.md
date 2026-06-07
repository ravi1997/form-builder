# 02 — Database Schema Reference

This document is the authoritative reference for all MongoDB collections in the Form Builder Platform. Every document written by backend service modules or validated by Pydantic serializers MUST conform to the definitions, types, index specifications, and relationship mappings detailed below.

---

## 1. Global Document Envelope

Every document across all collections (unless explicitly marked as a system-level singleton) MUST contain the following default envelope fields:

```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId | null",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "created_by": "ObjectId (user_id) | null",
  "is_deleted": "Boolean (default: false)",
  "deleted_at": "ISODate | null"
}
```

* **Multi-Tenancy Isolation Rule**: Any query executing on an organization-scoped collection MUST include the filter criteria: `{"org_id": current_org_id, "is_deleted": false}`.
* **Audit Trail Rule**: System mutations MUST trigger an append event to the `audit_logs` collection detailing the delta payload.

---

## 2. Schema Definitions by Collection Group

### 2.1 System Collections

#### Collection: `system_config`
Stores deployment-wide system-level parameters. There is only a single configuration document in the collection.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "key": "String (unique)",
  "value": "Any",
  "updated_at": "ISODate",
  "updated_by": "ObjectId"
}
```
* **Indexes**:
  - `{"key": 1}` (Unique)
* **Example Document**:
```json
{
  "_id": {"$oid": "603d4a259c6b8c2c5c994501"},
  "key": "email_api_url",
  "value": "https://rpcapplication.aiims.edu/services/api/v1/mail/single",
  "updated_at": {"$date": "2026-06-07T10:00:00Z"},
  "updated_by": {"$oid": "603d4a259c6b8c2c5c994500"}
}
```

#### Collection: `audit_logs`
An append-only log recording structural, data, or configuration updates. This collection does not support soft deletes or TTL updates.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId | null",
  "project_id": "ObjectId | null",
  "entity_type": "String (e.g., 'forms', 'users', 'analyses')",
  "entity_id": "ObjectId",
  "action": "String (e.g., 'create', 'update', 'delete', 'publish', 'login')",
  "actor_id": "ObjectId",
  "actor_role": "String",
  "ip_address": "String",
  "user_agent": "String",
  "before": "Object | null",
  "after": "Object | null",
  "metadata": "Object",
  "timestamp": "ISODate",
  "archived": "Boolean (default: false)"
}
```
* **Indexes**:
  - `{"org_id": 1, "timestamp": -1}`
  - `{"entity_type": 1, "entity_id": 1}`
  - `{"actor_id": 1, "timestamp": -1}`
  - `{"timestamp": 1}`
* **Example Document**:
```json
{
  "_id": {"$oid": "603d4a259c6b8c2c5c994502"},
  "org_id": {"$oid": "603d4a259c6b8c2c5c994510"},
  "project_id": {"$oid": "603d4a259c6b8c2c5c994520"},
  "entity_type": "forms",
  "entity_id": {"$oid": "603d4a259c6b8c2c5c994550"},
  "action": "publish",
  "actor_id": {"$oid": "603d4a259c6b8c2c5c994500"},
  "actor_role": "org_admin",
  "ip_address": "192.168.1.50",
  "user_agent": "Mozilla/5.0 ... FlutterClient",
  "before": {"production_branch": "main"},
  "after": {"production_branch": "v2_release"},
  "metadata": {"commit_id": "abc123xyz"},
  "timestamp": {"$date": "2026-06-07T10:05:00Z"},
  "archived": false
}
```

---

### 2.2 Identity & Access Collections

#### Collection: `users`
Standard record for all application user logins.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "email": "String (unique, validated case-insensitive)",
  "password_hash": "String",
  "full_name": "String",
  "display_name": "String",
  "avatar_url": "String | null",
  "phone": "String | null",
  "status": "String (enum: pending_approval | active | suspended | deactivated)",
  "email_verified": "Boolean",
  "phone_verified": "Boolean",
  "last_login_at": "ISODate | null",
  "login_count": "Number",
  "failed_login_attempts": "Number",
  "locked_until": "ISODate | null",
  "two_factor_enabled": "Boolean",
  "two_factor_secret": "String | null",
  "notification_preferences": {
    "email": "Boolean",
    "sms": "Boolean",
    "push": "Boolean",
    "in_app": "Boolean"
  },
  "device_tokens": [
    {
      "token": "String",
      "platform": "String (enum: android | ios | web | desktop)",
      "created_at": "ISODate"
    }
  ],
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "approved_at": "ISODate | null",
  "approved_by": "ObjectId | null",
  "is_deleted": "Boolean",
  "deleted_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"email": 1}` (Unique)
  - `{"status": 1}`

#### Collection: `organisations`
Organizations can contain nested branches, forming a structural department/unit tree.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "name": "String",
  "slug": "String (unique)",
  "description": "String",
  "parent_org_id": "ObjectId | null",
  "org_type": "String (enum: organisation | department | team | unit)",
  "status": "String (enum: pending_approval | active | suspended)",
  "approved_at": "ISODate | null",
  "approved_by": "ObjectId | null",
  "settings": {
    "allow_public_forms": "Boolean",
    "default_form_theme": "Object",
    "max_members": "Number",
    "allow_external_collaborators": "Boolean"
  },
  "compliance_ids": ["ObjectId"],
  "storage_quota_bytes": "Number",
  "storage_used_bytes": "Number",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "created_by": "ObjectId",
  "is_deleted": "Boolean",
  "deleted_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"slug": 1}` (Unique)
  - `{"parent_org_id": 1}`

#### Collection: `org_memberships`
Tracks many-to-many relationship structures linking users to their target organizations.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "org_id": "ObjectId",
  "role": "String (enum: org_admin | org_editor | org_analyst | org_viewer)",
  "custom_permissions": ["String"],
  "status": "String (enum: active | suspended | pending)",
  "invited_by": "ObjectId | null",
  "joined_at": "ISODate | null",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "is_deleted": "Boolean",
  "deleted_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"user_id": 1, "org_id": 1}` (Unique)
  - `{"org_id": 1}`

#### Collection: `groups`
Organisational static or logical grouping definitions.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "name": "String",
  "description": "String",
  "type": "String (enum: static | dynamic)",
  "dynamic_rule": {
    "field": "String",
    "operator": "String (enum: equals | contains | in)",
    "value": "Any"
  },
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "created_by": "ObjectId",
  "is_deleted": "Boolean",
  "deleted_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"org_id": 1}`

#### Collection: `group_members`
Links users to static group memberships.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "group_id": "ObjectId",
  "user_id": "ObjectId",
  "added_by": "ObjectId",
  "created_at": "ISODate"
}
```
* **Indexes**:
  - `{"group_id": 1, "user_id": 1}` (Unique)

#### Collection: `invitations`
Used to track system-level invite token linkages.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "token": "String (unique)",
  "org_id": "ObjectId",
  "project_id": "ObjectId | null",
  "invited_by": "ObjectId",
  "invited_email": "String",
  "role": "String",
  "status": "String (enum: pending | accepted | expired | revoked)",
  "expires_at": "ISODate",
  "accepted_at": "ISODate | null",
  "created_at": "ISODate"
}
```
* **Indexes**:
  - `{"token": 1}` (Unique)
  - `{"expires_at": 1}` (TTL index)

#### Collection: `sessions`
Tracks active sessions and login tokens.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "refresh_token_hash": "String (unique)",
  "device_info": "String",
  "ip_address": "String",
  "expires_at": "ISODate",
  "created_at": "ISODate"
}
```
* **Indexes**:
  - `{"refresh_token_hash": 1}` (Unique)
  - `{"expires_at": 1}` (TTL index)

#### Collection: `api_keys`
API key linkages.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "user_id": "ObjectId",
  "name": "String",
  "key_hash": "String",
  "key_prefix": "String",
  "scopes": ["String"],
  "rate_limit_per_hour": "Number",
  "last_used_at": "ISODate | null",
  "usage_count": "Number",
  "expires_at": "ISODate | null",
  "status": "String (enum: active | revoked)",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "is_deleted": "Boolean",
  "deleted_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"key_hash": 1}` (Unique)
  - `{"org_id": 1}`

#### Collection: `oauth_clients`
Registered third-party clients.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "client_id": "String (unique)",
  "client_secret_hash": "String",
  "name": "String",
  "redirect_uris": ["String"],
  "scopes": ["String"],
  "grant_types": ["String"],
  "status": "String (enum: active | revoked)",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "is_deleted": "Boolean",
  "deleted_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"client_id": 1}` (Unique)

---

### 2.3 Project Collections

#### Collection: `projects`
Organizational workspaces grouping forms, analysis flows, and dashboards.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "name": "String",
  "description": "String",
  "slug": "String",
  "owner_org_id": "ObjectId",
  "shared_org_ids": ["ObjectId"],
  "status": "String (enum: active | archived)",
  "settings": {
    "default_form_theme": "Object",
    "default_compliance_ids": ["ObjectId"],
    "default_language": "String"
  },
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "created_by": "ObjectId",
  "is_deleted": "Boolean",
  "deleted_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"org_id": 1}`
  - `{"slug": 1}`

#### Collection: `project_members`
Memberships assigned inside projects.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "project_id": "ObjectId",
  "user_id": "ObjectId",
  "org_id": "ObjectId",
  "role": "String (enum: project_owner | project_editor | project_analyst | project_viewer)",
  "invited_by": "ObjectId",
  "joined_at": "ISODate",
  "created_at": "ISODate",
  "is_deleted": "Boolean"
}
```
* **Indexes**:
  - `{"project_id": 1, "user_id": 1}` (Unique)

---

### 2.4 Plugin & Concept Collections

#### Collection: `concept_registry`
The root register cataloguing builder concepts.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "concept_id": "String (unique)",
  "name": "String",
  "description": "String",
  "builder_type": "String (enum: form_builder | analysis_coder | dashboard_builder)",
  "supported_component_types": ["String"],
  "output_format": "String",
  "version_support": "Boolean",
  "collaboration_support": "Boolean",
  "is_system": "Boolean",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```
* **Indexes**:
  - `{"concept_id": 1}` (Unique)

#### Collection: `plugins`
Metadata for installed extension plugins.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "plugin_id": "String (unique)",
  "name": "String",
  "description": "String",
  "author": "String",
  "version": "String",
  "manifest": "Object",
  "status": "String (enum: active | suspended | unloaded)",
  "concept_targets": ["String"],
  "permissions": ["String"],
  "installed_at": "ISODate",
  "installed_by": "ObjectId",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "is_deleted": "Boolean",
  "deleted_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"plugin_id": 1}` (Unique)

#### Collection: `plugin_versions`
Historical versions of installed plugins.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "plugin_id": "String",
  "version": "String",
  "manifest": "Object",
  "files_path": "String",
  "status": "String (enum: active | deprecated | yanked)",
  "released_at": "ISODate",
  "created_at": "ISODate"
}
```
* **Indexes**:
  - `{"plugin_id": 1, "version": 1}` (Unique)

#### Collection: `component_schemas`
Contains UI properties schemas exposing customizable controls to the builders.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "plugin_id": "String",
  "plugin_version": "String",
  "concept_id": "String",
  "component_type": "String",
  "display_name": "String",
  "description": "String",
  "icon_path": "String",
  "composition": ["Object"],
  "properties": ["Object"],
  "input_ports": ["Object"],
  "output_ports": ["Object"],
  "widget_config": "Object",
  "preview_schema": "Object",
  "offline_support": "Boolean",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```
* **Indexes**:
  - `{"plugin_id": 1, "component_type": 1}` (Unique)

---

### 2.5 Form Collections

#### Collection: `form_templates`
Pre-packaged reusable form configurations.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId | null",
  "project_id": "ObjectId | null",
  "name": "String",
  "description": "String",
  "category": "String",
  "tags": ["String"],
  "is_system": "Boolean",
  "is_public": "Boolean",
  "schema": "Object",
  "usage_count": "Number",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "created_by": "ObjectId",
  "is_deleted": "Boolean",
  "deleted_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"category": 1}`
  - `{"org_id": 1}`

#### Collection: `form_responses`
Collected form responses from users.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "form_id": "ObjectId",
  "commit_id": "String",
  "org_id": "ObjectId",
  "project_id": "ObjectId",
  "respondent_id": "ObjectId | null",
  "respondent_email": "String | null",
  "session_id": "String | null",
  "status": "String (enum: submitted | draft)",
  "is_anonymous": "Boolean",
  "is_legacy": "Boolean",
  "submission_number": "Number",
  "answers": {
    "question_id": {
      "value": "Any",
      "display_value": "String",
      "file_ids": ["ObjectId"],
      "answered_at": "ISODate",
      "iteration_index": "Number"
    }
  },
  "repeat_groups": {
    "section_id": [
      {
        "iteration": "Number",
        "answers": "Object"
      }
    ]
  },
  "metadata": {
    "ip_address": "String | null",
    "user_agent": "String",
    "device_type": "String",
    "platform": "String",
    "started_at": "ISODate",
    "completed_at": "ISODate",
    "time_taken_seconds": "Number",
    "offline_submitted": "Boolean"
  },
  "edit_history": [
    {
      "edited_at": "ISODate",
      "edited_by": "ObjectId",
      "before": "Object",
      "after": "Object"
    }
  ],
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "submitted_at": "ISODate | null",
  "is_deleted": "Boolean",
  "deleted_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"form_id": 1, "submitted_at": -1}`
  - `{"respondent_id": 1}`
  - `{"org_id": 1}`

#### Collection: `response_drafts`
Temporary caches for incomplete submissions.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "form_id": "ObjectId",
  "commit_id": "String",
  "respondent_id": "ObjectId | null",
  "org_id": "ObjectId",
  "partial_answers": "Object",
  "last_saved_at": "ISODate",
  "expires_at": "ISODate",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```
* **Indexes**:
  - `{"form_id": 1, "respondent_id": 1}` (Unique)
  - `{"expires_at": 1}` (TTL index)

#### Collection: `file_uploads`
Uploaded attachments.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "form_id": "ObjectId",
  "response_id": "ObjectId | null",
  "question_id": "String",
  "original_filename": "String",
  "stored_filename": "String",
  "file_path": "String",
  "mime_type": "String",
  "file_size_bytes": "Number",
  "file_type": "String (enum: pdf | video | image | other)",
  "upload_status": "String (enum: pending | uploading | complete | failed)",
  "upload_offset": "Number",
  "checksum_sha256": "String | null",
  "virus_scan_status": "String (enum: pending | clean | infected)",
  "uploaded_by": "ObjectId",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "is_deleted": "Boolean",
  "deleted_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"org_id": 1}`
  - `{"form_id": 1}`
  - `{"response_id": 1}`

#### Collection: `edit_sessions`
Ephemeral indicators tracking co-editing presence.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "entity_type": "String (enum: form | analysis | dashboard)",
  "entity_id": "ObjectId",
  "user_id": "ObjectId",
  "org_id": "ObjectId",
  "started_at": "ISODate",
  "last_ping_at": "ISODate"
}
```
* **Indexes**:
  - `{"last_ping_at": 1}` (TTL index, e.g., 60s)

#### Collection: `pending_merges`
Tracks conflicts between parallel versioning changes.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "form_id": "ObjectId",
  "branch_name": "String",
  "base_commit_id": "String",
  "their_commit_id": "String",
  "our_changes": "Object",
  "conflict_fields": ["String"],
  "status": "String (enum: pending | resolved | abandoned)",
  "resolver_id": "ObjectId | null",
  "resolved_at": "ISODate | null",
  "created_at": "ISODate",
  "created_by": "ObjectId"
}
```
* **Indexes**:
  - `{"form_id": 1, "status": 1}`

---

### 2.6 Analysis Collections

#### Collection: `analyses`
Definitions of Directed Acyclic Graphs executing computations.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "project_id": "ObjectId",
  "name": "String",
  "description": "String",
  "linked_form_ids": ["ObjectId"],
  "execution_modes": ["String"],
  "schedule": "String | null",
  "reactive_debounce_ms": "Number",
  "graph": {
    "nodes": [
      {
        "id": "String",
        "type": "String",
        "position": { "x": "Number", "y": "Number" },
        "size": { "width": "Number", "height": "Number" },
        "properties": "Object",
        "label": "String",
        "is_disabled": "Boolean"
      }
    ],
    "edges": [
      {
        "id": "String",
        "from_node": "String",
        "from_port": "String",
        "to_node": "String",
        "to_port": "String",
        "label": "String | null"
      }
    ]
  },
  "last_run_id": "ObjectId | null",
  "status": "String (enum: idle | running | error)",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "created_by": "ObjectId",
  "is_deleted": "Boolean",
  "deleted_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"project_id": 1}`
  - `{"org_id": 1}`

#### Collection: `analysis_runs`
Historical execution runs of analyses.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "analysis_id": "ObjectId",
  "org_id": "ObjectId",
  "trigger": "String (enum: on_demand | scheduled | reactive | manual)",
  "triggered_by": "ObjectId | null",
  "status": "String (enum: queued | running | completed | failed | partial)",
  "started_at": "ISODate",
  "completed_at": "ISODate | null",
  "celery_task_id": "String | null",
  "node_statuses": {
    "node_id": {
      "status": "String",
      "started_at": "ISODate",
      "completed_at": "ISODate",
      "error": "String | null"
    }
  },
  "error_summary": "String | null",
  "result_ids": {
    "node_id": "ObjectId"
  },
  "created_at": "ISODate"
}
```
* **Indexes**:
  - `{"analysis_id": 1, "created_at": -1}`

#### Collection: `analysis_results`
Data cached output snapshots matching execute nodes.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "run_id": "ObjectId",
  "analysis_id": "ObjectId",
  "node_id": "String",
  "org_id": "ObjectId",
  "output_type": "String (enum: table | value | dataframe | chart_data | error)",
  "data": "Any",
  "row_count": "Number | null",
  "column_definitions": [
    {
      "name": "String",
      "type": "String",
      "label": "String"
    }
  ],
  "cached_until": "ISODate | null",
  "created_at": "ISODate"
}
```
* **Indexes**:
  - `{"run_id": 1}`
  - `{"analysis_id": 1, "node_id": 1}`

#### Collection: `analysis_exports`
CSV, Excel, or PDF document exports generated from results.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "analysis_id": "ObjectId",
  "run_id": "ObjectId",
  "org_id": "ObjectId",
  "format": "String (enum: csv | excel | pdf)",
  "node_ids": ["String"],
  "file_path": "String",
  "file_size_bytes": "Number",
  "status": "String (enum: queued | generating | ready | failed | expired)",
  "expires_at": "ISODate",
  "created_at": "ISODate",
  "created_by": "ObjectId"
}
```
* **Indexes**:
  - `{"expires_at": 1}` (TTL index, e.g., 7 days)

---

### 2.7 Dashboard Collections

#### Collection: `dashboard_snapshots`
Rendered snapshots.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "dashboard_id": "ObjectId",
  "org_id": "ObjectId",
  "data": "Object",
  "created_at": "ISODate"
}
```
* **Indexes**:
  - `{"dashboard_id": 1, "created_at": -1}`

---

### 2.8 Notification Collections

#### Collection: `notification_templates`
Jinja2 templates for SMS, Email, and in-app notices.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId | null",
  "name": "String",
  "event_type": "String",
  "channels": {
    "email": {
      "subject": "String",
      "body_html": "String",
      "body_text": "String"
    },
    "sms": {
      "message": "String"
    },
    "in_app": {
      "title": "String",
      "body": "String"
    }
  },
  "variables": [
    {
      "key": "String",
      "description": "String",
      "example": "String"
    }
  ],
  "is_system": "Boolean",
  "is_active": "Boolean",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "created_by": "ObjectId | null"
}
```
* **Indexes**:
  - `{"org_id": 1}`
  - `{"event_type": 1}`

#### Collection: `notification_rules`
Triggers checking event payloads to send alerts.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "project_id": "ObjectId | null",
  "form_id": "ObjectId | null",
  "name": "String",
  "event_type": "String",
  "trigger_conditions": ["Object"],
  "channels": ["String"],
  "recipient_type": "String (enum: form_owner | specific_users | role | group | respondent)",
  "recipient_ids": ["ObjectId"],
  "template_id": "ObjectId",
  "is_active": "Boolean",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "created_by": "ObjectId"
}
```
* **Indexes**:
  - `{"org_id": 1}`
  - `{"event_type": 1}`

#### Collection: `notification_log`
Dispatch log containing retry intervals.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "rule_id": "ObjectId",
  "org_id": "ObjectId",
  "event_type": "String",
  "recipient_id": "ObjectId",
  "channel": "String (enum: email | sms | in_app | push)",
  "status": "String (enum: queued | sent | failed | retrying)",
  "attempt_count": "Number",
  "max_attempts": "Number",
  "next_retry_at": "ISODate | null",
  "provider_response": "Object | null",
  "created_at": "ISODate",
  "last_attempt_at": "ISODate | null"
}
```
* **Indexes**:
  - `{"status": 1, "next_retry_at": 1}`
  - `{"org_id": 1}`

#### Collection: `webhook_configs`
Endpoints mapped to receive event streams.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "form_id": "ObjectId | null",
  "project_id": "ObjectId | null",
  "name": "String",
  "url": "String",
  "secret": "String",
  "events": ["String"],
  "is_active": "Boolean",
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "created_by": "ObjectId"
}
```
* **Indexes**:
  - `{"org_id": 1}`

#### Collection: `webhook_delivery_log`
Audit trials mapping callback runs.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "webhook_config_id": "ObjectId",
  "org_id": "ObjectId",
  "event_type": "String",
  "payload": "Object",
  "status": "String (enum: queued | delivered | failed | retrying)",
  "http_status_code": "Number | null",
  "response_body": "String | null",
  "attempt_count": "Number",
  "next_retry_at": "ISODate | null",
  "delivered_at": "ISODate | null",
  "created_at": "ISODate"
}
```
* **Indexes**:
  - `{"status": 1, "next_retry_at": 1}`

---

### 2.9 Compliance Collections

#### Collection: `compliance_standards`
Lists behaviors injected for GDPR, HIPAA, or ISO 27001.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "code": "String (unique)",
  "name": "String",
  "description": "String",
  "region": "String",
  "behavioral_constraints": [
    {
      "type": "String",
      "config": "Object"
    }
  ],
  "is_system": "Boolean",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```
* **Indexes**:
  - `{"code": 1}` (Unique)

#### Collection: `org_compliance`
Links organisations to adopted guidelines.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "compliance_id": "ObjectId",
  "adopted_at": "ISODate",
  "adopted_by": "ObjectId",
  "effective_from": "ISODate",
  "notes": "String | null"
}
```
* **Indexes**:
  - `{"org_id": 1, "compliance_id": 1}` (Unique)

---

### 2.10 Storage Collections

#### Collection: `storage_quotas`
Disk allocations tracked for each workspace.

* **Schema**:
```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId (unique)",
  "quota_bytes": "Number",
  "used_bytes": {
    "files": "Number",
    "database": "Number",
    "audit_logs": "Number",
    "total": "Number"
  },
  "warning_threshold": "Number",
  "last_calculated_at": "ISODate",
  "set_by": "ObjectId",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```
* **Indexes**:
  - `{"org_id": 1}` (Unique)
