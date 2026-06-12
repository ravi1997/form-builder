# Form Builder Platform - Database Models Documentation

This document provides comprehensive documentation for all MongoDB collections and their corresponding Pydantic models in the Form Builder Platform.

## Table of Contents

1. [Base Models](#base-models)
2. [System Collections](#system-collections)
3. [Identity & Access Collections](#identity--access-collections)
4. [Project Collections](#project-collections)
5. [Plugin & Concept Collections](#plugin--concept-collections)
6. [Form Collections](#form-collections)
7. [Analysis Collections](#analysis-collections)
8. [Dashboard Collections](#dashboard-collections)
9. [Notification Collections](#notification-collections)
10. [Compliance Collections](#compliance-collections)
11. [Storage Collections](#storage-collections)
12. [Common Patterns](#common-patterns)

---

## Base Models

### BaseDBModel
All collection models inherit from `BaseDBModel` which provides common fields:

```python
class BaseDBModel(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    org_id: Optional[PyObjectId] = Field(None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[PyObjectId] = Field(None)
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(None)
```

**Common Fields:**
- `_id`: MongoDB ObjectId (aliased as `id`)
- `org_id`: Organization ID, null for system-level documents
- `created_at`: Timestamp when document was created
- `updated_at`: Timestamp when document was last updated
- `created_by`: User ID who created the document
- `is_deleted`: Soft delete flag
- `deleted_at`: Timestamp when document was deleted (if soft-deleted)

**Common Methods:**
- `to_dict()`: Convert model to MongoDB-compatible dictionary
- `update_timestamp()`: Update the `updated_at` field
- `mark_deleted()`: Mark document as soft-deleted

---

## System Collections

### system_config
Stores system-wide configuration settings.

**Schema:**
```json
{
  "_id": ObjectId,
  "key": "platform_name",
  "value": "Form Builder Platform",
  "updated_at": ISODate,
  "updated_by": ObjectId
}
```

**Example Keys:**
- `platform_name`, `platform_version`
- `email_api_url`, `email_api_token`
- `sms_api_url`, `sms_api_token`
- `max_file_size_pdf`, `max_file_size_video`
- `maintenance_mode`, `registration_open`

### audit_logs
Append-only audit trail for all system actions.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": ObjectId,
  "project_id": ObjectId,
  "entity_type": "form",
  "entity_id": ObjectId,
  "action": "created",
  "actor_id": ObjectId,
  "actor_role": "org_admin",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "before": {},
  "after": {"name": "New Form"},
  "metadata": {},
  "timestamp": ISODate,
  "archived": false
}
```

**Indexes:**
- `org_id`: Filter by organization
- `entity_type + entity_id`: Find all actions on specific entity
- `actor_id`: Find all actions by specific user
- `timestamp`: Sort by time
- `archived`: Separate active from archived logs

---

## Identity & Access Collections

### users
Stores user accounts and profile information.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": null,
  "email": "user@example.com",
  "password_hash": "$2b$12$...",
  "full_name": "John Doe",
  "display_name": "John",
  "status": "active",
  "email_verified": true,
  "notification_preferences": {
    "email": true,
    "sms": true,
    "push": true,
    "in_app": true
  },
  "device_tokens": [
    {
      "token": "expo_push_token...",
      "platform": "ios",
      "created_at": ISODate
    }
  ],
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": ObjectId,
  "is_deleted": false,
  "deleted_at": null
}
```

### organisations
Stores organizational hierarchy and settings.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": null,
  "name": "AIIMS Hospital",
  "slug": "aiims-hospital",
  "description": "Primary healthcare institution",
  "parent_org_id": null,
  "org_type": "organisation",
  "status": "active",
  "settings": {
    "allow_public_forms": true,
    "default_form_theme": {...},
    "max_members": 100
  },
  "compliance_ids": [ObjectId],
  "storage_quota_bytes": 107374182400,
  "storage_used_bytes": 5368709120,
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": ObjectId,
  "is_deleted": false,
  "deleted_at": null
}
```

### org_memberships
Maps users to organizations with roles.

**Schema:**
```json
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "org_id": ObjectId,
  "role": "org_admin",
  "custom_permissions": ["custom_permission"],
  "status": "active",
  "invited_by": ObjectId,
  "joined_at": ISODate,
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": ObjectId,
  "is_deleted": false,
  "deleted_at": null
}
```

### groups
Defines user groups for permission management.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": ObjectId,
  "name": "Form Reviewers",
  "description": "Users who can review forms",
  "type": "static",
  "dynamic_rule": {
    "field": "role",
    "operator": "equals",
    "value": "org_editor"
  },
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": ObjectId,
  "is_deleted": false,
  "deleted_at": null
}
```

### invitations
Stores pending and accepted user invitations.

**Schema:**
```json
{
  "_id": ObjectId,
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "org_id": ObjectId,
  "project_id": ObjectId,
  "invited_by": ObjectId,
  "invited_email": "newuser@example.com",
  "role": "org_editor",
  "status": "pending",
  "expires_at": ISODate,
  "accepted_at": ISODate,
  "created_at": ISODate
}
```

---

## Project Collections

### projects
Containers for forms, analyses, and dashboards.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": ObjectId,
  "name": "Patient Feedback Survey",
  "description": "Collect patient satisfaction data",
  "slug": "patient-feedback-survey",
  "owner_org_id": ObjectId,
  "shared_org_ids": [ObjectId],
  "status": "active",
  "settings": {
    "default_form_theme": {...},
    "default_compliance_ids": [ObjectId],
    "notification_rules": [...],
    "default_language": "en"
  },
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": ObjectId,
  "is_deleted": false,
  "deleted_at": null
}
```

### project_members
Maps users to projects with roles.

**Schema:**
```json
{
  "_id": ObjectId,
  "project_id": ObjectId,
  "user_id": ObjectId,
  "org_id": ObjectId,
  "role": "project_owner",
  "invited_by": ObjectId,
  "joined_at": ISODate,
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": ObjectId,
  "is_deleted": false,
  "deleted_at": null
}
```

---

## Plugin & Concept Collections

### concept_registry
Defines available component concepts.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": null,
  "concept_id": "form_field",
  "name": "Form Field",
  "description": "Individual form field components",
  "builder_type": "form_builder",
  "supported_component_types": ["text_input", "dropdown"],
  "output_format": "json",
  "version_support": true,
  "collaboration_support": true,
  "is_system": true,
  "created_at": ISODate,
  "updated_at": ISODate
}
```

### plugins
Stores installed plugin information.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": null,
  "plugin_id": "advanced-calculator",
  "name": "Advanced Calculator",
  "description": "Complex mathematical calculations",
  "author": "Plugin Developer",
  "version": "1.0.0",
  "manifest": {...},
  "status": "active",
  "concept_targets": ["form_field"],
  "permissions": ["db_read_own_org"],
  "installed_at": ISODate,
  "installed_by": ObjectId,
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": ObjectId,
  "is_deleted": false,
  "deleted_at": null
}
```

### component_schemas
Defines individual component schemas.

**Schema:**
```json
{
  "_id": ObjectId,
  "plugin_id": ObjectId,
  "plugin_version": "1.0.0",
  "concept_id": "form_field",
  "component_type": "advanced_calculator",
  "display_name": "Advanced Calculator",
  "description": "Performs complex calculations",
  "composition": [...],
  "properties": [...],
  "input_ports": [...],
  "output_ports": [...],
  "offline_support": true,
  "created_at": ISODate,
  "updated_at": ISODate
}
```

---

## Form Collections

### forms
Stores form metadata with Git-like versioning.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": ObjectId,
  "project_id": ObjectId,
  "name": "Patient Intake Form",
  "description": "Initial patient information",
  "branches": {
    "main": "a1b2c3d4e5f6",
    "feature/new-questions": "b2c3d4e5f6a7"
  },
  "production_branch": "main",
  "tags": {
    "v1.0": "a1b2c3d4e5f6"
  },
  "template_id": ObjectId,
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": ObjectId,
  "is_deleted": false,
  "deleted_at": null
}
```

### form_commits
Stores form schema versions (Git-like commits).

**Schema:**
```json
{
  "_id": ObjectId,
  "form_id": ObjectId,
  "commit_id": "a1b2c3d4e5f6",
  "parent_ids": ["z9y8x7w6v5u4"],
  "author_id": ObjectId,
  "message": "Add patient demographics section",
  "branch": "main",
  "tag": "v1.0",
  "timestamp": ISODate,
  "schema": {
    "ui": {
      "theme": {...},
      "layout": "single_page",
      "cover_page": {...},
      "thank_you_page": {...}
    },
    "access": {
      "type": "public",
      "allowed_org_ids": [],
      "allow_anonymous": true
    },
    "settings": {
      "expires_at": ISODate,
      "allow_multiple_submissions": false,
      "response_edit_policy": "no_edit"
    },
    "sections": [...]
  }
}
```

### form_responses
Stores submitted form responses with complex structure.

**Schema:**
```json
{
  "_id": ObjectId,
  "form_id": ObjectId,
  "commit_id": "a1b2c3d4e5f6",
  "org_id": ObjectId,
  "project_id": ObjectId,
  "respondent_id": ObjectId,
  "respondent_email": "anonymous@example.com",
  "session_id": "sess_123456",
  "status": "submitted",
  "is_anonymous": false,
  "is_legacy": false,
  "submission_number": 42,
  "answers": {
    "name_123": {
      "value": "John Doe",
      "display_value": "John Doe",
      "file_ids": [],
      "answered_at": ISODate,
      "iteration_index": 0
    }
  },
  "repeat_groups": {
    "medications_456": [
      {
        "iteration": 0,
        "answers": {
          "medication_name_789": {
            "value": "Aspirin",
            "display_value": "Aspirin",
            "answered_at": ISODate
          }
        }
      }
    ]
  },
  "metadata": {
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "started_at": ISODate,
    "completed_at": ISODate,
    "time_taken_seconds": 125.5,
    "offline_submitted": false
  },
  "edit_history": [...],
  "submitted_at": ISODate,
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": ObjectId,
  "is_deleted": false,
  "deleted_at": null
}
```

---

## Analysis Collections

### analyses
Stores analysis pipeline definitions.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": ObjectId,
  "project_id": ObjectId,
  "name": "Patient Response Analysis",
  "description": "Analyze patient feedback data",
  "linked_form_ids": [ObjectId],
  "execution_modes": ["on_demand", "scheduled"],
  "schedule": "0 9 * * 1",  # Every Monday at 9 AM
  "reactive_debounce_ms": 1000,
  "graph": {
    "nodes": [...],
    "edges": [...]
  },
  "last_run_id": ObjectId,
  "status": "idle",
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": ObjectId,
  "is_deleted": false,
  "deleted_at": null
}
```

### analysis_runs
Stores individual analysis execution records.

**Schema:**
```json
{
  "_id": ObjectId,
  "analysis_id": ObjectId,
  "org_id": ObjectId,
  "trigger": "scheduled",
  "triggered_by": ObjectId,
  "status": "completed",
  "started_at": ISODate,
  "completed_at": ISODate,
  "celery_task_id": "celery_task_123",
  "node_statuses": {
    "node_1": {
      "status": "completed",
      "started_at": ISODate,
      "completed_at": ISODate
    }
  },
  "error_summary": null,
  "result_ids": {
    "node_1": ObjectId
  },
  "created_at": ISODate
}
```

---

## Dashboard Collections

### dashboards
Stores dashboard configurations.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": ObjectId,
  "project_id": ObjectId,
  "name": "Patient Analytics Dashboard",
  "description": "Overview of patient metrics",
  "is_public": false,
  "public_token": "pub_token_123",
  "canvas": {
    "width": 1200,
    "height": 800,
    "background_color": "#FFFFFF",
    "widgets": [...]
  },
  "settings": {
    "auto_refresh": true,
    "refresh_interval_seconds": 300,
    "theme": {...}
  },
  "linked_analysis_ids": [ObjectId],
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": ObjectId,
  "is_deleted": false,
  "deleted_at": null
}
```

---

## Notification Collections

### notification_templates
Stores reusable notification templates.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": null,
  "name": "Form Submission Alert",
  "event_type": "response.submitted",
  "channels": {
    "email": {
      "subject": "New form submission received",
      "body_html": "<p>...</p>",
      "body_text": "..."
    },
    "sms": {
      "message": "New form submission received"
    },
    "in_app": {
      "title": "New Submission",
      "body": "A new form has been submitted"
    }
  },
  "variables": [...],
  "is_system": true,
  "is_active": true,
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": ObjectId,
  "is_deleted": false,
  "deleted_at": null
}
```

---

## Compliance Collections

### compliance_standards
Defines available compliance frameworks.

**Schema:**
```json
{
  "_id": ObjectId,
  "code": "GDPR",
  "name": "General Data Protection Regulation",
  "description": "EU data protection regulation",
  "region": "EU",
  "behavioral_constraints": [...],
  "is_system": true,
  "created_at": ISODate,
  "updated_at": ISODate,
  "created_by": null
}
```

### org_compliance
Maps organizations to compliance standards.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": ObjectId,
  "compliance_id": ObjectId,
  "adopted_at": ISODate,
  "adopted_by": ObjectId,
  "effective_from": ISODate,
  "notes": "GDPR compliance for EU operations"
}
```

---

## Storage Collections

### storage_quotas
Manages storage quotas per organization.

**Schema:**
```json
{
  "_id": ObjectId,
  "org_id": ObjectId,
  "quota_bytes": 107374182400,  // 100 GB
  "used_bytes": {
    "files": 3221225472,       // 3 GB
    "database": 1073741824,     // 1 GB
    "audit_logs": 536870912,    // 512 MB
    "total": 4831838208         // 4.5 GB
  },
  "warning_threshold": 0.8,
  "last_calculated_at": ISODate,
  "set_by": ObjectId,
  "created_at": ISODate,
  "updated_at": ISODate
}
```

---

## Common Patterns

### Soft Delete Pattern
All collections (except `audit_logs`) implement soft delete:
```json
{
  "is_deleted": false,
  "deleted_at": null
}
```

When deleting, set:
```json
{
  "is_deleted": true,
  "deleted_at": "2024-01-01T00:00:00Z"
}
```

### Organization Scoping
Most documents include an `org_id` field for multi-tenancy:
- `null`: System-level document
- `ObjectId`: Organization-specific document

### Timestamp Pattern
All documents include timestamps:
```json
{
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### User Tracking
Most documents track who created them:
```json
{
  "created_by": ObjectId("...")
}
```

### Status Fields
Many collections include status fields for workflow management:
- `status`: "active", "pending", "suspended", etc.
- `is_active`: Boolean flag
- `is_deleted`: Soft delete flag

### TTL Indexes
Several collections use Time-To-Live indexes for automatic cleanup:
- `invitations.expires_at`: 30 days
- `response_drafts.expires_at`: 30 days
- `edit_sessions.last_ping_at`: 60 seconds
- `analysis_exports.expires_at`: 7 days

### Index Strategy
Collections are indexed for common query patterns:
- Foreign key relationships (`org_id`, `user_id`, etc.)
- Status fields (`status`, `is_deleted`)
- Time-based queries (`created_at`, `updated_at`)
- Unique constraints (`email`, `slug`, etc.)
- TTL fields (`expires_at`)