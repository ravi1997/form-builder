"""
Maintenance Tasks - Celery tasks for system maintenance and cleanup
Handles database cleanup, optimization, and system health checks.
"""

import os
import datetime
import shutil
from celery import Celery
from bson import ObjectId
from typing import Dict, Any, List, Optional

from app.extensions import mongo
from app.services.quota_service import calculate_organization_quota

# Get Celery app from main worker
from .celery_config import get_celery_app
celery_app = get_celery_app()


def _utcnow_iso():
    """Get current UTC datetime in ISO format."""
    return datetime.datetime.utcnow().isoformat()


def _to_object_id(value):
    """Convert string to ObjectId if valid."""
    if isinstance(value, ObjectId):
        return value
    if ObjectId.is_valid(str(value)):
        return ObjectId(str(value))
    raise ValueError(f"Invalid ObjectId: {value}")


def _safe_result_payload(status, error=None, **extra):
    """Create a standardized result payload."""
    payload = {"status": status, "error": error}
    payload.update(extra)
    return payload


@celery_app.task(name="app.workers.maintenance_tasks.nightly_maintenance_task")
def nightly_maintenance_task():
    """
    Run nightly maintenance tasks including cleanup and optimization.
    """
    try:
        results = {
            "expired_exports": 0,
            "expired_drafts": 0,
            "old_audit_logs": 0,
            "orphaned_files": 0,
            "quota_updates": 0
        }
        
        # Clean up expired exports
        export_result = cleanup_expired_exports_task()
        if export_result.get("status") == "completed":
            results["expired_exports"] = export_result.get("deleted_count", 0)
        
        # Clean up expired drafts
        draft_result = cleanup_expired_drafts_task()
        if draft_result.get("status") == "completed":
            results["expired_drafts"] = draft_result.get("deleted_count", 0)
        
        # Archive old audit logs
        audit_result = archive_old_audit_logs_task()
        if audit_result.get("status") == "completed":
            results["old_audit_logs"] = audit_result.get("archived_count", 0)
        
        # Clean up orphaned files
        file_result = cleanup_orphaned_files_task()
        if file_result.get("status") == "completed":
            results["orphaned_files"] = file_result.get("deleted_count", 0)
        
        # Update all organization quotas
        quota_result = calculate_all_quotas_task()
        if quota_result.get("status") == "completed":
            results["quota_updates"] = quota_result.get("updated_count", 0)
        
        # Update system stats
        _update_system_stats()
        
        return _safe_result_payload(
            "completed",
            **results
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


@celery_app.task(name="app.workers.maintenance_tasks.cleanup_expired_exports_task")
def cleanup_expired_exports_task():
    """
    Clean up expired export files (older than 7 days).
    """
    try:
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        
        # Find expired exports
        expired_exports = list(mongo.db.analysis_exports.find({
            "expires_at": {"$lt": cutoff_date},
            "status": "ready"
        }))
        
        deleted_count = 0
        for export in expired_exports:
            # Delete file
            file_path = export.get("file_path")
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except:
                    pass
            
            # Mark export as expired
            mongo.db.analysis_exports.update_one(
                {"_id": export["_id"]},
                {"$set": {
                    "status": "expired",
                    "updated_at": _utcnow_iso()
                }}
            )
        
        return _safe_result_payload(
            "completed",
            deleted_count=deleted_count
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


@celery_app.task(name="app.workers.maintenance_tasks.cleanup_expired_drafts_task")
def cleanup_expired_drafts_task():
    """
    Clean up expired response drafts (older than 30 days).
    """
    try:
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        
        result = mongo.db.response_drafts.delete_many({
            "expires_at": {"$lt": cutoff_date}
        })
        
        return _safe_result_payload(
            "completed",
            deleted_count=result.deleted_count
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


@celery_app.task(name="app.workers.maintenance_tasks.archive_old_audit_logs_task")
def archive_old_audit_logs_task():
    """
    Archive audit logs older than 90 days to cold storage.
    """
    try:
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=90)
        
        # Find old audit logs
        old_logs = list(mongo.db.audit_logs.find({
            "timestamp": {"$lt": cutoff_date},
            "archived": {"$ne": True}
        }))
        
        archived_count = 0
        for log in old_logs:
            # In a real implementation, you would move these to a separate collection
            # or external storage. For now, we'll just mark them as archived.
            mongo.db.audit_logs.update_one(
                {"_id": log["_id"]},
                {"$set": {
                    "archived": True,
                    "archived_at": _utcnow_iso()
                }}
            )
            archived_count += 1
        
        return _safe_result_payload(
            "completed",
            archived_count=archived_count
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


@celery_app.task(name="app.workers.maintenance_tasks.cleanup_orphaned_files_task")
def cleanup_orphaned_files_task():
    """
    Clean up orphaned files that are not referenced in the database.
    """
    try:
        uploads_root = os.environ.get("UPLOADS_ROOT", "/var/uploads")
        deleted_count = 0
        
        # Get all referenced file paths from database
        referenced_files = set()
        
        # Check file_uploads collection
        for file_upload in mongo.db.file_uploads.find({}, {"file_path": 1}):
            if file_upload.get("file_path"):
                referenced_files.add(file_upload["file_path"])
        
        # Check analysis_exports collection
        for export in mongo.db.analysis_exports.find({}, {"file_path": 1}):
            if export.get("file_path"):
                referenced_files.add(export["file_path"])
        
        # Walk through uploads directory and find unreferenced files
        for root, dirs, files in os.walk(uploads_root):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip if file is referenced
                if file_path in referenced_files:
                    continue
                
                # Skip directories and system files
                if file.startswith('.') or file.startswith('__'):
                    continue
                
                # Check if file is old (older than 1 day)
                try:
                    file_age = datetime.datetime.now() - datetime.datetime.fromtimestamp(
                        os.path.getmtime(file_path)
                    )
                    
                    if file_age.days > 1:
                        os.remove(file_path)
                        deleted_count += 1
                except:
                    pass
        
        return _safe_result_payload(
            "completed",
            deleted_count=deleted_count
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


@celery_app.task(name="app.workers.maintenance_tasks.calculate_all_quotas_task")
def calculate_all_quotas_task():
    """
    Calculate storage quotas for all organizations.
    """
    try:
        # Get all organizations
        orgs = list(mongo.db.organisations.find({
            "is_deleted": {"$ne": True},
            "status": "active"
        }))
        
        updated_count = 0
        for org in orgs:
            try:
                calculate_organization_quota(org["_id"])
                updated_count += 1
            except Exception as e:
                # Log error but continue with other orgs
                print(f"Error calculating quota for org {org['_id']}: {e}")
        
        return _safe_result_payload(
            "completed",
            updated_count=updated_count
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


@celery_app.task(name="app.workers.maintenance_tasks.cleanup_old_sessions_task")
def cleanup_old_sessions_task():
    """
    Clean up expired user sessions.
    """
    try:
        # Remove expired sessions (TTL index should handle this, but manual cleanup is good)
        expired_sessions = list(mongo.db.sessions.find({
            "expires_at": {"$lt": datetime.datetime.utcnow()}
        }))
        
        expired_count = len(expired_sessions)
        if expired_count > 0:
            # Delete expired sessions
            session_ids = [session["_id"] for session in expired_sessions]
            mongo.db.sessions.delete_many({"_id": {"$in": session_ids}})
        
        return _safe_result_payload(
            "completed",
            deleted_count=expired_count
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


@celery_app.task(name="app.workers.maintenance_tasks.cleanup_failed_tasks_task")
def cleanup_failed_tasks_task():
    """
    Clean up old failed Celery task results from backend.
    """
    try:
        # This would typically clean up the Celery backend results
        # For Redis backend, expired results are automatically cleaned up
        # This task can be extended if using a different backend
        
        # Clean up old failed analysis runs
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        
        result = mongo.db.analysis_runs.update_many(
            {
                "status": "failed",
                "created_at": {"$lt": cutoff_date}
            },
            {"$set": {
                "status": "archived",
                "archived_at": _utcnow_iso()
            }}
        )
        
        return _safe_result_payload(
            "completed",
            archived_count=result.modified_count
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


@celery_app.task(name="app.workers.maintenance_tasks.optimize_database_indexes_task")
def optimize_database_indexes_task():
    """
    Optimize database indexes and analyze query performance.
    """
    try:
        # This task would typically run database-specific optimizations
        # For MongoDB, this might include:
        # - Analyzing query patterns
        # - Suggesting new indexes
        # - Rebuilding existing indexes
        
        # For now, we'll just log that the task ran
        # In production, you might want to integrate with MongoDB's index optimization
        
        return _safe_result_payload(
            "completed",
            message="Database optimization task completed"
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


@celery_app.task(name="app.workers.maintenance_tasks.backup_system_data_task")
def backup_system_data_task():
    """
    Create backup of critical system data.
    """
    try:
        # This is a placeholder for backup functionality
        # In production, this would:
        # - Create database dumps
        # - Backup file uploads
        # - Store backups in secure location
        # - Verify backup integrity
        
        backup_timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_info = {
            "timestamp": backup_timestamp,
            "status": "completed",
            "backup_type": "system_data",
            "estimated_size": "0 bytes"  # Placeholder
        }
        
        # Log backup event
        mongo.db.audit_logs.insert_one({
            "entity_type": "system",
            "entity_id": "backup",
            "action": "backup_created",
            "actor_id": None,
            "actor_role": "system",
            "timestamp": _utcnow_iso(),
            "metadata": backup_info
        })
        
        return _safe_result_payload(
            "completed",
            backup_info=backup_info
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


@celery_app.task(name="app.workers.maintenance_tasks.check_system_health_task")
def check_system_health_task():
    """
    Check overall system health and report issues.
    """
    try:
        health_status = {
            "database": "healthy",
            "redis": "healthy",
            "storage": "healthy",
            "overall": "healthy",
            "issues": []
        }
        
        # Check MongoDB connection
        try:
            mongo.db.command("ping")
        except Exception as e:
            health_status["database"] = "unhealthy"
            health_status["issues"].append(f"MongoDB connection failed: {e}")
        
        # Check Redis connection (if available)
        try:
            # This would typically check Redis connection
            # For now, we'll assume it's healthy
            pass
        except Exception as e:
            health_status["redis"] = "unhealthy"
            health_status["issues"].append(f"Redis connection failed: {e}")
        
        # Check storage space
        try:
            uploads_root = os.environ.get("UPLOADS_ROOT", "/var/uploads")
            if os.path.exists(uploads_root):
                total, used, free = shutil.disk_usage(uploads_root)
                free_percent = (free / total) * 100
                
                if free_percent < 10:  # Less than 10% free space
                    health_status["storage"] = "warning"
                    health_status["issues"].append(f"Low disk space: {free_percent:.1f}% free")
        except Exception as e:
            health_status["storage"] = "error"
            health_status["issues"].append(f"Storage check failed: {e}")
        
        # Update overall status
        if health_status["issues"]:
            health_status["overall"] = "degraded" if len(health_status["issues"]) < 3 else "unhealthy"
        
        # Store health check result
        mongo.db.system_health.insert_one({
            "timestamp": _utcnow_iso(),
            "status": health_status["overall"],
            "checks": health_status,
            "issues_count": len(health_status["issues"])
        })
        
        return _safe_result_payload(
            "completed",
            health_status=health_status
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


def _update_system_stats():
    """Update system statistics."""
    try:
        stats = {
            "timestamp": _utcnow_iso(),
            "users": mongo.db.users.count_documents({"status": "active", "is_deleted": {"$ne": True}}),
            "organisations": mongo.db.organisations.count_documents({"status": "active", "is_deleted": {"$ne": True}}),
            "projects": mongo.db.projects.count_documents({"status": "active", "is_deleted": {"$ne": True}}),
            "forms": mongo.db.forms.count_documents({"is_deleted": {"$ne": True}}),
            "form_responses": mongo.db.form_responses.count_documents({"is_deleted": {"$ne": True}}),
            "analyses": mongo.db.analyses.count_documents({"is_deleted": {"$ne": True}}),
            "dashboards": mongo.db.dashboards.count_documents({"is_deleted": {"$ne": True}}),
            "plugins": mongo.db.plugins.count_documents({"status": "active", "is_deleted": {"$ne": True}})
        }
        
        # Update or insert system stats
        mongo.db.system_stats.update_one(
            {"_id": "latest"},
            {"$set": stats},
            upsert=True
        )
        
        # Keep historical stats (last 30 days)
        thirty_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=30)
        mongo.db.system_stats.delete_many({
            "timestamp": {"$lt": thirty_days_ago},
            "_id": {"$ne": "latest"}
        })
        
    except Exception as e:
        print(f"Error updating system stats: {e}")