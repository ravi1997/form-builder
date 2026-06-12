# E2E Test Suite Plan

## Test Philosophy
- **Opaque-box & Requirement-driven**: The E2E tests target the APIs and UI widgets as an end-user would, without accessing private/internal details directly where possible.
- **Systematic Coverage**: We partition tests across 4 Tiers:
  - **Tier 1 (Feature Coverage)**: Core happy paths (5 tests per feature).
  - **Tier 2 (Boundary & Corner Cases)**: Edge cases and constraints (5 tests per feature).
  - **Tier 3 (Cross-Feature Interactions)**: Pairwise interactions between features.
  - **Tier 4 (Real-World Application Scenarios)**: Multi-stage workflows mimicking actual usage.

---

## Test Directory Structure

```
backend/tests/e2e/
├── conftest.py
├── test_e2e_dynamic_groups.py       # Tiers 1-3 group tests
├── test_e2e_compliance_quota.py      # Tiers 1-3 compliance and quota tests
└── test_e2e_workflows.py             # Tier 4 real-world workflows

frontend/test/e2e/
├── e2e_dynamic_groups_test.dart       # Tiers 1-3 group UI tests
├── e2e_formula_calculations_test.dart # Tiers 1-3 AST engine and dependency tests
├── e2e_compliance_quota_test.dart     # Tiers 1-3 compliance holds and quota indicator UI tests
├── e2e_dashboard_canvas_test.dart     # Tiers 1-3 dashboard builder and grid tests
└── e2e_workflows_test.dart            # Tier 4 real-world integration workflows
```

---

## Feature Inventory & Test Coverage

### F1: Dynamic Group Membership Rules
- **Tier 1**:
  - Test 1: Single rule condition evaluation matches correct organization member.
  - Test 2: Logical AND rule combinations filter members correctly.
  - Test 3: Logical OR rule combinations filter members correctly.
  - Test 4: Logical NOT rule inversion filters out members correctly.
  - Test 5: Dynamic group membership updates dynamically when candidate data changes.
- **Tier 2**:
  - Test 6: Empty dynamic rule `{}` defaults to match all organization active members (or returns empty depending on spec; here, standard is empty rules match active members of the organization).
  - Test 7: Case-insensitive evaluation of string filters (`ends_with`, `starts_with`, `contains`).
  - Test 8: Graceful handling of missing candidate fields (safely skips rather than crashes).
  - Test 9: Comma-separated strings inside `in` operator (e.g. `role in admin,member`).
  - Test 10: Graceful recovery and fallback when malformed operator is passed.

### F2: AST Formula Calculations Engine
- **Tier 1**:
  - Test 11: Simple mathematical operators (`+`, `-`, `*`, `/`, `%`) and parentheses precedence.
  - Test 12: Cascading recalculation (fields depend on other calculated fields, evaluated up to 5 times).
  - Test 13: Variable replacement evaluates correctly using inputs.
  - Test 14: Submitting formula-populated forms saves calculated values to database.
  - Test 15: Modulo calculations evaluate remainder.
- **Tier 2**:
  - Test 16: Division by zero returns `0.0` fallback.
  - Test 17: Deeply nested parentheses evaluation (e.g., `((((q1 + 10))))`).
  - Test 18: Circular reference detection (stops at 5 iterations to prevent infinite loop).
  - Test 19: Coercion of string inputs (e.g. `"20"`) to doubles before math evaluations.
  - Test 20: Missing/null variables default to `0.0` to prevent crashing.

### F3: Compliance Legal Holds & Quotas
- **Tier 1**:
  - Test 21: Storage quota calculation updates usage progressive bars.
  - Test 22: Warning banner is visible when quota exceeds 80%.
  - Test 23: Block new form submissions and creation when quota is 100% full.
  - Test 24: Creation of compliance holds and toggling switches in admin panel.
  - Test 25: Block deletion of held resources (form, project, response).
- **Tier 2**:
  - Test 26: Quota check near the absolute boundary (1 byte left).
  - Test 27: Propagation check: blocking deletion of response when parent form is held.
  - Test 28: Toggle hold off immediately restores delete permission.
  - Test 29: Hold targets containing non-existent IDs.
  - Test 30: Restricting compliance endpoint access to `org_admin` (normal users blocked with 403).

### F4: Drag-and-Drop Dashboard Canvas
- **Tier 1**:
  - Test 31: Add KPI card / Bar chart widget to canvas.
  - Test 32: Drag widget to snap-to-grid coordinate.
  - Test 33: Canvas lock property prevents moving/resizing.
  - Test 34: Coordinates save to backend and restore on reload.
  - Test 35: Overlapping z-order positioning.
- **Tier 2**:
  - Test 36: Coordinates clamped within canvas boundaries (cannot drag off-screen).
  - Test 37: Snapping to custom grid sizes (e.g. 8px, 16px).
  - Test 38: Clamping widget dimensions on resize (minimum sizes).
  - Test 39: Render mock indicator when linked analysis has no runs.
  - Test 40: Public token layout preview matches read-only config.

---

## Tier 3: Cross-Feature Interactions
1. **F1 x F2**: Dynamic Group filters visibility of a Section containing calculations; verify math only runs when the qualified user fills it.
2. **F1 x F3**: Restrict compliance legal hold actions to dynamic group members.
3. **F1 x F4**: Dynamic group permission restricts dashboard canvas layout editor to authorized roles.
4. **F2 x F3**: Calculations compute file upload sizes, and if the total exceeds quota limits, the submission is rejected.
5. **F2 x F4**: Dashboard KPI widget binds to aggregate values computed via the AST formula engine.
6. **F3 x F4**: Legal hold placed on a project locks dashboard canvas edits of dashboards inside that project.

---

## Tier 4: Real-World Scenarios
1. **Workflow 1: Audited Project Legal Hold and Blocked Deletion**
   - Place project on legal hold -> attempt deleting child form -> blocked -> toggle hold off -> delete -> success.
2. **Workflow 2: Healthcare Formula Calculation and KPI Dashboard Propagation**
   - Submit form response with inputs -> AST calculation resolves risk rate -> dashboard KPI widget aggregates risk rate and displays.
3. **Workflow 3: Member Promotion and Canvas Layout Customization**
   - Update user role -> dynamic group rule matches -> user logs in and accesses canvas -> drag-drop layout edit -> save coordinates -> reload.
4. **Workflow 4: Storage Quota Blockage, Cleanup, and Recovery**
   - Seed quota full -> submit form fails -> admin deletes files -> quota falls below limit -> submit form succeeds.
5. **Workflow 5: Public Sharing of Aggregated Compliance Statistics**
   - Public token dashboard loaded -> displays read-only widgets without edit grids showing hold numbers.
