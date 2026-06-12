"""
Audit Service - Handles audit logging, compliance tracking, and audit trail management
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import logging
from bson import ObjectId
from pymongo.errors import PyMongoError

from ..models.audit import (
    AuditLog, AuditLogCreate, ComplianceStandard, OrgCompliance,
    AuditLogFilter, ComplianceReport
)
from ..models.common import PyObjectId
from ..utils.validators import validate_object_id
from ..utils.service_utils import (
    ServiceError, ValidationError, NotFoundError, handle_database_errors,
    create_service_response, ServiceLogger, validate_required_fields,
    validate_string_length, sanitize_dict
)
from ..extensions import mongo_db

logger = ServiceLogger("audit_service").logger


class AuditService:
    """Service for managing audit logs and compliance tracking"""
    
    def __init__(self):
        self.sensitive_fields = {
            'password', 'password_hash', 'secret', 'token', 'key', 'credit_card',
            'ssn', 'social_security', 'bank_account', 'routing_number'
        }
        
    @handle_database_errors
    async def log_action(
        self,
        entity_type: str,
        entity_id: PyObjectId,
        action: str,
        actor_id: PyObjectId,
        actor_role: str,
        before: Optional[Dict[str, Any]] = None,
        after: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        org_id: Optional[PyObjectId] = None,
        project_id: Optional[PyObjectId] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """Log an audit action"""
        try:
            # Validate required fields
            validate_required_fields({
                'entity_type': entity_type,
                'entity_id': entity_id,
                'action': action,
                'actor_id': actor_id,
                'actor_role': actor_role
            }, ['entity_type', 'entity_id', 'action', 'actor_id', 'actor_role'])
            
            # Validate string lengths
            validate_string_length(entity_type, 1, 50, "entity_type")
            validate_string_length(action, 1, 50, "action")
            validate_string_length(actor_role, 1, 50, "actor_role")
            
            # Validate ObjectIds
            entity_oid = validate_object_id(entity_id, "entity_id")
            actor_oid = validate_object_id(actor_id, "actor_id")
            
            if org_id:
                org_oid = validate_object_id(org_id, "org_id")
            
            if project_id:
                project_oid = validate_object_id(project_id, "project_id")
            
            # Sanitize sensitive data
            sanitized_before = self._sanitize_sensitive_data(before) if before else None
            sanitized_after = self._sanitize_sensitive_data(after) if after else None
            sanitized_metadata = sanitize_dict(metadata) if metadata else {}
            
            audit_data = AuditLogCreate(
                entity_type=entity_type,
                entity_id=entity_oid,
                action=action,
                actor_id=actor_oid,
                actor_role=actor_role,
                before=sanitized_before,
                after=sanitized_after,
                metadata=sanitized_metadata,
                org_id=org_oid if org_id else None,
                project_id=project_oid if project_id else None,
                ip_address=ip_address,
                user_agent=user_agent,
                timestamp=datetime.utcnow()
            )
            
            result = await mongo_db.audit_logs.insert_one(audit_data.dict(by_alias=True))
            audit_data.id = result.inserted_id
            
            return AuditLog(**audit_data.dict(by_alias=True))
            
        except Exception as e:
            logger.error(f"Error logging audit action: {e}")
            raise
    
    def _sanitize_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data from audit logs"""
        if not isinstance(data, dict):
            return data
            
        sanitized = {}
        for key, value in data.items():
            if key.lower() in self.sensitive_fields:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_sensitive_data(value)
            elif isinstance(value, list):
                sanitized[key] = [self._sanitize_sensitive_data(item) if isinstance(item, dict) else item for item in value]
            else:
                sanitized[key] = value
        
        return sanitized
    
    @handle_database_errors
    async def get_audit_logs(
        self,
        filter_params: AuditLogFilter,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLog]:
        """Get audit logs with filtering"""
        try:
            # Validate pagination parameters
            if not isinstance(limit, int) or limit < 1 or limit > 1000:
                raise ValidationError("Limit must be between 1 and 1000", "limit")
            
            if not isinstance(offset, int) or offset < 0:
                raise ValidationError("Offset must be a non-negative integer", "offset")
            
            # Build query
            query = {}
            
            if filter_params.org_id:
                org_oid = validate_object_id(filter_params.org_id, "org_id")
                query["org_id"] = org_oid
                
            if filter_params.project_id:
                project_oid = validate_object_id(filter_params.project_id, "project_id")
                query["project_id"] = project_oid
                
            if filter_params.entity_type:
                validate_string_length(filter_params.entity_type, 1, 50, "entity_type")
                query["entity_type"] = filter_params.entity_type
                
            if filter_params.entity_id:
                entity_oid = validate_object_id(filter_params.entity_id, "entity_id")
                query["entity_id"] = entity_oid
                
            if filter_params.action:
                validate_string_length(filter_params.action, 1, 50, "action")
                query["action"] = filter_params.action
                
            if filter_params.actor_id:
                actor_oid = validate_object_id(filter_params.actor_id, "actor_id")
                query["actor_id"] = actor_oid
                
            if filter_params.actor_role:
                validate_string_length(filter_params.actor_role, 1, 50, "actor_role")
                query["actor_role"] = filter_params.actor_role
                
            if filter_params.date_from:
                if not isinstance(filter_params.date_from, datetime):
                    raise ValidationError("date_from must be a datetime object", "date_from")
                query["timestamp"] = {"$gte": filter_params.date_from}
                
            if filter_params.date_to:
                if not isinstance(filter_params.date_to, datetime):
                    raise ValidationError("date_to must be a datetime object", "date_to")
                if "timestamp" in query:
                    query["timestamp"]["$lte"] = filter_params.date_to
                else:
                    query["timestamp"] = {"$lte": filter_params.date_to}
            
            # Exclude archived logs by default
            if not filter_params.include_archived:
                query["archived"] = False
            
            # Execute query
            cursor = mongo_db.audit_logs.find(query).sort("timestamp", -1).skip(offset).limit(limit)
            
            logs = []
            async for doc in cursor:
                logs.append(AuditLog(**doc))
            
            return logs
            
        except Exception as e:
            logger.error(f"Error fetching audit logs: {e}")
            raise
    
    @handle_database_errors
    async def get_audit_log(self, log_id: PyObjectId) -> Optional[AuditLog]:
        """Get a single audit log by ID"""
        try:
            log_oid = validate_object_id(log_id, "log_id")
            log_doc = await mongo_db.audit_logs.find_one({"_id": log_oid})
            if not log_doc:
                raise NotFoundError("audit_log", log_oid)
            return AuditLog(**log_doc)
        except Exception as e:
            logger.error(f"Error fetching audit log {log_id}: {e}")
            raise
    
    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: PyObjectId,
        limit: int = 50
    ) -> List[AuditLog]:
        """Get audit history for a specific entity"""
        try:
            filter_params = AuditLogFilter(
                entity_type=entity_type,
                entity_id=entity_id
            )
            
            return await self.get_audit_logs(filter_params, limit)
            
        except PyMongoError as e:
            logger.error(f"Error fetching entity history for {entity_type} {entity_id}: {e}")
            raise
    
    async def get_user_activity(
        self,
        user_id: PyObjectId,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs for a specific user"""
        try:
            filter_params = AuditLogFilter(
                actor_id=user_id,
                date_from=date_from,
                date_to=date_to
            )
            
            return await self.get_audit_logs(filter_params, limit)
            
        except PyMongoError as e:
            logger.error(f"Error fetching user activity for {user_id}: {e}")
            raise
    
    async def archive_old_logs(self, days_to_keep: int = 90) -> int:
        """Archive audit logs older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            result = await mongo_db.audit_logs.update_many(
                {
                    "timestamp": {"$lt": cutoff_date},
                    "archived": False
                },
                {"$set": {"archived": True}}
            )
            
            archived_count = result.modified_count
            logger.info(f"Archived {archived_count} audit logs older than {days_to_keep} days")
            
            return archived_count
            
        except PyMongoError as e:
            logger.error(f"Error archiving old audit logs: {e}")
            raise
    
    async def delete_archived_logs(self, days_to_keep: int = 365) -> int:
        """Delete archived audit logs older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            result = await mongo_db.audit_logs.delete_many({
                "timestamp": {"$lt": cutoff_date},
                "archived": True
            })
            
            deleted_count = result.deleted_count
            logger.info(f"Deleted {deleted_count} archived audit logs older than {days_to_keep} days")
            
            return deleted_count
            
        except PyMongoError as e:
            logger.error(f"Error deleting archived audit logs: {e}")
            raise
    
    @handle_database_errors
    async def create_compliance_standard(
        self,
        code: str,
        name: str,
        description: str,
        region: str,
        behavioral_constraints: List[Dict[str, Any]],
        created_by: PyObjectId
    ) -> ComplianceStandard:
        """Create a new compliance standard"""
        try:
            # Validate required fields
            validate_required_fields({
                'code': code,
                'name': name,
                'description': description,
                'region': region,
                'behavioral_constraints': behavioral_constraints,
                'created_by': created_by
            }, ['code', 'name', 'description', 'region', 'behavioral_constraints', 'created_by'])
            
            # Validate string lengths
            validate_string_length(code, 1, 20, "code")
            validate_string_length(name, 1, 100, "name")
            validate_string_length(description, 1, 500, "description")
            validate_string_length(region, 1, 50, "region")
            
            # Validate ObjectIds
            created_by_oid = validate_object_id(created_by, "created_by")
            
            # Check if standard already exists
            existing = await mongo_db.compliance_standards.find_one({"code": code})
            if existing:
                raise ConflictError(f"Compliance standard with code '{code}' already exists", "DUPLICATE_COMPLIANCE_CODE")
            
            standard_data = {
                "code": code,
                "name": name,
                "description": description,
                "region": region,
                "behavioral_constraints": behavioral_constraints,
                "is_system": False,
                "created_by": created_by_oid,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await mongo_db.compliance_standards.insert_one(standard_data)
            standard_data["_id"] = result.inserted_id
            
            return ComplianceStandard(**standard_data)
            
        except Exception as e:
            logger.error(f"Error creating compliance standard: {e}")
            raise
    
    async def get_compliance_standards(self, include_system: bool = True) -> List[ComplianceStandard]:
        """Get all compliance standards"""
        try:
            query = {}
            if not include_system:
                query["is_system"] = False
            
            cursor = mongo_db.compliance_standards.find(query).sort("code", 1)
            
            standards = []
            async for doc in cursor:
                standards.append(ComplianceStandard(**doc))
            
            return standards
            
        except PyMongoError as e:
            logger.error(f"Error fetching compliance standards: {e}")
            raise
    
    async def adopt_compliance_standard(
        self,
        org_id: PyObjectId,
        compliance_id: PyObjectId,
        adopted_by: PyObjectId,
        effective_from: datetime,
        notes: Optional[str] = None
    ) -> OrgCompliance:
        """Adopt a compliance standard for an organization"""
        try:
            # Check if compliance standard exists
            compliance_doc = await mongo_db.compliance_standards.find_one({"_id": compliance_id})
            if not compliance_doc:
                raise ValueError("Compliance standard not found")
            
            # Check if already adopted
            existing = await mongo_db.org_compliance.find_one({
                "org_id": org_id,
                "compliance_id": compliance_id
            })
            
            if existing:
                # Update existing adoption
                await mongo_db.org_compliance.update_one(
                    {"_id": existing["_id"]},
                    {
                        "$set": {
                            "effective_from": effective_from,
                            "notes": notes,
                            "adopted_at": datetime.utcnow(),
                            "adopted_by": adopted_by
                        }
                    }
                )
                
                existing["effective_from"] = effective_from
                existing["notes"] = notes
                existing["adopted_at"] = datetime.utcnow()
                existing["adopted_by"] = adopted_by
                
                return OrgCompliance(**existing)
            
            # Create new adoption
            compliance_data = {
                "org_id": org_id,
                "compliance_id": compliance_id,
                "adopted_at": datetime.utcnow(),
                "adopted_by": adopted_by,
                "effective_from": effective_from,
                "notes": notes
            }
            
            result = await mongo_db.org_compliance.insert_one(compliance_data)
            compliance_data["_id"] = result.inserted_id
            
            return OrgCompliance(**compliance_data)
            
        except PyMongoError as e:
            logger.error(f"Error adopting compliance standard: {e}")
            raise
    
    async def get_org_compliance(self, org_id: PyObjectId) -> List[OrgCompliance]:
        """Get compliance standards adopted by an organization"""
        try:
            cursor = mongo_db.org_compliance.find({"org_id": org_id}).sort("adopted_at", -1)
            
            compliances = []
            async for doc in cursor:
                compliances.append(OrgCompliance(**doc))
            
            return compliances
            
        except PyMongoError as e:
            logger.error(f"Error fetching org compliance for {org_id}: {e}")
            raise
    
    async def generate_compliance_report(
        self,
        org_id: PyObjectId,
        compliance_id: PyObjectId,
        date_from: datetime,
        date_to: datetime
    ) -> ComplianceReport:
        """Generate compliance report for an organization"""
        try:
            # Get compliance standard
            compliance_doc = await mongo_db.compliance_standards.find_one({"_id": compliance_id})
            if not compliance_doc:
                raise ValueError("Compliance standard not found")
            
            compliance_standard = ComplianceStandard(**compliance_doc)
            
            # Get audit logs for the period
            filter_params = AuditLogFilter(
                org_id=org_id,
                date_from=date_from,
                date_to=date_to
            )
            
            audit_logs = await self.get_audit_logs(filter_params, limit=10000)
            
            # Analyze compliance
            report_data = {
                "org_id": org_id,
                "compliance_id": compliance_id,
                "compliance_standard": compliance_standard,
                "period": {
                    "from": date_from,
                    "to": date_to
                },
                "total_audit_logs": len(audit_logs),
                "generated_at": datetime.utcnow(),
                "findings": []
            }
            
            # Check behavioral constraints
            for constraint in compliance_standard.behavioral_constraints:
                constraint_type = constraint.get("type")
                config = constraint.get("config", {})
                
                if constraint_type == "data_retention":
                    # Check data retention compliance
                    retention_findings = await self._check_data_retention_compliance(
                        org_id, config, audit_logs
                    )
                    report_data["findings"].extend(retention_findings)
                
                elif constraint_type == "access_control":
                    # Check access control compliance
                    access_findings = await self._check_access_control_compliance(
                        org_id, config, audit_logs
                    )
                    report_data["findings"].extend(access_findings)
                
                elif constraint_type == "audit_trail":
                    # Check audit trail compliance
                    audit_findings = await self._check_audit_trail_compliance(
                        org_id, config, audit_logs
                    )
                    report_data["findings"].extend(audit_findings)
            
            return ComplianceReport(**report_data)
            
        except PyMongoError as e:
            logger.error(f"Error generating compliance report: {e}")
            raise
    
    async def _check_data_retention_compliance(
        self,
        org_id: PyObjectId,
        config: Dict[str, Any],
        audit_logs: List[AuditLog]
    ) -> List[Dict[str, Any]]:
        """Check data retention compliance"""
        findings = []
        
        # Example: Check if data is being deleted according to retention policy
        delete_actions = [log for log in audit_logs if log.action == "delete"]
        
        if len(delete_actions) > 0:
            findings.append({
                "constraint_type": "data_retention",
                "status": "info",
                "message": f"Found {len(delete_actions)} delete actions in audit period",
                "details": {
                    "delete_count": len(delete_actions),
                    "actions": [f"{log.action} on {log.entity_type}" for log in delete_actions[:5]]
                }
            })
        
        return findings
    
    async def _check_access_control_compliance(
        self,
        org_id: PyObjectId,
        config: Dict[str, Any],
        audit_logs: List[AuditLog]
    ) -> List[Dict[str, Any]]:
        """Check access control compliance"""
        findings = []
        
        # Example: Check for unauthorized access attempts
        failed_actions = [log for log in audit_logs if "failed" in log.action.lower()]
        
        if len(failed_actions) > 0:
            findings.append({
                "constraint_type": "access_control",
                "status": "warning",
                "message": f"Found {len(failed_actions)} failed access attempts",
                "details": {
                    "failed_count": len(failed_actions),
                    "actions": [f"{log.action} by {log.actor_role}" for log in failed_actions[:5]]
                }
            })
        
        return findings
    
    async def _check_audit_trail_compliance(
        self,
        org_id: PyObjectId,
        config: Dict[str, Any],
        audit_logs: List[AuditLog]
    ) -> List[Dict[str, Any]]:
        """Check audit trail compliance"""
        findings = []
        
        # Example: Check if all required actions are being logged
        required_actions = config.get("required_actions", [])
        
        for action in required_actions:
            action_count = len([log for log in audit_logs if log.action == action])
            
            if action_count == 0:
                findings.append({
                    "constraint_type": "audit_trail",
                    "status": "error",
                    "message": f"Required action '{action}' not found in audit logs",
                    "details": {
                        "required_action": action,
                        "found_count": 0
                    }
                })
        
        return findings
    
    async def export_audit_logs(
        self,
        filter_params: AuditLogFilter,
        format: str = "json"
    ) -> str:
        """Export audit logs in specified format"""
        try:
            # Get all matching logs (no limit for export)
            logs = await self.get_audit_logs(filter_params, limit=10000)
            
            if format.lower() == "json":
                return json.dumps([log.dict(by_alias=True) for log in logs], indent=2, default=str)
            elif format.lower() == "csv":
                # Generate CSV format
                import csv
                import io
                
                output = io.StringIO()
                if logs:
                    writer = csv.DictWriter(output, fieldnames=logs[0].dict().keys())
                    writer.writeheader()
                    for log in logs:
                        writer.writerow(log.dict())
                
                return output.getvalue()
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting audit logs: {e}")
            raise


# Global service instance
audit_service = AuditService()