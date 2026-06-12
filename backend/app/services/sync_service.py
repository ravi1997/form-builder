import datetime
from bson import ObjectId

from app.extensions import mongo


def _parse_watermark(last_synced_at):
    if not last_synced_at:
        return None

    if isinstance(last_synced_at, datetime.datetime):
        return last_synced_at

    if isinstance(last_synced_at, str):
        try:
            return datetime.datetime.fromisoformat(last_synced_at.replace("Z", "+00:00"))
        except ValueError:
            return None

    return None


def _serialize_form(form_doc):
    schema = form_doc.get("schema") or {}
    return {
        "id": str(form_doc["_id"]),
        "orgId": str(form_doc.get("org_id")) if form_doc.get("org_id") is not None else None,
        "projectId": str(form_doc.get("project_id"))
        if form_doc.get("project_id") is not None
        else None,
        "name": form_doc.get("name", ""),
        "description": form_doc.get("description", ""),
        "schemaJson": schema,
        "lastSyncedAt": (
            form_doc.get("updated_at").isoformat()
            if isinstance(form_doc.get("updated_at"), datetime.datetime)
            else form_doc.get("updated_at")
        ),
    }


def get_sync_delta(last_synced_at=None):
    watermark = _parse_watermark(last_synced_at)

    form_query = {"is_deleted": False}
    tombstone_query = {}

    if watermark is not None:
        form_query["updated_at"] = {"$gt": watermark}
        tombstone_query["deleted_at"] = {"$gt": watermark}

    updated = []
    for form_doc in mongo.db.forms.find(form_query).sort("updated_at", 1):
        updated.append(_serialize_form(form_doc))

    tombstones = []
    for tomb_doc in mongo.db.tombstones.find(tombstone_query).sort("deleted_at", 1):
        tombstones.append(
            {
                "entity_type": tomb_doc.get("entity_type"),
                "entity_id": str(tomb_doc.get("entity_id")),
                "deleted_at": (
                    tomb_doc.get("deleted_at").isoformat()
                    if isinstance(tomb_doc.get("deleted_at"), datetime.datetime)
                    else tomb_doc.get("deleted_at")
                ),
            }
        )

    server_synced_at = datetime.datetime.utcnow().isoformat() + "Z"
    return {
        "updated": updated,
        "tombstones": tombstones,
        "server_synced_at": server_synced_at,
    }
