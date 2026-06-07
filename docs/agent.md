# Agent Core Instructions (Low-Token Spec)

Minimize token ingestion by reading only this compressed spec for standard operations.

---

## 1. Stack & Paths
* **BE**: Py3.11+ / Flask 3 / Gunicorn / Celery 5 / PyMongo / Redis 7 / ES 8 / NetworkX. Paths: `backend/app/routes/`, `services/`, `engines/`, `workers/`.
* **FE**: Flutter 3 / Riverpod 2 / Drift SQLite. Paths: `frontend/lib/features/`, `core/offline/`.

## 2. Multi-Tenancy & Safety
* **DB Scoping**: Queries MUST filter `{"org_id": current_org_id, "is_deleted": False}`.
* **Privileges**: Plugins run via subprocess dropping rights to `nobody`. Blacklist: `os.system`, `subprocess`, `importlib`, `ctypes`, `socket`.
* **API Validation**: Enforce Pydantic schemas on input/output payload scopes.

## 3. Core Mechanics Shorthand
* **Git-Forms**: Schemas saved as commits in `form_commits`. Branches HEAD in `forms`. 3-way merges handle version updates.
* **DAG Coder**: NetworkX validates cycles, computes `topological_sort`. Celery executes steps, caches in `analysis_results`.
* **Offline Sync**: Client caches to Drift. Sync calls delta API `/sync?last_synced_at=TS`. Delete via `tombstones`.
* **Visual UI**: Frontend parses `component_schemas` JSON properties to render native Material 3 widgets at runtime.
* **Testing**: Python `pytest` + `mongomock` / Flutter unit + golden tests.

## 4. Key Collection Fields
* `users`: `email` (UQ), `password_hash`, `status: pending_approval|active|suspended`.
* `form_responses`: `answers: {q_id: {value, display_value, file_ids}}`.
* `analyses`: `graph: {nodes: [{id, type, properties}], edges: [{from_node, to_node}]}`.
* `dashboards`: `canvas: {width, height, widgets: [{id, type, position, size, data_binding}]}`.
* `tombstones`: `entity_type: forms|responses|projects`, `entity_id`, `deleted_at`.

## 5. Strict Operational Constraints
* **DO NOT EDIT DOCS**: The documentation files inside `/docs/` are finalized architectural specifications. DO NOT modify, overwrite, or edit these documents under any scenario.
* **Git Status**: Use standard Git commands (`git status`, `git diff`, `git log`) to verify code edits, monitor execution progress, and track overall project implementation status.

