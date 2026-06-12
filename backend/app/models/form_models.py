from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from bson import ObjectId
from datetime import datetime
from enum import Enum


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


class FormLayout(str, Enum):
    SINGLE_PAGE = "single_page"
    MULTI_PAGE = "multi_page"
    WIZARD = "wizard"


class FormAccessType(str, Enum):
    PUBLIC = "public"
    ORG = "org"
    GROUPS = "groups"
    USERS = "users"


class ResponseEditPolicy(str, Enum):
    NO_EDIT = "no_edit"
    ROLE_EDIT = "role_edit"
    TIME_WINDOW_EDIT = "time_window_edit"
    ALWAYS_EDIT = "always_edit"


class FetchActionSource(str, Enum):
    OWN_PREVIOUS_RESPONSE = "own_previous_response"
    OTHER_FORM_LAST_RESPONSE = "other_form_last_response"
    EXTERNAL_URL = "external_url"


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"


class OfflineBehavior(str, Enum):
    LEAVE_BLANK = "leave_blank"
    BLOCK_SUBMISSION = "block_submission"
    USE_CACHE = "use_cache"


class CalculationTrigger(str, Enum):
    ON_CHANGE = "on_change"
    ON_LOAD = "on_load"


class SkipLogicJumpTarget(str, Enum):
    SECTION = "section"
    SUB_SECTION = "sub_section"
    QUESTION = "question"
    END = "end"


class ValidationRuleType(str, Enum):
    MIN = "min"
    MAX = "max"
    MIN_LENGTH = "min_length"
    MAX_LENGTH = "max_length"
    PATTERN = "pattern"
    CUSTOM = "custom"


class ConditionType(str, Enum):
    ROLE = "role"
    GROUP = "group"
    ANSWER = "answer"
    ALWAYS_VISIBLE = "always_visible"
    ALWAYS_HIDDEN = "always_hidden"


class ComparisonOperator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IN = "in"
    NOT_IN = "not_in"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


class LogicalOperator(str, Enum):
    AND = "AND"
    OR = "OR"


class Condition(BaseModel):
    type: ConditionType
    roles: Optional[List[str]] = None
    group_ids: Optional[List[PyObjectId]] = None
    field_id: Optional[str] = None
    operator: Optional[ComparisonOperator] = None
    value: Optional[Any] = None

    @validator('roles')
    def validate_roles(cls, v, values):
        if values.get('type') == ConditionType.ROLE and not v:
            raise ValueError("roles are required for role condition")
        return v

    @validator('group_ids')
    def validate_group_ids(cls, v, values):
        if values.get('type') == ConditionType.GROUP and not v:
            raise ValueError("group_ids are required for group condition")
        return v

    @validator('field_id')
    def validate_field_id(cls, v, values):
        if values.get('type') == ConditionType.ANSWER and not v:
            raise ValueError("field_id is required for answer condition")
        return v

    @validator('operator')
    def validate_operator(cls, v, values):
        if values.get('type') == ConditionType.ANSWER and not v:
            raise ValueError("operator is required for answer condition")
        return v


class VisibilityRules(BaseModel):
    operator: LogicalOperator = LogicalOperator.AND
    conditions: List[Condition] = []


class ValidationRule(BaseModel):
    type: ValidationRuleType
    value: Any
    message: str


class CalculationDef(BaseModel):
    trigger: CalculationTrigger
    formula_ast: Dict[str, Any]
    target_question_id: str


class FetchActionDef(BaseModel):
    source: FetchActionSource
    form_id: Optional[PyObjectId] = None
    url: Optional[str] = None
    method: HttpMethod = HttpMethod.GET
    headers: Optional[Dict[str, str]] = {}
    body_template: Optional[str] = None
    field_mapping: List[Dict[str, str]] = []
    offline_behavior: OfflineBehavior = OfflineBehavior.LEAVE_BLANK

    @validator('form_id')
    def validate_form_id(cls, v, values):
        if values.get('source') == FetchActionSource.OTHER_FORM_LAST_RESPONSE and not v:
            raise ValueError("form_id is required for other_form_last_response source")
        return v

    @validator('url')
    def validate_url(cls, v, values):
        if values.get('source') == FetchActionSource.EXTERNAL_URL and not v:
            raise ValueError("url is required for external_url source")
        return v


class SkipLogicDef(BaseModel):
    conditions: VisibilityRules
    jump_to: SkipLogicJumpTarget
    target_id: str


class Question(BaseModel):
    id: str
    type: str
    label: str
    description: Optional[str] = ""
    required: bool = False
    properties: Dict[str, Any] = {}
    visibility_rules: Optional[VisibilityRules] = VisibilityRules()
    validation_rules: List[ValidationRule] = []
    calculations: List[CalculationDef] = []
    fetch_action: Optional[FetchActionDef] = None
    skip_logic: Optional[SkipLogicDef] = None
    ui: Optional[Dict[str, Any]] = {}


class SubSection(BaseModel):
    id: str
    title: str
    repeatable: bool = False
    max_repeats: int = 1
    visibility_rules: Optional[VisibilityRules] = VisibilityRules()
    questions: List[Question] = []


class Section(BaseModel):
    id: str
    title: str
    description: Optional[str] = ""
    repeatable: bool = False
    max_repeats: int = 1
    min_repeats: int = 1
    visibility_rules: Optional[VisibilityRules] = VisibilityRules()
    sub_sections: List[SubSection] = []


class FormUI(BaseModel):
    theme: Dict[str, Any] = {}
    layout: FormLayout = FormLayout.SINGLE_PAGE
    primary_color: Optional[str] = "#3B82F6"
    font: Optional[str] = "Inter"
    logo_url: Optional[str] = None
    cover_page: Optional[Dict[str, Any]] = {}
    thank_you_page: Optional[Dict[str, Any]] = {}


class FormAccess(BaseModel):
    type: FormAccessType = FormAccessType.ORG
    allowed_org_ids: List[PyObjectId] = []
    allowed_group_ids: List[PyObjectId] = []
    allowed_user_ids: List[PyObjectId] = []
    allow_anonymous: bool = False


class FormSettings(BaseModel):
    expires_at: Optional[datetime] = None
    max_responses: Optional[int] = None
    allow_multiple_submissions: bool = False
    allow_draft_save: bool = True
    response_edit_policy: ResponseEditPolicy = ResponseEditPolicy.NO_EDIT
    edit_time_window_hours: Optional[int] = None
    edit_allowed_roles: List[str] = []
    require_login: bool = False


class WebhookConfig(BaseModel):
    url: str
    events: List[str]
    secret: Optional[str] = None


class FormSchema(BaseModel):
    ui: FormUI = FormUI()
    access: FormAccess = FormAccess()
    settings: FormSettings = FormSettings()
    webhook_configs: List[WebhookConfig] = []
    sections: List[Section] = []


class FormCommit(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    form_id: PyObjectId
    commit_id: str
    parent_ids: List[str] = []
    author_id: PyObjectId
    message: str
    branch: str
    tag: Optional[str] = None
    timestamp: datetime
    schema: FormSchema

    class Config:
        allow_population_by_field_name = True


class Form(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    org_id: PyObjectId
    project_id: PyObjectId
    name: str
    description: Optional[str] = ""
    branches: Dict[str, str] = {"main": ""}
    production_branch: str = "main"
    tags: Dict[str, str] = {}
    template_id: Optional[PyObjectId] = None
    created_at: datetime
    updated_at: datetime
    created_by: PyObjectId
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True


class FormTemplate(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    org_id: Optional[PyObjectId] = None
    project_id: Optional[PyObjectId] = None
    name: str
    description: Optional[str] = ""
    category: Optional[str] = ""
    tags: List[str] = []
    is_system: bool = False
    is_public: bool = False
    schema: FormSchema
    usage_count: int = 0
    created_at: datetime
    updated_at: datetime
    created_by: PyObjectId
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True


class FormResponse(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    form_id: PyObjectId
    commit_id: str
    org_id: PyObjectId
    project_id: PyObjectId
    respondent_id: Optional[PyObjectId] = None
    respondent_email: Optional[str] = None
    session_id: str
    status: str = "submitted"
    is_anonymous: bool = False
    is_legacy: bool = False
    submission_number: int = 1
    answers: Dict[str, Any] = {}
    repeat_groups: Dict[str, List[Dict[str, Any]]] = {}
    metadata: Dict[str, Any] = {}
    edit_history: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime
    submitted_at: Optional[datetime] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None

    class Config:
        allow_population_by_field_name = True


class ResponseDraft(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    form_id: PyObjectId
    commit_id: str
    respondent_id: PyObjectId
    org_id: PyObjectId
    partial_answers: Dict[str, Any] = {}
    last_saved_at: datetime
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        allow_population_by_field_name = True


class PendingMerge(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    form_id: PyObjectId
    branch_name: str
    base_commit_id: str
    their_commit_id: str
    our_changes: Dict[str, Any] = {}
    conflict_fields: List[str] = []
    status: str = "pending"
    resolver_id: Optional[PyObjectId] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    created_by: PyObjectId

    class Config:
        allow_population_by_field_name = True


class EditSession(BaseModel):
    id: Optional[PyObjectId] = Field(None, alias="_id")
    entity_type: str
    entity_id: PyObjectId
    user_id: PyObjectId
    org_id: PyObjectId
    started_at: datetime
    last_ping_at: datetime

    class Config:
        allow_population_by_field_name = True


class BranchCreateRequest(BaseModel):
    name: str
    from_commit_id: str


class BranchDeleteRequest(BaseModel):
    branch_name: str


class MergeRequest(BaseModel):
    source_branch: str
    target_branch: str
    message: Optional[str] = None


class TagCreateRequest(BaseModel):
    tag_name: str
    commit_id: str
    message: Optional[str] = None


class PublishRequest(BaseModel):
    branch_name: str
    message: Optional[str] = None


class MergeConflictResolution(BaseModel):
    pending_merge_id: PyObjectId
    resolved_fields: Dict[str, Any] = {}
    resolution_strategy: str = "manual"


class FormCommitResponse(BaseModel):
    commit_id: str
    message: str
    author_id: str
    branch: str
    tag: Optional[str] = None
    timestamp: datetime
    parent_ids: List[str] = []


class FormBranchResponse(BaseModel):
    name: str
    commit_id: str
    is_production: bool = False


class FormDiffResponse(BaseModel):
    additions: Dict[str, Any] = {}
    deletions: Dict[str, Any] = {}
    modifications: Dict[str, Any] = {}
    conflicts: List[str] = []


class MergeResponse(BaseModel):
    status: str
    commit_id: Optional[str] = None
    conflict_fields: List[str] = []
    pending_merge_id: Optional[str] = None