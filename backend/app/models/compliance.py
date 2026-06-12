from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from .base import BaseDBModel, PyObjectId


class BehavioralConstraint(BaseModel):
    """Behavioral constraint for compliance standards."""
    
    type: str = Field(...)
    config: Dict[str, Any] = Field(...)


class ComplianceStandard(BaseDBModel):
    """Model for compliance_standards collection."""
    
    code: str = Field(..., description="e.g., 'GDPR', 'HIPAA'")
    name: str = Field(...)
    description: str = Field(...)
    region: str = Field(...)
    behavioral_constraints: List[BehavioralConstraint] = Field(default_factory=list)
    is_system: bool = Field(default=True)
    created_by: Optional[PyObjectId] = Field(None, description="Always null for super_admin")


class OrgCompliance(BaseModel):
    """Model for org_compliance collection."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    org_id: PyObjectId = Field(...)
    compliance_id: PyObjectId = Field(...)
    adopted_at: datetime = Field(default_factory=datetime.utcnow)
    adopted_by: PyObjectId = Field(...)
    effective_from: datetime = Field(...)
    notes: Optional[str] = Field(None)

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