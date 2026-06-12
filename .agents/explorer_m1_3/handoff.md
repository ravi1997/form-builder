# Handoff Report - Explorer 3

## 1. Observation
- **Observation 1 (Backend Claims)**: In `backend/app/services/auth_service.py:145-158`, the `_active_org_claims` function returns a dictionary for each organization membership without a `group_ids` list:
  ```python
  def _active_org_claims(user_id):
      memberships = mongo.db.org_memberships.find(
          {"user_id": _oid(user_id), "is_deleted": False, "status": "active"}
      )
      claims = []
      for membership in memberships:
          claims.append(
              {
                  "org_id": str(membership.get("org_id")),
                  "role": membership.get("role", "org_viewer"),
                  "status": membership.get("status", "active"),
              }
          )
      return claims
  ```
- **Observation 2 (Unoptimized Permission Checks)**: In `backend/app/services/auth_service.py:422-424` and `446-449`, group permissions are checked by querying the database using `get_user_groups` directly, even when a decoded token is already present:
  ```python
          elif ctype == "group":
              user_groups = get_user_groups(decoded_token.get("sub"), str(resource_org_id))
  ```
- **Observation 3 (Frontend Widget Focus Bug)**: In `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart:234-245`, the `TextFormField` is defined without a `TextEditingController`, and updates using `onChanged` and `initialValue`:
  ```dart
                          child: TextFormField(
                            initialValue: cond['value']?.toString() ?? '',
                            decoration: const InputDecoration(
                              labelText: 'Value',
                              border: OutlineInputBorder(),
                              contentPadding: EdgeInsets.symmetric(horizontal: AppSpacing.sm),
                            ),
                            onChanged: (val) {
                              _updateCondition(index, 'value', val);
                            },
                          ),
  ```
- **Observation 4 (Invalid Default Role)**: In `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart:60-63`, the default rule value is set to `'org_member'`:
  ```dart
        _conditions = [
          {'field': 'role', 'operator': 'equals', 'value': 'org_member'}
        ];
  ```
  However, in `backend/app/services/auth_service.py:30`, valid roles are defined as `ORG_ROLES = {"org_admin", "org_editor", "org_analyst", "org_viewer"}`.
- **Observation 5 (Tests execution)**:
  - Running `.venv/bin/pytest backend/tests/test_auth.py` succeeded with `9 passed, 125 warnings in 3.29s`.
  - Running `flutter test` inside the `frontend/` directory succeeded with `All tests passed!`.

## 2. Logic Chain
1. **JWT Access Token Claims**: Since `_active_org_claims` does not populate `group_ids`, any token generated on `/api/auth/login` and `/api/auth/refresh` lacks the user's groups.
2. **Database Overhead**: Since authorization checks (`evaluate_visibility_rules`, `user_has_access_to_resource`) do not find `group_ids` in the decoded token claims, they must query the database dynamically on every check, causing unnecessary DB load.
3. **Text Field Re-creation**: In `DynamicGroupRuleBuilder`, when a user types into the value field, `onChanged` is triggered, which invokes `setState` and rebuilds the widget tree. Since the `TextFormField` lacks a controller and only defines `initialValue`, Flutter destroys and rebuilds the underlying element, dropping the focus state and cursor position.
4. **Default Role Mismatch**: Since `'org_member'` is not a valid system role, a dynamic group configured with the default rule will always evaluate to empty (0 matching members).

## 3. Caveats
- Evaluating dynamic group memberships during token creation queries all groups in the user's organizations and evaluates their JSON rules. In organizations with massive user bases and many groups, this could introduce latency. Caching resolved memberships may be needed in the future.
- The `DynamicGroupRuleBuilder` is not currently imported or referenced in other parts of the frontend application. It is assumed to be wired up in a future step.

## 4. Conclusion
- **Backend Fixes**:
  - Update `_active_org_claims` to include resolved `group_ids` list inside the claims for each organization.
  - Optimize `evaluate_visibility_rules` and `user_has_access_to_resource` to read `group_ids` from JWT claims if available.
- **Frontend Fixes**:
  - Add and manage `List<TextEditingController> _controllers` in `_DynamicGroupRuleBuilderState` to preserve keyboard focus and cursor position during rule editing.
  - Correct the default rule value from `'org_member'` to `'org_viewer'`.

## 5. Verification Method
- **Backend Verification**:
  1. Add a test case `test_access_token_contains_group_ids_claims` to `backend/tests/test_auth.py` that verifies that the access token returned on login contains the correct dynamic group IDs in its organization claims.
  2. Run `.venv/bin/pytest backend/tests/test_auth.py`.
- **Frontend Verification**:
  1. Add a widget test in the `frontend/test/` directory targeting `DynamicGroupRuleBuilder` that validates the rule updates and focus retention when entering text.
  2. Run `flutter test`.
