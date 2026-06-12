## 2026-06-12T08:41:25Z
You are a Worker subagent assigned to implement Milestone 1: Dynamic Group Membership Rules.

Your working directory is: `/home/ravi/workspace/form-builder/.agents/worker_m1_gen2`

Please read `/home/ravi/workspace/form-builder/.agents/sub_orch_m1_gen2/SCOPE.md` and the original explorer analyses (e.g. `/home/ravi/workspace/form-builder/.agents/explorer_m1_1/analysis.md`) for detailed specifications.

Your tasks are:
1. Backend verification and implementation:
   - Check `backend/app/services/auth_service.py`. Ensure that `_active_org_claims` correctly resolves user's groups (`group_ids` claims) using an optimized single-user check `is_user_in_group` rather than `get_user_groups`.
   - Ensure `get_user_groups_from_claims_or_db` is implemented and used in `evaluate_visibility_rules` and `user_has_access_to_resource`.
   - Add a unit/integration test `test_access_token_contains_group_ids` to `backend/tests/test_auth.py` that verifies that the JWT claims returned from `/api/auth/login` and `/api/auth/refresh` include the dynamic/static `group_ids`.
   - Run the backend tests using `/home/ravi/workspace/form-builder/.venv/bin/pytest backend/tests/test_auth.py`.

2. Frontend implementation:
   - Modify `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`.
   - Fix the focus loss and cursor resetting bug: extract the condition row into a stateful child widget (e.g. `_ConditionRow`) that manages its own `TextEditingController`, and use stable keys (e.g. `ObjectKey` or `ValueKey`) inside `ListView.builder`.
   - Change the default rule value from `'org_member'` to `'org_viewer'`.
   - Implement `didUpdateWidget` in the state to deeply compare and reload the rule if `initialRule` changes.
   - Run `flutter test` or add specific widget tests in `frontend/test/e2e/e2e_dynamic_groups_test.dart` to verify correctness of rule builders and focus/cursor persistence.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Please report your results and write a handoff report to `/home/ravi/workspace/form-builder/.agents/worker_m1_gen2/handoff.md`. Communicate back when done.
