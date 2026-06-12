import datetime
import uuid
import json
from typing import Optional, Dict, Any, List, Union
import logging
from bson import ObjectId
from app.extensions import mongo, redis_client
from app.models.dashboard import (
    Dashboard, Widget, Canvas, DashboardSettings, DashboardTheme,
    DashboardResponse, LinkedAnalysis, AnalysisOutputNode,
    WidgetDataResponse, CanvasDataResponse, FilterOptionsResponse
)
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)


def map_node_type_to_output_type(node_type: str) -> str:
    """Map analysis node type to output type."""
    if node_type in ("kpi_value", "scalar_aggregator"):
        return "value"
    elif node_type in ("table_output", "table_generator"):
        return "table"
    elif node_type in ("bar_chart_data", "line_chart_data", "pie_chart_data", "chart_formatter"):
        return "chart_data"
    return "unknown"


def serialize_doc(doc: Any) -> Any:
    """Serialize MongoDB document for JSON response."""
    if not doc:
        return doc
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        new_doc = {}
        for k, v in doc.items():
            if isinstance(v, ObjectId):
                new_doc[k] = str(v)
            elif isinstance(v, datetime.datetime):
                new_doc[k] = v.isoformat()
            elif isinstance(v, dict):
                new_doc[k] = serialize_doc(v)
            elif isinstance(v, list):
                new_doc[k] = [serialize_doc(item) if isinstance(item, (dict, list)) else (str(item) if isinstance(item, ObjectId) else item) for item in v]
            else:
                new_doc[k] = v
        return new_doc
    if isinstance(doc, ObjectId):
        return str(doc)
    return doc


def apply_filters(result_data: Dict[str, Any], widget: Dict[str, Any], filter_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Applies active filter state to the result data.
    Only table/dataframe-like structures support row filtering.
    """
    if not isinstance(result_data, dict):
        return result_data

    # Table rows could be in result_data['rows'] directly, or under result_data['out']['rows']
    target_dict = result_data
    if "rows" not in target_dict and isinstance(target_dict.get("out"), dict):
        target_dict = target_dict["out"]

    if "rows" not in target_dict:
        return result_data

    rows = target_dict.get("rows", [])
    if not isinstance(rows, list):
        return result_data

    for binding in widget.get("filters", []):
        filter_widget_id = binding.get("filter_widget_id")
        bound_field = binding.get("bound_field")

        if not filter_widget_id or not bound_field:
            continue

        if filter_widget_id not in filter_state:
            continue  # Filter widget has no value set → skip

        filter_value = filter_state[filter_widget_id]
        if filter_value is None or filter_value == "":
            continue

        if isinstance(filter_value, list):
            rows = [r for r in rows if r.get(bound_field) in filter_value]
        elif isinstance(filter_value, dict) and "start" in filter_value and "end" in filter_value:
            # Date range filter
            start_val = str(filter_value["start"])
            end_val = str(filter_value["end"])
            rows = [
                r for r in rows
                if start_val <= str(r.get(bound_field, "")) <= end_val
            ]
        else:
            rows = [r for r in rows if str(r.get(bound_field, "")) == str(filter_value)]

    target_dict["rows"] = rows
    target_dict["row_count"] = len(rows)
    
    # If we modified result_data["out"], reflect changes
    if "out" in result_data and isinstance(result_data["out"], dict) and "rows" in result_data["out"]:
        result_data["out"] = target_dict

    return result_data


class DashboardService:
    """Service for dashboard operations with canvas and widget management."""

    def _project_query(self, project_oid: ObjectId, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build project query with access control."""
        query = {"_id": project_oid, "is_deleted": False}
        if context and context.get("system_role") != "super_admin":
            org_ids = context.get("org_ids", [])
            if org_ids:
                query["org_id"] = {"$in": [ObjectId(org_id) if ObjectId.is_valid(org_id) else org_id for org_id in org_ids]}
        return query

    def _dashboard_query(self, dashboard_oid: ObjectId, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build dashboard query with access control."""
        query = {"_id": dashboard_oid, "is_deleted": False}
        if context and context.get("system_role") != "super_admin":
            org_ids = context.get("org_ids", [])
            if org_ids:
                query["org_id"] = {"$in": [ObjectId(org_id) if ObjectId.is_valid(org_id) else org_id for org_id in org_ids]}
        return query

    def _analysis_query(self, analysis_oid: ObjectId, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build analysis query with access control."""
        query = {"_id": analysis_oid, "is_deleted": False}
        if context and context.get("system_role") != "super_admin":
            org_ids = context.get("org_ids", [])
            if org_ids:
                query["org_id"] = {"$in": [ObjectId(org_id) if ObjectId.is_valid(org_id) else org_id for org_id in org_ids]}
        return query

    def create_dashboard(self, data: Dict[str, Any], author_id: str, context: Optional[Dict[str, Any]] = None) -> Dashboard:
        """Create a new dashboard with canvas structure and audit logging."""
        project_id = data.get("project_id")
        if not project_id:
            raise ValueError("project_id is required")
            
        project_oid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        project = mongo.db.projects.find_one(self._project_query(project_oid, context))
        if not project:
            raise ValueError("Project not found")
            
        org_id = project.get("org_id")
        name = data.get("name")
        if not name or not name.strip():
            raise ValueError("Dashboard name is required")
        name = name.strip()
        if len(name) > 120:
            raise ValueError("Dashboard name exceeds 120 characters")
            
        # Check name uniqueness within the project (case-insensitive)
        existing = mongo.db.dashboards.find_one({
            "project_id": project_oid,
            "name": {"$regex": f"^{name}$", "$options": "i"},
            "is_deleted": False
        })
        if existing:
            raise ValueError("Dashboard name conflict")
            
        description = data.get("description", "")
        if description and len(description) > 500:
            raise ValueError("Description exceeds 500 characters")
            
        canvas_data = data.get("canvas") or {}
        width = canvas_data.get("width", 1920)
        height = canvas_data.get("height", 1080)
        bg_color = canvas_data.get("background_color", "#F5F5F5")
        
        if not (800 <= width <= 7680):
            raise ValueError("Canvas width must be between 800 and 7680")
        if not (600 <= height <= 4320):
            raise ValueError("Canvas height must be between 600 and 4320")
            
        # Widgets must be empty on creation
        widgets = []
        
        settings_data = data.get("settings") or {}
        auto_refresh = settings_data.get("auto_refresh", False)
        refresh_interval = settings_data.get("refresh_interval_seconds", 60)
        if auto_refresh and not (10 <= refresh_interval <= 3600):
            raise ValueError("Refresh interval must be between 10 and 3600 seconds")
            
        theme_data = settings_data.get("theme") or {
            "font_family": "Inter",
            "primary_color": "#1976D2",
            "border_radius": 8
        }
        
        author_oid = ObjectId(author_id) if author_id and ObjectId.is_valid(author_id) else author_id
        
        dashboard_doc = {
            "org_id": org_id,
            "project_id": project_oid,
            "name": name,
            "description": description,
            "is_public": False,
            "public_token": None,
            "canvas": {
                "width": width,
                "height": height,
                "background_color": bg_color,
                "widgets": widgets
            },
            "settings": {
                "auto_refresh": auto_refresh,
                "refresh_interval_seconds": refresh_interval,
                "theme": theme_data
            },
            "linked_analysis_ids": [],
            "created_at": datetime.datetime.utcnow().isoformat(),
            "updated_at": datetime.datetime.utcnow().isoformat(),
            "created_by": author_oid,
            "is_deleted": False,
            "deleted_at": None
        }
        
        result = mongo.db.dashboards.insert_one(dashboard_doc)
        dashboard_doc["_id"] = result.inserted_id
        
        # Log audit event
        try:
            audit_service.log_action(
                entity_type="dashboard",
                entity_id=result.inserted_id,
                action="create",
                actor_id=author_oid,
                actor_role="user",
                before={},
                after={
                    "name": name,
                    "project_id": str(project_oid),
                    "org_id": str(org_id) if org_id else None,
                    "canvas_width": width,
                    "canvas_height": height
                }
            )
        except Exception as e:
            logger.error(f"Failed to log dashboard creation audit event: {e}")
        
        return dashboard_doc

    def list_dashboards(self, project_id: str, page: int = 1, per_page: int = 20, 
                       search_text: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """List dashboards for a project with pagination."""
        project_oid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        query = {"project_id": project_oid, "is_deleted": False}
        project = mongo.db.projects.find_one(self._project_query(project_oid, context))
        if not project:
            return [], {"total": 0, "page": page, "per_page": per_page, "total_pages": 0}
        
        if search_text:
            query["name"] = {"$regex": search_text, "$options": "i"}
            
        total = mongo.db.dashboards.count_documents(query)
        dashboards_cursor = mongo.db.dashboards.find(query)\
            .skip((page - 1) * per_page)\
            .limit(per_page)
            
        dashboards = []
        for d in dashboards_cursor:
            # Strip canvas widgets for lists
            if "canvas" in d and "widgets" in d["canvas"]:
                del d["canvas"]["widgets"]
            # Populate creator user metadata
            creator_id = d.get("created_by")
            if creator_id:
                user = mongo.db.users.find_one({"_id": ObjectId(creator_id) if ObjectId.is_valid(creator_id) else creator_id})
                if user:
                    d["created_by_user"] = {
                        "_id": str(user["_id"]),
                        "full_name": user.get("full_name") or user.get("name") or "Unknown",
                        "avatar_url": user.get("avatar_url") or ""
                    }
                else:
                    d["created_by_user"] = {
                        "_id": str(creator_id),
                        "full_name": "Unknown",
                        "avatar_url": ""
                    }
            dashboards.append(d)
            
        total_pages = (total + per_page - 1) // per_page if total > 0 else 0
        return dashboards, {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages
        }

    def get_dashboard(self, dashboard_id: str, context: Optional[Dict[str, Any]] = None) -> Optional[DashboardResponse]:
        """Get dashboard details with linked analyses."""
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        dashboard = mongo.db.dashboards.find_one(self._dashboard_query(d_oid, context))
        if not dashboard:
            return None
            
        # Resolve linked analyses metadata
        linked_analyses = []
        for a_id in dashboard.get("linked_analysis_ids", []):
            a_oid = ObjectId(a_id) if ObjectId.is_valid(a_id) else a_id
            analysis = mongo.db.analyses.find_one(self._analysis_query(a_oid, context))
            if not analysis:
                continue
                
            last_run = mongo.db.analysis_runs.find_one(
                {"analysis_id": a_oid},
                sort=[("created_at", -1)]
            )
            status = "idle"
            last_run_id = None
            if last_run:
                status = last_run.get("status", "idle")
                last_run_id = str(last_run["_id"])
                
            output_nodes = []
            nodes = analysis.get("graph", {}).get("nodes", [])
            for node in nodes:
                node_type = node.get("type")
                if node_type in (
                    "table_output", "kpi_value", "bar_chart_data", "line_chart_data", "pie_chart_data",
                    "table_generator", "scalar_aggregator", "chart_formatter"
                ):
                    node_id = node.get("id")
                    props = node.get("properties", {})
                    label = props.get("title") or props.get("label") or props.get("name") or node_id
                    output_type = map_node_type_to_output_type(node_type)
                    output_nodes.append({
                        "node_id": node_id,
                        "label": label,
                        "type": node_type,
                        "output_type": output_type
                    })
            linked_analyses.append({
                "_id": str(analysis["_id"]),
                "name": analysis.get("name", "Unnamed Analysis"),
                "status": status,
                "last_run_id": last_run_id,
                "output_nodes": output_nodes
            })
            
        return {
            "dashboard": dashboard,
            "linked_analyses": linked_analyses
        }

    def update_dashboard(self, dashboard_id: str, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Optional[DashboardResponse]:
        """Update dashboard metadata with audit logging."""
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        dashboard = mongo.db.dashboards.find_one(self._dashboard_query(d_oid, context))
        if not dashboard:
            return None
            
        update_fields = {}
        before_state = {}
        after_state = {}
        
        name = data.get("name")
        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("Dashboard name is required")
            if len(name) > 120:
                raise ValueError("Dashboard name exceeds 120 characters")
                
            before_state["name"] = dashboard.get("name")
            after_state["name"] = name
                
            # Verify uniqueness
            existing = mongo.db.dashboards.find_one({
                "project_id": dashboard["project_id"],
                "name": {"$regex": f"^{name}$", "$options": "i"},
                "_id": {"$ne": d_oid},
                "is_deleted": False
            })
            if existing:
                raise ValueError("Dashboard name conflict")
            update_fields["name"] = name
            
        description = data.get("description")
        if description is not None:
            if len(description) > 500:
                raise ValueError("Description exceeds 500 characters")
            before_state["description"] = dashboard.get("description")
            after_state["description"] = description
            update_fields["description"] = description
            
        settings = data.get("settings")
        if settings is not None:
            current_settings = dashboard.get("settings") or {}
            
            auto_refresh = settings.get("auto_refresh", current_settings.get("auto_refresh", False))
            refresh_interval = settings.get("refresh_interval_seconds", current_settings.get("refresh_interval_seconds", 60))
            if auto_refresh and not (10 <= refresh_interval <= 3600):
                raise ValueError("Refresh interval must be between 10 and 3600 seconds")
                
            before_state["settings"] = current_settings
            merged_settings = {
                "auto_refresh": auto_refresh,
                "refresh_interval_seconds": refresh_interval,
                "theme": {**(current_settings.get("theme") or {}), **(settings.get("theme") or {})}
            }
            after_state["settings"] = merged_settings
            update_fields["settings"] = merged_settings
            
        if update_fields:
            update_fields["updated_at"] = datetime.datetime.utcnow().isoformat()
            mongo.db.dashboards.update_one(self._dashboard_query(d_oid, context), {"$set": update_fields})
            
            # Log audit event
            try:
                audit_service.log_action(
                    entity_type="dashboard",
                    entity_id=d_oid,
                    action="update",
                    actor_id=dashboard.get("created_by"),
                    actor_role="user",
                    before=before_state,
                    after=after_state
                )
            except Exception as e:
                logger.error(f"Failed to log dashboard update audit event: {e}")
            
        return self.get_dashboard(dashboard_id, context)

    def delete_dashboard(self, dashboard_id: str, context: Optional[Dict[str, Any]] = None, deleted_by: Optional[str] = None) -> None:
        """Soft delete a dashboard with audit logging."""
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        dashboard = mongo.db.dashboards.find_one(self._dashboard_query(d_oid, context))
        if not dashboard:
            raise ValueError("Dashboard not found")
        
        before_state = {
            "name": dashboard.get("name"),
            "project_id": str(dashboard.get("project_id")),
            "org_id": str(dashboard.get("org_id")) if dashboard.get("org_id") else None,
            "is_deleted": False
        }
        
        deleted_by_oid = ObjectId(deleted_by) if deleted_by and ObjectId.is_valid(deleted_by) else deleted_by
        
        mongo.db.dashboards.update_one(
            self._dashboard_query(d_oid, context),
            {"$set": {
                "is_deleted": True,
                "deleted_at": datetime.datetime.utcnow().isoformat(),
                "updated_at": datetime.datetime.utcnow().isoformat()
            }}
        )
        
        # Log audit event
        try:
            audit_service.log_action(
                entity_type="dashboard",
                entity_id=d_oid,
                action="delete",
                actor_id=deleted_by_oid or dashboard.get("created_by"),
                actor_role="user",
                before=before_state,
                after={"is_deleted": True, "deleted_at": datetime.datetime.utcnow().isoformat()}
            )
        except Exception as e:
            logger.error(f"Failed to log dashboard deletion audit event: {e}")

    def save_canvas(self, dashboard_id: str, canvas: Dict[str, Any], context: Optional[Dict[str, Any]] = None, author_id: Optional[str] = None) -> Optional[DashboardResponse]:
        """Save dashboard canvas with widgets and audit logging."""
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        dashboard = mongo.db.dashboards.find_one(self._dashboard_query(d_oid, context))
        if not dashboard:
            return None
            
        if not isinstance(canvas, dict):
            raise ValueError("Canvas must be a dictionary")
            
        width = canvas.get("width", 1920)
        height = canvas.get("height", 1080)
        bg_color = canvas.get("background_color", "#F5F5F5")
        
        if not (800 <= width <= 7680):
            raise ValueError("Canvas width must be between 800 and 7680")
        if not (600 <= height <= 4320):
            raise ValueError("Canvas height must be between 600 and 4320")
            
        widgets = canvas.get("widgets", [])
        if not isinstance(widgets, list):
            raise ValueError("Widgets must be a list")
            
        widget_ids = set()
        linked_analysis_ids = set()
        
        # Built-in valid components
        valid_types = {
            "kpi_card", "bar_chart", "line_chart", "pie_chart", "data_table",
            "text_label", "image_widget", "filter_widget", "divider_widget"
        }
        valid_refresh_modes = {"with_dashboard", "independent", "never"}
        filter_widget_ids = set()
        
        for widget in widgets:
            wid = widget.get("id")
            wtype = widget.get("type")
            pos = widget.get("position") or {}
            size = widget.get("size") or {}
            z_index = widget.get("z_index", 0)
            binding = widget.get("data_binding")
            
            if not wid:
                raise ValueError("Each widget must have an id")
            try:
                uuid.UUID(str(wid))
            except ValueError:
                raise ValueError(f"Widget id {wid} is not a valid UUIDv4")
                
            if wid in widget_ids:
                raise ValueError(f"Duplicate widget id found: {wid}")
            widget_ids.add(wid)
            
            if wtype not in valid_types:
                raise ValueError(f"Unknown widget type: {wtype}")

            if wtype == "filter_widget":
                filter_widget_ids.add(wid)
                
            if pos.get("x", 0) < 0 or pos.get("y", 0) < 0:
                raise ValueError("Widget coordinates x and y must be greater than or equal to 0")
                
            if size.get("width", 20) < 20 or size.get("height", 20) < 20:
                raise ValueError("Widget width and height must be greater than or equal to 20px")
                
            if not (0 <= z_index <= 999):
                raise ValueError("z_index must be between 0 and 999")
                
            if binding:
                analysis_id = binding.get("analysis_id")
                node_id = binding.get("node_id")
                refresh_mode = binding.get("refresh_mode", "with_dashboard")
                
                if refresh_mode not in valid_refresh_modes:
                    raise ValueError(f"Invalid refresh_mode: {refresh_mode}")
                if not analysis_id or not node_id:
                    raise ValueError("data_binding requires analysis_id and node_id")

                a_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
                analysis = mongo.db.analyses.find_one(self._analysis_query(a_oid, context))
                if not analysis:
                    raise ValueError(f"Bound analysis {analysis_id} does not exist")

                nodes = analysis.get("graph", {}).get("nodes", [])
                if not any(n.get("id") == node_id for n in nodes):
                    raise ValueError(f"Node {node_id} not found in analysis {analysis_id}")

                linked_analysis_ids.add(a_oid)

            for f in widget.get("filters", []):
                filter_widget_id = f.get("filter_widget_id")
                if not filter_widget_id:
                    raise ValueError("Each filter binding must specify filter_widget_id")
                if filter_widget_id == wid:
                    raise ValueError("Widget cannot filter itself")

        # Verify that each referenced filter widget id exists in the widgets array
        for widget in widgets:
            for f in widget.get("filters", []):
                fwid = f.get("filter_widget_id")
                if fwid not in widget_ids:
                    raise ValueError(f"Filter widget {fwid} does not exist in canvas")
                    
        linked_analysis_list = list(linked_analysis_ids)
        
        # Atomically update
        before_widget_count = len(dashboard.get("canvas", {}).get("widgets", []))
        after_widget_count = len(widgets)
        
        mongo.db.dashboards.update_one(
            self._dashboard_query(d_oid, context),
            {"$set": {
                "canvas": {
                    "width": width,
                    "height": height,
                    "background_color": bg_color,
                    "widgets": widgets
                },
                "linked_analysis_ids": linked_analysis_list,
                "updated_at": datetime.datetime.utcnow().isoformat()
            }}
        )
        
        # Write Audit Log
        try:
            audit_service.log_action(
                entity_type="dashboard",
                entity_id=d_oid,
                action="canvas_saved",
                actor_id=ObjectId(author_id) if author_id and ObjectId.is_valid(author_id) else dashboard.get("created_by"),
                actor_role="user",
                before={"widget_count": before_widget_count, "canvas_width": dashboard.get("canvas", {}).get("width"), "canvas_height": dashboard.get("canvas", {}).get("height")},
                after={"widget_count": after_widget_count, "canvas_width": width, "canvas_height": height}
            )
        except Exception as e:
            logger.error(f"Failed to log canvas save audit event: {e}")
        
        return self.get_dashboard(dashboard_id, context)

    def resolve_widget_data(self, dashboard: Dict[str, Any], filter_state: Optional[Dict[str, Any]] = None) -> Dict[str, WidgetDataResponse]:
        """Resolve widget data from analysis results."""
        if not filter_state:
            filter_state = {}
            
        canvas = dashboard.get("canvas", {})
        widgets = canvas.get("widgets", [])
        
        widget_data = {}
        
        for widget in widgets:
            wid = widget.get("id")
            binding = widget.get("data_binding")
            
            if not binding or not binding.get("analysis_id") or not binding.get("node_id"):
                widget_data[wid] = {
                    "status": "no_binding",
                    "data": None,
                    "run_id": None,
                    "generated_at": None,
                    "error": None
                }
                continue
                
            analysis_id = binding["analysis_id"]
            node_id = binding["node_id"]
            
            a_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
            
            # Find latest completed analysis run
            last_run = mongo.db.analysis_runs.find_one(
                {"analysis_id": a_oid, "status": "completed"},
                sort=[("created_at", -1)]
            )
            if not last_run:
                widget_data[wid] = {
                    "status": "no_run",
                    "data": None,
                    "run_id": None,
                    "generated_at": None,
                    "error": "No completed runs found for bound analysis"
                }
                continue
                
            run_id = last_run["_id"]
            
            # Get analysis result
            result = mongo.db.analysis_results.find_one({
                "analysis_run_id": run_id,
                "node_id": node_id
            })
            if not result:
                widget_data[wid] = {
                    "status": "no_run",
                    "data": None,
                    "run_id": str(run_id),
                    "generated_at": last_run.get("updated_at"),
                    "error": "No cached result for output node in latest run"
                }
                continue
                
            if result.get("status") == "error":
                widget_data[wid] = {
                    "status": "error",
                    "data": None,
                    "run_id": str(run_id),
                    "generated_at": result.get("updated_at"),
                    "error": result.get("error", "Output node execution failed")
                }
                continue
                
            raw_data = result.get("data", {})
            
            # The actual output value of the node is normally stored inside raw_data['out']
            out_val = raw_data.get("out") if isinstance(raw_data, dict) else raw_data
            
            # Apply filter binding if applicable
            if isinstance(out_val, dict) and "rows" in out_val:
                # We can copy out_val to avoid mutating database-loaded documents
                out_val = json.loads(json.dumps(out_val))
                out_val = apply_filters(out_val, widget, filter_state)
            elif isinstance(out_val, dict) and "out" in out_val and isinstance(out_val["out"], dict) and "rows" in out_val["out"]:
                out_val = json.loads(json.dumps(out_val))
                out_val["out"] = apply_filters(out_val["out"], widget, filter_state)
                
            # Wrap scalar aggregations in a dict for KPI cards
            if not isinstance(out_val, (dict, list)) and out_val is not None:
                out_val = {"value": out_val}
                
            widget_data[wid] = {
                "status": "ok",
                "data": out_val,
                "run_id": str(run_id),
                "generated_at": result.get("updated_at") or last_run.get("updated_at"),
                "error": None
            }
            
        return widget_data

    def get_filter_options(self, analysis_id: str, node_id: str, column: str, limit: int = 200, context: Optional[Dict[str, Any]] = None) -> FilterOptionsResponse:
        """Get filter options for a column from analysis results."""
        a_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
        analysis = mongo.db.analyses.find_one(self._analysis_query(a_oid, context))
        if not analysis:
            return {"column": column, "values": [], "total_distinct": 0}
        
        # Latest completed run
        run = mongo.db.analysis_runs.find_one(
            {"analysis_id": a_oid, "status": "completed"},
            sort=[("created_at", -1)]
        )
        if not run:
            return {"column": column, "values": [], "total_distinct": 0}
            
        run_id = run["_id"]
        
        # Attempt to read from Redis cache
        cache_key = f"filter_opts:{analysis_id}:{node_id}:{column}:{run_id}"
        if redis_client:
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass
                
        # Find result
        res = mongo.db.analysis_results.find_one({
            "analysis_run_id": run_id,
            "node_id": node_id
        })
        if not res or res.get("status") != "success":
            return {"column": column, "values": [], "total_distinct": 0}
            
        raw_data = res.get("data", {})
        out_val = raw_data.get("out") if isinstance(raw_data, dict) else raw_data
        
        rows = []
        if isinstance(out_val, dict):
            rows = out_val.get("rows", [])
        elif isinstance(out_val, list):
            rows = out_val
            
        distinct_vals = set()
        for r in rows:
            if isinstance(r, dict) and column in r:
                val = r[column]
                if val is not None:
                    distinct_vals.add(val)
                    
        sorted_vals = sorted(list(distinct_vals), key=lambda x: str(x))
        limited_vals = sorted_vals[:limit]
        
        result_payload = {
            "column": column,
            "values": limited_vals,
            "total_distinct": len(sorted_vals)
        }
        
        # Write to Redis cache with 5 minutes TTL (300 seconds)
        if redis_client:
            try:
                redis_client.setex(cache_key, 300, json.dumps(result_payload))
            except Exception:
                pass
                
        return result_payload

    def create_snapshot(self, dashboard_id: str, author_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a dashboard snapshot."""
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        dashboard = mongo.db.dashboards.find_one(self._dashboard_query(d_oid, context))
        if not dashboard:
            return None
            
        widget_data = self.resolve_widget_data(dashboard)
        
        canvas = dashboard.get("canvas", {})
        canvas_meta = {
            "name": dashboard.get("name", ""),
            "width": canvas.get("width", 1920),
            "height": canvas.get("height", 1080),
            "background_color": canvas.get("background_color", "#F5F5F5")
        }
        
        snapshot_doc = {
            "dashboard_id": d_oid,
            "org_id": dashboard.get("org_id"),
            "data": {
                "widget_data": widget_data,
                "canvas_meta": canvas_meta,
                "snapshot_at": datetime.datetime.utcnow().isoformat()
            },
            "created_at": datetime.datetime.utcnow().isoformat(),
            "created_by": ObjectId(author_id) if author_id and ObjectId.is_valid(author_id) else author_id,
            "is_deleted": False,
            "deleted_at": None
        }
        
        mongo.db.dashboard_snapshots.insert_one(snapshot_doc)
        return snapshot_doc

    def enable_public_sharing(self, dashboard_id: str, author_id: Optional[str] = None) -> Dict[str, Any]:
        """Enable public sharing for a dashboard with audit logging."""
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
        if not dashboard:
            raise ValueError("Dashboard not found")

        token = str(uuid.uuid4())
        mongo.db.dashboards.update_one(
            {"_id": d_oid},
            {
                "$set": {
                    "is_public": True,
                    "public_token": token,
                    "updated_at": datetime.datetime.utcnow().isoformat(),
                }
            },
        )

        # Log audit event
        try:
            audit_service.log_action(
                entity_type="dashboard",
                entity_id=d_oid,
                action="dashboard_made_public",
                actor_id=ObjectId(author_id) if author_id and ObjectId.is_valid(author_id) else dashboard.get("created_by"),
                actor_role="user",
                before={"is_public": False},
                after={"is_public": True, "public_token": token}
            )
        except Exception as e:
            logger.error(f"Failed to log public sharing audit event: {e}")

        platform_config = mongo.db.system_config.find_one({"key": "platform_url"})
        platform_url = platform_config.get("value") if platform_config else "http://localhost:5000"
        public_url = f"{platform_url.rstrip('/')}/api/v1/public/dashboards/{token}"

        return {
            "is_public": True,
            "public_token": token,
            "public_url": public_url
        }

    def revoke_public_sharing(self, dashboard_id: str, author_id: Optional[str] = None) -> None:
        """Revoke public sharing for a dashboard with audit logging."""
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
        if not dashboard:
            raise ValueError("Dashboard not found")

        before_state = {"is_public": True, "public_token": dashboard.get("public_token")}
        
        mongo.db.dashboards.update_one(
            {"_id": d_oid},
            {
                "$set": {
                    "is_public": False,
                    "public_token": None,
                    "updated_at": datetime.datetime.utcnow().isoformat(),
                }
            },
        )
        
        # Log audit event
        try:
            audit_service.log_action(
                entity_type="dashboard",
                entity_id=d_oid,
                action="dashboard_sharing_revoked",
                actor_id=ObjectId(author_id) if author_id and ObjectId.is_valid(author_id) else dashboard.get("created_by"),
                actor_role="user",
                before=before_state,
                after={"is_public": False, "public_token": None}
            )
        except Exception as e:
            logger.error(f"Failed to log public sharing revocation audit event: {e}")

    def get_public_dashboard(self, token: str) -> Optional[Dict[str, Any]]:
        """Get public dashboard by token."""
        dashboard = mongo.db.dashboards.find_one({
            "public_token": token,
            "is_public": True,
            "is_deleted": False
        })
        return dashboard

    def list_snapshots(self, dashboard_id: str, page: int = 1, per_page: int = 20) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """List dashboard snapshots."""
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        
        query = {"dashboard_id": d_oid, "is_deleted": False}
        total = mongo.db.dashboard_snapshots.count_documents(query)

        snapshots_cursor = mongo.db.dashboard_snapshots.find(query, {"data.widget_data": 0}).sort(
            "created_at", -1
        ).skip((page - 1) * per_page).limit(per_page)

        snapshots = []
        for snap in snapshots_cursor:
            creator_id = snap.get("created_by")
            if creator_id:
                user = mongo.db.users.find_one({"_id": ObjectId(creator_id) if ObjectId.is_valid(creator_id) else creator_id})
                if user:
                    snap["created_by_user"] = {
                        "_id": str(user["_id"]),
                        "full_name": user.get("full_name") or user.get("name") or "Unknown",
                    }
                else:
                    snap["created_by_user"] = {"_id": str(creator_id), "full_name": "Unknown"}
            snapshots.append(snap)

        total_pages = (total + per_page - 1) // per_page if total > 0 else 0
        return snapshots, {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
        }

    def get_snapshot(self, dashboard_id: str, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific dashboard snapshot."""
        snap_oid = ObjectId(snapshot_id) if ObjectId.is_valid(snapshot_id) else snapshot_id
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        
        snapshot = mongo.db.dashboard_snapshots.find_one({
            "_id": snap_oid,
            "dashboard_id": d_oid,
            "is_deleted": False
        })
        return snapshot

    def delete_snapshot(self, dashboard_id: str, snapshot_id: str) -> None:
        """Delete a dashboard snapshot."""
        snap_oid = ObjectId(snapshot_id) if ObjectId.is_valid(snapshot_id) else snapshot_id
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        
        snapshot = mongo.db.dashboard_snapshots.find_one({
            "_id": snap_oid,
            "dashboard_id": d_oid,
            "is_deleted": False
        })
        if not snapshot:
            raise ValueError("Snapshot not found")

        mongo.db.dashboard_snapshots.update_one(
            {"_id": snap_oid},
            {"$set": {"is_deleted": True, "deleted_at": datetime.datetime.utcnow().isoformat()}},
        )


dashboard_service = DashboardService()