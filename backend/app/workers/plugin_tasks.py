"""
Plugin Tasks - Celery tasks for plugin operations.

This module provides:
- Background plugin installation
- Plugin validation and verification
- Plugin cleanup and maintenance
- Plugin health monitoring
"""

import os
import json
import shutil
import tempfile
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import logging
from celery import Celery
from pymongo import MongoClient
from redis import Redis
from bson import ObjectId

from ..models.plugin import Plugin, PluginStatus, PluginVersionStatus
from ..services.plugin_service import PluginService
from ..engines.plugin_engine import PluginEngine
from ..utils.validators import ValidationError
from ..utils.security import PluginSecurityError

logger = logging.getLogger(__name__)

# Get Celery app instance
celery_app = Celery('plugin_tasks')


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def install_plugin_task(self, plugin_file_path: str, installer_id: str, 
                       auto_approve_permissions: bool = False):
    """
    Background task to install a plugin.
    
    Args:
        plugin_file_path: Path to plugin file
        installer_id: ID of user installing the plugin
        auto_approve_permissions: Whether to auto-approve permissions
    """
    try:
        # Get database connections
        mongo_client = MongoClient(os.getenv('MONGODB_URI'))
        redis_client = Redis.from_url(os.getenv('REDIS_URL'))
        
        # Initialize services
        plugin_engine = PluginEngine(mongo_client, redis_client)
        plugin_service = PluginService(
            mongo_client.formbuilder,
            redis_client,
            plugin_engine
        )
        
        # Install plugin
        from ..models.plugin import PluginInstallRequest
        install_request = PluginInstallRequest(
            plugin_file=plugin_file_path,
            auto_approve_permissions=auto_approve_permissions
        )
        
        plugin = plugin_service.install_plugin(install_request, ObjectId(installer_id))
        
        # Log success
        logger.info(f"Background plugin installation successful: {plugin.plugin_id}")
        
        return {
            "success": True,
            "plugin_id": plugin.plugin_id,
            "message": "Plugin installed successfully"
        }
        
    except ValidationError as e:
        logger.error(f"Plugin validation failed: {str(e)}")
        return {
            "success": False,
            "error": "validation_error",
            "message": str(e)
        }
    except PluginSecurityError as e:
        logger.error(f"Plugin security error: {str(e)}")
        return {
            "success": False,
            "error": "security_error",
            "message": str(e)
        }
    except Exception as e:
        logger.error(f"Plugin installation failed: {str(e)}")
        
        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            "success": False,
            "error": "installation_failed",
            "message": "Failed to install plugin after retries"
        }
    finally:
        # Cleanup connections
        if 'mongo_client' in locals():
            mongo_client.close()
        if 'redis_client' in locals():
            redis_client.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def uninstall_plugin_task(self, plugin_id: str, uninstaller_id: str):
    """
    Background task to uninstall a plugin.
    
    Args:
        plugin_id: ID of plugin to uninstall
        uninstaller_id: ID of user uninstalling the plugin
    """
    try:
        # Get database connections
        mongo_client = MongoClient(os.getenv('MONGODB_URI'))
        redis_client = Redis.from_url(os.getenv('REDIS_URL'))
        
        # Initialize services
        plugin_engine = PluginEngine(mongo_client, redis_client)
        plugin_service = PluginService(
            mongo_client.formbuilder,
            redis_client,
            plugin_engine
        )
        
        # Uninstall plugin
        success = plugin_service.uninstall_plugin(plugin_id, ObjectId(uninstaller_id))
        
        if success:
            logger.info(f"Background plugin uninstallation successful: {plugin_id}")
            return {
                "success": True,
                "plugin_id": plugin_id,
                "message": "Plugin uninstalled successfully"
            }
        else:
            return {
                "success": False,
                "error": "uninstall_failed",
                "message": "Failed to uninstall plugin"
            }
        
    except ValidationError as e:
        logger.error(f"Plugin uninstallation validation failed: {str(e)}")
        return {
            "success": False,
            "error": "validation_error",
            "message": str(e)
        }
    except Exception as e:
        logger.error(f"Plugin uninstallation failed: {str(e)}")
        
        # Retry on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            "success": False,
            "error": "uninstall_failed",
            "message": "Failed to uninstall plugin after retries"
        }
    finally:
        # Cleanup connections
        if 'mongo_client' in locals():
            mongo_client.close()
        if 'redis_client' in locals():
            redis_client.close()


@celery_app.task
def validate_plugin_task(plugin_file_path: str, platform_version: str = "1.0.0"):
    """
    Background task to validate a plugin without installing it.
    
    Args:
        plugin_file_path: Path to plugin file
        platform_version: Platform version to check compatibility
    """
    try:
        from ..utils.validators import validate_plugin_installation
        
        plugin_path = Path(plugin_file_path)
        if not plugin_path.exists():
            return {
                "success": False,
                "error": "file_not_found",
                "message": f"Plugin file not found: {plugin_file_path}"
            }
        
        # Validate plugin
        manifest = validate_plugin_installation(plugin_path, [], platform_version)
        
        return {
            "success": True,
            "plugin_id": manifest.get('plugin_id'),
            "plugin_name": manifest.get('name'),
            "version": manifest.get('version'),
            "concept_targets": manifest.get('concept_targets', []),
            "permissions": manifest.get('permissions', []),
            "components_count": len(manifest.get('components', [])),
            "message": "Plugin validation successful"
        }
        
    except ValidationError as e:
        logger.error(f"Plugin validation failed: {str(e)}")
        return {
            "success": False,
            "error": "validation_error",
            "message": str(e)
        }
    except Exception as e:
        logger.error(f"Plugin validation error: {str(e)}")
        return {
            "success": False,
            "error": "validation_failed",
            "message": "Failed to validate plugin"
        }


@celery_app.task
def cleanup_plugin_sandbox_task():
    """
    Background task to cleanup expired plugin sandboxes.
    """
    try:
        # Get database connections
        mongo_client = MongoClient(os.getenv('MONGODB_URI'))
        redis_client = Redis.from_url(os.getenv('REDIS_URL'))
        
        # Find expired sandboxes (older than 1 hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        
        # This would typically query a sandbox registry
        # For now, just clean up temp directories
        temp_dir = Path('/tmp')
        plugin_temp_dirs = [
            d for d in temp_dir.iterdir() 
            if d.is_dir() and d.name.startswith('plugin_') and 
            d.stat().st_mtime < cutoff_time.timestamp()
        ]
        
        cleaned_count = 0
        for plugin_dir in plugin_temp_dirs:
            try:
                shutil.rmtree(plugin_dir)
                cleaned_count += 1
                logger.info(f"Cleaned up plugin sandbox: {plugin_dir}")
            except Exception as e:
                logger.error(f"Failed to cleanup plugin sandbox {plugin_dir}: {str(e)}")
        
        return {
            "success": True,
            "cleaned_sandboxes": cleaned_count,
            "message": f"Cleaned up {cleaned_count} plugin sandboxes"
        }
        
    except Exception as e:
        logger.error(f"Plugin sandbox cleanup failed: {str(e)}")
        return {
            "success": False,
            "error": "cleanup_failed",
            "message": "Failed to cleanup plugin sandboxes"
        }
    finally:
        # Cleanup connections
        if 'mongo_client' in locals():
            mongo_client.close()
        if 'redis_client' in locals():
            redis_client.close()


@celery_app.task
def monitor_plugin_health_task():
    """
    Background task to monitor plugin health and status.
    """
    try:
        # Get database connections
        mongo_client = MongoClient(os.getenv('MONGODB_URI'))
        redis_client = Redis.from_url(os.getenv('REDIS_URL'))
        
        db = mongo_client.formbuilder
        
        # Get all active plugins
        active_plugins = list(db.plugins.find({
            "status": PluginStatus.ACTIVE,
            "is_deleted": False
        }))
        
        health_report = {
            "total_plugins": len(active_plugins),
            "healthy_plugins": 0,
            "unhealthy_plugins": 0,
            "issues": []
        }
        
        for plugin_doc in active_plugins:
            plugin = Plugin(**plugin_doc)
            
            # Check plugin health
            is_healthy = True
            issues = []
            
            # Check if plugin files exist
            plugin_dir = Path(__file__).parent.parent / "plugins" / "installed" / plugin.plugin_id
            if not plugin_dir.exists():
                is_healthy = False
                issues.append("Plugin directory not found")
            
            # Check if manifest exists
            manifest_file = plugin_dir / "manifest.json"
            if not manifest_file.exists():
                is_healthy = False
                issues.append("Plugin manifest not found")
            
            # Check if handler file exists
            backend_config = plugin.manifest.get('backend', {})
            handler_file = plugin_dir / backend_config.get('handler', 'handler.py')
            if not handler_file.exists():
                is_healthy = False
                issues.append("Plugin handler not found")
            
            if is_healthy:
                health_report["healthy_plugins"] += 1
            else:
                health_report["unhealthy_plugins"] += 1
                health_report["issues"].append({
                    "plugin_id": plugin.plugin_id,
                    "plugin_name": plugin.name,
                    "issues": issues
                })
        
        logger.info(f"Plugin health check completed: {health_report}")
        
        return {
            "success": True,
            "health_report": health_report,
            "message": "Plugin health monitoring completed"
        }
        
    except Exception as e:
        logger.error(f"Plugin health monitoring failed: {str(e)}")
        return {
            "success": False,
            "error": "monitoring_failed",
            "message": "Failed to monitor plugin health"
        }
    finally:
        # Cleanup connections
        if 'mongo_client' in locals():
            mongo_client.close()


@celery_app.task
def update_plugin_version_task(plugin_id: str, new_version: str, 
                              version_file_path: str, updater_id: str):
    """
    Background task to update a plugin to a new version.
    
    Args:
        plugin_id: ID of plugin to update
        new_version: New version string
        version_file_path: Path to new version file
        updater_id: ID of user updating the plugin
    """
    try:
        # Get database connections
        mongo_client = MongoClient(os.getenv('MONGODB_URI'))
        redis_client = Redis.from_url(os.getenv('REDIS_URL'))
        
        db = mongo_client.formbuilder
        
        # Get existing plugin
        plugin_doc = db.plugins.find_one({
            "plugin_id": plugin_id,
            "is_deleted": False
        })
        
        if not plugin_doc:
            return {
                "success": False,
                "error": "plugin_not_found",
                "message": f"Plugin not found: {plugin_id}"
            }
        
        plugin = Plugin(**plugin_doc)
        
        # Validate new version
        from ..utils.validators import validate_plugin_installation
        version_path = Path(version_file_path)
        manifest = validate_plugin_installation(version_path, [plugin_id], "1.0.0")
        
        # Check if version matches
        if manifest.get('version') != new_version:
            return {
                "success": False,
                "error": "version_mismatch",
                "message": f"Version mismatch: expected {new_version}, got {manifest.get('version')}"
            }
        
        # Create plugin version record
        plugin_version = {
            "plugin_id": plugin.id,
            "version": new_version,
            "manifest": manifest,
            "files_path": f"/plugins/installed/{plugin_id}",
            "status": PluginVersionStatus.ACTIVE,
            "released_at": datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
        
        # Insert version record
        db.plugin_versions.insert_one(plugin_version)
        
        # Update plugin record
        db.plugins.update_one(
            {"_id": plugin.id},
            {
                "$set": {
                    "version": new_version,
                    "manifest": manifest,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update plugin files
        plugin_dir = Path(__file__).parent.parent / "plugins" / "installed" / plugin_id
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)
        
        shutil.copytree(version_path, plugin_dir)
        
        logger.info(f"Plugin version updated: {plugin_id} to {new_version}")
        
        return {
            "success": True,
            "plugin_id": plugin_id,
            "old_version": plugin.version,
            "new_version": new_version,
            "message": "Plugin version updated successfully"
        }
        
    except ValidationError as e:
        logger.error(f"Plugin version update validation failed: {str(e)}")
        return {
            "success": False,
            "error": "validation_error",
            "message": str(e)
        }
    except Exception as e:
        logger.error(f"Plugin version update failed: {str(e)}")
        return {
            "success": False,
            "error": "update_failed",
            "message": "Failed to update plugin version"
        }
    finally:
        # Cleanup connections
        if 'mongo_client' in locals():
            mongo_client.close()


@celery_app.task
def backup_plugin_task(plugin_id: str, backup_path: str):
    """
    Background task to backup a plugin.
    
    Args:
        plugin_id: ID of plugin to backup
        backup_path: Path to backup directory
    """
    try:
        # Get database connections
        mongo_client = MongoClient(os.getenv('MONGODB_URI'))
        
        db = mongo_client.formbuilder
        
        # Get plugin
        plugin_doc = db.plugins.find_one({
            "plugin_id": plugin_id,
            "is_deleted": False
        })
        
        if not plugin_doc:
            return {
                "success": False,
                "error": "plugin_not_found",
                "message": f"Plugin not found: {plugin_id}"
            }
        
        plugin = Plugin(**plugin_doc)
        
        # Create backup directory
        backup_dir = Path(backup_path) / f"plugin_{plugin_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup plugin files
        plugin_dir = Path(__file__).parent.parent / "plugins" / "installed" / plugin_id
        if plugin_dir.exists():
            shutil.copytree(plugin_dir, backup_dir / "files")
        
        # Backup plugin data
        plugin_data = {
            "plugin": plugin_doc,
            "components": list(db.component_schemas.find({"plugin_id": plugin.id})),
            "versions": list(db.plugin_versions.find({"plugin_id": plugin.id}))
        }
        
        with open(backup_dir / "plugin_data.json", 'w') as f:
            json.dump(plugin_data, f, default=str)
        
        logger.info(f"Plugin backup completed: {plugin_id} to {backup_dir}")
        
        return {
            "success": True,
            "plugin_id": plugin_id,
            "backup_path": str(backup_dir),
            "message": "Plugin backup completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Plugin backup failed: {str(e)}")
        return {
            "success": False,
            "error": "backup_failed",
            "message": "Failed to backup plugin"
        }
    finally:
        # Cleanup connections
        if 'mongo_client' in locals():
            mongo_client.close()


# Schedule periodic tasks
@celery_app.task
def schedule_plugin_health_check():
    """Schedule periodic plugin health checks."""
    monitor_plugin_health_task.delay()


@celery_app.task
def schedule_sandbox_cleanup():
    """Schedule periodic sandbox cleanup."""
    cleanup_plugin_sandbox_task.delay()