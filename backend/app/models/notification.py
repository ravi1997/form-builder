from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
from bson import ObjectId
from .base import BaseDBModel, PyObjectId


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    PUSH = "push"
    WEBHOOK = "webhook"


class DeliveryStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


class RecipientType(str, Enum):
    FORM_OWNER = "form_owner"
    SPECIFIC_USERS = "specific_users"
    ROLE = "role"
    GROUP = "group"
    RESPONDENT = "respondent"


class EmailChannel(BaseModel):
    """Email channel configuration."""
    
    subject: str = Field(...)
    body_html: str = Field(...)
    body_text: str = Field(...)


class SMSChannel(BaseModel):
    """SMS channel configuration."""
    
    message: str = Field(...)


class InAppChannel(BaseModel):
    """In-app channel configuration."""
    
    title: str = Field(...)
    body: str = Field(...)


class NotificationChannels(BaseModel):
    """Notification channel configurations."""
    
    email: Optional[EmailChannel] = Field(None)
    sms: Optional[SMSChannel] = Field(None)
    in_app: Optional[InAppChannel] = Field(None)


class TemplateVariable(BaseModel):
    """Template variable definition."""
    
    key: str = Field(...)
    description: str = Field(...)
    example: str = Field(...)


class NotificationTemplate(BaseDBModel):
    """Model for notification_templates collection."""
    
    org_id: Optional[PyObjectId] = Field(None, description="Null for system templates")
    name: str = Field(...)
    event_type: str = Field(...)
    channels: NotificationChannels = Field(...)
    variables: List[TemplateVariable] = Field(default_factory=list)
    is_system: bool = Field(default=False)
    is_active: bool = Field(default=True)


class NotificationRuleCondition(BaseModel):
    """Condition for notification rules (same as form visibility conditions)."""
    
    type: str = Field(..., description="role, group, answer, always_visible, always_hidden")
    roles: Optional[List[str]] = Field(None)
    group_ids: Optional[List[PyObjectId]] = Field(None)
    field_id: Optional[str] = Field(None)
    operator: Optional[str] = Field(None)
    value: Optional[Any] = Field(None)


class NotificationRule(BaseDBModel):
    """Model for notification_rules collection."""
    
    project_id: Optional[PyObjectId] = Field(None)
    form_id: Optional[PyObjectId] = Field(None)
    name: str = Field(...)
    event_type: str = Field(...)
    trigger_conditions: List[NotificationRuleCondition] = Field(default_factory=list)
    channels: List[NotificationChannel] = Field(default_factory=list)
    recipient_type: RecipientType = Field(...)
    recipient_ids: List[PyObjectId] = Field(default_factory=list)
    template_id: PyObjectId = Field(...)
    is_active: bool = Field(default=True)


class NotificationLog(BaseModel):
    """Model for notification_log collection."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    rule_id: PyObjectId = Field(...)
    org_id: PyObjectId = Field(...)
    event_type: str = Field(...)
    recipient_id: PyObjectId = Field(...)
    channel: NotificationChannel = Field(...)
    status: DeliveryStatus = Field(default=DeliveryStatus.QUEUED)
    attempt_count: int = Field(default=0)
    max_attempts: int = Field(default=3)
    next_retry_at: Optional[datetime] = Field(None)
    provider_response: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_attempt_at: Optional[datetime] = Field(None)

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


class WebhookConfig(BaseDBModel):
    """Model for webhook_configs collection."""
    
    form_id: Optional[PyObjectId] = Field(None)
    project_id: Optional[PyObjectId] = Field(None)
    name: str = Field(...)
    url: str = Field(...)
    secret: str = Field(..., description="HMAC signing key")
    events: List[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)


class WebhookDeliveryLog(BaseModel):
    """Model for webhook_delivery_log collection."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    webhook_config_id: PyObjectId = Field(...)
    org_id: PyObjectId = Field(...)
    event_type: str = Field(...)
    payload: Dict[str, Any] = Field(...)
    status: DeliveryStatus = Field(default=DeliveryStatus.QUEUED)
    http_status_code: Optional[int] = Field(None)
    response_body: Optional[str] = Field(None)
    attempt_count: int = Field(default=0)
    next_retry_at: Optional[datetime] = Field(None)
    delivered_at: Optional[datetime] = Field(None)
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