# Handoff Report — Milestone 1: Dynamic Group Membership Rules

## 1. Observation
- **Scope Reference**: `/home/ravi/workspace/form-builder/.agents/sub_orch_m1/SCOPE.md` lines 13-14:
  > "Evaluation during user login (`/api/auth/login`) and session refresh (`/api/auth/refresh`). The resulting group memberships should be evaluated and included in the JWT access token's organization claims, e.g. as `group_ids` list inside the claims for each organization."
- **Access Token claims in Backend**: In `backend/app/services/auth_service.py` lines 145-158, `_active_org_claims` is defined as:
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
  It does not include `group_ids` in the claims dict.
- **Rule evaluation in Backend**: In `backend/app/services/auth_service.py` lines 423-424 (inside `evaluate_visibility_rules`) and 447-448 (inside `user_has_access_to_resource`):
  ```python
  user_groups = get_user_groups(decoded_token.get("sub"), str(resource_org_id))
  ```
  It calls `get_user_groups` directly, querying the database and re-evaluating rules on every check.
- **Frontend Widget State Rebuilding**: In `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart` lines 234-245:
  ```dart
  // Value text field
  Expanded(
    flex: 4,
    child: TextFormField(
      initialValue: cond['value']?.toString() ?? '',
      ...
      onChanged: (val) {
        _updateCondition(index, 'value', val);
      },
    ),
  ),
  ```
  And `_updateCondition` calls `setState(() { _conditions[index][key] = val; _notifyChange(); });`.
- **Default condition value**: In `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart` lines 60-62:
  ```dart
  _conditions = [
    {'field': 'role', 'operator': 'equals', 'value': 'org_member'}
  ];
  ```
- **Backend valid roles**: In `backend/app/services/auth_service.py` line 30:
  ```python
  ORG_ROLES = {"org_admin", "org_editor", "org_analyst", "org_viewer"}
  ```

---

## 2. Logic Chain
1. **Observation 1 & 2**: The JWT org claims list lacks `group_ids`. This directly violates the interface contract defined in `SCOPE.md`.
2. **Observation 3**: The backend performs recursive rule evaluation directly against the database on every single element visibility check or resource access check. Since the access token does not store the evaluated groups, caching them in the JWT claims during token creation (login/refresh) and loading them directly from claims will significantly optimize performance.
3. **Observation 4**: The `DynamicGroupRuleBuilder` widget reconstructs text fields dynamically within `ListView.builder` on every keystroke by calling parent `setState` through `onChanged`. Because these text fields do not have stable keys or persistent state/controllers across parent rebuilds, the widget state is discarded, causing instant focus loss and cursor resetting.
4. **Observation 5 & 6**: The widget's default condition uses `org_member` as the default role value. However, the backend only recognizes `org_admin`, `org_editor`, `org_analyst`, and `org_viewer`. Therefore, any group created with the default rule will result in empty membership, which is a logic mismatch.

---

## 3. Caveats
- We assume that the JWT claims inside the token are of a reasonable size. Since organizations typically have a small number of groups per user (usually < 20), including their object IDs in the access token claims will not cause token bloat.
- We assume that group memberships do not change mid-session in a way that requires real-time enforcement without session refresh. If immediate revocation is required, using JWT claims means the group changes won't take effect until the access token expires (15 minutes) or is refreshed. This is standard JWT behavior and matches the `SCOPE.md` requirements.

---

## 4. Conclusion
Milestone 1 is currently incomplete and has critical flaws:
1. **Backend**: Missing `group_ids` in access token JWT claims, and sub-optimal DB query behavior on resource checks.
2. **Frontend**: The `DynamicGroupRuleBuilder` widget is unusable due to a focus loss bug when typing rules, and initializes with an invalid default role (`org_member`).

Both can be resolved via:
1. Caching evaluated `group_ids` inside the organization claims inside `_active_org_claims` and updating token verification to consume from claims.
2. Introducing a stateful child row widget `_ConditionRow` using an `ObjectKey` and `TextEditingController` inside `DynamicGroupRuleBuilder`, and changing the default rule role value to `org_viewer`.

---

## 5. Verification Method
- **Backend verification**:
  - Run `../.venv/bin/pytest` in `backend` to ensure all existing tests pass.
  - Implement a new test `test_jwt_claims_include_group_ids` in `backend/tests/test_auth.py` and run it.
- **Frontend verification**:
  - Run `flutter test` in `frontend` to ensure existing tests pass.
  - Add a widget test in `frontend/test/dynamic_group_rule_builder_test.dart` to verify that text fields retain focus during keystrokes.
