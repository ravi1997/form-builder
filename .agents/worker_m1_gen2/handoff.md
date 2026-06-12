# Handoff Report: Milestone 1: Dynamic Group Membership Rules

## 1. Observation
- **Backend implementation**: We inspected `backend/app/services/auth_service.py` (specifically lines 216-240 and 484-493) and observed that `_active_org_claims` resolves dynamic groups using `is_user_in_group` (the optimized single-user check) and embeds `group_ids` in the JWT access token.
- **Backend resource access check**: `get_user_groups_from_claims_or_db` is implemented and invoked in both `evaluate_visibility_rules` (line 515) and `user_has_access_to_resource` (line 539).
- **Backend test coverage**: In `backend/tests/test_auth.py` (lines 257-277), we observed that the existing `test_access_token_contains_group_ids` test successfully verified token claims only for `/api/auth/login`. We extended it to verify refreshed tokens via `/api/auth/refresh`.
- **Backend test results**: Running `/home/ravi/workspace/form-builder/.venv/bin/pytest backend/tests/test_auth.py` succeeded with:
  ```
  backend/tests/test_auth.py ..........                                    [100%]
  ======================= 10 passed, 157 warnings in 3.73s =======================
  ```
- **Frontend focus and default role issues**: In `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`, we observed that:
  - Re-rendering on every keystroke reset text field selection and focus.
  - The default rule value was `'org_member'`, which is not a valid organization role on the backend.
  - `didUpdateWidget` was missing, meaning rules initialized by the parent from the outside were not correctly updated/reloaded.
- **Frontend test results**: Running `flutter test test/e2e/e2e_dynamic_groups_test.dart` initially failed with:
  ```
  Expected: 'org_member'
  Actual: 'org_viewer'
  ```
- **Resolved Frontend tests**: After refactoring the widget and updating the tests to check `controller.text` and expect `'org_viewer'`, running `flutter test test/e2e/e2e_dynamic_groups_test.dart` succeeded with:
  ```
  All tests passed!
  ```

## 2. Logic Chain
- **Backend Single-User Check**: The backend architecture requires that `_active_org_claims` resolve user groups in a performant manner. Using `is_user_in_group` avoids loading and matching all members of an organization, which is O(N) where N is number of users. Instead, it checks only the specific candidate's static membership or dynamic rule, resolving in O(1) per group.
- **Access Token Claims**: By verifying that both `/api/auth/login` and `/api/auth/refresh` return `group_ids` inside the decoded token's org list, we ensure that authorization checks across subsequent requests can be validated without database lookup.
- **Frontend Focus Loss & Cursor Jump**: By extracting condition rows into a stateful `_ConditionRow` child widget and managing a local `TextEditingController`, the controller instance is maintained across rebuilds. Furthermore, using a stable `ValueKey` inside `ListView.builder` based on `_conditionKeys` guarantees that the widget is preserved and mapped to the same element in the tree, resolving the focus loss and cursor resetting issues completely.
- **Invalid Default Value**: Changing the default role value from `'org_member'` to `'org_viewer'` ensures that new rules map to a valid default role on the backend.
- **didUpdateWidget Implementation**: Deeply comparing `initialRule` in `didUpdateWidget` and calling `_loadRule` when it differs ensures that external modifications to the rule propagate correctly to the widget state, while avoiding unnecessary re-initialization (and cursor resets) on standard local state updates.

## 3. Caveats
No caveats.

## 4. Conclusion
Milestone 1 has been fully implemented and verified on both backend and frontend. The backend correctly optimized and populated `group_ids` claims on both login and refresh endpoints. The frontend dynamic group rule builder widget now retains keyboard focus and cursor position during typing, initializes with the correct `'org_viewer'` default role, and reacts correctly to parent state modifications via `didUpdateWidget`.

## 5. Verification Method
To independently verify the changes, execute the following commands in the terminal:

1. **Backend verification**:
   Run the pytest auth tests:
   ```bash
   /home/ravi/workspace/form-builder/.venv/bin/pytest backend/tests/test_auth.py
   ```
   *Expected outcome*: All 10 tests pass (including `test_access_token_contains_group_ids` which checks login and refresh token contents).

2. **Frontend verification**:
   Run the flutter widget/E2E tests:
   ```bash
   flutter test test/e2e/e2e_dynamic_groups_test.dart
   ```
   *Expected outcome*: All 6 tests pass (including `T3: Focus retention during typing and didUpdateWidget reload behavior`).
