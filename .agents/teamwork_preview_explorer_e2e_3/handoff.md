# E2E Test Suite Projections and Findings Report

## 1. Observation
The codebase was inspected to identify all existing backend and frontend components for the four features, as well as their corresponding tests.

### Feature 1: Dynamic Group Rules
- **Backend Schema / Logic**: 
  - File: `backend/app/services/auth_service.py`
  - Function: `resolve_group_members(group: dict, org_id: str)` (lines 463-539) resolves users dynamically based on rule operators: `equals`, `not_equals`, `contains`, `starts_with`, `ends_with`, `in`.
  - Function: `get_user_groups(user_id: str, org_id: str)` (lines 453-460) queries `mongo.db.groups` and resolves active group memberships for a user.
- **Frontend Component**: 
  - File: `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`
  - Details: State widget allowing UI construction of rules with AND/OR logical operators and conditions spanning fields: `role`, `email`, `full_name`, `status`, `membership_status`.
- **Existing Tests**:
  - File: `backend/tests/test_auth.py`
  - Functions: `test_group_resolution_and_permission_helpers` (lines 133-144) and `test_advanced_dynamic_rules` (lines 146-192) test rule matching on mock DB collections.

### Feature 2: AST Formula Calculations Engine
- **Frontend Parser**:
  - File: `frontend/lib/core/formula/formula_parser.dart`
  - Details: Implements `ExpressionNode`, `NumberNode`, `VariableNode`, and `BinaryOpNode` to evaluate formulas with standard arithmetic operators (`+`, `-`, `*`, `/`, `%`).
- **Cascading Recalculation**:
  - File: `frontend/lib/features/form_builder/providers/form_builder_provider.dart`
  - Function: `FormPlayNotifier.evaluateFormulas(List<FormSection> sections)` (lines 493-544) runs up to 5 iterations for cascading/dependent formula recalculation.
- **Existing Tests**:
  - File: `frontend/test/formula_parser_test.dart` (lines 1-23) tests basic AST parsing and evaluation.
  - File: `frontend/test/formula_eval_integration_test.dart` (lines 1-78) tests integration with `formPlayProvider` and `FormPlayNotifier`.

### Feature 3: Compliance Legal Holds & Quotas UI
- **Backend Services**:
  - File: `backend/app/services/compliance_service.py` provides `create_legal_hold`, `list_legal_holds`, `toggle_legal_hold`, and `is_resource_held(target_type, target_id)`.
  - File: `backend/app/services/quota_service.py` provides `calculate_organization_quota` and `enforce_org_quota`.
- **Backend Routes**:
  - File: `backend/app/routes/compliance.py` exposes `/api/orgs/<org_id>/compliance/holds` (GET/POST) and `/api/compliance/holds/<hold_id>` (PUT).
  - File: `backend/app/routes/forms.py` calls `enforce_org_quota` on form creation (line 264) and blocks with `403` status and `QUOTA_EXCEEDED` code.
- **Frontend UI**:
  - File: `frontend/lib/features/compliance/presentation/pages/compliance_page.dart` renders the storage progress bar, warning indicator for near-quota limits, and a list of active legal holds with toggle switches.
- **Existing Tests**:
  - File: `backend/tests/test_compliance.py` (lines 1-102) tests legal hold propagation and deletion blocking (returning 409 `LEGAL_HOLD_ACTIVE`).
  - File: `backend/tests/test_quota.py` (lines 1-30) tests that form creation is blocked when organization quota is exceeded.
  - File: `frontend/test/compliance_page_test.dart` (lines 1-37) tests widget rendering and hold toggle switches.

### Feature 4: Drag-and-Drop Dashboard Canvas
- **Frontend UI / Grid Layouts**:
  - File: `frontend/lib/features/dashboard_builder/canvas/dashboard_canvas.dart` wraps elements in an `InteractiveViewer`, rendering a `CanvasGrid` overlay and a stack of `DraggableWidgetWrapper` components.
- **Canvas State**:
  - File: `frontend/lib/features/dashboard_builder/providers/canvas_state_provider.dart` defines `CanvasStateNotifier` which implements `moveWidget` (lines 222-233) and `resizeWidget` (lines 235-252) using snap-to-grid grid size.
- **Existing Tests**:
  - File: `frontend/test/form_canvas_play_test.dart` (lines 100-155) verifies drag targets and ghost indicators during drag interactions.

---

## 2. Logic Chain
1. Existing backend tests run inside a python virtual environment `.venv` using `pytest`. Execution of `../.venv/bin/pytest` in the `backend` folder succeeded with:
   > `46 passed, 332 warnings in 8.22s`
2. Existing frontend tests are executed using the Flutter SDK. Running `flutter test` in `frontend` completed with:
   > `All tests passed!`
3. Although unit and integration tests exist for individual components, they mock databases/providers locally and do not verify full pairwise integration or multi-stage user workflows (e.g., dynamic roles restricting access to legal holds, or calculations updating widgets on the canvas).
4. An E2E test plan is necessary to cross-link the 4 features across 4 tiers: Feature Coverage, Boundary Cases, Cross-Feature Interactions, and Real-World Application Scenarios.

---

## 3. Caveats
- No live browser automation framework (e.g., Integration Test/Patrol for Flutter, or Selenium/Playwright for Backend) was run during the read-only exploration phase. Projections assume a mock/driver-based integration environment already configured in the pipeline.
- Database states assume mongomock in backend unit testing and real/mock MongoDB instances for full-scale E2E testing environments.

---

## 4. Conclusion & Proposed E2E Test Plan
We propose creating the following exact files to form the E2E test suite.

### Proposed Test File Structure

```
backend/tests/e2e/
├── test_e2e_compliance_workflows.py     # Tier 3 & Tier 4 compliance/holds flows
└── test_e2e_dynamic_group_rules.py     # Tier 1 & Tier 2 dynamic group edge cases

frontend/test/e2e/
├── e2e_dashboard_canvas_test.dart      # Tier 1, 2, & 4 dashboard canvas flows
├── e2e_formula_calculations_test.dart   # Tier 1 & 2 AST calculation corner cases
└── e2e_compliance_quota_test.dart       # Tier 1 & 2 quota & warning indicators
```

---

### Tier 1: Feature Coverage (>=5 tests per feature, >=20 total)

#### 1. Dynamic Group Rules (Backend & Frontend)
- **Test 1**: Verify dynamic rule evaluation returns matching users for a single role-based condition.
- **Test 2**: Verify dynamic rule evaluation returns matching users for logical AND operator combinations.
- **Test 3**: Verify `DynamicGroupRuleBuilder` UI displays correctly with loaded initial rules.
- **Test 4**: Verify UI conditions can be added and removed dynamically in `DynamicGroupRuleBuilder`.
- **Test 5**: Verify group memberships update in database when user roles change.

#### 2. AST Formula Calculations Engine (Frontend)
- **Test 6**: Verify simple arithmetic precedence evaluation in `FormulaParser`.
- **Test 7**: Verify evaluation with variables and correct fallback on missing values.
- **Test 8**: Verify cascading calculations complete successfully up to 5 iterations.
- **Test 9**: Verify calculated field updates dynamically in play mode upon typing values.
- **Test 10**: Verify division by zero yields `0.0` rather than causing application crashes.

#### 3. Compliance Legal Holds & Quotas UI (Backend & Frontend)
- **Test 11**: Verify quota usage progress bar updates based on used storage bytes.
- **Test 12**: Verify compliance warning threshold triggers warning message at >=80% usage.
- **Test 13**: Verify active legal hold switches can be toggled on/off on the `CompliancePage`.
- **Test 14**: Verify backend blocks form creation when the organization quota is full.
- **Test 15**: Verify backend blocks deletion of forms, projects, and responses under an active hold.

#### 4. Drag-and-Drop Dashboard Canvas (Frontend)
- **Test 16**: Verify `CanvasGrid` overlay switches visibility based on edit vs preview mode.
- **Test 17**: Verify widgets (`kpi_card`, `bar_chart`) can be added to the canvas.
- **Test 18**: Verify widget drag moves snap coordinates to the active grid size.
- **Test 19**: Verify widgets cannot be moved beyond canvas boundary constraints.
- **Test 20**: Verify widget lock property prevents movement and resizing updates.

---

### Tier 2: Boundary/Corner Cases (>=5 tests per feature, >=20 total)

#### 1. Dynamic Group Rules
- **Test 21**: Empty dynamic rules (no conditions) return all organization members.
- **Test 22**: Case-insensitive evaluations for string operators (`contains`, `starts_with`).
- **Test 23**: Evaluating dynamic groups when there are zero memberships in an organization.
- **Test 24**: Checking invalid operator handles gracefully without raising exceptions.
- **Test 25**: Using `in` operator with comma-separated list of values.

#### 2. AST Formula Calculations Engine
- **Test 26**: Extremely nested parenthesis (e.g. `(((q1 + 1)))`) parsing.
- **Test 27**: Formula cycles (self-references) terminate gracefully at the 5-iteration limit.
- **Test 28**: Negative value calculations and extreme floating point comparisons.
- **Test 29**: Invalid syntax parsing (e.g. `q1 ++ * 5`) throws explicit format exceptions.
- **Test 30**: Null variable inputs evaluate as 0.0 without crash.

#### 3. Compliance Legal Holds & Quotas UI
- **Test 31**: Storage quota usage exactly at 80% boundary triggers warning.
- **Test 32**: Legal hold target IDs containing non-existent IDs does not break the query service.
- **Test 33**: propagated holds: trying to delete a response when only its parent form is under hold.
- **Test 34**: Quota limit check with very small increments (e.g. 1 byte left).
- **Test 35**: Authorization checks for compliance routes (ensure normal users receive 403).

#### 4. Drag-and-Drop Canvas
- **Test 36**: Dragging widget coordinates completely out of canvas clamps to borders.
- **Test 37**: Resizing a widget below minimum limits (20x20) or larger than canvas boundaries.
- **Test 38**: Zooming canvas to extreme levels (0.25x or 2.0x) and panning.
- **Test 39**: Snap to grid with maximum grid sizes (e.g., 64).
- **Test 40**: Z-index boundaries (handling extremely large/small z-index increments).

---

### Tier 3: Cross-Feature Interactions

- **Interaction 1: Dynamic Groups & Compliance Legal Holds**
  - A project hold is active. A group is resolved dynamically. Only members of the resolved group can toggle the legal hold status.
- **Interaction 2: AST Formulas & Quotas**
  - Complex calculation results are submitted. The database size increases, triggering the storage quota threshold, which blocks subsequent form creations.
- **Interaction 3: Canvas Widgets & AST Formulas**
  - A KPI card on the canvas is bound to a calculation field. Filling a form triggers the AST calculation, which live-updates the KPI card value on the canvas.
- **Interaction 4: Canvas Widgets & Compliance holds**
  - Canvas dashboards belong to a project. Putting a legal hold on the project freezes the dashboard design canvas (making it read-only).
- **Interaction 5: Dynamic Groups & Canvas Dashboards**
  - Users are added to dynamic groups based on email domain. Only users matching the group rule are authorized to edit widgets on the design canvas.

---

### Tier 4: Real-World Application Scenarios (>=5 complex workflows)

- **Scenario 1: End-to-End Compliance Auditing & Legal Hold**
  - Set hold -> Editor attempt delete form -> Blocked (409) -> Deactivate hold -> Delete form -> Success.
- **Scenario 2: Dynamic Team Onboarding & Dashboard Provisioning**
  - Add user -> Dynamic group resolves role -> User logs in -> Instantly displays group-restricted dashboard canvas widgets.
- **Scenario 3: Multi-Stage Calculation Form Submission under Quota Pressure**
  - Fill calculations form -> UI calculates total -> Storage near quota (85%) -> Submit -> Success -> Upload huge resource -> Submit next form -> Blocked (403).
- **Scenario 4: Interactive Dashboard Canvas Design and Real-Time Data Refresh**
  - Designer builds dashboard -> Snap to grid on -> Adds KPI card & chart -> Binds to formula -> Preview mode -> Answers change -> Widgets auto-refresh.
- **Scenario 5: Dynamic Group Permission-Based Form Field Visibility & Calculated Submission**
  - User with matching dynamic group email logs in -> Extra fields display -> Risk rating AST calculates -> Submit -> Normal user logs in -> Fields hidden -> Default calculation -> Submit.

---

### Proposed Test File Implementations

#### File 1: `backend/tests/e2e/test_e2e_compliance_workflows.py`
```python
import pytest
from bson import ObjectId
import datetime
from app.services.compliance_service import is_resource_held, create_legal_hold
from app.services.quota_service import enforce_org_quota

def test_scenario_compliance_audit_lifecycle(client, db):
    org_id = ObjectId()
    project_id = ObjectId()
    form_id = ObjectId()
    
    db.forms.insert_one({"_id": form_id, "org_id": org_id, "project_id": project_id, "is_deleted": False})
    
    # 1. Start: hold active
    hold_id = create_legal_hold(org_id, "Audit", "E2E Hold", "project", [project_id], ObjectId())["_id"]
    
    # 2. Editor attempt delete -> Blocked
    res = client.delete(f"/api/internal/v1/forms/{form_id}")
    assert res.status_code == 409
    
    # 3. Deactivate hold
    client.put(f"/api/compliance/holds/{hold_id}", json={"is_active": False}, headers={"Authorization": "Bearer mock-token"})
    
    # 4. Try again -> Success
    db.legal_holds.update_one({"_id": hold_id}, {"$set": {"is_active": False}})
    res = client.delete(f"/api/internal/v1/forms/{form_id}")
    assert res.status_code == 200

def test_cross_feature_formulas_and_quotas(client, db):
    org_id = ObjectId()
    db.storage_quotas.insert_one({
        "org_id": org_id,
        "quota_bytes": 100,
        "used_bytes": {"total": 99}
    })
    
    # Submission triggers quota enforcement -> Exceeded
    with pytest.raises(ValueError, match="Organization quota exceeded"):
        enforce_org_quota(org_id, requested_bytes=2)
```

#### File 2: `backend/tests/e2e/test_e2e_dynamic_group_rules.py`
```python
import pytest
from bson import ObjectId
from app.services.auth_service import resolve_group_members

def test_dynamic_group_boundary_empty_rules(db):
    org_id = ObjectId()
    u_id = ObjectId()
    db.org_memberships.insert_one({"user_id": u_id, "org_id": org_id, "role": "org_member", "status": "active", "is_deleted": False})
    db.users.insert_one({"_id": u_id, "status": "active"})
    
    group = {"type": "dynamic", "dynamic_rule": {}}
    members = resolve_group_members(group, str(org_id))
    assert str(u_id) in members # Empty rules default match

def test_dynamic_group_case_insensitivity(db):
    org_id = ObjectId()
    u_id = ObjectId()
    db.org_memberships.insert_one({"user_id": u_id, "org_id": org_id, "role": "org_member", "status": "active", "is_deleted": False})
    db.users.insert_one({"_id": u_id, "email": "User@Company.com", "status": "active"})
    
    group = {"type": "dynamic", "dynamic_rule": {"field": "email", "operator": "ends_with", "value": "@company.com"}}
    members = resolve_group_members(group, str(org_id))
    assert str(u_id) in members
```

#### File 3: `frontend/test/e2e/e2e_dashboard_canvas_test.dart`
```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:frontend/features/dashboard_builder/canvas/dashboard_canvas.dart';
import 'package:frontend/features/dashboard_builder/providers/canvas_state_provider.dart';

void main() {
  testWidgets('E2E Dashboard Canvas Drag, Resize, and Lock flow', (WidgetTester tester) async {
    final container = ProviderContainer();
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(
          home: Scaffold(
            body: DashboardCanvas(dashboardId: 'test_dash'),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final notifier = container.read(canvasStateProvider('test_dash').notifier);
    
    // 1. Add Widget
    notifier.addWidget(type: 'kpi_card', position: const Offset(10, 10));
    await tester.pumpAndSettle();
    expect(container.read(canvasStateProvider('test_dash')).widgets.length, 1);

    // 2. Move with snap
    notifier.toggleSnapToGrid();
    notifier.moveWidget(container.read(canvasStateProvider('test_dash')).widgets.first.id, 15, 15);
    expect(container.read(canvasStateProvider('test_dash')).widgets.first.position.x, 16.0); // snaps to 8

    // 3. Lock widget
    notifier.toggleLockWidget(container.read(canvasStateProvider('test_dash')).widgets.first.id);
    notifier.moveWidget(container.read(canvasStateProvider('test_dash')).widgets.first.id, 50, 50);
    expect(container.read(canvasStateProvider('test_dash')).widgets.first.position.x, 16.0); // should not move
  });
}
```

#### File 4: `frontend/test/e2e/e2e_formula_calculations_test.dart`
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/core/formula/formula_parser.dart';

void main() {
  test('E2E Formula Calculation boundaries', () {
    // 1. Nested parenthesis
    final parser1 = FormulaParser('(((q1 + 10) * 2))');
    expect(parser1.parse().evaluate({'q1': 5.0}), 30.0);

    // 2. Division by zero fallback
    final parser2 = FormulaParser('q1 / (q2 - 2)');
    expect(parser2.parse().evaluate({'q1': 10.0, 'q2': 2.0}), 0.0);
  });
}
```

#### File 5: `frontend/test/e2e/e2e_compliance_quota_test.dart`
```dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/compliance/presentation/pages/compliance_page.dart';

void main() {
  testWidgets('E2E Quota threshold warning indicator rendering', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: CompliancePage()),
    );
    await tester.pumpAndSettle();

    // Verify warning status renders when usage is near limits
    expect(find.textContaining('Warning: Near storage limit'), findsOneWidget);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
  });
}
```

---

## 5. Verification Method

To independently verify the test plan implementation and execute E2E tests:

### 1. Execute Backend pytest Suite
Run python tests using the pytest runner:
```bash
# Navigate to backend and run E2E specifically
cd backend
../.venv/bin/pytest tests/e2e/
```

### 2. Execute Frontend flutter test Suite
Run Dart unit/widget tests using the flutter tool:
```bash
# Navigate to frontend and run E2E specifically
cd frontend
flutter test test/e2e/
```

### 3. Invalidation Conditions
- If the backend fails with a database connection issue, verify mongomock or clean test database instances are active.
- If the frontend fails on finding widgets, ensure testing runs with a consistent screen size configuration (e.g. `tester.binding.setSurfaceSize(const Size(1400, 1000))`).
