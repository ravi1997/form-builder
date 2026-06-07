# 08 — Dashboard System

This document outlines the free-form layout mechanics, widget schema properties, and analysis bindings for the **Dashboard Builder** subsystem.

---

## 1. Dashboard Workspace Schema

Dashboards are configured as single dynamic canvases. Position and layout properties are defined using absolute coordinate systems.

```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "project_id": "ObjectId",
  "name": "String",
  "description": "String",
  "is_public": "Boolean",
  "public_token": "String | null",
  "canvas": {
    "width": 1920,
    "height": 1080,
    "background_color": "String (HEX)",
    "widgets": [
      {
        "id": "String (UUID)",
        "type": "String",
        "position": { "x": "Number", "y": "Number" },
        "size": { "width": "Number", "height": "Number" },
        "z_index": "Number",
        "is_locked": "Boolean",
        "properties": "Object",
        "data_binding": {
          "analysis_id": "ObjectId",
          "node_id": "String (UUID)",
          "refresh_mode": "String (enum: with_dashboard | independent | never)"
        },
        "filters": [
          {
            "filter_widget_id": "String (UUID)",
            "bound_field": "String"
          }
        ]
      }
    ]
  },
  "settings": {
    "auto_refresh": "Boolean",
    "refresh_interval_seconds": 60,
    "theme": "Object"
  },
  "linked_analysis_ids": ["ObjectId"]
}
```

---

## 2. Interactive Free-Form Canvas

The Flutter canvas translates widget bounds using absolute layout elements:
- **Responsive Scaler**: Computes physical client device dimensions against the logical canvas size (`1920x1080`) to apply a uniform scaling transform (`Matrix4`).
- **Overlap Rules**: Dragging operations calculate visual overlap warnings, but lock states prevent overlapping modifications on locked widgets.
- **Layer ordering**: Evaluated relative to the widget `z_index` property.

---

## 3. Core Widget Specifications

### 3.1 KPI Card (`kpi_card`)
* **Purpose**: Renders a single metrics property.
* **Expected Input**: `value` or single cell from `dataframe`.
* **Properties**:
  - `title`: String
  - `color`: String (HEX code)
  - `font_size`: Number
  - `prefix`: String
  - `suffix`: String

### 3.2 Bar Chart (`bar_chart`) / Line Chart (`line_chart`)
* **Purpose**: Plotting categorical/timeseries datasets.
* **Expected Input**: `chart_data` structure.
* **Properties**:
  - `x_axis_label`: String
  - `y_axis_label`: String
  - `show_legend`: Boolean
  - `palette`: Array of Colors

### 3.3 Pie Chart (`pie_chart`)
* **Purpose**: Renders percentage distributions.
* **Expected Input**: `chart_data` structure.
* **Properties**:
  - `donut_hole`: Boolean
  - `show_percentages`: Boolean

### 3.4 Data Table (`data_table`)
* **Purpose**: Display tabular rows directly.
* **Expected Input**: `table` structure.
* **Properties**:
  - `show_search`: Boolean
  - `striped_rows`: Boolean
  - `rows_per_page`: Number

### 3.5 Filter Widget (`filter_widget`)
* **Purpose**: Exposes filter inputs to modify downstream datasets.
* **Expected Input**: Form question enum list or unique values from a column.
* **Properties**:
  - `filter_type`: String (enum: `dropdown` | `date_range` | `checkbox_group`)
  - `target_field`: String
