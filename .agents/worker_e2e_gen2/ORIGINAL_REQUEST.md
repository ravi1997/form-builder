## 2026-06-12T08:44:45Z
Objective: Create the missing E2E integration workflow test files on both the backend and frontend, and verify that the entire E2E test suite compiles and runs cleanly.

Scope boundaries:
- Do not modify existing production source files, except if test setup requires it.
- Implement only the missing test files: `backend/tests/e2e/test_e2e_workflows.py` and `frontend/test/e2e/e2e_workflows_test.dart`.

Input information:
- Predecessor E2E plan: /home/ravi/workspace/form-builder/.agents/sub_orch_e2e/E2E_PLAN.md
- Requirements document: /home/ravi/workspace/form-builder/.agents/sub_orch_e2e_gen2/ORIGINAL_REQUEST.md
- Test infra plan: /home/ravi/workspace/form-builder/TEST_INFRA.md
- Pre-existing backend test examples: /home/ravi/workspace/form-builder/backend/tests/e2e/test_e2e_dynamic_groups.py, /home/ravi/workspace/form-builder/backend/tests/e2e/test_e2e_compliance_quota.py, /home/ravi/workspace/form-builder/backend/tests/e2e/conftest.py
- Pre-existing frontend test examples: /home/ravi/workspace/form-builder/frontend/test/e2e/e2e_dynamic_groups_test.dart, /home/ravi/workspace/form-builder/frontend/test/e2e/e2e_formula_calculations_test.dart, /home/ravi/workspace/form-builder/frontend/test/e2e/e2e_compliance_quota_test.dart, /home/ravi/workspace/form-builder/frontend/test/e2e/e2e_dashboard_canvas_test.dart
- Your working directory: /home/ravi/workspace/form-builder/.agents/worker_e2e_gen2

Tasks:
1. Create `backend/tests/e2e/test_e2e_workflows.py` and implement E2E tests for at least the following Tier 4 workflows:
   - Workflow 1: Audited Project Legal Hold and Blocked Deletion (verify that legal hold on project blocks child form/response deletion, and releasing it allows deletion).
   - Workflow 3: Member Promotion and Canvas Layout Customization (verify that promoting user to org_admin dynamically matches dynamic group rules and allows dashboard canvas coordinates saving).
   - Workflow 4: Storage Quota Blockage, Cleanup, and Recovery (verify that exceeding storage quota blocks form creation with 403, and cleaning up/recovery allows it again).
   - Workflow 5: Public Sharing of Aggregated Compliance Statistics (verify that enabling sharing on a dashboard allows reading widget data via public token route without authorization).

2. Create `frontend/test/e2e/e2e_workflows_test.dart` and implement E2E integration widget/state tests for Tier 4 workflows:
   - Workflow 2: Healthcare Formula Calculation and KPI Dashboard Propagation (verify that entering answers in FormPlay triggers AST formulas, which propagates values and updates dashboard widget bindings).
   - Workflow 3: Member Promotion and Canvas Layout Customization (verify that changing user role matches rules and updates dashboard canvas layout/permissions).
   - Workflow 4: Storage Quota Blockage, Cleanup, and Recovery (verify that full quota displays error banner and blocks submissions, and cleanup resolves it).
   - Workflow 5: Public Sharing of Aggregated Compliance Statistics (verify read-only layout widget presentation via public token).

3. Verify the E2E test suite by executing tests:
   - Run backend tests: cd /home/ravi/workspace/form-builder/backend && ../.venv/bin/pytest tests/e2e/
   - Run frontend tests: cd /home/ravi/workspace/form-builder/frontend && flutter test test/e2e/
   Ensure all tests pass.

4. Write a detailed handoff report `handoff.md` in your working directory (/home/ravi/workspace/form-builder/.agents/worker_e2e_gen2) documenting the test implementations, run commands, output logs, and any verification results.
