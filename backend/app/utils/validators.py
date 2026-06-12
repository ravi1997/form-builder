"""
Validation utilities for plugin system.

This module provides:
- Plugin manifest validation
- Component schema validation
- Plugin installation validation
"""

import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from pydantic import ValidationError

from ..models.plugin import (
    ConceptRegistry, Plugin, ComponentSchema, 
    PrimitiveRef, PropertyDef, PortDef, BuilderType
)
from .security import (
    validate_manifest_permissions, 
    validate_component_schema_security,
    PluginSecurityError
)


class ValidationError(Exception):
    """Validation error for plugins."""
    pass


def validate_plugin_manifest(manifest: Dict[str, Any]) -> bool:
    """
    Validate plugin manifest structure and content.
    
    Args:
        manifest: Plugin manifest dictionary
        
    Returns:
        True if manifest is valid
        
    Raises:
        ValidationError: If manifest is invalid
    """
    required_fields = [
        'plugin_id', 'name', 'version', 'min_platform_version',
        'author', 'description', 'concept_targets', 'permissions',
        'backend', 'components'
    ]
    
    # Check required fields
    for field in required_fields:
        if field not in manifest:
            raise ValidationError(f"Required field missing: {field}")
    
    # Validate plugin_id format
    plugin_id = manifest['plugin_id']
    if not re.match(r'^[a-z0-9_-]+$', plugin_id):
        raise ValidationError(
            "plugin_id must contain only lowercase letters, numbers, hyphens, and underscores"
        )
    
    # Validate version format (semantic versioning)
    version = manifest['version']
    if not re.match(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9-]+)?(\+[a-zA-Z0-9-]+)?$', version):
        raise ValidationError(
            "version must follow semantic versioning (e.g., 1.0.0, 2.1.3-beta)"
        )
    
    # Validate author structure
    author = manifest['author']
    if not isinstance(author, dict) or 'name' not in author:
        raise ValidationError("author must be a dictionary with 'name' field")
    
    # Validate concept_targets
    concept_targets = manifest['concept_targets']
    if not isinstance(concept_targets, list) or not concept_targets:
        raise ValidationError("concept_targets must be a non-empty list")
    
    # Validate permissions
    try:
        validate_manifest_permissions(manifest)
    except PluginSecurityError as e:
        raise ValidationError(f"Permission validation failed: {str(e)}")
    
    # Validate backend configuration
    backend = manifest['backend']
    if not isinstance(backend, dict) or 'handler' not in backend:
        raise ValidationError("backend must be a dictionary with 'handler' field")
    
    # Validate components
    components = manifest['components']
    if not isinstance(components, list):
        raise ValidationError("components must be a list")
    
    for component in components:
        validate_component_definition(component)
    
    return True


def validate_component_definition(component: Dict[str, Any]) -> bool:
    """
    Validate component definition in manifest.
    
    Args:
        component: Component definition dictionary
        
    Returns:
        True if component definition is valid
        
    Raises:
        ValidationError: If component definition is invalid
    """
    required_fields = ['type', 'schema']
    
    for field in required_fields:
        if field not in component:
            raise ValidationError(f"Component missing required field: {field}")
    
    # Validate component type
    component_type = component['type']
    if not re.match(r'^[a-z0-9_-]+$', component_type):
        raise ValidationError(
            "component type must contain only lowercase letters, numbers, hyphens, and underscores"
        )
    
    return True


def validate_component_schema(schema: Dict[str, Any]) -> bool:
    """
    Validate component schema structure and content.
    
    Args:
        schema: Component schema dictionary
        
    Returns:
        True if schema is valid
        
    Raises:
        ValidationError: If schema is invalid
    """
    required_fields = [
        'type', 'display_name', 'concept', 'properties'
    ]
    
    for field in required_fields:
        if field not in schema:
            raise ValidationError(f"Component schema missing required field: {field}")
    
    # Validate security
    try:
        validate_component_schema_security(schema)
    except PluginSecurityError as e:
        raise ValidationError(f"Security validation failed: {str(e)}")
    
    # Validate properties
    properties = schema.get('properties', [])
    if not isinstance(properties, list):
        raise ValidationError("properties must be a list")
    
    for prop in properties:
        validate_property_definition(prop)
    
    # Validate input/output ports if present
    if 'input_ports' in schema:
        validate_ports(schema['input_ports'], 'input')
    
    if 'output_ports' in schema:
        validate_ports(schema['output_ports'], 'output')
    
    # Validate composition if present
    if 'composition' in schema:
        validate_composition(schema['composition'])
    
    return True


def validate_property_definition(prop: Dict[str, Any]) -> bool:
    """
    Validate property definition in component schema.
    
    Args:
        prop: Property definition dictionary
        
    Returns:
        True if property definition is valid
        
    Raises:
        ValidationError: If property definition is invalid
    """
    required_fields = ['key', 'label', 'type']
    
    for field in required_fields:
        if field not in prop:
            raise ValidationError(f"Property missing required field: {field}")
    
    # Validate property key
    key = prop['key']
    if not re.match(r'^[a-z0-9_-]+$', key):
        raise ValidationError(
            "property key must contain only lowercase letters, numbers, hyphens, and underscores"
        )
    
    # Validate property type
    prop_type = prop['type']
    allowed_types = ['string', 'number', 'boolean', 'enum', 'color', 'object', 'array']
    if prop_type not in allowed_types:
        raise ValidationError(f"Invalid property type: {prop_type}. Allowed: {allowed_types}")
    
    # Validate enum options
    if prop_type == 'enum' and 'options' not in prop:
        raise ValidationError("Enum property must have 'options' field")
    
    if prop_type == 'enum' and not isinstance(prop.get('options', []), list):
        raise ValidationError("Enum options must be a list")
    
    return True


def validate_ports(ports: List[Dict[str, Any]], port_type: str) -> bool:
    """
    Validate port definitions in component schema.
    
    Args:
        ports: List of port definitions
        port_type: Type of ports ('input' or 'output')
        
    Returns:
        True if ports are valid
        
    Raises:
        ValidationError: If ports are invalid
    """
    if not isinstance(ports, list):
        raise ValidationError(f"{port_type}_ports must be a list")
    
    for port in ports:
        required_fields = ['id', 'label', 'data_type']
        
        for field in required_fields:
            if field not in port:
                raise ValidationError(f"Port missing required field: {field}")
        
        # Validate port ID
        port_id = port['id']
        if not re.match(r'^[a-z0-9_-]+$', port_id):
            raise ValidationError(
                "port ID must contain only lowercase letters, numbers, hyphens, and underscores"
            )
    
    return True


def validate_composition(composition: List[Dict[str, Any]]) -> bool:
    """
    Validate composition references in component schema.
    
    Args:
        composition: List of composition references
        
    Returns:
        True if composition is valid
        
    Raises:
        ValidationError: If composition is invalid
    """
    if not isinstance(composition, list):
        raise ValidationError("composition must be a list")
    
    for comp_ref in composition:
        if not isinstance(comp_ref, dict):
            raise ValidationError("Composition reference must be a dictionary")
        
        required_fields = ['primitive', 'property_key']
        
        for field in required_fields:
            if field not in comp_ref:
                raise ValidationError(f"Composition reference missing required field: {field}")
    
    return True


def validate_plugin_files(plugin_dir: Path) -> bool:
    """
    Validate plugin file structure.
    
    Args:
        plugin_dir: Path to plugin directory
        
    Returns:
        True if file structure is valid
        
    Raises:
        ValidationError: If file structure is invalid
    """
    # Check if directory exists
    if not plugin_dir.exists():
        raise ValidationError(f"Plugin directory does not exist: {plugin_dir}")
    
    # Check for manifest.json
    manifest_file = plugin_dir / "manifest.json"
    if not manifest_file.exists():
        raise ValidationError("manifest.json not found in plugin directory")
    
    # Load and validate manifest
    try:
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        validate_plugin_manifest(manifest)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in manifest.json: {str(e)}")
    except Exception as e:
        raise ValidationError(f"Manifest validation failed: {str(e)}")
    
    # Check for component schema files
    components = manifest.get('components', [])
    for component in components:
        schema_file = plugin_dir / component.get('schema')
        if not schema_file.exists():
            raise ValidationError(f"Component schema file not found: {schema_file}")
        
        # Validate schema file
        try:
            with open(schema_file, 'r') as f:
                schema = json.load(f)
            validate_component_schema(schema)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in {schema_file}: {str(e)}")
        except Exception as e:
            raise ValidationError(f"Schema validation failed for {schema_file}: {str(e)}")
    
    # Check for backend handler file
    backend = manifest.get('backend', {})
    handler_file = plugin_dir / backend.get('handler', 'handler.py')
    if not handler_file.exists():
        raise ValidationError(f"Backend handler file not found: {handler_file}")
    
    # Check for requirements.txt if specified
    requirements = backend.get('requirements', [])
    if requirements:
        requirements_file = plugin_dir / "requirements.txt"
        if not requirements_file.exists():
            raise ValidationError("requirements.txt not found but requirements specified in manifest")
    
    return True


def validate_plugin_compatibility(manifest: Dict[str, Any], platform_version: str) -> bool:
    """
    Validate plugin compatibility with platform version.
    
    Args:
        manifest: Plugin manifest dictionary
        platform_version: Current platform version
        
    Returns:
        True if plugin is compatible
        
    Raises:
        ValidationError: If plugin is not compatible
    """
    min_version = manifest.get('min_platform_version')
    if not min_version:
        raise ValidationError("min_platform_version not specified in manifest")
    
    # Simple version comparison (can be enhanced with proper semantic version parsing)
    if min_version > platform_version:
        raise ValidationError(
            f"Plugin requires platform version {min_version} or higher, "
            f"but current version is {platform_version}"
        )
    
    return True


def validate_plugin_dependencies(manifest: Dict[str, Any], installed_plugins: List[str]) -> bool:
    """
    Validate plugin dependencies.
    
    Args:
        manifest: Plugin manifest dictionary
        installed_plugins: List of installed plugin IDs
        
    Returns:
        True if dependencies are satisfied
        
    Raises:
        ValidationError: If dependencies are not satisfied
    """
    dependencies = manifest.get('dependencies', {})
    
    for dep_plugin_id, version_constraint in dependencies.items():
        if dep_plugin_id not in installed_plugins:
            raise ValidationError(f"Required dependency not installed: {dep_plugin_id}")
        
        # For now, just check existence. Can be enhanced with version constraint validation
        # version_constraint could be like ">=1.0.0", "==2.1.0", etc.
    
    return True


def validate_plugin_uniqueness(plugin_id: str, existing_plugins: List[str]) -> bool:
    """
    Validate that plugin ID is unique.
    
    Args:
        plugin_id: Plugin ID to validate
        existing_plugins: List of existing plugin IDs
        
    Returns:
        True if plugin ID is unique
        
    Raises:
        ValidationError: If plugin ID is not unique
    """
    if plugin_id in existing_plugins:
        raise ValidationError(f"Plugin ID already exists: {plugin_id}")
    
    return True


def validate_plugin_installation(plugin_dir: Path, installed_plugins: List[str], 
                               platform_version: str) -> Dict[str, Any]:
    """
    Complete validation for plugin installation.
    
    Args:
        plugin_dir: Path to plugin directory
        installed_plugins: List of installed plugin IDs
        platform_version: Current platform version
        
    Returns:
        Validated plugin manifest
        
    Raises:
        ValidationError: If validation fails
    """
    # Validate file structure
    validate_plugin_files(plugin_dir)
    
    # Load manifest
    manifest_file = plugin_dir / "manifest.json"
    with open(manifest_file, 'r') as f:
        manifest = json.load(f)
    
    # Validate manifest
    validate_plugin_manifest(manifest)
    
    # Validate compatibility
    validate_plugin_compatibility(manifest, platform_version)
    
    # Validate dependencies
    validate_plugin_dependencies(manifest, installed_plugins)
    
    # Validate uniqueness
    plugin_id = manifest['plugin_id']
    validate_plugin_uniqueness(plugin_id, installed_plugins)
    
    return manifest