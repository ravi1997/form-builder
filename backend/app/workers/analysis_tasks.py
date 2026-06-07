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

@celery_app.task(name="app.workers.analysis_tasks.run_analysis_graph_task")
def run_analysis_graph_task(analysis_run_id):
    """
    Asynchronously executes an analysis pipeline graph.
    """
    run_oid = ObjectId(analysis_run_id) if ObjectId.is_valid(analysis_run_id) else analysis_run_id
    
    # Update status to running
    mongo.db.analysis_runs.update_one(
        {"_id": run_oid},
        {"$set": {"status": "running", "updated_at": datetime.datetime.utcnow().isoformat()}}
    )
    
    try:
        # Fetch the run document
        run_doc = mongo.db.analysis_runs.find_one({"_id": run_oid})
        if not run_doc:
            raise ValueError(f"Analysis run {analysis_run_id} not found.")
            
        analysis_id = run_doc.get("analysis_id")
        analysis_oid = ObjectId(analysis_id) if ObjectId.is_valid(analysis_id) else analysis_id
        
        # Fetch the analysis document
        analysis_doc = mongo.db.analyses.find_one({"_id": analysis_oid})
        if not analysis_doc:
            raise ValueError(f"Analysis {analysis_id} not found.")
            
        graph = analysis_doc.get("graph", {})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        
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
                    "updated_at": datetime.datetime.utcnow().isoformat()
                }}
            )
            return {"status": "failed", "error": str(e)}

        node_outputs = {} # node_id -> {port: data}
        node_statuses = {} # node_id -> status (success, error, blocked)
        
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
                        "updated_at": datetime.datetime.utcnow().isoformat()
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
                        "updated_at": datetime.datetime.utcnow().isoformat()
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
                        "updated_at": datetime.datetime.utcnow().isoformat()
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
                    
                    form_oid = ObjectId(form_id) if ObjectId.is_valid(form_id) else form_id
                    docs = list(mongo.db.form_responses.find({"form_id": form_oid}))
                    if include_drafts:
                        drafts = list(mongo.db.response_drafts.find({"form_id": form_oid}))
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
                        "updated_at": datetime.datetime.utcnow().isoformat()
                    }},
                    upsert=True
                )
                
            except Exception as e:
                node_statuses[node_id] = "error"
                mongo.db.analysis_results.update_one(
                    {"analysis_run_id": run_oid, "node_id": node_id},
                    {"$set": {
                        "status": "error",
                        "error": str(e),
                        "updated_at": datetime.datetime.utcnow().isoformat()
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
                "updated_at": datetime.datetime.utcnow().isoformat()
            }}
        )
        return {"status": run_status, "error": run_error}
        
    except Exception as e:
        mongo.db.analysis_runs.update_one(
            {"_id": run_oid},
            {"$set": {
                "status": "failed",
                "error": str(e),
                "updated_at": datetime.datetime.utcnow().isoformat()
            }}
        )
        return {"status": "failed", "error": str(e)}
