from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from .base import BaseDBModel, PyObjectId


class StorageUsage(BaseModel):
    """Storage usage breakdown."""
    
    files: int = Field(default=0)
    database: int = Field(default=0)
    audit_logs: int = Field(default=0)
    total: int = Field(default=0)


class StorageQuota(BaseModel):
    """Model for storage_quotas collection."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    org_id: PyObjectId = Field(..., unique=True)
    quota_bytes: int = Field(...)
    used_bytes: StorageUsage = Field(default_factory=StorageUsage)
    warning_threshold: float = Field(default=0.8)
    last_calculated_at: datetime = Field(default_factory=datetime.utcnow)
    set_by: PyObjectId = Field(...)
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