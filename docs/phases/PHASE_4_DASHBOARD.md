# PHASE 4: Dashboard Builder — Complete Implementation Plan

**Phase Goal:** Deliver a fully functional free-form canvas dashboard builder with all built-in
widget types, data binding to analysis output nodes, configurable auto-refresh, public sharing
via token, dashboard snapshots, PDF export, and a complete Flutter UI with edit/preview modes.

**Prerequisite Phases:** Phase 1 (Foundation), Phase 2 (Form Builder), Phase 3 (Analysis Coder)
must be complete. The `analyses`, `analysis_runs`, and `analysis_results` collections must be
populated and accessible.

---

## Table of Contents

1. [MongoDB Collection Reference](#1-mongodb-collection-reference)
2. [Dashboard CRUD API](#2-dashboard-crud-api)
3. [Canvas Save/Load API](#3-canvas-saveload-api)
4. [Public Token Generation and Unauthenticated Access](#4-public-token-generation-and-unauthenticated-access)
5. [Dashboard Snapshot API](#5-dashboard-snapshot-api)
6. [Auto-Refresh Architecture](#6-auto-refresh-architecture)
7. [Filter Widget Binding API](#7-filter-widget-binding-api)
8. [Built-in Widget Specifications](#8-built-in-widget-specifications)
9. [Flutter: Free-Form Canvas Implementation](#9-flutter-free-form-canvas-implementation)
10. [Flutter: Widget Library Sidebar](#10-flutter-widget-library-sidebar)
11. [Flutter: Widget Property Panel](#11-flutter-widget-property-panel)
12. [Flutter: Data Binding UI](#12-flutter-data-binding-ui)
13. [Flutter: Filter Widget Interaction](#13-flutter-filter-widget-interaction)
14. [Flutter: Auto-Refresh Implementation](#14-flutter-auto-refresh-implementation)
15. [Flutter: Public Dashboard View](#15-flutter-public-dashboard-view)
16. [Flutter: Dashboard Sharing Dialog](#16-flutter-dashboard-sharing-dialog)
17. [Flutter: Edit Mode vs Preview Mode](#17-flutter-edit-mode-vs-preview-mode)
18. [Dashboard PDF Export](#18-dashboard-pdf-export)
19. [Error Codes Reference](#19-error-codes-reference)
20. [Backend File Locations](#20-backend-file-locations)

---

## 1. MongoDB Collection Reference

All dashboard-related data is stored in the following collections (defined in CONTEXT.md §5.7).
Reproduce them here for quick reference.

### `dashboards` Collection

```json
{
  "_id": "ObjectId",
  "org_id": "ObjectId",
  "project_id": "ObjectId",
  "name": "string (max 120 chars)",
  "description": "string (max 500 chars, optional)",
  "is_public": "boolean (default: false)",
  "public_token": "string (UUID-v4, null unless is_public=true)",
  "canvas": {
    "width": "number (px, default 1920)",
    "height": "number (px, default 1080)",
    "background_color": "string (hex, default '#F5F5F5')",
    "widgets": ["Widget[]  — see Widget schema below"]
  },
  "settings": {
    "auto_refresh": "boolean (default: false)",
    "refresh_interval_seconds": "number (min 10, max 3600, default 60)",
    "theme": {
      "font_family": "string (default 'Inter')",
      "primary_color": "string (hex)",
      "border_radius": "number (px)"
    }
  },
  "linked_analysis_ids": ["ObjectId[]  — denormalised list of all analyses used"],
  "created_at": "ISODate",
  "updated_at": "ISODate",
  "created_by": "ObjectId",
  "is_deleted": "boolean",
  "deleted_at": "ISODate or null"
}
```

### Widget Sub-Document Schema

```json
{
  "id": "string (UUID-v4, unique within canvas)",
  "type": "string (component_type — see §8 for all built-in types)",
  "position": { "x": "number (px)", "y": "number (px)" },
  "size": { "width": "number (px)", "height": "number (px)" },
  "z_index": "number (integer, default 0)",
  "is_locked": "boolean (default: false)",
  "properties": "object (widget-type-specific — see §8)",
  "data_binding": {
    "analysis_id": "ObjectId or null",
    "node_id": "string (node UUID within analysis) or null",
    "refresh_mode": "enum: with_dashboard | independent | never"
  },
  "filters": [
    {
      "filter_widget_id": "string (UUID of a filter widget on the same canvas)",
      "bound_field": "string (column name in the data source)"
    }
  ]
}
```

### `dashboard_snapshots` Collection

```json
{
  "_id": "ObjectId",
  "dashboard_id": "ObjectId",
  "org_id": "ObjectId",
  "data": {
    "widget_data": {
      "<widget_id>": "any (the resolved data for each widget at snapshot time)"
    },
    "canvas_meta": {
      "name": "string",
      "width": "number",
      "height": "number"
    },
    "snapshot_at": "ISODate"
  },
  "created_at": "ISODate",
  "created_by": "ObjectId",
  "is_deleted": "boolean",
  "deleted_at": "ISODate or null"
}
```

**Indexes to create:**

```
dashboards: { org_id: 1 }
dashboards: { project_id: 1 }
dashboards: { public_token: 1 }   ← sparse, unique, used for public access lookups
dashboards: { is_deleted: 1 }
dashboard_snapshots: { dashboard_id: 1, created_at: -1 }
```

---

## 2. Dashboard CRUD API

**Blueprint:** `backend/app/routes/dashboard.py`
**Service:** `backend/app/services/dashboard_service.py`
**Base route prefix:** `/api/internal/v1/dashboards`

All endpoints require a valid JWT access token unless noted otherwise.
Permission model:
- `org_admin`, `org_editor` → full CRUD
- `org_analyst` → read + create (cannot delete others' dashboards)
- `org_viewer` → read only
- `project_owner`, `project_editor` → full CRUD within project
- `project_analyst` → read + create
- `project_viewer` → read only

### 2.1 Create Dashboard

```
POST /api/internal/v1/dashboards
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "project_id": "ObjectId string (required)",
  "name": "string (required, 1–120 chars)",
  "description": "string (optional, max 500 chars)",
  "canvas": {
    "width": 1920,
    "height": 1080,
    "background_color": "#F5F5F5",
    "widgets": []
  },
  "settings": {
    "auto_refresh": false,
    "refresh_interval_seconds": 60,
    "theme": {}
  }
}
```

**Validation rules:**
- `project_id` must be a valid ObjectId and the requesting user must have access to that project
- `name` required, stripped of leading/trailing whitespace, unique within the project (case-insensitive)
- `canvas.width` range: 800–7680; `canvas.height` range: 600–4320
- `settings.refresh_interval_seconds` range: 10–3600 (only validated if `auto_refresh` is true)
- `canvas.widgets` must be an empty array on creation (widgets are added via PATCH)

**Response 201:**

```json
{
  "dashboard": {
    "_id": "ObjectId string",
    "org_id": "ObjectId string",
    "project_id": "ObjectId string",
    "name": "Dashboard Name",
    "description": "",
    "is_public": false,
    "public_token": null,
    "canvas": { "width": 1920, "height": 1080, "background_color": "#F5F5F5", "widgets": [] },
    "settings": { "auto_refresh": false, "refresh_interval_seconds": 60, "theme": {} },
    "linked_analysis_ids": [],
    "created_at": "2026-06-07T09:00:00Z",
    "updated_at": "2026-06-07T09:00:00Z",
    "created_by": "ObjectId string"
  }
}
```

**Error responses:**

| HTTP Code | Error Code | Condition |
|-----------|-----------|-----------|
| 400 | `VALIDATION_ERROR` | Missing/invalid fields |
| 403 | `FORBIDDEN` | User lacks org/project access |
| 404 | `PROJECT_NOT_FOUND` | project_id does not exist |
| 409 | `DASHBOARD_NAME_CONFLICT` | Name already taken in project |

---

### 2.2 List Dashboards

```
GET /api/internal/v1/dashboards?project_id=<id>&page=1&per_page=20&search=<text>
Authorization: Bearer <access_token>
```

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | ObjectId string | Yes | Filter by project |
| `page` | integer | No | Page number (default: 1) |
| `per_page` | integer | No | Items per page (default: 20, max: 100) |
| `search` | string | No | Case-insensitive name match |

**Response 200:**

```json
{
  "dashboards": [
    {
      "_id": "...",
      "name": "...",
      "description": "...",
      "is_public": false,
      "settings": { "auto_refresh": true, "refresh_interval_seconds": 30 },
      "linked_analysis_ids": ["..."],
      "created_at": "...",
      "updated_at": "...",
      "created_by_user": { "_id": "...", "full_name": "...", "avatar_url": "..." }
    }
  ],
  "pagination": {
    "total": 42,
    "page": 1,
    "per_page": 20,
    "total_pages": 3
  }
}
```

Note: the `canvas.widgets` array is **NOT** returned in the list endpoint to keep payloads small.
Widgets are returned only by the get-by-ID endpoint.

---

### 2.3 Get Dashboard by ID

```
GET /api/internal/v1/dashboards/<dashboard_id>
Authorization: Bearer <access_token>
```

**Response 200:** Full dashboard document including all widgets, plus resolved analysis metadata:

```json
{
  "dashboard": { "<full dashboard document>" },
  "linked_analyses": [
    {
      "_id": "ObjectId",
      "name": "Analysis name",
      "status": "idle|running|error",
      "last_run_id": "ObjectId",
      "output_nodes": [
        {
          "node_id": "uuid",
          "label": "Node label",
          "type": "table_output|kpi_value|bar_chart_data|...",
          "output_type": "table|value|chart_data"
        }
      ]
    }
  ]
}
```

The `output_nodes` array is built by reading the `analyses.graph.nodes` field and filtering for
nodes whose `type` is one of the output node types:
`table_output`, `kpi_value`, `bar_chart_data`, `line_chart_data`, `pie_chart_data`.

**Error responses:**

| HTTP Code | Error Code | Condition |
|-----------|-----------|-----------|
| 403 | `FORBIDDEN` | No access to this dashboard's project/org |
| 404 | `DASHBOARD_NOT_FOUND` | Dashboard not found or soft-deleted |

---

### 2.4 Update Dashboard Metadata

```
PATCH /api/internal/v1/dashboards/<dashboard_id>
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body (all fields optional):**

```json
{
  "name": "New Name",
  "description": "Updated description",
  "settings": {
    "auto_refresh": true,
    "refresh_interval_seconds": 30,
    "theme": { "primary_color": "#1976D2" }
  }
}
```

- Partial updates — only provided fields are changed
- `name` uniqueness still enforced
- `settings` is merged (not replaced): only provided sub-keys are updated

**Response 200:** Updated dashboard document (same shape as GET by ID).

---

### 2.5 Delete Dashboard

```
DELETE /api/internal/v1/dashboards/<dashboard_id>
Authorization: Bearer <access_token>
```

- Soft delete: sets `is_deleted=true`, `deleted_at=now()`
- Only `org_admin`, `project_owner`, or the dashboard creator may delete
- Orphaned snapshots are NOT deleted (kept for audit history); they are filtered in queries
- **Response 200:** `{ "message": "Dashboard deleted" }`

---

## 3. Canvas Save/Load API

The canvas (widget positions, sizes, bindings) is embedded inside the dashboard document.
Saving the canvas replaces the entire `canvas` field atomically. No partial widget-level saves
exist — the full canvas is always sent.

### 3.1 Save Canvas State

```
PUT /api/internal/v1/dashboards/<dashboard_id>/canvas
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "canvas": {
    "width": 1920,
    "height": 1080,
    "background_color": "#F5F5F5",
    "widgets": [
      {
        "id": "uuid-v4",
        "type": "kpi_card",
        "position": { "x": 40, "y": 40 },
        "size": { "width": 280, "height": 140 },
        "z_index": 1,
        "is_locked": false,
        "properties": {
          "title": "Total Responses",
          "value_format": "number",
          "prefix": "",
          "suffix": "",
          "icon": "people",
          "color_scheme": "blue"
        },
        "data_binding": {
          "analysis_id": "ObjectId string or null",
          "node_id": "node-uuid or null",
          "refresh_mode": "with_dashboard"
        },
        "filters": []
      }
    ]
  }
}
```

**Validation rules:**

- `canvas.widgets` is an array of zero or more valid Widget objects
- Each widget `id` must be a valid UUID-v4; all ids must be unique within the array
- `type` must be a valid component_type known to the system (checked against `component_schemas`)
- `position.x` and `position.y` must be >= 0
- `size.width` and `size.height` must be >= 20px
- `z_index` must be an integer in range 0–999
- `data_binding.analysis_id` if present: must be a valid analysis the user has access to
- `data_binding.node_id` if present: must be a node that exists in the referenced analysis
- `data_binding.refresh_mode` must be one of: `with_dashboard`, `independent`, `never`
- Each `filters[].filter_widget_id` must reference a widget `id` that exists in the same `widgets` array

**Service logic (`dashboard_service.save_canvas`):**

1. Load existing dashboard; verify user has write access
2. Validate entire canvas structure
3. Recompute `linked_analysis_ids`: collect all unique `analysis_id` values from widgets that have a non-null `data_binding.analysis_id`
4. Atomically `$set` `canvas`, `linked_analysis_ids`, `updated_at`
5. Write an audit log entry: `entity_type="dashboard"`, `action="canvas_saved"`, `before={widget_count: N}`, `after={widget_count: M}`
6. Return updated dashboard

**Response 200:** Full updated dashboard document.

**Error responses:**

| HTTP Code | Error Code | Condition |
|-----------|-----------|-----------|
| 400 | `CANVAS_VALIDATION_ERROR` | Invalid widget structure |
| 400 | `INVALID_ANALYSIS_BINDING` | Bound analysis_id or node_id not found |
| 403 | `FORBIDDEN` | Viewer role trying to save |
| 404 | `DASHBOARD_NOT_FOUND` | Dashboard not found |

---

### 3.2 Load Canvas Data (with Widget Data Resolution)

When the dashboard editor opens, the client must load both the canvas structure AND the current
data for each bound widget.

```
GET /api/internal/v1/dashboards/<dashboard_id>/canvas/data
Authorization: Bearer <access_token>
```

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `filter_state` | JSON string (URL-encoded) | Optional current filter state: `{"widget_id": "column_value", ...}` |

**Response 200:**

```json
{
  "canvas": { "<canvas object with all widgets>" },
  "widget_data": {
    "<widget_id>": {
      "status": "ok|loading|error|no_binding|no_run",
      "data": "<widget-type-specific data structure — see §8>",
      "run_id": "ObjectId string",
      "generated_at": "ISODate",
      "error": "string or null"
    }
  }
}
```

**Server resolution logic:**

For each widget with a non-null `data_binding`:
1. Look up the latest `analysis_run` for `analysis_id` where `status=completed`
2. Look up the `analysis_result` for that `run_id` + `node_id`
3. Apply active filter state: for each filter in `widget.filters`, find the filter widget's current
   value and filter the result data rows by `bound_field == filter_value`
4. Return widget-type-specific formatted data (see §8 for each type's expected format)

If no completed run exists: return `{ "status": "no_run" }`.
If the analysis node failed: return `{ "status": "error", "error": "node error message" }`.
If no binding: return `{ "status": "no_binding" }`.

---

## 4. Public Token Generation and Unauthenticated Access

### 4.1 Enable Public Sharing

```
POST /api/internal/v1/dashboards/<dashboard_id>/public-token
Authorization: Bearer <access_token>
```

Requires `org_admin` or `project_owner` role.

**Service logic:**
1. Generate `public_token = str(uuid.uuid4())` (UUID-v4, 36 chars with hyphens)
2. Set `is_public=true`, `public_token=<token>`, `updated_at=now()`
3. Atomically save to dashboards collection
4. Write audit log: `action="dashboard_made_public"`

**Response 200:**

```json
{
  "is_public": true,
  "public_token": "550e8400-e29b-41d4-a716-446655440000",
  "public_url": "https://<platform_domain>/public/dashboard/550e8400-e29b-41d4-a716-446655440000"
}
```

The `public_url` is constructed by the server from `system_config.platform_url`.

### 4.2 Revoke Public Access

```
DELETE /api/internal/v1/dashboards/<dashboard_id>/public-token
Authorization: Bearer <access_token>
```

Sets `is_public=false`, `public_token=null`. The old token immediately becomes invalid
(the lookup query requires both `is_public=true` and the token match).

**Response 200:** `{ "message": "Public access revoked" }`

### 4.3 Public (Unauthenticated) Dashboard Access

```
GET /api/v1/public/dashboards/<public_token>
```

**No authorization required.** Rate-limited to 20 req/min per IP (Flask-Limiter).

**Server logic:**
1. Look up: `{ "public_token": <token>, "is_public": true, "is_deleted": false }`
2. If not found → 404
3. Resolve widget data (same as §3.2) — filter state defaults to empty
4. Do NOT include internal org_id, project_id, created_by, or user information in the response

**Response 200:**

```json
{
  "dashboard": {
    "name": "string",
    "description": "string",
    "canvas": { "<canvas with widgets (properties only — no data_binding details)>" },
    "settings": {
      "auto_refresh": true,
      "refresh_interval_seconds": 60
    },
    "last_updated": "ISODate"
  },
  "widget_data": {
    "<widget_id>": { "status": "ok", "data": "<...>", "generated_at": "ISODate" }
  }
}
```

**Security note:** The `data_binding` field (containing internal analysis_id and node_id) is
**stripped** from the widget objects returned in the public endpoint. Only `properties` and
positioning data are returned.

### 4.4 Public Dashboard Data Refresh

For auto-refresh, the public viewer polls a separate lightweight endpoint:

```
GET /api/v1/public/dashboards/<public_token>/data
```

Query parameter: `filter_state=<url-encoded JSON>`

Same logic as §4.3 but only returns `widget_data` (not the full canvas structure).
This reduces payload on every refresh cycle.

**Response 200:**

```json
{
  "widget_data": { "<widget_id>": { "status": "ok", "data": "<...>", "generated_at": "ISODate" } },
  "server_time": "ISODate"
}
```

---

## 5. Dashboard Snapshot API

A snapshot captures the current resolved widget data at a point in time. Snapshots are stored
in `dashboard_snapshots` and can be used for historical comparison or PDF generation.

### 5.1 Create Snapshot

```
POST /api/internal/v1/dashboards/<dashboard_id>/snapshots
Authorization: Bearer <access_token>
```

**No request body.** The server resolves all widget data at the time of the call.

**Service logic (`dashboard_service.create_snapshot`):**

1. Fetch the dashboard (verify access)
2. For each bound widget: resolve latest analysis_result data (same as §3.2)
3. Build snapshot document:
```json
{
  "dashboard_id": "ObjectId",
  "org_id": "ObjectId",
  "data": {
    "widget_data": { "<widget_id>": "<data>" },
    "canvas_meta": {
      "name": "string",
      "width": 1920,
      "height": 1080,
      "background_color": "#F5F5F5"
    },
    "snapshot_at": "ISODate"
  },
  "created_at": "ISODate",
  "created_by": "ObjectId"
}
```
4. Insert into `dashboard_snapshots`
5. Return new snapshot

**Response 201:**

```json
{
  "snapshot": {
    "_id": "ObjectId string",
    "dashboard_id": "...",
    "data": { "snapshot_at": "ISODate", "widget_data": { "..." } },
    "created_at": "ISODate",
    "created_by": "ObjectId string"
  }
}
```

---

### 5.2 List Snapshots

```
GET /api/internal/v1/dashboards/<dashboard_id>/snapshots?page=1&per_page=20
Authorization: Bearer <access_token>
```

**Response 200:** Paginated list of snapshot metadata (excludes large `data.widget_data` field):

```json
{
  "snapshots": [
    {
      "_id": "...",
      "dashboard_id": "...",
      "snapshot_at": "ISODate",
      "created_at": "ISODate",
      "created_by_user": { "_id": "...", "full_name": "..." }
    }
  ],
  "pagination": { "total": 5, "page": 1, "per_page": 20, "total_pages": 1 }
}
```

---

### 5.3 Get Snapshot by ID

```
GET /api/internal/v1/dashboards/<dashboard_id>/snapshots/<snapshot_id>
Authorization: Bearer <access_token>
```

**Response 200:** Full snapshot document including `data.widget_data`.

---

### 5.4 Delete Snapshot

```
DELETE /api/internal/v1/dashboards/<dashboard_id>/snapshots/<snapshot_id>
Authorization: Bearer <access_token>
```

Requires `org_admin` or `project_owner`. Soft-deletes the snapshot.
**Response 200:** `{ "message": "Snapshot deleted" }`

---

## 6. Auto-Refresh Architecture

The dashboard supports configurable auto-refresh. Two mechanisms exist: **WebSocket push** for
authenticated editors, and **HTTP polling** for both public viewers and authenticated viewers.

### 6.1 Design Decision: Polling Primary, WebSocket Secondary

The primary refresh mechanism is **client-side HTTP polling** because:
- It is stateless and works for public (unauthenticated) viewers
- It works through Nginx without additional WebSocket config
- Analysis results only change when a new analysis run completes (not streaming data)

WebSocket (Flask-SocketIO) is used only for **push notifications** when a new analysis run
completes, to trigger the polling client to refresh immediately rather than waiting for the
next poll interval.

### 6.2 Polling Endpoint

Already defined in §4.4 for public dashboards.

For authenticated dashboards, the same pattern applies:

```
GET /api/internal/v1/dashboards/<dashboard_id>/data
Authorization: Bearer <access_token>
```

Query parameters:
- `filter_state` (JSON string, optional)

Response: Same as §4.4 `widget_data` structure.

**Server caching:** Results for each `(dashboard_id, analysis_run_id)` pair are cached in Redis
for `refresh_interval_seconds` to prevent redundant DB reads. Cache key:
`dashboard_data:{dashboard_id}:{run_id_hash}`. TTL = `refresh_interval_seconds`.

### 6.3 WebSocket Push Notification

When a new `analysis_run` completes (status changes to `completed`), the Celery analysis task
emits a Socket.IO event to notify connected dashboard clients.

**Socket.IO event emitted by Celery worker:**

```python
# In backend/app/workers/analysis_tasks.py, after run completion:
socketio.emit(
    'analysis_run_completed',
    {
        'analysis_id': str(analysis_id),
        'run_id': str(run_id),
        'status': 'completed',
        'completed_at': datetime.utcnow().isoformat()
    },
    room=f'org_{org_id}'    # room = org-scoped channel
)
```

**Socket.IO room management:**
- Authenticated client joins room `org_{org_id}` on connect
- Client listens for `analysis_run_completed` events
- On receipt, client checks if the completed `analysis_id` is in the dashboard's `linked_analysis_ids`
- If yes: client immediately calls the polling endpoint regardless of timer state
- If no: event is ignored

**Flutter WebSocket integration:** see §14.

### 6.4 Per-Widget Independent Refresh

Widgets with `refresh_mode = "independent"` manage their own refresh cycle independently of the
dashboard-level interval. The server does not differentiate — the client controls this by calling
the data endpoint only for specific widget IDs.

For independent refresh, the Flutter client makes per-widget data requests:

```
GET /api/internal/v1/dashboards/<dashboard_id>/widgets/<widget_id>/data
Authorization: Bearer <access_token>
```

Response:

```json
{
  "widget_id": "uuid",
  "status": "ok|loading|error|no_binding|no_run",
  "data": "<widget-type-specific>",
  "generated_at": "ISODate"
}
```

Widgets with `refresh_mode = "never"` are never auto-refreshed; their data is only resolved on
initial page load.

### 6.5 Auto-Refresh Settings Enforcement

| Setting | Behavior |
|---------|----------|
| `auto_refresh: false` | Client never auto-polls; data shown is from initial load |
| `auto_refresh: true`, `refresh_interval_seconds: N` | Client polls every N seconds |
| Dashboard is public | Same settings apply; uses the unauthenticated data endpoint |
| Minimum interval | 10 seconds (enforced server-side validation and client-side clamp) |

---

## 7. Filter Widget Binding API

Filter widgets allow users to interactively filter data shown in other widgets. Filter state is
**client-side only** — the server is stateless with respect to filter values. Filter values are
sent as query parameters on data fetch requests.

### 7.1 Filter State Structure

The filter state is a flat JSON object mapping filter widget IDs to their current values:

```json
{
  "<filter_widget_id_1>": "2026-01",
  "<filter_widget_id_2>": "Dr. Smith",
  "<filter_widget_id_3>": ["Option A", "Option B"]
}
```

Value types:
- Single string: for dropdown, text, and date filter widgets
- Array of strings: for multi-select filter widgets
- Date range object: `{ "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" }` for date range widgets

### 7.2 Server-Side Filter Application

When the server resolves widget data and a `filter_state` is provided:

**Algorithm (implemented in `dashboard_service.py`):**

```python
def apply_filters(result_data: dict, widget: dict, filter_state: dict) -> dict:
    """
    result_data: the raw analysis_result.data dict
    widget: the widget sub-document
    filter_state: {filter_widget_id: value, ...}
    Returns filtered data in same format as input
    """
    if result_data.get('output_type') not in ('table', 'dataframe'):
        return result_data  # Only table/dataframe supports row filtering

    rows = result_data.get('rows', [])

    for binding in widget.get('filters', []):
        filter_widget_id = binding['filter_widget_id']
        bound_field = binding['bound_field']

        if filter_widget_id not in filter_state:
            continue  # Filter widget has no value set → skip

        filter_value = filter_state[filter_widget_id]

        if isinstance(filter_value, list):
            rows = [r for r in rows if r.get(bound_field) in filter_value]
        elif isinstance(filter_value, dict) and 'start' in filter_value:
            # Date range filter
            rows = [
                r for r in rows
                if filter_value['start'] <= str(r.get(bound_field, '')) <= filter_value['end']
            ]
        else:
            rows = [r for r in rows if str(r.get(bound_field, '')) == str(filter_value)]

    result_data['rows'] = rows
    result_data['row_count'] = len(rows)
    return result_data
```

**Important:** Filters are applied after data is fetched from `analysis_results`. The server
does NOT re-run the analysis for each filter change — only the cached result set is filtered.
This means filter options must be pre-computed from the full result set and cached.

### 7.3 Filter Options Endpoint

Returns distinct values for a given column in an analysis result, used to populate filter
widget dropdown options:

```
GET /api/internal/v1/dashboards/<dashboard_id>/filter-options
Authorization: Bearer <access_token>
```

**Query parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `analysis_id` | ObjectId | Yes | The analysis to query |
| `node_id` | string | Yes | The output node UUID |
| `column` | string | Yes | The column to get distinct values for |
| `limit` | integer | No | Max distinct values to return (default: 200) |

**Response 200:**

```json
{
  "column": "department",
  "values": ["Cardiology", "Neurology", "Oncology"],
  "total_distinct": 3
}
```

Server logic:
1. Find latest completed run for the analysis
2. Load the `analysis_result` for the node
3. Extract distinct values for the column from `result.data.rows`
4. Sort alphabetically, apply limit
5. Cache result in Redis: key `filter_opts:{analysis_id}:{node_id}:{column}:{run_id}`, TTL 5 minutes

---

## 8. Built-in Widget Specifications

Each widget type is a `dashboard_widget` concept registered in `component_schemas`. All widget
types share common base properties. Below is the complete specification for each built-in type.

### 8.0 Common Widget Properties (all types)

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `title` | string | `""` | Widget title shown in a header bar |
| `show_title` | boolean | `true` | Whether to render the title bar |
| `title_font_size` | number | `16` | Title font size in px |
| `title_color` | string (hex) | `"#212121"` | Title text colour |
| `background_color` | string (hex) | `"#FFFFFF"` | Widget card background |
| `border_radius` | number | `8` | Corner radius in px |
| `border_width` | number | `1` | Border thickness in px |
| `border_color` | string (hex) | `"#E0E0E0"` | Border colour |
| `padding` | number | `16` | Internal padding in px |
| `show_loading_spinner` | boolean | `true` | Show spinner while data loads |
| `no_data_message` | string | `"No data available"` | Shown when widget has no data |

---

### 8.1 KPI Card (`kpi_card`)

Displays a single numeric value with optional comparison and trend indicator.

**API data format expected from analysis node (`kpi_value` output node):**

```json
{
  "output_type": "value",
  "data": {
    "value": 12345.67,
    "label": "Total Responses",
    "previous_value": 10890.0,
    "unit": "responses"
  }
}
```

**Widget-specific properties:**

| Property | Type | Default | Options/Notes |
|----------|------|---------|--------------|
| `value_format` | enum | `"number"` | `number`, `currency`, `percentage`, `compact` |
| `decimal_places` | integer | `0` | 0–4 decimal places |
| `prefix` | string | `""` | Text before value (e.g., `"₹"`) |
| `suffix` | string | `""` | Text after value (e.g., `"%"`) |
| `show_comparison` | boolean | `false` | Show delta vs previous_value |
| `comparison_label` | string | `"vs last period"` | Label next to delta |
| `positive_is_good` | boolean | `true` | If true, positive delta = green; if false, positive = red |
| `icon` | string | `""` | Material icon name or empty |
| `icon_color` | string (hex) | `"#1976D2"` | Icon colour |
| `value_font_size` | number | `36` | Font size of main value in px |
| `value_color` | string (hex) | `"#212121"` | Main value text colour |
| `color_scheme` | enum | `"default"` | `default`, `blue`, `green`, `red`, `purple`, `orange` |

**Rendering logic:**

1. If `value_format == "compact"`: format as 1.2K, 3.4M, etc.
2. If `value_format == "currency"`: use locale-aware formatting with prefix
3. If `show_comparison` and `previous_value` is present:
   - `delta = value - previous_value`
   - `delta_pct = ((delta) / previous_value) * 100`
   - Show `▲ 13.4% vs last period` (green) or `▼ 3.2% vs last period` (red)
   - Colour logic inverted if `positive_is_good = false`
4. Render icon (if set) using Flutter's `Icon` widget with `icon_color`

---

### 8.2 Bar Chart (`bar_chart`)

Renders a vertical or horizontal bar chart.

**API data format expected (from `bar_chart_data` output node):**

```json
{
  "output_type": "chart_data",
  "data": {
    "chart_type": "bar",
    "labels": ["Jan", "Feb", "Mar", "Apr"],
    "series": [
      {
        "name": "Submissions",
        "values": [120, 145, 98, 210],
        "color": "#1976D2"
      },
      {
        "name": "Approvals",
        "values": [90, 130, 85, 180],
        "color": "#388E3C"
      }
    ],
    "x_axis_label": "Month",
    "y_axis_label": "Count"
  }
}
```

**Widget-specific properties:**

| Property | Type | Default | Options/Notes |
|----------|------|---------|--------------|
| `orientation` | enum | `"vertical"` | `vertical`, `horizontal` |
| `stacked` | boolean | `false` | Stack series bars |
| `show_legend` | boolean | `true` | Display legend |
| `legend_position` | enum | `"bottom"` | `top`, `bottom`, `left`, `right` |
| `show_grid_lines` | boolean | `true` | Draw grid lines |
| `show_values_on_bars` | boolean | `false` | Show value labels on each bar |
| `bar_width_ratio` | number | `0.6` | Bar width as proportion of category width (0.1–1.0) |
| `color_palette` | array of hex strings | `["#1976D2","#388E3C","#F57C00","#7B1FA2"]` | Series colours (applied in order) |
| `x_axis_label` | string | `""` | Override x-axis label |
| `y_axis_label` | string | `""` | Override y-axis label |
| `animate` | boolean | `true` | Entry animation |

**Rendering logic:**

Use Flutter package `fl_chart` (or equivalent). Map `series[i].values[j]` to bar height at
`labels[j]` for series `i`. Apply `color_palette[i]` as bar colour (override `series[i].color`
if `color_palette` is explicitly set by user). Filter application (see §7.2) reduces the number
of data points shown.

---

### 8.3 Line Chart (`line_chart`)

Renders a line/area chart, typically for time-series data.

**API data format (from `line_chart_data` output node):**

```json
{
  "output_type": "chart_data",
  "data": {
    "chart_type": "line",
    "labels": ["2026-01", "2026-02", "2026-03"],
    "series": [
      {
        "name": "Responses",
        "values": [300, 450, 280],
        "color": "#1976D2"
      }
    ],
    "x_axis_label": "Month",
    "y_axis_label": "Count"
  }
}
```

**Widget-specific properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| `fill_area` | boolean | `false` | Fill area under line |
| `fill_opacity` | number | `0.2` | 0.0–1.0 |
| `show_dots` | boolean | `true` | Show data point dots |
| `dot_radius` | number | `4` | Dot radius in px |
| `line_width` | number | `2` | Line stroke width |
| `smooth` | boolean | `true` | Bezier curve interpolation |
| `show_legend` | boolean | `true` | |
| `legend_position` | enum | `"bottom"` | |
| `show_grid_lines` | boolean | `true` | |
| `color_palette` | array of hex | `["#1976D2","#388E3C"]` | |
| `animate` | boolean | `true` | |

---

### 8.4 Pie / Donut Chart (`pie_chart`)

Renders a pie or donut chart.

**API data format (from `pie_chart_data` output node):**

```json
{
  "output_type": "chart_data",
  "data": {
    "chart_type": "pie",
    "segments": [
      { "label": "Male", "value": 345, "color": "#1976D2" },
      { "label": "Female", "value": 289, "color": "#E91E63" },
      { "label": "Other", "value": 42, "color": "#9E9E9E" }
    ]
  }
}
```

**Widget-specific properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| `donut` | boolean | `false` | Render as donut (hollow centre) |
| `donut_hole_ratio` | number | `0.5` | Hole size as ratio of radius (0.2–0.9) |
| `center_label` | string | `""` | Text shown in donut centre (only if `donut=true`) |
| `show_legend` | boolean | `true` | |
| `legend_position` | enum | `"right"` | |
| `show_percentage_labels` | boolean | `true` | Show % on each slice |
| `show_value_labels` | boolean | `false` | Show raw value on each slice |
| `min_slice_percentage` | number | `2.0` | Slices below this % are merged into "Other" |
| `color_palette` | array of hex | `["#1976D2","#E91E63","#388E3C","..."]` | Applied in order |
| `animate` | boolean | `true` | |

---

### 8.5 Data Table (`data_table`)

Renders a scrollable, sortable data table.

**API data format (from `table_output` output node):**

```json
{
  "output_type": "table",
  "data": {
    "rows": [
      { "patient_id": "P001", "name": "John Doe", "score": 85 },
      { "patient_id": "P002", "name": "Jane Smith", "score": 92 }
    ],
    "row_count": 2,
    "columns": [
      { "name": "patient_id", "label": "Patient ID", "type": "string" },
      { "name": "name", "label": "Name", "type": "string" },
      { "name": "score", "label": "Score", "type": "number" }
    ]
  }
}
```

**Widget-specific properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| `show_row_numbers` | boolean | `false` | Prepend row index column |
| `striped_rows` | boolean | `true` | Alternate row background colour |
| `row_height` | number | `48` | Row height in px |
| `header_background` | string (hex) | `"#F5F5F5"` | Header row background |
| `header_text_color` | string (hex) | `"#424242"` | Header text colour |
| `font_size` | number | `13` | Data cell font size |
| `allow_sort` | boolean | `true` | Click-to-sort column headers |
| `default_sort_column` | string | `""` | Column name to sort by default |
| `default_sort_direction` | enum | `"asc"` | `asc`, `desc` |
| `column_overrides` | array of objects | `[]` | Per-column config: `{ "name": "score", "width": 100, "label": "Custom Label", "hidden": false }` |
| `max_rows_display` | number | `100` | Maximum rows to show (pagination) |
| `show_pagination` | boolean | `true` | Show page navigation below table |
| `show_search` | boolean | `false` | Show inline search/filter bar |
| `wrap_text` | boolean | `false` | Allow text wrap in cells |

**Rendering notes:**
- Sorting is **client-side** on the loaded row set (not re-fetching from server)
- Pagination is client-side within the loaded `max_rows_display` rows
- `show_search` filters rows client-side by string match across all visible columns

---

### 8.6 Text / Label Widget (`text_label`)

Displays static text, markdown, or dynamic values from a KPI analysis result.

**API data format:** Optional. If `data_binding` is set to a `kpi_value` node, the text template
can reference `{{value}}`. If no binding, text is fully static.

```json
{
  "output_type": "value",
  "data": { "value": 12345 }
}
```

**Widget-specific properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| `text` | string | `"Label"` | The text content; supports `{{value}}` placeholder |
| `font_size` | number | `16` | px |
| `font_weight` | enum | `"regular"` | `thin`, `light`, `regular`, `medium`, `semibold`, `bold`, `heavy` |
| `text_color` | string (hex) | `"#212121"` | |
| `text_align` | enum | `"left"` | `left`, `center`, `right`, `justify` |
| `allow_markdown` | boolean | `false` | Render text as markdown |
| `value_format` | enum | `"number"` | Same options as KPI card (applied to `{{value}}`) |
| `prefix` | string | `""` | |
| `suffix` | string | `""` | |

---

### 8.7 Image Widget (`image_widget`)

Displays a static image from URL or an uploaded asset.

**No data binding.** This is a purely static/display widget.

**Widget-specific properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| `image_url` | string | `""` | HTTPS URL or relative path to uploaded image |
| `fit` | enum | `"contain"` | `contain`, `cover`, `fill`, `none`, `scale_down` |
| `alt_text` | string | `""` | Accessibility alt text |
| `link_url` | string | `""` | If set, image is clickable and navigates to this URL |
| `border_radius` | number | `0` | Additional corner radius for image itself |

**Rendering notes:** Images are loaded via Flutter's `Image.network` with `cached_network_image`
for caching. If `image_url` is empty, show a placeholder icon.

---

### 8.8 Filter Widget (`filter_widget`)

An interactive UI control that other widgets listen to via the FilterBinding mechanism.

**No data binding to an analysis node.** The filter widget is the *source* of filtering, not a
consumer of analysis data. However, it can optionally fetch its option list dynamically
(see §7.3).

**Widget-specific properties:**

| Property | Type | Default | Options/Notes |
|----------|------|---------|--------------|
| `filter_type` | enum | `"dropdown"` | `dropdown`, `multi_select`, `date_picker`, `date_range_picker`, `text_search`, `radio_group` |
| `label` | string | `"Filter"` | Filter label text |
| `placeholder` | string | `"Select..."` | Shown when no value selected |
| `options_source` | enum | `"static"` | `static`, `dynamic` |
| `static_options` | array of strings | `[]` | Used when `options_source="static"` |
| `dynamic_analysis_id` | ObjectId | `null` | Analysis to fetch options from |
| `dynamic_node_id` | string | `null` | Node ID within the analysis |
| `dynamic_column` | string | `null` | Column to get distinct values from |
| `default_value` | any | `null` | Pre-selected value on load |
| `allow_clear` | boolean | `true` | Show an "All / Clear" option |
| `clear_label` | string | `"All"` | Label for the clear/all option |
| `multi_select` | boolean | `false` | Deprecated — use `filter_type="multi_select"` |

**How filter state flows (client-side):**

1. User interacts with filter widget → updates local `filterState[widget.id] = newValue`
2. Client triggers a data refresh for all widgets that have a `filters[]` entry with
   `filter_widget_id == this.widget.id`
3. Refresh call includes `filter_state` query param with the updated state
4. Server applies filters (§7.2) and returns filtered data
5. Affected widgets update their display

---

### 8.9 Divider / Spacer Widget (`divider_widget`)

A visual separator or empty spacer for layout purposes.

**No data binding.**

**Widget-specific properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| `style` | enum | `"divider"` | `divider`, `spacer` |
| `direction` | enum | `"horizontal"` | `horizontal`, `vertical` |
| `line_color` | string (hex) | `"#E0E0E0"` | Only for `style="divider"` |
| `line_thickness` | number | `1` | px |
| `line_style` | enum | `"solid"` | `solid`, `dashed`, `dotted` |

---

## 9. Flutter: Free-Form Canvas Implementation

**Feature folder:** `frontend/lib/features/dashboard_builder/`

### 9.1 File Structure

```
dashboard_builder/
  dashboard_builder_page.dart          ← top-level page with mode switcher
  canvas/
    dashboard_canvas.dart              ← main canvas widget
    canvas_controller.dart             ← Riverpod StateNotifier for canvas state
    canvas_grid.dart                   ← background grid rendering
    canvas_ruler.dart                  ← optional ruler overlay
    widget_placeholder.dart            ← drag target placeholder
  widgets/
    draggable_widget_wrapper.dart      ← drag + resize + select wrapper
    widget_renderer.dart               ← routes to specific widget type renderer
    kpi_card_widget.dart
    bar_chart_widget.dart
    line_chart_widget.dart
    pie_chart_widget.dart
    data_table_widget.dart
    text_label_widget.dart
    image_widget.dart
    filter_widget_widget.dart          ← the filter control widget
    divider_widget.dart
  sidebar/
    widget_library_sidebar.dart        ← widget palette sidebar
    widget_category.dart
  properties/
    property_panel.dart                ← right panel for selected widget
    binding_panel.dart                 ← data binding sub-panel
    filter_binding_panel.dart
  providers/
    dashboard_provider.dart
    canvas_state_provider.dart
    widget_data_provider.dart
    filter_state_provider.dart
  models/
    dashboard_model.dart
    widget_model.dart
    widget_data_model.dart
    filter_state_model.dart
  services/
    dashboard_service.dart
```

### 9.2 Canvas State Model

```dart
// canvas_state_provider.dart
@freezed
class CanvasState with _$CanvasState {
  const factory CanvasState({
    required String dashboardId,
    required double canvasWidth,
    required double canvasHeight,
    required String backgroundColor,
    required List<WidgetModel> widgets,
    required String? selectedWidgetId,
    required bool isDirty,   // true if unsaved changes exist
    required bool isLoading,
    required CanvasMode mode,  // edit | preview
    required double zoomLevel,  // 0.25 – 2.0, default 1.0
    required Offset panOffset,
  }) = _CanvasState;
}

enum CanvasMode { edit, preview }
```

### 9.3 Canvas Widget Implementation

The canvas uses a `Stack` inside an `InteractiveViewer` for pan and zoom:

```dart
// dashboard_canvas.dart (structure)

class DashboardCanvas extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(canvasStateProvider);

    return Stack(
      children: [
        // 1. Background: canvas background colour + optional grid
        CanvasBackground(
          color: Color(int.parse(state.backgroundColor.replaceAll('#', '0xFF'))),
          showGrid: state.mode == CanvasMode.edit,
        ),

        // 2. All widgets rendered in z-index order
        ...state.widgets
            .sorted((a, b) => a.zIndex.compareTo(b.zIndex))
            .map((w) => DraggableWidgetWrapper(widget: w)),

        // 3. Edit mode overlay: selection box, alignment guides
        if (state.mode == CanvasMode.edit) ...[
          SelectionOverlay(selectedWidgetId: state.selectedWidgetId),
          AlignmentGuides(),
        ],
      ],
    );
  }
}
```

The outer `InteractiveViewer`:

```dart
InteractiveViewer(
  boundaryMargin: const EdgeInsets.all(200),
  minScale: 0.25,
  maxScale: 2.0,
  onInteractionUpdate: (details) {
    ref.read(canvasStateProvider.notifier).updateZoom(details.scale);
    ref.read(canvasStateProvider.notifier).updatePan(details.focalPoint);
  },
  child: SizedBox(
    width: canvasWidth,
    height: canvasHeight,
    child: DashboardCanvas(),
  ),
)
```

### 9.4 Widget Drag and Move

Each widget is wrapped in `DraggableWidgetWrapper` which uses a `GestureDetector` to handle
drag (move) and a resize handle in each corner.

```dart
// draggable_widget_wrapper.dart (structure)

class DraggableWidgetWrapper extends ConsumerStatefulWidget {
  final WidgetModel widget;

  @override
  ConsumerState<DraggableWidgetWrapper> createState() => _DraggableWidgetWrapperState();
}

class _DraggableWidgetWrapperState extends ConsumerState<DraggableWidgetWrapper> {
  Offset _dragStartOffset = Offset.zero;
  Offset _widgetStartPosition = Offset.zero;

  @override
  Widget build(BuildContext context) {
    final isSelected = ref.watch(
      canvasStateProvider.select((s) => s.selectedWidgetId == widget.widget.id)
    );
    final isLocked = widget.widget.isLocked;
    final mode = ref.watch(canvasStateProvider.select((s) => s.mode));

    return Positioned(
      left: widget.widget.position.x,
      top: widget.widget.position.y,
      child: GestureDetector(
        onTap: () {
          if (mode == CanvasMode.edit) {
            ref.read(canvasStateProvider.notifier).selectWidget(widget.widget.id);
          }
        },
        onPanStart: mode == CanvasMode.edit && !isLocked
            ? (details) {
                _dragStartOffset = details.globalPosition;
                _widgetStartPosition = Offset(
                    widget.widget.position.x, widget.widget.position.y);
              }
            : null,
        onPanUpdate: mode == CanvasMode.edit && !isLocked
            ? (details) {
                final delta = details.globalPosition - _dragStartOffset;
                final newX = (_widgetStartPosition.dx + delta.dx).clamp(0.0, canvasWidth - widget.widget.size.width);
                final newY = (_widgetStartPosition.dy + delta.dy).clamp(0.0, canvasHeight - widget.widget.size.height);
                ref.read(canvasStateProvider.notifier).moveWidget(
                  widget.widget.id, newX, newY,
                );
              }
            : null,
        child: Stack(
          children: [
            // Main widget content
            SizedBox(
              width: widget.widget.size.width,
              height: widget.widget.size.height,
              child: WidgetRenderer(widget: widget.widget),
            ),
            // Selection border + resize handles (edit mode only)
            if (mode == CanvasMode.edit && isSelected)
              SelectionBorder(widget: widget.widget),
          ],
        ),
      ),
    );
  }
}
```

### 9.5 Widget Resize

Resize handles appear on the 8 cardinal and diagonal corners of the selection border when a
widget is selected in edit mode.

```dart
// Selection border with resize handles
// Handles: topLeft, top, topRight, right, bottomRight, bottom, bottomLeft, left

class ResizeHandle extends StatelessWidget {
  final ResizeDirection direction;
  final WidgetModel widget;

  // Minimum size enforced: 20x20 px
  static const double minWidth = 20;
  static const double minHeight = 20;
}
```

Resize logic (pseudo-code):

```
onPanUpdate(direction, delta):
  newWidth = clamp(originalWidth + delta.x * widthMultiplier, minWidth, canvasWidth)
  newHeight = clamp(originalHeight + delta.y * heightMultiplier, minHeight, canvasHeight)
  newX = originalX + (direction is left-anchored ? delta.x : 0)
  newY = originalY + (direction is top-anchored ? delta.y : 0)
  canvasNotifier.resizeWidget(widgetId, newX, newY, newWidth, newHeight)
```

### 9.6 Z-Index (Layering)

Z-index is managed by the canvas state. Widgets are rendered in z-index order using a
`sorted()` call on the widgets list. Editing operations:

- **Bring to Front:** set `z_index = max(all z_indexes) + 1`
- **Send to Back:** set `z_index = min(all z_indexes) - 1`
- **Bring Forward:** swap z_index with the widget immediately above
- **Send Backward:** swap z_index with the widget immediately below

These actions are available via right-click context menu on selected widget (in edit mode) and
via toolbar buttons.

### 9.7 Grid Snapping

In edit mode, a configurable snap-to-grid feature aligns widget positions to a grid.

```dart
// Grid settings (stored in local UI preferences, not in DB)
static const int defaultGridSize = 8;  // px

double snapToGrid(double value, int gridSize) {
  return (value / gridSize).round() * gridSize.toDouble();
}
```

Snapping is applied during drag (`onPanUpdate`) when snap is enabled (toggle button in toolbar).

### 9.8 Multi-Widget Selection

Hold `Shift` and click widgets to add them to the selection. Multi-selection enables:
- Group move
- Group delete
- Align operations (align left/center/right/top/middle/bottom)

```dart
// Canvas state supports multi-selection
required Set<String> selectedWidgetIds,
```

### 9.9 Alignment Guides

When dragging a widget in edit mode, show dashed alignment guide lines when the widget's edge
or centre aligns with another widget's edge or centre (within 4px tolerance).

Alignment guide rendering: overlay `CustomPaint` drawing horizontal and vertical dashed lines.

### 9.10 Canvas Toolbar

Positioned at the top of the dashboard builder page:

```
[Dashboard Name (editable)] | [Undo] [Redo] | [Zoom: 75%] | [Grid ⊞] [Snap ◫] |
[Layers ☰] | [Share ⟨⟩] | [Preview ▶] | [Save ✓] | [Export PDF ⬇]
```

- **Undo/Redo:** Managed by an undo stack in `canvas_state_provider` (max 50 states)
- **Zoom:** Dropdown with presets: 50%, 75%, 100%, 125%, 150%; also + / - buttons
- **Grid:** Toggle canvas grid visibility
- **Snap:** Toggle grid snapping
- **Layers:** Opens a layers panel showing widget z-index stack
- **Share:** Opens sharing dialog (§16)
- **Preview:** Switches to preview mode (§17)
- **Save:** Triggers PUT canvas save API; shows loading indicator; disabled if `!isDirty`
- **Export PDF:** Triggers PDF export (§18)

---

## 10. Flutter: Widget Library Sidebar

The widget library sidebar is shown on the left side of the canvas in edit mode.

**Location:** `frontend/lib/features/dashboard_builder/sidebar/widget_library_sidebar.dart`

### 10.1 Sidebar Structure

```
┌─────────────────────┐
│ 🔍 Search widgets   │
├─────────────────────┤
│ ▸ Charts            │
│   📊 Bar Chart      │
│   📈 Line Chart     │
│   🥧 Pie Chart      │
├─────────────────────┤
│ ▸ Data Display      │
│   📋 KPI Card       │
│   📄 Data Table     │
├─────────────────────┤
│ ▸ Content           │
│   🔤 Text/Label     │
│   🖼 Image          │
├─────────────────────┤
│ ▸ Controls          │
│   🔽 Filter Widget  │
├─────────────────────┤
│ ▸ Layout            │
│   ─ Divider         │
└─────────────────────┘
```

**Widget categories:**

| Category | Widget Types |
|----------|-------------|
| Charts | `bar_chart`, `line_chart`, `pie_chart` |
| Data Display | `kpi_card`, `data_table` |
| Content | `text_label`, `image_widget` |
| Controls | `filter_widget` |
| Layout | `divider_widget` |

### 10.2 Adding a Widget from the Sidebar

Two interaction methods:

**Method 1: Drag from sidebar to canvas**

```dart
// Widget in sidebar
LongPressDraggable<String>(
  data: 'kpi_card',   // widget type identifier
  feedback: WidgetDragPreview(type: 'kpi_card'),
  child: WidgetLibraryItem(type: 'kpi_card'),
)

// Canvas as DragTarget
DragTarget<String>(
  onAcceptWithDetails: (details) {
    final localPosition = canvasCoordinateFromGlobal(details.offset);
    ref.read(canvasStateProvider.notifier).addWidget(
      type: details.data,
      position: Offset(localPosition.dx, localPosition.dy),
    );
  },
  builder: (context, candidateData, rejectedData) => dashboardCanvas,
)
```

**Method 2: Click to add at centre of current viewport**

```dart
onTap: () {
  final viewportCentre = Offset(canvasWidth / 2, canvasHeight / 2);
  ref.read(canvasStateProvider.notifier).addWidget(
    type: 'kpi_card',
    position: viewportCentre,
  );
}
```

### 10.3 New Widget Default Sizes

When a widget is added, use these defaults:

| Widget Type | Default Width | Default Height |
|-------------|--------------|----------------|
| `kpi_card` | 280 | 140 |
| `bar_chart` | 480 | 320 |
| `line_chart` | 480 | 320 |
| `pie_chart` | 340 | 320 |
| `data_table` | 600 | 400 |
| `text_label` | 240 | 60 |
| `image_widget` | 300 | 200 |
| `filter_widget` | 240 | 56 |
| `divider_widget` | 400 | 4 |

New widgets are assigned `z_index = max(existing z_indexes) + 1`.

### 10.4 Plugin-Provided Widgets

The sidebar must also display widgets provided by installed plugins with
`concept_targets = ["dashboard_widget"]`. Load plugin component schemas from the API:

```
GET /api/internal/v1/plugins/components?concept=dashboard_widget
```

Plugin widgets appear in a "Plugins" category at the bottom of the sidebar.

---

## 11. Flutter: Widget Property Panel

The right-side property panel shows properties for the currently selected widget.

**Location:** `frontend/lib/features/dashboard_builder/properties/property_panel.dart`

### 11.1 Panel Layout

```
┌──────────────────────────────┐
│ 📊 Bar Chart                 │  ← widget type name
│ [widget.id truncated]        │
├──────────────────────────────┤
│ TABS: [General] [Data] [Style]│
├──────────────────────────────┤
│ General Tab:                 │
│  Title: [_______________]    │
│  Show Title: [✓]             │
│  Locked: [ ]                 │
│                              │
│ Position & Size:             │
│  X: [40___] Y: [40___]       │
│  W: [480__] H: [320__]       │
│  Z: [1____]                  │
├──────────────────────────────┤
│ [Delete Widget]              │
└──────────────────────────────┘
```

### 11.2 Tab: General

Shared fields across all widgets:
- Title (text field)
- Show Title (checkbox)
- Background Colour (colour picker)
- Border Radius (number input)
- Border Width + Colour
- Padding
- Locked (checkbox — prevents move/resize)
- No Data Message (text field)

Position & Size:
- X, Y: numeric inputs; changes applied immediately (snap-aware)
- Width, Height: numeric inputs
- Z-Index: numeric input + "Bring to Front" / "Send to Back" buttons

### 11.3 Tab: Data (Data Binding)

See §12 for the full Data Binding UI specification.

### 11.4 Tab: Style

Widget-type-specific styling properties. For each widget type, render the relevant properties
as a list of form controls:

**Control types for property values:**

| Property Type | Flutter Control |
|--------------|----------------|
| `string` | `TextFormField` |
| `number` | `TextFormField` with `TextInputType.numberWithOptions` |
| `boolean` | `Switch` |
| `color` | Colour swatch button → opens `ColorPicker` dialog |
| `enum` | `DropdownButton<String>` |
| `array of strings` | Chips with add/remove |
| `array of hex colors` | Colour swatches with add/remove |

Properties are grouped by their `group` field from the component schema. Groups are rendered as
`ExpansionTile` sections.

### 11.5 Empty State

When no widget is selected:

```
┌──────────────────────────────┐
│                              │
│   Select a widget to edit    │
│   its properties             │
│                              │
│   Or drag a widget from      │
│   the sidebar to get started │
│                              │
└──────────────────────────────┘
```

---

## 12. Flutter: Data Binding UI

The Data tab of the property panel is the data binding UI.

**Location:** `frontend/lib/features/dashboard_builder/properties/binding_panel.dart`

### 12.1 Binding Panel Layout

```
┌──────────────────────────────┐
│ DATA BINDING                 │
├──────────────────────────────┤
│ Analysis:                    │
│ [Select Analysis ▼]          │
│   • Responses Analysis       │ ← dropdown of linked_analysis_ids + others in project
│   • Surgical Outcomes        │
│   • ─────────────────────    │
│   • Browse all analyses...   │
│                              │
│ Output Node:                 │
│ [Select Output Node ▼]       │
│   • Total Count (KPI)        │ ← filtered to compatible output types
│   • Monthly Trend (Line)     │
│                              │
│ Refresh Mode:                │
│ ○ With Dashboard             │
│ ○ Independent                │
│   Interval: [___30___] secs  │
│ ○ Never                      │
│                              │
│ [Remove Binding]             │
└──────────────────────────────┘
```

### 12.2 Analysis Dropdown

**Data loading:**

```dart
// Loads all analyses accessible to the user in the current project
final analysesProvider = FutureProvider.family<List<AnalysisSummary>, String>(
  (ref, projectId) async {
    return ref.read(dashboardServiceProvider).getProjectAnalyses(projectId);
  }
);
```

Analyses already linked to the dashboard are shown first with a "● Linked" badge.
All other accessible analyses in the project are shown below a separator.
"Browse all analyses..." opens a search dialog.

### 12.3 Output Node Dropdown

Populated after an analysis is selected. Shows only **output-type nodes**:
`table_output`, `kpi_value`, `bar_chart_data`, `line_chart_data`, `pie_chart_data`.

**Compatibility filter:** Some widgets only accept certain node types:

| Widget Type | Compatible Output Node Types |
|-------------|------------------------------|
| `kpi_card` | `kpi_value` |
| `bar_chart` | `bar_chart_data` |
| `line_chart` | `line_chart_data` |
| `pie_chart` | `pie_chart_data` |
| `data_table` | `table_output` |
| `text_label` | `kpi_value` (optional) |
| `filter_widget` | none (uses dynamic options from any node) |

Incompatible nodes are greyed out in the dropdown with a tooltip explaining the incompatibility.

### 12.4 Refresh Mode

Three options presented as radio buttons:
- **With Dashboard:** widget refreshes on the same cycle as the dashboard (default)
- **Independent:** widget refreshes on its own schedule; shows interval input (min 10s)
- **Never:** widget data is frozen at page load; never re-fetched

### 12.5 Binding Validation

When binding is set:
1. Show a preview section below the binding panel:

```
┌──────────────────────────────┐
│ DATA PREVIEW                 │
│ Last run: 2026-06-07 09:30   │
│ Status: ✓ Completed          │
│                              │
│ [Preview data]               │ ← loads widget_data for just this widget
└──────────────────────────────┘
```

2. If incompatible node type: show warning banner in red

---

## 13. Flutter: Filter Widget Interaction

### 13.1 Filter State Provider

```dart
// filter_state_provider.dart
// Holds the current value for every filter widget on the canvas

final filterStateProvider = StateNotifierProvider<FilterStateNotifier, Map<String, dynamic>>(
  (ref) => FilterStateNotifier(),
);

class FilterStateNotifier extends StateNotifier<Map<String, dynamic>> {
  FilterStateNotifier() : super({});

  void updateFilter(String filterWidgetId, dynamic value) {
    state = { ...state, filterWidgetId: value };
  }

  void clearFilter(String filterWidgetId) {
    final newState = Map<String, dynamic>.from(state);
    newState.remove(filterWidgetId);
    state = newState;
  }

  void clearAll() {
    state = {};
  }
}
```

### 13.2 Filter Widget Rendering

The filter widget renders a `DropdownButton`, `MultiSelectChip`, `TextField`, or `DateRangePicker`
based on `filter_type` property.

```dart
// filter_widget_widget.dart

class FilterWidgetRenderer extends ConsumerWidget {
  final WidgetModel widget;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filterType = widget.properties['filter_type'] as String;
    final filterState = ref.watch(filterStateProvider);
    final currentValue = filterState[widget.id];

    return switch (filterType) {
      'dropdown' => _buildDropdown(context, ref, currentValue),
      'multi_select' => _buildMultiSelect(context, ref, currentValue),
      'date_picker' => _buildDatePicker(context, ref, currentValue),
      'date_range_picker' => _buildDateRangePicker(context, ref, currentValue),
      'text_search' => _buildTextSearch(context, ref, currentValue),
      'radio_group' => _buildRadioGroup(context, ref, currentValue),
      _ => const SizedBox.shrink(),
    };
  }

  void _onValueChanged(WidgetRef ref, dynamic newValue) {
    ref.read(filterStateProvider.notifier).updateFilter(widget.id, newValue);
    // Trigger data refresh for all widgets that bind to this filter
    ref.read(widgetDataRefreshProvider.notifier).refreshFilterDependents(widget.id);
  }
}
```

### 13.3 Propagation: Which Widgets Refresh

When a filter value changes:

```dart
// widget_data_provider.dart

void refreshFilterDependents(String filterWidgetId) {
  final canvas = ref.read(canvasStateProvider).widgets;
  final affectedWidgets = canvas.where(
    (w) => w.filters.any((f) => f.filterWidgetId == filterWidgetId)
  );
  for (final w in affectedWidgets) {
    refreshWidgetData(w.id);
  }
}
```

### 13.4 Dynamic Options Loading

If `options_source == "dynamic"`, the filter widget loads its options from the API on mount:

```dart
final filterOptionsProvider = FutureProvider.family<List<String>, FilterOptionsKey>(
  (ref, key) async => ref.read(dashboardServiceProvider).getFilterOptions(
    dashboardId: key.dashboardId,
    analysisId: key.analysisId,
    nodeId: key.nodeId,
    column: key.column,
  ),
);
```

Show a loading indicator in the filter widget while options are being fetched.

---

## 14. Flutter: Auto-Refresh Implementation

### 14.1 Refresh Timer

```dart
// widget_data_provider.dart

class WidgetDataNotifier extends StateNotifier<Map<String, WidgetDataState>> {
  Timer? _refreshTimer;
  final Ref _ref;

  void startAutoRefresh(int intervalSeconds) {
    _refreshTimer?.cancel();
    _refreshTimer = Timer.periodic(Duration(seconds: intervalSeconds), (_) {
      refreshAll();
    });
  }

  void stopAutoRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = null;
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> refreshAll() async {
    final filterState = _ref.read(filterStateProvider);
    final result = await _ref.read(dashboardServiceProvider)
        .fetchDashboardData(dashboardId: dashboardId, filterState: filterState);
    state = _buildStateFromResponse(result);
  }
}
```

### 14.2 WebSocket Trigger

```dart
// In dashboard_builder_page.dart, initState or onMounted:

final socket = ref.read(socketIoProvider);
socket.on('analysis_run_completed', (data) {
  final completedAnalysisId = data['analysis_id'];
  final linkedIds = ref.read(dashboardProvider).linkedAnalysisIds;
  if (linkedIds.contains(completedAnalysisId)) {
    // A linked analysis has new results — refresh immediately
    ref.read(widgetDataProvider.notifier).refreshAll();
  }
});
```

### 14.3 Independent Widget Refresh

Each widget with `refresh_mode == "independent"` manages its own `Timer.periodic`:

```dart
// In DraggableWidgetWrapper
@override
void initState() {
  super.initState();
  if (widget.widget.dataBinding?.refreshMode == RefreshMode.independent) {
    final interval = widget.widget.dataBinding!.independentIntervalSeconds ?? 60;
    _timer = Timer.periodic(Duration(seconds: interval), (_) {
      ref.read(widgetDataProvider.notifier).refreshWidgetData(widget.widget.id);
    });
  }
}
```

### 14.4 Visibility-Aware Refresh

Pause auto-refresh when the app goes to background (using `WidgetsBindingObserver`):

```dart
class _DashboardPageState extends ConsumerState<DashboardBuilderPage>
    with WidgetsBindingObserver {

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused) {
      ref.read(widgetDataProvider.notifier).stopAutoRefresh();
    } else if (state == AppLifecycleState.resumed) {
      final settings = ref.read(dashboardProvider).settings;
      if (settings.autoRefresh) {
        ref.read(widgetDataProvider.notifier).startAutoRefresh(
          settings.refreshIntervalSeconds,
        );
      }
    }
  }
}
```

---

## 15. Flutter: Public Dashboard View

**Route:** `/public/dashboard/:token` (accessible without login)

**Location:** `frontend/lib/features/dashboard_builder/public_dashboard_page.dart`

### 15.1 Public View Behaviour

- No authentication required; JWT token is NOT sent with requests
- Canvas is rendered in **preview mode** (no edit controls, no sidebar, no toolbar)
- Auto-refresh works using the public polling endpoint (`/api/v1/public/dashboards/<token>/data`)
- Filter widgets are interactive (filter state is client-side only)
- Top bar shows: dashboard name + org logo (if configured) + "Powered by Form Builder" attribution

### 15.2 Page Load Sequence

1. Parse `token` from route
2. Call `GET /api/v1/public/dashboards/<token>` (no auth header)
3. On success: render canvas with widget data
4. On 404: show "Dashboard not found or access revoked" error page
5. Start auto-refresh timer if `settings.auto_refresh == true`

### 15.3 Responsive Layout

The public dashboard view is responsive:
- **Desktop:** Full canvas at 100% zoom with scrolling
- **Tablet (768–1279px):** Canvas scaled to fit viewport width, vertical scroll
- **Mobile (<768px):** Canvas scaled to 50% or less; widgets may be shown in a linearized
  vertical list (alternative "mobile layout" mode if canvas width > 1200px)

Mobile linearization algorithm:
1. Sort widgets by `position.y` then `position.x`
2. Render each widget at full viewport width in vertical order
3. Filters rendered as a collapsible panel at the top

### 15.4 Public View Security

- `data_binding` details are stripped from the response (see §4.3)
- No org/project IDs are exposed
- No user information is exposed
- If the dashboard contains sensitive data (org_admin has no control over what is on the canvas),
  this is by design — the org_admin chose to make the dashboard public

---

## 16. Flutter: Dashboard Sharing Dialog

**Location:** `frontend/lib/features/dashboard_builder/sharing_dialog.dart`

Opened from the "Share" toolbar button.

### 16.1 Dialog Layout

```
┌──────────────────────────────────────────┐
│ Share Dashboard                      [✕] │
├──────────────────────────────────────────┤
│ INTERNAL SHARING                         │
│ This dashboard is visible to all         │
│ members of your project.                 │
│                                          │
│ PUBLIC SHARING                           │
│ ○ Private (only project members)         │
│ ● Public (anyone with the link)          │
│                                          │
│ Public Link:                             │
│ https://platform.aiims.edu/public/       │
│ dashboard/550e8400-e29b-...              │
│ [Copy Link]  [Open in Browser]           │
│                                          │
│ ⚠️  Anyone with this link can view       │
│ this dashboard without logging in.       │
│                                          │
│ [Revoke Public Access]                   │
│                                          │
│ AUTO-REFRESH (for public viewers)        │
│ ○ Disabled                               │
│ ● Every [60] seconds                     │
│                                          │
│                              [Close]     │
└──────────────────────────────────────────┘
```

### 16.2 State and Actions

| Action | API Call |
|--------|---------|
| Toggle public ON | `POST /dashboards/<id>/public-token` |
| Toggle public OFF | `DELETE /dashboards/<id>/public-token` |
| Copy link | Clipboard API; copies `public_url` |
| Open in browser | `launchUrl(Uri.parse(public_url))` |
| Change auto-refresh | `PATCH /dashboards/<id>` with updated `settings` |

Show loading spinner during API calls; disable controls while pending.

---

## 17. Flutter: Edit Mode vs Preview Mode

### 17.1 Mode Toggle

The toolbar contains a **Preview** button that toggles between edit and preview mode.
Mode is tracked in `CanvasState.mode`:

```dart
enum CanvasMode { edit, preview }
```

### 17.2 Edit Mode Features

| Feature | Description |
|---------|-------------|
| Widget sidebar | Visible on left |
| Property panel | Visible on right |
| Drag to move | Enabled |
| Resize handles | Visible |
| Selection border | Shown on click |
| Context menu | Right-click → z-order, delete, duplicate |
| Grid + snap | Toggleable |
| Canvas pan/zoom | Via InteractiveViewer |
| Save button | Enabled when `isDirty` |
| Filter widgets | Interactive (changes apply to edit preview) |

### 17.3 Preview Mode Features

| Feature | Description |
|---------|-------------|
| Widget sidebar | Hidden |
| Property panel | Hidden |
| Drag to move | Disabled |
| Resize handles | Hidden |
| Selection border | Never shown |
| Context menu | Disabled |
| Grid | Hidden |
| Canvas pan/zoom | Enabled (view only) |
| Filter widgets | Fully interactive |
| Auto-refresh | Active (if configured) |
| "Edit" button | Shown in toolbar to return to edit mode |

### 17.4 Unsaved Changes Warning

Switching from edit mode with unsaved changes (`isDirty == true`) shows a dialog:

```
Unsaved Changes
You have unsaved changes to this dashboard.
Do you want to save before switching to preview?

[Cancel] [Discard] [Save & Preview]
```

---

## 18. Dashboard PDF Export

### 18.1 Server-Side PDF Generation

PDF generation is handled entirely server-side using **WeasyPrint** (consistent with the tech
stack decision from CONTEXT.md §3).

**Celery task:** `backend/app/workers/export_tasks.py` → `generate_dashboard_pdf`

```
POST /api/internal/v1/dashboards/<dashboard_id>/export/pdf
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "filter_state": {},
  "include_snapshot": true,
  "page_size": "A4",
  "orientation": "landscape",
  "title": "Dashboard Report — June 2026"
}
```

**Request fields:**

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `filter_state` | object | `{}` | Active filter values to bake in |
| `include_snapshot` | boolean | `true` | Whether to save a snapshot alongside the PDF |
| `page_size` | enum | `"A4"` | `A4`, `A3`, `Letter`, `Legal` |
| `orientation` | enum | `"landscape"` | `landscape`, `portrait` |
| `title` | string | dashboard name | Custom title on PDF cover |

**Response 202 (Accepted — task queued):**

```json
{
  "export_id": "ObjectId string",
  "status": "queued",
  "poll_url": "/api/internal/v1/dashboards/<id>/export/<export_id>/status"
}
```

### 18.2 PDF Generation Task Logic

Stored as a new collection: `dashboard_exports`

```json
{
  "_id": "ObjectId",
  "dashboard_id": "ObjectId",
  "org_id": "ObjectId",
  "status": "queued | generating | ready | failed",
  "file_path": "string (relative path in UPLOADS_ROOT)",
  "file_size_bytes": "number",
  "expires_at": "ISODate (7 days from creation)",
  "created_at": "ISODate",
  "created_by": "ObjectId",
  "celery_task_id": "string"
}
```

**Task execution steps:**

1. Load dashboard + resolve all widget data (using `filter_state` from the request)
2. Render an HTML representation of the dashboard:
   - Use a Jinja2 HTML template: `backend/app/templates/dashboard_export.html`
   - Render each widget as an HTML/CSS element (charts as SVG via a charting library)
   - Apply dashboard `background_color` and widget positions as CSS absolute positioning
3. Convert HTML to PDF using WeasyPrint:
   ```python
   from weasyprint import HTML
   pdf_bytes = HTML(string=html_content, base_url=base_url).write_pdf()
   ```
4. Save PDF to `UPLOADS_ROOT/dashboard_exports/<dashboard_id>/<export_id>.pdf`
5. Update `dashboard_exports` status to `ready`, set `file_path` and `file_size_bytes`
6. Optionally create a snapshot (§5.1)

**Chart rendering in PDF:** Charts are rendered server-side as SVG using the `matplotlib`
library (already available in the Python ecosystem). The SVG is embedded inline in the HTML.
For each chart widget, the task calls:

```python
def render_chart_to_svg(chart_type: str, data: dict) -> str:
    """Returns an SVG string for the given chart type and data."""
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # non-interactive backend
    # ... build figure based on chart_type and data dict
    # ... return fig as SVG string via io.StringIO
```

### 18.3 Export Status and Download

**Poll status:**

```
GET /api/internal/v1/dashboards/<dashboard_id>/export/<export_id>/status
Authorization: Bearer <access_token>
```

**Response 200:**

```json
{
  "export_id": "...",
  "status": "queued | generating | ready | failed",
  "file_size_bytes": 2097152,
  "expires_at": "ISODate",
  "download_url": "/api/internal/v1/dashboards/<id>/export/<export_id>/download"
}
```

`download_url` is only present when `status == "ready"`.

**Download:**

```
GET /api/internal/v1/dashboards/<dashboard_id>/export/<export_id>/download
Authorization: Bearer <access_token>
```

Response: Binary PDF file with headers:

```
Content-Type: application/pdf
Content-Disposition: attachment; filename="dashboard_<name>_<date>.pdf"
Content-Length: <file_size_bytes>
```

### 18.4 Flutter: Export Flow

```dart
// In toolbar, "Export PDF" button:

Future<void> _exportPdf() async {
  final exportId = await ref.read(dashboardServiceProvider).requestPdfExport(
    dashboardId: dashboardId,
    filterState: ref.read(filterStateProvider),
    pageSize: 'A4',
    orientation: 'landscape',
  );

  // Show non-blocking snackbar
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text('PDF export started. You will be notified when ready.')),
  );

  // Poll every 3 seconds until status == 'ready' or 'failed'
  _pollExportStatus(exportId);
}

Future<void> _pollExportStatus(String exportId) async {
  const interval = Duration(seconds: 3);
  const maxWait = Duration(minutes: 5);
  final deadline = DateTime.now().add(maxWait);

  while (DateTime.now().isBefore(deadline)) {
    await Future.delayed(interval);
    final status = await ref.read(dashboardServiceProvider).getExportStatus(exportId);
    if (status.status == 'ready') {
      _showDownloadNotification(status.downloadUrl);
      return;
    } else if (status.status == 'failed') {
      _showErrorNotification();
      return;
    }
  }
  // Timeout
  _showErrorNotification();
}
```

On completion, show an in-app notification with a download button. On mobile, download the file
to the device's downloads folder using `path_provider` and `dio`.

---

## 19. Error Codes Reference

All errors follow the standard format from CONTEXT.md §15:

```json
{ "error": { "code": "ERROR_CODE", "message": "Human-readable message", "details": {} } }
```

| Error Code | HTTP Status | Description |
|-----------|-------------|-------------|
| `DASHBOARD_NOT_FOUND` | 404 | Dashboard ID does not exist or is soft-deleted |
| `DASHBOARD_NAME_CONFLICT` | 409 | A dashboard with this name already exists in the project |
| `CANVAS_VALIDATION_ERROR` | 400 | Canvas structure failed validation |
| `INVALID_ANALYSIS_BINDING` | 400 | Referenced analysis or node does not exist |
| `WIDGET_ID_CONFLICT` | 400 | Duplicate widget IDs in the widget array |
| `SNAPSHOT_NOT_FOUND` | 404 | Snapshot not found |
| `PUBLIC_TOKEN_NOT_FOUND` | 404 | Public token does not match any active public dashboard |
| `EXPORT_NOT_FOUND` | 404 | Export record not found |
| `EXPORT_NOT_READY` | 409 | Download requested but export is not ready yet |
| `FILTER_COLUMN_NOT_FOUND` | 400 | Requested column not found in the analysis result |
| `ANALYSIS_NO_RUN` | 422 | Analysis has never been run — no data to display |
| `FORBIDDEN` | 403 | User lacks required role |
| `VALIDATION_ERROR` | 400 | Request body failed field validation |

---

## 20. Backend File Locations

| File | Responsibility |
|------|---------------|
| `backend/app/routes/dashboard.py` | All dashboard API route definitions (Flask Blueprint) |
| `backend/app/services/dashboard_service.py` | Business logic: CRUD, canvas save/load, data resolution, snapshots |
| `backend/app/workers/export_tasks.py` | Celery task: `generate_dashboard_pdf` |
| `backend/app/engines/analysis_engine.py` | Reused for resolving analysis results for widgets |
| `backend/app/templates/dashboard_export.html` | Jinja2 HTML template for PDF export |
| `backend/app/utils/chart_renderer.py` | Server-side chart SVG rendering via matplotlib |
| `frontend/lib/features/dashboard_builder/` | All Flutter dashboard builder code |
| `frontend/lib/features/dashboard_builder/public_dashboard_page.dart` | Public view |

**Blueprint registration** (in `backend/app/__init__.py`):

```python
from app.routes.dashboard import dashboard_bp
app.register_blueprint(dashboard_bp, url_prefix='/api/internal/v1/dashboards')
```

**Public endpoint** is registered under a separate blueprint:

```python
from app.routes.api_v1 import api_v1_bp
app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
# Public dashboard endpoints live in api_v1_bp at /api/v1/public/dashboards/<token>
```
