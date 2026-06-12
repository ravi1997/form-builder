"""
Plugin Service - Business logic for plugin management.

This service handles:
- Plugin installation and uninstallation
- Plugin lifecycle management
- Plugin configuration and settings
- Plugin execution coordination
- Plugin security and permission management
"""

import os
import json
import shutil
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime
import logging
from bson import ObjectId

from ..models.plugin import (
    Plugin, PluginVersion, ComponentSchema, ConceptRegistry,
    PluginStatus, PluginInstallRequest, PluginUpdateRequest,
    ComponentSchemaCreate, BuilderType
)
from ..engines.plugin_engine import PluginEngine
from ..utils.security import validate_manifest_permissions
from ..utils.validators import (
    validate_plugin_installation, ValidationError
)
from ..utils.pagination import PaginationParams, PaginatedResult

logger = logging.getLogger(__name__)


class PluginService:
    """Service for managing plugins and their lifecycle."""
    
    def __init__(self, mongo_db, redis_client, plugin_engine: PluginEngine):
        self.db = mongo_db
        self.redis = redis_client
        self.plugin_engine = plugin_engine
        self.plugins_collection = self.db.plugins
        self.plugin_versions_collection = self.db.plugin_versions
        self.component_schemas_collection = self.db.component_schemas
        self.concept_registry_collection = self.db.concept_registry
        
        # Plugin directories
        self.plugins_root = Path(__file__).parent.parent / "plugins"
        self.builtin_dir = self.plugins_root / "builtin"
        self.installed_dir = self.plugins_root / "installed"
    
    async def initialize_concept_registry(self):
        """Initialize the concept registry with built-in concepts."""
        builtin_concepts = [
            {
                "concept_id": "form_field",
                "name": "Form Field",
                "description": "Components that can be used in form builder",
                "builder_type": BuilderType.FORM_BUILDER,
                "supported_component_types": ["text_input", "dropdown", "checkbox", "radio_group"],
                "output_format": "json",
                "version_support": True,
                "collaboration_support": True,
                "is_system": True
            },
            {
                "concept_id": "analysis_node",
                "name": "Analysis Node",
                "description": "Nodes that can be used in analysis coder",
                "builder_type": BuilderType.ANALYSIS_CODER,
                "supported_component_types": ["filter", "sort", "group_by", "join"],
                "output_format": "dataframe",
                "version_support": True,
                "collaboration_support": True,
                "is_system": True
            },
            {
                "concept_id": "dashboard_widget",
                "name": "Dashboard Widget",
                "description": "Widgets that can be used in dashboard builder",
                "builder_type": BuilderType.DASHBOARD_BUILDER,
                "supported_component_types": ["kpi_card", "chart", "table", "filter"],
                "output_format": "json",
                "version_support": True,
                "collaboration_support": True,
                "is_system": True
            }
        ]
        
        for concept_data in builtin_concepts:
            existing = await self.concept_registry_collection.find_one({
                "concept_id": concept_data["concept_id"]
            })
            
            if not existing:
                concept = ConceptRegistry(**concept_data)
                await self.concept_registry_collection.insert_one(concept.to_dict())
                logger.info(f"Created concept registry entry: {concept_data['concept_id']}")
    
    async def install_plugin(self, request: PluginInstallRequest, installer_id: ObjectId) -> Plugin:
        """
        Install a new plugin.
        
        Args:
            request: Plugin installation request
            installer_id: ID of user installing the plugin
            
        Returns:
            Installed plugin
            
        Raises:
            ValidationError: If plugin validation fails
        """
        # Get current platform version
        platform_version = await self._get_platform_version()
        
        # Get list of installed plugins
        installed_plugins = await self._get_installed_plugin_ids()
        
        # Validate plugin file
        plugin_path = Path(request.plugin_file)
        if not plugin_path.exists():
            raise ValidationError(f"Plugin file not found: {request.plugin_file}")
        
        try:
            # Complete validation
            manifest = validate_plugin_installation(plugin_path, installed_plugins, platform_version)
            
            # Check permissions if not auto-approved
            if not request.auto_approve_permissions:
                permissions = manifest.get('permissions', [])
                if permissions:
                    # In a real implementation, this would trigger an admin approval workflow
                    # For now, we'll just log and continue
                    logger.warning(f"Plugin requires permissions that need approval: {permissions}")
            
            # Install the plugin
            plugin = await self.plugin_engine.install_plugin(str(plugin_path), installer_id)
            
            # Log the installation
            await self._log_plugin_action("install", plugin.id, installer_id)
            
            logger.info(f"Plugin installed successfully: {plugin.plugin_id}")
            return plugin
            
        except Exception as e:
            logger.error(f"Plugin installation failed: {str(e)}")
            raise ValidationError(f"Plugin installation failed: {str(e)}")
    
    async def uninstall_plugin(self, plugin_id: str, uninstaller_id: ObjectId) -> bool:
        """
        Uninstall a plugin.
        
        Args:
            plugin_id: ID of plugin to uninstall
            uninstaller_id: ID of user uninstalling the plugin
            
        Returns:
            True if successful
            
        Raises:
            ValidationError: If plugin cannot be uninstalled
        """
        # Get plugin
        plugin = await self._get_plugin_by_id(plugin_id)
        if not plugin:
            raise ValidationError(f"Plugin not found: {plugin_id}")
        
        # Check if it's a system plugin
        if plugin.is_system:
            raise ValidationError("Cannot uninstall system plugin")
        
        # Check if plugin is in use
        if await self._is_plugin_in_use(plugin_id):
            raise ValidationError("Plugin is currently in use and cannot be uninstalled")
        
        try:
            # Uninstall the plugin
            success = await self.plugin_engine.uninstall_plugin(plugin_id)
            
            if success:
                # Log the uninstallation
                await self._log_plugin_action("uninstall", plugin.id, uninstaller_id)
                logger.info(f"Plugin uninstalled successfully: {plugin_id}")
                return True
            else:
                raise ValidationError("Plugin uninstallation failed")
                
        except Exception as e:
            logger.error(f"Plugin uninstallation failed: {str(e)}")
            raise ValidationError(f"Plugin uninstallation failed: {str(e)}")
    
    async def update_plugin(self, plugin_id: str, request: PluginUpdateRequest, 
                           updater_id: ObjectId) -> Plugin:
        """
        Update plugin configuration.
        
        Args:
            plugin_id: ID of plugin to update
            request: Update request data
            updater_id: ID of user making the update
            
        Returns:
            Updated plugin
        """
        # Get plugin
        plugin = await self._get_plugin_by_id(plugin_id)
        if not plugin:
            raise ValidationError(f"Plugin not found: {plugin_id}")
        
        # Update fields
        update_data = {}
        if request.status is not None:
            update_data["status"] = request.status
        if request.permissions is not None:
            # Validate permissions
            try:
                validate_manifest_permissions({"permissions": request.permissions})
                update_data["permissions"] = request.permissions
            except Exception as e:
                raise ValidationError(f"Invalid permissions: {str(e)}")
        
        if not update_data:
            raise ValidationError("No fields to update")
        
        # Update in database
        result = await self.plugins_collection.update_one(
            {"_id": plugin.id, "is_deleted": False},
            {"$set": {**update_data, "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count == 0:
            raise ValidationError("Plugin update failed")
        
        # Get updated plugin
        updated_plugin = await self._get_plugin_by_id(plugin_id)
        
        # Log the update
        await self._log_plugin_action("update", plugin.id, updater_id)
        
        logger.info(f"Plugin updated successfully: {plugin_id}")
        return updated_plugin
    
    async def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """
        Get plugin by ID.
        
        Args:
            plugin_id: Plugin ID
            
        Returns:
            Plugin or None if not found
        """
        plugin_doc = await self.plugins_collection.find_one({
            "plugin_id": plugin_id,
            "is_deleted": False
        })
        
        if not plugin_doc:
            return None
        
        return Plugin(**plugin_doc)
    
    async def list_plugins(self, params: PaginationParams) -> PaginatedResult[Plugin]:
        """
        List plugins with pagination.
        
        Args:
            params: Pagination parameters
            
        Returns:
            Paginated list of plugins
        """
        # Build query
        query = {"is_deleted": False}
        
        # Get total count
        total = await self.plugins_collection.count_documents(query)
        
        # Get paginated results
        skip = (params.page - 1) * params.per_page
        cursor = self.plugins_collection.find(query).skip(skip).limit(params.per_page)
        
        if params.sort_by:
            sort_order = 1 if params.sort_order == "asc" else -1
            cursor = cursor.sort(params.sort_by, sort_order)
        
        plugins = []
        async for doc in cursor:
            plugins.append(Plugin(**doc))
        
        return PaginatedResult(
            items=plugins,
            total=total,
            page=params.page,
            per_page=params.per_page
        )
    
    async def get_plugin_components(self, plugin_id: str, concept_id: str) -> List[ComponentSchema]:
        """
        Get components for a specific plugin and concept.
        
        Args:
            plugin_id: Plugin ID
            concept_id: Concept ID
            
        Returns:
            List of component schemas
        """
        plugin = await self._get_plugin_by_id(plugin_id)
        if not plugin:
            raise ValidationError(f"Plugin not found: {plugin_id}")
        
        # Get components from database
        cursor = self.component_schemas_collection.find({
            "plugin_id": plugin.id,
            "concept_id": concept_id
        })
        
        components = []
        async for doc in cursor:
            components.append(ComponentSchema(**doc))
        
        return components
    
    async def get_concept_components(self, concept_id: str) -> List[Dict[str, Any]]:
        """
        Get all components for a specific concept across all plugins.
        
        Args:
            concept_id: Concept ID
            
        Returns:
            List of component dictionaries
        """
        # Get all active plugins that target this concept
        plugin_cursor = self.plugins_collection.find({
            "concept_targets": concept_id,
            "status": PluginStatus.ACTIVE,
            "is_deleted": False
        })
        
        components = []
        async for plugin_doc in plugin_cursor:
            plugin = Plugin(**plugin_doc)
            
            # Get components for this plugin and concept
            plugin_components = await self.get_plugin_components(plugin.plugin_id, concept_id)
            
            for component in plugin_components:
                components.append({
                    "plugin_id": plugin.plugin_id,
                    "plugin_name": plugin.name,
                    "plugin_version": plugin.version,
                    "component_type": component.component_type,
                    "display_name": component.display_name,
                    "description": component.description,
                    "icon_path": component.icon_path,
                    "properties": component.properties,
                    "input_ports": component.input_ports,
                    "output_ports": component.output_ports,
                    "offline_support": component.offline_support
                })
        
        return components
    
    async def execute_plugin_method(self, plugin_id: str, method_name: str,
                                  *args, org_id: Optional[ObjectId] = None, **kwargs) -> Any:
        """
        Execute a method from a plugin.
        
        Args:
            plugin_id: Plugin ID
            method_name: Method name to execute
            org_id: Organization ID for scoping
            *args, **kwargs: Method arguments
            
        Returns:
            Method result
        """
        # Check if plugin is active
        plugin = await self._get_plugin_by_id(plugin_id)
        if not plugin:
            raise ValidationError(f"Plugin not found: {plugin_id}")
        
        if plugin.status != PluginStatus.ACTIVE:
            raise ValidationError(f"Plugin is not active: {plugin_id}")
        
        # Execute method through plugin engine
        try:
            result = await self.plugin_engine.execute_plugin_method(
                plugin_id, method_name, *args, org_id=org_id, **kwargs
            )
            return result
        except Exception as e:
            logger.error(f"Plugin method execution failed: {str(e)}")
            raise ValidationError(f"Plugin method execution failed: {str(e)}")
    
    async def get_plugin_statistics(self) -> Dict[str, Any]:
        """
        Get plugin statistics.
        
        Returns:
            Dictionary with plugin statistics
        """
        # Get counts
        total_plugins = await self.plugins_collection.count_documents({"is_deleted": False})
        active_plugins = await self.plugins_collection.count_documents({
            "status": PluginStatus.ACTIVE,
            "is_deleted": False
        })
        
        # Get concept counts
        concepts = await self.concept_registry_collection.count_documents({})
        
        # Get component counts
        total_components = await self.component_schemas_collection.count_documents({})
        
        return {
            "total_plugins": total_plugins,
            "active_plugins": active_plugins,
            "inactive_plugins": total_plugins - active_plugins,
            "total_concepts": concepts,
            "total_components": total_components,
            "system_plugins": await self.plugins_collection.count_documents({
                "is_system": True,
                "is_deleted": False
            })
        }
    
    async def _get_plugin_by_id(self, plugin_id: str) -> Optional[Plugin]:
        """Get plugin by ID from database."""
        doc = await self.plugins_collection.find_one({
            "plugin_id": plugin_id,
            "is_deleted": False
        })
        
        if not doc:
            return None
        
        return Plugin(**doc)
    
    async def _get_installed_plugin_ids(self) -> List[str]:
        """Get list of installed plugin IDs."""
        cursor = self.plugins_collection.find(
            {"is_deleted": False},
            {"plugin_id": 1}
        )
        
        plugin_ids = []
        async for doc in cursor:
            plugin_ids.append(doc["plugin_id"])
        
        return plugin_ids
    
    async def _get_platform_version(self) -> str:
        """Get current platform version."""
        # This would typically come from system_config
        # For now, return a default
        return "1.0.0"
    
    async def _is_plugin_in_use(self, plugin_id: str) -> bool:
        """Check if plugin is currently in use."""
        # This would check if any forms, analyses, or dashboards are using this plugin
        # For now, return False (not in use)
        return False
    
    async def _log_plugin_action(self, action: str, plugin_id: ObjectId, actor_id: ObjectId):
        """Log plugin action to audit log."""
        # This would create an audit log entry
        # For now, just log to the application log
        logger.info(f"Plugin action: {action}, plugin_id: {plugin_id}, actor_id: {actor_id}")
    
    async def create_component_schema(self, request: ComponentSchemaCreate) -> ComponentSchema:
        """
        Create a new component schema.
        
        Args:
            request: Component schema creation request
            
        Returns:
            Created component schema
        """
        # Validate plugin exists
        plugin_doc = await self.plugins_collection.find_one({
            "_id": request.plugin_id,
            "is_deleted": False
        })
        
        if not plugin_doc:
            raise ValidationError("Plugin not found")
        
        # Create component schema
        component_schema = ComponentSchema(
            plugin_id=request.plugin_id,
            plugin_version=request.plugin_version,
            concept_id=request.concept_id,
            component_type=request.component_type,
            display_name=request.display_name,
            description=request.description,
            icon_path=request.icon_path,
            composition=request.composition,
            properties=request.properties,
            input_ports=request.input_ports,
            output_ports=request.output_ports,
            widget_config=request.widget_config,
            preview_schema=request.preview_schema,
            offline_support=request.offline_support
        )
        
        # Save to database
        result = await self.component_schemas_collection.insert_one(
            component_schema.to_dict()
        )
        
        component_schema.id = result.inserted_id
        
        logger.info(f"Component schema created: {request.component_type}")
        return component_schema