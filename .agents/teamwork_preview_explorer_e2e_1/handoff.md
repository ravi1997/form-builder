# E2E Test Suite Projections and Component Analysis Report

This report analyzes the components, existing tests, and details the E2E test plan following the 4-tier testing methodology for the Form Builder Platform's 4 major features.

---

## 1. Observation

We performed a comprehensive code review of the Form Builder Platform codebase. Below are the exact locations, file paths, line numbers, and implementation details observed for each of the 4 features:

### Feature 1: Dynamic Group Rules
*   **Backend Service (`backend/app/services/auth_service.py`):**
    *   Lines 463–539: Definition of `resolve_group_members(group: dict, org_id: str)`.
        *   Lines 468–473: Handles `dynamic` groups by fetching active memberships in the org:
            ```python
            memberships = list(mongo.db.org_memberships.find({
                "org_id": _oid(org_id),
                "status": "active",
                "is_deleted": False,
            }))
            ```
        *   Lines 481–523: Evaluates operators (`equals`/`eq`, `not_equals`/`ne`, `contains`, `starts_with`, `ends_with`, `in`) and logical operators (`AND`, `OR`, `NOT`) against candidate dictionary keys: `role`, `membership_status`, `email`, `full_name`, `status`.
    *   **Backend Routes (`backend/app/routes/auth.py`):**
        *   Lines 365–382: Routes for managing groups. `POST /orgs/<org_id>/groups` creates groups accepting dynamic rules in request payload.
    *   **Frontend Widget (`frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`):**
        *   Lines 5–17: `DynamicGroupRuleBuilder` is a `StatefulWidget` editing `Map<String, dynamic>? initialRule` and notifying parent via `ValueChanged<Map<String, dynamic>> onChanged`.
        *   Lines 23–38: Supported fields: `role`, `email`, `full_name`, `status`, `membership_status`. Operators: `equals`, `not_equals`, `contains`, `starts_with`, `ends_with`, `in`.
        *   Lines 113–160: Logical operator dropdown (`AND`, `OR`) and "Add Condition" button.

### Feature 2: AST Formula Calculations Engine
*   **Frontend AST Core (`frontend/lib/core/formula/formula_parser.dart`):**
    *   Lines 1–40: AST node representations (`ExpressionNode`, `NumberNode`, `VariableNode`, `BinaryOpNode`) supporting operations `+`, `-`, `*`, `/`, `%` and guarding against division by zero (returning `0.0`).
    *   Lines 42–141: Recursive descent parser in `FormulaParser` that tokenizes and parses parenthesis `()`, unary signs, variable identifiers, and floating-point numeric literals.
*   **Frontend Recalculation Flow (`frontend/lib/features/form_builder/providers/form_builder_provider.dart`):**
    *   Lines 493–544: `FormPlayNotifier.evaluateFormulas(List<FormSection> sections)` translates answered field values to double variables, parses and evaluates formula properties stored in `q.calculations`, and iterates up to 5 times (lines 510–539) to handle cascading/dependent field recalculations safely.

### Feature 3: Compliance Legal Holds & Quotas UI
*   **Backend Compliance Service (`backend/app/services/compliance_service.py`):**
    *   Lines 10–22: `create_legal_hold(...)` creates a hold targeting `"project"`, `"form"`, or `"response"`.
    *   Lines 47–70: `is_resource_held(target_type, target_id)` determines if a resource is locked under a hold, recursively checking its parents (response -> form -> project).
*   **Backend Storage Quotas Service (`backend/app/services/quota_service.py`):**
    *   Lines 35–52: `calculate_organization_quota(org_id)` sums uploaded files in `uploads/{org_id}/` and database data size, checking against `warning_threshold` (defaulting to 0.8).
    *   Lines 55–62: `enforce_org_quota(org_id, requested_bytes)` blocks operations by raising a `ValueError("Organization quota exceeded")`.
*   **Backend Routes & Blockers:**
    *   `backend/app/routes/compliance.py` (Lines 29–93): Administrative compliance routes to view, create, and toggle holds (`GET/POST /api/orgs/<org_id>/compliance/holds`, `PUT /api/compliance/holds/<hold_id>`).
    *   `backend/app/routes/forms.py` (Lines 702–733): Blocks deletion of forms and responses when held, returning 409 status code with error `{"code": "LEGAL_HOLD_ACTIVE", ...}`.
*   **Frontend Page (`frontend/lib/features/compliance/presentation/pages/compliance_page.dart`):**
    *   Lines 147–231: Progress bar displaying organization storage usage ratio. When `usageRatio >= _warningThreshold` (80%), the border turns amber and displays warning label: `'Warning: Near storage limit'`.
    *   Lines 235–301: Renders holds listing with Switches that toggle active states and an "Add Legal Hold" dialog.

### Feature 4: Drag-and-Drop Dashboard Canvas
*   **Frontend Canvas Widgets (`frontend/lib/features/dashboard_builder/canvas/`):**
    *   `dashboard_canvas.dart` (Lines 22–69): Wraps stack containing a `CanvasGrid` overlay and child widgets with `InteractiveViewer` supporting pan and zoom scales (0.25 to 2.0).
    *   `draggable_widget_wrapper.dart` (Lines 75–160): Handles gesture detection: `onPanStart`/`onPanUpdate` to trigger movements and a bottom-right circular anchor to resize widgets on the grid.
*   **Frontend State (`frontend/lib/features/dashboard_builder/providers/canvas_state_provider.dart`):**
    *   Lines 128–131: Snaps coordinates to grid if enabled:
        ```dart
        double _snap(double val) {
          if (!state.snapToGrid) return val;
          return (val / state.gridSize).round() * state.gridSize.toDouble();
        }
        ```
    *   Lines 133–159: Retains an undo/redo history stack of up to 50 states.
    *   Lines 222–252: Moves and resizes widgets relative to canvas width/height boundaries, clamping sizes between 20.0 and maximum canvas size.

### Analysis of Existing Tests
1.  **Dynamic Group Rules**: Tested in `backend/tests/test_auth.py` (lines 133–193). Covers pytest database insertion and membership resolutions on AND/OR compound conditions. No frontend tests exist.
2.  **AST Formula calculations**: Tested in `frontend/test/formula_parser_test.dart` (unit parser testing) and `frontend/test/formula_eval_integration_test.dart` (integration testing Riverpod notifications).
3.  **Compliance Legal Holds & Quotas**: Backend tested in `backend/tests/test_compliance.py` (checks deletion blocked by 409) and `backend/tests/test_quota.py` (checks creation blocked by 403). Frontend tested in `frontend/test/compliance_page_test.dart` (renders indicators and toggles holds).
4.  **Drag-and-Drop Dashboard Canvas**: NO dedicated tests exist in `frontend/test` for dashboard building or canvas gestures.

---

## 2. Logic Chain

From these observations, we conclude:
1.  **Unified Schema Mapping**: The backend services and frontend widgets share identical rule fields (`role`, `email`, `full_name`, etc.) and operators, which simplifies E2E validation of JSON structure passing.
2.  **Cascading Recalculation Limits**: The 5-iteration limit in `evaluateFormulas` avoids infinite loops. E2E tests must verify this boundary to ensure the UI does not hang when cyclical calculations occur.
3.  **Test Gaps**: The complete absence of Dashboard Canvas tests indicates a critical area for testing.
4.  **Verification Flow**: We can verify test suites by running `../.venv/bin/pytest` and `flutter test` directly.

---

## 3. Caveats

*   No live databases or services were modified, in compliance with the read-only investigation constraint.
*   Assumes the implementer will execute E2E tests within the virtual environment environment (`../.venv/bin/pytest`) and the Flutter SDK environment.

---

## 4. Conclusion & Proposed E2E Test Plan

We propose adding E2E scenarios across two new files:
- Backend: `backend/tests/test_e2e_scenarios.py`
- Frontend: `frontend/test/e2e_scenarios_test.dart`

### Tier 1: Feature Coverage (Total: 20 tests)
*   **Dynamic Group Rules (5 tests)**:
    1.  `test_group_creation`: Verify dynamic group creation via `POST /api/orgs/<org_id>/groups` stores the rules in the DB.
    2.  `test_resolve_members_single`: Verify `resolve_group_members` isolates a single rule.
    3.  `test_resolve_members_compound`: Verify compound AND/OR resolution.
    4.  `test_widget_rendering`: Flutter Widget test showing fields are listed in `DynamicGroupRuleBuilder`.
    5.  `test_widget_change_callback`: Verify `onChanged` is invoked with correct rule map when conditions are updated.
*   **AST Formula Engine (5 tests)**:
    6.  `test_ast_arithmetic`: Verify AST parser processes complex operators with correct order of operations.
    7.  `test_ast_variables`: Verify AST variables evaluation using a variable mappings catalog.
    8.  `test_zero_division`: Verify division/modulo by zero returns 0.0.
    9.  `test_integration_recalculation`: Integration test asserting answers recalculate when dependent fields modify.
    10. `test_integration_cascading`: Assert cascading dependencies resolve correctly.
*   **Compliance Legal Holds & Quotas UI (5 tests)**:
    11. `test_deletion_block`: Assert deleting held form/response returns 409 `LEGAL_HOLD_ACTIVE`.
    12. `test_hold_inheritance`: Verify hold status propagation from Project -> Form -> Response.
    13. `test_quota_calculation`: Assert correct calculation of directory uploads size + database dataSize.
    14. `test_quota_warning_ui`: Widget test verifying warning banner turns amber when usage exceeds 80%.
    15. `test_quota_creation_block`: Assert form creation is blocked when organization quota is 100% exceeded.
*   **Drag-and-Drop Dashboard Canvas (5 tests)**:
    16. `test_canvas_mode_toggle`: Verify CanvasState mode switches and clears selections.
    17. `test_grid_snapping`: Assert coordinates snap onto the configured grid spacing.
    18. `test_canvas_boundaries`: Verify moved widgets are locked within the canvas dimensions boundaries.
    19. `test_canvas_undo_redo`: Assert history stack records undo/redo steps up to 50 operations.
    20. `test_widget_locking`: Verify moving/resizing is blocked when a widget is locked.

### Tier 2: Boundary/Corner Cases (Total: 20 tests)
*   **Dynamic Group Rules (5 tests)**:
    1.  Empty rules: Resolves to all org members.
    2.  Missing fields in condition: Defaults to False gracefully.
    3.  Null and empty type check comparison.
    4.  Invalid operators: Fallback to False gracefully.
    5.  Scale tests: Resolving groups containing 10,000+ members.
*   **AST Formula Engine (5 tests)**:
    6.  Circular loop: Verify execution terminates at 5 iterations.
    7.  Unary signs, negative numbers, and floating-point parses.
    8.  Malformed parentheses syntax throws handled exceptions.
    9.  Undefined variables default to 0.0.
    10. Floating overflow/underflow handling.
*   **Compliance Legal Holds & Quotas UI (5 tests)**:
    11. Exactly 100.0% quota usage limits.
    12. Placing holds on soft-deleted resources does not trigger errors.
    13. Compound holds evaluation: Active project hold overrides inactive form hold.
    14. Concurrent delete requests during hold deactivation.
    15. Quota calculation when directory `uploads/{org_id}/` does not exist on disk.
*   **Drag-and-Drop Dashboard Canvas (5 tests)**:
    16. Extreme zIndex increments do not trigger integer overflow/underflow.
    17. Clamping zero or negative canvas sizes.
    18. Zoom limits constrained strictly between 0.25 and 2.0.
    19. Overlapping element alignments.
    20. Grid sizes clamped between 4 and 64 pixels.

### Tier 3: Cross-Feature Interactions (Pairwise combinations)
1.  **Dynamic Group Rules + Compliance Legal Holds**: Verify dynamic group members have standard access, but are blocked from deleting held forms/responses regardless of role permissions.
2.  **AST Formula + Drag-and-Drop Canvas**: Verify modifying data sources triggers AST recalculations and dashboard charts bound to calculations update dynamically.
3.  **Compliance/Quotas + Drag-and-Drop Canvas**: Verify dashboard saves are rejected with quota errors when storage limits are exceeded.
4.  **Dynamic Group Rules + AST Formula**: Conditionally display/hide AST calculation inputs and triggers depending on resolved user memberships.
5.  **Compliance Legal Holds + AST Formula**: Verify forms/responses under active holds block updates, preserving calculated values and preventing recalculation execution.

### Tier 4: Real-World Application Scenarios (5 complex workflows)
1.  **Audit Compliance Workflow**: Admin sets hold on Project -> Editor attempts delete and fails (409) -> Admin toggles hold inactive -> Editor successfully deletes form.
2.  **Dynamic Regional Assignment Survey**: User logs in -> Dynamic rules qualify Bob (Bob's email finishes survey) ->bob enters figures -> AST evaluates margins -> Bob submits -> Alice fails criteria and is rejected.
3.  **Real-Time Quota Warning in Dashboard Session**: Dashboard editor drags elements onto Canvas -> background job pushes storage over 80% -> Amber warning banner displays on canvas in real-time -> User locks layout and saves.
4.  **Quota Recovery & Form Creation**: Quota is exceeded (100% full) -> Admin form creation fails -> Admin clears deleted files -> Quota drops to 70% -> Admin successfully builds form.
5.  **Interactive Canvas Layout Tune**: Drag Line Chart -> Snap to 16px grid -> Resize widget -> Accidental move -> Tap Undo to recover -> Apply property changes -> Redo -> Lock widget -> Save.

---

## 5. Verification Method

To execute and verify the E2E test suites proposed:

### Backend test verification
Run command in `/home/ravi/workspace/form-builder/backend`:
```bash
../.venv/bin/pytest tests/test_e2e_scenarios.py
```
To run all tests and verify all pass successfully:
```bash
../.venv/bin/pytest
```

### Frontend test verification
Run command in `/home/ravi/workspace/form-builder/frontend`:
```bash
flutter test test/e2e_scenarios_test.dart
```
To run all tests and verify all pass successfully:
```bash
flutter test
```
