import os
import datetime
from celery import Celery
from bson import ObjectId
from app.extensions import mongo
from app.services.dashboard_service import dashboard_service

# Setup Celery
redis_uri = os.environ.get("REDIS_URI", "redis://localhost:6379/0")
celery_app = Celery("dashboard_tasks", broker=redis_uri, backend=redis_uri)

def _utcnow_iso():
    return datetime.datetime.utcnow().isoformat()

def _to_object_id(value):
    if isinstance(value, ObjectId):
        return value
    if ObjectId.is_valid(str(value)):
        return ObjectId(str(value))
    raise ValueError(f"Invalid ObjectId: {value}")

def _safe_result_payload(status, error=None, **extra):
    payload = {"status": status, "error": error}
    payload.update(extra)
    return payload


@celery_app.task(name="app.workers.dashboard_tasks.refresh_dashboard_data")
def refresh_dashboard_data_task(dashboard_id, context=None):
    """
    Background task to refresh dashboard widget data.
    Triggers analysis runs if needed and updates widget data cache.
    """
    try:
        dashboard_oid = _to_object_id(dashboard_id)
        dashboard = mongo.db.dashboards.find_one({"_id": dashboard_oid, "is_deleted": False})
        if not dashboard:
            return _safe_result_payload("failed", f"Dashboard {dashboard_id} not found")
        
        # Get all widgets with data bindings
        canvas = dashboard.get("canvas", {})
        widgets = canvas.get("widgets", [])
        
        # Find analyses that need to be run
        analysis_ids_to_run = set()
        for widget in widgets:
            binding = widget.get("data_binding")
            if binding and binding.get("analysis_id"):
                analysis_id = binding["analysis_id"]
                analysis_ids_to_run.add(_to_object_id(analysis_id))
        
        # Trigger analysis runs for each analysis
        run_results = {}
        for analysis_id in analysis_ids_to_run:
            # Create a new analysis run
            run_doc = {
                "analysis_id": analysis_id,
                "org_id": dashboard.get("org_id"),
                "trigger": "dashboard_refresh",
                "triggered_by": None,  # System trigger
                "status": "queued",
                "started_at": None,
                "completed_at": None,
                "celery_task_id": None,
                "node_statuses": {},
                "error_summary": None,
                "result_ids": {},
                "created_at": _utcnow_iso()
            }
            
            # Insert run document
            result = mongo.db.analysis_runs.insert_one(run_doc)
            run_id = result.inserted_id
            
            # Trigger analysis run task (assuming it exists in analysis_tasks)
            try:
                from app.workers.analysis_tasks import run_analysis_graph_task
                task = run_analysis_graph_task.delay(str(run_id))
                
                # Update run with task ID
                mongo.db.analysis_runs.update_one(
                    {"_id": run_id},
                    {"$set": {"celery_task_id": task.id, "status": "queued"}}
                )
                
                run_results[str(analysis_id)] = {
                    "run_id": str(run_id),
                    "task_id": task.id,
                    "status": "queued"
                }
            except ImportError:
                # If analysis_tasks not available, mark as failed
                mongo.db.analysis_runs.update_one(
                    {"_id": run_id},
                    {"$set": {"status": "failed", "error_summary": "Analysis engine not available"}}
                )
                run_results[str(analysis_id)] = {
                    "run_id": str(run_id),
                    "status": "failed",
                    "error": "Analysis engine not available"
                }
        
        return _safe_result_payload(
            "success",
            "Dashboard refresh initiated",
            dashboard_id=dashboard_id,
            analyses_triggered=len(analysis_ids_to_run),
            run_results=run_results
        )
        
    except Exception as e:
        return _safe_result_payload("failed", f"Dashboard refresh failed: {str(e)}")


@celery_app.task(name="app.workers.dashboard_tasks.cleanup_old_snapshots")
def cleanup_old_snapshots_task(retention_days=30):
    """
    Background task to clean up old dashboard snapshots.
    Removes snapshots older than retention_days.
    """
    try:
        cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=retention_days)
        
        # Find and mark old snapshots as deleted
        result = mongo.db.dashboard_snapshots.update_many(
            {
                "created_at": {"$lt": cutoff_date},
                "is_deleted": False
            },
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": _utcnow_iso()
                }
            }
        )
        
        return _safe_result_payload(
            "success",
            f"Cleaned up {result.modified_count} old snapshots",
            retention_days=retention_days,
            cutoff_date=cutoff_date.isoformat(),
            snapshots_deleted=result.modified_count
        )
        
    except Exception as e:
        return _safe_result_payload("failed", f"Snapshot cleanup failed: {str(e)}")


@celery_app.task(name="app.workers.dashboard_tasks.generate_dashboard_snapshot")
def generate_dashboard_snapshot_task(dashboard_id, author_id, context=None):
    """
    Background task to generate a dashboard snapshot.
    Captures current widget data and saves as snapshot.
    """
    try:
        dashboard_oid = _to_object_id(dashboard_id)
        dashboard = mongo.db.dashboards.find_one({"_id": dashboard_oid, "is_deleted": False})
        if not dashboard:
            return _safe_result_payload("failed", f"Dashboard {dashboard_id} not found")
        
        # Use dashboard service to create snapshot
        snapshot = dashboard_service.create_snapshot(dashboard_id, author_id, context)
        if not snapshot:
            return _safe_result_payload("failed", f"Failed to create snapshot for dashboard {dashboard_id}")
        
        return _safe_result_payload(
            "success",
            "Dashboard snapshot created",
            dashboard_id=dashboard_id,
            snapshot_id=str(snapshot["_id"]),
            created_at=snapshot["created_at"]
        )
        
    except Exception as e:
        return _safe_result_payload("failed", f"Snapshot generation failed: {str(e)}")


@celery_app.task(name="app.workers.dashboard_tasks.update_dashboard_access_stats")
def update_dashboard_access_stats_task(dashboard_id, access_type="view", user_id=None):
    """
    Background task to update dashboard access statistics.
    Tracks view counts and last access times.
    """
    try:
        dashboard_oid = _to_object_id(dashboard_id)
        
        # Update dashboard access stats
        update_data = {
            "$set": {
                "last_accessed_at": _utcnow_iso(),
                f"stats.{access_type}_count": {"$ifNull": [f"$stats.{access_type}_count", 0]} + 1
            },
            "$inc": {"stats.total_access_count": 1}
        }
        
        if user_id:
            update_data["$set"]["stats.last_accessed_by"] = _to_object_id(user_id)
        
        result = mongo.db.dashboards.update_one(
            {"_id": dashboard_oid},
            update_data
        )
        
        if result.matched_count == 0:
            return _safe_result_payload("failed", f"Dashboard {dashboard_id} not found")
        
        return _safe_result_payload(
            "success",
            "Dashboard access stats updated",
            dashboard_id=dashboard_id,
            access_type=access_type
        )
        
    except Exception as e:
        return _safe_result_payload("failed", f"Access stats update failed: {str(e)}")


@celery_app.task(name="app.workers.dashboard_tasks.cache_filter_options")
def cache_filter_options_task(analysis_id, node_id, column, limit=200):
    """
    Background task to cache filter options for a dashboard widget.
    Pre-computes distinct values for filter dropdowns.
    """
    try:
        analysis_oid = _to_object_id(analysis_id)
        
        # Get latest completed analysis run
        run = mongo.db.analysis_runs.find_one(
            {"analysis_id": analysis_oid, "status": "completed"},
            sort=[("created_at", -1)]
        )
        
        if not run:
            return _safe_result_payload("failed", f"No completed runs found for analysis {analysis_id}")
        
        run_id = run["_id"]
        
        # Get analysis result
        result = mongo.db.analysis_results.find_one({
            "analysis_run_id": run_id,
            "node_id": node_id
        })
        
        if not result or result.get("status") != "success":
            return _safe_result_payload("failed", f"No successful result found for node {node_id}")
        
        # Extract distinct values
        raw_data = result.get("data", {})
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
        
        # Cache in Redis (if available)
        from app.extensions import redis_client
        if redis_client:
            try:
                cache_key = f"filter_opts:{analysis_id}:{node_id}:{column}:{run_id}"
                cache_payload = {
                    "column": column,
                    "values": limited_vals,
                    "total_distinct": len(sorted_vals)
                }
                import json
                redis_client.setex(cache_key, 300, json.dumps(cache_payload))  # 5 minutes TTL
            except Exception:
                pass  # Redis not available, continue without caching
        
        return _safe_result_payload(
            "success",
            "Filter options cached",
            analysis_id=analysis_id,
            node_id=node_id,
            column=column,
            distinct_values_count=len(sorted_vals),
            cached_values_count=len(limited_vals)
        )
        
    except Exception as e:
        return _safe_result_payload("failed", f"Filter options caching failed: {str(e)}")


@celery_app.task(name="app.workers.dashboard_tasks.validate_dashboard_integrity")
def validate_dashboard_integrity_task(dashboard_id):
    """
    Background task to validate dashboard integrity.
    Checks for broken analysis bindings, invalid widgets, etc.
    """
    try:
        dashboard_oid = _to_object_id(dashboard_id)
        dashboard = mongo.db.dashboards.find_one({"_id": dashboard_oid, "is_deleted": False})
        if not dashboard:
            return _safe_result_payload("failed", f"Dashboard {dashboard_id} not found")
        
        issues = []
        warnings = []
        
        canvas = dashboard.get("canvas", {})
        widgets = canvas.get("widgets", [])
        
        # Check each widget
        for widget in widgets:
            widget_id = widget.get("id")
            widget_type = widget.get("type")
            
            # Check widget ID validity
            try:
                import uuid
                uuid.UUID(str(widget_id))
            except ValueError:
                issues.append(f"Widget {widget_id} has invalid UUID")
            
            # Check widget type
            valid_types = {
                "kpi_card", "bar_chart", "line_chart", "pie_chart", "data_table",
                "text_label", "image_widget", "filter_widget", "divider_widget"
            }
            if widget_type not in valid_types:
                issues.append(f"Widget {widget_id} has invalid type: {widget_type}")
            
            # Check data binding
            binding = widget.get("data_binding")
            if binding:
                analysis_id = binding.get("analysis_id")
                node_id = binding.get("node_id")
                
                if not analysis_id or not node_id:
                    issues.append(f"Widget {widget_id} has incomplete data binding")
                else:
                    # Check if analysis exists
                    analysis = mongo.db.analyses.find_one({
                        "_id": _to_object_id(analysis_id),
                        "is_deleted": False
                    })
                    if not analysis:
                        issues.append(f"Widget {widget_id} references non-existent analysis: {analysis_id}")
                    else:
                        # Check if node exists in analysis
                        nodes = analysis.get("graph", {}).get("nodes", [])
                        if not any(n.get("id") == node_id for n in nodes):
                            issues.append(f"Widget {widget_id} references non-existent node: {node_id}")
            
            # Check filter bindings
            for filter_binding in widget.get("filters", []):
                filter_widget_id = filter_binding.get("filter_widget_id")
                if not filter_widget_id:
                    issues.append(f"Widget {widget_id} has incomplete filter binding")
                else:
                    # Check if filter widget exists
                    filter_widget = next((w for w in widgets if w.get("id") == filter_widget_id), None)
                    if not filter_widget:
                        issues.append(f"Widget {widget_id} references non-existent filter widget: {filter_widget_id}")
                    elif filter_widget.get("type") != "filter_widget":
                        issues.append(f"Widget {widget_id} references non-filter widget as filter: {filter_widget_id}")
        
        # Update dashboard with validation status
        validation_result = {
            "validated_at": _utcnow_iso(),
            "issues_count": len(issues),
            "warnings_count": len(warnings),
            "issues": issues,
            "warnings": warnings,
            "is_valid": len(issues) == 0
        }
        
        mongo.db.dashboards.update_one(
            {"_id": dashboard_oid},
            {"$set": {"validation": validation_result}}
        )
        
        return _safe_result_payload(
            "success",
            "Dashboard validation completed",
            dashboard_id=dashboard_id,
            **validation_result
        )
        
    except Exception as e:
        return _safe_result_payload("failed", f"Dashboard validation failed: {str(e)}")