from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from .base import PyObjectId, SystemConfigModel


class AuditLogModel(BaseModel):
    """Model for audit_logs collection (append-only, never soft-deleted)."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    org_id: Optional[PyObjectId] = Field(None)
    project_id: Optional[PyObjectId] = Field(None, description="Optional project context")
    entity_type: str = Field(..., description="Type of entity being audited")
    entity_id: PyObjectId = Field(..., description="ID of the entity being audited")
    action: str = Field(..., description="Action performed on the entity")
    actor_id: Optional[PyObjectId] = Field(None, description="User who performed the action")
    actor_role: Optional[str] = Field(None, description="Role of the actor at time of action")
    ip_address: Optional[str] = Field(None)
    user_agent: Optional[str] = Field(None)
    before: Optional[Dict[str, Any]] = Field(None, description="Snapshot before change")
    after: Optional[Dict[str, Any]] = Field(None, description="Snapshot after change")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    archived: bool = Field(default=False)

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


class SystemConfigCreate(BaseModel):
    """Model for creating system configuration."""
    
    key: str = Field(..., description="Unique configuration key")
    value: Any = Field(..., description="Configuration value")
    updated_by: Optional[PyObjectId] = Field(None)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str
        }


class SystemConfigUpdate(BaseModel):
    """Model for updating system configuration."""
    
    value: Any = Field(..., description="New configuration value")
    updated_by: Optional[PyObjectId] = Field(None)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str
        }


class AuditLogCreate(BaseModel):
    """Model for creating audit log entries."""
    
    org_id: Optional[PyObjectId] = Field(None)
    project_id: Optional[PyObjectId] = Field(None)
    entity_type: str = Field(..., description="Type of entity being audited")
    entity_id: PyObjectId = Field(..., description="ID of the entity being audited")
    action: str = Field(..., description="Action performed on the entity")
    actor_id: Optional[PyObjectId] = Field(None)
    actor_role: Optional[str] = Field(None)
    ip_address: Optional[str] = Field(None)
    user_agent: Optional[str] = Field(None)
    before: Optional[Dict[str, Any]] = Field(None)
    after: Optional[Dict[str, Any]] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str
        }