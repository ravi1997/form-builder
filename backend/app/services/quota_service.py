import os
from datetime import datetime, timezone

from bson import ObjectId

from app.extensions import mongo


def _oid(value):
    if isinstance(value, ObjectId):
        return value
    if ObjectId.is_valid(str(value)):
        return ObjectId(str(value))
    return value


def get_directory_size(path):
    total = 0
    if not os.path.exists(path):
        return 0
    for root, _, files in os.walk(path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            try:
                total += os.path.getsize(file_path)
            except OSError:
                continue
    return total


def get_storage_quota(org_id):
    return mongo.db.storage_quotas.find_one({"org_id": _oid(org_id)})


def calculate_organization_quota(org_id):
    org_oid = _oid(org_id)
    db_stats = mongo.db.command("dbstats")
    file_size = get_directory_size(f"uploads/{org_oid}/")
    total = file_size + int(db_stats.get("dataSize", 0))
    doc = {
        "org_id": org_oid,
        "used_bytes": {
            "files": file_size,
            "database": int(db_stats.get("dataSize", 0)),
            "total": total,
        },
        "quota_bytes": get_storage_quota(org_oid).get("quota_bytes", 0) if get_storage_quota(org_oid) else 0,
        "warning_threshold": get_storage_quota(org_oid).get("warning_threshold", 0.8) if get_storage_quota(org_oid) else 0.8,
        "last_calculated_at": datetime.now(timezone.utc),
    }
    mongo.db.storage_quotas.update_one({"org_id": org_oid}, {"$set": doc}, upsert=True)
    return doc


def enforce_org_quota(org_id, requested_bytes=0):
    quota_doc = get_storage_quota(org_id)
    if not quota_doc:
        return
    used = quota_doc.get("used_bytes", {}).get("total", 0)
    quota_bytes = quota_doc.get("quota_bytes", 0)
    if quota_bytes and used + requested_bytes >= quota_bytes:
        raise ValueError("Organization quota exceeded")

