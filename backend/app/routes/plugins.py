"""
Plugin API Routes - REST endpoints for plugin management.

This module provides:
- Plugin installation and uninstallation endpoints
- Plugin listing and retrieval endpoints
- Plugin component endpoints
- Plugin execution endpoints
- Plugin management endpoints
"""

from typing import List, Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
import logging

from ..models.plugin import (
    Plugin, PluginInstallRequest, PluginUpdateRequest,
    ComponentSchemaCreate, ComponentSchema
)
from ..services.plugin_service import PluginService
from ..utils.pagination import PaginationParams
from ..utils.security import require_permission
from ..utils.validators import ValidationError

logger = logging.getLogger(__name__)

# Create blueprint
plugin_bp = Blueprint('plugins', __name__, url_prefix='/api/plugins')


def get_plugin_service() -> PluginService:
    """Get plugin service instance."""
    return current_app.plugin_service


@plugin_bp.route('/', methods=['GET'])
@jwt_required()
async def list_plugins():
    """List all plugins."""
    try:
        # Parse pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        params = PaginationParams(
            page=page,
            per_page=per_page,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        service = get_plugin_service()
        result = await service.list_plugins(params)
        
        return jsonify({
            "success": True,
            "data": {
                "plugins": [plugin.dict() for plugin in result.items],
                "pagination": {
                    "page": result.page,
                    "per_page": result.per_page,
                    "total": result.total,
                    "pages": (result.total + result.per_page - 1) // result.per_page
                }
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing plugins: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "Failed to list plugins"
            }
        }), 500


@plugin_bp.route('/<plugin_id>', methods=['GET'])
@jwt_required()
async def get_plugin(plugin_id: str):
    """Get a specific plugin."""
    try:
        service = get_plugin_service()
        plugin = await service.get_plugin(plugin_id)
        
        if not plugin:
            return jsonify({
                "success": False,
                "error": {
                    "code": "not_found",
                    "message": "Plugin not found"
                }
            }), 404
        
        return jsonify({
            "success": True,
            "data": plugin.dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting plugin: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "Failed to get plugin"
            }
        }), 500


@plugin_bp.route('/', methods=['POST'])
@jwt_required()
@require_permission('plugin:install')
async def install_plugin():
    """Install a new plugin."""
    try:
        # Get current user ID
        current_user_id = get_jwt_identity()
        
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "invalid_request",
                    "message": "No request data provided"
                }
            }), 400
        
        # Validate request
        try:
            install_request = PluginInstallRequest(**data)
        except Exception as e:
            return jsonify({
                "success": False,
                "error": {
                    "code": "validation_error",
                    "message": f"Invalid request data: {str(e)}"
                }
            }), 400
        
        # Install plugin
        service = get_plugin_service()
        plugin = await service.install_plugin(install_request, ObjectId(current_user_id))
        
        return jsonify({
            "success": True,
            "data": plugin.dict(),
            "message": "Plugin installed successfully"
        }), 201
        
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "validation_error",
                "message": str(e)
            }
        }), 400
    except Exception as e:
        logger.error(f"Error installing plugin: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "Failed to install plugin"
            }
        }), 500


@plugin_bp.route('/<plugin_id>', methods=['PUT'])
@jwt_required()
@require_permission('plugin:update')
async def update_plugin(plugin_id: str):
    """Update a plugin."""
    try:
        # Get current user ID
        current_user_id = get_jwt_identity()
        
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "invalid_request",
                    "message": "No request data provided"
                }
            }), 400
        
        # Validate request
        try:
            update_request = PluginUpdateRequest(**data)
        except Exception as e:
            return jsonify({
                "success": False,
                "error": {
                    "code": "validation_error",
                    "message": f"Invalid request data: {str(e)}"
                }
            }), 400
        
        # Update plugin
        service = get_plugin_service()
        plugin = await service.update_plugin(plugin_id, update_request, ObjectId(current_user_id))
        
        return jsonify({
            "success": True,
            "data": plugin.dict(),
            "message": "Plugin updated successfully"
        }), 200
        
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "validation_error",
                "message": str(e)
            }
        }), 400
    except Exception as e:
        logger.error(f"Error updating plugin: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "Failed to update plugin"
            }
        }), 500


@plugin_bp.route('/<plugin_id>', methods=['DELETE'])
@jwt_required()
@require_permission('plugin:uninstall')
async def uninstall_plugin(plugin_id: str):
    """Uninstall a plugin."""
    try:
        # Get current user ID
        current_user_id = get_jwt_identity()
        
        # Uninstall plugin
        service = get_plugin_service()
        success = await service.uninstall_plugin(plugin_id, ObjectId(current_user_id))
        
        if success:
            return jsonify({
                "success": True,
                "message": "Plugin uninstalled successfully"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": {
                    "code": "uninstall_failed",
                    "message": "Failed to uninstall plugin"
                }
            }), 400
        
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "validation_error",
                "message": str(e)
            }
        }), 400
    except Exception as e:
        logger.error(f"Error uninstalling plugin: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "Failed to uninstall plugin"
            }
        }), 500


@plugin_bp.route('/<plugin_id>/components/<concept_id>', methods=['GET'])
@jwt_required()
async def get_plugin_components(plugin_id: str, concept_id: str):
    """Get components for a specific plugin and concept."""
    try:
        service = get_plugin_service()
        components = await service.get_plugin_components(plugin_id, concept_id)
        
        return jsonify({
            "success": True,
            "data": [component.dict() for component in components]
        }), 200
        
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "validation_error",
                "message": str(e)
            }
        }), 400
    except Exception as e:
        logger.error(f"Error getting plugin components: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "Failed to get plugin components"
            }
        }), 500


@plugin_bp.route('/concepts/<concept_id>/components', methods=['GET'])
@jwt_required()
async def get_concept_components(concept_id: str):
    """Get all components for a specific concept."""
    try:
        service = get_plugin_service()
        components = await service.get_concept_components(concept_id)
        
        return jsonify({
            "success": True,
            "data": components
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting concept components: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "Failed to get concept components"
            }
        }), 500


@plugin_bp.route('/<plugin_id>/execute/<method_name>', methods=['POST'])
@jwt_required()
@require_permission('plugin:execute')
async def execute_plugin_method(plugin_id: str, method_name: str):
    """Execute a method from a plugin."""
    try:
        # Get current user ID and org ID
        current_user_id = get_jwt_identity()
        org_id = request.headers.get('X-Org-ID')  # Org ID from header
        
        # Parse request body for arguments
        data = request.get_json() or {}
        args = data.get('args', [])
        kwargs = data.get('kwargs', {})
        
        # Execute method
        service = get_plugin_service()
        result = await service.execute_plugin_method(
            plugin_id, method_name, *args, 
            org_id=ObjectId(org_id) if org_id else None, 
            **kwargs
        )
        
        return jsonify({
            "success": True,
            "data": result
        }), 200
        
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "validation_error",
                "message": str(e)
            }
        }), 400
    except Exception as e:
        logger.error(f"Error executing plugin method: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "execution_error",
                "message": "Failed to execute plugin method"
            }
        }), 500


@plugin_bp.route('/statistics', methods=['GET'])
@jwt_required()
@require_permission('plugin:read')
async def get_plugin_statistics():
    """Get plugin statistics."""
    try:
        service = get_plugin_service()
        stats = await service.get_plugin_statistics()
        
        return jsonify({
            "success": True,
            "data": stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting plugin statistics: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "Failed to get plugin statistics"
            }
        }), 500


@plugin_bp.route('/components', methods=['POST'])
@jwt_required()
@require_permission('plugin:manage')
async def create_component_schema():
    """Create a new component schema."""
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": {
                    "code": "invalid_request",
                    "message": "No request data provided"
                }
            }), 400
        
        # Validate request
        try:
            create_request = ComponentSchemaCreate(**data)
        except Exception as e:
            return jsonify({
                "success": False,
                "error": {
                    "code": "validation_error",
                    "message": f"Invalid request data: {str(e)}"
                }
            }), 400
        
        # Create component schema
        service = get_plugin_service()
        component_schema = await service.create_component_schema(create_request)
        
        return jsonify({
            "success": True,
            "data": component_schema.dict(),
            "message": "Component schema created successfully"
        }), 201
        
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": {
                "code": "validation_error",
                "message": str(e)
            }
        }), 400
    except Exception as e:
        logger.error(f"Error creating component schema: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "Failed to create component schema"
            }
        }), 500


@plugin_bp.route('/health', methods=['GET'])
@jwt_required()
async def plugin_health_check():
    """Health check for plugin system."""
    try:
        service = get_plugin_service()
        
        # Check if plugin engine is available
        if service.plugin_engine:
            return jsonify({
                "success": True,
                "data": {
                    "status": "healthy",
                    "plugin_engine": "available"
                }
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": {
                    "code": "service_unavailable",
                    "message": "Plugin engine not available"
                }
            }), 503
        
    except Exception as e:
        logger.error(f"Error in plugin health check: {str(e)}")
        return jsonify({
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "Plugin health check failed"
            }
        }), 500