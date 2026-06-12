import datetime
import json
import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional, Union
from bson import ObjectId
from flask import current_app

from app.extensions import mongo, redis_client
from app.services.notification_service import (
    send_email, send_sms, create_in_app_notification,
    record_delivery_attempt, schedule_retry, notify_super_admins_of_failure
)

logger = logging.getLogger(__name__)


def _now():
    """Get current UTC datetime."""
    return datetime.datetime.utcnow()


def _oid(value):
    """Convert value to ObjectId if valid, otherwise return as-is."""
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    if ObjectId.is_valid(str(value)):
        return ObjectId(str(value))
    return value


def _serialize_doc(doc):
    """Serialize MongoDB document for JSON response."""
    if not doc:
        return doc
    if isinstance(doc, list):
        return [_serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime.datetime):
                result[key] = value.isoformat()
            elif isinstance(value, (dict, list)):
                result[key] = _serialize_doc(value)
            else:
                result[key] = value
        return result
    return doc


class NotificationEngine:
    """Engine for processing and delivering notifications."""
    
    def __init__(self):
        self.event_handlers = {}
        self.template_cache = {}
        self.retry_queue = []
        self.worker_running = False
        self.worker_thread = None
        
        # Register default event handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default event handlers."""
        self.register_event_handler("response.submitted", self._handle_response_submitted)
        self.register_event_handler("response.edited", self._handle_response_edited)
        self.register_event_handler("form.published", self._handle_form_published)
        self.register_event_handler("form.version_changed", self._handle_form_version_changed)
        self.register_event_handler("collaboration.conflict", self._handle_collaboration_conflict)
        self.register_event_handler("analysis.run_completed", self._handle_analysis_run_completed)
        self.register_event_handler("analysis.run_failed", self._handle_analysis_run_failed)
        self.register_event_handler("invite.accepted", self._handle_invite_accepted)
        self.register_event_handler("user.approved", self._handle_user_approved)
        self.register_event_handler("user.suspended", self._handle_user_suspended)
        self.register_event_handler("quota.warning_80", self._handle_quota_warning)
        self.register_event_handler("quota.warning_90", self._handle_quota_warning)
        self.register_event_handler("quota.exceeded", self._handle_quota_exceeded)
        self.register_event_handler("plugin.installed", self._handle_plugin_installed)
        self.register_event_handler("plugin.error", self._handle_plugin_error)
        self.register_event_handler("webhook.failed", self._handle_webhook_failed)
        self.register_event_handler("scheduled_analysis.completed", self._handle_scheduled_analysis_completed)
    
    def register_event_handler(self, event_type: str, handler_func):
        """Register an event handler function."""
        self.event_handlers[event_type] = handler_func
    
    def trigger_event(self, event_type: str, context: Dict, async_mode: bool = True):
        """Trigger a notification event."""
        try:
            if event_type not in self.event_handlers:
                logger.warning(f"No handler registered for event: {event_type}")
                return
            
            if async_mode:
                # Queue event for processing
                self._queue_event(event_type, context)
            else:
                # Process event synchronously
                self._process_event(event_type, context)
            
        except Exception as e:
            logger.error(f"Error triggering event {event_type}: {str(e)}")
    
    def _queue_event(self, event_type: str, context: Dict):
        """Queue an event for processing."""
        event_data = {
            "event_type": event_type,
            "context": context,
            "queued_at": _now(),
            "status": "queued"
        }
        
        # Store in MongoDB for persistence
        mongo.db.notification_queue.insert_one(event_data)
        
        # Start worker if not running
        if not self.worker_running:
            self._start_worker()
    
    def _start_worker(self):
        """Start the notification worker thread."""
        if self.worker_running:
            return
        
        self.worker_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Notification worker started")
    
    def _worker_loop(self):
        """Main worker loop for processing notifications."""
        while self.worker_running:
            try:
                # Get next event from queue
                event = mongo.db.notification_queue.find_one_and_update(
                    {"status": "queued"},
                    {"$set": {"status": "processing", "processing_started_at": _now()}}
                )
                
                if event:
                    try:
                        self._process_event(event["event_type"], event["context"])
                        
                        # Mark as completed
                        mongo.db.notification_queue.update_one(
                            {"_id": event["_id"]},
                            {"$set": {"status": "completed", "completed_at": _now()}}
                        )
                        
                    except Exception as e:
                        logger.error(f"Error processing event {event['_id']}: {str(e)}")
                        
                        # Mark as failed
                        mongo.db.notification_queue.update_one(
                            {"_id": event["_id"]},
                            {"$set": {
                                "status": "failed",
                                "error": str(e),
                                "failed_at": _now()
                            }}
                        )
                else:
                    # No events to process, sleep briefly
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in notification worker loop: {str(e)}")
                time.sleep(5)  # Sleep longer on error
    
    def _process_event(self, event_type: str, context: Dict):
        """Process a single notification event."""
        handler = self.event_handlers.get(event_type)
        if not handler:
            logger.warning(f"No handler for event: {event_type}")
            return
        
        try:
            handler(context)
        except Exception as e:
            logger.error(f"Error in event handler for {event_type}: {str(e)}")
            raise
    
    def _get_notification_template(self, event_type: str, org_id: ObjectId = None):
        """Get notification template for an event."""
        cache_key = f"{event_type}:{org_id}"
        
        # Check cache
        if cache_key in self.template_cache:
            cached_time, template = self.template_cache[cache_key]
            # Cache templates for 5 minutes
            if time.time() - cached_time < 300:
                return template
        
        # Get template from database
        template = mongo.db.notification_templates.find_one({
            "event_type": event_type,
            "org_id": org_id,
            "is_active": True
        })
        
        if not template:
            # Try system template
            template = mongo.db.notification_templates.find_one({
                "event_type": event_type,
                "org_id": None,
                "is_active": True
            })
        
        if template:
            # Cache template
            self.template_cache[cache_key] = (time.time(), template)
        
        return template
    
    def _render_template(self, template: Dict, context: Dict) -> Dict:
        """Render template with context variables."""
        def replace_variables(text: str, context: Dict) -> str:
            if not text:
                return text
            
            # Replace {{variable}} patterns
            pattern = r'\{\{(\w+)\}\}'
            
            def replacer(match):
                var_name = match.group(1)
                value = context.get(var_name, '')
                return str(value)
            
            return re.sub(pattern, replacer, text)
        
        rendered = {
            "email": {
                "subject": replace_variables(template.get("channels", {}).get("email", {}).get("subject", ""), context),
                "body_html": replace_variables(template.get("channels", {}).get("email", {}).get("body_html", ""), context),
                "body_text": replace_variables(template.get("channels", {}).get("email", {}).get("body_text", ""), context)
            },
            "sms": {
                "message": replace_variables(template.get("channels", {}).get("sms", {}).get("message", ""), context)
            },
            "in_app": {
                "title": replace_variables(template.get("channels", {}).get("in_app", {}).get("title", ""), context),
                "body": replace_variables(template.get("channels", {}).get("in_app", {}).get("body", ""), context)
            }
        }
        
        return rendered
    
    def _get_recipients(self, rule: Dict, context: Dict) -> List[Dict]:
        """Get list of recipients for a notification rule."""
        recipient_type = rule.get("recipient_type")
        recipient_ids = rule.get("recipient_ids", [])
        
        recipients = []
        
        if recipient_type == "form_owner":
            # Get form owner
            form_id = context.get("form_id")
            if form_id:
                form = mongo.db.forms.find_one({
                    "_id": _oid(form_id),
                    "is_deleted": False
                })
                if form:
                    owner = mongo.db.users.find_one({
                        "_id": form["created_by"],
                        "is_deleted": False
                    })
                    if owner:
                        recipients.append(owner)
        
        elif recipient_type == "specific_users":
            # Get specific users
            users = mongo.db.users.find({
                "_id": {"$in": [_oid(uid) for uid in recipient_ids]},
                "is_deleted": False
            })
            recipients = list(users)
        
        elif recipient_type == "role":
            # Get users by role
            org_id = context.get("org_id")
            if org_id:
                memberships = mongo.db.org_memberships.find({
                    "org_id": _oid(org_id),
                    "role": {"$in": recipient_ids},
                    "status": "active",
                    "is_deleted": False
                })
                user_ids = [m["user_id"] for m in memberships]
                users = mongo.db.users.find({
                    "_id": {"$in": user_ids},
                    "is_deleted": False
                })
                recipients = list(users)
        
        elif recipient_type == "group":
            # Get users by group
            org_id = context.get("org_id")
            if org_id:
                group_members = mongo.db.group_members.find({
                    "group_id": {"$in": [_oid(gid) for gid in recipient_ids]},
                    "is_deleted": False
                })
                user_ids = [gm["user_id"] for gm in group_members]
                users = mongo.db.users.find({
                    "_id": {"$in": user_ids},
                    "is_deleted": False
                })
                recipients = list(users)
        
        elif recipient_type == "respondent":
            # Get form respondent
            response_id = context.get("response_id")
            if response_id:
                response = mongo.db.form_responses.find_one({
                    "_id": _oid(response_id)
                })
                if response and response.get("respondent_id"):
                    respondent = mongo.db.users.find_one({
                        "_id": response["respondent_id"],
                        "is_deleted": False
                    })
                    if respondent:
                        recipients.append(respondent)
        
        return recipients
    
    def _send_notification(self, rule: Dict, context: Dict, rendered_template: Dict):
        """Send notification through specified channels."""
        recipients = self._get_recipients(rule, context)
        channels = rule.get("channels", [])
        
        for recipient in recipients:
            for channel in channels:
                try:
                    if channel == "email":
                        self._send_email_notification(recipient, rendered_template["email"], context)
                    elif channel == "sms":
                        self._send_sms_notification(recipient, rendered_template["sms"], context)
                    elif channel == "in_app":
                        self._send_in_app_notification(recipient, rendered_template["in_app"], context, rule)
                    elif channel == "push":
                        self._send_push_notification(recipient, rendered_template["in_app"], context)
                    elif channel == "webhook":
                        self._send_webhook_notification(rule, context)
                
                except Exception as e:
                    logger.error(f"Error sending {channel} notification to {recipient.get('email')}: {str(e)}")
                    # Continue with other notifications
    
    def _send_email_notification(self, recipient: Dict, email_content: Dict, context: Dict):
        """Send email notification."""
        if not recipient.get("email"):
            return
        
        # Check user preferences
        prefs = recipient.get("notification_preferences", {})
        if not prefs.get("email", True):
            return
        
        # Create notification log
        log_doc = {
            "org_id": context.get("org_id"),
            "rule_id": context.get("rule_id"),
            "event_type": context.get("event_type"),
            "recipient_id": recipient["_id"],
            "channel": "email",
            "status": "queued",
            "attempt_count": 1,
            "max_attempts": 3,
            "created_at": _now()
        }
        
        result = mongo.db.notification_log.insert_one(log_doc)
        log_id = result.inserted_id
        
        try:
            # Send email
            response = send_email(
                recipient_email=recipient["email"],
                subject=email_content["subject"],
                body_html=email_content["body_html"],
                body_text=email_content["body_text"],
                log_id=log_id
            )
            
            if response.status_code == 200:
                record_delivery_attempt(log_id, "sent", {"status_code": response.status_code})
            else:
                # Schedule retry
                schedule_retry(log_id, 60)  # Retry in 1 minute
        
        except Exception as e:
            logger.error(f"Error sending email to {recipient['email']}: {str(e)}")
            schedule_retry(log_id, 60)
    
    def _send_sms_notification(self, recipient: Dict, sms_content: Dict, context: Dict):
        """Send SMS notification."""
        if not recipient.get("phone"):
            return
        
        # Check user preferences
        prefs = recipient.get("notification_preferences", {})
        if not prefs.get("sms", True):
            return
        
        # Create notification log
        log_doc = {
            "org_id": context.get("org_id"),
            "rule_id": context.get("rule_id"),
            "event_type": context.get("event_type"),
            "recipient_id": recipient["_id"],
            "channel": "sms",
            "status": "queued",
            "attempt_count": 1,
            "max_attempts": 3,
            "created_at": _now()
        }
        
        result = mongo.db.notification_log.insert_one(log_doc)
        log_id = result.inserted_id
        
        try:
            # Send SMS
            response = send_sms(
                recipient_phone=recipient["phone"],
                message=sms_content["message"],
                log_id=log_id
            )
            
            if response.status_code == 200:
                record_delivery_attempt(log_id, "sent", {"status_code": response.status_code})
            else:
                # Schedule retry
                schedule_retry(log_id, 60)
        
        except Exception as e:
            logger.error(f"Error sending SMS to {recipient['phone']}: {str(e)}")
            schedule_retry(log_id, 60)
    
    def _send_in_app_notification(self, recipient: Dict, in_app_content: Dict, context: Dict, rule: Dict):
        """Send in-app notification."""
        # Create in-app notification
        create_in_app_notification(
            org_id=context.get("org_id"),
            recipient_id=recipient["_id"],
            event_type=context.get("event_type"),
            title=in_app_content["title"],
            body=in_app_content["body"],
            action_url=context.get("action_url"),
            rule_id=rule.get("_id"),
            metadata=context
        )
    
    def _send_push_notification(self, recipient: Dict, in_app_content: Dict, context: Dict):
        """Send push notification (placeholder implementation)."""
        # This would integrate with FCM/APN services
        logger.info(f"Push notification to {recipient.get('email')}: {in_app_content['title']}")
    
    def _send_webhook_notification(self, rule: Dict, context: Dict):
        """Send webhook notification."""
        # This would be implemented in the webhook service
        logger.info(f"Webhook notification for rule {rule.get('_id')}")
    
    def _find_active_rules(self, event_type: str, org_id: ObjectId = None, context: Dict = None) -> List[Dict]:
        """Find active notification rules for an event."""
        query = {
            "event_type": event_type,
            "is_active": True,
            "is_deleted": False
        }
        
        if org_id:
            query["org_id"] = org_id
        
        rules = list(mongo.db.notification_rules.find(query))
        
        # Filter rules by trigger conditions
        active_rules = []
        for rule in rules:
            if self._evaluate_trigger_conditions(rule, context or {}):
                active_rules.append(rule)
        
        return active_rules
    
    def _evaluate_trigger_conditions(self, rule: Dict, context: Dict) -> bool:
        """Evaluate trigger conditions for a rule."""
        conditions = rule.get("trigger_conditions", [])
        
        if not conditions:
            return True
        
        # Simple condition evaluation (can be enhanced)
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator", "equals")
            value = condition.get("value")
            
            context_value = context.get(field)
            
            if operator == "equals" and context_value != value:
                return False
            elif operator == "not_equals" and context_value == value:
                return False
            elif operator == "contains" and value not in str(context_value or ""):
                return False
            elif operator == "greater_than" and (context_value or 0) <= value:
                return False
            elif operator == "less_than" and (context_value or 0) >= value:
                return False
        
        return True
    
    # Event handlers
    def _handle_response_submitted(self, context: Dict):
        """Handle response.submitted event."""
        org_id = context.get("org_id")
        form_id = context.get("form_id")
        response_id = context.get("response_id")
        
        # Get form details
        form = mongo.db.forms.find_one({
            "_id": _oid(form_id),
            "is_deleted": False
        })
        
        if not form:
            return
        
        # Build context
        full_context = {
            **context,
            "form_name": form.get("name"),
            "action_url": f"/forms/{form_id}/responses/{response_id}"
        }
        
        # Find and execute rules
        rules = self._find_active_rules("response.submitted", org_id, full_context)
        
        for rule in rules:
            template = self._get_notification_template("response.submitted", org_id)
            if template:
                rendered = self._render_template(template, full_context)
                self._send_notification(rule, full_context, rendered)
    
    def _handle_response_edited(self, context: Dict):
        """Handle response.edited event."""
        # Similar to response.submitted but with different context
        org_id = context.get("org_id")
        form_id = context.get("form_id")
        response_id = context.get("response_id")
        
        form = mongo.db.forms.find_one({
            "_id": _oid(form_id),
            "is_deleted": False
        })
        
        if not form:
            return
        
        full_context = {
            **context,
            "form_name": form.get("name"),
            "action_url": f"/forms/{form_id}/responses/{response_id}"
        }
        
        rules = self._find_active_rules("response.edited", org_id, full_context)
        
        for rule in rules:
            template = self._get_notification_template("response.edited", org_id)
            if template:
                rendered = self._render_template(template, full_context)
                self._send_notification(rule, full_context, rendered)
    
    def _handle_form_published(self, context: Dict):
        """Handle form.published event."""
        org_id = context.get("org_id")
        form_id = context.get("form_id")
        
        form = mongo.db.forms.find_one({
            "_id": _oid(form_id),
            "is_deleted": False
        })
        
        if not form:
            return
        
        full_context = {
            **context,
            "form_name": form.get("name"),
            "action_url": f"/forms/{form_id}"
        }
        
        rules = self._find_active_rules("form.published", org_id, full_context)
        
        for rule in rules:
            template = self._get_notification_template("form.published", org_id)
            if template:
                rendered = self._render_template(template, full_context)
                self._send_notification(rule, full_context, rendered)
    
    def _handle_form_version_changed(self, context: Dict):
        """Handle form.version_changed event."""
        # Similar to form.published
        self._handle_form_published(context)
    
    def _handle_collaboration_conflict(self, context: Dict):
        """Handle collaboration.conflict event."""
        org_id = context.get("org_id")
        form_id = context.get("form_id")
        
        form = mongo.db.forms.find_one({
            "_id": _oid(form_id),
            "is_deleted": False
        })
        
        if not form:
            return
        
        full_context = {
            **context,
            "form_name": form.get("name"),
            "action_url": f"/forms/{form_id}/conflicts"
        }
        
        rules = self._find_active_rules("collaboration.conflict", org_id, full_context)
        
        for rule in rules:
            template = self._get_notification_template("collaboration.conflict", org_id)
            if template:
                rendered = self._render_template(template, full_context)
                self._send_notification(rule, full_context, rendered)
    
    def _handle_analysis_run_completed(self, context: Dict):
        """Handle analysis.run_completed event."""
        org_id = context.get("org_id")
        analysis_id = context.get("analysis_id")
        
        analysis = mongo.db.analyses.find_one({
            "_id": _oid(analysis_id),
            "is_deleted": False
        })
        
        if not analysis:
            return
        
        full_context = {
            **context,
            "analysis_name": analysis.get("name"),
            "action_url": f"/analyses/{analysis_id}"
        }
        
        rules = self._find_active_rules("analysis.run_completed", org_id, full_context)
        
        for rule in rules:
            template = self._get_notification_template("analysis.run_completed", org_id)
            if template:
                rendered = self._render_template(template, full_context)
                self._send_notification(rule, full_context, rendered)
    
    def _handle_analysis_run_failed(self, context: Dict):
        """Handle analysis.run_failed event."""
        org_id = context.get("org_id")
        analysis_id = context.get("analysis_id")
        
        analysis = mongo.db.analyses.find_one({
            "_id": _oid(analysis_id),
            "is_deleted": False
        })
        
        if not analysis:
            return
        
        full_context = {
            **context,
            "analysis_name": analysis.get("name"),
            "error_message": context.get("error", "Unknown error"),
            "action_url": f"/analyses/{analysis_id}"
        }
        
        rules = self._find_active_rules("analysis.run_failed", org_id, full_context)
        
        for rule in rules:
            template = self._get_notification_template("analysis.run_failed", org_id)
            if template:
                rendered = self._render_template(template, full_context)
                self._send_notification(rule, full_context, rendered)
    
    def _handle_invite_accepted(self, context: Dict):
        """Handle invite.accepted event."""
        org_id = context.get("org_id")
        user_id = context.get("user_id")
        
        user = mongo.db.users.find_one({
            "_id": _oid(user_id),
            "is_deleted": False
        })
        
        if not user:
            return
        
        full_context = {
            **context,
            "user_name": user.get("full_name") or user.get("display_name"),
            "user_email": user.get("email")
        }
        
        rules = self._find_active_rules("invite.accepted", org_id, full_context)
        
        for rule in rules:
            template = self._get_notification_template("invite.accepted", org_id)
            if template:
                rendered = self._render_template(template, full_context)
                self._send_notification(rule, full_context, rendered)
    
    def _handle_user_approved(self, context: Dict):
        """Handle user.approved event."""
        user_id = context.get("user_id")
        
        user = mongo.db.users.find_one({
            "_id": _oid(user_id),
            "is_deleted": False
        })
        
        if not user:
            return
        
        full_context = {
            **context,
            "user_name": user.get("full_name") or user.get("display_name"),
            "user_email": user.get("email")
        }
        
        # Notify all org admins
        org_memberships = mongo.db.org_memberships.find({
            "user_id": _oid(user_id),
            "status": "active",
            "is_deleted": False
        })
        
        for membership in org_memberships:
            org_id = membership["org_id"]
            rules = self._find_active_rules("user.approved", org_id, full_context)
            
            for rule in rules:
                template = self._get_notification_template("user.approved", org_id)
                if template:
                    rendered = self._render_template(template, full_context)
                    self._send_notification(rule, full_context, rendered)
    
    def _handle_user_suspended(self, context: Dict):
        """Handle user.suspended event."""
        # Similar to user.approved
        self._handle_user_approved(context)
    
    def _handle_quota_warning(self, context: Dict):
        """Handle quota.warning events."""
        org_id = context.get("org_id")
        threshold = context.get("threshold", 80)
        
        full_context = {
            **context,
            "threshold": f"{threshold}%"
        }
        
        rules = self._find_active_rules(f"quota.warning_{threshold}", org_id, full_context)
        
        for rule in rules:
            template = self._get_notification_template(f"quota.warning_{threshold}", org_id)
            if template:
                rendered = self._render_template(template, full_context)
                self._send_notification(rule, full_context, rendered)
    
    def _handle_quota_exceeded(self, context: Dict):
        """Handle quota.exceeded event."""
        org_id = context.get("org_id")
        
        full_context = {**context}
        
        rules = self._find_active_rules("quota.exceeded", org_id, full_context)
        
        for rule in rules:
            template = self._get_notification_template("quota.exceeded", org_id)
            if template:
                rendered = self._render_template(template, full_context)
                self._send_notification(rule, full_context, rendered)
    
    def _handle_plugin_installed(self, context: Dict):
        """Handle plugin.installed event."""
        # Notify super admins
        notify_super_admins_of_failure(
            event_type="plugin.installed",
            message=f"Plugin {context.get('plugin_name')} has been installed"
        )
    
    def _handle_plugin_error(self, context: Dict):
        """Handle plugin.error event."""
        # Notify super admins
        notify_super_admins_of_failure(
            event_type="plugin.error",
            message=f"Plugin {context.get('plugin_name')} encountered an error: {context.get('error')}"
        )
    
    def _handle_webhook_failed(self, context: Dict):
        """Handle webhook.failed event."""
        # Notify super admins
        notify_super_admins_of_failure(
            event_type="webhook.failed",
            message=f"Webhook delivery failed: {context.get('error')}"
        )
    
    def _handle_scheduled_analysis_completed(self, context: Dict):
        """Handle scheduled_analysis.completed event."""
        # Similar to analysis.run_completed but for scheduled runs
        self._handle_analysis_run_completed(context)
    
    def stop_worker(self):
        """Stop the notification worker."""
        self.worker_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Notification worker stopped")


# Create engine instance
notification_engine = NotificationEngine()