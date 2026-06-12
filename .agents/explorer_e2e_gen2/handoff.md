# E2E Exploration Report

## 1. Observation
Below are the exact implementation locations and details observed in the codebase for each of the 4 features, along with test execution runners.

### F1: Dynamic Group Rules
- **Backend Service Evaluation**: Implemented in `backend/app/services/auth_service.py` (lines 145–213).
  - `evaluate_dynamic_rule_condition(cond: dict, candidate: dict) -> bool` (line 145): Standardizes type for string comparisons and supports operators: `equals`, `eq`, `not_equals`, `ne`, `contains`, `starts_with`, `ends_with`, and `in`.
  - `evaluate_dynamic_rule(r: dict, candidate: dict) -> bool` (line 174): Recursively evaluates conditions under logical operators `AND`, `OR`, `NOT`.
  - `is_user_in_group(user_doc, membership, group)` (line 193): Extracts user properties (`role`, `membership_status`, `email`, `full_name`, `status`) to build the candidate dictionary passed to rule evaluation.
- **Backend Blueprint API**: Implemented in `backend/app/routes/auth.py` (lines 374–382) under route `@admin_bp.route("/orgs/<org_id>/groups", methods=["POST"])` which calls `create_group(..., dynamic_rule=data.get("dynamic_rule"))`.
- **Frontend Rule Builder**: Implemented in `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart` (lines 7–264).
  - Handles logical operator selection (`AND` or `OR`) and updates a list of conditions matching fields (`role`, `email`, `full_name`, `status`, `membership_status`) and operators (`equals`, `not_equals`, `contains`, `starts_with`, `ends_with`, `in`) via the `onChanged` callback.
- **Pre-existing Tests**: `frontend/test/e2e/e2e_dynamic_groups_test.dart` and `frontend/test/dynamic_group_rule_builder_test.dart`.

### F2: AST Formula calculations engine
- **Backend Evaluator**: Implemented in `backend/app/engines/analysis_engine.py` (lines 145–159): `evaluate_formula(data, target_col: str, formula: str) -> list` parses formulas utilizing pandas `df.eval(formula)` (used primarily by the analysis worker).
- **Frontend Parser**: Implemented in `frontend/lib/core/formula/formula_parser.dart` (lines 1–142):
  - Defines AST nodes: `ExpressionNode`, `NumberNode`, `VariableNode`, and `BinaryOpNode` (line 21) which implements `+`, `-`, `*`, `/`, `%` with a fallback to `0.0` for division/modulo by zero (line 35-36) and missing variables (line 18).
- **Frontend Cascading Recalculation**: Implemented in `frontend/lib/features/form_builder/providers/form_builder_provider.dart` (lines 493–544):
  - `evaluateFormulas(List<FormSection> sections)` loops up to 5 iterations (line 510) to compute cascading formulas and prevent infinite loops in the presence of circular references.
- **Pre-existing Tests**: `frontend/test/e2e/e2e_formula_calculations_test.dart`, `frontend/test/formula_eval_integration_test.dart`, and `frontend/test/formula_parser_test.dart`.

### F3: Compliance Legal Holds & Quotas
- **Backend Legal Holds Service**: Implemented in `backend/app/services/compliance_service.py` (lines 1–71):
  - `is_resource_held(target_type, target_id)` (line 47) recursively checks if a resource is directly held or inherits a hold from its parent (e.g. form inherits from project, response inherits from form).
- **Backend Compliance API**: Implemented in `backend/app/routes/compliance.py` (lines 1–94) mapping holds CRUD endpoints (`GET /api/orgs/<org_id>/compliance/holds`, `POST /api/orgs/<org_id>/compliance/holds`, `PUT /api/compliance/holds/<hold_id>`).
- **Backend Quota Service**: Implemented in `backend/app/services/quota_service.py` (lines 1–64):
  - `calculate_organization_quota` (line 35) sums directory size under `uploads/{org_id}/` and DB data size from `dbstats`, updating MongoDB.
  - `enforce_org_quota(org_id, requested_bytes=0)` (line 55) raises `ValueError("Organization quota exceeded")`.
- **Backend Celery Worker**: Implemented in `backend/app/workers/quota_tasks.py` (lines 12–15) triggering quota updates.
- **Backend Enforcement Interceptors**:
  - `backend/app/routes/forms.py` (lines 715, 729) blocks deleting forms and responses if held, returning HTTP 409 `LEGAL_HOLD_ACTIVE`.
  - `backend/app/routes/forms.py` (lines 264–270) blocks form creation if quota is exceeded, returning HTTP 403 `QUOTA_EXCEEDED`.
- **Frontend Compliance UI**: Implemented in `frontend/lib/features/compliance/presentation/pages/compliance_page.dart` (lines 1–308):
  - Displays storage quota using `LinearProgressIndicator` (line 199) and displays a warning banner when usage exceeds 80% (line 216).
  - Lists legal holds and includes a Switch to toggle their active state (line 293).
- **Pre-existing Tests**: `frontend/test/compliance_page_test.dart` and `backend/tests/test_compliance.py`, `backend/tests/test_quota.py`.

### F4: Drag-and-Drop Canvas
- **Backend Dashboard Blueprint**: Implemented in `backend/app/routes/dashboard.py` (lines 1–611) supporting dashboard CRUD operations, canvas saving (`PUT /api/internal/v1/dashboards/<dashboard_id>/canvas`), resolving widget data, snapshots, and public token revocation.
- **Backend Dashboard Service**: Implemented in `backend/app/services/dashboard_service.py` (lines 97–709):
  - `save_canvas(dashboard_id, canvas, context=None)` (line 374) validates canvas dimensions, widget types, coordinate bounds, z-index ranges, and bound analysis node schemas.
- **Frontend Canvas Rendering**: Implemented in `frontend/lib/features/dashboard_builder/canvas/dashboard_canvas.dart` (lines 1–81) rendering `InteractiveViewer` with `CanvasGrid` overlay and `DraggableWidgetWrapper`s.
- **Frontend Gesture Wrapper**: Implemented in `frontend/lib/features/dashboard_builder/widgets/draggable_widget_wrapper.dart` (lines 1–173) binding tap, pan-drag, pan-resize, and lock icons to riverpod provider actions.
- **Frontend Coordinate Logic**: Implemented in `frontend/lib/features/dashboard_builder/providers/canvas_state_provider.dart` (lines 1–506):
  - `moveWidget` (line 222) snaps and clamps position:
    ```dart
    final snappedX = _snap(x).clamp(0.0, state.canvasWidth - w.size.width);
    final snappedY = _snap(y).clamp(0.0, state.canvasHeight - w.size.height);
    ```
  - `resizeWidget` (line 235) snaps and clamps width, height, and positions.
  - Snapping mechanism `_snap(double val)` (line 128) rounds values to intervals of `state.gridSize` (clamped between 4 and 64).
- **Pre-existing Tests**: `backend/tests/test_dashboard.py` (no pre-existing E2E frontend canvas tests).

---

## 2. Logic Chain
- **F1 (Dynamic Groups)**: The backend evaluator matches candidate properties against JSON structures generated by `DynamicGroupRuleBuilder`. E2E tests must verify both the UI builder outputting correct JSON schemas and the backend service correctly resolving user membership filters based on those schemas.
- **F2 (AST Engine)**: Cascadings run exclusively client-side via Riverpod (`form_builder_provider.dart`) and evaluate formulas up to 5 times. Backend simply receives the submitted form responses. Thus, E2E calculations can be thoroughly verified through Flutter widget tests, while backend tests verify database storage.
- **F3 (Compliance & Quota)**: deletion and creation restrictions are enforced via HTTP 409 (`LEGAL_HOLD_ACTIVE`) and HTTP 403 (`QUOTA_EXCEEDED`) status codes. On the frontend, visual progressive bars reflect storage usage. E2E tests should trigger these limit breaches (e.g. mock DB quota state) and assert proper API response codes and UI warning banners.
- **F4 (Dashboard Canvas)**: Drag-and-drop snapping and clamping boundaries are processed entirely inside the Flutter Riverpod State Notifier, which saves the coordinates to MongoDB. E2E tests should verify dragging gestures, clamping boundaries, grid snapping in Flutter integration tests, and check that correct coordinates are stored and loaded from the backend APIs.
- **Test Environments**: Running the test suites verified that:
  - Python tests can be run using the virtual environment's `pytest` command since `TestingConfig` isolates the DB via `mongomock://localhost`.
  - Flutter tests can be run using the `flutter test` command.

---

## 3. Caveats
- No actual code modifications were made.
- Background Celery worker tasks execution details were not run in a production Celery setup, but rather isolated in unittest mock runners.
- The project assumes standard network isolation in pytest configuration where Elasticsearch (`search_service.py`) is bypassed or mocked.

---

## 4. Conclusion
The implementation locations of the 4 features have been fully mapped. 

### Design Suggestions for E2E Tests:
1. **Backend Tests (`backend/tests/e2e/`)**:
   - `conftest.py`: Establish setup/tear-down fixtures for orgs, projects, forms, legal holds, and storage quotas.
   - `test_e2e_dynamic_groups.py`: Call groups API endpoints and verify user evaluation outputs.
   - `test_e2e_compliance_quota.py`: Insert legal holds and storage quota blocks; verify delete and create calls fail with correct HTTP codes (`409` and `403`).
   - `test_e2e_workflows.py`: Chain workflows: Place hold -> attempt delete (fail) -> release hold -> delete (succeed).
2. **Frontend Tests (`frontend/test/e2e/`)**:
   - `e2e_compliance_quota_test.dart`: Render `CompliancePage` with >80% usage and verify progressive indicator turns warning color and displays banner.
   - `e2e_dashboard_canvas_test.dart`: Execute drag and resize gestures; verify coordinates snap to 8px/16px grids and clamp at canvas boundaries.
   - `e2e_workflows_test.dart`: Binds a KPI card widget to an AST calculation formula and simulates updates based on form field inputs.

---

## 5. Verification Method
To verify that tests execute correctly:
1. **Backend (Python)**:
   Navigate to `/home/ravi/workspace/form-builder/backend` and run:
   ```bash
   ../.venv/bin/pytest
   ```
2. **Frontend (Flutter)**:
   Navigate to `/home/ravi/workspace/form-builder/frontend` and run:
   ```bash
   flutter test
   ```
