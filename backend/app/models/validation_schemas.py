from pydantic import BaseModel, Field, validator, constr
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import re


# --- Common Models ---

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")


class ErrorResponse(BaseModel):
    status: str = Field("error", description="Response status")
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")


class SuccessResponse(BaseModel):
    status: str = Field("success", description="Response status")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")


# --- Authentication Models ---

class LoginRequest(BaseModel):
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$', description="User email")
    password: str = Field(..., min_length=8, description="User password")


class RegisterRequest(BaseModel):
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$', description="User email")
    password: str = Field(..., min_length=8, description="User password")
    full_name: str = Field(..., min_length=2, max_length=100, description="User full name")
    display_name: Optional[str] = Field(None, max_length=50, description="User display name")


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, description="Refresh token")


# --- Organization Models ---

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Organization name")
    description: Optional[str] = Field(None, max_length=500, description="Organization description")
    parent_org_id: Optional[str] = Field(None, description="Parent organization ID")
    org_type: str = Field("organisation", regex=r'^(organisation|department|team|unit)$', description="Organization type")


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Organization name")
    description: Optional[str] = Field(None, max_length=500, description="Organization description")
    settings: Optional[Dict[str, Any]] = Field(None, description="Organization settings")


# --- Project Models ---

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Project name")
    description: Optional[str] = Field(None, max_length=500, description="Project description")
    owner_org_id: str = Field(..., description="Owner organization ID")
    shared_org_ids: Optional[List[str]] = Field([], description="Shared organization IDs")
    settings: Optional[Dict[str, Any]] = Field(None, description="Project settings")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Project name")
    description: Optional[str] = Field(None, max_length=500, description="Project description")
    shared_org_ids: Optional[List[str]] = Field(None, description="Shared organization IDs")
    settings: Optional[Dict[str, Any]] = Field(None, description="Project settings")


# --- Form Models ---

class FormAccessConfig(BaseModel):
    type: str = Field(..., regex=r'^(public|org|groups|users)$', description="Access type")
    allowed_org_ids: Optional[List[str]] = Field([], description="Allowed organization IDs")
    allowed_group_ids: Optional[List[str]] = Field([], description="Allowed group IDs")
    allowed_user_ids: Optional[List[str]] = Field([], description="Allowed user IDs")
    allow_anonymous: bool = Field(False, description="Allow anonymous access")


class FormSettings(BaseModel):
    expires_at: Optional[datetime] = Field(None, description="Form expiration date")
    max_responses: Optional[int] = Field(None, ge=1, description="Maximum number of responses")
    allow_multiple_submissions: bool = Field(False, description="Allow multiple submissions")
    allow_draft_save: bool = Field(True, description="Allow draft saving")
    response_edit_policy: str = Field("no_edit", regex=r'^(no_edit|role_edit|time_window_edit|always_edit)$', description="Response edit policy")
    edit_time_window_hours: Optional[int] = Field(None, ge=1, description="Edit time window in hours")
    edit_allowed_roles: Optional[List[str]] = Field([], description="Roles allowed to edit")
    require_login: bool = Field(False, description="Require login to submit")


class FormUI(BaseModel):
    theme: Dict[str, Any] = Field(..., description="UI theme")
    layout: str = Field(..., regex=r'^(single_page|multi_page|wizard)$', description="Form layout")
    primary_color: Optional[str] = Field(None, regex=r'^#[0-9A-Fa-f]{6}$', description="Primary color")
    font: Optional[str] = Field(None, description="Font family")
    logo_url: Optional[str] = Field(None, description="Logo URL")
    cover_page: Optional[Dict[str, Any]] = Field(None, description="Cover page settings")
    thank_you_page: Optional[Dict[str, Any]] = Field(None, description="Thank you page settings")


class FormSchema(BaseModel):
    ui: FormUI = Field(..., description="UI configuration")
    access: FormAccessConfig = Field(..., description="Access configuration")
    settings: FormSettings = Field(..., description="Form settings")
    sections: List[Dict[str, Any]] = Field([], description="Form sections")


class FormCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Form name")
    description: Optional[str] = Field(None, max_length=500, description="Form description")
    org_id: str = Field(..., description="Organization ID")
    project_id: str = Field(..., description="Project ID")
    author_id: Optional[str] = Field(None, description="Author ID")


class FormUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Form name")
    description: Optional[str] = Field(None, max_length=500, description="Form description")


class BranchCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, regex=r'^[a-zA-Z0-9_-]+$', description="Branch name")
    from_branch: str = Field("main", description="Source branch")
    from_commit_id: Optional[str] = Field(None, description="Source commit ID")


class CommitCreate(BaseModel):
    schema: FormSchema = Field(..., description="Form schema")
    branch: str = Field("main", description="Branch name")
    parent_id: Optional[str] = Field(None, description="Parent commit ID")
    message: str = Field("Schema update", description="Commit message")
    author_id: Optional[str] = Field(None, description="Author ID")


class MergeRequest(BaseModel):
    source_branch: str = Field(..., description="Source branch")
    target_branch: str = Field(..., description="Target branch")
    author_id: Optional[str] = Field(None, description="Author ID")


class PublishRequest(BaseModel):
    branch: str = Field(..., description="Branch to publish")


# --- Analysis Models ---

class NodePosition(BaseModel):
    x: float = Field(..., ge=0, description="X position")
    y: float = Field(..., ge=0, description="Y position")


class NodeSize(BaseModel):
    width: float = Field(..., ge=50, description="Node width")
    height: float = Field(..., ge=50, description="Node height")


class AnalysisNode(BaseModel):
    id: str = Field(..., min_length=1, max_length=50, regex=r'^[a-zA-Z0-9_-]+$', description="Node ID")
    type: str = Field(..., min_length=1, description="Node type")
    position: NodePosition = Field(..., description="Node position")
    size: NodeSize = Field(..., description="Node size")
    properties: Dict[str, Any] = Field({}, description="Node properties")
    label: Optional[str] = Field(None, max_length=100, description="Node label")
    is_disabled: bool = Field(False, description="Is node disabled")


class AnalysisEdge(BaseModel):
    id: str = Field(..., min_length=1, max_length=50, regex=r'^[a-zA-Z0-9_-]+$', description="Edge ID")
    from_node: str = Field(..., description="Source node ID")
    from_port: str = Field(..., description="Source port")
    to_node: str = Field(..., description="Target node ID")
    to_port: str = Field(..., description="Target port")
    label: Optional[str] = Field(None, max_length=50, description="Edge label")


class AnalysisGraph(BaseModel):
    nodes: List[AnalysisNode] = Field([], description="Analysis nodes")
    edges: List[AnalysisEdge] = Field([], description="Analysis edges")


class AnalysisCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Analysis name")
    description: Optional[str] = Field(None, max_length=500, description="Analysis description")
    org_id: str = Field(..., description="Organization ID")
    project_id: str = Field(..., description="Project ID")
    graph: AnalysisGraph = Field(..., description="Analysis graph")
    linked_form_ids: Optional[List[str]] = Field([], description="Linked form IDs")
    execution_modes: List[str] = Field(["on_demand"], description="Execution modes")
    schedule: Optional[str] = Field(None, description="Cron schedule")
    reactive_debounce_ms: int = Field(1000, ge=0, description="Reactive debounce in milliseconds")


class AnalysisUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Analysis name")
    description: Optional[str] = Field(None, max_length=500, description="Analysis description")
    graph: Optional[AnalysisGraph] = Field(None, description="Analysis graph")
    linked_form_ids: Optional[List[str]] = Field(None, description="Linked form IDs")
    execution_modes: Optional[List[str]] = Field(None, description="Execution modes")
    schedule: Optional[str] = Field(None, description="Cron schedule")
    reactive_debounce_ms: Optional[int] = Field(None, ge=0, description="Reactive debounce in milliseconds")


# --- Dashboard Models ---

class WidgetPosition(BaseModel):
    x: float = Field(..., ge=0, description="X position")
    y: float = Field(..., ge=0, description="Y position")


class WidgetSize(BaseModel):
    width: float = Field(..., ge=50, description="Widget width")
    height: float = Field(..., ge=50, description="Widget height")


class DataBinding(BaseModel):
    analysis_id: str = Field(..., description="Analysis ID")
    node_id: str = Field(..., description="Node ID")
    refresh_mode: str = Field("with_dashboard", regex=r'^(with_dashboard|independent|never)$', description="Refresh mode")


class FilterBinding(BaseModel):
    filter_widget_id: str = Field(..., description="Filter widget ID")
    bound_field: str = Field(..., description="Bound field")


class DashboardWidget(BaseModel):
    id: str = Field(..., min_length=1, max_length=50, regex=r'^[a-zA-Z0-9_-]+$', description="Widget ID")
    type: str = Field(..., min_length=1, description="Widget type")
    position: WidgetPosition = Field(..., description="Widget position")
    size: WidgetSize = Field(..., description="Widget size")
    z_index: int = Field(0, ge=0, description="Z-index")
    is_locked: bool = Field(False, description="Is widget locked")
    properties: Dict[str, Any] = Field({}, description="Widget properties")
    data_binding: Optional[DataBinding] = Field(None, description="Data binding")
    filters: Optional[List[FilterBinding]] = Field([], description="Filter bindings")


class DashboardCanvas(BaseModel):
    width: float = Field(..., ge=100, description="Canvas width")
    height: float = Field(..., ge=100, description="Canvas height")
    background_color: str = Field("#FFFFFF", regex=r'^#[0-9A-Fa-f]{6}$', description="Background color")
    widgets: List[DashboardWidget] = Field([], description="Dashboard widgets")


class DashboardSettings(BaseModel):
    auto_refresh: bool = Field(False, description="Auto refresh enabled")
    refresh_interval_seconds: int = Field(300, ge=10, description="Refresh interval in seconds")
    theme: Dict[str, Any] = Field({}, description="Dashboard theme")


class DashboardCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Dashboard name")
    description: Optional[str] = Field(None, max_length=500, description="Dashboard description")
    org_id: str = Field(..., description="Organization ID")
    project_id: str = Field(..., description="Project ID")
    canvas: DashboardCanvas = Field(..., description="Dashboard canvas")
    settings: DashboardSettings = Field(DashboardSettings(), description="Dashboard settings")
    linked_analysis_ids: Optional[List[str]] = Field([], description="Linked analysis IDs")


class DashboardUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="Dashboard name")
    description: Optional[str] = Field(None, max_length=500, description="Dashboard description")
    canvas: Optional[DashboardCanvas] = Field(None, description="Dashboard canvas")
    settings: Optional[DashboardSettings] = Field(None, description="Dashboard settings")
    linked_analysis_ids: Optional[List[str]] = Field(None, description="Linked analysis IDs")


# --- Plugin Models ---

class PluginManifest(BaseModel):
    plugin_id: str = Field(..., min_length=2, max_length=50, regex=r'^[a-z0-9_-]+$', description="Plugin ID")
    name: str = Field(..., min_length=2, max_length=100, description="Plugin name")
    version: str = Field(..., regex=r'^\d+\.\d+\.\d+$', description="Plugin version")
    min_platform_version: str = Field(..., regex=r'^\d+\.\d+\.\d+$', description="Minimum platform version")
    author: Dict[str, str] = Field({}, description="Plugin author")
    description: str = Field(..., max_length=500, description="Plugin description")
    concept_targets: List[str] = Field([], description="Concept targets")
    permissions: List[str] = Field([], description="Plugin permissions")
    backend: Dict[str, Any] = Field({}, description="Backend configuration")
    components: List[Dict[str, Any]] = Field([], description="Plugin components")


class ComponentProperty(BaseModel):
    key: str = Field(..., min_length=1, max_length=50, description="Property key")
    label: str = Field(..., min_length=1, max_length=100, description="Property label")
    type: str = Field(..., regex=r'^(string|number|boolean|enum|color|object|array)$', description="Property type")
    default: Any = Field(None, description="Default value")
    required: bool = Field(False, description="Is property required")
    options: List[Any] = Field([], description="Property options")
    group: str = Field("General", description="Property group")


class ComponentPort(BaseModel):
    id: str = Field(..., min_length=1, max_length=50, description="Port ID")
    label: str = Field(..., min_length=1, max_length=100, description="Port label")
    data_type: str = Field(..., description="Port data type")


class ComponentSchema(BaseModel):
    type: str = Field(..., min_length=1, max_length=50, description="Component type")
    display_name: str = Field(..., min_length=1, max_length=100, description="Display name")
    concept: str = Field(..., regex=r'^(form_field|analysis_node|dashboard_widget)$', description="Component concept")
    composition: List[Dict[str, Any]] = Field([], description="Component composition")
    properties: List[ComponentProperty] = Field([], description="Component properties")
    input_ports: List[ComponentPort] = Field([], description="Input ports")
    output_ports: List[ComponentPort] = Field([], description="Output ports")
    widget_config: Dict[str, Any] = Field({}, description="Widget configuration")
    preview_schema: Dict[str, Any] = Field({}, description="Preview schema")
    offline_support: bool = Field(False, description="Offline support")


class ComponentConfigValidation(BaseModel):
    component_type: str = Field(..., min_length=1, description="Component type")
    config: Dict[str, Any] = Field(..., description="Component configuration")


# --- File Upload Models ---

class UploadInit(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255, description="Filename")
    file_size: int = Field(..., ge=1, le=500 * 1024 * 1024, description="File size in bytes")
    org_id: str = Field(..., description="Organization ID")
    form_id: str = Field(..., description="Form ID")
    question_id: str = Field(..., description="Question ID")
    response_id: Optional[str] = Field(None, description="Response ID")


class UploadChunk(BaseModel):
    upload_offset: int = Field(..., ge=0, description="Upload offset")
    content_length: int = Field(..., ge=1, le=5 * 1024 * 1024, description="Content length")


# --- API Key Models ---

class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="API key name")
    scopes: List[str] = Field([], description="API key scopes")
    rate_limit_per_hour: int = Field(1000, ge=1, le=10000, description="Rate limit per hour")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")


class APIKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="API key name")
    scopes: Optional[List[str]] = Field(None, description="API key scopes")
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=10000, description="Rate limit per hour")
    status: Optional[str] = Field(None, regex=r'^(active|revoked)$', description="API key status")


# --- Response Validation ---

class FormResponse(BaseModel):
    answers: Dict[str, Any] = Field(..., description="Form answers")
    respondent_email: Optional[str] = Field(None, regex=r'^[^@]+@[^@]+\.[^@]+$', description="Respondent email")
    session_id: Optional[str] = Field(None, description="Session ID")
    started_at: Optional[datetime] = Field(None, description="Start time")
    time_taken_seconds: Optional[int] = Field(None, ge=0, description="Time taken in seconds")


# --- Validation Utilities ---

class ValidationUtils:
    @staticmethod
    def validate_object_id(value: str) -> bool:
        """Validate MongoDB ObjectId format"""
        return re.match(r'^[0-9a-fA-F]{24}$', value) is not None
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        return re.match(r'^[^@]+@[^@]+\.[^@]+$', email) is not None
    
    @staticmethod
    def validate_color(color: str) -> bool:
        """Validate hex color format"""
        return re.match(r'^#[0-9A-Fa-f]{6}$', color) is not None
    
    @staticmethod
    def validate_cron_expression(cron: str) -> bool:
        """Validate cron expression format"""
        # Basic validation for cron expression
        parts = cron.split()
        if len(parts) != 5:
            return False
        
        # Each part should contain valid cron syntax
        valid_chars = set('0123456789*/-,')
        for part in parts:
            if not all(c in valid_chars or c.isalpha() for c in part):
                return False
        
        return True
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Basic HTML sanitization"""
        if not text:
            return text
        
        # Remove potentially dangerous HTML tags
        dangerous_tags = ['script', 'iframe', 'object', 'embed', 'link', 'style']
        for tag in dangerous_tags:
            text = re.sub(f'<{tag}.*?>.*?</{tag}>', '', text, flags=re.IGNORECASE | re.DOTALL)
            text = re.sub(f'<{tag}.*?>', '', text, flags=re.IGNORECASE)
        
        return text