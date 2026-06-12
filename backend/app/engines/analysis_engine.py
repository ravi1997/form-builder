import json
import networkx as nx
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from bson import ObjectId
import re
import requests
from io import StringIO
import csv

class GraphCycleException(Exception):
    """Exception raised when a cycle is detected in a graph."""
    pass

class NodeExecutionError(Exception):
    """Exception raised during node execution."""
    pass

def validate_graph(graph: Dict) -> bool:
    """
    Validate the analysis graph structure.
    
    Args:
        graph: Dictionary containing nodes and edges
        
    Returns:
        bool: True if valid
        
    Raises:
        ValueError: If graph structure is invalid
    """
    if not isinstance(graph, dict):
        raise ValueError("Graph must be a dictionary")
    
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    
    if not isinstance(nodes, list):
        raise ValueError("Graph nodes must be a list")
    
    if not isinstance(edges, list):
        raise ValueError("Graph edges must be a list")
    
    # Validate nodes
    node_ids = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("Each node must be a dictionary")
        
        if "id" not in node:
            raise ValueError("Each node must have an id")
        
        node_id = node["id"]
        if not isinstance(node_id, str):
            raise ValueError("Node ID must be a string")
        
        if node_id in node_ids:
            raise ValueError(f"Duplicate node ID: {node_id}")
        node_ids.add(node_id)
        
        # Validate node type
        if "type" not in node:
            raise ValueError(f"Node {node_id} must have a type")
        
        # Validate node position
        position = node.get("position", {})
        if not isinstance(position, dict):
            raise ValueError(f"Node {node_id} position must be a dictionary")
        
        # Validate node size
        size = node.get("size", {})
        if not isinstance(size, dict):
            raise ValueError(f"Node {node_id} size must be a dictionary")
    
    # Validate edges
    edge_ids = set()
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("Each edge must be a dictionary")
        
        if "id" not in edge:
            edge["id"] = str(ObjectId())
        
        edge_id = edge["id"]
        if edge_id in edge_ids:
            raise ValueError(f"Duplicate edge ID: {edge_id}")
        edge_ids.add(edge_id)
        
        from_node = edge.get("from_node")
        to_node = edge.get("to_node")
        
        if not from_node or not to_node:
            raise ValueError("Edge must have from_node and to_node")
        
        if from_node not in node_ids:
            raise ValueError(f"Edge from_node {from_node} does not exist")
        
        if to_node not in node_ids:
            raise ValueError(f"Edge to_node {to_node} does not exist")
    
    # Validate DAG (no cycles)
    try:
        validate_and_sort_dag(graph)
    except GraphCycleException as e:
        raise ValueError(f"Graph contains cycles: {str(e)}")
    
    return True

def _normalize_dependencies(value):
    """Return a dependency list from the supported graph input shapes."""
    if value is None:
        return []
    if isinstance(value, dict):
        dependencies = value.get("dependencies", [])
        if dependencies is None:
            return []
        if isinstance(dependencies, (str, bytes)):
            raise ValueError("dependencies must be a list of node ids")
        return list(dependencies)
    if isinstance(value, (str, bytes)):
        raise ValueError("dependencies must be a list of node ids")
    return list(value)

def _build_dag_from_schema(graph):
    """Build a DiGraph from the documented analysis graph schema."""
    dag = nx.DiGraph()
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    for node in nodes:
        node_id = node.get("id")
        if not node_id:
            raise ValueError("Each node must include an id")
        dag.add_node(node_id)

    for edge in edges:
        from_node = edge.get("from_node")
        to_node = edge.get("to_node")
        if not from_node or not to_node:
            raise ValueError("Each edge must include from_node and to_node")
        dag.add_edge(from_node, to_node)

    return dag

def validate_and_sort_dag(graph):
    """
    Validates that a graph has no cycles and returns its nodes in topological order.
    
    The graph can be represented as:
    1. A dictionary where keys are node IDs and values are dictionaries with a 'dependencies' list.
       E.g., {"node_1": {"dependencies": []}, "node_2": {"dependencies": ["node_1"]}}
    2. A dictionary mapping node IDs directly to a list of dependency node IDs.
       E.g., {"node_1": [], "node_2": ["node_1"]}
    3. A networkx.DiGraph object.
    
    Raises GraphCycleException if the graph contains cyclic loops.
    Returns a list of node IDs in topological execution order.
    """
    if isinstance(graph, nx.DiGraph):
        dg = graph
    elif isinstance(graph, dict) and "nodes" in graph and "edges" in graph:
        dg = _build_dag_from_schema(graph)
    else:
        dg = nx.DiGraph()
        for node_id, value in graph.items():
            dg.add_node(node_id)
            for dep in _normalize_dependencies(value):
                # Add edge from dependency to node_id, meaning dependency must execute first.
                dg.add_edge(dep, node_id)

    if not nx.is_directed_acyclic_graph(dg):
        try:
            cycle = nx.find_cycle(dg)
            cycle_str = " -> ".join([f"{u}->{v}" for u, v in cycle])
            raise GraphCycleException(f"Graph contains a cycle: {cycle_str}")
        except GraphCycleException:
            raise
        except Exception:
            raise GraphCycleException("Graph contains one or more cyclic loops.")

    return list(nx.topological_sort(dg))

# --- Data Processing Helpers ---

def load_data(data) -> pd.DataFrame:
    """Converts input data (DataFrame, list of dicts, dict, or JSON string) to a Pandas DataFrame."""
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, str):
        data = json.loads(data)
    if isinstance(data, list):
        return pd.DataFrame(data)
    if isinstance(data, dict):
        return pd.DataFrame([data])
    return pd.DataFrame()

def to_records(df: pd.DataFrame) -> list:
    """Converts a Pandas DataFrame back to a list of dictionaries (records)."""
    if df.empty:
        return []
    return df.to_dict(orient="records")

def evaluate_filter(data, query_string: str) -> list:
    """
    Filters records based on a Pandas query string.
    E.g., query_string="age > 30 and status == 'active'"
    """
    df = load_data(data)
    if df.empty:
        return []
    try:
        filtered_df = df.query(query_string)
        return to_records(filtered_df)
    except Exception as e:
        # Fallback to python evaluation if query fails or for custom behavior
        raise ValueError(f"Error evaluating filter query '{query_string}': {e}")

def evaluate_aggregation(data, groupby_cols: list, aggregations: dict) -> list:
    """
    Groups data and applies aggregation functions.
    E.g., groupby_cols=["department"], aggregations={"salary": "mean", "age": "max"}
    """
    df = load_data(data)
    if df.empty:
        return []
    try:
        grouped_df = df.groupby(groupby_cols).agg(aggregations).reset_index()
        return to_records(grouped_df)
    except Exception as e:
        raise ValueError(f"Error evaluating aggregation: {e}")

def evaluate_projection(data, columns: list) -> list:
    """
    Selects specific columns from the data.
    E.g., columns=["id", "name"]
    """
    df = load_data(data)
    if df.empty:
        return []
    # Only select columns that exist in the dataframe to avoid errors
    existing_cols = [col for col in columns if col in df.columns]
    projected_df = df[existing_cols]
    return to_records(projected_df)

def evaluate_formula(data, target_col: str, formula: str) -> list:
    """
    Evaluates a formula to create or update a column.
    E.g., target_col="total", formula="quantity * unit_price"
    """
    df = load_data(data)
    if df.empty:
        return []
    try:
        # Use pandas eval to calculate the new/updated column
        df[target_col] = df.eval(formula)
        return to_records(df)
    except Exception as e:
        raise ValueError(f"Error evaluating formula '{formula}': {e}")

# --- Node Execution Functions ---

def execute_form_responses_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute form_responses data source node."""
    properties = node.get("properties", {})
    form_id = properties.get("form_id")
    include_drafts = properties.get("include_drafts", False)
    
    if not form_id:
        raise ValueError("form_id is required for form_responses node")
    
    from app.extensions import mongo
    
    form_oid = ObjectId(form_id)
    form_query = {"_id": form_oid, "is_deleted": {"$ne": True}}
    if context.get("org_id"):
        form_query["org_id"] = ObjectId(context["org_id"])
    
    form = mongo.db.forms.find_one(form_query)
    if not form:
        raise ValueError(f"Form {form_id} does not exist")
    
    # Get responses
    response_query = {"form_id": form_oid}
    if context.get("org_id"):
        response_query["org_id"] = ObjectId(context["org_id"])
    
    docs = list(mongo.db.form_responses.find(response_query))
    
    if include_drafts:
        draft_query = {"form_id": form_oid}
        if context.get("org_id"):
            draft_query["org_id"] = ObjectId(context["org_id"])
        drafts = list(mongo.db.response_drafts.find(draft_query))
        docs.extend(drafts)
    
    records = []
    for doc in docs:
        rec = {"_id": str(doc["_id"])}
        if "answers" in doc:
            rec.update(doc["answers"])
        elif "values" in doc:
            rec.update(doc["values"])
        else:
            for k, v in doc.items():
                if k not in ["_id", "form_id", "org_id", "project_id", "created_at", "updated_at"]:
                    rec[k] = str(v) if isinstance(v, ObjectId) else v
        records.append(rec)
    
    return {"out": records}

def execute_csv_upload_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute csv_upload data source node."""
    properties = node.get("properties", {})
    file_path = properties.get("file_path")
    
    if not file_path:
        raise ValueError("file_path is required for csv_upload node")
    
    try:
        df = pd.read_csv(file_path)
        return {"out": to_records(df)}
    except Exception as e:
        raise ValueError(f"Error reading CSV file: {str(e)}")

def execute_manual_data_entry_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute manual_data_entry data source node."""
    properties = node.get("properties", {})
    data = properties.get("data", [])
    
    if not isinstance(data, list):
        raise ValueError("data must be a list of records for manual_data_entry node")
    
    return {"out": data}

def execute_cross_form_join_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute cross_form_join data source node."""
    properties = node.get("properties", {})
    form1_id = properties.get("form1_id")
    form2_id = properties.get("form2_id")
    join_key = properties.get("join_key")
    
    if not all([form1_id, form2_id, join_key]):
        raise ValueError("form1_id, form2_id, and join_key are required for cross_form_join node")
    
    from app.extensions import mongo
    
    # Get data from both forms
    form1_data = execute_form_responses_node(
        {"properties": {"form_id": form1_id}}, {}, context
    )["out"]
    
    form2_data = execute_form_responses_node(
        {"properties": {"form_id": form2_id}}, {}, context
    )["out"]
    
    # Convert to DataFrames and join
    df1 = pd.DataFrame(form1_data)
    df2 = pd.DataFrame(form2_data)
    
    if df1.empty or df2.empty:
        return {"out": []}
    
    if join_key not in df1.columns or join_key not in df2.columns:
        raise ValueError(f"Join key '{join_key}' not found in form data")
    
    merged_df = df1.merge(df2, on=join_key, how="inner", suffixes=("_form1", "_form2"))
    return {"out": to_records(merged_df)}

def execute_external_api_fetch_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute external_api_fetch data source node."""
    properties = node.get("properties", {})
    url = properties.get("url")
    method = properties.get("method", "GET")
    headers = properties.get("headers", {})
    body = properties.get("body")
    
    if not url:
        raise ValueError("url is required for external_api_fetch node")
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=body if method.upper() != "GET" else None
        )
        response.raise_for_status()
        
        data = response.json()
        if isinstance(data, dict):
            data = [data]
        
        return {"out": data}
    except Exception as e:
        raise ValueError(f"Error fetching external API data: {str(e)}")

def execute_filter_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute filter transform node."""
    properties = node.get("properties", {})
    query = properties.get("query")
    in_data = inputs.get("in", [])
    
    if not query:
        return {"out": in_data}
    
    return {"out": evaluate_filter(in_data, query)}

def execute_sort_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute sort transform node."""
    properties = node.get("properties", {})
    columns = properties.get("columns", [])
    ascending = properties.get("ascending", True)
    in_data = inputs.get("in", [])
    
    if not columns:
        return {"out": in_data}
    
    df = load_data(in_data)
    if df.empty:
        return {"out": []}
    
    try:
        sorted_df = df.sort_values(by=columns, ascending=ascending)
        return {"out": to_records(sorted_df)}
    except Exception as e:
        raise ValueError(f"Error sorting data: {str(e)}")

def execute_group_by_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute group_by transform node."""
    properties = node.get("properties", {})
    groupby_cols = properties.get("columns", [])
    aggregations = properties.get("aggregations", {})
    in_data = inputs.get("in", [])
    
    if not groupby_cols or not aggregations:
        return {"out": in_data}
    
    return {"out": evaluate_aggregation(in_data, groupby_cols, aggregations)}

def execute_join_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute join transform node."""
    properties = node.get("properties", {})
    left_on = properties.get("left_on")
    right_on = properties.get("right_on")
    how = properties.get("how", "inner")
    
    left_data = inputs.get("left", [])
    right_data = inputs.get("right", [])
    
    if not left_on or not right_on:
        raise ValueError("left_on and right_on are required for join node")
    
    df_left = load_data(left_data)
    df_right = load_data(right_data)
    
    if df_left.empty or df_right.empty:
        return {"out": []}
    
    try:
        merged_df = df_left.merge(df_right, left_on=left_on, right_on=right_on, how=how)
        return {"out": to_records(merged_df)}
    except Exception as e:
        raise ValueError(f"Error joining data: {str(e)}")

def execute_calculate_column_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute calculate_column transform node."""
    properties = node.get("properties", {})
    target_column = properties.get("target_column")
    formula = properties.get("formula")
    in_data = inputs.get("in", [])
    
    if not target_column or not formula:
        return {"out": in_data}
    
    return {"out": evaluate_formula(in_data, target_column, formula)}

def execute_pivot_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute pivot transform node."""
    properties = node.get("properties", {})
    index = properties.get("index", [])
    columns = properties.get("columns", [])
    values = properties.get("values", [])
    aggfunc = properties.get("aggfunc", "sum")
    in_data = inputs.get("in", [])
    
    if not index or not columns or not values:
        return {"out": in_data}
    
    df = load_data(in_data)
    if df.empty:
        return {"out": []}
    
    try:
        pivot_df = df.pivot_table(index=index, columns=columns, values=values, aggfunc=aggfunc)
        # Reset index to convert pivot table to regular table
        pivot_df = pivot_df.reset_index()
        return {"out": to_records(pivot_df)}
    except Exception as e:
        raise ValueError(f"Error pivoting data: {str(e)}")

def execute_unpivot_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute unpivot transform node."""
    properties = node.get("properties", {})
    id_vars = properties.get("id_vars", [])
    value_vars = properties.get("value_vars", [])
    var_name = properties.get("var_name", "variable")
    value_name = properties.get("value_name", "value")
    in_data = inputs.get("in", [])
    
    if not id_vars or not value_vars:
        return {"out": in_data}
    
    df = load_data(in_data)
    if df.empty:
        return {"out": []}
    
    try:
        unpivoted_df = df.melt(
            id_vars=id_vars, 
            value_vars=value_vars, 
            var_name=var_name, 
            value_name=value_name
        )
        return {"out": to_records(unpivoted_df)}
    except Exception as e:
        raise ValueError(f"Error unpivoting data: {str(e)}")

def execute_rename_columns_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute rename_columns transform node."""
    properties = node.get("properties", {})
    column_mapping = properties.get("column_mapping", {})
    in_data = inputs.get("in", [])
    
    if not column_mapping:
        return {"out": in_data}
    
    df = load_data(in_data)
    if df.empty:
        return {"out": []}
    
    try:
        renamed_df = df.rename(columns=column_mapping)
        return {"out": to_records(renamed_df)}
    except Exception as e:
        raise ValueError(f"Error renaming columns: {str(e)}")

def execute_select_columns_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute select_columns transform node."""
    properties = node.get("properties", {})
    columns = properties.get("columns", [])
    exclude = properties.get("exclude", False)
    in_data = inputs.get("in", [])
    
    if not columns:
        return {"out": in_data}
    
    df = load_data(in_data)
    if df.empty:
        return {"out": []}
    
    try:
        if exclude:
            # Exclude specified columns
            existing_cols = [col for col in df.columns if col not in columns]
            selected_df = df[existing_cols]
        else:
            # Select only specified columns that exist
            existing_cols = [col for col in columns if col in df.columns]
            selected_df = df[existing_cols]
        
        return {"out": to_records(selected_df)}
    except Exception as e:
        raise ValueError(f"Error selecting columns: {str(e)}")

def execute_deduplicate_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute deduplicate transform node."""
    properties = node.get("properties", {})
    subset = properties.get("subset", [])
    keep = properties.get("keep", "first")
    in_data = inputs.get("in", [])
    
    df = load_data(in_data)
    if df.empty:
        return {"out": []}
    
    try:
        deduplicated_df = df.drop_duplicates(subset=subset if subset else None, keep=keep)
        return {"out": to_records(deduplicated_df)}
    except Exception as e:
        raise ValueError(f"Error deduplicating data: {str(e)}")

def execute_fill_missing_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute fill_missing transform node."""
    properties = node.get("properties", {})
    method = properties.get("method", "mean")
    value = properties.get("value")
    columns = properties.get("columns", [])
    in_data = inputs.get("in", [])
    
    df = load_data(in_data)
    if df.empty:
        return {"out": []}
    
    try:
        if columns:
            target_cols = [col for col in columns if col in df.columns]
        else:
            target_cols = df.columns
        
        for col in target_cols:
            if method == "value" and value is not None:
                df[col] = df[col].fillna(value)
            elif method == "mean":
                df[col] = df[col].fillna(df[col].mean())
            elif method == "median":
                df[col] = df[col].fillna(df[col].median())
            elif method == "mode":
                df[col] = df[col].fillna(df[col].mode().iloc[0] if not df[col].mode().empty else 0)
            elif method == "forward":
                df[col] = df[col].fillna(method="ffill")
            elif method == "backward":
                df[col] = df[col].fillna(method="bfill")
        
        return {"out": to_records(df)}
    except Exception as e:
        raise ValueError(f"Error filling missing values: {str(e)}")

def execute_count_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute count aggregation node."""
    properties = node.get("properties", {})
    groupby_cols = properties.get("columns", [])
    in_data = inputs.get("in", [])
    
    if not groupby_cols:
        # Simple count
        df = load_data(in_data)
        return {"out": {"count": len(df)}}
    
    # Group by count
    aggregations = {"_count": "size"}
    return {"out": evaluate_aggregation(in_data, groupby_cols, aggregations)}

def execute_sum_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute sum aggregation node."""
    properties = node.get("properties", {})
    column = properties.get("column")
    groupby_cols = properties.get("columns", [])
    in_data = inputs.get("in", [])
    
    if not column:
        raise ValueError("column is required for sum node")
    
    df = load_data(in_data)
    if df.empty:
        return {"out": {"sum": 0}}
    
    if not groupby_cols:
        # Simple sum
        if column in df.columns:
            return {"out": {"sum": df[column].sum()}}
        else:
            return {"out": {"sum": 0}}
    
    # Group by sum
    aggregations = {column: "sum"}
    return {"out": evaluate_aggregation(in_data, groupby_cols, aggregations)}

def execute_average_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute average aggregation node."""
    properties = node.get("properties", {})
    column = properties.get("column")
    groupby_cols = properties.get("columns", [])
    in_data = inputs.get("in", [])
    
    if not column:
        raise ValueError("column is required for average node")
    
    df = load_data(in_data)
    if df.empty:
        return {"out": {"average": 0}}
    
    if not groupby_cols:
        # Simple average
        if column in df.columns:
            return {"out": {"average": df[column].mean()}}
        else:
            return {"out": {"average": 0}}
    
    # Group by average
    aggregations = {column: "mean"}
    return {"out": evaluate_aggregation(in_data, groupby_cols, aggregations)}

def execute_min_max_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute min_max aggregation node."""
    properties = node.get("properties", {})
    column = properties.get("column")
    groupby_cols = properties.get("columns", [])
    in_data = inputs.get("in", [])
    
    if not column:
        raise ValueError("column is required for min_max node")
    
    df = load_data(in_data)
    if df.empty:
        return {"out": {"min": None, "max": None}}
    
    if not groupby_cols:
        # Simple min/max
        if column in df.columns:
            return {"out": {"min": df[column].min(), "max": df[column].max()}}
        else:
            return {"out": {"min": None, "max": None}}
    
    # Group by min/max
    aggregations = {f"{column}_min": "min", f"{column}_max": "max"}
    return {"out": evaluate_aggregation(in_data, groupby_cols, aggregations)}

def execute_median_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute median aggregation node."""
    properties = node.get("properties", {})
    column = properties.get("column")
    groupby_cols = properties.get("columns", [])
    in_data = inputs.get("in", [])
    
    if not column:
        raise ValueError("column is required for median node")
    
    df = load_data(in_data)
    if df.empty:
        return {"out": {"median": 0}}
    
    if not groupby_cols:
        # Simple median
        if column in df.columns:
            return {"out": {"median": df[column].median()}}
        else:
            return {"out": {"median": 0}}
    
    # Group by median
    aggregations = {column: "median"}
    return {"out": evaluate_aggregation(in_data, groupby_cols, aggregations)}

def execute_percentile_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute percentile aggregation node."""
    properties = node.get("properties", {})
    column = properties.get("column")
    percentile = properties.get("percentile", 50)
    groupby_cols = properties.get("columns", [])
    in_data = inputs.get("in", [])
    
    if not column:
        raise ValueError("column is required for percentile node")
    
    df = load_data(in_data)
    if df.empty:
        return {"out": {"percentile": 0}}
    
    if not groupby_cols:
        # Simple percentile
        if column in df.columns:
            return {"out": {"percentile": df[column].quantile(percentile / 100)}}
        else:
            return {"out": {"percentile": 0}}
    
    # Group by percentile (pandas doesn't support percentile in agg, so we'll handle differently)
    # For now, return simple percentile
    return {"out": {"percentile": df[column].quantile(percentile / 100) if column in df.columns else 0}}

def execute_frequency_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute frequency aggregation node."""
    properties = node.get("properties", {})
    column = properties.get("column")
    in_data = inputs.get("in", [])
    
    if not column:
        raise ValueError("column is required for frequency node")
    
    df = load_data(in_data)
    if df.empty:
        return {"out": []}
    
    if column not in df.columns:
        return {"out": []}
    
    try:
        frequency_df = df[column].value_counts().reset_index()
        frequency_df.columns = [column, "count"]
        return {"out": to_records(frequency_df)}
    except Exception as e:
        raise ValueError(f"Error calculating frequency: {str(e)}")

def execute_cross_tabulation_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute cross_tabulation aggregation node."""
    properties = node.get("properties", {})
    index_col = properties.get("index_column")
    columns_col = properties.get("columns_column")
    values_col = properties.get("values_column")
    aggfunc = properties.get("aggfunc", "count")
    in_data = inputs.get("in", [])
    
    if not all([index_col, columns_col]):
        raise ValueError("index_column and columns_column are required for cross_tabulation node")
    
    df = load_data(in_data)
    if df.empty:
        return {"out": []}
    
    try:
        if values_col and aggfunc != "count":
            crosstab_df = pd.crosstab(
                df[index_col], 
                df[columns_col], 
                values=df[values_col] if values_col in df.columns else None,
                aggfunc=aggfunc
            )
        else:
            crosstab_df = pd.crosstab(df[index_col], df[columns_col])
        
        # Reset index to convert to regular table
        crosstab_df = crosstab_df.reset_index()
        return {"out": to_records(crosstab_df)}
    except Exception as e:
        raise ValueError(f"Error creating cross tabulation: {str(e)}")

def execute_table_output_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute table_output output node."""
    properties = node.get("properties", {})
    page_size = properties.get("page_size", 10)
    columns = properties.get("columns", [])
    in_data = inputs.get("in", [])
    
    df = load_data(in_data)
    
    # Auto-detect columns if not provided
    if not columns and not df.empty:
        columns = [{"name": col, "type": str(df[col].dtype)} for col in df.columns]
    
    return {
        "out": {
            "type": "table",
            "columns": columns,
            "rows": in_data,
            "row_count": len(df),
            "page_size": page_size
        }
    }

def execute_kpi_value_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute kpi_value output node."""
    properties = node.get("properties", {})
    column = properties.get("column")
    aggregation = properties.get("aggregation", "sum")
    in_data = inputs.get("in", [])
    
    df = load_data(in_data)
    if df.empty or not column or column not in df.columns:
        return {"out": {"type": "kpi", "value": 0, "label": properties.get("label", "")}}
    
    try:
        if aggregation == "sum":
            value = df[column].sum()
        elif aggregation == "mean":
            value = df[column].mean()
        elif aggregation == "count":
            value = len(df)
        elif aggregation == "min":
            value = df[column].min()
        elif aggregation == "max":
            value = df[column].max()
        else:
            value = df[column].sum()
        
        return {
            "out": {
                "type": "kpi",
                "value": float(value) if pd.notna(value) else 0,
                "label": properties.get("label", "")
            }
        }
    except Exception as e:
        raise ValueError(f"Error calculating KPI value: {str(e)}")

def execute_bar_chart_data_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute bar_chart_data output node."""
    properties = node.get("properties", {})
    label_column = properties.get("label_column")
    value_column = properties.get("value_column")
    in_data = inputs.get("in", [])
    
    df = load_data(in_data)
    if df.empty or not all([label_column, value_column]):
        return {"out": {"type": "bar_chart", "labels": [], "datasets": []}}
    
    if label_column not in df.columns or value_column not in df.columns:
        return {"out": {"type": "bar_chart", "labels": [], "datasets": []}}
    
    try:
        chart_data = {
            "type": "bar_chart",
            "labels": df[label_column].tolist(),
            "datasets": [
                {
                    "label": value_column,
                    "data": df[value_column].tolist()
                }
            ]
        }
        return {"out": chart_data}
    except Exception as e:
        raise ValueError(f"Error creating bar chart data: {str(e)}")

def execute_line_chart_data_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute line_chart_data output node."""
    properties = node.get("properties", {})
    x_column = properties.get("x_column")
    y_column = properties.get("y_column")
    in_data = inputs.get("in", [])
    
    df = load_data(in_data)
    if df.empty or not all([x_column, y_column]):
        return {"out": {"type": "line_chart", "labels": [], "datasets": []}}
    
    if x_column not in df.columns or y_column not in df.columns:
        return {"out": {"type": "line_chart", "labels": [], "datasets": []}}
    
    try:
        # Sort by x_column for line chart
        df = df.sort_values(x_column)
        
        chart_data = {
            "type": "line_chart",
            "labels": df[x_column].tolist(),
            "datasets": [
                {
                    "label": y_column,
                    "data": df[y_column].tolist()
                }
            ]
        }
        return {"out": chart_data}
    except Exception as e:
        raise ValueError(f"Error creating line chart data: {str(e)}")

def execute_pie_chart_data_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute pie_chart_data output node."""
    properties = node.get("properties", {})
    label_column = properties.get("label_column")
    value_column = properties.get("value_column")
    in_data = inputs.get("in", [])
    
    df = load_data(in_data)
    if df.empty or not all([label_column, value_column]):
        return {"out": {"type": "pie_chart", "labels": [], "data": []}}
    
    if label_column not in df.columns or value_column not in df.columns:
        return {"out": {"type": "pie_chart", "labels": [], "data": []}}
    
    try:
        chart_data = {
            "type": "pie_chart",
            "labels": df[label_column].tolist(),
            "data": df[value_column].tolist()
        }
        return {"out": chart_data}
    except Exception as e:
        raise ValueError(f"Error creating pie chart data: {str(e)}")

def execute_export_node(node: Dict, inputs: Dict, context: Dict) -> Dict:
    """Execute export output node."""
    properties = node.get("properties", {})
    format_type = properties.get("format", "csv")
    filename = properties.get("filename", "export")
    in_data = inputs.get("in", [])
    
    df = load_data(in_data)
    if df.empty:
        return {"out": {"type": "export", "status": "empty", "message": "No data to export"}}
    
    try:
        if format_type.lower() == "csv":
            csv_data = df.to_csv(index=False)
            return {
                "out": {
                    "type": "export",
                    "format": "csv",
                    "filename": f"{filename}.csv",
                    "data": csv_data,
                    "row_count": len(df)
                }
            }
        elif format_type.lower() == "excel":
            # For Excel, we'd typically use openpyxl or xlsxwriter
            # For now, return CSV format with Excel metadata
            csv_data = df.to_csv(index=False)
            return {
                "out": {
                    "type": "export",
                    "format": "excel",
                    "filename": f"{filename}.xlsx",
                    "data": csv_data,
                    "row_count": len(df)
                }
            }
        elif format_type.lower() == "pdf":
            # For PDF, we'd typically use reportlab or similar
            # For now, return data structure for PDF generation
            return {
                "out": {
                    "type": "export",
                    "format": "pdf",
                    "filename": f"{filename}.pdf",
                    "data": to_records(df),
                    "row_count": len(df)
                }
            }
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
    except Exception as e:
        raise ValueError(f"Error exporting data: {str(e)}")

# --- Main Execution Engine ---

NODE_EXECUTORS = {
    # Data Sources
    "form_responses": execute_form_responses_node,
    "csv_upload": execute_csv_upload_node,
    "manual_data_entry": execute_manual_data_entry_node,
    "cross_form_join": execute_cross_form_join_node,
    "external_api_fetch": execute_external_api_fetch_node,
    
    # Transforms
    "filter": execute_filter_node,
    "sort": execute_sort_node,
    "group_by": execute_group_by_node,
    "join": execute_join_node,
    "calculate_column": execute_calculate_column_node,
    "pivot": execute_pivot_node,
    "unpivot": execute_unpivot_node,
    "rename_columns": execute_rename_columns_node,
    "select_columns": execute_select_columns_node,
    "deduplicate": execute_deduplicate_node,
    "fill_missing": execute_fill_missing_node,
    
    # Aggregations
    "count": execute_count_node,
    "sum": execute_sum_node,
    "average": execute_average_node,
    "min_max": execute_min_max_node,
    "median": execute_median_node,
    "percentile": execute_percentile_node,
    "frequency": execute_frequency_node,
    "cross_tabulation": execute_cross_tabulation_node,
    
    # Outputs
    "table_output": execute_table_output_node,
    "kpi_value": execute_kpi_value_node,
    "bar_chart_data": execute_bar_chart_data_node,
    "line_chart_data": execute_line_chart_data_node,
    "pie_chart_data": execute_pie_chart_data_node,
    "export_node": execute_export_node
}

def execute_analysis_graph(graph: Dict, context: Dict) -> Dict:
    """
    Execute a complete analysis graph with error isolation.
    
    Args:
        graph: Dictionary containing nodes and edges
        context: Execution context (org_id, user_id, etc.)
        
    Returns:
        Dict: Execution results with node outputs and status
        
    Raises:
        GraphCycleException: If graph contains cycles
        NodeExecutionError: If critical node execution fails
    """
    # Validate graph structure
    validate_graph(graph)
    
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    
    # Build dependency graph
    node_map = {node["id"]: node for node in nodes}
    
    # Build graph for topological sorting
    graph_dict = {}
    for node in nodes:
        node_id = node["id"]
        dependencies = []
        for edge in edges:
            if edge["to_node"] == node_id:
                dependencies.append(edge["from_node"])
        graph_dict[node_id] = dependencies
    
    # Get execution order
    try:
        execution_order = validate_and_sort_dag(graph_dict)
    except GraphCycleException:
        raise
    
    # Execute nodes in order with error isolation
    node_outputs = {}
    node_errors = {}
    node_statuses = {}
    
    for node_id in execution_order:
        node = node_map.get(node_id)
        if not node:
            node_errors[node_id] = f"Node {node_id} not found in graph"
            node_statuses[node_id] = "error"
            continue
        
        if node.get("is_disabled", False):
            node_statuses[node_id] = "blocked"
            continue
        
        # Check if dependencies failed
        dependencies = graph_dict.get(node_id, [])
        failed_dependencies = [dep for dep in dependencies if node_statuses.get(dep) == "error"]
        
        if failed_dependencies:
            node_errors[node_id] = f"Dependencies failed: {', '.join(failed_dependencies)}"
            node_statuses[node_id] = "blocked"
            continue
        
        # Execute node
        try:
            # Resolve inputs from edges
            inputs = {}
            for edge in edges:
                if edge["to_node"] == node_id:
                    from_node = edge["from_node"]
                    from_port = edge["from_port"]
                    to_port = edge["to_port"]
                    
                    if from_node in node_outputs and from_port in node_outputs[from_node]:
                        inputs[to_port] = node_outputs[from_node][from_port]
            
            # Get node executor
            node_type = node.get("type")
            executor = NODE_EXECUTORS.get(node_type)
            
            if not executor:
                raise ValueError(f"Unknown node type: {node_type}")
            
            # Execute node
            output = executor(node, inputs, context)
            node_outputs[node_id] = output
            node_statuses[node_id] = "success"
            
        except Exception as e:
            error_msg = str(e)
            node_errors[node_id] = error_msg
            node_statuses[node_id] = "error"
            
            # Log error but continue with other nodes (error isolation)
            continue
    
    return {
        "node_outputs": node_outputs,
        "node_errors": node_errors,
        "node_statuses": node_statuses,
        "execution_order": execution_order
    }
