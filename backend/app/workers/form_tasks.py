from celery import Celery
from datetime import datetime, timedelta
from bson import ObjectId
from app.extensions import mongo, celery
from app.services.form_service import FormService
from app.services.notification_service import NotificationService
from app.services.audit_service import AuditService
import logging

logger = logging.getLogger(__name__)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def async_form_publish(self, form_id, branch_name, user_id, message=None):
    """Asynchronously publish a form branch to production."""
    try:
        result = FormService.publish_form_branch(
            form_id=form_id,
            publish_data={"branch_name": branch_name, "message": message},
            user_id=user_id
        )
        
        # Log audit event
        AuditService.log_event(
            org_id=result.get("org_id"),
            entity_type="form",
            entity_id=ObjectId(form_id),
            action="publish",
            actor_id=ObjectId(user_id),
            metadata={
                "branch_name": branch_name,
                "commit_id": result.get("publication", {}).get("commit_id"),
                "message": message
            }
        )
        
        # Send notification to form stakeholders
        NotificationService.send_form_published_notification(
            form_id=form_id,
            branch_name=branch_name,
            published_by=user_id
        )
        
        return {
            "status": "success",
            "form_id": form_id,
            "branch_name": branch_name,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Failed to publish form {form_id} branch {branch_name}: {str(e)}")
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def async_form_merge(self, form_id, source_branch, target_branch, user_id, message=None):
    """Asynchronously merge form branches."""
    try:
        result = FormService.merge_form_branches(
            form_id=form_id,
            merge_data={"source_branch": source_branch, "target_branch": target_branch, "message": message},
            user_id=user_id
        )
        
        # Log audit event
        AuditService.log_event(
            org_id=result.get("org_id"),
            entity_type="form",
            entity_id=ObjectId(form_id),
            action="merge",
            actor_id=ObjectId(user_id),
            metadata={
                "source_branch": source_branch,
                "target_branch": target_branch,
                "result": result.get("result", {}).get("status"),
                "conflict_fields": result.get("result", {}).get("conflict_fields", [])
            }
        )
        
        # If merge conflicts detected, send notification
        if result.get("result", {}).get("status") == "conflict":
            NotificationService.send_merge_conflict_notification(
                form_id=form_id,
                source_branch=source_branch,
                target_branch=target_branch,
                conflict_fields=result.get("result", {}).get("conflict_fields", []),
                pending_merge_id=result.get("result", {}).get("pending_merge_id")
            )
        
        return {
            "status": "success",
            "form_id": form_id,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Failed to merge form {form_id} branches {source_branch} -> {target_branch}: {str(e)}")
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def async_form_cleanup(self, form_id):
    """Clean up old form commits and maintain storage quotas."""
    try:
        # Get form details
        form = mongo.db.forms.find_one({
            "_id": ObjectId(form_id),
            "is_deleted": False
        })
        
        if not form:
            logger.warning(f"Form {form_id} not found for cleanup")
            return {"status": "skipped", "reason": "Form not found"}
        
        # Find commits older than 90 days that are not on any branch or tag
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        # Get all active commit IDs (current branch heads and tagged commits)
        active_commit_ids = set()
        
        # Add branch head commits
        for branch_name, commit_id in form.get("branches", {}).items():
            active_commit_ids.add(commit_id)
        
        # Add tagged commits
        for tag_name, commit_id in form.get("tags", {}).items():
            active_commit_ids.add(commit_id)
        
        # Find old commits not in active set
        old_commits = mongo.db.form_commits.find({
            "form_id": ObjectId(form_id),
            "timestamp": {"$lt": cutoff_date},
            "commit_id": {"$nin": list(active_commit_ids)}
        })
        
        deleted_count = 0
        for commit in old_commits:
            # Check if this commit is referenced by any responses
            response_count = mongo.db.form_responses.count_documents({
                "form_id": ObjectId(form_id),
                "commit_id": commit["commit_id"]
            })
            
            if response_count == 0:
                # Safe to delete
                mongo.db.form_commits.delete_one({"_id": commit["_id"]})
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old commits for form {form_id}")
        
        return {
            "status": "success",
            "form_id": form_id,
            "deleted_commits": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Failed to cleanup form {form_id}: {str(e)}")
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def async_form_template_usage_update(self, template_id):
    """Update template usage statistics."""
    try:
        # Count forms using this template
        usage_count = mongo.db.forms.count_documents({
            "template_id": ObjectId(template_id),
            "is_deleted": False
        })
        
        # Update template
        mongo.db.form_templates.update_one(
            {"_id": ObjectId(template_id)},
            {"$set": {"usage_count": usage_count, "updated_at": datetime.utcnow()}}
        )
        
        return {
            "status": "success",
            "template_id": template_id,
            "usage_count": usage_count
        }
        
    except Exception as e:
        logger.error(f"Failed to update template usage for {template_id}: {str(e)}")
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def async_form_response_migration(self, form_id, old_commit_id, new_commit_id):
    """Migrate form responses from old commit to new commit."""
    try:
        # Find responses with old commit ID
        responses = mongo.db.form_responses.find({
            "form_id": ObjectId(form_id),
            "commit_id": old_commit_id,
            "is_deleted": False
        })
        
        migrated_count = 0
        for response in responses:
            # Update response to new commit
            mongo.db.form_responses.update_one(
                {"_id": response["_id"]},
                {
                    "$set": {
                        "commit_id": new_commit_id,
                        "is_legacy": True,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            migrated_count += 1
        
        logger.info(f"Migrated {migrated_count} responses for form {form_id} from {old_commit_id} to {new_commit_id}")
        
        return {
            "status": "success",
            "form_id": form_id,
            "old_commit_id": old_commit_id,
            "new_commit_id": new_commit_id,
            "migrated_responses": migrated_count
        }
        
    except Exception as e:
        logger.error(f"Failed to migrate responses for form {form_id}: {str(e)}")
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def async_form_backup(self, form_id, backup_type="full"):
    """Create a backup of form data."""
    try:
        form = mongo.db.forms.find_one({
            "_id": ObjectId(form_id),
            "is_deleted": False
        })
        
        if not form:
            logger.warning(f"Form {form_id} not found for backup")
            return {"status": "skipped", "reason": "Form not found"}
        
        backup_data = {
            "form_id": form_id,
            "backup_type": backup_type,
            "created_at": datetime.utcnow(),
            "form_data": form,
            "commits": []
        }
        
        if backup_type == "full":
            # Include all commits
            commits = mongo.db.form_commits.find({
                "form_id": ObjectId(form_id)
            })
            backup_data["commits"] = list(commits)
        
        elif backup_type == "production":
            # Include only production branch commits
            production_branch = form.get("production_branch", "main")
            production_commit_id = form.get("branches", {}).get(production_branch)
            
            if production_commit_id:
                production_commit = mongo.db.form_commits.find_one({
                    "form_id": ObjectId(form_id),
                    "commit_id": production_commit_id
                })
                if production_commit:
                    backup_data["commits"] = [production_commit]
        
        # Store backup in separate collection
        mongo.db.form_backups.insert_one(backup_data)
        
        logger.info(f"Created {backup_type} backup for form {form_id}")
        
        return {
            "status": "success",
            "form_id": form_id,
            "backup_type": backup_type,
            "commits_count": len(backup_data["commits"])
        }
        
    except Exception as e:
        logger.error(f"Failed to create backup for form {form_id}: {str(e)}")
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def async_form_restore(self, form_id, backup_id, restore_type="schema"):
    """Restore form from backup."""
    try:
        # Get backup data
        backup = mongo.db.form_backups.find_one({
            "_id": ObjectId(backup_id),
            "form_id": ObjectId(form_id)
        })
        
        if not backup:
            logger.warning(f"Backup {backup_id} not found for form {form_id}")
            return {"status": "skipped", "reason": "Backup not found"}
        
        if restore_type == "schema":
            # Restore form schema from backup
            if backup["commits"]:
                # Use the latest commit from backup
                latest_commit = max(backup["commits"], key=lambda x: x["timestamp"])
                
                # Create new commit with restored schema
                FormService.update_form_schema(
                    form_id=form_id,
                    schema=latest_commit["schema"],
                    user_id=backup["form_data"]["created_by"],
                    message=f"Restore from backup (commit: {latest_commit['commit_id']})"
                )
        
        elif restore_type == "full":
            # Full restore (more complex, requires careful handling)
            # This would need to restore the entire form structure
            logger.warning(f"Full restore not implemented for form {form_id}")
            return {"status": "skipped", "reason": "Full restore not implemented"}
        
        logger.info(f"Restored form {form_id} from backup {backup_id}")
        
        return {
            "status": "success",
            "form_id": form_id,
            "backup_id": backup_id,
            "restore_type": restore_type
        }
        
    except Exception as e:
        logger.error(f"Failed to restore form {form_id} from backup {backup_id}: {str(e)}")
        raise self.retry(exc=e)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def async_form_quota_check(self, org_id):
    """Check and enforce form quotas for an organization."""
    try:
        # Get organization details
        org = mongo.db.organisations.find_one({
            "_id": ObjectId(org_id),
            "is_deleted": False
        })
        
        if not org:
            logger.warning(f"Organization {org_id} not found for quota check")
            return {"status": "skipped", "reason": "Organization not found"}
        
        # Count forms
        form_count = mongo.db.forms.count_documents({
            "org_id": ObjectId(org_id),
            "is_deleted": False
        })
        
        # Check against quota
        max_forms = org.get("settings", {}).get("max_forms", 100)
        
        if form_count > max_forms:
            logger.warning(f"Organization {org_id} exceeded form quota: {form_count}/{max_forms}")
            
            # Send notification to org admins
            NotificationService.send_quota_exceeded_notification(
                org_id=org_id,
                resource_type="forms",
                current_count=form_count,
                max_count=max_forms
            )
        
        return {
            "status": "success",
            "org_id": org_id,
            "form_count": form_count,
            "max_forms": max_forms,
            "within_quota": form_count <= max_forms
        }
        
    except Exception as e:
        logger.error(f"Failed to check form quota for org {org_id}: {str(e)}")
        raise self.retry(exc=e)


# Scheduled tasks

@celery.task
def scheduled_form_cleanup():
    """Scheduled task to clean up old form commits across all organizations."""
    try:
        # Find all forms
        forms = mongo.db.forms.find({"is_deleted": False})
        
        total_cleaned = 0
        for form in forms:
            try:
                result = async_form_cleanup.delay(str(form["_id"]))
                total_cleaned += 1
            except Exception as e:
                logger.error(f"Failed to schedule cleanup for form {form['_id']}: {str(e)}")
        
        logger.info(f"Scheduled cleanup for {total_cleaned} forms")
        return {"status": "success", "forms_scheduled": total_cleaned}
        
    except Exception as e:
        logger.error(f"Failed to schedule form cleanup: {str(e)}")
        return {"status": "error", "error": str(e)}


@celery.task
def scheduled_quota_checks():
    """Scheduled task to check quotas for all organizations."""
    try:
        # Find all organizations
        orgs = mongo.db.organisations.find({"is_deleted": False})
        
        total_checked = 0
        for org in orgs:
            try:
                result = async_form_quota_check.delay(str(org["_id"]))
                total_checked += 1
            except Exception as e:
                logger.error(f"Failed to schedule quota check for org {org['_id']}: {str(e)}")
        
        logger.info(f"Scheduled quota checks for {total_checked} organizations")
        return {"status": "success", "orgs_checked": total_checked}
        
    except Exception as e:
        logger.error(f"Failed to schedule quota checks: {str(e)}")
        return {"status": "error", "error": str(e)}


@celery.task
def scheduled_template_usage_updates():
    """Scheduled task to update template usage statistics."""
    try:
        # Find all templates
        templates = mongo.db.form_templates.find({"is_deleted": False})
        
        total_updated = 0
        for template in templates:
            try:
                result = async_form_template_usage_update.delay(str(template["_id"]))
                total_updated += 1
            except Exception as e:
                logger.error(f"Failed to schedule template usage update for template {template['_id']}: {str(e)}")
        
        logger.info(f"Scheduled template usage updates for {total_updated} templates")
        return {"status": "success", "templates_updated": total_updated}
        
    except Exception as e:
        logger.error(f"Failed to schedule template usage updates: {str(e)}")
        return {"status": "error", "error": str(e)}