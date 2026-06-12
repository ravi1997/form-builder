import os
import datetime
from celery import Celery
from bson import ObjectId
from app.extensions import mongo
from app.engines.analysis_engine import (
    execute_analysis_graph,
    GraphCycleException
)

# Get Celery app from shared config
from .celery_config import get_celery_app
celery_app = get_celery_app()

# Import task status service
from app.services.task_status_service import TaskStatusService

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

@celery_app.task(name="app.workers.analysis_tasks.run_analysis_graph_task")
def run_analysis_graph_task(analysis_run_id, task_record_id=None):
    """
    Asynchronously executes an analysis pipeline graph.
    """
    # Update task status if provided
    if task_record_id:
        TaskStatusService.update_task_status(
            task_record_id, 
            "running",
            progress=10,
            metadata={"analysis_run_id": analysis_run_id}
        )
    
    run_oid = _to_object_id(analysis_run_id)
    run_doc = mongo.db.analysis_runs.find_one({"_id": run_oid})
    if not run_doc:
        return _safe_result_payload("failed", f"Analysis run {analysis_run_id} not found.", run_id=str(run_oid))
    
    try:
        # Update status to running
        mongo.db.analysis_runs.update_one(
            {"_id": run_oid},
            {"$set": {"status": "running", "started_at": _utcnow_iso()}}
        )
        
        # Update task status progress
        if task_record_id:
            TaskStatusService.update_task_status(
                task_record_id, 
                "running",
                progress=20
            )
        
        analysis_id = run_doc.get("analysis_id")
        analysis_oid = _to_object_id(analysis_id)
        
        # Fetch the analysis document
        analysis_doc = mongo.db.analyses.find_one({"_id": analysis_oid, "is_deleted": {"$ne": True}})
        if not analysis_doc:
            raise ValueError(f"Analysis {analysis_id} not found.")
        
        graph = analysis_doc.get("graph", {})
        analysis_org_id = analysis_doc.get("org_id")
        
        # Build execution context
        context = {
            "org_id": str(analysis_org_id) if analysis_org_id else None,
            "analysis_id": str(analysis_oid),
            "run_id": str(run_oid)
        }
        
        # Execute the analysis graph
        try:
            execution_result = execute_analysis_graph(graph, context)
            
            # Update task status progress
            if task_record_id:
                TaskStatusService.update_task_status(
                    task_record_id, 
                    "running",
                    progress=50
                )
        except GraphCycleException as e:
            mongo.db.analysis_runs.update_one(
                {"_id": run_oid},
                {"$set": {
                    "status": "failed",
                    "error": str(e),
                    "completed_at": _utcnow_iso()
                }}
            )
            return _safe_result_payload("failed", str(e), run_id=str(run_oid))
        
        # Process execution results
        node_outputs = execution_result.get("node_outputs", {})
        node_errors = execution_result.get("node_errors", {})
        node_statuses = execution_result.get("node_statuses", {})
        
        # Store results for each node
        result_ids = {}
        for node_id, outputs in node_outputs.items():
            if node_statuses.get(node_id) != "success":
                continue
                
            # Determine output type based on node type
            node = next((n for n in graph.get("nodes", []) if n["id"] == node_id), None)
            if not node:
                continue
                
            node_type = node.get("type")
            output_data = outputs.get("out", {})
            
            # Determine output type
            if node_type in ["table_output"]:
                output_type = "table"
            elif node_type in ["kpi_value"]:
                output_type = "value"
            elif node_type in ["bar_chart_data", "line_chart_data", "pie_chart_data"]:
                output_type = "chart_data"
            else:
                output_type = "dataframe"
            
            # Calculate row count and column definitions
            row_count = 0
            column_definitions = []
            
            if isinstance(output_data, dict):
                if output_data.get("type") == "table":
                    row_count = output_data.get("row_count", 0)
                    column_definitions = output_data.get("columns", [])
                elif output_data.get("type") in ["kpi", "chart_data"]:
                    row_count = 1
                    column_definitions = [{"name": "value", "type": "float"}]
                elif "rows" in output_data:
                    row_count = len(output_data.get("rows", []))
                    # Auto-detect columns
                    if output_data.get("rows"):
                        first_row = output_data["rows"][0]
                        column_definitions = [
                            {"name": key, "type": type(value).__name__}
                            for key, value in first_row.items()
                        ]
            elif isinstance(output_data, list):
                row_count = len(output_data)
                if output_data:
                    first_row = output_data[0]
                    column_definitions = [
                        {"name": key, "type": type(value).__name__}
                        for key, value in first_row.items()
                        if not key.startswith("_")
                    ]
            
            # Create result document
            result_doc = {
                "run_id": run_oid,
                "analysis_id": analysis_oid,
                "node_id": node_id,
                "org_id": analysis_org_id,
                "output_type": output_type,
                "data": output_data,
                "row_count": row_count,
                "column_definitions": column_definitions,
                "created_at": _utcnow_iso()
            }
            
            # Insert result and store ID
            result = mongo.db.analysis_results.insert_one(result_doc)
            result_ids[node_id] = result.inserted_id
        
        # Determine overall run status
        all_statuses = node_statuses.values()
        error_count = sum(1 for status in all_statuses if status == "error")
        blocked_count = sum(1 for status in all_statuses if status == "blocked")
        success_count = sum(1 for status in all_statuses if status == "success")
        
        if error_count > 0:
            run_status = "failed"
            error_summary = f"{error_count} node(s) failed execution"
        elif blocked_count > 0 and success_count == 0:
            run_status = "failed"
            error_summary = "All nodes were blocked due to dependency failures"
        elif blocked_count > 0:
            run_status = "partial"
            error_summary = f"{blocked_count} node(s) were blocked, {success_count} completed successfully"
        else:
            run_status = "completed"
            error_summary = None
        
        # Update run document
        update_data = {
            "status": run_status,
            "completed_at": _utcnow_iso(),
            "node_statuses": node_statuses,
            "result_ids": result_ids
        }
        
        if error_summary:
            update_data["error_summary"] = error_summary
        
        mongo.db.analysis_runs.update_one(
            {"_id": run_oid},
            {"$set": update_data}
        )
        
        # Update analysis status
        analysis_update = {
            "status": "idle" if run_status in ["completed", "partial"] else "error",
            "updated_at": _utcnow_iso()
        }
        
        if run_status in ["completed", "partial"]:
            analysis_update["last_run_id"] = run_oid
        
        mongo.db.analyses.update_one(
            {"_id": analysis_oid},
            {"$set": analysis_update}
        )
        
        return _safe_result_payload(
            run_status,
            error_summary,
            run_id=str(run_oid),
            node_statuses=node_statuses,
            node_errors=node_errors,
            result_ids={k: str(v) for k, v in result_ids.items()}
        )
        
    except Exception as e:
        error_msg = str(e)
        mongo.db.analysis_runs.update_one(
            {"_id": run_oid},
            {"$set": {
                "status": "failed",
                "error": error_msg,
                "completed_at": _utcnow_iso()
            }}
        )
        
        # Update analysis status to error
        if analysis_oid:
            mongo.db.analyses.update_one(
                {"_id": analysis_oid},
                {"$set": {
                    "status": "error",
                    "updated_at": _utcnow_iso()
                }}
            )
        
        return _safe_result_payload("failed", error_msg, run_id=str(run_oid))

@celery_app.task(name="app.workers.analysis_tasks.schedule_analysis_execution")
def schedule_analysis_execution(analysis_id):
    """
    Scheduled task for executing analyses with scheduled execution mode.
    """
    analysis_oid = _to_object_id(analysis_id)
    
    # Fetch analysis
    analysis = mongo.db.analyses.find_one({
        "_id": analysis_oid,
        "is_deleted": {"$ne": True},
        "status": {"$ne": "running"}
    })
    
    if not analysis:
        return _safe_result_payload("skipped", f"Analysis {analysis_id} not found or not available")
    
    # Check if scheduled mode is enabled
    execution_modes = analysis.get("execution_modes", [])
    if "scheduled" not in execution_modes:
        return _safe_result_payload("skipped", f"Analysis {analysis_id} does not have scheduled execution enabled")
    
    # Create and run analysis
    run_doc = {
        "analysis_id": analysis_oid,
        "org_id": analysis.get("org_id"),
        "trigger": "scheduled",
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
    
    result = mongo.db.analysis_runs.insert_one(run_doc)
    run_id = result.inserted_id
    
    # Queue the execution task
    task = run_analysis_graph_task.delay(str(run_id))
    
    # Update run with task ID
    mongo.db.analysis_runs.update_one(
        {"_id": run_id},
        {"$set": {"celery_task_id": task.id}}
    )
    
    return _safe_result_payload("queued", None, run_id=str(run_id), task_id=task.id)
        except ValueError as e:
            mongo.db.analysis_runs.update_one(
                {"_id": run_oid},
                {"$set": {
                    "status": "failed",
                    "error": str(e),
                    "updated_at": _utcnow_iso()
                }}
            )
            return _safe_result_payload("failed", str(e), run_id=str(run_oid))

        node_outputs = {} # node_id -> {port: data}
        node_statuses = {} # node_id -> status (success, error, blocked)
        node_errors = {}
        
        for node_id in sorted_node_ids:
            node = node_map.get(node_id)
            if not node:
                # If node is in dependencies but not in nodes list (external)
                node_statuses[node_id] = "error"
                # Cache node result
                mongo.db.analysis_results.update_one(
                    {"analysis_run_id": run_oid, "node_id": node_id},
                    {"$set": {
                        "status": "error",
                        "error": "Node definition not found in graph.",
                        "updated_at": _utcnow_iso()
                    }},
                    upsert=True
                )
                continue
                
            if node.get("is_disabled", False):
                node_statuses[node_id] = "blocked"
                mongo.db.analysis_results.update_one(
                    {"analysis_run_id": run_oid, "node_id": node_id},
                    {"$set": {
                        "status": "blocked",
                        "error": "Node is disabled.",
                        "updated_at": _utcnow_iso()
                    }},
                    upsert=True
                )
                continue
            
            # Check if any parent node is in error or blocked
            parents = graph_dict.get(node_id, [])
            parent_failed_or_blocked = False
            for p in parents:
                if node_statuses.get(p) in ["error", "blocked"]:
                    parent_failed_or_blocked = True
                    break
                    
            if parent_failed_or_blocked:
                node_statuses[node_id] = "blocked"
                mongo.db.analysis_results.update_one(
                    {"analysis_run_id": run_oid, "node_id": node_id},
                    {"$set": {
                        "status": "blocked",
                        "error": "Dependency failed or was blocked.",
                        "updated_at": _utcnow_iso()
                    }},
                    upsert=True
                )
                continue
                
            # Execute node logic
            try:
                node_type = node.get("type")
                properties = node.get("properties", {})
                
                # Resolve inputs from edges
                inputs = {}
                for edge in edges:
                    if edge["to_node"] == node_id:
                        from_node = edge["from_node"]
                        from_port = edge["from_port"]
                        to_port = edge["to_port"]
                        # Get output from parent node
                        parent_output = node_outputs.get(from_node, {}).get(from_port)
                        inputs[to_port] = parent_output
                
                output_data = {}
                
                if node_type == "form_source":
                    form_id = properties.get("form_id")
                    include_drafts = properties.get("include_drafts", False)
                    if not form_id:
                        raise ValueError("form_id is required for form_source")
                    
                    form_oid = _to_object_id(form_id)
                    form_query = {"_id": form_oid, "is_deleted": {"$ne": True}}
                    if analysis_org_id is not None:
                        form_query["org_id"] = analysis_org_id
                    # Verify form exists in database and belongs to the same tenant when possible.
                    if not mongo.db.forms.find_one(form_query):
                        raise ValueError(f"Form {form_id} does not exist.")
                        
                    response_query = {"form_id": form_oid}
                    if analysis_org_id is not None:
                        response_query["org_id"] = analysis_org_id
                    docs = list(mongo.db.form_responses.find(response_query))
                    if include_drafts:
                        draft_query = {"form_id": form_oid}
                        if analysis_org_id is not None:
                            draft_query["org_id"] = analysis_org_id
                        drafts = list(mongo.db.response_drafts.find(draft_query))
                        docs.extend(drafts)
                        
                    records = []
                    for doc in docs:
                        rec = {"_id": str(doc["_id"])}
                        if "values" in doc:
                            rec.update(doc["values"])
                        elif "answers" in doc:
                            rec.update(doc["answers"])
                        else:
                            for k, v in doc.items():
                                if k not in ["_id", "form_id"]:
                                    rec[k] = str(v) if isinstance(v, ObjectId) else v
                        records.append(rec)
                    output_data["out"] = records
                    
                elif node_type == "csv_source":
                    file_path = properties.get("file_path")
                    if not file_path:
                        raise ValueError("file_path is required for csv_source")
                    df = pd.read_csv(file_path)
                    output_data["out"] = to_records(df)
                    
                elif node_type == "pandas_filter":
                    query_str = properties.get("query")
                    in_data = inputs.get("in", [])
                    if not query_str:
                        output_data["out"] = in_data
                    else:
                        output_data["out"] = evaluate_filter(in_data, query_str)
                        
                elif node_type == "pandas_column_select":
                    cols = properties.get("columns", [])
                    in_data = inputs.get("in", [])
                    output_data["out"] = evaluate_projection(in_data, cols)
                    
                elif node_type == "dataframe_join":
                    left_data = inputs.get("left", [])
                    right_data = inputs.get("right", [])
                    left_on = properties.get("left_on")
                    right_on = properties.get("right_on")
                    how = properties.get("how", "inner")
                    
                    df_left = load_data(left_data)
                    df_right = load_data(right_data)
                    
                    if df_left.empty or df_right.empty:
                        output_data["out"] = []
                    else:
                        merged_df = df_left.merge(df_right, left_on=left_on, right_on=right_on, how=how)
                        output_data["out"] = to_records(merged_df)
                        
                elif node_type == "group_by_aggregation":
                    in_data = inputs.get("in", [])
                    keys = properties.get("keys", [])
                    agg_col = properties.get("aggregation_column")
                    func = properties.get("function", "count")
                    
                    if not keys or not agg_col:
                        output_data["out"] = in_data
                    else:
                        output_data["out"] = evaluate_aggregation(in_data, keys, {agg_col: func})
                        
                elif node_type == "scalar_aggregator":
                    in_data = inputs.get("in", [])
                    col = properties.get("column")
                    func = properties.get("function", "count")
                    
                    if not col:
                        output_data["out"] = None
                    else:
                        df = load_data(in_data)
                        if df.empty:
                            output_data["out"] = 0 if func == "count" else None
                        else:
                            val = df[col].agg(func)
                            if pd.isna(val):
                                output_data["out"] = None
                            elif isinstance(val, (int, float, str)):
                                output_data["out"] = val
                            else:
                                output_data["out"] = float(val) if isinstance(val, (float, int)) else str(val)
                                
                elif node_type == "chart_formatter":
                    in_data = inputs.get("in", [])
                    label_col = properties.get("label_column")
                    val_col = properties.get("value_column")
                    chart_type = properties.get("chart_type", "bar")
                    
                    df = load_data(in_data)
                    if df.empty or not label_col or not val_col:
                        output_data["out"] = {"chart_type": chart_type, "labels": [], "datasets": []}
                    else:
                        output_data["out"] = {
                            "chart_type": chart_type,
                            "labels": df[label_col].tolist(),
                            "datasets": [
                                {
                                    "label": val_col,
                                    "data": df[val_col].tolist()
                                }
                            ]
                        }
                        
                elif node_type == "table_generator":
                    in_data = inputs.get("in", [])
                    page_size = properties.get("page_size", 10)
                    cols = properties.get("columns", [])
                    
                    output_data["out"] = {
                        "columns": cols,
                        "rows": in_data,
                        "page_size": page_size
                    }
                else:
                    raise ValueError(f"Unknown node type: {node_type}")
                    
                node_outputs[node_id] = output_data
                node_statuses[node_id] = "success"
                
                # Cache results
                mongo.db.analysis_results.update_one(
                    {"analysis_run_id": run_oid, "node_id": node_id},
                    {"$set": {
                        "status": "success",
                        "data": output_data,
                        "updated_at": _utcnow_iso()
                    }},
                    upsert=True
                )
                
            except Exception as e:
                node_statuses[node_id] = "error"
                node_errors[node_id] = str(e)
                mongo.db.analysis_results.update_one(
                    {"analysis_run_id": run_oid, "node_id": node_id},
                    {"$set": {
                        "status": "error",
                        "error": str(e),
                        "updated_at": _utcnow_iso()
                    }},
                    upsert=True
                )
                
        # Determine overall run status
        all_statuses = node_statuses.values()
        if any(s == "error" for s in all_statuses):
            run_status = "failed"
            run_error = "One or more nodes failed execution."
        else:
            run_status = "completed"
            run_error = None
            
        mongo.db.analysis_runs.update_one(
            {"_id": run_oid},
            {"$set": {
                "status": run_status,
                "error": run_error,
                "updated_at": _utcnow_iso(),
                "node_statuses": node_statuses,
                "node_errors": node_errors
            }}
        )
        
        # Update final task status
        if task_record_id:
            TaskStatusService.update_task_status(
                task_record_id,
                "completed" if run_status == "completed" else "failed",
                progress=100,
                error=run_error,
                result={
                    "run_status": run_status,
                    "run_id": str(run_oid),
                    "node_statuses": node_statuses,
                    "node_errors": node_errors
                }
            )
        
        return _safe_result_payload(
            run_status,
            run_error,
            run_id=str(run_oid),
            node_statuses=node_statuses,
            node_errors=node_errors
        )
        
    except Exception as e:
        mongo.db.analysis_runs.update_one(
            {"_id": run_oid},
            {"$set": {
                "status": "failed",
                "error": str(e),
                "completed_at": _utcnow_iso()
            }}
        )
        
        # Update task status on error
        if task_record_id:
            TaskStatusService.update_task_status(
                task_record_id,
                "failed",
                error=str(e)
            )
        
        return _safe_result_payload("failed", str(e), run_id=str(run_oid))


@celery_app.task(name="app.workers.analysis_tasks.run_scheduled_analyses_task")
def run_scheduled_analyses_task():
    """
    Run all analyses that are scheduled for execution.
    """
    try:
        # Find analyses with scheduled execution mode
        scheduled_analyses = list(mongo.db.analyses.find({
            "execution_modes": "scheduled",
            "schedule": {"$exists": True, "$ne": None},
            "status": "idle",
            "is_deleted": {"$ne": True}
        }))
        
        triggered_count = 0
        
        for analysis in scheduled_analyses:
            # Check if analysis should run now (simplified cron check)
            should_run = _should_run_scheduled_analysis(analysis)
            
            if should_run:
                # Create analysis run
                run_data = {
                    "analysis_id": analysis["_id"],
                    "org_id": analysis.get("org_id"),
                    "trigger": "scheduled",
                    "triggered_by": None,  # System-triggered
                    "status": "queued",
                    "created_at": _utcnow_iso()
                }
                
                result = mongo.db.analysis_runs.insert_one(run_data)
                
                # Queue the analysis execution
                run_analysis_graph_task.delay(str(result.inserted_id))
                triggered_count += 1
        
        return _safe_result_payload(
            "completed",
            triggered_count=triggered_count
        )
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))


def _should_run_scheduled_analysis(analysis: Dict) -> bool:
    """
    Check if a scheduled analysis should run now.
    This is a simplified implementation - in production, you'd use a proper cron parser.
    """
    schedule = analysis.get("schedule")
    if not schedule:
        return False
    
    # Get last run time
    last_run_id = analysis.get("last_run_id")
    if last_run_id:
        last_run = mongo.db.analysis_runs.find_one({"_id": last_run_id})
        if last_run:
            last_run_time = last_run.get("created_at")
            # For now, just run if it's been more than 5 minutes since last run
            # In production, this would use the actual cron schedule
            if last_run_time:
                last_run_dt = datetime.datetime.fromisoformat(last_run_time.replace('Z', '+00:00'))
                now = datetime.datetime.utcnow()
                delta = now - last_run_dt
                return delta.total_seconds() >= 300  # 5 minutes
    
    return True
