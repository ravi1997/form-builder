# Analysis Report — Milestone 1: Dynamic Group Membership Rules

## Executive Summary
This report details the exploration and analysis of Milestone 1: Dynamic Group Membership Rules. It analyzes the backend Python/Flask service handling group membership rule evaluation and access token generation, alongside the frontend Flutter widget (`DynamicGroupRuleBuilder`) used to construct these dynamic rules. It identifies key deficiencies in both parts and outlines a comprehensive strategy for implementation and verification.

---

## 1. Backend Analysis: Dynamic Rule Evaluation & JWT Claims
We examined `backend/app/services/auth_service.py` and `backend/app/routes/auth.py`.

### 1.1 Current Evaluation Logic
- **`resolve_group_members(group: dict, org_id: str)`**:
  - Successfully handles both `static` and `dynamic` groups.
  - Queries `org_memberships` for active members, fetches the matching users, and constructs a `candidate` context dictionary for each membership.
  - Evaluates recursive nested rules (e.g. `AND`, `OR`, `NOT`) via helper `evaluate_rule(rule, candidate)` and evaluates leaf conditions via `evaluate_condition(cond, candidate)`.
  - Leaf conditions support fields: `role`, `membership_status` (membership's `status`), `email`, `full_name`, and `status` (user's `status`).
  - Supported operators: `equals` (`eq`), `not_equals` (`ne`), `contains`, `starts_with`, `ends_with`, and `in`.
- **`get_user_groups(user_id: str, org_id: str)`**:
  - Dynamically calculates the groups a user belongs to in an organization by iterating over all active groups, calling `resolve_group_members`, and checking if `user_id` is in the matched members list.

### 1.2 Identified Deficiencies & Missing Requirements
1. **Missing Access Token Claims**:
   - During user login (`/api/auth/login`) and session refresh (`/api/auth/refresh`), the access token is constructed by `build_access_token`, which calls `_active_org_claims(user_id)`.
   - Currently, `_active_org_claims` includes only `org_id`, `role`, and `status` in the JWT claims for each active membership. The evaluated group memberships (`group_ids`) are **completely missing** from the claims.
2. **Performance Bottleneck on Rule Evaluation**:
   - `get_user_groups` is called on *every* request checking resource access (e.g., in `user_has_access_to_resource` for forms/responses and in `evaluate_visibility_rules` for form elements).
   - This database-intensive check retrieves all groups, fetches all users in the organization, and re-evaluates all dynamic rules *per request*.
   - **Fix**: Cache the evaluated `group_ids` list in the access token's organization claims during login/refresh. On subsequent API calls, read `group_ids` directly from the decoded JWT claims instead of querying the database.

### 1.3 Proposed Backend Fixes
1. **Include Group IDs in Claims (`_active_org_claims`)**:
   Update `_active_org_claims` in `backend/app/services/auth_service.py` to evaluate the user's groups:
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
                   "group_ids": get_user_groups(user_id, org_id_str), # Added group_ids
               }
           )
       return claims
   ```

2. **Retrieve Groups from Claims with Fallback**:
   Introduce a helper function in `auth_service.py` to retrieve the groups from the JWT claims, falling back to database query for backward compatibility (e.g. for existing unit tests that pass mock decoded tokens):
   ```python
   def get_user_groups_from_claims_or_db(decoded_token: dict[str, Any], org_id: str, user_id: str):
       org_oid = str(org_id)
       for claim in decoded_token.get("orgs", []):
           if str(claim.get("org_id")) == org_oid and claim.get("status") == "active":
               if "group_ids" in claim:
                   return claim["group_ids"]
       return get_user_groups(user_id, org_id)
   ```
   Update line 423 (in `evaluate_visibility_rules`) and line 447 (in `user_has_access_to_resource`) to call this helper instead of direct `get_user_groups` calls.

---

## 2. Frontend Analysis: DynamicGroupRuleBuilder Widget
We examined `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`.

### 2.1 Identified Bugs & UI/UX Issues
1. **Focus Loss & Cursor Resetting Bug**:
   - The value field uses `TextFormField` with `initialValue: cond['value']?.toString() ?? ''`.
   - On every keystroke, the `onChanged` callback calls `_updateCondition`, which updates the parent state via `setState`.
   - Rebuilding the parent widget causes `ListView.builder` to rebuild all row widgets. Because they lack a stable `Key` and are recreated, Flutter discards the state of the text fields, resulting in immediate **focus loss** and the **cursor jumping** to the end of the text on every character typed.
2. **Invalid Default Rule Value**:
   - When no rule is provided, the default rule initialized is:
     `{'field': 'role', 'operator': 'equals', 'value': 'org_member'}`.
   - However, `org_member` is **not** a valid organization role on the backend (valid roles are: `org_admin`, `org_editor`, `org_analyst`, `org_viewer`). No user will ever match the default rule.
   - **Fix**: Change the default role value to `org_viewer`.
3. **Missing `didUpdateWidget` Handling**:
   - The state class does not override `didUpdateWidget`.
   - If the parent resets the rule (e.g., clearing the form from the outside), `DynamicGroupRuleBuilder` will ignore the change and continue displaying the old state.
   - **Fix**: Implement `didUpdateWidget` with a deep comparison check to safely reload the rule when it is modified by the parent.

### 2.2 Proposed Frontend Refactoring
Introduce a stateful `_ConditionRow` widget for each condition row in the list to encapsulate text controllers, and assign it a stable `ObjectKey` in `ListView.builder`.

#### Proposed Replacement for `dynamic_group_rule_builder.dart`:
```dart
import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/design_system.dart';

class DynamicGroupRuleBuilder extends StatefulWidget {
  final Map<String, dynamic>? initialRule;
  final ValueChanged<Map<String, dynamic>> onChanged;

  const DynamicGroupRuleBuilder({
    super.key,
    this.initialRule,
    required this.onChanged,
  });

  @override
  State<DynamicGroupRuleBuilder> createState() => _DynamicGroupRuleBuilderState();
}

class _DynamicGroupRuleBuilderState extends State<DynamicGroupRuleBuilder> {
  late String _logicalOperator;
  late List<Map<String, dynamic>> _conditions;

  final List<String> _fields = [
    'role',
    'email',
    'full_name',
    'status',
    'membership_status',
  ];

  final List<String> _operators = [
    'equals',
    'not_equals',
    'contains',
    'starts_with',
    'ends_with',
    'in',
  ];

  @override
  void initState() {
    super.initState();
    _loadRule(widget.initialRule);
  }

  @override
  void didUpdateWidget(covariant DynamicGroupRuleBuilder oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialRule != oldWidget.initialRule) {
      final oldRule = oldWidget.initialRule;
      final newRule = widget.initialRule;
      if (!_areRulesEqual(oldRule, newRule)) {
        setState(() {
          _loadRule(newRule);
        });
      }
    }
  }

  bool _areRulesEqual(Map<String, dynamic>? r1, Map<String, dynamic>? r2) {
    if (r1 == null && r2 == null) return true;
    if (r1 == null || r2 == null) return false;
    
    final op1 = r1['logical_operator'] ?? 'AND';
    final op2 = r2['logical_operator'] ?? 'AND';
    if (op1 != op2) return false;

    final cond1 = r1['conditions'] as List?;
    final cond2 = r2['conditions'] as List?;
    if (cond1 == null && cond2 == null) return true;
    if (cond1 == null || cond2 == null) return false;
    if (cond1.length != cond2.length) return false;

    for (int i = 0; i < cond1.length; i++) {
      final c1 = cond1[i] as Map?;
      final c2 = cond2[i] as Map?;
      if (c1 == null && c2 == null) continue;
      if (c1 == null || c2 == null) return false;
      if (c1['field'] != c2['field'] ||
          c1['operator'] != c2['operator'] ||
          c1['value']?.toString() != c2['value']?.toString()) {
        return false;
      }
    }
    return true;
  }

  void _loadRule(Map<String, dynamic>? rule) {
    if (rule != null && (rule.containsKey('logical_operator') || rule.containsKey('conditions'))) {
      _logicalOperator = rule['logical_operator'] ?? 'AND';
      final rawConditions = rule['conditions'] as List?;
      _conditions = rawConditions != null
          ? List<Map<String, dynamic>>.from(
              rawConditions.map((c) => Map<String, dynamic>.from(c as Map)),
            )
          : [];
    } else if (rule != null && rule.containsKey('field')) {
      _logicalOperator = 'AND';
      _conditions = [Map<String, dynamic>.from(rule)];
    } else {
      _logicalOperator = 'AND';
      _conditions = [
        {'field': 'role', 'operator': 'equals', 'value': 'org_viewer'} // Fixed default from 'org_member' to 'org_viewer'
      ];
    }
  }

  void _notifyChange() {
    widget.onChanged({
      'logical_operator': _logicalOperator,
      'conditions': _conditions,
    });
  }

  void _addCondition() {
    setState(() {
      _conditions.add({
        'field': 'role',
        'operator': 'equals',
        'value': '',
      });
      _notifyChange();
    });
  }

  void _removeCondition(int index) {
    setState(() {
      _conditions.removeAt(index);
      _notifyChange();
    });
  }

  void _updateCondition(int index, Map<String, dynamic> updatedCond) {
    setState(() {
      _conditions[index] = updatedCond;
      _notifyChange();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      color: AppColors.surfaceCard.withOpacity(0.4),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        side: BorderSide(
          color: AppColors.borderSubtle.withOpacity(0.3),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text(
                  'Match',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                DropdownButton<String>(
                  value: _logicalOperator,
                  dropdownColor: AppColors.surfaceCard,
                  style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.white),
                  items: ['AND', 'OR'].map((op) {
                    return DropdownMenuItem<String>(
                      value: op,
                      child: Text(op),
                    );
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) {
                      setState(() {
                        _logicalOperator = val;
                        _notifyChange();
                      });
                    }
                  },
                ),
                const SizedBox(width: AppSpacing.sm),
                const Text(
                  'of the following conditions:',
                  style: TextStyle(fontSize: 14),
                ),
                const Spacer(),
                ElevatedButton.icon(
                  onPressed: _addCondition,
                  icon: const Icon(Icons.add, size: 16),
                  label: const Text('Add Condition'),
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm,
                      vertical: AppSpacing.xs,
                    ),
                  ),
                ),
              ],
            ),
            const Divider(height: AppSpacing.lg),
            if (_conditions.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
                child: Text(
                  'No conditions configured. All members in organization will be included.',
                  style: TextStyle(fontStyle: FontStyle.italic, color: Colors.grey),
                ),
              )
            else
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _conditions.length,
                itemBuilder: (context, index) {
                  final cond = _conditions[index];
                  return _ConditionRow(
                    key: ObjectKey(cond), // Crucial for preserving item state & focus
                    condition: cond,
                    fields: _fields,
                    operators: _operators,
                    onChanged: (updated) => _updateCondition(index, updated),
                    onDeleted: () => _removeCondition(index),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }
}

class _ConditionRow extends StatefulWidget {
  final Map<String, dynamic> condition;
  final List<String> fields;
  final List<String> operators;
  final ValueChanged<Map<String, dynamic>> onChanged;
  final VoidCallback onDeleted;

  const _ConditionRow({
    super.key,
    required this.condition,
    required this.fields,
    required this.operators,
    required this.onChanged,
    required this.onDeleted,
  });

  @override
  State<_ConditionRow> createState() => _ConditionRowState();
}

class _ConditionRowState extends State<_ConditionRow> {
  late TextEditingController _valueController;

  @override
  void initState() {
    super.initState();
    _valueController = TextEditingController(text: widget.condition['value']?.toString() ?? '');
  }

  @override
  void didUpdateWidget(covariant _ConditionRow oldWidget) {
    super.didUpdateWidget(oldWidget);
    final newValue = widget.condition['value']?.toString() ?? '';
    if (_valueController.text != newValue) {
      _valueController.text = newValue;
    }
  }

  @override
  void dispose() {
    _valueController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        children: [
          // Field dropdown
          Expanded(
            flex: 3,
            child: DropdownButtonFormField<String>(
              value: widget.fields.contains(widget.condition['field']) ? widget.condition['field'] : widget.fields.first,
              decoration: const InputDecoration(
                labelText: 'Field',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: AppSpacing.sm),
              ),
              dropdownColor: AppColors.surfaceCard,
              items: widget.fields.map((f) {
                return DropdownMenuItem(
                  value: f,
                  child: Text(f),
                );
              }).toList(),
              onChanged: (val) {
                if (val != null) {
                  final updated = Map<String, dynamic>.from(widget.condition);
                  updated['field'] = val;
                  widget.onChanged(updated);
                }
              },
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          // Operator dropdown
          Expanded(
            flex: 3,
            child: DropdownButtonFormField<String>(
              value: widget.operators.contains(widget.condition['operator']) ? widget.condition['operator'] : widget.operators.first,
              decoration: const InputDecoration(
                labelText: 'Operator',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: AppSpacing.sm),
              ),
              dropdownColor: AppColors.surfaceCard,
              items: widget.operators.map((op) {
                return DropdownMenuItem(
                  value: op,
                  child: Text(op),
                );
              }).toList(),
              onChanged: (val) {
                if (val != null) {
                  final updated = Map<String, dynamic>.from(widget.condition);
                  updated['operator'] = val;
                  widget.onChanged(updated);
                }
              },
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          // Value text field
          Expanded(
            flex: 4,
            child: TextFormField(
              controller: _valueController,
              decoration: const InputDecoration(
                labelText: 'Value',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: AppSpacing.sm),
              ),
              onChanged: (val) {
                final updated = Map<String, dynamic>.from(widget.condition);
                updated['value'] = val;
                widget.onChanged(updated);
              },
            ),
          ),
          const SizedBox(width: AppSpacing.xs),
          IconButton(
            icon: const Icon(Icons.delete, color: Colors.redAccent),
            onPressed: widget.onDeleted,
          ),
        ],
      ),
    );
  }
}
```

---

## 3. Implementation and Verification Strategy
This strategy details the sequence of modifications and verification steps.

### 3.1 Step-by-Step Implementation Sequence
1. **Backend Improvements**:
   - Modify `backend/app/services/auth_service.py` to add `group_ids` to token claims.
   - Introduce `get_user_groups_from_claims_or_db` and refactor existing resource/visibility logic.
2. **Backend Tests**:
   - Write integration test verification in `backend/tests/test_auth.py` (e.g., `test_jwt_claims_include_group_ids`).
3. **Frontend Refactoring**:
   - Overwrite `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart` with the refactored code.
4. **Frontend Tests**:
   - Add widget test verification in `frontend/test/dynamic_group_rule_builder_test.dart` simulating user typing.

### 3.2 Verification Methods
- **Backend Tests**: Run `/home/ravi/workspace/form-builder/.venv/bin/pytest` and verify success of all tests.
- **Frontend Tests**: Run `flutter test` and verify that all widget and unit tests pass.
