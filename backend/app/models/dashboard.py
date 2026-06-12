from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from uuid import uuid4
from .base import BaseDBModel, PyObjectId


class WidgetPosition(BaseModel):
    """Position of a widget on the dashboard canvas."""
    
    x: float = Field(...)
    y: float = Field(...)


class WidgetSize(BaseModel):
    """Size of a widget on the dashboard canvas."""
    
    width: float = Field(...)
    height: float = Field(...)


class RefreshMode(str, Enum):
    WITH_DASHBOARD = "with_dashboard"
    INDEPENDENT = "independent"
    NEVER = "never"


class DataBinding(BaseModel):
    """Data binding for dashboard widgets."""
    
    analysis_id: PyObjectId = Field(...)
    node_id: str = Field(...)
    refresh_mode: RefreshMode = Field(default=RefreshMode.WITH_DASHBOARD)


class FilterBinding(BaseModel):
    """Filter binding for dashboard widgets."""
    
    filter_widget_id: str = Field(...)
    bound_field: str = Field(...)


class Widget(BaseModel):
    """Widget on the dashboard canvas."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str = Field(..., description="Component type")
    position: WidgetPosition = Field(...)
    size: WidgetSize = Field(...)
    z_index: int = Field(default=0)
    is_locked: bool = Field(default=False)
    properties: Dict[str, Any] = Field(default_factory=dict)
    data_binding: Optional[DataBinding] = Field(None)
    filters: List[FilterBinding] = Field(default_factory=list)


class Canvas(BaseModel):
    """Dashboard canvas configuration."""
    
    width: float = Field(...)
    height: float = Field(...)
    background_color: str = Field(default="#FFFFFF")
    widgets: List[Widget] = Field(default_factory=list)


class DashboardSettings(BaseModel):
    """Dashboard settings configuration."""
    
    auto_refresh: bool = Field(default=True)
    refresh_interval_seconds: int = Field(default=300)
    theme: Dict[str, Any] = Field(default_factory=dict)


class Dashboard(BaseDBModel):
    """Model for dashboards collection."""
    
    project_id: PyObjectId = Field(...)
    name: str = Field(...)
    description: Optional[str] = Field(None)
    is_public: bool = Field(default=False)
    public_token: Optional[str] = Field(None, description="Token for public access")
    canvas: Canvas = Field(...)
    settings: DashboardSettings = Field(default_factory=DashboardSettings)
    linked_analysis_ids: List[PyObjectId] = Field(default_factory=list)


class DashboardSnapshot(BaseModel):
    """Model for dashboard_snapshots collection."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    dashboard_id: PyObjectId = Field(...)
    org_id: PyObjectId = Field(...)
    data: Dict[str, Any] = Field(...)
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