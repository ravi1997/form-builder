import datetime
import uuid
import json
import hashlib
from bson import ObjectId
from app.extensions import mongo, redis_client

def map_node_type_to_output_type(node_type):
    if node_type in ("kpi_value", "scalar_aggregator"):
        return "value"
    elif node_type in ("table_output", "table_generator"):
        return "table"
    elif node_type in ("bar_chart_data", "line_chart_data", "pie_chart_data", "chart_formatter"):
        return "chart_data"
    return "unknown"

def serialize_doc(doc):
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

def apply_filters(result_data: dict, widget: dict, filter_state: dict) -> dict:
    """
    Applies active filter state to the result data.
    Only table/dataframe-like structures support row filtering.
    """
    if not isinstance(result_data, dict):
        return result_data

    # Table rows could be in result_data['rows'] directly, or under result_data['out']['rows']
    # If the top level has 'rows', filter it. If it doesn't but has 'out', check if 'out' is a dict and has 'rows'
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
    def create_dashboard(self, data, author_id):
        project_id = data.get("project_id")
        if not project_id:
            raise ValueError("project_id is required")
            
        project_oid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        project = mongo.db.projects.find_one({"_id": project_oid})
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
            
        canvas = data.get("canvas") or {}
        width = canvas.get("width", 1920)
        height = canvas.get("height", 1080)
        bg_color = canvas.get("background_color", "#F5F5F5")
        
        if not (800 <= width <= 7680):
            raise ValueError("Canvas width must be between 800 and 7680")
        if not (600 <= height <= 4320):
            raise ValueError("Canvas height must be between 600 and 4320")
            
        # Widgets must be empty on creation
        widgets = []
        
        settings = data.get("settings") or {}
        auto_refresh = settings.get("auto_refresh", False)
        refresh_interval = settings.get("refresh_interval_seconds", 60)
        if auto_refresh and not (10 <= refresh_interval <= 3600):
            raise ValueError("Refresh interval must be between 10 and 3600 seconds")
            
        theme = settings.get("theme") or {
            "font_family": "Inter",
            "primary_color": "#1976D2",
            "border_radius": 8
        }
        
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
                "theme": theme
            },
            "linked_analysis_ids": [],
            "created_at": datetime.datetime.utcnow().isoformat(),
            "updated_at": datetime.datetime.utcnow().isoformat(),
            "created_by": ObjectId(author_id) if ObjectId.is_valid(author_id) else author_id,
            "is_deleted": False,
            "deleted_at": None
        }
        
        mongo.db.dashboards.insert_one(dashboard_doc)
        return dashboard_doc

    def list_dashboards(self, project_id, page=1, per_page=20, search_text=None):
        project_oid = ObjectId(project_id) if ObjectId.is_valid(project_id) else project_id
        query = {"project_id": project_oid, "is_deleted": False}
        
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

    def get_dashboard(self, dashboard_id):
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
        if not dashboard:
            return None
            
        # Resolve linked analyses metadata
        linked_analyses = []
        for a_id in dashboard.get("linked_analysis_ids", []):
            a_oid = ObjectId(a_id) if ObjectId.is_valid(a_id) else a_id
            analysis = mongo.db.analyses.find_one({"_id": a_oid})
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

    def update_dashboard(self, dashboard_id, data):
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
        if not dashboard:
            return None
            
        update_fields = {}
        
        name = data.get("name")
        if name is not None:
            name = name.strip()
            if not name:
                raise ValueError("Dashboard name is required")
            if len(name) > 120:
                raise ValueError("Dashboard name exceeds 120 characters")
                
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
            update_fields["description"] = description
            
        settings = data.get("settings")
        if settings is not None:
            current_settings = dashboard.get("settings") or {}
            
            auto_refresh = settings.get("auto_refresh", current_settings.get("auto_refresh", False))
            refresh_interval = settings.get("refresh_interval_seconds", current_settings.get("refresh_interval_seconds", 60))
            if auto_refresh and not (10 <= refresh_interval <= 3600):
                raise ValueError("Refresh interval must be between 10 and 3600 seconds")
                
            merged_settings = {
                "auto_refresh": auto_refresh,
                "refresh_interval_seconds": refresh_interval,
                "theme": {**(current_settings.get("theme") or {}), **(settings.get("theme") or {})}
            }
            update_fields["settings"] = merged_settings
            
        if update_fields:
            update_fields["updated_at"] = datetime.datetime.utcnow().isoformat()
            mongo.db.dashboards.update_one({"_id": d_oid}, {"$set": update_fields})
            
        return self.get_dashboard(dashboard_id)

    def delete_dashboard(self, dashboard_id):
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        mongo.db.dashboards.update_one(
            {"_id": d_oid},
            {"$set": {
                "is_deleted": True,
                "deleted_at": datetime.datetime.utcnow().isoformat(),
                "updated_at": datetime.datetime.utcnow().isoformat()
            }}
        )

    def save_canvas(self, dashboard_id, canvas):
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
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
                
                if refresh_mode not in ("with_dashboard", "independent", "never"):
                    raise ValueError(f"Invalid refresh_mode: {refresh_mode}")
                    
                if analysis_id:
                    # Verify analysis exists
                    a_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
                    analysis = mongo.db.analyses.find_one({"_id": a_oid})
                    if not analysis:
                        raise ValueError(f"Bound analysis {analysis_id} does not exist")
                    
                    if node_id:
                        # Verify node exists in analysis
                        nodes = analysis.get("graph", {}).get("nodes", [])
                        if not any(n.get("id") == node_id for n in nodes):
                            raise ValueError(f"Node {node_id} not found in analysis {analysis_id}")
                            
                    linked_analysis_ids.add(ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id)
                    
            # Check filter bindings exist in this canvas
            for f in widget.get("filters", []):
                filter_widget_id = f.get("filter_widget_id")
                if not filter_widget_id:
                    raise ValueError("Each filter binding must specify filter_widget_id")
                    
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
            {"_id": d_oid},
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
        mongo.db.audit_logs.insert_one({
            "org_id": dashboard.get("org_id"),
            "entity_type": "dashboard",
            "entity_id": d_oid,
            "action": "canvas_saved",
            "before": {"widget_count": before_widget_count},
            "after": {"widget_count": after_widget_count},
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        
        return self.get_dashboard(dashboard_id)

    def resolve_widget_data(self, dashboard, filter_state=None):
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

    def get_filter_options(self, analysis_id, node_id, column, limit=200):
        a_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
        
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

    def create_snapshot(self, dashboard_id, author_id):
        d_oid = ObjectId(dashboard_id) if ObjectId.is_valid(dashboard_id) else dashboard_id
        dashboard = mongo.db.dashboards.find_one({"_id": d_oid, "is_deleted": False})
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
            "created_by": ObjectId(author_id) if ObjectId.is_valid(author_id) else author_id,
            "is_deleted": False,
            "deleted_at": None
        }
        
        mongo.db.dashboard_snapshots.insert_one(snapshot_doc)
        return snapshot_doc

dashboard_service = DashboardService()
