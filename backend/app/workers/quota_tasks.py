import os
from bson import ObjectId

from app.services.quota_service import calculate_organization_quota

# Get Celery app from shared config
from .celery_config import get_celery_app
celery_app = get_celery_app()


@celery_app.task(name="app.workers.quota_tasks.calculate_organization_quota_task")
def calculate_organization_quota_task(org_id):
    return calculate_organization_quota(ObjectId(org_id) if ObjectId.is_valid(org_id) else org_id)
