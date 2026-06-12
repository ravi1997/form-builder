from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
from bson import ObjectId
from uuid import uuid4
from .base import BaseDBModel, PyObjectId


class FormLayout(str, Enum):
    SINGLE_PAGE = "single_page"
    MULTI_PAGE = "multi_page"
    WIZARD = "wizard"


class AccessType(str, Enum):
    PUBLIC = "public"
    ORG = "org"
    GROUPS = "groups"
    USERS = "users"


class ResponseEditPolicy(str, Enum):
    NO_EDIT = "no_edit"
    ROLE_EDIT = "role_edit"
    TIME_WINDOW_EDIT = "time_window_edit"
    ALWAYS_EDIT = "always_edit"


class ResponseStatus(str, Enum):
    SUBMITTED = "submitted"
    DRAFT = "draft"


class FileUploadStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETE = "complete"
    FAILED = "failed"


class VirusScanStatus(str, Enum):
    PENDING = "pending"
    CLEAN = "clean"
    INFECTED = "infected"


class FileType(str, Enum):
    PDF = "pdf"
    VIDEO = "video"
    IMAGE = "image"
    OTHER = "other"


class MergeStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    ABANDONED = "abandoned"


# Complex nested structures for forms
class VisibilityCondition(BaseModel):
    """Condition for visibility rules."""
    
    type: str = Field(..., description="role, group, answer, always_visible, always_hidden")
    roles: Optional[List[str]] = Field(None)
    group_ids: Optional[List[PyObjectId]] = Field(None)
    field_id: Optional[str] = Field(None)
    operator: Optional[str] = Field(None)
    value: Optional[Any] = Field(None)


class VisibilityRules(BaseModel):
    """Visibility rules for form elements."""
    
    operator: str = Field(default="AND", description="AND or OR")
    conditions: List[VisibilityCondition] = Field(default_factory=list)


class ValidationRule(BaseModel):
    """Validation rule for form questions."""
    
    type: str = Field(..., description="min, max, min_length, max_length, pattern, custom")
    value: Any = Field(...)
    message: str = Field(...)


class CalculationDef(BaseModel):
    """Calculation definition for form questions."""
    
    trigger: str = Field(..., description="on_change, on_load")
    formula_ast: Dict[str, Any] = Field(...)
    target_question_id: str = Field(...)


class FetchActionDef(BaseModel):
    """Fetch action definition for form questions."""
    
    source: str = Field(..., description="own_previous_response, other_form_last_response, external_url")
    form_id: Optional[PyObjectId] = Field(None)
    url: Optional[str] = Field(None)
    method: str = Field(default="GET", description="GET or POST")
    headers: Dict[str, Any] = Field(default_factory=dict)
    body_template: Optional[str] = Field(None)
    field_mapping: List[Dict[str, str]] = Field(default_factory=list)
    offline_behavior: str = Field(default="leave_blank", description="leave_blank, block_submission, use_cache")


class SkipLogicDef(BaseModel):
    """Skip logic definition for form questions."""
    
    conditions: VisibilityRules
    jump_to: str = Field(..., description="section, sub_section, question, end")
    target_id: str = Field(...)


class WebhookConfig(BaseModel):
    """Webhook configuration for forms."""
    
    url: str = Field(...)
    events: List[str] = Field(default_factory=list)
    secret: Optional[str] = Field(None)


class FormUISettings(BaseModel):
    """UI settings for forms."""
    
    theme: Dict[str, Any] = Field(default_factory=dict)
    layout: FormLayout = Field(default=FormLayout.SINGLE_PAGE)
    primary_color: Optional[str] = Field(None)
    font: Optional[str] = Field(None)
    logo_url: Optional[str] = Field(None)
    cover_page: Dict[str, Any] = Field(default_factory=dict)
    thank_you_page: Dict[str, Any] = Field(default_factory=dict)


class FormAccessSettings(BaseModel):
    """Access settings for forms."""
    
    type: AccessType = Field(default=AccessType.PUBLIC)
    allowed_org_ids: List[PyObjectId] = Field(default_factory=list)
    allowed_group_ids: List[PyObjectId] = Field(default_factory=list)
    allowed_user_ids: List[PyObjectId] = Field(default_factory=list)
    allow_anonymous: bool = Field(default=True)


class FormSettings(BaseModel):
    """Settings for forms."""
    
    expires_at: Optional[datetime] = Field(None)
    max_responses: Optional[int] = Field(None)
    allow_multiple_submissions: bool = Field(default=False)
    allow_draft_save: bool = Field(default=True)
    response_edit_policy: ResponseEditPolicy = Field(default=ResponseEditPolicy.NO_EDIT)
    edit_time_window_hours: Optional[int] = Field(None)
    edit_allowed_roles: List[str] = Field(default_factory=list)
    require_login: bool = Field(default=False)
    webhook_configs: List[WebhookConfig] = Field(default_factory=list)


class Question(BaseModel):
    """Question model for forms."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str = Field(..., description="Component type")
    label: str = Field(...)
    description: Optional[str] = Field(None)
    required: bool = Field(default=False)
    properties: Dict[str, Any] = Field(default_factory=dict)
    visibility_rules: VisibilityRules = Field(default_factory=VisibilityRules)
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    calculations: List[CalculationDef] = Field(default_factory=list)
    fetch_action: Optional[FetchActionDef] = Field(None)
    skip_logic: Optional[SkipLogicDef] = Field(None)
    ui: Dict[str, Any] = Field(default_factory=dict)


class SubSection(BaseModel):
    """Sub-section model for forms."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(...)
    repeatable: bool = Field(default=False)
    max_repeats: int = Field(default=1)
    visibility_rules: VisibilityRules = Field(default_factory=VisibilityRules)
    questions: List[Question] = Field(default_factory=list)


class Section(BaseModel):
    """Section model for forms."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(...)
    description: Optional[str] = Field(None)
    repeatable: bool = Field(default=False)
    max_repeats: int = Field(default=1)
    min_repeats: int = Field(default=1)
    visibility_rules: VisibilityRules = Field(default_factory=VisibilityRules)
    sub_sections: List[SubSection] = Field(default_factory=list)


class FormSchema(BaseModel):
    """Complete form schema."""
    
    ui: FormUISettings = Field(default_factory=FormUISettings)
    access: FormAccessSettings = Field(default_factory=FormAccessSettings)
    settings: FormSettings = Field(default_factory=FormSettings)
    sections: List[Section] = Field(default_factory=list)


# Main form models
class Form(BaseDBModel):
    """Model for forms collection with proper branches structure."""
    
    project_id: PyObjectId = Field(...)
    name: str = Field(...)
    description: Optional[str] = Field(None)
    branches: Dict[str, str] = Field(default_factory=dict)
    production_branch: str = Field(default="main")
    tags: Dict[str, str] = Field(default_factory=dict)
    template_id: Optional[PyObjectId] = Field(None)


class FormCommit(BaseModel):
    """Model for form_commits collection."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    form_id: PyObjectId = Field(...)
    commit_id: str = Field(..., description="SHA-like, unique per form")
    parent_ids: List[str] = Field(default_factory=list)
    author_id: PyObjectId = Field(...)
    message: str = Field(...)
    branch: str = Field(...)
    tag: Optional[str] = Field(None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    schema: FormSchema = Field(...)

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


class FormTemplate(BaseDBModel):
    """Model for form_templates collection."""
    
    org_id: Optional[PyObjectId] = Field(None, description="Null for system templates")
    project_id: Optional[PyObjectId] = Field(None)
    name: str = Field(...)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None)
    tags: List[str] = Field(default_factory=list)
    is_system: bool = Field(default=False)
    is_public: bool = Field(default=False)
    schema: FormSchema = Field(...)
    usage_count: int = Field(default=0)


class AnswerObject(BaseModel):
    """Answer object for form responses."""
    
    value: Any = Field(...)
    display_value: str = Field(...)
    file_ids: List[PyObjectId] = Field(default_factory=list)
    answered_at: datetime = Field(default_factory=datetime.utcnow)
    iteration_index: int = Field(default=0)


class RepeatGroup(BaseModel):
    """Repeat group for form responses."""
    
    iteration: int = Field(...)
    answers: Dict[str, AnswerObject] = Field(default_factory=dict)


class ResponseMetadata(BaseModel):
    """Metadata for form responses."""
    
    ip_address: Optional[str] = Field(None)
    user_agent: Optional[str] = Field(None)
    device_type: Optional[str] = Field(None)
    platform: Optional[str] = Field(None)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    time_taken_seconds: Optional[float] = Field(None)
    offline_submitted: bool = Field(default=False)


class EditHistoryEntry(BaseModel):
    """Edit history entry for form responses."""
    
    edited_at: datetime = Field(default_factory=datetime.utcnow)
    edited_by: Optional[PyObjectId] = Field(None)
    before: Dict[str, Any] = Field(default_factory=dict)
    after: Dict[str, Any] = Field(default_factory=dict)


class FormResponse(BaseDBModel):
    """Model for form_responses collection with complex answers structure."""
    
    form_id: PyObjectId = Field(...)
    commit_id: str = Field(..., description="Version pinned to")
    project_id: PyObjectId = Field(...)
    respondent_id: Optional[PyObjectId] = Field(None, description="Null for anonymous")
    respondent_email: Optional[str] = Field(None, description="For anonymous tracking")
    session_id: str = Field(...)
    status: ResponseStatus = Field(default=ResponseStatus.DRAFT)
    is_anonymous: bool = Field(default=False)
    is_legacy: bool = Field(default=False, description="True if commit_id != production_branch HEAD")
    submission_number: int = Field(default=0, description="Sequential per form")
    answers: Dict[str, AnswerObject] = Field(default_factory=dict)
    repeat_groups: Dict[str, List[RepeatGroup]] = Field(default_factory=dict)
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata)
    edit_history: List[EditHistoryEntry] = Field(default_factory=list)
    submitted_at: Optional[datetime] = Field(None)


class ResponseDraft(BaseModel):
    """Model for response_drafts collection."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    form_id: PyObjectId = Field(...)
    commit_id: str = Field(...)
    respondent_id: PyObjectId = Field(...)
    org_id: PyObjectId = Field(...)
    partial_answers: Dict[str, Any] = Field(default_factory=dict)
    last_saved_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(...)
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


class FileUpload(BaseDBModel):
    """Model for file_uploads collection."""
    
    form_id: Optional[PyObjectId] = Field(None)
    response_id: Optional[PyObjectId] = Field(None)
    question_id: Optional[str] = Field(None)
    original_filename: str = Field(...)
    stored_filename: str = Field(...)
    file_path: str = Field(..., description="Relative to uploads root")
    mime_type: str = Field(...)
    file_size_bytes: int = Field(...)
    file_type: FileType = Field(...)
    upload_status: FileUploadStatus = Field(default=FileUploadStatus.PENDING)
    upload_offset: int = Field(default=0, description="For resumable uploads")
    checksum_sha256: Optional[str] = Field(None)
    virus_scan_status: VirusScanStatus = Field(default=VirusScanStatus.PENDING)
    uploaded_by: Optional[PyObjectId] = Field(None)


class EditSession(BaseModel):
    """Model for edit_sessions collection (ephemeral - presence awareness)."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    entity_type: str = Field(...)
    entity_id: PyObjectId = Field(...)
    user_id: PyObjectId = Field(...)
    org_id: PyObjectId = Field(...)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_ping_at: datetime = Field(default_factory=datetime.utcnow)

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


class PendingMerge(BaseDBModel):
    """Model for pending_merges collection (conflict states)."""
    
    form_id: PyObjectId = Field(...)
    branch_name: str = Field(...)
    base_commit_id: str = Field(...)
    their_commit_id: str = Field(...)
    our_changes: Dict[str, Any] = Field(default_factory=dict)
    conflict_fields: List[str] = Field(default_factory=list)
    status: MergeStatus = Field(default=MergeStatus.PENDING)
    resolver_id: Optional[PyObjectId] = Field(None)
    resolved_at: Optional[datetime] = Field(None)