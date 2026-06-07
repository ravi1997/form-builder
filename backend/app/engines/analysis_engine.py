import json
import networkx as nx
import pandas as pd

class GraphCycleException(Exception):
    """Exception raised when a cycle is detected in a graph."""
    pass

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
    else:
        dg = nx.DiGraph()
        for node_id, value in graph.items():
            dg.add_node(node_id)
            if isinstance(value, dict):
                dependencies = value.get("dependencies", [])
            else:
                dependencies = value
            for dep in dependencies:
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

# --- Evaluation Helpers using Pandas/JSON ---

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
