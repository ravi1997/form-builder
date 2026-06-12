from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum
from bson import ObjectId
from uuid import uuid4
from .base import BaseDBModel, PyObjectId


class ExecutionMode(str, Enum):
    ON_DEMAND = "on_demand"
    REACTIVE = "reactive"
    SCHEDULED = "scheduled"


class AnalysisStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"


class TriggerType(str, Enum):
    ON_DEMAND = "on_demand"
    SCHEDULED = "scheduled"
    REACTIVE = "reactive"
    MANUAL = "manual"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class OutputType(str, Enum):
    TABLE = "table"
    VALUE = "value"
    DATAFRAME = "dataframe"
    CHART_DATA = "chart_data"
    ERROR = "error"


class ExportFormat(str, Enum):
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


class ExportStatus(str, Enum):
    QUEUED = "queued"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


class NodePosition(BaseModel):
    """Position of a node in the analysis graph."""
    
    x: float = Field(...)
    y: float = Field(...)


class NodeSize(BaseModel):
    """Size of a node in the analysis graph."""
    
    width: float = Field(...)
    height: float = Field(...)


class NodeStatus(BaseModel):
    """Status of a node during analysis execution."""
    
    status: str = Field(...)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    error: Optional[str] = Field(None)


class Node(BaseModel):
    """Node in the analysis graph."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str = Field(..., description="Component type from component_schemas")
    position: NodePosition = Field(...)
    size: NodeSize = Field(...)
    properties: Dict[str, Any] = Field(default_factory=dict)
    label: str = Field(...)
    is_disabled: bool = Field(default=False)


class Edge(BaseModel):
    """Edge in the analysis graph."""
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    from_node: str = Field(...)
    from_port: str = Field(...)
    to_node: str = Field(...)
    to_port: str = Field(...)
    label: Optional[str] = Field(None)


class Graph(BaseModel):
    """Analysis graph structure."""
    
    nodes: List[Node] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)


class ColumnDefinition(BaseModel):
    """Column definition for analysis results."""
    
    name: str = Field(...)
    type: str = Field(...)
    label: str = Field(...)


class Analysis(BaseDBModel):
    """Model for analyses collection."""
    
    project_id: PyObjectId = Field(...)
    name: str = Field(...)
    description: Optional[str] = Field(None)
    linked_form_ids: List[PyObjectId] = Field(default_factory=list)
    execution_modes: List[ExecutionMode] = Field(default_factory=list)
    schedule: Optional[str] = Field(None, description="Cron expression, null if not scheduled")
    reactive_debounce_ms: int = Field(default=1000)
    graph: Graph = Field(default_factory=Graph)
    last_run_id: Optional[PyObjectId] = Field(None)
    status: AnalysisStatus = Field(default=AnalysisStatus.IDLE)


class AnalysisRun(BaseModel):
    """Model for analysis_runs collection."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    analysis_id: PyObjectId = Field(...)
    org_id: PyObjectId = Field(...)
    trigger: TriggerType = Field(...)
    triggered_by: PyObjectId = Field(...)
    status: RunStatus = Field(default=RunStatus.QUEUED)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)
    celery_task_id: Optional[str] = Field(None)
    node_statuses: Dict[str, NodeStatus] = Field(default_factory=dict)
    error_summary: Optional[str] = Field(None)
    result_ids: Dict[str, PyObjectId] = Field(default_factory=dict)
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


class AnalysisResult(BaseModel):
    """Model for analysis_results collection."""
    
    id: Optional[PyObjectId] = Field(None, alias="_id")
    run_id: PyObjectId = Field(...)
    analysis_id: PyObjectId = Field(...)
    node_id: str = Field(...)
    org_id: PyObjectId = Field(...)
    output_type: OutputType = Field(...)
    data: Dict[str, Any] = Field(..., description="Actual result data")
    row_count: int = Field(default=0)
    column_definitions: List[ColumnDefinition] = Field(default_factory=list)
    cached_until: Optional[datetime] = Field(None)
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


class AnalysisExport(BaseDBModel):
    """Model for analysis_exports collection."""
    
    analysis_id: PyObjectId = Field(...)
    run_id: PyObjectId = Field(...)
    format: ExportFormat = Field(...)
    node_ids: List[str] = Field(default_factory=list)
    file_path: str = Field(...)
    file_size_bytes: Optional[int] = Field(None)
    status: ExportStatus = Field(default=ExportStatus.QUEUED)
    expires_at: Optional[datetime] = Field(None)