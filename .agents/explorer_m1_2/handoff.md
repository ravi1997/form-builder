# Milestone 1 Handoff Report - Dynamic Group Membership Rules

This is a **Hard Handoff** containing the complete analysis and plan for the implementer agent.

---

## 1. Observation

### Observation 1.1: Missing `group_ids` in Access Token Claims
* **File**: `backend/app/services/auth_service.py`
* **Line Range**: 145-171
* **Verbatim Code**:
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
  And:
  ```python
  def build_access_token(user_doc):
      now = int(_now().timestamp())
      payload = {
          "sub": str(user_doc["_id"]),
          "email": user_doc.get("email"),
          "system_role": user_doc.get("system_role", "user"),
          "orgs": _active_org_claims(user_doc["_id"]),
          "iat": now,
          "exp": now + ACCESS_TOKEN_TTL_SECONDS,
      }
      return jwt.encode(payload, _jwt_secret(), algorithm="HS256")
  ```

### Observation 1.2: Inefficient Group Membership Lookup
* **File**: `backend/app/services/auth_service.py`
* **Line Range**: 453-460, 468-480
* **Verbatim Code**:
  ```python
  def get_user_groups(user_id: str, org_id: str):
      result = []
      groups = mongo.db.groups.find({"org_id": _oid(org_id), "is_deleted": False})
      for group in groups:
          members = resolve_group_members(group, org_id)
          if str(user_id) in {str(member_id) for member_id in members}:
              result.append(str(group["_id"]))
      return result
  ```
  And:
  ```python
  def resolve_group_members(group: dict, org_id: str):
      ...
      if group.get("type") == "dynamic":
          memberships = list(mongo.db.org_memberships.find({
              "org_id": _oid(org_id),
              "status": "active",
              "is_deleted": False,
          }))
          if not memberships:
              return []
          
          user_ids = [m["user_id"] for m in memberships]
          users_cursor = mongo.db.users.find({"_id": {"$in": user_ids}})
          users_map = {str(u["_id"]): u for u in users_cursor}
  ```

### Observation 1.3: Focus Loss & Cursor Jumping in Rule Builder
* **File**: `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`
* **Line Range**: 91-96, 171-179, 234-245
* **Verbatim Code**:
  ```dart
  void _updateCondition(int index, String key, dynamic val) {
    setState(() {
      _conditions[index][key] = val;
      _notifyChange();
    });
  }
  ```
  And:
  ```dart
  ListView.builder(
    shrinkWrap: true,
    physics: const NeverScrollableScrollPhysics(),
    itemCount: _conditions.length,
    itemBuilder: (context, index) {
      final cond = _conditions[index];
      return Padding(
        ...
        child: Row(
          children: [
            ...
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

### Observation 1.4: Invalid Default Role Rule Value
* **File**: `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`
* **Line Range**: 60-62
* **Verbatim Code**:
  ```dart
  _conditions = [
    {'field': 'role', 'operator': 'equals', 'value': 'org_member'}
  ];
  ```

---

## 2. Logic Chain

1. **Access Token Generation**:
   * When users log in (via `/api/auth/login`) or refresh sessions (via `/api/auth/refresh`), their access token is constructed using `build_access_token` (Observation 1.1).
   * `build_access_token` calls `_active_org_claims(user_doc["_id"])` to construct organization claims (Observation 1.1).
   * Since `_active_org_claims` only includes `org_id`, `role`, and `status`, the token misses group membership details, preventing enforcement of group-level access rules (Conclusion 1).
2. **Performance Constraints on Token Resolution**:
   * Resolving a user's groups currently relies on `get_user_groups`, which calls `resolve_group_members` for every group in the org (Observation 1.2).
   * If a group is dynamic, `resolve_group_members` queries all memberships and users in the organization to check if they match the rule (Observation 1.2).
   * Doing this for every login/refresh is extremely inefficient because it turns a single user login into an O(N) database-and-evaluation scan of all organization members (Conclusion 2).
   * Therefore, we must refactor rule evaluation to evaluate the rule directly against a single user's `candidate` profile, and retrieve static group memberships via direct query.
3. **Frontend Widget Rebuilds and Focus Loss**:
   * The `TextFormField` value field uses `initialValue` and triggers `_updateCondition` on every keystroke (`onChanged`) (Observation 1.3).
   * `_updateCondition` calls `setState` in the parent state, which forces `ListView.builder` to rebuild all item widgets (Observation 1.3).
   * Because the list is rebuilt without stable keys, and because the `TextFormField` does not have a persistent `TextEditingController` but relies on `initialValue`, Flutter recreates the text field widget/state, resulting in immediate loss of focus and cursor reset to position 0 after typing a single letter (Conclusion 3).
   * Therefore, we must extract the row into a `StatefulWidget` (`DynamicGroupRuleRow`) that manages its own `TextEditingController`, and render the rows with unique, stable keys (`ValueKey`).
4. **Invalid Default Rule**:
   * The default condition specifies `'value': 'org_member'` (Observation 1.4).
   * However, there is no `'org_member'` role in the backend (valid roles are `org_admin`, `org_editor`, `org_analyst`, `org_viewer`).
   * This means a user creating a rule with the default role field will never match any members unless they manually edit the text (Conclusion 4).

---

## 3. Caveats

* We assume that group permissions only need to be updated during token login or refresh. If a user's membership changes while they have a valid session, the token is not automatically re-evaluated until their next token refresh (which occurs every 15 minutes by default). This is normal JWT behavior.
* We assume that user attributes (like `status`, `full_name`, `email`) and membership roles (`role`, `status`) do not contain complex nested BSON structures that require special MongoDB-specific queries. The current `candidate` construction standardizes fields as strings, which is sufficient.

---

## 4. Conclusion

Milestone 1 requires:
1. **Backend updates**:
   * Refactoring the inner helper functions of `resolve_group_members` (`evaluate_condition` and `evaluate_rule`) to module-level functions.
   * Implementing `is_user_in_group(user_doc, membership, group)` to perform an O(1) membership check.
   * Modifying `_active_org_claims` to include `group_ids` list resolved using the optimized `is_user_in_group` check.
2. **Frontend updates**:
   * Modifying `dynamic_group_rule_builder.dart` to use a list of unique stable keys for condition rows.
   * Extracting the list item row into a stateful `DynamicGroupRuleRow` containing its own `TextEditingController` to prevent cursor jumps and focus loss.
   * Fixing the default role value from `'org_member'` to `'org_viewer'`.

---

## 5. Verification Method

### 5.1 Backend Verification
* **Test Command**: `pytest tests/test_auth.py` from the `backend/` directory using the virtualenv `../.venv/bin/pytest`.
* **Testing Plan**:
  Add a unit test `test_access_token_contains_group_ids(client, db)` in `backend/tests/test_auth.py`. The test should:
  1. Register a user and mark them active.
  2. Create an organization membership.
  3. Create a static group and add the user.
  4. Create a dynamic group with a rule matching the user (e.g. `role == 'org_admin'`).
  5. Login the user and decode the returned access token's claims.
  6. Assert that `decoded["orgs"][0]["group_ids"]` contains both the static and dynamic group IDs.

### 5.2 Frontend Verification
* **Test Command**: `flutter test` in `frontend/` directory.
* **Testing Plan**:
  Create a widget test `frontend/test/dynamic_group_rule_builder_test.dart` that:
  1. Builds `DynamicGroupRuleBuilder` inside a `MaterialApp`.
  2. Taps the value text field, inputs characters (e.g., `'admin'`), and triggers `tester.pump()`.
  3. Verifies that the widget has updated the value, and that the text field is still focused (verifying focus is not lost and cursor position hasn't reset).
  4. Adds and deletes conditions and verifies that state of other rows remains intact.
