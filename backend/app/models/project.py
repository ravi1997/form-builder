from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
from bson import ObjectId
from .base import BaseDBModel, PyObjectId


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectMembershipRole(str, Enum):
    PROJECT_OWNER = "project_owner"
    PROJECT_EDITOR = "project_editor"
    PROJECT_ANALYST = "project_analyst"
    PROJECT_VIEWER = "project_viewer"


class NotificationRule(BaseModel):
    """Notification rule structure for project settings."""
    
    event_type: str = Field(...)
    channels: List[str] = Field(default_factory=list)
    recipient_type: str = Field(...)
    recipient_ids: List[PyObjectId] = Field(default_factory=list)
    template_id: Optional[PyObjectId] = Field(None)
    is_active: bool = Field(default=True)


class ProjectSettings(BaseModel):
    """Project settings configuration."""
    
    default_form_theme: Dict[str, Any] = Field(default_factory=dict)
    default_compliance_ids: List[PyObjectId] = Field(default_factory=list)
    notification_rules: List[NotificationRule] = Field(default_factory=list)
    default_language: str = Field(default="en")


class Project(BaseDBModel):
    """Model for projects collection."""
    
    name: str = Field(...)
    description: Optional[str] = Field(None)
    slug: str = Field(...)
    owner_org_id: PyObjectId = Field(...)
    shared_org_ids: List[PyObjectId] = Field(default_factory=list)
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE)
    settings: ProjectSettings = Field(default_factory=ProjectSettings)


class ProjectMembership(BaseDBModel):
    """Model for project_members collection."""
    
    project_id: PyObjectId = Field(...)
    user_id: PyObjectId = Field(...)
    org_id: PyObjectId = Field(...)
    role: ProjectMembershipRole = Field(...)
    invited_by: Optional[PyObjectId] = Field(None)
    joined_at: Optional[datetime] = Field(None)