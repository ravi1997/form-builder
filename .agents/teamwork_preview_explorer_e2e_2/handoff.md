# Handoff Report: E2E Test Suite Design Plan

## 1. Observation
The codebase was inspected using filesystem search and pattern matching, revealing the backend and frontend components for each of the four target features, as well as the existing test suites.

### Feature 1: Dynamic Group Rules
- **Backend Components**:
  - `backend/app/services/auth_service.py` (line 463): Defines `def resolve_group_members(group: dict, org_id: str)` which evaluates a group's `dynamic_rule` with logical operators `AND`, `OR`, `NOT` and leaf conditions (`equals`, `eq`, `not_equals`, `ne`, `contains`, `starts_with`, `ends_with`, `in`) against membership attributes.
  - `backend/app/routes/auth.py` (line 374): Route `/api/admin/orgs/<org_id>/groups` to create static or dynamic groups.
- **Frontend Components**:
  - `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`: Widget that provides a UI to build dynamic rules visually.
- **Existing Tests**:
  - `backend/tests/test_auth.py` (line 133): `test_group_resolution_and_permission_helpers` tests basic `resolve_group_members` operation.
  - `backend/tests/test_auth.py` (line 146): `test_advanced_dynamic_rules` tests advanced evaluation of combined logical operators (`AND`, `OR`) and operators (`ends_with`, `contains`, `starts_with`).
  - No frontend widget tests exist for `DynamicGroupRuleBuilder`.

### Feature 2: AST Formula Calculations Engine
- **Backend Components**:
  - Calculations are handled entirely on the client-side. The backend has no representation of the calculations engine.
- **Frontend Components**:
  - `frontend/lib/core/formula/formula_parser.dart`: Custom parser implementing recursive descent parsing of mathematical expressions (supporting `+`, `-`, `*`, `/`, `%` and parentheses) with variable substitution.
  - `frontend/lib/features/form_builder/providers/form_builder_provider.dart` (line 493): `FormPlayNotifier.evaluateFormulas` iterates up to 5 times (cascading dependency resolver) using `FormulaParser` when a field value is modified via `setAnswer` (line 478).
- **Existing Tests**:
  - `frontend/test/formula_parser_test.dart`: Contains `FormulaParser basics` and `FormulaParser variables` unit tests.
  - `frontend/test/formula_eval_integration_test.dart`: Tests `formPlayProvider` integration with a mock `FormulaTestFormBuilderNotifier` ensuring that inputs automatically evaluate cascading formulas.

### Feature 3: Compliance Legal Holds & Quotas UI
- **Backend Components**:
  - `backend/app/services/compliance_service.py`: Implements CRUD for legal holds (`create_legal_hold`, `list_legal_holds`, `toggle_legal_hold`, `is_resource_held`). Holds prevent deletion of `project`, `form`, or `response` resources.
  - `backend/app/services/quota_service.py`: Performs directory calculation of files and dbstats (`calculate_organization_quota`) and enforces limits on resource additions (`enforce_org_quota`).
  - `backend/app/routes/compliance.py`: Exposes routes under `/api` for listing, creating, and toggling holds.
  - `backend/app/routes/forms.py` (line 264): Calls `enforce_org_quota` to block form creation when quotas are exceeded.
- **Frontend Components**:
  - `frontend/lib/features/compliance/presentation/pages/compliance_page.dart`: Page displaying the storage quota usage bar, rendering warning thresholds (amber highlight above 80%), listing active holds, and rendering switches to toggle holds.
- **Existing Tests**:
  - `backend/tests/test_quota.py`: `test_form_creation_blocked_when_quota_exceeded` tests that `QUOTA_EXCEEDED` is returned if quotas are exceeded.
  - `frontend/test/compliance_page_test.dart`: Widget test checking `CompliancePage` rendering, title, storage warning text, hold lists, and switch toggling.

### Feature 4: Drag-and-Drop Dashboard Canvas
- **Backend Components**:
  - `backend/app/routes/dashboard.py`: Defines CRUD routes for dashboards, saving canvases, compiling widget data with bound analysis node results, and token-based public sharing.
- **Frontend Components**:
  - `frontend/lib/features/dashboard_builder/canvas/dashboard_canvas.dart`: Renders widgets on a 2D canvas wrapped in `InteractiveViewer` with `CanvasGrid` overlay and `DraggableWidgetWrapper`.
  - `frontend/lib/features/dashboard_builder/canvas/canvas_grid.dart`: Grid layout helper.
  - `frontend/lib/features/dashboard_builder/widgets/draggable_widget_wrapper.dart`: Widget wrapper handling drag/positioning.
- **Existing Tests**:
  - `backend/tests/test_dashboard.py`: Contains `test_dashboard_crud`, `test_canvas_save_and_resolution`, `test_snapshots`, and `test_public_sharing`.
  - No frontend tests exist for dashboard canvas, widgets, or dragging.

---

## 2. Logic Chain
1. **Dynamic Group Rules** logic is split: backend computes target members based on rule JSON, and frontend builds rules visually. E2E verification must verify that visual rule building on the frontend translates to correct membership results and permission policies on the backend.
2. **AST Formula engine** is frontend-only, but its calculations determine submitted response data. E2E tests must verify that typing in formula-based inputs yields correct computed values which are then sent to and correctly stored by the backend.
3. **Compliance & Quotas** restrict write operations (holds block delete, quotas block create). E2E tests must simulate these blocking actions across the frontend interface and verify that backend errors (e.g., `403 QUOTA_EXCEEDED`) translate to proper warnings and blocked states in the UI.
4. **Drag-and-Drop Dashboard Canvas** features rich interactive positioning on the client side, while the layout coordinates and widget configurations are saved on the backend database. E2E tests must simulate dragging and dropping components and ensure they are parsed, saved to the database, and rendered correctly on page refresh.

---

## 3. Caveats
- The execution of E2E tests assumes that a mock or test MongoDB instance and a local Python Flask server are running during the frontend integration test run.
- Mobile browser drag-and-drop interactions are modeled as touch gestures, which may differ slightly from mouse drag events in desktop E2E testing.
- Network requests are isolated as local server calls since we are operating in `CODE_ONLY` network mode.

---

## 4. Conclusion & E2E Test Plan
To systematically test these features, we propose a 4-tier E2E testing plan using `pytest` for backend API E2E flows and `flutter test` (via `integration_test` package) for client-server integration.

### Tier 1: Feature Coverage (Total: 20 tests, 5 per feature)

#### Feature 1: Dynamic Group Rules
- **E2E-F1-1: End-to-End Rule Creation and Member Listing**
  - Use `DynamicGroupRuleBuilder` to construct a rule, save it, and assert the backend returns the correct members via `/api/admin/orgs/<org_id>/groups`.
- **E2E-F1-2: AND Condition Dynamic Evaluation**
  - Save an AND dynamic rule and assert that member list only includes users meeting all conditions.
- **E2E-F1-3: OR Condition Dynamic Evaluation**
  - Save an OR dynamic rule and assert that member list includes users meeting either condition.
- **E2E-F1-4: NOT Operator Membership Inversion**
  - Create a NOT rule (e.g. `NOT role == 'org_viewer'`) and verify members list excludes viewers.
- **E2E-F1-5: Permission Verification on Dynamic Group**
  - Verify that a user resolved dynamically into a group successfully acquires the group's custom permissions.

#### Feature 2: AST Formula Calculations Engine
- **E2E-F2-1: Basic Arithmetic Form Submission**
  - Fill numeric fields, verify formula calculation in play mode, submit form, and verify backend records the computed float.
- **E2E-F2-2: Cascading Variables Update**
  - Change input `q1` where `q_calc1 = q1 + 1` and `q_calc2 = q_calc1 * 2`, verify correct cascading recalculation in play mode.
- **E2E-F2-3: Parentheses Order of Operations**
  - Input values verifying `(q1 + q2) * q3` parses and computes with mathematical precedence.
- **E2E-F2-4: Modulo Operator Calculations**
  - Verify formula `q1 % q2` evaluates correctly and handles remainder logic in play mode.
- **E2E-F2-5: Unresolved Variable Defaulting**
  - Open a form with calculation nodes, leave inputs blank, and verify it defaults variables to `0.0`.

#### Feature 3: Compliance Legal Holds & Quotas UI
- **E2E-F3-1: Legal Hold Creation and Toggle in Admin UI**
  - Access `CompliancePage`, create a hold, toggle it on, and verify it persists as `is_active: true` in MongoDB.
- **E2E-F3-2: Deletion Blocker on Held Form**
  - Place a form on legal hold, try to delete it from the UI, and verify the deletion is blocked with a descriptive alert.
- **E2E-F3-3: Active Hold on Project Cascade**
  - Apply hold to a project, attempt deleting a child response of that project, and verify it is rejected.
- **E2E-F3-4: Quota Usage Alert Bar Rendering**
  - Seed database storage quota above the warning threshold, verify the amber warning bar displays on the `CompliancePage`.
- **E2E-F3-5: Form Creation Blocked when Quota Exceeded**
  - Seed quota to 100% used, click "Create Form", verify the UI alerts `QUOTA_EXCEEDED` and API rejects the post.

#### Feature 4: Drag-and-Drop Dashboard Canvas
- **E2E-F4-1: Widget Drag, Position, and Canvas Save**
  - Drag a KPI Card widget, drop it on the canvas at coordinate `(150, 250)`, save dashboard, reload, and verify coordinate values are persisted.
- **E2E-F4-2: Widget Overlapping and zIndex Modification**
  - Drop two widgets, change their overlapping order, and verify `zIndex` updates are correctly saved and rendered.
- **E2E-F4-3: Interactive Canvas Pan & Zoom**
  - Simulate pinch/zoom and pan gestures on `DashboardCanvas` and verify viewport transformations.
- **E2E-F4-4: Data Bound KPI Card Rendering**
  - Drag a KPI card, bind it to an analysis result, and verify it fetches and displays correct aggregate numeric values.
- **E2E-F4-5: Public Dashboard Sharing Toggle**
  - Enable sharing, fetch the dashboard using public token, verify layout displays correctly in read-only mode without grid lines.

---

### Tier 2: Boundary / Corner Cases (Total: 20 tests, 5 per feature)

#### Feature 1: Dynamic Group Rules
- **E2E-F1-B1: Empty Rule Membership**
  - Set `dynamic_rule` to empty object `{}` and verify the resolved members list is empty.
- **E2E-F1-B2: Missing Candidate Attributes**
  - Evaluate a rule targeting `email` against a user without an email field, verify it safely returns `False`.
- **E2E-F1-B3: Commas in "in" Operator**
  - Test the `in` operator with a comma-separated string, verifying matching elements are resolved correctly.
- **E2E-F1-B4: Complex Nested Logical Rules**
  - Test deep nested rule structures: `AND(OR(email_ends, name_starts), NOT(role_equals))`.
- **E2E-F1-B5: Malformed Operator Resolution**
  - Pass an invalid operator (e.g. `regex_match`) and verify the resolver handles it by returning `False` instead of crashing.

#### Feature 2: AST Formula Calculations Engine
- **E2E-F2-B1: Division by Zero Prevention**
  - Input `0` into the denominator of a division formula, verify value returns `0.0` without crashing.
- **E2E-F2-B2: Circular Dependency Loop Termination**
  - Establish a circular loop (`A = B` and `B = A`) and verify the engine breaks the loop after 5 iterations.
- **E2E-F2-B3: Malformed Formula Syntax Errors**
  - Pass malformed syntax (e.g. `5 + * 2`) and verify the UI handles the parser exception gracefully.
- **E2E-F2-B4: String Value Input Conversion**
  - Input a string value like `"12.5"` and verify it is automatically parsed to a double for calculations.
- **E2E-F2-B5: Overflow/Underflow Numeric Values**
  - Evaluate formulas resulting in extremely large numbers and verify double precision limits are managed.

#### Feature 3: Compliance Legal Holds & Quotas UI
- **E2E-F3-B1: File Storage Upload at 100% Quota**
  - Try uploading a file when the organization quota is exactly reached, and verify it is blocked.
- **E2E-F3-B2: Legal Hold on Non-Existent Target**
  - Attempt to create a legal hold referencing a garbage ObjectID, and verify the backend validates and rejects it.
- **E2E-F3-B3: Parallel Deletions of Held Resource**
  - Trigger simultaneous delete requests for a held form, and verify concurrency is safely handled.
- **E2E-F3-B4: Toggle Inactive Hold Retention**
  - Toggle a hold from active to inactive, verify that deletion permissions are restored immediately.
- **E2E-F3-B5: Directory Calculation Disk Error Recovery**
  - Simulate an OS permission error during directory traversal and verify `quota_service` falls back safely.

#### Feature 4: Drag-and-Drop Dashboard Canvas
- **E2E-F4-B1: Negative Coordinates Drop**
  - Drag widget to negative coordinates, verify it snaps to `(0, 0)` or is clamped inside canvas bounds.
- **E2E-F4-B2: Off-Canvas Drop Bounds Clipping**
  - Drag widget outside the maximum width/height of the canvas, verify it is clamped to border limits.
- **E2E-F4-B3: Canvas Size Reduction Compression**
  - Shrink the canvas size from `1920x1080` to `800x600`, verify widgets outside the new boundary snap to fit inside.
- **E2E-F4-B4: Missing Linked Analysis Run State**
  - Bind a widget to an analysis that has no runs, verify the widget renders a "No Data Available" warning.
- **E2E-F4-B5: Extremely Large Data Table Loading**
  - Bind a dashboard table widget to a run result containing 10,000 rows, and verify pagination/rendering doesn't freeze the UI.

---

### Tier 3: Cross-Feature Interactions
1. **F1 x F2 (Dynamic Groups & Formulas)**: Create a form where a formula field is inside a section visible only to a dynamic group. Verify calculations only execute for users belonging to that dynamic group.
2. **F1 x F3 (Dynamic Groups & Compliance)**: Restrict compliance actions (e.g. creating legal holds) to a dynamic group. Verify that non-group members are blocked from hold creation.
3. **F1 x F4 (Dynamic Groups & Dashboard Canvas)**: Limit dashboard editing to a dynamic group. Verify qualified users can drag and drop widgets, while others are restricted to read-only views.
4. **F2 x F3 (Formulas & Compliance/Quotas)**: A formula computes a numeric file size. Verify that when the calculation result exceeds the remaining quota, the form submission is rejected.
5. **F2 x F4 (Formulas & Dashboard Canvas)**: A dashboard widget displays aggregates of submission data calculated via the AST formula engine. Verify updates to submissions are propagated to the dashboard widget.
6. **F3 x F4 (Compliance & Dashboard Canvas)**: Place a project under legal hold. Verify that the dashboards belonging to that project are locked (canvas editing is disabled, dragging widgets is blocked).

---

### Tier 4: Real-World Application Scenarios (5 Complex Workflows)
1. **Workflow 1: Audited Project Legal Hold and Blocked Deletion**
   - Compliance officer logs in -> sees warning threshold at 85% on `CompliancePage` -> creates Legal Hold on "Project Alpha" -> editor logs in and tries to delete "Form A" in "Project Alpha" -> system blocks deletion -> editor tries to create a new form and is warned about quota limits.
2. **Workflow 2: Healthcare Formula Calculation and KPI Dashboard Propagation**
   - Inspector fills healthcare form -> inputs blood pressure -> AST formula engine calculates risk score -> inspector submits -> data is saved -> clinic manager opens dashboard -> KPI widget aggregates risk scores and renders.
3. **Workflow 3: Member Promotion and Canvas Layout Customization**
   - Admin changes user role -> session refresh detects new dynamic group membership ("Dashboard Editors") -> user navigates to dashboard -> edit mode becomes available -> user drags new bar chart to coordinate `(300, 100)` -> canvas is saved and reloaded.
4. **Workflow 4: Storage Quota Blockage, Cleanup, and Recovery**
   - Org storage reaches 100% -> user uploads file -> backend returns `403 QUOTA_EXCEEDED` -> admin deletes non-held files -> quota drops to 75% -> user resubmits file -> submission succeeds.
5. **Workflow 5: Public Sharing of Aggregated Compliance Statistics**
   - Admin creates dashboard displaying compliance holds -> toggles public sharing token -> external auditor loads public URL -> dashboard is rendered in read-only mode, without edit grids, showing real-time statistics.

---

## 5. Proposed Files and Structure

### Backend E2E Tests (`backend/tests/e2e/`)
Create these files under `backend/tests/e2e/`:

1. `backend/tests/e2e/conftest.py`:
   - Configures the Flask test client, seeds test databases, and provides common auth headers/tokens for dynamic groups.
2. `backend/tests/e2e/test_dynamic_groups_e2e.py`:
   - Tests API routes for group CRUD, evaluation of complex logical operations, and permission verification.
3. `backend/tests/e2e/test_compliance_quota_e2e.py`:
   - Tests compliance legal holds, storage quota enforcement, warning threshold updates, and deletion blockage.
4. `backend/tests/e2e/test_dashboard_canvas_e2e.py`:
   - Tests dashboard CRUD, canvas coordinate saving, data bindings resolution, and public token revocation.

### Frontend E2E Integration Tests (`frontend/integration_test/`)
Create these files under `frontend/integration_test/`:

1. `frontend/integration_test/dynamic_group_rules_e2e_test.dart`:
   - Tests the `DynamicGroupRuleBuilder` widget, verifying visual rules generate correct JSON and sync with the backend.
2. `frontend/integration_test/formula_calculations_e2e_test.dart`:
   - Tests math formula entry, cascading variable evaluation, division by zero, and submission of computed values.
3. `frontend/integration_test/compliance_quota_e2e_test.dart`:
   - Tests storage warning thresholds rendering, active legal holds listing, deletion blockers, and quota exceeded alert dialogs.
4. `frontend/integration_test/dashboard_canvas_drag_drop_e2e_test.dart`:
   - Tests drag-and-drop widget placement, positioning coordinates, overlapping zIndex order, and interactive pan/zoom.
5. `frontend/integration_test/app_workflows_e2e_test.dart`:
   - Contains the 5 complex real-world workflows tying multiple features together.

---

## 6. Verification Method

To verify the test suite execution, run the following commands:

### Running Backend E2E Tests:
Ensure you are in `backend/` and execute:
```bash
../.venv/bin/pytest tests/e2e/
```

### Running Frontend E2E Integration Tests:
Ensure you are in `frontend/` and execute:
```bash
flutter test integration_test/
```
*(Optionally use `flutter drive` if running against real mobile device simulators)*

### Invalidation Conditions:
- If a change is made to `resolve_group_members` in `auth_service.py` that changes the logical operator schema, the dynamic rules E2E tests will fail.
- If the division by zero behavior in `formula_parser.dart` is modified to return `null` instead of `0.0`, the calculations engine integration tests will fail.
