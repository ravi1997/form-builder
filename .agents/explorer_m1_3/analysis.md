# Milestone 1: Dynamic Group Membership Rules - Explorer Analysis Report

## Summary
An investigation was conducted on the backend authentication services and the frontend dynamic group rule builder widget. We identified several crucial improvements and bug fixes:
1. **Backend**: Access token claims (`group_ids`) are currently missing from organization claims during login and refresh. We propose populating `group_ids` dynamically in `_active_org_claims` and optimizing resource access checks to read from JWT claims instead of querying the database.
2. **Frontend**: The `DynamicGroupRuleBuilder` widget suffers from focus loss and cursor jumps when typing condition values, because `TextFormField` is recreated without a controller on every keystroke. Additionally, the default rule value of `"org_member"` is invalid, as the backend only supports `"org_admin"`, `"org_editor"`, `"org_analyst"`, and `"org_viewer"`.

---

## 1. Backend Analysis & Proposed Fixes

### 1.1 Lack of `group_ids` in JWT access token claims
In `backend/app/services/auth_service.py`, `_active_org_claims` is responsible for building claims for each organization membership. Currently, it only includes `org_id`, `role`, and `status`:
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

**Proposed Fix**:
Modify `_active_org_claims` to call `get_user_groups(user_id, org_id_str)` to query and resolve group memberships at token construction (which is used by both `/api/auth/login` and `/api/auth/refresh`).

```python
def _active_org_claims(user_id):
    memberships = mongo.db.org_memberships.find(
        {"user_id": _oid(user_id), "is_deleted": False, "status": "active"}
    )
    claims = []
    for membership in memberships:
        org_id_str = str(membership.get("org_id"))
        claims.append(
            {
                "org_id": org_id_str,
                "role": membership.get("role", "org_viewer"),
                "status": membership.get("status", "active"),
                "group_ids": get_user_groups(user_id, org_id_str),
            }
        )
    return claims
```

### 1.2 Resource Access Optimization
Since the access token now contains the user's groups, we should optimize `evaluate_visibility_rules` and `user_has_access_to_resource` in `backend/app/services/auth_service.py` to read groups from the JWT claims first. This minimizes database queries during request authorization.

**Patch for `evaluate_visibility_rules`**:
```python
        elif ctype == "group":
            user_groups = None
            orgs_claims = decoded_token.get("orgs", [])
            for claim in orgs_claims:
                if str(claim.get("org_id")) == str(resource_org_id):
                    user_groups = claim.get("group_ids")
                    break
            if user_groups is None:
                user_groups = get_user_groups(decoded_token.get("sub"), str(resource_org_id))
            results.append(any(str(group_id) in set(condition.get("group_ids", [])) for group_id in user_groups))
```

**Patch for `user_has_access_to_resource`**:
```python
            if access_type == "groups":
                user_groups = None
                orgs_claims = decoded_token.get("orgs", [])
                for claim in orgs_claims:
                    if str(claim.get("org_id")) == str(resource.get("org_id")):
                        user_groups = claim.get("group_ids")
                        break
                if user_groups is None:
                    user_groups = get_user_groups(decoded_token.get("sub"), str(resource.get("org_id")))
                user_groups = set(user_groups)
                allowed_groups = {str(gid) for gid in form_access.get("allowed_group_ids", [])}
                return bool(user_groups & allowed_groups)
```

---

## 2. Frontend Analysis & Proposed Fixes

### 2.1 Focus Loss & Cursor Jump in `DynamicGroupRuleBuilder`
In `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`, the `TextFormField` is constructed as:
```dart
TextFormField(
  initialValue: cond['value']?.toString() ?? '',
  ...
  onChanged: (val) {
    _updateCondition(index, 'value', val);
  },
)
```
Where `_updateCondition` calls `setState` and triggers a full rebuild. Without a persistent `TextEditingController`, Flutter destroys and rebuilds the `TextFormField` element, dropping the keyboard focus and resetting the cursor position.

**Proposed Fix**:
Manage a `List<TextEditingController> _controllers` within `_DynamicGroupRuleBuilderState`. Add, remove, and dispose of these controllers in sync with `_conditions`.

```dart
class _DynamicGroupRuleBuilderState extends State<DynamicGroupRuleBuilder> {
  late String _logicalOperator;
  late List<Map<String, dynamic>> _conditions;
  late List<TextEditingController> _controllers; // Keep track of text controllers
  
  // ...
  
  @override
  void initState() {
    super.initState();
    _loadRule(widget.initialRule);
  }

  void _loadRule(Map<String, dynamic>? rule) {
    // ...
    // Map initial rules, change default rule value to 'org_viewer'
    // ...
    _controllers = _conditions
        .map((c) => TextEditingController(text: c['value']?.toString() ?? ''))
        .toList();
  }

  @override
  void dispose() {
    for (final controller in _controllers) {
      controller.dispose();
    }
    super.dispose();
  }

  void _addCondition() {
    setState(() {
      _conditions.add({
        'field': 'role',
        'operator': 'equals',
        'value': '',
      });
      _controllers.add(TextEditingController(text: ''));
      _notifyChange();
    });
  }

  void _removeCondition(int index) {
    setState(() {
      _conditions.removeAt(index);
      _controllers[index].dispose();
      _controllers.removeAt(index);
      _notifyChange();
    });
  }
}
```
And bind the controller in `build`:
```dart
TextFormField(
  controller: _controllers[index],
  decoration: const InputDecoration(
    labelText: 'Value',
    border: OutlineInputBorder(),
    contentPadding: EdgeInsets.symmetric(horizontal: AppSpacing.sm),
  ),
  onChanged: (val) {
    _updateCondition(index, 'value', val);
  },
)
```

### 2.2 Invalid Default Role `"org_member"`
The builder uses `'org_member'` as a default value when no initial rule is provided:
```dart
      _conditions = [
        {'field': 'role', 'operator': 'equals', 'value': 'org_member'}
      ];
```
However, the system defines valid organization roles in `auth_service.py` as:
```python
ORG_ROLES = {"org_admin", "org_editor", "org_analyst", "org_viewer"}
```
Setting `'org_member'` results in empty dynamic groups by default.
**Proposed Fix**:
Change the default value to a valid system role, such as `'org_viewer'`.
