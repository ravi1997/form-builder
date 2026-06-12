from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
from bson import ObjectId
from .base import BaseDBModel, PyObjectId


class BuilderType(str, Enum):
    FORM_BUILDER = "form_builder"
    ANALYSIS_CODER = "analysis_coder"
    DASHBOARD_BUILDER = "dashboard_builder"


class PluginStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    UNLOADED = "unloaded"


class PluginVersionStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    YANKED = "yanked"


class ConceptRegistry(BaseDBModel):
    """Model for concept_registry collection."""
    
    org_id: Optional[PyObjectId] = Field(None, description="Always null for system-level")
    concept_id: str = Field(..., description="e.g., 'form_field', 'analysis_node', 'dashboard_widget'")
    name: str = Field(...)
    description: str = Field(...)
    builder_type: BuilderType = Field(...)
    supported_component_types: List[str] = Field(default_factory=list)
    output_format: str = Field(...)
    version_support: bool = Field(default=False)
    collaboration_support: bool = Field(default=False)
    is_system: bool = Field(default=True, description="True = cannot be deleted")


class Plugin(BaseDBModel):
    """Model for plugins collection."""
    
    org_id: Optional[PyObjectId] = Field(None, description="Always null for system-level")
    plugin_id: str = Field(..., unique=True, description="Unique slug")
    name: str = Field(...)
    description: str = Field(...)
    author: str = Field(...)
    version: str = Field(..., description="Semver version")
    manifest: Dict[str, Any] = Field(..., description="Full manifest JSON")
    status: PluginStatus = Field(default=PluginStatus.ACTIVE)
    concept_targets: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    installed_at: Optional[datetime] = Field(None)
    installed_by: Optional[PyObjectId] = Field(None)


class PluginVersion(BaseModel):
    """Model for plugin_versions collection."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    plugin_id: PyObjectId = Field(...)
    version: str = Field(...)
    manifest: Dict[str, Any] = Field(...)
    files_path: str = Field(..., description="Path to this version's files on server")
    status: PluginVersionStatus = Field(default=PluginVersionStatus.ACTIVE)
    released_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for MongoDB operations."""
        data = self.dict(by_alias=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data


class PrimitiveRef(BaseModel):
    """Reference to primitive component for form field composition."""
    
    primitive: str = Field(..., description="Primitive component type")
    property_key: str = Field(..., description="Property key to map to")
    label_from_property: Optional[str] = Field(None)
    visibility: Optional[str] = Field(None)


class PropertyDef(BaseModel):
    """Property definition for component configuration."""
    
    key: str = Field(...)
    label: str = Field(...)
    type: str = Field(..., description="string, number, boolean, enum, color, object, array")
    default: Any = Field(None)
    required: bool = Field(default=False)
    options: List[Any] = Field(default_factory=list)
    group: str = Field(default="General")


class PortDef(BaseModel):
    """Port definition for analysis nodes."""
    
    id: str = Field(...)
    label: str = Field(...)
    data_type: str = Field(...)


class ComponentSchema(BaseModel):
    """Model for component_schemas collection."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    plugin_id: PyObjectId = Field(...)
    plugin_version: str = Field(...)
    concept_id: str = Field(...)
    component_type: str = Field(...)
    display_name: str = Field(...)
    description: str = Field(...)
    icon_path: Optional[str] = Field(None)
    composition: List[PrimitiveRef] = Field(default_factory=list)
    properties: List[PropertyDef] = Field(default_factory=list)
    input_ports: List[PortDef] = Field(default_factory=list)
    output_ports: List[PortDef] = Field(default_factory=list)
    widget_config: Dict[str, Any] = Field(default_factory=dict)
    preview_schema: Dict[str, Any] = Field(default_factory=dict)
    offline_support: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for MongoDB operations."""
        data = self.dict(by_alias=True)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data