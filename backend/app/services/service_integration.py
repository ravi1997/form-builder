"""
Service Integration - Ensures proper integration and communication between services
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from bson import ObjectId

from .audit_service import audit_service
from .storage_service import storage_service
from .auth_service import auth_service
from .dashboard_service import dashboard_service
from .utils.service_utils import ServiceLogger

logger = ServiceLogger("service_integration").logger


class ServiceIntegration:
    """Handles integration and communication between services"""
    
    def __init__(self):
        self.services = {
            'audit': audit_service,
            'storage': storage_service,
            'auth': auth_service,
            'dashboard': dashboard_service
        }
    
    async def log_user_action(self, user_id: ObjectId, action: str, entity_type: str, 
                           entity_id: ObjectId, before: Dict[str, Any] = None, 
                           after: Dict[str, Any] = None, **kwargs) -> None:
        """Log user action with proper context"""
        try:
            # Get user context
            user_doc = await self._get_user_context(user_id)
            if not user_doc:
                logger.warning(f"User not found for action logging: {user_id}")
                return
            
            # Determine organization context
            org_id = kwargs.get('org_id')
            if not org_id and entity_type in ['form', 'dashboard', 'analysis', 'project']:
                org_id = await self._get_entity_org_id(entity_type, entity_id)
            
            # Log the action
            await audit_service.log_action(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                actor_id=user_id,
                actor_role=user_doc.get('system_role', 'user'),
                before=before,
                after=after,
                org_id=org_id,
                project_id=kwargs.get('project_id'),
                ip_address=kwargs.get('ip_address'),
                user_agent=kwargs.get('user_agent')
            )
            
        except Exception as e:
            logger.error(f"Error logging user action: {e}")
            # Don't fail the operation if logging fails
    
    async def _get_user_context(self, user_id: ObjectId) -> Optional[Dict[str, Any]]:
        """Get user context for logging"""
        try:
            # This would typically query the user service
            # For now, we'll return a basic context
            return {
                '_id': user_id,
                'system_role': 'user'  # Default role
            }
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return None
    
    async def _get_entity_org_id(self, entity_type: str, entity_id: ObjectId) -> Optional[ObjectId]:
        """Get organization ID for an entity"""
        try:
            # This would query the appropriate service based on entity type
            # For now, we'll return None
            return None
        except Exception as e:
            logger.error(f"Error getting entity org ID: {e}")
            return None
    
    async def check_file_upload_permission(self, user_id: ObjectId, org_id: ObjectId, 
                                        file_size: int) -> bool:
        """Check if user has permission to upload file and if storage is available"""
        try:
            # Check storage availability
            if not await storage_service.check_storage_available(org_id, file_size):
                return False
            
            # Check user permissions (would integrate with auth service)
            # For now, we'll assume permission is granted
            return True
            
        except Exception as e:
            logger.error(f"Error checking file upload permission: {e}")
            return False
    
    async def create_dashboard_with_audit(self, dashboard_data: Dict[str, Any], 
                                       user_id: ObjectId) -> Dict[str, Any]:
        """Create dashboard with proper audit logging"""
        try:
            # Create dashboard
            dashboard = dashboard_service.create_dashboard(
                data=dashboard_data,
                author_id=str(user_id)
            )
            
            # Log the creation
            await self.log_user_action(
                user_id=user_id,
                action="create",
                entity_type="dashboard",
                entity_id=dashboard["_id"],
                after={
                    "name": dashboard.get("name"),
                    "project_id": str(dashboard.get("project_id")),
                    "org_id": str(dashboard.get("org_id"))
                }
            )
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Error creating dashboard with audit: {e}")
            raise
    
    async def upload_file_with_quota_check(self, file_data: Dict[str, Any], 
                                         user_id: ObjectId) -> Dict[str, Any]:
        """Upload file with quota check and audit logging"""
        try:
            org_id = file_data.get('org_id')
            file_size = file_data.get('file_size')
            
            # Check permissions and quota
            if not await self.check_file_upload_permission(user_id, org_id, file_size):
                raise PermissionError("File upload not allowed or quota exceeded")
            
            # Upload file
            file_upload = await storage_service.initiate_file_upload(**file_data)
            
            # Log the upload
            await self.log_user_action(
                user_id=user_id,
                action="upload",
                entity_type="file",
                entity_id=file_upload.id,
                after={
                    "filename": file_upload.original_filename,
                    "file_size": file_upload.file_size_bytes,
                    "mime_type": file_upload.mime_type
                },
                org_id=org_id
            )
            
            return file_upload
            
        except Exception as e:
            logger.error(f"Error uploading file with quota check: {e}")
            raise
    
    async def delete_file_with_cleanup(self, file_id: ObjectId, 
                                     user_id: ObjectId) -> bool:
        """Delete file with proper cleanup and audit logging"""
        try:
            # Get file info before deletion
            file_upload = await storage_service.get_file_upload(file_id)
            if not file_upload:
                return False
            
            # Delete file
            success = await storage_service.delete_file_upload(file_id, user_id)
            
            if success:
                # Log the deletion
                await self.log_user_action(
                    user_id=user_id,
                    action="delete",
                    entity_type="file",
                    entity_id=file_id,
                    before={
                        "filename": file_upload.original_filename,
                        "file_size": file_upload.file_size_bytes,
                        "mime_type": file_upload.mime_type
                    },
                    org_id=file_upload.org_id
                )
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting file with cleanup: {e}")
            return False
    
    async def get_user_dashboard_access(self, user_id: ObjectId, 
                                      dashboard_id: ObjectId) -> bool:
        """Check if user has access to dashboard"""
        try:
            # Get dashboard
            dashboard_response = dashboard_service.get_dashboard(str(dashboard_id))
            if not dashboard_response:
                return False
            
            dashboard = dashboard_response.get("dashboard")
            if not dashboard:
                return False
            
            # Check user permissions (would integrate with auth service)
            # For now, we'll check if user is in the same organization
            user_orgs = await self._get_user_orgs(user_id)
            dashboard_org = dashboard.get("org_id")
            
            if dashboard_org and dashboard_org in user_orgs:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking dashboard access: {e}")
            return False
    
    async def _get_user_orgs(self, user_id: ObjectId) -> List[ObjectId]:
        """Get user's organizations"""
        try:
            # This would integrate with the auth service
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Error getting user orgs: {e}")
            return []
    
    async def log_compliance_violation(self, violation_type: str, entity_type: str, 
                                     entity_id: ObjectId, details: Dict[str, Any]) -> None:
        """Log compliance violation"""
        try:
            await audit_service.log_action(
                entity_type=entity_type,
                entity_id=entity_id,
                action=f"compliance_violation_{violation_type}",
                actor_id=ObjectId("000000000000000000000000"),  # System actor
                actor_role="system",
                before={},
                after={
                    "violation_type": violation_type,
                    "severity": details.get("severity", "medium"),
                    "description": details.get("description", ""),
                    "remediation": details.get("remediation", "")
                }
            )
            
        except Exception as e:
            logger.error(f"Error logging compliance violation: {e}")
    
    async def get_service_health_status(self) -> Dict[str, Any]:
        """Get health status of all services"""
        try:
            health_status = {}
            
            # Check audit service
            try:
                # Simple check - try to get audit logs
                await audit_service.get_audit_logs(type('AuditLogFilter')(), limit=1)
                health_status['audit'] = {'status': 'healthy', 'message': 'OK'}
            except Exception as e:
                health_status['audit'] = {'status': 'unhealthy', 'message': str(e)}
            
            # Check storage service
            try:
                # Simple check - try to get storage quota
                await storage_service.get_storage_quota(ObjectId("000000000000000000000000"))
                health_status['storage'] = {'status': 'healthy', 'message': 'OK'}
            except Exception as e:
                health_status['storage'] = {'status': 'unhealthy', 'message': str(e)}
            
            # Check dashboard service
            try:
                # Simple check - try to list dashboards
                dashboard_service.list_dashboards("000000000000000000000000", page=1, per_page=1)
                health_status['dashboard'] = {'status': 'healthy', 'message': 'OK'}
            except Exception as e:
                health_status['dashboard'] = {'status': 'unhealthy', 'message': str(e)}
            
            # Overall status
            all_healthy = all(status['status'] == 'healthy' for status in health_status.values())
            health_status['overall'] = {
                'status': 'healthy' if all_healthy else 'degraded',
                'timestamp': datetime.utcnow().isoformat(),
                'services_checked': len(health_status)
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error getting service health status: {e}")
            return {
                'overall': {'status': 'error', 'message': str(e)},
                'timestamp': datetime.utcnow().isoformat()
            }


# Global service integration instance
service_integration = ServiceIntegration()