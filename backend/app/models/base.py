from typing import Optional, Any, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class BaseDBModel(BaseModel):
    """Base model for all database collections with common fields."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    org_id: Optional[PyObjectId] = Field(None, description="Organization ID, null for system-level docs")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[PyObjectId] = Field(None, description="User ID who created the record")
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = Field(None)

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

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.utcnow()

    def mark_deleted(self):
        """Mark the record as deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.update_timestamp()


class SystemConfigModel(BaseModel):
    """Model for system_config collection (single document per key)."""
    
    key: str = Field(..., description="Unique configuration key")
    value: Any = Field(..., description="Configuration value")
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[PyObjectId] = Field(None)

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary for MongoDB operations."""
        data = self.dict(by_alias=True)
        return data