from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
from bson import ObjectId
from .base import BaseDBModel, PyObjectId


class UserStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class OrgType(str, Enum):
    ORGANISATION = "organisation"
    DEPARTMENT = "department"
    TEAM = "team"
    UNIT = "unit"


class OrgStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class OrgMembershipRole(str, Enum):
    ORG_ADMIN = "org_admin"
    ORG_EDITOR = "org_editor"
    ORG_ANALYST = "org_analyst"
    ORG_VIEWER = "org_viewer"


class MembershipStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"


class GroupType(str, Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"


class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ApiKeyStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class OAuthClientStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class NotificationPreferences(BaseModel):
    email: bool = Field(default=True)
    sms: bool = Field(default=True)
    push: bool = Field(default=True)
    in_app: bool = Field(default=True)


class DeviceToken(BaseModel):
    token: str
    platform: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DynamicRule(BaseModel):
    field: str = Field(..., description="Field to evaluate, e.g., 'role'")
    operator: str = Field(..., description="Operator: equals, contains, in")
    value: Any = Field(..., description="Value to compare against")


class User(BaseDBModel):
    """Model for users collection."""
    
    email: EmailStr = Field(..., unique=True)
    password_hash: str = Field(...)
    full_name: str = Field(...)
    display_name: Optional[str] = Field(None)
    avatar_url: Optional[str] = Field(None)
    phone: Optional[str] = Field(None)
    status: UserStatus = Field(default=UserStatus.PENDING_APPROVAL)
    email_verified: bool = Field(default=False)
    phone_verified: bool = Field(default=False)
    last_login_at: Optional[datetime] = Field(None)
    login_count: int = Field(default=0)
    failed_login_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(None)
    two_factor_enabled: bool = Field(default=False)
    two_factor_secret: Optional[str] = Field(None)
    notification_preferences: NotificationPreferences = Field(default_factory=NotificationPreferences)
    device_tokens: List[DeviceToken] = Field(default_factory=list)
    approved_at: Optional[datetime] = Field(None)
    approved_by: Optional[PyObjectId] = Field(None)


class Organisation(BaseDBModel):
    """Model for organisations collection."""
    
    org_id: Optional[PyObjectId] = Field(None, description="Null for top-level orgs")
    name: str = Field(...)
    slug: str = Field(..., unique=True)
    description: Optional[str] = Field(None)
    logo_url: Optional[str] = Field(None)
    parent_org_id: Optional[PyObjectId] = Field(None, description="Null for root orgs")
    org_type: OrgType = Field(default=OrgType.ORGANISATION)
    status: OrgStatus = Field(default=OrgStatus.PENDING_APPROVAL)
    approved_at: Optional[datetime] = Field(None)
    approved_by: Optional[PyObjectId] = Field(None)
    settings: Dict[str, Any] = Field(default_factory=dict)
    compliance_ids: List[PyObjectId] = Field(default_factory=list)
    storage_quota_bytes: int = Field(default=0)
    storage_used_bytes: int = Field(default=0)


class OrgMembership(BaseDBModel):
    """Model for org_memberships collection."""
    
    user_id: PyObjectId = Field(...)
    org_id: PyObjectId = Field(...)
    role: OrgMembershipRole = Field(...)
    custom_permissions: List[str] = Field(default_factory=list)
    status: MembershipStatus = Field(default=MembershipStatus.PENDING)
    invited_by: Optional[PyObjectId] = Field(None)
    joined_at: Optional[datetime] = Field(None)


class Group(BaseDBModel):
    """Model for groups collection."""
    
    name: str = Field(...)
    description: Optional[str] = Field(None)
    type: GroupType = Field(default=GroupType.STATIC)
    dynamic_rule: Optional[DynamicRule] = Field(None)


class GroupMember(BaseModel):
    """Model for group_members collection (no soft delete)."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    group_id: PyObjectId = Field(...)
    user_id: PyObjectId = Field(...)
    added_by: PyObjectId = Field(...)
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


class Invitation(BaseDBModel):
    """Model for invitations collection."""
    
    token: str = Field(..., unique=True)
    org_id: PyObjectId = Field(...)
    project_id: Optional[PyObjectId] = Field(None)
    invited_by: PyObjectId = Field(...)
    invited_email: EmailStr = Field(...)
    role: str = Field(...)
    status: InvitationStatus = Field(default=InvitationStatus.PENDING)
    expires_at: datetime = Field(...)
    accepted_at: Optional[datetime] = Field(None)


class Session(BaseModel):
    """Model for sessions collection (refresh token registry)."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    user_id: PyObjectId = Field(...)
    refresh_token_hash: str = Field(...)
    device_info: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = Field(None)
    expires_at: datetime = Field(...)

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


class ApiKey(BaseDBModel):
    """Model for api_keys collection."""
    
    user_id: PyObjectId = Field(..., description="Owner of the API key")
    name: str = Field(...)
    key_hash: str = Field(...)
    key_prefix: str = Field(..., description="First 8 chars for display")
    scopes: List[str] = Field(default_factory=list)
    rate_limit_per_hour: int = Field(default=1000)
    last_used_at: Optional[datetime] = Field(None)
    usage_count: int = Field(default=0)
    expires_at: Optional[datetime] = Field(None)
    status: ApiKeyStatus = Field(default=ApiKeyStatus.ACTIVE)


class OAuthClient(BaseDBModel):
    """Model for oauth_clients collection."""
    
    client_id: str = Field(..., unique=True)
    client_secret_hash: str = Field(...)
    name: str = Field(...)
    redirect_uris: List[str] = Field(default_factory=list)
    scopes: List[str] = Field(default_factory=list)
    grant_types: List[str] = Field(default_factory=list)
    status: OAuthClientStatus = Field(default=OAuthClientStatus.ACTIVE)