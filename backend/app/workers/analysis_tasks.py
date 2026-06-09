import os
import datetime
import pandas as pd
from celery import Celery
from bson import ObjectId
from app.extensions import mongo
from app.engines.analysis_engine import (
    validate_and_sort_dag,
    GraphCycleException,
    load_data,
    to_records,
    evaluate_filter,
    evaluate_aggregation,
    evaluate_projection,
    evaluate_formula
)

# Setup Celery
redis_uri = os.environ.get("REDIS_URI", "redis://localhost:6379/0")
celery_app = Celery("tasks", broker=redis_uri, backend=redis_uri)

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
def run_analysis_graph_task(analysis_run_id):
    """
    Asynchronously executes an analysis pipeline graph.
    """
    run_oid = _to_object_id(analysis_run_id)
    run_doc = mongo.db.analysis_runs.find_one({"_id": run_oid})
    if not run_doc:
        return _safe_result_payload("failed", f"Analysis run {analysis_run_id} not found.", run_id=str(run_oid))
    
    try:
        # Update status to running after the run exists.
        mongo.db.analysis_runs.update_one(
            {"_id": run_oid},
            {"$set": {"status": "running", "updated_at": _utcnow_iso()}}
        )
            
        analysis_id = run_doc.get("analysis_id")
        analysis_oid = _to_object_id(analysis_id)
        
        # Fetch the analysis document
        analysis_doc = mongo.db.analyses.find_one({"_id": analysis_oid, "is_deleted": {"$ne": True}})
        if not analysis_doc:
            raise ValueError(f"Analysis {analysis_id} not found.")
            
        graph = analysis_doc.get("graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        analysis_org_id = analysis_doc.get("org_id")
        
        # Build networkx graph for sorting and validation
        node_map = {n["id"]: n for n in nodes}
        
        # Build graph dictionary for validate_and_sort_dag
        graph_dict = {}
        for node in nodes:
            node_id = node["id"]
            # Find dependencies
            deps = []
            for edge in edges:
                if edge["to_node"] == node_id:
                    deps.append(edge["from_node"])
            graph_dict[node_id] = deps
            
        # Validate and sort
        try:
            sorted_node_ids = validate_and_sort_dag(graph_dict)
        except GraphCycleException as e:
            mongo.db.analysis_runs.update_one(
                {"_id": run_oid},
                {"$set": {
                    "status": "failed",
                    "error": str(e),
                    "updated_at": _utcnow_iso()
                }}
            )
            return _safe_result_payload("failed", str(e), run_id=str(run_oid))
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
                "updated_at": _utcnow_iso()
            }}
        )
        return _safe_result_payload("failed", str(e), run_id=str(run_oid))
