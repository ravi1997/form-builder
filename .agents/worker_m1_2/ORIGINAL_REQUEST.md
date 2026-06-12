## 2026-06-12T08:40:06Z
You are Milestone 1 Worker 1 (Replacement). Your working directory is /home/ravi/workspace/form-builder/.agents/worker_m1_2.
Your task is to implement the changes detailed in /home/ravi/workspace/form-builder/.agents/sub_orch_m1/SCOPE.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Specifically, you need to:
1. Backend changes in backend/app/services/auth_service.py:
   - Extract evaluation helpers evaluate_condition and evaluate_rule from resolve_group_members into module-level functions.
   - Implement is_user_in_group(user_doc, membership, group).
   - In _active_org_claims(user_id), query groups and add group_ids inside organisation claims.
   - Implement get_user_groups_from_claims_or_db(decoded_token, org_id, user_id) helper and use it inside evaluate_visibility_rules and user_has_access_to_resource (and check_permission if appropriate).
2. Backend tests:
   - Add test case test_access_token_contains_group_ids in backend/tests/test_auth.py to verify login/refresh tokens and claims logic.
   - Run the backend test suite via .venv/bin/pytest backend/tests/ to verify the changes.
3. Frontend changes in frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart:
   - Change the default rule value from 'org_member' to 'org_viewer'.
   - Extract condition rows into a stateful child widget (e.g. DynamicGroupRuleRow) that manages its own TextEditingController and uses stable ValueKeys to preserve text focus, selection cursor position, and state during editing.
   - Implement didUpdateWidget in DynamicGroupRuleBuilder to update local rule state from parent's initialRule.
4. Frontend tests:
   - Create a widget test frontend/test/dynamic_group_rule_builder_test.dart to verify input editing, focus retention, and correct dynamic rule state generation.
   - Run the frontend tests via flutter test inside frontend/.

When done, write a detailed handoff report to /home/ravi/workspace/form-builder/.agents/worker_m1_2/handoff.md detailing the files changed, test commands run, and test results. Then, send a message to parent f1a37dc4-593b-446e-89f8-57a99e76a54f.
