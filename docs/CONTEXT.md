# MASTER CONTEXT — Form Builder Platform
# This file is the authoritative reference for ALL architectural decisions.
# All AI agents writing documentation for this project MUST read this file first.

---

## 1. PROJECT IDENTITY

- **Name**: Form Builder Platform (working title)
- **Type**: Self-hosted SaaS meta-platform
- **Vision**: A plugin-extensible, JSON-driven platform that renders drag-and-drop builders
  for forms, analysis pipelines, and dashboards — connected by a shared data layer and
  a strict organisational hierarchy.
- **Target Scale**: 10,000 concurrent users, 1,000+ forms, 10,000–50,000 form submissions/day
- **Deployment**: Single self-hosted server (Docker Compose), operated by platform owner;
  clients access it as a SaaS web/mobile/desktop application
- **Billing**: No billing tiers — all features free to all approved organisations
- **Institution context**: AIIMS (custom email/SMS HTTP APIs provided)

---

## 2. THE THREE BUILDERS

### 2.1 Form Builder
- Drag-and-drop canvas for building forms
- Forms are JSON structures; responses are JSON
- Form structure: Sections → Sub-sections (repeatable) → Questions (repeatable)
- Forms have UI JSON (theme, layout, branding)
- Git-like versioning with full branching support
- Published branch = production; responses tied to commit_id
- Public OR internal access per form
- Form lifecycle: expiry date, response cap, draft saving, multi-submission policy, response editing policy

### 2.2 Analysis Coder
- Node graph (DAG) visual builder (like n8n/Node-RED)
- Nodes: data sources, transforms, aggregations, outputs
- Edges: typed connections between node ports
- Execution modes: on-demand, reactive/live, scheduled (all three must exist from day 1)
- Execution engine runs on Celery workers
- Results exported as CSV, Excel, PDF
- Error isolation: failing branch stops only that subgraph, others continue

### 2.3 Dashboard Builder
- Free-form canvas (like Figma — absolute positioning, resize, layers)
- Widget types: KPI card, bar/line/pie chart, data table, text/label, image, filter widget
- Widgets bind to analysis output nodes
- Auto-refresh: configurable per dashboard or disabled
- Public shareable dashboards supported
- Can pull from multiple analyses simultaneously

---

## 3. TECH STACK (FINAL — DO NOT DEVIATE)

### Backend
| Technology | Version Guidance | Purpose |
|---|---|---|
| Python | 3.11+ | Language |
| Flask | 3.x | REST API framework |
| Gunicorn | latest | WSGI server, multi-worker |
| Celery | 5.x | Background task queue |
| APScheduler | 3.x | Cron scheduling inside Celery |
| MongoDB | 7.x | Primary database |
| PyMongo / Motor | latest | MongoDB driver (Motor for async) |
| Redis | 7.x | Celery broker, cache, rate limit, presence |
| Flask-SocketIO | latest | WebSocket server (presence awareness only) |
| Elasticsearch | 8.x | Full-text search across responses + audit logs |
| WeasyPrint | latest | PDF export generation |
| NetworkX | latest | DAG graph parsing and topological sort |
| python-jose | latest | JWT creation and validation |
| Flask-Limiter | latest | API rate limiting |
| Nginx | latest | Reverse proxy, SSL termination |

### Frontend
| Technology | Version Guidance | Purpose |
|---|---|---|
| Flutter | 3.x (stable) | Cross-platform app (Web, Android, iOS, Desktop) |
| Dart | 3.x | Language |
| Riverpod | 2.x | State management |
| Drift | latest | Local SQLite offline database |
| http / dio | latest | HTTP client |
| flutter_secure_storage | latest | Secure token storage |
| socket_io_client | latest | WebSocket client for presence |
| tus_client | latest | Resumable chunked file uploads |

### Infrastructure
| Technology | Purpose |
|---|---|
| Docker + Docker Compose | Container orchestration |
| Nginx | Reverse proxy, serve Flutter web build |
| Redis | Shared broker + cache |
| Elasticsearch | Search and analytics indexing |

---

## 4. DIRECTORY STRUCTURE (PROJECT ROOT)

```
form-builder/
  docs/                      ← All documentation (this folder)
    phases/                  ← Phase-by-phase implementation plans
  backend/                   ← Python Flask application
    app/
      __init__.py
      config.py
      extensions.py          ← Flask extensions initialisation
      models/                ← Pydantic models (not ORM — MongoDB is schemaless)
      routes/                ← Blueprint-based route modules
        auth.py
        orgs.py
        projects.py
        forms.py
        analysis.py
        dashboard.py
        plugins.py
        admin.py
        api_v1.py            ← Public REST API
      services/              ← Business logic layer
        auth_service.py
        form_service.py
        analysis_service.py
        dashboard_service.py
        plugin_service.py
        notification_service.py
        storage_service.py
        search_service.py
        audit_service.py
        sync_service.py
      engines/               ← Core processing engines
        form_engine.py       ← Versioning, merge, diff, visibility evaluation
        analysis_engine.py   ← DAG execution, node runner
        plugin_engine.py     ← Plugin loader, sandbox, registry
        formula_engine.py    ← AST evaluation for form calculations
        notification_engine.py
      workers/               ← Celery task definitions
        analysis_tasks.py
        export_tasks.py
        notification_tasks.py
        sync_tasks.py
        maintenance_tasks.py
      plugins/               ← Installed plugins directory
        builtin/             ← Built-in plugin packages
        installed/           ← Admin-installed plugin packages
      utils/
        security.py
        validators.py
        pagination.py
        serializers.py
    tests/
    requirements.txt
    celery_worker.py
    wsgi.py
  frontend/                  ← Flutter application
    lib/
      main.dart
      app/
        router.dart
        theme.dart
        constants.dart
      core/
        auth/
        models/
        providers/
        services/
        offline/
        sync/
      features/
        form_builder/
        analysis_coder/
        dashboard_builder/
        form_viewer/
        admin/
        notifications/
      shared/
        widgets/
        json_ui_engine/      ← JSON-driven primitive renderer
        formula_builder/
    pubspec.yaml
    tests/
  docker/
    docker-compose.yml
    docker-compose.prod.yml
    nginx/
      nginx.conf
    backend/
      Dockerfile
    frontend/
      Dockerfile
  scripts/
    seed.py                  ← Database seeding (super_admin, built-in components)
    backup.sh
    restore.sh
  .env.example
  .env
```

---

## 5. MONGODB COLLECTIONS (COMPLETE)

Every document in every collection (except system_config) MUST have:
- `_id`: ObjectId
- `org_id`: ObjectId or null (null for system-level docs)
- `created_at`: ISODate
- `updated_at`: ISODate
- `created_by`: ObjectId (user_id)
- `is_deleted`: Boolean (soft delete flag)
- `deleted_at`: ISODate or null

### 5.1 SYSTEM COLLECTIONS

**system_config** (single document)
```
{
  _id, key: String (unique), value: Any, updated_at, updated_by
}
Keys: platform_name, platform_version, email_api_url, email_api_token,
      sms_api_url, sms_api_token, max_file_size_pdf, max_file_size_video,
      max_file_size_image, max_file_size_other, default_storage_quota_bytes,
      maintenance_mode, registration_open, smtp_from_name, smtp_from_email
```

**audit_logs** (append-only, never soft-deleted)
```
{
  _id, org_id, project_id (optional), entity_type, entity_id,
  action, actor_id, actor_role, ip_address, user_agent,
  before: Object (snapshot before change),
  after: Object (snapshot after change),
  metadata: Object, timestamp, archived: Boolean
}
Indexes: org_id, entity_type+entity_id, actor_id, timestamp, archived
```

### 5.2 IDENTITY & ACCESS COLLECTIONS

**users**
```
{
  _id, email (unique), password_hash, full_name, display_name,
  avatar_url, phone, status: enum[pending_approval|active|suspended|deactivated],
  email_verified: Boolean, phone_verified: Boolean,
  last_login_at, login_count, failed_login_attempts, locked_until,
  two_factor_enabled: Boolean, two_factor_secret,
  notification_preferences: {
    email: Boolean, sms: Boolean, push: Boolean, in_app: Boolean
  },
  device_tokens: [{ token, platform, created_at }],
  created_at, updated_at, approved_at, approved_by, is_deleted, deleted_at
}
```

**organisations**
```
{
  _id, org_id: null (orgs are top-level), name, slug (unique),
  description, logo_url, parent_org_id (null for root orgs),
  org_type: enum[organisation|department|team|unit],
  status: enum[pending_approval|active|suspended],
  approved_at, approved_by,
  settings: {
    allow_public_forms: Boolean,
    default_form_theme: Object,
    max_members: Number,
    allow_external_collaborators: Boolean
  },
  compliance_ids: [ObjectId],   ← references compliance_standards
  storage_quota_bytes: Number,
  storage_used_bytes: Number,
  created_at, updated_at, created_by, is_deleted, deleted_at
}
```

**org_memberships**
```
{
  _id, user_id, org_id, role: enum[org_admin|org_editor|org_analyst|org_viewer],
  custom_permissions: [String],
  status: enum[active|suspended|pending],
  invited_by, joined_at, created_at, updated_at, is_deleted, deleted_at
}
Indexes: user_id+org_id (unique), org_id, user_id
```

**groups**
```
{
  _id, org_id, name, description,
  type: enum[static|dynamic],
  dynamic_rule: {
    field: String,  ← e.g., "role"
    operator: enum[equals|contains|in],
    value: Any
  },
  created_at, updated_at, created_by, is_deleted, deleted_at
}
```

**group_members** (for static groups only; dynamic resolved at query time)
```
{ _id, group_id, user_id, added_by, created_at }
Indexes: group_id+user_id (unique)
```

**invitations**
```
{
  _id, token (unique, JWT), org_id, project_id (optional),
  invited_by, invited_email, role, status: enum[pending|accepted|expired|revoked],
  expires_at (TTL indexed), accepted_at, created_at
}
```

**sessions** (refresh token registry)
```
{ _id, user_id, refresh_token_hash, device_info, ip_address, expires_at (TTL), created_at }
```

**api_keys**
```
{
  _id, org_id, user_id (owner), name, key_hash, key_prefix (first 8 chars for display),
  scopes: [String],  ← e.g., ["forms:read", "responses:write"]
  rate_limit_per_hour: Number, last_used_at, usage_count,
  expires_at (optional), status: enum[active|revoked],
  created_at, updated_at, is_deleted, deleted_at
}
```

**oauth_clients**
```
{
  _id, org_id, client_id (unique), client_secret_hash, name, redirect_uris: [String],
  scopes: [String], grant_types: [String], status: enum[active|revoked],
  created_at, updated_at, is_deleted, deleted_at
}
```

### 5.3 PROJECT COLLECTIONS

**projects**
```
{
  _id, name, description, slug, owner_org_id,
  shared_org_ids: [ObjectId],  ← orgs this project is shared with
  status: enum[active|archived],
  settings: {
    default_form_theme: Object,
    default_compliance_ids: [ObjectId],
    notification_rules: [NotificationRule],
    default_language: String
  },
  created_at, updated_at, created_by, org_id, is_deleted, deleted_at
}
```

**project_members**
```
{
  _id, project_id, user_id, org_id,
  role: enum[project_owner|project_editor|project_analyst|project_viewer],
  invited_by, joined_at, created_at, is_deleted
}
Indexes: project_id+user_id (unique)
```

### 5.4 PLUGIN & CONCEPT COLLECTIONS

**concept_registry**
```
{
  _id, concept_id: String (e.g., "form_field", "analysis_node", "dashboard_widget"),
  name, description,
  builder_type: enum[form_builder|analysis_coder|dashboard_builder],
  supported_component_types: [String],
  output_format: String,
  version_support: Boolean,
  collaboration_support: Boolean,
  is_system: Boolean,  ← true = cannot be deleted
  created_at, updated_at, org_id: null (system-level)
}
```

**plugins**
```
{
  _id, plugin_id: String (unique slug), name, description, author,
  version: String (semver), manifest: Object (full manifest JSON),
  status: enum[active|suspended|unloaded],
  concept_targets: [String],  ← which concept_ids this plugin extends
  permissions: [String],      ← declared permissions in manifest
  installed_at, installed_by, org_id: null (system-level),
  created_at, updated_at, is_deleted, deleted_at
}
```

**plugin_versions**
```
{
  _id, plugin_id, version: String, manifest: Object,
  files_path: String,  ← path to this version's files on server
  status: enum[active|deprecated|yanked],
  released_at, created_at
}
Indexes: plugin_id+version (unique)
```

**component_schemas**
```
{
  _id, plugin_id, plugin_version, concept_id, component_type: String (unique per plugin+version),
  display_name, description, icon_path,
  composition: [PrimitiveRef],  ← for form fields: array of primitive component references
  properties: [PropertyDef],    ← configurable properties with type, default, validation
  input_ports: [PortDef],       ← for analysis nodes
  output_ports: [PortDef],      ← for analysis nodes
  widget_config: Object,        ← for dashboard widgets
  preview_schema: Object,       ← how to render in read-only/preview mode
  offline_support: Boolean,
  created_at, updated_at
}
```

### 5.5 FORM COLLECTIONS

**forms**
```
{
  _id, org_id, project_id, name, description,
  branches: {
    main: String (commit_id),   ← always exists
    [branch_name]: String (commit_id)
  },
  production_branch: String,    ← which branch is "live" (default: "main")
  tags: { [tag_name]: String (commit_id) },
  template_id: ObjectId (null if not from template),
  created_at, updated_at, created_by, is_deleted, deleted_at
}
Indexes: project_id, org_id
```

**form_commits**
```
{
  _id,
  form_id: ObjectId,
  commit_id: String (SHA-like, unique per form),
  parent_ids: [String],           ← array supports merge commits
  author_id: ObjectId,
  message: String,
  branch: String,
  tag: String (optional),
  timestamp: ISODate,
  schema: {                       ← FULL form schema snapshot
    ui: {
      theme: Object,
      layout: enum[single_page|multi_page|wizard],
      primary_color, font, logo_url, cover_page: Object, thank_you_page: Object
    },
    access: {
      type: enum[public|org|groups|users],
      allowed_org_ids: [ObjectId],
      allowed_group_ids: [ObjectId],
      allowed_user_ids: [ObjectId],
      allow_anonymous: Boolean
    },
    settings: {
      expires_at: ISODate (optional),
      max_responses: Number (optional),
      allow_multiple_submissions: Boolean,
      allow_draft_save: Boolean,
      response_edit_policy: enum[no_edit|role_edit|time_window_edit|always_edit],
      edit_time_window_hours: Number,
      edit_allowed_roles: [String],
      require_login: Boolean
    },
    webhook_configs: [{ url, events: [String], secret }],
    sections: [Section]
  }
}

Section: {
  id: String (UUID), title, description, repeatable: Boolean,
  max_repeats: Number, min_repeats: Number,
  visibility_rules: VisibilityRules,
  sub_sections: [SubSection]
}

SubSection: {
  id: String (UUID), title, repeatable: Boolean,
  max_repeats: Number,
  visibility_rules: VisibilityRules,
  questions: [Question]
}

Question: {
  id: String (UUID), type: String (component_type),
  label, description, required: Boolean,
  properties: Object (component-specific, matches PropertyDef in component_schema),
  visibility_rules: VisibilityRules,
  validation_rules: [ValidationRule],
  calculations: [CalculationDef],   ← visual formula builder output
  fetch_action: FetchActionDef (optional),
  skip_logic: SkipLogicDef (optional),
  ui: Object (rendering overrides)
}

VisibilityRules: {
  operator: enum[AND|OR],
  conditions: [Condition]
}

Condition (union type):
  { type: "role", roles: [String] }
  { type: "group", group_ids: [ObjectId] }
  { type: "answer", field_id: String, operator: enum[equals|not_equals|contains|
    greater_than|less_than|in|not_in|is_empty|is_not_empty], value: Any }
  { type: "always_visible" }
  { type: "always_hidden" }

SkipLogicDef: {
  conditions: VisibilityRules,
  jump_to: enum[section|sub_section|question|end],
  target_id: String
}

FetchActionDef: {
  source: enum[own_previous_response|other_form_last_response|external_url],
  form_id: ObjectId (for other_form_last_response),
  url: String (for external_url),
  method: enum[GET|POST],
  headers: Object,
  body_template: String,
  field_mapping: [{ source_path: String, target_question_id: String }],
  offline_behavior: enum[leave_blank|block_submission|use_cache]
}

CalculationDef: {
  trigger: enum[on_change|on_load],
  formula_ast: Object,   ← output of visual formula builder
  target_question_id: String
}

ValidationRule: {
  type: enum[min|max|min_length|max_length|pattern|custom],
  value: Any, message: String
}
```

**form_templates**
```
{
  _id, org_id (null = system template), project_id (optional),
  name, description, category, tags: [String],
  is_system: Boolean, is_public: Boolean,
  schema: Object (same as form_commit.schema),
  usage_count: Number,
  created_at, updated_at, created_by, is_deleted, deleted_at
}
```

**form_responses**
```
{
  _id, form_id, commit_id (version pinned to),
  org_id, project_id,
  respondent_id: ObjectId (null for anonymous),
  respondent_email: String (for anonymous tracking),
  session_id: String,
  status: enum[submitted|draft],
  is_anonymous: Boolean,
  is_legacy: Boolean,               ← true if commit_id != production_branch HEAD
  submission_number: Number,        ← sequential per form
  answers: {
    [question_id]: {
      value: Any,
      display_value: String,
      file_ids: [ObjectId],         ← references file_uploads
      answered_at: ISODate,
      iteration_index: Number       ← for repeatable sections
    }
  },
  repeat_groups: {
    [section_id]: [
      { iteration: Number, answers: { [question_id]: AnswerObj } }
    ]
  },
  metadata: {
    ip_address, user_agent, device_type, platform, started_at, completed_at,
    time_taken_seconds, offline_submitted: Boolean
  },
  edit_history: [{ edited_at, edited_by, before: Object, after: Object }],
  created_at, updated_at, submitted_at, is_deleted, deleted_at
}
Indexes: form_id+commit_id, respondent_id, status, submitted_at, org_id
```

**response_drafts**
```
{
  _id, form_id, commit_id, respondent_id, org_id,
  partial_answers: Object,
  last_saved_at, expires_at (TTL — 30 days default),
  created_at, updated_at
}
Indexes: form_id+respondent_id (unique)
```

**file_uploads**
```
{
  _id, org_id, form_id, response_id, question_id,
  original_filename, stored_filename, file_path (relative to uploads root),
  mime_type, file_size_bytes, file_type: enum[pdf|video|image|other],
  upload_status: enum[pending|uploading|complete|failed],
  upload_offset: Number (for resumable),
  checksum_sha256, virus_scan_status: enum[pending|clean|infected],
  uploaded_by, created_at, updated_at, is_deleted, deleted_at
}
Indexes: org_id, form_id, response_id
```

**edit_sessions** (ephemeral — presence awareness)
```
{ _id, entity_type, entity_id, user_id, org_id, started_at, last_ping_at (TTL 60s) }
```

**pending_merges** (conflict states)
```
{
  _id, form_id, branch_name, base_commit_id, their_commit_id, our_changes: Object,
  conflict_fields: [String], status: enum[pending|resolved|abandoned],
  resolver_id, resolved_at, created_at, created_by
}
```

### 5.6 ANALYSIS COLLECTIONS

**analyses**
```
{
  _id, org_id, project_id, name, description,
  linked_form_ids: [ObjectId],
  execution_modes: [enum[on_demand|reactive|scheduled]],
  schedule: String (cron expression, null if not scheduled),
  reactive_debounce_ms: Number (default 1000),
  graph: {
    nodes: [Node],
    edges: [Edge]
  },
  last_run_id: ObjectId,
  status: enum[idle|running|error],
  created_at, updated_at, created_by, is_deleted, deleted_at
}

Node: {
  id: String (UUID), type: String (component_type from component_schemas),
  position: { x: Number, y: Number },
  size: { width: Number, height: Number },
  properties: Object,
  label: String (user-set name for this node instance),
  is_disabled: Boolean
}

Edge: {
  id: String (UUID),
  from_node: String, from_port: String,
  to_node: String, to_port: String,
  label: String (optional)
}
```

**analysis_runs**
```
{
  _id, analysis_id, org_id, trigger: enum[on_demand|scheduled|reactive|manual],
  triggered_by: ObjectId, status: enum[queued|running|completed|failed|partial],
  started_at, completed_at, celery_task_id,
  node_statuses: {
    [node_id]: { status, started_at, completed_at, error: String }
  },
  error_summary: String,
  result_ids: { [node_id]: ObjectId },  ← references analysis_results
  created_at
}
```

**analysis_results**
```
{
  _id, run_id, analysis_id, node_id, org_id,
  output_type: enum[table|value|dataframe|chart_data|error],
  data: Object,          ← actual result data (table rows, KPI value, etc.)
  row_count: Number,
  column_definitions: [{ name, type, label }],
  cached_until: ISODate,
  created_at
}
```

**analysis_exports**
```
{
  _id, analysis_id, run_id, org_id,
  format: enum[csv|excel|pdf],
  node_ids: [String],    ← which output nodes to include
  file_path: String, file_size_bytes: Number,
  status: enum[queued|generating|ready|failed|expired],
  expires_at (TTL 7 days), created_at, created_by
}
```

### 5.7 DASHBOARD COLLECTIONS

**dashboards**
```
{
  _id, org_id, project_id, name, description,
  is_public: Boolean, public_token: String (for public access),
  canvas: {
    width: Number, height: Number, background_color: String,
    widgets: [Widget]
  },
  settings: {
    auto_refresh: Boolean, refresh_interval_seconds: Number,
    theme: Object
  },
  linked_analysis_ids: [ObjectId],
  created_at, updated_at, created_by, is_deleted, deleted_at
}

Widget: {
  id: String (UUID), type: String (component_type),
  position: { x, y }, size: { width, height },
  z_index: Number, is_locked: Boolean,
  properties: Object,
  data_binding: {
    analysis_id: ObjectId, node_id: String,
    refresh_mode: enum[with_dashboard|independent|never]
  },
  filters: [FilterBinding]
}

FilterBinding: {
  filter_widget_id: String,
  bound_field: String
}
```

**dashboard_snapshots**
```
{ _id, dashboard_id, org_id, data: Object, created_at }
```

### 5.8 NOTIFICATION COLLECTIONS

**notification_templates**
```
{
  _id, org_id (null = system), name, event_type: String,
  channels: {
    email: { subject: String, body_html: String, body_text: String },
    sms: { message: String },
    in_app: { title: String, body: String }
  },
  variables: [{ key, description, example }],
  is_system: Boolean, is_active: Boolean,
  created_at, updated_at, created_by
}
```

**notification_rules**
```
{
  _id, org_id, project_id (optional), form_id (optional),
  name, event_type: String,
  trigger_conditions: [Condition],   ← same Condition type as form visibility
  channels: [enum[email|sms|in_app|push|webhook]],
  recipient_type: enum[form_owner|specific_users|role|group|respondent],
  recipient_ids: [ObjectId],
  template_id: ObjectId,
  is_active: Boolean,
  created_at, updated_at, created_by
}
```

**notification_log**
```
{
  _id, rule_id, org_id, event_type, recipient_id,
  channel: enum[email|sms|in_app|push],
  status: enum[queued|sent|failed|retrying],
  attempt_count: Number, max_attempts: Number (default 3),
  next_retry_at: ISODate,
  provider_response: Object,
  created_at, last_attempt_at
}
```

**webhook_configs**
```
{
  _id, org_id, form_id, project_id,
  name, url, secret (HMAC signing key), events: [String],
  is_active: Boolean, created_at, updated_at, created_by
}
```

**webhook_delivery_log**
```
{
  _id, webhook_config_id, org_id, event_type, payload: Object,
  status: enum[queued|delivered|failed|retrying],
  http_status_code: Number, response_body: String,
  attempt_count: Number, next_retry_at: ISODate,
  delivered_at, created_at
}
```

### 5.9 COMPLIANCE COLLECTIONS

**compliance_standards**
```
{
  _id, code: String (e.g., "GDPR", "HIPAA"),
  name, description, region: String,
  behavioral_constraints: [
    { type: String, config: Object }
  ],
  is_system: Boolean,
  created_at, updated_at, created_by: null (super_admin)
}
```

**org_compliance**
```
{
  _id, org_id,
  compliance_id: ObjectId,
  adopted_at, adopted_by,
  effective_from: ISODate,
  notes: String
}
```

### 5.10 STORAGE COLLECTIONS

**storage_quotas**
```
{
  _id, org_id (unique), quota_bytes: Number,
  used_bytes: { files: Number, database: Number, audit_logs: Number, total: Number },
  warning_threshold: Number (default 0.8),
  last_calculated_at, set_by, created_at, updated_at
}
```

---

## 6. AUTH SYSTEM

### JWT Structure
```json
{
  "sub": "user_id",
  "email": "user@email.com",
  "system_role": "super_admin|user",
  "orgs": [
    { "org_id": "...", "role": "org_admin", "status": "active" }
  ],
  "iat": 1234567890,
  "exp": 1234567890
}
```
- Access token TTL: 15 minutes
- Refresh token TTL: 30 days (stored in sessions collection)
- Refresh tokens are single-use (rotated on each use)

### Auth Endpoints (all under /api/auth/)
- POST /register
- POST /login
- POST /logout
- POST /refresh
- POST /forgot-password
- POST /reset-password
- GET  /me
- POST /verify-email
- POST /accept-invite/{token}

### Role Hierarchy (most → least privileged)
```
super_admin > org_admin > org_editor > org_analyst > org_viewer
project_owner > project_editor > project_analyst > project_viewer
```

### ABAC Evaluation Order
1. Check system_role (super_admin bypasses all)
2. Check org membership + role for the resource's org
3. Check project membership + role
4. Check form-level access settings
5. Check question/option visibility_rules (role condition)
6. Evaluate answer-based conditions at render time

---

## 7. PLUGIN SYSTEM

### Plugin Manifest Format (manifest.json)
```json
{
  "plugin_id": "unique-slug",
  "name": "Plugin Display Name",
  "version": "1.0.0",
  "min_platform_version": "1.0.0",
  "author": { "name": "...", "email": "..." },
  "description": "...",
  "concept_targets": ["form_field", "analysis_node"],
  "permissions": ["db_read_own_org", "internet_access"],
  "backend": { "handler": "backend/handler.py", "requirements": [] },
  "components": [
    { "type": "my_component", "schema": "component_schema.json", "icon": "assets/icon.svg" }
  ],
  "changelog": "CHANGELOG.md"
}
```

### Permissions (must be declared, admin reviews on install)
- `db_read_own_org`: Read MongoDB for own org data only
- `db_write_own_org`: Write to own org's collections
- `internet_access`: Make outbound HTTP calls
- `filesystem_read`: Read from server filesystem (plugins dir only)
- `filesystem_write`: Write to designated plugin output directory

### Plugin Security Rules
- Plugin handler.py runs in a **subprocess** (NOT in the main Flask process)
- Subprocess has restricted Python builtins (no `os`, `subprocess`, `importlib` unless permitted)
- Database access is always filtered by `org_id` automatically (no cross-org data access ever)
- Internet access is only allowed if `internet_access` permission declared and approved
- Plugin subprocess is given a sandboxed config dict (no raw DB connection strings)

### Component Schema Format (component_schema.json)
```json
{
  "type": "my_component_type",
  "display_name": "My Component",
  "concept": "form_field|analysis_node|dashboard_widget",
  "composition": [
    {
      "primitive": "text_input",
      "property_key": "value",
      "label_from_property": "label",
      "visibility": null
    }
  ],
  "properties": [
    {
      "key": "placeholder",
      "label": "Placeholder Text",
      "type": "string|number|boolean|enum|color|object|array",
      "default": "",
      "required": false,
      "options": [],
      "group": "Appearance"
    }
  ],
  "input_ports": [
    { "id": "input", "label": "Input Data", "data_type": "dataframe" }
  ],
  "output_ports": [
    { "id": "output", "label": "Filtered Data", "data_type": "dataframe" }
  ],
  "offline_support": true,
  "preview_schema": {}
}
```

---

## 8. ANALYSIS NODES — BUILT-IN (ALL REQUIRED DAY 1)

### Data Sources
- `form_responses`: Loads all responses for a form (branch-aware)
- `csv_upload`: Upload and parse a CSV file
- `manual_data_entry`: Inline data table editor
- `cross_form_join`: Joins responses from two forms
- `external_api_fetch`: Fetches JSON from an external HTTP endpoint

### Transforms
- `filter`: Filter rows by condition
- `sort`: Sort rows by column(s)
- `group_by`: Group rows + aggregate
- `join`: Join two datasets on a key
- `calculate_column`: Add a computed column (expression-based)
- `pivot`: Pivot table transformation
- `unpivot`: Reverse pivot
- `rename_columns`: Rename column headers
- `select_columns`: Keep/drop specific columns
- `deduplicate`: Remove duplicate rows
- `fill_missing`: Fill null/missing values

### Aggregations
- `count`: Count rows (with group-by support)
- `sum`: Sum a numeric column
- `average`: Average a numeric column
- `min_max`: Min and Max
- `median`: Median value
- `percentile`: Nth percentile
- `frequency`: Frequency distribution
- `cross_tabulation`: Cross-tab between two categorical columns

### Outputs
- `table_output`: Render a data table
- `kpi_value`: Single numeric KPI
- `bar_chart_data`: Formatted bar chart data
- `line_chart_data`: Formatted line chart data
- `pie_chart_data`: Formatted pie chart data
- `export_node`: Trigger CSV/Excel/PDF export

---

## 9. FLUTTER PRIMITIVE COMPONENTS (JSON UI ENGINE)

All primitives accept standard properties: `label`, `placeholder`, `required`,
`disabled`, `readonly`, `hint_text`, `error_message`, `ui_overrides`.

### Text & Input
- `text_input`: Single-line text (string)
- `text_area`: Multi-line text (string)
- `number_input`: Numeric (int or float, with min/max/step)
- `email_input`: Email with format validation
- `phone_input`: Phone with country code picker
- `password_input`: Masked text input
- `url_input`: URL with format validation

### Selection
- `dropdown`: Single select from options list
- `multi_select`: Multiple select with checkboxes
- `radio_group`: Radio button group (single select)
- `checkbox`: Single true/false checkbox
- `checkbox_group`: Multiple checkboxes (array of selected values)
- `toggle`: Boolean toggle switch
- `button_group`: Segmented button selection

### Date & Time
- `date_picker`: Calendar date selector
- `time_picker`: Time selector
- `datetime_picker`: Combined date + time
- `date_range_picker`: Start and end date pair

### Media & Files
- `file_upload`: File picker with type + size constraints
- `image_capture`: Camera/gallery picker (images)
- `signature`: Touch/mouse signature pad
- `audio_record`: Audio recording

### Interactive
- `rating`: Star rating (configurable max)
- `slider`: Range slider (min/max/step)
- `number_stepper`: Increment/decrement number
- `color_picker`: Color selection

### Location & Special
- `location_picker`: GPS coordinates with map preview
- `barcode_scanner`: QR/barcode scanner
- `fetch_button`: Button that triggers a FetchActionDef

### Display (non-input)
- `heading`: Section heading text
- `paragraph`: Descriptive text block
- `divider`: Visual separator
- `image_display`: Display an image from URL or upload
- `video_display`: Display a video

---

## 10. OFFLINE SYNC POLICY

### What Gets Synced to Device (Full Offline — All Platforms)
1. User profile + auth tokens
2. All org memberships and roles for the user
3. All project metadata the user can access
4. All forms (schema only — commits from production branch) the user has access to
5. User's own response drafts
6. Notification history (last 100)
7. Plugin component schemas (for rendering)

### What Does NOT Sync (Server-Side Only)
1. Other users' responses (privacy + size)
2. Analysis results (computation is server-side)
3. Dashboard data (depends on analysis)
4. Audit logs
5. Admin data

### Sync Engine Behavior
- On app start: check connectivity → if online, sync queue first, then pull updates
- On connectivity restore: auto-trigger sync
- Conflict detection: optimistic locking via `base_commit_id` on every save
- Conflict resolution: GitHub-style 3-way merge UI (per-field conflict selection)

### File Sync (Resumable Uploads — tus Protocol)
- Chunked in 5MB chunks
- On reconnect: server reports offset, client resumes from that offset
- Old version offline form submissions: accepted as-is, tagged `is_legacy: true`, user notified on next open

---

## 11. NOTIFICATION SYSTEM

### Email/SMS API (Fixed Endpoints)
```
Email: POST https://rpcapplication.aiims.edu/services/api/v1/mail/single
SMS:   POST https://rpcapplication.aiims.edu/services/api/v1/sms/single
Auth:  Bearer token from system_config
```

### Retry Policy
- Max attempts: 3
- Backoff: 1 min → 5 min → 15 min
- After 3 failures: mark `failed`, log, notify super_admin

### Template Variables Available in All Templates
`{{user_name}}`, `{{user_email}}`, `{{org_name}}`, `{{project_name}}`,
`{{form_name}}`, `{{response_count}}`, `{{action_url}}`, `{{timestamp}}`,
`{{actor_name}}`, `{{entity_type}}`, `{{entity_name}}`

### Events That Trigger Notifications
- `response.submitted`: New form response received
- `response.edited`: Response edited by respondent
- `form.published`: Form published to production
- `form.version_changed`: New version committed
- `collaboration.conflict`: Edit conflict detected
- `analysis.run_completed`: Analysis run finished
- `analysis.run_failed`: Analysis run failed
- `invite.accepted`: Invitation accepted
- `user.approved`: User approved by admin
- `user.suspended`: User suspended
- `quota.warning_80`: Storage at 80%
- `quota.warning_90`: Storage at 90%
- `quota.exceeded`: Storage quota exceeded
- `plugin.installed`: Plugin installed
- `plugin.error`: Plugin error in production
- `webhook.failed`: Webhook delivery failed
- `scheduled_analysis.completed`: Scheduled run completed

---

## 12. SECURITY POLICIES

### API Security
- All routes require JWT except: POST /auth/login, POST /auth/register, GET /forms/:id (public forms)
- Rate limits: 60 req/min for authenticated, 20 req/min for unauthenticated, 1000 req/hr per API key
- CORS: restricted to configured origins only
- All inputs validated and sanitised before use
- SQL/NoSQL injection: parameterised queries only
- File uploads: virus scan (ClamAV), MIME type validation, size check, stored outside web root

### Plugin Security
- Subprocess isolation (not same process)
- Restricted Python builtins in subprocess
- DB access scoped to own org automatically
- Permissions declared and admin-approved
- No direct DB connection string access (SDK-provided filtered client)
- Plugin output directory is isolated per plugin

### Data Security
- Passwords: bcrypt with cost factor 12
- Sensitive config (tokens, secrets): stored in .env, never in DB
- JWT secrets: rotated quarterly
- HMAC for webhook payloads: SHA-256 with webhook secret
- Audit log: append-only (no delete API), archived per retention policy
- File paths: never exposed directly; served through authenticated endpoints

---

## 13. DATA POLICIES

### Retention Policy
- Default: retain all data forever
- Configurable per org: apply to responses, file uploads, audit logs
- Celery maintenance task runs nightly to enforce retention policies
- Audit logs: archive to cold storage after threshold (super_admin configurable)

### Storage Quota
- Set per org by super_admin
- Covers: file storage + DB document size (estimated) + audit log size
- At 80%: warning notification to org_admin
- At 90%: warning to org_admin + super_admin
- At 100%+: allow overflow, notify both admins, block new file uploads (not form submissions)
- Quota tracking updated after every file upload and nightly for DB size

### Right to Be Forgotten
- No individual response purge on request
- If an organisation is deleted: all org data purged after 30-day grace period
- Purge covers: responses, files, users, projects, forms, analyses, dashboards

### Compliance Behavior (when standard adopted by org)
- `GDPR`: Enables data retention UI, adds consent checkbox option to forms, enables right-to-erasure workflows
- `HIPAA`: Enforces audit logging on all data access, forces TLS, enables BAA acknowledgment flow
- `ISO 27001`: Enables security incident logging, enforces password complexity policy
- All: Add compliance badge to forms/responses

---

## 14. DEPLOYMENT ARCHITECTURE

### Docker Compose Services
```yaml
services:
  nginx:      ← Port 80/443, reverse proxy to Flask + serves Flutter web build
  flask_api:  ← Gunicorn, multiple workers, internal port 5000
  celery_worker: ← Celery worker pool (concurrency=4 default)
  celery_beat:   ← APScheduler + Celery beat for cron tasks
  mongodb:    ← Port 27017 (internal only)
  redis:      ← Port 6379 (internal only)
  elasticsearch: ← Port 9200 (internal only)
  flower:     ← Celery monitoring UI (admin access only, internal port 5555)
```

### Environment Variables Required (.env)
```
FLASK_ENV=production
SECRET_KEY=
JWT_SECRET_KEY=
MONGODB_URI=mongodb://mongodb:27017/formbuilder
REDIS_URL=redis://redis:6379/0
ELASTICSEARCH_URL=http://elasticsearch:9200
EMAIL_API_URL=https://rpcapplication.aiims.edu/services/api/v1/mail/single
EMAIL_API_TOKEN=
SMS_API_URL=https://rpcapplication.aiims.edu/services/api/v1/sms/single
SMS_API_TOKEN=
UPLOADS_ROOT=/var/uploads
MAX_UPLOAD_SIZE_PDF=52428800
MAX_UPLOAD_SIZE_VIDEO=314572800
MAX_UPLOAD_SIZE_IMAGE=52428800
MAX_UPLOAD_SIZE_OTHER=104857600
CELERY_CONCURRENCY=4
CORS_ORIGINS=
PLATFORM_VERSION=1.0.0
```

### Update Mechanism
- Admin panel in Flutter app triggers version upgrade
- Backend calls Docker API to pull new image and perform rolling restart
- Zero-downtime preferred via Nginx upstream swap
- Maintenance window mode: set via system_config.maintenance_mode = true

---

## 15. CODING STANDARDS SUMMARY

### Python
- Follow PEP 8
- Type hints on all functions
- Pydantic models for request/response validation
- Services layer handles business logic (routes are thin)
- All DB operations in service layer, never in routes
- All errors return structured JSON: `{ "error": { "code": "...", "message": "...", "details": {} } }`
- HTTP status codes: 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable Entity, 500 Internal Server Error

### Dart/Flutter
- Follow Dart style guide + flutter_lints
- Feature-first folder structure
- All API calls go through a service class
- Riverpod providers for all state
- Separate repository layer for data access
- No business logic in widgets
- All user-visible strings in l10n (en first)

---

## 16. PHASE BOUNDARIES

### Phase 1: Foundation
Docker, Flask shell, MongoDB, Redis, Auth (JWT+roles+invites), Org/User CRUD,
Plugin engine (loader, sandbox, registry), Concept registry seeding,
Flutter app shell (routing, auth screens, org switcher), Audit log

### Phase 2: Form Builder
Form versioning engine, Form Builder UI (drag-drop), JSON UI Engine (primitives),
Formula builder modal, Skip logic property panel, Fetch action button,
Form Viewer + response collection, Draft save + offline sync (basic),
Resumable file uploads, Form templates, Git-style merge UI

### Phase 3: Analysis Coder
Node graph canvas, DAG execution engine, All built-in node types,
Scheduled execution, Elasticsearch integration, Export engine (CSV/Excel/PDF),
Analysis result caching + run history

### Phase 4: Dashboard Builder
Free-form canvas, All built-in widget types, Data binding to analyses,
Auto-refresh, Public dashboard sharing

### Phase 5: Advanced Platform
Compliance registry + behavioral enforcement, Full notification engine,
Webhook system + delivery log, Public REST API + OAuth + API keys + rate limiting,
Storage quota management, Update mechanism, Full admin panel,
Audit log search + archiving

### Phase 6: LLM Integration
LLM as analysis node type, LLM form builder assistant,
Natural language dashboard queries

---

## 17. API VERSIONING STRATEGY

- All public REST API routes: `/api/v1/...`
- Internal (Flutter) API routes: `/api/internal/v1/...`
- Breaking changes require new version: `/api/v2/...`
- Deprecated endpoints return `Deprecation` header with sunset date
- API version in response header: `X-API-Version: 1.0.0`
