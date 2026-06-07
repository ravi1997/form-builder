# 05 — Plugin System

> **Authoritative reference**: Always read `/docs/CONTEXT.md` before modifying this document.  
> **Scope**: This document covers everything needed to understand, develop, install, and maintain plugins for the Form Builder Platform.

---

## Table of Contents

1. [Overview](#overview)
2. [Plugin Package Anatomy](#plugin-package-anatomy)
3. [manifest.json Specification](#manifestjson-specification)
4. [Component Schema Format](#component-schema-format)
5. [Property Definition Types](#property-definition-types)
6. [Plugin Lifecycle](#plugin-lifecycle)
7. [Plugin Loading Process](#plugin-loading-process)
8. [Subprocess Sandbox Mechanics](#subprocess-sandbox-mechanics)
9. [Org-Scoped DB Access in Plugins](#org-scoped-db-access-in-plugins)
10. [Plugin Versioning](#plugin-versioning)
11. [Plugin Permissions](#plugin-permissions)
12. [handler.py Interface Contract](#handlerpy-interface-contract)
13. [Built-in Plugin Package Structure](#built-in-plugin-package-structure)
14. [Component Rendering Pipeline](#component-rendering-pipeline)
15. [Concept Registry](#concept-registry)
16. [Plugin Development Guide](#plugin-development-guide)
17. [Future Plugin Marketplace](#future-plugin-marketplace)

---

## Overview

The Plugin System is the extensibility backbone of the Form Builder Platform. It allows new component types — form fields, analysis nodes, and dashboard widgets — to be registered, loaded, and executed without modifying the core platform codebase.

**Core design principles:**

- **Isolation**: Plugin backend code runs in a subprocess, never inside the main Flask process.
- **Org-scoped security**: All database access granted to a plugin is automatically scoped to the requesting organisation's data.
- **Concept-driven extension**: Plugins extend defined "concepts" (`form_field`, `analysis_node`, `dashboard_widget`). New concepts can only be added by `super_admin` via the Concept Registry.
- **Schema-driven rendering**: Plugin components are rendered in Flutter entirely based on their `component_schema.json` — no Dart code is shipped with a plugin.
- **Versioned coexistence**: Multiple versions of the same plugin can be installed simultaneously, with each component schema pinned to the version that created it.

**Plugin storage locations:**

| Path | Purpose |
|------|---------|
| `backend/app/plugins/builtin/` | Built-in system plugins (shipped with platform) |
| `backend/app/plugins/installed/` | Admin-installed third-party plugins |

Each plugin occupies its own subdirectory named `{plugin_id}/` within the appropriate parent directory.

---

## Plugin Package Anatomy

A plugin package is a directory with the following required and optional files:

```
{plugin_id}/
├── manifest.json            ← REQUIRED. Plugin metadata and capability declarations.
├── component_schema.json    ← REQUIRED (for single-component plugins).
│                               Multi-component plugins declare multiple schemas listed in manifest.
├── backend/
│   └── handler.py           ← REQUIRED if plugin has backend logic.
│                               Receives JSON via stdin, writes JSON to stdout.
├── assets/
│   ├── icon.svg             ← Component icons shown in builder palette.
│   ├── preview.png          ← Optional: screenshot for marketplace listing.
│   └── ...                  ← Any additional static asset files.
├── schemas/
│   ├── my_component_a.json  ← Per-component schemas (multi-component plugins).
│   └── my_component_b.json
├── requirements.txt         ← Python dependencies for handler.py subprocess.
│                               These are installed into a plugin-specific venv.
├── CHANGELOG.md             ← Optional. Human-readable version history.
└── README.md                ← Optional. Developer documentation.
```

### File-by-File Explanation

#### `manifest.json`
The entry point for the Plugin Engine. Declares plugin identity, capabilities, permissions, and component mappings. The Plugin Engine reads this file first on every load. See [manifest.json Specification](#manifestjson-specification) for the complete field reference.

#### `component_schema.json` (or per-component files under `schemas/`)
Defines the structure, properties, and rendering metadata of one or more components contributed by this plugin. The platform stores each schema in the `component_schemas` MongoDB collection. See [Component Schema Format](#component-schema-format) for the complete field reference.

#### `backend/handler.py`
The Python entrypoint for plugin execution. The Plugin Engine spawns this as a subprocess when a plugin component needs to execute backend logic (e.g., an analysis node processes data, or a form field needs server-side validation). Communication is exclusively via **stdin/stdout JSON messages**. See [handler.py Interface Contract](#handlerpy-interface-contract).

#### `assets/`
Static files — SVG icons, preview images. Icons referenced in `manifest.json` components entries must exist in this directory. Icons are served from the platform's static file server, not exposed directly from the plugin directory.

#### `requirements.txt`
Standard pip requirements file. During plugin installation, the Plugin Engine creates a **plugin-specific Python virtual environment** at a managed path (e.g., `/var/plugins_venvs/{plugin_id}/`) and runs `pip install -r requirements.txt` into it. The subprocess for `handler.py` is always invoked using this venv's Python interpreter.

#### `CHANGELOG.md`
Optional markdown file listing changes per version. Referenced in `manifest.json` as `"changelog": "CHANGELOG.md"`. Displayed in the admin plugin management UI.

---

## manifest.json Specification

The `manifest.json` file is the authoritative descriptor for a plugin. Every field is validated by the Plugin Engine on load. Validation failures cause the plugin to enter the `unloaded` state with an error message stored in the `plugins` MongoDB document.

### Complete Field Reference

```json
{
  "plugin_id": "my-custom-plugin",
  "name": "My Custom Plugin",
  "version": "1.2.0",
  "min_platform_version": "1.0.0",
  "max_platform_version": "2.99.99",
  "author": {
    "name": "Author Full Name",
    "email": "author@example.com",
    "url": "https://example.com"
  },
  "description": "A brief description of what this plugin does.",
  "concept_targets": ["form_field", "analysis_node"],
  "permissions": ["db_read_own_org", "internet_access"],
  "backend": {
    "handler": "backend/handler.py",
    "requirements": ["requests==2.31.0", "pandas==2.1.0"]
  },
  "components": [
    {
      "type": "my_text_field",
      "schema": "component_schema.json",
      "icon": "assets/icon_text.svg",
      "concept": "form_field"
    },
    {
      "type": "my_analysis_node",
      "schema": "schemas/analysis_node.json",
      "icon": "assets/icon_node.svg",
      "concept": "analysis_node"
    }
  ],
  "changelog": "CHANGELOG.md"
}
```

### Field Reference Table

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `plugin_id` | `string` | **Yes** | Unique slug. Must match `^[a-z0-9-]+$`. Max 64 chars. Used as the directory name and primary key in `plugins` collection. Must be globally unique across all installed plugins. |
| `name` | `string` | **Yes** | Human-readable display name. Max 128 chars. Shown in admin UI and builder palette headers. |
| `version` | `string` | **Yes** | Semantic version string (`MAJOR.MINOR.PATCH`). Must be a valid semver string. Used for version coexistence and upgrade detection. |
| `min_platform_version` | `string` | **Yes** | Minimum platform version required. If the running platform version is below this, the plugin fails to load with error `PLUGIN_PLATFORM_VERSION_TOO_LOW`. |
| `max_platform_version` | `string` | No | Maximum platform version this plugin supports. If set and exceeded, plugin fails to load with error `PLUGIN_PLATFORM_VERSION_TOO_HIGH`. Omit to support all future versions. |
| `author` | `object` | **Yes** | Author/publisher information. |
| `author.name` | `string` | **Yes** | Author's full name. Max 128 chars. |
| `author.email` | `string` | **Yes** | Author's contact email. Must be valid email format. |
| `author.url` | `string` | No | Author's website URL. Must be valid URL if present. |
| `description` | `string` | **Yes** | Plugin description shown in admin UI. Max 1024 chars. Plain text only (no markdown). |
| `concept_targets` | `array[string]` | **Yes** | List of concept IDs this plugin extends. Each value must exist in the `concept_registry` collection. Valid built-in values: `"form_field"`, `"analysis_node"`, `"dashboard_widget"`. Must be non-empty array. |
| `permissions` | `array[string]` | **Yes** | List of permission strings the plugin requires. Each must be a valid permission identifier (see [Plugin Permissions](#plugin-permissions)). Can be an empty array `[]` if no special permissions needed. Admin must explicitly approve each permission on install. |
| `backend` | `object` | No | Backend execution configuration. Omit if plugin has no server-side logic (pure UI/rendering plugins). |
| `backend.handler` | `string` | If `backend` present | Relative path to the handler Python file within the plugin directory. Conventionally `"backend/handler.py"`. |
| `backend.requirements` | `array[string]` | No | Python package requirement strings (PEP 508 format). Installed into the plugin's dedicated venv. Example: `"pandas==2.1.0"`. These take precedence over (and must not conflict with) platform requirements. |
| `components` | `array[object]` | **Yes** | List of component descriptors contributed by this plugin. Must contain at least one entry. |
| `components[].type` | `string` | **Yes** | Unique component type identifier. Must match `^[a-z0-9_]+$`. Must be globally unique across all installed plugins. Used as the `component_type` field in `component_schemas` collection. |
| `components[].schema` | `string` | **Yes** | Relative path to the component's JSON schema file within the plugin directory. |
| `components[].icon` | `string` | **Yes** | Relative path to the SVG icon file within the plugin directory. Icon is displayed in the builder palette. |
| `components[].concept` | `string` | **Yes** | The concept ID this component implements. Must be one of the values declared in `concept_targets`. |
| `changelog` | `string` | No | Relative path to the CHANGELOG.md file. Displayed in admin plugin UI for version history. |

### Validation Rules

1. `plugin_id` must be unique. Installing a plugin with an existing `plugin_id` constitutes an **upgrade**, not a new install.
2. `concept_targets` values must all exist in `concept_registry.concept_id`. Invalid concept IDs cause load failure.
3. All `components[].type` values must be unique across all currently installed plugins globally. The Plugin Engine checks this before registering the plugin.
4. All file paths referenced in `backend.handler`, `components[].schema`, and `components[].icon` must exist relative to the plugin package directory.
5. `version` must be parseable as a valid semver string.
6. `permissions` values must all be from the approved permissions list (see [Plugin Permissions](#plugin-permissions)).

### Error Codes on Manifest Validation Failure

| Error Code | Cause |
|-----------|-------|
| `PLUGIN_MANIFEST_MISSING` | `manifest.json` file not found in plugin directory |
| `PLUGIN_MANIFEST_INVALID_JSON` | File cannot be parsed as JSON |
| `PLUGIN_MANIFEST_MISSING_FIELD` | A required field is absent |
| `PLUGIN_ID_CONFLICT` | `plugin_id` already taken by a different plugin |
| `PLUGIN_COMPONENT_TYPE_CONFLICT` | A `component_type` already exists from another plugin |
| `PLUGIN_UNKNOWN_CONCEPT` | `concept_targets` contains unknown concept ID |
| `PLUGIN_UNKNOWN_PERMISSION` | `permissions` contains invalid permission string |
| `PLUGIN_PLATFORM_VERSION_TOO_LOW` | Platform version below `min_platform_version` |
| `PLUGIN_PLATFORM_VERSION_TOO_HIGH` | Platform version exceeds `max_platform_version` |
| `PLUGIN_HANDLER_NOT_FOUND` | `backend.handler` path does not exist |
| `PLUGIN_SCHEMA_NOT_FOUND` | A `components[].schema` path does not exist |
| `PLUGIN_ICON_NOT_FOUND` | A `components[].icon` path does not exist |

---

## Component Schema Format

Each component schema file (`component_schema.json`) defines a single component type in detail. The Plugin Engine reads this file and upserts a document into the `component_schemas` MongoDB collection.

### Complete Schema Structure

```json
{
  "type": "my_component_type",
  "display_name": "My Component",
  "description": "One-line description of this component shown in the palette tooltip.",
  "concept": "form_field",
  "composition": [
    {
      "primitive": "text_input",
      "property_key": "value",
      "label_from_property": "label",
      "placeholder_from_property": "placeholder",
      "visibility": null
    }
  ],
  "properties": [
    {
      "key": "label",
      "label": "Field Label",
      "type": "string",
      "default": "Enter text",
      "required": true,
      "max_length": 256,
      "group": "Content"
    },
    {
      "key": "placeholder",
      "label": "Placeholder Text",
      "type": "string",
      "default": "",
      "required": false,
      "group": "Appearance"
    },
    {
      "key": "max_length",
      "label": "Max Characters",
      "type": "number",
      "default": 500,
      "required": false,
      "min": 1,
      "max": 10000,
      "group": "Validation"
    }
  ],
  "input_ports": [],
  "output_ports": [],
  "widget_config": null,
  "preview_schema": {
    "show_label": true,
    "placeholder_preview": "Sample text input"
  },
  "offline_support": true
}
```

### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `string` | **Yes** | Component type identifier. Must match `components[].type` in `manifest.json`. Must match `^[a-z0-9_]+$`. |
| `display_name` | `string` | **Yes** | Human-readable name shown in the builder palette card. Max 64 chars. |
| `description` | `string` | **Yes** | Tooltip/description text in the palette. Max 256 chars. |
| `concept` | `string` | **Yes** | Which concept this component belongs to: `"form_field"`, `"analysis_node"`, or `"dashboard_widget"`. |
| `composition` | `array[PrimitiveRef]` | Conditional | Required for `form_field` components. Defines how the component renders as a composition of platform primitives. See [Composition — PrimitiveRef](#composition--primitiveref). |
| `properties` | `array[PropertyDef]` | **Yes** | List of configurable properties for this component. These appear in the property panel when the component is selected in the builder. See [Property Definition Types](#property-definition-types). |
| `input_ports` | `array[PortDef]` | Conditional | Required for `analysis_node` components. Defines data input ports. See [Port Definitions](#port-definitions). |
| `output_ports` | `array[PortDef]` | Conditional | Required for `analysis_node` components. Defines data output ports. |
| `widget_config` | `object` or `null` | Conditional | Required for `dashboard_widget` components. Dashboard-specific rendering config. See [Widget Config](#widget-config). |
| `preview_schema` | `object` | **Yes** | Describes how the component renders in read-only/preview mode. At minimum `{}`. Used by the form viewer to render submitted responses. |
| `offline_support` | `boolean` | **Yes** | Whether this component works offline (in Drift SQLite + Flutter). If `false`, the component is hidden/disabled when the app is offline. |

---

### Composition — PrimitiveRef

Used exclusively for `form_field` components. A form field is composed of one or more platform-native primitive components (defined in CONTEXT.md §9).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `primitive` | `string` | **Yes** | The primitive component type to use. Must be one of the built-in primitive identifiers (e.g., `"text_input"`, `"dropdown"`, `"date_picker"`). See CONTEXT.md §9 for the full list. |
| `property_key` | `string` | **Yes** | The property key in the form response that this primitive writes to. Typically `"value"` for single-primitive fields, or a sub-key for complex fields. |
| `label_from_property` | `string` | No | If set, the primitive's `label` prop is sourced from the component property with this key. Example: `"label"` means the label comes from the `label` property. |
| `placeholder_from_property` | `string` | No | Maps the component property to the primitive's `placeholder`. |
| `visibility` | `VisibilityRules` or `null` | No | Conditional visibility rule for this specific primitive within the composite field. Uses the same VisibilityRules structure as form visibility (see §5.4 CONTEXT.md). `null` means always visible. |
| `required_from_property` | `string` | No | If set, the primitive's `required` prop is sourced from the named property (typically `"required"`). |
| `readonly_when_prefilled` | `boolean` | No | If `true`, this primitive becomes read-only when its value has been populated via a FetchAction. Default: `false`. |

**Example — A composite phone field:**
```json
"composition": [
  {
    "primitive": "dropdown",
    "property_key": "country_code",
    "label_from_property": null,
    "visibility": null
  },
  {
    "primitive": "text_input",
    "property_key": "number",
    "label_from_property": "label",
    "placeholder_from_property": "placeholder",
    "visibility": null
  }
]
```

---

### Port Definitions

Used for `analysis_node` components only.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | **Yes** | Port identifier. Must be unique within the node's input or output ports. Used in `Edge.from_port` / `Edge.to_port` in the analysis graph. Example: `"input"`, `"output"`, `"data_in"`. |
| `label` | `string` | **Yes** | Human-readable port label shown on the node canvas. Example: `"Input Data"`. |
| `data_type` | `string` | **Yes** | The data type this port accepts/produces. Used to enforce type compatibility between connected nodes. Valid values: `"dataframe"`, `"value"`, `"table"`, `"chart_data"`, `"any"`. |
| `required` | `boolean` | No | For input ports: whether this input must be connected before the node can execute. Default: `true`. |
| `multiple` | `boolean` | No | For input ports: whether multiple edges can connect to this port. Default: `false`. |
| `description` | `string` | No | Tooltip text explaining what this port expects/produces. |

---

### Widget Config

Used for `dashboard_widget` components. Provides dashboard-specific rendering metadata.

```json
"widget_config": {
  "min_width": 200,
  "min_height": 150,
  "default_width": 400,
  "default_height": 300,
  "resizable": true,
  "data_binding_required": true,
  "supports_filter_binding": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `min_width` | `number` | No | Minimum pixel width on the dashboard canvas. Default: `100`. |
| `min_height` | `number` | No | Minimum pixel height on the dashboard canvas. Default: `100`. |
| `default_width` | `number` | No | Default pixel width when dropped onto the canvas. Default: `300`. |
| `default_height` | `number` | No | Default pixel height when dropped onto canvas. Default: `200`. |
| `resizable` | `boolean` | No | Whether the widget can be resized by dragging. Default: `true`. |
| `data_binding_required` | `boolean` | No | Whether this widget requires a `data_binding` to an analysis output node. If `true`, the widget shows a warning state until bound. Default: `false`. |
| `supports_filter_binding` | `boolean` | No | Whether this widget can receive filter bindings from a `filter_widget` type widget. Default: `false`. |

---

## Property Definition Types

Properties defined in `component_schema.json` → `properties[]` appear in the **Property Panel** on the right side of any builder when a component is selected. Each property definition (PropertyDef) has a `type` field that determines both the validation logic and the UI control rendered in the property panel.

### Common Fields (All Types)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `key` | `string` | **Yes** | Property identifier. Must be unique within the component's properties array. Alphanumeric + underscores only. This key appears in `Question.properties` in the form schema. |
| `label` | `string` | **Yes** | Human-readable label in the property panel. Max 64 chars. |
| `type` | `string` | **Yes** | Property type. One of: `"string"`, `"number"`, `"boolean"`, `"enum"`, `"color"`, `"object"`, `"array"`. |
| `default` | `any` | **Yes** | Default value applied when component is dropped onto the canvas. Must match the declared type. |
| `required` | `boolean` | No | Whether this property must have a non-null, non-empty value. Default: `false`. |
| `group` | `string` | No | Property panel group/section name. Properties with the same `group` value are rendered together under a collapsible group header. Common groups: `"Content"`, `"Appearance"`, `"Validation"`, `"Behaviour"`, `"Advanced"`. Default: `"General"`. |
| `description` | `string` | No | Tooltip text shown on hover next to the property label. Max 256 chars. |
| `hidden` | `boolean` | No | If `true`, this property exists in the schema but is not shown in the property panel. Used for internal tracking values. Default: `false`. |
| `readonly` | `boolean` | No | If `true`, displayed in property panel but not editable. Default: `false`. |
| `depends_on` | `object` | No | Conditional display rule: `{ "property_key": "...", "value": "..." }`. This property is shown in the panel only when another property equals the specified value. |

---

### Type: `string`

Renders as a single-line text input in the property panel.

```json
{
  "key": "placeholder",
  "label": "Placeholder Text",
  "type": "string",
  "default": "",
  "required": false,
  "max_length": 256,
  "min_length": 0,
  "pattern": null,
  "multiline": false,
  "group": "Appearance"
}
```

| Extra Field | Type | Description |
|-------------|------|-------------|
| `max_length` | `number` | Maximum character length for the string value. |
| `min_length` | `number` | Minimum character length. Default: `0`. |
| `pattern` | `string` or `null` | Regex pattern the value must match. Validated at save time. |
| `multiline` | `boolean` | If `true`, renders a multi-line textarea in the property panel. Default: `false`. |

---

### Type: `number`

Renders as a numeric spinner input in the property panel.

```json
{
  "key": "max_length",
  "label": "Max Characters",
  "type": "number",
  "default": 500,
  "required": false,
  "min": 1,
  "max": 10000,
  "step": 1,
  "integer_only": true,
  "group": "Validation"
}
```

| Extra Field | Type | Description |
|-------------|------|-------------|
| `min` | `number` | Minimum allowed value. |
| `max` | `number` | Maximum allowed value. |
| `step` | `number` | Increment/decrement step for the spinner. Default: `1`. |
| `integer_only` | `boolean` | If `true`, rejects non-integer values. Default: `false`. |

---

### Type: `boolean`

Renders as a toggle switch in the property panel.

```json
{
  "key": "required",
  "label": "Required Field",
  "type": "boolean",
  "default": false,
  "required": false,
  "group": "Validation"
}
```

No additional fields beyond the common set.

---

### Type: `enum`

Renders as a dropdown select in the property panel. The value stored is always the `value` field of the selected option.

```json
{
  "key": "alignment",
  "label": "Text Alignment",
  "type": "enum",
  "default": "left",
  "required": true,
  "options": [
    { "value": "left",   "label": "Left" },
    { "value": "center", "label": "Center" },
    { "value": "right",  "label": "Right" }
  ],
  "group": "Appearance"
}
```

| Extra Field | Type | Description |
|-------------|------|-------------|
| `options` | `array[object]` | **Required.** List of selectable options. Each item: `{ "value": string, "label": string }`. `value` is what is stored; `label` is what is shown. Must contain at least one option. |

---

### Type: `color`

Renders as a color picker widget in the property panel. Stores value as a hex color string (e.g., `"#FF5733"`).

```json
{
  "key": "primary_color",
  "label": "Primary Color",
  "type": "color",
  "default": "#2196F3",
  "required": false,
  "allow_opacity": true,
  "group": "Appearance"
}
```

| Extra Field | Type | Description |
|-------------|------|-------------|
| `allow_opacity` | `boolean` | If `true`, renders an RGBA picker (stores as `"#RRGGBBAA"`). Default: `false`. |

---

### Type: `object`

Renders as an expandable inline JSON editor or a set of nested property fields in the property panel. Used for structured sub-configurations.

```json
{
  "key": "border_style",
  "label": "Border Style",
  "type": "object",
  "default": { "width": 1, "color": "#CCCCCC", "radius": 4 },
  "required": false,
  "schema": {
    "width": { "type": "number", "label": "Width", "min": 0, "max": 20 },
    "color": { "type": "color", "label": "Color" },
    "radius": { "type": "number", "label": "Corner Radius", "min": 0, "max": 100 }
  },
  "group": "Appearance"
}
```

| Extra Field | Type | Description |
|-------------|------|-------------|
| `schema` | `object` | Optional. Describes the nested keys and their types as a map of `{ key: PropertyDef }`. If provided, renders as structured sub-fields. If omitted, renders as a raw JSON editor. |

---

### Type: `array`

Renders as a list editor in the property panel with add/remove/reorder controls. Used for things like option lists in a custom dropdown component.

```json
{
  "key": "options",
  "label": "Options",
  "type": "array",
  "default": [],
  "required": false,
  "item_type": "string",
  "min_items": 1,
  "max_items": 100,
  "group": "Content"
}
```

| Extra Field | Type | Description |
|-------------|------|-------------|
| `item_type` | `string` | Type of each list item. One of: `"string"`, `"number"`, `"object"`. Default: `"string"`. |
| `item_schema` | `object` | If `item_type` is `"object"`, describes the structure of each item using the same PropertyDef map format as `object.schema`. |
| `min_items` | `number` | Minimum number of items. Default: `0`. |
| `max_items` | `number` | Maximum number of items. Default: `1000`. |

---

## Plugin Lifecycle

A plugin moves through the following states. State transitions are persisted to the `plugins.status` field in MongoDB.

```
            ┌─────────────────────────────┐
            │                             │
            ▼                             │
        [Install]                         │ (upgrade: new version
            │                             │  installed over existing)
            ▼                             │
       ┌─────────┐   Admin approves    ┌──┴─────────┐
       │ pending │ ──────────────────► │   active   │◄──┐
       └─────────┘                     └────────────┘   │ (admin re-enables)
                                             │           │
                                     Admin   │           │
                                    suspends │           │
                                             ▼           │
                                       ┌───────────┐     │
                                       │ suspended │─────┘
                                       └───────────┘
                                             │
                                      Admin removes
                                             │
                                             ▼
                                       ┌──────────┐
                                       │ unloaded │
                                       └──────────┘
```

> **Note:** The `plugins.status` field in MongoDB uses `enum[active|suspended|unloaded]`. A `pending` state exists transiently during the install/approval flow but may also be persisted until admin approval is granted.

### State Descriptions

| State | Description | Effect on Components |
|-------|-------------|----------------------|
| **Pending** | Plugin has been uploaded by admin but not yet reviewed and approved. | Components from this plugin do not appear in any builder palette. Existing schemas are registered in `component_schemas` but hidden. |
| **Active** | Plugin is fully approved and operational. | Components appear in all relevant builder palettes. Backend handler.py can be invoked. |
| **Suspended** | Plugin has been temporarily disabled by admin (e.g., due to a security concern or malfunction). | Components disappear from builder palettes. Existing forms/analyses that use this plugin's components continue to render (read-only) but the backend handler is NOT invoked. No new component instances can be added. |
| **Unloaded** | Plugin has been completely removed or has permanently failed to load. | Components are hidden from palettes. Existing component instances in forms show a degraded "plugin not available" state. Backend handler is never invoked. |

### Transition Actions

| Transition | Actor | What Happens |
|-----------|-------|--------------|
| Install → Pending | `super_admin` uploads plugin package | Plugin Engine validates manifest, registers component schemas, sets status to `pending`. Permission review screen shown. |
| Pending → Active | `super_admin` approves all permissions | Plugin Engine spawns handler.py in a test-ping subprocess to verify it starts. Sets status `active` in DB. |
| Active → Suspended | `super_admin` or system (on repeated errors) | Backend handler subprocess is killed if running. Status set to `suspended`. Notification sent. |
| Suspended → Active | `super_admin` re-enables | Plugin Engine performs re-validation of manifest. Status set back to `active`. |
| Any → Unloaded | `super_admin` removes plugin | Component schemas remain in DB but `is_deleted: true`. Plugin directory removed. Status set to `unloaded`. |
| Pending → Unloaded | Manifest validation fails | Automatic. Error stored in plugin document metadata. |

---

## Plugin Loading Process

### Server Startup Loading

On every Flask/Gunicorn server start, the `PluginEngine` (at `backend/app/engines/plugin_engine.py`) performs the following steps:

1. **Discovery**: Scan both `backend/app/plugins/builtin/` and `backend/app/plugins/installed/` directories. For each subdirectory found, attempt to load it as a plugin.

2. **Manifest Validation**: For each discovered plugin directory, read and validate `manifest.json`. Validation failures are logged with the specific error code. The plugin is set to `unloaded` status in DB.

3. **Version Check**: Compare `manifest.json` `min_platform_version` and `max_platform_version` against `PLATFORM_VERSION` from `.env`. Mismatch → `unloaded`.

4. **Plugin ID Reconciliation**: Check `plugins` collection in MongoDB:
   - If `plugin_id` exists and `version` matches → update `status` from DB, apply if `active`.
   - If `plugin_id` exists and `version` differs → treat as upgrade candidate.
   - If `plugin_id` not in DB → new plugin, set status to `pending`.

5. **Permission Check**: For each `permissions` entry in the manifest, verify the permission was previously admin-approved (checked in `plugins` collection `approved_permissions` field). Unapproved permissions → plugin stays in `pending`.

6. **Component Schema Registration**: For each active plugin, read all component schema files listed in `manifest.json`. Upsert into `component_schemas` collection keyed by `plugin_id + plugin_version + component_type`.

7. **Venv Preparation**: If `backend.requirements` is non-empty and the plugin-specific venv doesn't exist or is stale, trigger a background venv creation task (Celery worker). The plugin is set to `pending` until the venv is ready.

8. **Health Ping**: For each active plugin with a `backend.handler`, spawn a test subprocess invocation with `{"action": "ping"}`. Expect `{"status": "ok"}` within 5 seconds. Failure → set plugin to `suspended`, log error, notify super_admin.

9. **Registry Update**: Update the in-memory plugin registry (a dict keyed by `plugin_id`) with all active plugins and their component schemas. This registry is used by routes and services to resolve component types at request time.

### Hot-Load at Runtime

The Plugin Engine supports hot-loading a new plugin or upgrading an existing one without server restart via `POST /api/internal/v1/plugins/{plugin_id}/reload` (super_admin only).

Hot-load steps:
1. Admin places the new plugin package under `backend/app/plugins/installed/{plugin_id}/`.
2. Admin calls the reload endpoint.
3. Plugin Engine re-reads the manifest for that specific `plugin_id`.
4. Re-runs the full load sequence for that single plugin (steps 2–9 above).
5. Updates the in-memory registry.
6. All new requests immediately use the updated component schemas.
7. Existing in-flight requests that already resolved the old component type continue to completion using cached type info.

**Constraint**: Hot-load does NOT restart Celery workers. If a new plugin version changes the `handler.py` interface, the old Celery workers may have the old handler cached. A Celery worker restart is required (`POST /api/internal/v1/system/restart-workers`, super_admin only) for handler changes to take full effect in background task execution.

---

## Subprocess Sandbox Mechanics

### How the Subprocess Is Spawned

When a plugin's backend handler needs to be invoked (e.g., an analysis node runs), the Plugin Engine calls `plugin_engine.invoke_handler(plugin_id, payload)`:

```python
# Pseudocode — plugin_engine.py
def invoke_handler(plugin_id: str, payload: dict, org_id: str, timeout: int = 30) -> dict:
    plugin = registry[plugin_id]
    python_bin = f"/var/plugins_venvs/{plugin_id}/bin/python"
    handler_path = plugin.handler_abs_path
    
    sandboxed_payload = {
        "org_id": str(org_id),
        "db_config": {
            "uri": MONGODB_URI,         # full URI passed — access enforced by SDK
            "allowed_org_id": str(org_id)
        },
        "permissions": plugin.approved_permissions,
        "payload": payload
    }
    
    proc = subprocess.Popen(
        [python_bin, handler_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=sandbox_env,               # restricted environment
        cwd=plugin.directory_path,
        timeout=timeout
    )
    
    stdout, stderr = proc.communicate(
        input=json.dumps(sandboxed_payload).encode("utf-8"),
        timeout=timeout
    )
    
    if proc.returncode != 0:
        raise PluginExecutionError(stderr.decode("utf-8"))
    
    return json.loads(stdout.decode("utf-8"))
```

### Sandbox Environment Variables

The subprocess is given a restricted OS environment. The following environment variables are passed to the subprocess:

| Variable | Value | Purpose |
|----------|-------|---------|
| `PLUGIN_ID` | Plugin's ID | Self-identification |
| `PLUGIN_VERSION` | Plugin's version | Self-identification |
| `ORG_ID` | Requesting org's ObjectId | Scope enforcement |
| `PLATFORM_VERSION` | Running platform version | Version checks |
| `PYTHONPATH` | Plugin directory path | Import resolution |
| `PYTHONHASHSEED` | `"0"` | Deterministic output |

The following are **explicitly NOT** passed to the subprocess:
- `SECRET_KEY`, `JWT_SECRET_KEY`, `EMAIL_API_TOKEN`, `SMS_API_TOKEN`, `REDIS_URL`, `ELASTICSEARCH_URL`.
- Any host OS environment variables not in the whitelist.

### Restricted Python Builtins

The Plugin Engine's sandboxed Python environment restricts certain imports. The `handler.py` is executed in a subprocess that has the following modules unavailable (ImportError raised if attempted):

- `os.system`, `os.popen`, `os.execv` (shell execution)
- `subprocess` (further process spawning)
- `importlib` (dynamic module loading)
- `ctypes` (C extension bypass)
- `socket` (unless `internet_access` permission is approved)
- `urllib`, `http.client`, `requests` (unless `internet_access` permission is approved)

**Note**: These restrictions are enforced by the plugin SDK's import hook, not by OS-level sandboxing. Plugin authors should treat these as contractual, not as a security boundary (the subprocess isolation is the actual security boundary).

### Input/Output Protocol

- **Input**: The Plugin Engine writes a single JSON object to the subprocess's `stdin`, terminated by a newline.
- **Output**: The subprocess must write a single JSON object to `stdout`, terminated by a newline, then exit with code `0`.
- **Errors**: Any `stderr` output is captured and logged to the platform's error log. Non-zero exit code triggers a `PluginExecutionError`.
- **Timeout**: Default 30 seconds. Configurable per-invocation. On timeout, the subprocess is `SIGKILL`ed and a timeout error is returned to the caller.

### Error Isolation

- If a plugin subprocess crashes or times out, the error is isolated to that specific execution.
- In analysis execution: the failing node is marked `error` in `analysis_runs.node_statuses`. Other branches of the DAG continue executing.
- In form submission: if a plugin form field's server-side validation fails, the specific field's error is returned to the client; other fields are unaffected.
- Repeated failures (configurable threshold, default 5 consecutive failures) trigger automatic plugin `suspension` and a `plugin.error` notification to `super_admin`.

---

## Org-Scoped DB Access in Plugins

### SDK-Provided Filtered Client

Plugins never receive a raw MongoDB connection string. Instead, the plugin SDK (a small Python library installed into every plugin's venv) provides a filtered database client:

```python
# Available in handler.py via the plugin SDK
from plugin_sdk import get_db_client

db = get_db_client()  # Automatically org-scoped
```

### How It Works

The `get_db_client()` function in the plugin SDK:

1. Reads `ORG_ID` from the subprocess environment variables (set by the Plugin Engine).
2. Reads the DB URI from the sandboxed config dict passed via stdin (`db_config.uri`).
3. Returns a wrapped `PyMongo` client whose every query automatically appends `{"org_id": ObjectId(ORG_ID)}` to the query filter.
4. **Insert operations** automatically set `org_id` on every inserted document.
5. **Update operations** always include `{"org_id": ObjectId(ORG_ID)}` in the filter, preventing cross-org updates.
6. **Delete operations** are blocked unless `db_write_own_org` permission is approved.

### Permitted Collections

A plugin with `db_read_own_org` permission can read from:
- `form_responses` (filtered to own org)
- `forms`, `form_commits` (filtered to own org)
- `analyses`, `analysis_results` (filtered to own org)
- `projects` (filtered to own org)
- `users` (filtered to own org's members only — joined via `org_memberships`)
- `component_schemas` (read-only, all orgs — schema data is non-sensitive)

A plugin with `db_write_own_org` permission can write to:
- `analysis_results` (own org only)
- Plugin-specific collections prefixed `plugin_{plugin_id}_` (own org only, auto-created)

### Blocked Operations (Always, Regardless of Permissions)

- Reading from `users.password_hash`, `users.two_factor_secret`, `api_keys.key_hash`, `sessions.refresh_token_hash`.
- Reading from `audit_logs` (audit data is never exposed to plugins).
- Reading from `system_config` (contains platform secrets).
- Any cross-org query (queries that would return data from other orgs are rejected before execution).
- Dropping collections.
- Creating indexes.
- Running arbitrary JavaScript (`$where`, `mapReduce`, `$function` operators are blocked).

---

## Plugin Versioning

### Coexistence of Multiple Versions

The platform supports multiple versions of the same plugin being installed simultaneously. This is essential for backward compatibility: a form built with plugin version 1.0.0 must continue to render correctly even after the plugin is upgraded to version 2.0.0.

**How it works:**

1. Each plugin version is stored as a separate entry in `plugin_versions` collection.
2. Each component schema in `component_schemas` is keyed by `(plugin_id, plugin_version, component_type)`.
3. When a form is saved, each question's `component_type` is recorded in the form schema. The `component_schemas` lookup at render time uses `(component_type, plugin_version)` — where `plugin_version` is resolved from the form's commit.
4. The `plugins` collection stores the **active** version. Only one version can be `active` at a time; older versions have status `deprecated` in `plugin_versions`.

### Version Pinning in component_schemas

The `component_schemas` collection schema includes:

```json
{
  "plugin_id": "my-plugin",
  "plugin_version": "1.0.0",
  "component_type": "my_text_field",
  ...
}
```

When rendering a form question of type `"my_text_field"`, the platform:
1. Looks up the form's commit.
2. Checks the `plugin_version` that was active when this question was added (stored as `question.ui.plugin_version` in the form schema).
3. Fetches the `component_schema` for `(component_type="my_text_field", plugin_version="1.0.0")`.
4. If the schema for that exact version is not found (e.g., it was yanked), falls back to the nearest available version with a deprecation warning.

### Upgrading a Plugin

When a new version of an existing plugin is installed:

1. The new plugin package is placed in the `installed/` directory.
2. Admin triggers `reload` via the admin panel.
3. Plugin Engine detects that `plugin_id` exists with a different `version`.
4. New version is registered in `plugin_versions`.
5. Existing `component_schemas` for the old version remain in place.
6. New `component_schemas` for the new version are registered.
7. Old `plugin_versions` entry is set to `deprecated`.
8. `plugins` document is updated to reflect the new active version.
9. New forms/analyses created after the upgrade use the new version's schemas.
10. Existing forms/analyses retain their pinned version and continue using old schemas.

### Version Deprecation and Yanking

| Status | Description |
|--------|-------------|
| `active` | Currently installed and in use for new components. |
| `deprecated` | Older version superseded by a newer one. Still resolves for existing components. |
| `yanked` | Critically flawed version, removed from registry. Falls back to nearest non-yanked version. |

---

## Plugin Permissions

### Permission Declaration

Permissions are declared in `manifest.json` in the `permissions` array:
```json
"permissions": ["db_read_own_org", "internet_access"]
```

On plugin install, the admin is presented with each declared permission and must approve them individually before the plugin can become `active`.

### Complete Permission List

| Permission | Description | Risk Level |
|-----------|-------------|------------|
| `db_read_own_org` | Read MongoDB collections for the requesting organisation's own data only. Subject to the filtered DB client (no cross-org). | Low |
| `db_write_own_org` | Write to the requesting organisation's own plugin-prefixed collections and to `analysis_results`. Subject to the filtered DB client. | Medium |
| `internet_access` | Make outbound HTTP/HTTPS requests. The `socket`, `urllib`, `requests`, `httpx` modules are unblocked. All requests should be to declared endpoints (see `manifest.json` optional `allowed_urls`). | High |
| `filesystem_read` | Read files from the plugin's own directory (`backend/app/plugins/installed/{plugin_id}/`) and from declared read paths. Cannot read outside this scope. | Medium |
| `filesystem_write` | Write files to the plugin's designated output directory (`/var/plugin_output/{plugin_id}/`). Cannot write outside this directory. | Medium |

### How Admin Reviews and Approves

1. Admin navigates to **Admin → Plugins → {plugin_name}** in the Flutter admin panel.
2. For each declared permission, a review card is shown with:
   - Permission name and risk level (colour-coded: green/yellow/red).
   - A plain-English description of what this permission enables.
   - An "Approve" / "Deny" toggle.
3. If all permissions are approved, the plugin status moves to `active`.
4. If any permission is denied, the plugin status remains `pending`. Admin can later re-visit and approve.
5. Approved permissions are stored in `plugins.approved_permissions: [String]` in MongoDB.
6. The Plugin Engine cross-checks `manifest.permissions` against `plugins.approved_permissions` on every load. If the manifest declares a permission not in `approved_permissions` (e.g., a new version added a new permission), the plugin is held in `pending` until re-reviewed.

### Permission Enforcement at Runtime

- The Plugin Engine passes `{"permissions": ["db_read_own_org"]}` in the sandboxed payload to the subprocess.
- The plugin SDK checks these permissions before enabling restricted functionality (e.g., `get_db_client()` raises `PluginPermissionError` if `db_read_own_org` is not in the payload's permissions list).
- Internet access enforcement: the sandbox environment does not unblock `socket` unless `internet_access` is in the permissions list.

---

## handler.py Interface Contract

### Input Contract

The plugin handler receives a single JSON object on `stdin`. The JSON is always a UTF-8 encoded string, followed by a newline (`\n`). The top-level structure is:

```json
{
  "org_id": "64f3c8a2b1d4e5f2a3c7d890",
  "db_config": {
    "uri": "mongodb://mongodb:27017/formbuilder",
    "allowed_org_id": "64f3c8a2b1d4e5f2a3c7d890"
  },
  "permissions": ["db_read_own_org"],
  "payload": {
    "action": "execute",
    "component_type": "my_analysis_node",
    "node_id": "node_abc123",
    "run_id": "64f3c8a2b1d4e5f2a3c7d891",
    "analysis_id": "64f3c8a2b1d4e5f2a3c7d892",
    "properties": {
      "filter_column": "age",
      "filter_value": 30
    },
    "input_data": {
      "input": {
        "columns": ["id", "name", "age"],
        "rows": [
          [1, "Alice", 30],
          [2, "Bob", 25]
        ]
      }
    }
  }
}
```

#### Top-Level Input Fields

| Field | Type | Description |
|-------|------|-------------|
| `org_id` | `string` | ObjectId string of the requesting organisation. All DB operations must be scoped to this. |
| `db_config` | `object` | MongoDB connection config. Passed to `plugin_sdk.get_db_client()`. Do not use directly. |
| `db_config.uri` | `string` | MongoDB URI. |
| `db_config.allowed_org_id` | `string` | Redundant safety: org_id that the SDK enforces on all queries. |
| `permissions` | `array[string]` | List of admin-approved permissions for this plugin. |
| `payload` | `object` | The actual invocation payload. Contents vary by `action`. |

#### Payload Field: `action`

| Action | Description |
|--------|-------------|
| `"ping"` | Health check. Handler must return `{"status": "ok"}` immediately. No DB access needed. |
| `"execute"` | Primary execution. Invoked when an analysis node runs or a form field's backend logic is needed. |
| `"validate"` | Server-side field validation. Invoked on form submission for plugin-provided form fields that declared server-side validation. |
| `"prefetch"` | Pre-populate data for a field (e.g., autocomplete suggestions). Invoked on field focus. |

#### Payload Fields for `action: "execute"` (Analysis Node)

| Field | Type | Description |
|-------|------|-------------|
| `component_type` | `string` | The component type being executed. |
| `node_id` | `string` | UUID of the node in the analysis graph. |
| `run_id` | `string` | ObjectId of the current `analysis_runs` document. |
| `analysis_id` | `string` | ObjectId of the `analyses` document. |
| `properties` | `object` | The node's configured properties (key-value pairs matching the component schema). |
| `input_data` | `object` | Map of `port_id → data`. Data format for `dataframe` type: `{ "columns": [...], "rows": [[...], ...] }`. For `value` type: `{ "value": any }`. |

#### Payload Fields for `action: "validate"` (Form Field)

| Field | Type | Description |
|-------|------|-------------|
| `component_type` | `string` | The form field component type. |
| `question_id` | `string` | UUID of the question in the form schema. |
| `form_id` | `string` | ObjectId of the form. |
| `commit_id` | `string` | The commit SHA the response is being submitted against. |
| `properties` | `object` | The question's configured properties. |
| `value` | `any` | The answer value submitted by the respondent. |
| `respondent_id` | `string` or `null` | ObjectId of authenticated respondent, or null for anonymous. |

---

### Output Contract

The handler must write a single JSON object to `stdout`, followed by a newline (`\n`), then exit with code `0`.

#### Output for `action: "ping"`

```json
{ "status": "ok" }
```

#### Output for `action: "execute"` (Analysis Node — Success)

```json
{
  "status": "success",
  "output_data": {
    "output": {
      "columns": ["id", "name", "age"],
      "rows": [[1, "Alice", 30]]
    }
  },
  "metadata": {
    "row_count": 1,
    "execution_time_ms": 142
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `"success"` or `"error"`. |
| `output_data` | `object` | Map of `port_id → data`. Format mirrors `input_data`. Must include all declared output ports. |
| `metadata` | `object` | Optional. `row_count`, `execution_time_ms`, `warnings: [string]`. |

#### Output for `action: "execute"` (Analysis Node — Error)

```json
{
  "status": "error",
  "error": {
    "code": "FILTER_COLUMN_NOT_FOUND",
    "message": "Column 'age' does not exist in the input dataframe.",
    "details": {}
  }
}
```

#### Output for `action: "validate"` (Form Field — Valid)

```json
{
  "status": "valid"
}
```

#### Output for `action: "validate"` (Form Field — Invalid)

```json
{
  "status": "invalid",
  "error_message": "The email domain is not in the approved list.",
  "field_id": "q_abc123"
}
```

### Error Handling in handler.py

- **Unhandled exceptions**: If `handler.py` raises an uncaught exception, the traceback goes to `stderr` and the process exits with a non-zero code. The Plugin Engine captures `stderr`, logs it, and returns a `PluginExecutionError` to the caller.
- **Timeout**: The subprocess is `SIGKILL`ed after the timeout. The Plugin Engine returns a timeout error. The plugin's error counter is incremented.
- **Expected errors**: Always catch expected errors and return `{"status": "error", "error": {...}}` to `stdout`. This is the preferred error path — it allows the platform to show user-friendly error messages without triggering the plugin error counter.
- **Example handler.py skeleton**:

```python
#!/usr/bin/env python3
"""
handler.py — Plugin handler entrypoint.
Reads JSON from stdin, writes JSON to stdout.
"""
import sys
import json
from plugin_sdk import get_db_client, PluginPermissionError


def handle_ping(payload: dict, db) -> dict:
    return {"status": "ok"}


def handle_execute(payload: dict, db) -> dict:
    properties = payload.get("properties", {})
    input_data = payload.get("input_data", {})
    
    # ... your logic here ...
    
    return {
        "status": "success",
        "output_data": {
            "output": {
                "columns": ["result"],
                "rows": [["value"]]
            }
        }
    }


def main():
    raw = sys.stdin.readline()
    envelope = json.loads(raw)
    
    db = get_db_client()  # org-scoped
    payload = envelope["payload"]
    action = payload.get("action", "execute")
    
    if action == "ping":
        result = handle_ping(payload, db)
    elif action == "execute":
        result = handle_execute(payload, db)
    else:
        result = {"status": "error", "error": {"code": "UNKNOWN_ACTION", "message": f"Unknown action: {action}"}}
    
    sys.stdout.write(json.dumps(result) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
```

---

## Built-in Plugin Package Structure

Built-in plugins ship with the platform and live at `backend/app/plugins/builtin/`. They provide the base primitive components for all three builders. Built-in plugins are **system plugins** — they cannot be uninstalled, suspended by non-`super_admin`, or overridden.

### Built-in Plugin Directory Layout

```
backend/app/plugins/builtin/
├── core_form_fields/
│   ├── manifest.json
│   ├── schemas/
│   │   ├── text_input.json
│   │   ├── text_area.json
│   │   ├── number_input.json
│   │   ├── email_input.json
│   │   ├── phone_input.json
│   │   ├── dropdown.json
│   │   ├── multi_select.json
│   │   ├── radio_group.json
│   │   ├── checkbox.json
│   │   ├── checkbox_group.json
│   │   ├── toggle.json
│   │   ├── button_group.json
│   │   ├── date_picker.json
│   │   ├── time_picker.json
│   │   ├── datetime_picker.json
│   │   ├── date_range_picker.json
│   │   ├── file_upload.json
│   │   ├── image_capture.json
│   │   ├── signature.json
│   │   ├── audio_record.json
│   │   ├── rating.json
│   │   ├── slider.json
│   │   ├── number_stepper.json
│   │   ├── color_picker.json
│   │   ├── location_picker.json
│   │   ├── barcode_scanner.json
│   │   ├── fetch_button.json
│   │   ├── heading.json
│   │   ├── paragraph.json
│   │   ├── divider.json
│   │   ├── image_display.json
│   │   └── video_display.json
│   └── assets/
│       └── icons/          ← One SVG per component
│
├── core_analysis_nodes/
│   ├── manifest.json
│   ├── schemas/
│   │   ├── form_responses.json
│   │   ├── csv_upload.json
│   │   ├── manual_data_entry.json
│   │   ├── cross_form_join.json
│   │   ├── external_api_fetch.json
│   │   ├── filter.json
│   │   ├── sort.json
│   │   ├── group_by.json
│   │   ├── join.json
│   │   ├── calculate_column.json
│   │   ├── pivot.json
│   │   ├── unpivot.json
│   │   ├── rename_columns.json
│   │   ├── select_columns.json
│   │   ├── deduplicate.json
│   │   ├── fill_missing.json
│   │   ├── count.json
│   │   ├── sum.json
│   │   ├── average.json
│   │   ├── min_max.json
│   │   ├── median.json
│   │   ├── percentile.json
│   │   ├── frequency.json
│   │   ├── cross_tabulation.json
│   │   ├── table_output.json
│   │   ├── kpi_value.json
│   │   ├── bar_chart_data.json
│   │   ├── line_chart_data.json
│   │   ├── pie_chart_data.json
│   │   └── export_node.json
│   └── backend/
│       └── handler.py      ← Implements all analysis node logic
│
└── core_dashboard_widgets/
    ├── manifest.json
    ├── schemas/
    │   ├── kpi_card.json
    │   ├── bar_chart.json
    │   ├── line_chart.json
    │   ├── pie_chart.json
    │   ├── data_table.json
    │   ├── text_label.json
    │   ├── image_widget.json
    │   └── filter_widget.json
    └── assets/
        └── icons/
```

### Built-in Plugin Manifest Characteristics

Built-in plugin manifests include an additional field not available to third-party plugins:

```json
{
  "plugin_id": "core_form_fields",
  "is_builtin": true,
  "is_system": true,
  ...
}
```

| Field | Description |
|-------|-------------|
| `is_builtin` | `true` for all built-in plugins. These are loaded before any installed plugins and their component types cannot be overridden. |
| `is_system` | `true` means the plugin cannot be suspended, unloaded, or deleted from the admin panel. Only direct filesystem modification + server restart can remove a system plugin. |

Built-in plugins do **not** require permission approval — they are trusted system code reviewed by the platform developers.

---

## Component Rendering Pipeline

### Overview

The path from a `component_schema.json` definition to an actual Flutter widget rendered on screen:

```
component_schema.json (MongoDB: component_schemas)
         │
         │  (loaded at app start / on sync)
         ▼
  Flutter: ComponentSchemaModel (Dart class)
         │
         │  (when a form is opened for filling)
         ▼
  Flutter: JSON UI Engine (shared/json_ui_engine/)
         │
         │  resolves composition[] array
         ▼
  Flutter: PrimitiveResolver
         │
         │  for each PrimitiveRef, instantiates
         ▼
  Flutter: Primitive Widget (e.g., TextInputWidget, DropdownWidget)
         │
         │  properties applied from Question.properties
         ▼
  Rendered Flutter Widget Tree
```

### Step-by-Step

1. **Schema Sync**: On app start (online), the Flutter app fetches all active `component_schemas` from `GET /api/internal/v1/plugins/schemas`. These are stored in Drift (SQLite) for offline access.

2. **Form Open**: When a user opens a form to fill, the Form Viewer loads the form's `form_commit.schema`. For each question, it reads `question.type` (the `component_type`).

3. **Schema Lookup**: The JSON UI Engine looks up the `component_schema` for the question's `component_type` from the local Drift DB. If not found (e.g., a plugin was installed after last sync), it attempts an online fetch.

4. **Composition Resolution**: For `form_field` components, the JSON UI Engine iterates `component_schema.composition[]`. For each `PrimitiveRef`:
   - It instantiates the declared `primitive` widget (e.g., `TextInputWidget`).
   - It maps `property_key` → the sub-field in `question.properties` that this primitive writes to.
   - It resolves `label_from_property`, `placeholder_from_property`, etc., from the form question's properties.
   - It evaluates `visibility` rules (if any) against the current form state.

5. **Property Application**: The `question.properties` object (stored in the form schema) is passed to each primitive widget as its configuration. The platform validates that `question.properties` matches the `PropertyDef` schema at form-save time (builder) and at render time (viewer — soft validation, with fallback to defaults).

6. **Answer Binding**: Each primitive widget is bound to an answer slot keyed by `question.id + property_key`. On change, it updates the local response draft in Drift. On submission, the full `answers` map is sent to the API.

7. **Visibility Rules**: Before rendering each question (or section/sub-section), the JSON UI Engine evaluates the `visibility_rules` conditions against the current `answers` map. Hidden elements are removed from the widget tree (not just made invisible).

8. **Read-Only/Preview Mode**: In response review (e.g., viewing a submitted response), the `preview_schema` object from `component_schema` is used. This may suppress edit controls, format values differently, or apply read-only styling. Each primitive widget has a `readonly` prop that is set to `true` in this mode.

9. **Offline Mode**: If `component_schema.offline_support` is `false` and the device is offline, the question is rendered with a placeholder widget: "This field requires an internet connection."

---

## Concept Registry

### What Is a Concept?

A "concept" is a category of component that the platform understands how to use. The three built-in concepts are:

| Concept ID | Builder | Description |
|-----------|---------|-------------|
| `form_field` | Form Builder | A question/input field in a form. Can have composition, validation, skip logic, calculations, and fetch actions. |
| `analysis_node` | Analysis Coder | A node in the DAG. Has typed input/output ports. Executed by the analysis engine. |
| `dashboard_widget` | Dashboard Builder | A visual element on the dashboard canvas. Can bind to analysis output nodes. |

### Concept Registry Collection (MongoDB)

```json
{
  "_id": "ObjectId",
  "concept_id": "form_field",
  "name": "Form Field",
  "description": "A question or input component in a form.",
  "builder_type": "form_builder",
  "supported_component_types": ["text_input", "dropdown", "..."],
  "output_format": "answer_value",
  "version_support": true,
  "collaboration_support": true,
  "is_system": true,
  "org_id": null,
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

### Adding a New Concept

Only `super_admin` can add new concepts to the registry. New concepts extend the platform's understanding of what kinds of components can exist.

**Procedure:**
1. `super_admin` navigates to **Admin → Platform → Concept Registry**.
2. Fills in the concept creation form: `concept_id` (must be unique), `name`, `description`, `builder_type` (which builder uses this concept), `output_format` (how the engine consumes this concept's output).
3. Platform validates: `concept_id` must match `^[a-z_]+$`, must not exist already.
4. New concept is inserted into `concept_registry` collection with `is_system: false`.
5. Plugin developers can now target this concept in their `manifest.json` `concept_targets`.
6. The corresponding builder (Form Builder, Analysis Coder, or Dashboard Builder) must be extended by a platform developer to understand how to use this new concept — this is a code change, not just a config change.

**Important**: Adding a concept to the registry alone is not sufficient to make it usable — the builder's rendering pipeline and the engine's execution pipeline must also be updated to handle the new concept type. The concept registry is a registry, not an automatic enablement mechanism.

---

## Plugin Development Guide

### Step 1: Set Up the Development Environment

1. Clone the platform repository.
2. Start the development stack: `docker compose up` from the `docker/` directory.
3. The platform should be running at `http://localhost`.
4. Log in as `super_admin` (seeded via `scripts/seed.py`).

### Step 2: Create the Plugin Directory

```bash
mkdir -p backend/app/plugins/installed/my-plugin/backend
mkdir -p backend/app/plugins/installed/my-plugin/assets
mkdir -p backend/app/plugins/installed/my-plugin/schemas
```

### Step 3: Write manifest.json

```json
{
  "plugin_id": "my-plugin",
  "name": "My Plugin",
  "version": "0.1.0",
  "min_platform_version": "1.0.0",
  "author": { "name": "Your Name", "email": "you@example.com" },
  "description": "A demonstration plugin.",
  "concept_targets": ["form_field"],
  "permissions": [],
  "backend": {
    "handler": "backend/handler.py",
    "requirements": []
  },
  "components": [
    {
      "type": "my_custom_field",
      "schema": "schemas/my_custom_field.json",
      "icon": "assets/icon.svg",
      "concept": "form_field"
    }
  ]
}
```

### Step 4: Write the Component Schema

Create `schemas/my_custom_field.json`:

```json
{
  "type": "my_custom_field",
  "display_name": "My Custom Field",
  "description": "A custom text field with character counter.",
  "concept": "form_field",
  "composition": [
    {
      "primitive": "text_input",
      "property_key": "value",
      "label_from_property": "label",
      "placeholder_from_property": "placeholder",
      "visibility": null
    }
  ],
  "properties": [
    {
      "key": "label",
      "label": "Label",
      "type": "string",
      "default": "My Field",
      "required": true,
      "group": "Content"
    },
    {
      "key": "placeholder",
      "label": "Placeholder",
      "type": "string",
      "default": "Type here...",
      "required": false,
      "group": "Content"
    },
    {
      "key": "max_chars",
      "label": "Max Characters",
      "type": "number",
      "default": 200,
      "required": false,
      "min": 1,
      "max": 5000,
      "group": "Validation"
    }
  ],
  "input_ports": [],
  "output_ports": [],
  "widget_config": null,
  "preview_schema": { "show_char_count": true },
  "offline_support": true
}
```

### Step 5: Write handler.py (If Needed)

If your plugin needs backend logic (e.g., server-side validation), create `backend/handler.py`. For a pure form field with no backend logic, you can omit the `backend` key from `manifest.json` entirely, or keep it but implement only the `ping` action.

### Step 6: Add an Icon

Place an SVG file at `assets/icon.svg`. Icons should be 24×24 viewBox, single color (the platform tints them based on the theme).

### Step 7: Install the Plugin

Option A — Restart the server (the Plugin Engine auto-discovers on startup):
```bash
docker compose restart flask_api
```

Option B — Hot-load (no restart needed):
```bash
curl -X POST http://localhost/api/internal/v1/plugins/my-plugin/reload \
  -H "Authorization: Bearer {super_admin_jwt}"
```

### Step 8: Approve the Plugin

1. Navigate to **Admin → Plugins** in the Flutter app.
2. Find "My Plugin" in the `pending` list.
3. Review permissions (none in this example).
4. Click "Approve". Plugin status changes to `active`.

### Step 9: Verify in Builder

1. Open the Form Builder.
2. In the left palette, find "My Plugin" category.
3. "My Custom Field" should appear as a draggable component.
4. Drag it onto the canvas and verify the property panel shows the declared properties.

### Step 10: Test Offline Rendering

1. Open the Flutter app in offline mode (disable network in device settings or simulator).
2. Open a form that contains your custom field.
3. Verify the field renders correctly (since `offline_support: true`).

---

## Future Plugin Marketplace

> **Status**: Planned for a future platform version. Not implemented in Phase 1–5.

### Concept

The Plugin Marketplace is a curated registry where verified plugin developers can publish plugins for all Form Builder Platform installations. Analogous to the Chrome Web Store or Docker Hub for plugins.

### Distribution Model

1. **Publisher Registration**: Plugin authors register on the marketplace website, undergo identity verification.
2. **Plugin Submission**: Author packages the plugin (zipped plugin directory), uploads to marketplace, fills metadata (category, screenshots, changelog).
3. **Automated Review**: Marketplace performs:
   - Manifest schema validation.
   - Security scan of `handler.py` for known malicious patterns.
   - Dependency vulnerability scan (via `safety` / `pip-audit`).
4. **Manual Review**: Marketplace team reviews permissions, intent, and implementation.
5. **Publishing**: Approved plugins appear in the marketplace catalog.

### Installation from Marketplace

In the admin panel, **Admin → Plugins → Browse Marketplace**:
1. Admin searches the marketplace catalog (served via marketplace API).
2. Admin clicks "Install" on a plugin.
3. Platform downloads the plugin zip, extracts to `installed/`, triggers hot-load.
4. Admin reviews permissions and approves.

### Plugin Signing

Marketplace plugins are signed with the marketplace's GPG key. The platform verifies the signature on install. Unsigned or tampered plugins are rejected.

### Revenue Model

Not applicable — platform has no billing tiers. Marketplace plugins are free.
