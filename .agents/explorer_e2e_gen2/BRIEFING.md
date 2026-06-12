# BRIEFING — 2026-06-12T14:16:15+05:30

## Mission
Investigate form-builder codebase (backend & Flutter frontend) to map feature implementations and test environment for designing the E2E test suite.

## 🔒 My Identity
- Archetype: Teamwork explorer
- Roles: Read-only investigator, analyzer
- Working directory: /home/ravi/workspace/form-builder/.agents/explorer_e2e_gen2
- Original parent: a23014f4-82cf-4e1f-85cf-b748ddc58318
- Milestone: E2E Exploration & Analysis

## 🔒 Key Constraints
- Read-only investigation — do NOT implement.
- Do not run any tests that write to shared global state.
- Focus on mapping Dynamic Group Rules, AST Formula Engine, Compliance Legal Holds & Quotas, and Drag-and-Drop Canvas.

## Current Parent
- Conversation ID: a23014f4-82cf-4e1f-85cf-b748ddc58318
- Updated: not yet

## Investigation State
- **Explored paths**: 
  - Backend: `backend/app/services/auth_service.py`, `backend/app/routes/identity.py`, `backend/app/routes/auth.py`, `backend/app/services/quota_service.py`, `backend/app/workers/quota_tasks.py`, `backend/app/services/compliance_service.py`, `backend/app/routes/compliance.py`, `backend/app/routes/forms.py`, `backend/app/services/dashboard_service.py`, `backend/app/routes/dashboard.py`, `backend/tests/conftest.py`, `backend/tests/test_identity.py`, `backend/tests/test_compliance.py`, `backend/tests/test_quota.py`, `backend/tests/test_dashboard.py`
  - Frontend: `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`, `frontend/lib/core/formula/formula_parser.dart`, `frontend/lib/features/form_builder/providers/form_builder_provider.dart`, `frontend/lib/features/compliance/presentation/pages/compliance_page.dart`, `frontend/lib/features/dashboard_builder/canvas/dashboard_canvas.dart`, `frontend/lib/features/dashboard_builder/widgets/draggable_widget_wrapper.dart`, `frontend/lib/features/dashboard_builder/providers/canvas_state_provider.dart`, `frontend/test/compliance_page_test.dart`, `frontend/test/e2e/e2e_dynamic_groups_test.dart`, `frontend/test/e2e/e2e_formula_calculations_test.dart`
- **Key findings**:
  - Backend uses `mongomock` in `TestingConfig`, which isolates testing from shared global database.
  - Cascade formulas run up to 5 iterations for circular references detection.
  - Progressive storage bar is part of `CompliancePage` widget.
  - Coordinate clamping and snapping are calculated in the `CanvasStateNotifier` provider.
- **Unexplored areas**: None. Codebase exploration is complete.

## Key Decisions Made
- Mapped all 4 features on backend and frontend code bases.
- Documented testing commands and mock fixtures.

## Artifact Index
- /home/ravi/workspace/form-builder/.agents/explorer_e2e_gen2/handoff.md — E2E exploration report
