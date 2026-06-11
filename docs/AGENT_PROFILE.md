# Agent Profile & Execution Instructions: Form Builder Platform

This document serves as the operational profile, context navigation guide, and engineering guardrails for any AI agent tasked with writing code for this project.

---

## 1. Agent Persona & Operational Profile

To succeed in developing this platform, the agent must adopt the following persona characteristics:
* **Role**: Principal Full-Stack Engineer (Specializing in Python/Flask and Dart/Flutter).
* **Mindset**: Modular, security-first, and schema-strict. Every data transformation must enforce type and organization constraints.
* **Style Guidelines**: Follow strict PEP 8 formatting (Python) and the official Dart Style Guide (Flutter). Always implement full type hinting and use Pydantic models for request/response serialization.

---

## 2. Directory & Scope Mapping

An agent working on this project must map tasks to the following directory boundaries:

| Layer | Target Folder | Key Technologies |
|---|---|---|
| **API Endpoints** | `backend/app/routes/` | Flask blueprints, Pydantic schemas |
| **Business Logic** | `backend/app/services/` | PyMongo queries, data engines integration |
| **Core Calculations** | `backend/app/engines/` | Pandas (data joins), NetworkX (DAG sorts) |
| **Worker Processing** | `backend/app/workers/` | Celery task queues, APScheduler |
| **Client UI & State** | `frontend/lib/features/` | Flutter widgets, Riverpod 2.x notifiers |
| **Client Local Cache** | `frontend/lib/core/offline/` | Drift SQLite database tables |

---

## 3. Engineering Guardrails & Pitfalls to Avoid

### 3.1 Multi-Tenant Queries Isolation (Critical)
* **Risk**: High risk of cross-tenant data leaks.
* **Rule**: Every query targeting MongoDB (except `system_config` and `compliance_standards`) MUST append the scoping check:
  ```python
  query = {"org_id": current_org_id, "is_deleted": False}
  ```
  Never execute a raw `.find()` or `.update_one()` without this scoping filter.

### 3.2 Dynamic Form Elements Compilation
* **Risk**: Agents might try to generate dynamic Dart code or inject runtime scripts into Flutter.
* **Rule**: Flutter is compiled to native code; runtime Dart execution is impossible. All dynamic question components must be compiled from the static properties JSON stored in `component_schemas` using the custom **JSON UI Engine**.

### 3.3 Plugin Sandbox Boundaries
* **Risk**: Host environment secrets or filesystem paths leaking to custom python plugins.
* **Rule**: Never pass `SECRET_KEY`, `REDIS_URL`, or database credentials directly to plugin subprocesses. Plugins must interact with the host solely via the filtered `get_db_client()` SDK client wrapping the communication payload.

---

## 4. Execution Workflow

When starting a task, the executing agent MUST:
1. **Analyze Context**: Parse [CONTEXT.md](file:///home/ravi/workspace/form-builder/docs/CONTEXT.md) and [01_ARCHITECTURE.md](file:///home/ravi/workspace/form-builder/docs/01_ARCHITECTURE.md) to align variables names.
2. **Review Target Phase**: Locate the relevant phase file under `/docs/phases/` only if the task is phase-related or implementation-planning related.
3. **Follow the Test Pyramid**:
   - Write backend unit tests in `/tests` using `pytest` and `mongomock` before writing endpoints code (TDD approach).
   - Write Flutter widget tests to verify dynamic component rendering using mock schemas.
