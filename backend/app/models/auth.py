from typing import Optional, Any, Dict, List, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator, EmailStr
from .base import PyObjectId, BaseDBModel


class UserStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class OrgStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class OrgType(str, Enum):
    ORGANISATION = "organisation"
    DEPARTMENT = "department"
    TEAM = "team"
    UNIT = "unit"


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


class SystemRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    USER = "user"


class OrgRole(str, Enum):
    ORG_ADMIN = "org_admin"
    ORG_EDITOR = "org_editor"
    ORG_ANALYST = "org_analyst"
    ORG_VIEWER = "org_viewer"


class ProjectRole(str, Enum):
    PROJECT_OWNER = "project_owner"
    PROJECT_EDITOR = "project_editor"
    PROJECT_ANALYST = "project_analyst"
    PROJECT_VIEWER = "project_viewer"


class NotificationPreference(BaseModel):
    email: bool = True
    sms: bool = True
    push: bool = True
    in_app: bool = True


class DeviceToken(BaseModel):
    token: str
    platform: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserModel(BaseDBModel):
    """Model for users collection."""
    
    email: EmailStr
    password_hash: str
    full_name: str
    display_name: str
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    status: UserStatus = UserStatus.PENDING_APPROVAL
    email_verified: bool = False
    phone_verified: bool = False
    last_login_at: Optional[datetime] = None
    login_count: int = 0
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    two_factor_enabled: bool = False
    two_factor_secret: Optional[str] = None
    notification_preferences: NotificationPreference = Field(default_factory=NotificationPreference)
    device_tokens: List[DeviceToken] = Field(default_factory=list)
    approved_at: Optional[datetime] = None
    approved_by: Optional[PyObjectId] = None
    system_role: SystemRole = SystemRole.USER
    
    class Config:
        use_enum_values = True


class OrganisationModel(BaseDBModel):
    """Model for organisations collection."""
    
    org_id: Optional[PyObjectId] = Field(None, description="Orgs are top-level, so this is null")
    name: str
    slug: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    parent_org_id: Optional[PyObjectId] = None
    org_type: OrgType = OrgType.ORGANISATION
    status: OrgStatus = OrgStatus.PENDING_APPROVAL
    approved_at: Optional[datetime] = None
    approved_by: Optional[PyObjectId] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    compliance_ids: List[PyObjectId] = Field(default_factory=list)
    storage_quota_bytes: int = 0
    storage_used_bytes: int = 0
    
    @validator('slug')
    def validate_slug(cls, v):
        if not v or not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug must contain only alphanumeric characters, hyphens, and underscores')
        return v.lower()
    
    class Config:
        use_enum_values = True


class OrgMembershipModel(BaseDBModel):
    """Model for org_memberships collection."""
    
    user_id: PyObjectId
    org_id: PyObjectId
    role: OrgRole
    custom_permissions: List[str] = Field(default_factory=list)
    status: MembershipStatus = MembershipStatus.ACTIVE
    invited_by: Optional[PyObjectId] = None
    joined_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class GroupModel(BaseDBModel):
    """Model for groups collection."""
    
    org_id: PyObjectId
    name: str
    description: Optional[str] = None
    type: GroupType = GroupType.STATIC
    dynamic_rule: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class GroupMemberModel(BaseDBModel):
    """Model for group_members collection."""
    
    group_id: PyObjectId
    user_id: PyObjectId
    added_by: Optional[PyObjectId] = None


class InvitationModel(BaseDBModel):
    """Model for invitations collection."""
    
    token: str
    org_id: Optional[PyObjectId] = None
    project_id: Optional[PyObjectId] = None
    invited_by: Optional[PyObjectId] = None
    invited_email: EmailStr
    role: str
    status: InvitationStatus = InvitationStatus.PENDING
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class SessionModel(BaseDBModel):
    """Model for sessions collection."""
    
    user_id: PyObjectId
    refresh_token_hash: str
    device_info: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    expires_at: datetime
    
    class Config:
        use_enum_values = True


class ApiKeyModel(BaseDBModel):
    """Model for api_keys collection."""
    
    org_id: PyObjectId
    user_id: PyObjectId
    name: str
    key_hash: str
    key_prefix: str
    scopes: List[str]
    rate_limit_per_hour: int = 1000
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    expires_at: Optional[datetime] = None
    status: ApiKeyStatus = ApiKeyStatus.ACTIVE
    
    class Config:
        use_enum_values = True


class OAuthClientModel(BaseDBModel):
    """Model for oauth_clients collection."""
    
    org_id: PyObjectId
    client_id: str
    client_secret_hash: str
    name: str
    redirect_uris: List[str]
    scopes: List[str]
    grant_types: List[str]
    status: OAuthClientStatus = OAuthClientStatus.ACTIVE
    
    class Config:
        use_enum_values = True


class ProjectModel(BaseDBModel):
    """Model for projects collection."""
    
    name: str
    description: Optional[str] = None
    slug: str
    owner_org_id: PyObjectId
    shared_org_ids: List[PyObjectId] = Field(default_factory=list)
    status: str = "active"  # Can be "active" or "archived"
    settings: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('slug')
    def validate_slug(cls, v):
        if not v or not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Slug must contain only alphanumeric characters, hyphens, and underscores')
        return v.lower()


class ProjectMembershipModel(BaseDBModel):
    """Model for project_members collection."""
    
    project_id: PyObjectId
    user_id: PyObjectId
    org_id: PyObjectId
    role: ProjectRole
    invited_by: Optional[PyObjectId] = None
    joined_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class JWTClaims(BaseModel):
    """JWT claims structure."""
    
    sub: str  # user_id
    email: str
    system_role: SystemRole
    orgs: List[Dict[str, Any]] = Field(default_factory=list)  # List of org claims
    iat: int  # Issued at
    exp: int  # Expiration
    
    class Config:
        use_enum_values = True


class AuthResponse(BaseModel):
    """Standard authentication response."""
    
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900  # 15 minutes


class LoginRequest(BaseModel):
    """Login request model."""
    
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    """Registration request model."""
    
    email: EmailStr
    password: str
    full_name: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request model."""
    
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """Password reset confirmation request model."""
    
    token: str
    new_password: str


class InviteAcceptRequest(BaseModel):
    """Invite acceptance request model."""
    
    email: EmailStr
    full_name: str
    password: str


class PermissionCheckRequest(BaseModel):
    """Permission check request model."""
    
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class PermissionCheckResponse(BaseModel):
    """Permission check response model."""
    
    allowed: bool
    reason: Optional[str] = None
    effective_role: Optional[str] = None