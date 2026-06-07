# 07 — Analysis Coder System

This document outlines the architecture, pipeline execution models, and complete node library specification for the **Analysis Coder** engine.

---

## 1. Graph Specification Schema

An analysis pipeline is a Directed Acyclic Graph (DAG) saved as JSON containing an array of `nodes` and typed `edges`.

```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "project_id": "ObjectId",
  "name": "String",
  "linked_form_ids": ["ObjectId"],
  "execution_modes": ["String (enum: on_demand | reactive | scheduled)"],
  "schedule": "String | null",
  "reactive_debounce_ms": 1000,
  "graph": {
    "nodes": [
      {
        "id": "String (UUID)",
        "type": "String",
        "position": { "x": 100, "y": 200 },
        "size": { "width": 150, "height": 100 },
        "properties": {},
        "label": "String",
        "is_disabled": "Boolean"
      }
    ],
    "edges": [
      {
        "id": "String (UUID)",
        "from_node": "String (UUID)",
        "from_port": "String",
        "to_node": "String (UUID)",
        "to_port": "String"
      }
    ]
  }
}
```

---

## 2. Port Connections & Data Type Safety

Ports are strictly typed to validate connections before execution:
- **`dataframe`**: A dynamic tabular structure representing Pandas DataFrames.
- **`value`**: A scalar primitive value (e.g. integer count, string label, float ratio).
- **`table`**: Configured rows and headers for final user tables.
- **`chart_data`**: Formatted JSON structures for visualization widgets.

Edges are invalid and rejected at API level if `from_port.type != to_port.type`.

---

## 3. DAG Validation & Execution Engine

1. **Cycle Detection**: Constructed and evaluated using Python's `NetworkX` library:
   ```python
   import networkx as nx
   dag = nx.DiGraph()
   for node in graph["nodes"]:
       dag.add_node(node["id"])
   for edge in graph["edges"]:
       dag.add_edge(edge["from_node"], edge["to_node"])
   if not nx.is_directed_acyclic_graph(dag):
       raise GraphCycleException("The analysis graph contains invalid loop cycles.")
   ```
2. **Topological Sort**: Node execution sequences are resolved using `nx.topological_sort(dag)`.
3. **Execution Isolation**: Runs inside a Celery background task. If a node fails, it caches an error state in its result object, marking all downstream dependent nodes as `blocked`, while independent branches continue executing to completion.

---

## 4. Analysis Node Library Reference

### 4.1 Data Sources

#### `form_source`
* **Description**: Loads answers from a form's responses.
* **Outputs**: `out` (`dataframe`)
* **Properties**:
  - `form_id`: ObjectId (Linked form)
  - `include_drafts`: Boolean (default: `false`)

#### `csv_source`
* **Description**: Reads a flat CSV from the uploaded files volume.
* **Outputs**: `out` (`dataframe`)
* **Properties**:
  - `file_path`: String

---

### 4.2 Transformations

#### `pandas_filter`
* **Description**: Evaluates logic statements to filter rows.
* **Inputs**: `in` (`dataframe`)
* **Outputs**: `out` (`dataframe`)
* **Properties**:
  - `query`: String (e.g. `Age >= 18 and Status == 'Approved'`)

#### `pandas_column_select`
* **Description**: Excludes or renames columns from the active dataset.
* **Inputs**: `in` (`dataframe`)
* **Outputs**: `out` (`dataframe`)
* **Properties**:
  - `columns`: Array of Strings

#### `dataframe_join`
* **Description**: Combines two datasets based on key values.
* **Inputs**: `left` (`dataframe`), `right` (`dataframe`)
* **Outputs**: `out` (`dataframe`)
* **Properties**:
  - `left_on`: String (column key)
  - `right_on`: String (column key)
  - `how`: String (enum: `inner` | `left` | `right` | `outer`)

#### `group_by_aggregation`
* **Description**: Aggregates records grouped by keys.
* **Inputs**: `in` (`dataframe`)
* **Outputs**: `out` (`dataframe`)
* **Properties**:
  - `keys`: Array of Strings
  - `aggregation_column`: String
  - `function`: String (enum: `sum` | `mean` | `count` | `min` | `max`)

---

### 4.3 Reducers & Visualizations

#### `scalar_aggregator`
* **Description**: Computes a single summary metric from a column.
* **Inputs**: `in` (`dataframe`)
* **Outputs**: `out` (`value`)
* **Properties**:
  - `column`: String
  - `function`: String (enum: `sum` | `mean` | `count` | `min` | `max`)

#### `chart_formatter`
* **Description**: Re-shapes tables into plotting formats.
* **Inputs**: `in` (`dataframe`)
* **Outputs**: `out` (`chart_data`)
* **Properties**:
  - `label_column`: String
  - `value_column`: String
  - `chart_type`: String (enum: `bar` | `line` | `pie`)

#### `table_generator`
* **Description**: Generates formatted tables.
* **Inputs**: `in` (`dataframe`)
* **Outputs**: `out` (`table`)
* **Properties**:
  - `page_size`: Number (default: `10`)
  - `columns`: Array of Objects `{name, label, align}`
