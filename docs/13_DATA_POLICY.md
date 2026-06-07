# 13 — Data Policy

This document outlines structural compliance patterns, data deletion scopes, retention logic, and tenant resource allocations.

---

## 1. Compliance Settings & Enforcements

The platform supports tenant-level adoption of regulatory standards (GDPR, HIPAA):

| Standard | System Action / Behavioural Changes |
|---|---|
| **GDPR** | - Injects explicit consent checkboxes before response submission.<br>- Encrypts respondent IP addresses.<br>- Runs weekly automated deletion tasks for records exceeding organization retention ceilings. |
| **HIPAA** | - Forces TLS 1.3 connectivity on all API endpoints.<br>- Records all data access events in `audit_logs` (read-actions included).<br>- Requires click-through BAA agreements for administrators. |

---

## 2. Quota Management

Celery executes a daily task to compile disk and database footprints:
```python
def calculate_organization_quota(org_id: ObjectId):
    db_size = db.command("dbstats")["dataSize"] # Filtered per organization namespace size
    file_size = get_directory_size(f"uploads/{org_id}/")
    
    db.storage_quotas.update_one(
        {"org_id": org_id},
        {"$set": {
            "used_bytes.files": file_size,
            "used_bytes.database": db_size,
            "used_bytes.total": file_size + db_size,
            "last_calculated_at": datetime.utcnow()
        }}
    )
```
When `used_bytes.total > quota_bytes * warning_threshold`, administrators receive a notification. If `used_bytes.total >= quota_bytes`, file uploads and form creations are blocked.

---

## 3. Organization Deletion Cascades

When an organization is flagged for deletion:
1. State changes to `is_deleted = True` and sets a 30-day recovery grace period.
2. During this grace period, all API keys are revoked, and login attempts are blocked.
3. After 30 days, a Celery job runs a complete deletion sweep:
   - Removes all records in `forms`, `form_commits`, `form_responses`, `analyses`, `dashboards`.
   - Deletes files located under `/uploads/{org_id}/` on the disk storage volume.
   - Clears index definitions matching `org_id` from Elasticsearch.
   - The organization record itself is permanently deleted.
