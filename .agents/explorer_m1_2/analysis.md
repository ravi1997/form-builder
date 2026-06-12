# Milestone 1: Dynamic Group Membership Rules - Analysis

This report presents findings from the investigation of Milestone 1, focusing on (1) backend dynamic rule evaluation and access token claims integration, and (2) frontend rule builder widget correctness, and outlines the recommended implementation/fix strategy.

---

## 1. Backend Investigation Findings

### 1.1 Access Token Claims Integration
* **File Path**: `backend/app/services/auth_service.py`
* **Current Behavior**:
  The function `_active_org_claims(user_id)` (lines 145-158) queries active memberships for the user and creates organization claims:
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
  These claims are embedded in the access token during `build_access_token` (called by both `/api/auth/login` and `/api/auth/refresh`).
* **Gap Identified**:
  There is no `"group_ids"` field in the active organization claims dictionary. As a result, the access token does not carry the user's group memberships (either static or dynamic), which is required for frontend and backend API authorization enforcement.
* **Proposed Fix**:
  Include a list of evaluated group IDs inside each organization claim:
  ```python
  "group_ids": get_user_groups(user_id, str(membership.get("org_id")))
  ```

### 1.2 Performance & Refactoring of Rule Evaluation
* **File Path**: `backend/app/services/auth_service.py`
* **Current Behavior**:
  `get_user_groups(user_id, org_id)` fetches all groups in the organization and calls `resolve_group_members(group, org_id)` to check if the user is in the returned member list:
  ```python
  def resolve_group_members(group: dict, org_id: str):
      if group.get("type") == "static":
          return [str(gm.get("user_id")) for gm in mongo.db.group_members.find({"group_id": group["_id"], "is_deleted": False})]
      
      rule = group.get("dynamic_rule") or {}
      if group.get("type") == "dynamic":
          # Queries all memberships in the org
          # Queries all users in the org
          # Evaluates rule on every single user
  ```
* **Gap Identified**:
  Using `resolve_group_members` inside `get_user_groups` during login/refresh is highly inefficient. If an organization has thousands of users, it will fetch all users and memberships and evaluate rules for everyone just to check if the logging-in user matches the group.
* **Proposed Fix**:
  1. Extract `evaluate_condition` and `evaluate_rule` helper functions from `resolve_group_members` into module-level functions `evaluate_dynamic_rule_condition` and `evaluate_dynamic_rule`.
  2. Implement an optimized membership check helper `is_user_in_group(user_doc, membership_doc, group_doc)`:
     - For **static groups**: Check if `mongo.db.group_members.find_one({"group_id": group["_id"], "user_id": user_doc["_id"], "is_deleted": False})` is not null.
     - For **dynamic groups**: Build the candidate dictionary using the user's active membership and user document:
       ```python
       candidate = {
           "role": membership_doc.get("role"),
           "membership_status": membership_doc.get("status"),
           "email": user_doc.get("email"),
           "full_name": user_doc.get("full_name"),
           "status": user_doc.get("status"),
       }
       ```
       and evaluate the extracted `evaluate_dynamic_rule(group.get("dynamic_rule") or {}, candidate)`.
  3. Update `_active_org_claims(user_doc)` to query all active groups in each org and filter them using `is_user_in_group`.

---

## 2. Frontend Investigation Findings

### 2.1 Focus Loss & Cursor Jumping in Value Field
* **File Path**: `frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`
* **Current Behavior**:
  The `ListView.builder` (lines 171-255) renders each condition directly. The Value input field is a `TextFormField` with an `initialValue` (line 235) and its `onChanged` callback directly calls `_updateCondition` (line 241), which calls `setState` on the parent widget:
  ```dart
  void _updateCondition(int index, String key, dynamic val) {
    setState(() {
      _conditions[index][key] = val;
      _notifyChange();
    });
  }
  ```
* **Gap Identified**:
  Calling `setState` in the parent widget on every keystroke forces the entire `ListView.builder` to rebuild. Because the `TextFormField` is recreated without a controller, it loses focus or causes the cursor selection to jump to the beginning/end of the field on every character typed. Additionally, because there are no stable keys on the rows, deleting or adding items can cause state mismatches.
* **Proposed Fix**:
  1. Extract the condition row into a separate `StatefulWidget` (e.g., `DynamicGroupRuleRow`) that manages its own `TextEditingController`.
  2. Maintain a list of unique keys/IDs (`_conditionKeys`) in the parent widget. When rendering, pass a `ValueKey(_conditionKeys[index])` to the row widget to ensure stable widget mapping across deletions/insertions.
  3. In `DynamicGroupRuleRow`'s `didUpdateWidget`, only update the controller's text if the value changes from the outside (preventing self-inflicted cursor jumps).

### 2.2 Invalid Default Role Rule Value
* **Current Behavior**:
  If no initial rule is provided, the builder defaults to:
  ```dart
  _conditions = [
    {'field': 'role', 'operator': 'equals', 'value': 'org_member'}
  ];
  ```
* **Gap Identified**:
  `'org_member'` is not a valid organization role. Valid roles are: `org_admin`, `org_editor`, `org_analyst`, and `org_viewer`. A dynamic rule targeting `'org_member'` will never match any active memberships.
* **Proposed Fix**:
  Change the default `'value'` to a valid role, such as `'org_viewer'`.

---

## 3. Proposal and Diffs

### 3.1 Proposed Backend Diffs (`backend/app/services/auth_service.py`)

```python
# Refactored Evaluation Helpers (Module-Level)
def evaluate_dynamic_rule_condition(cond: dict, candidate: dict) -> bool:
    field = cond.get("field")
    operator = cond.get("operator", "equals")
    value = cond.get("value")
    if not field:
        return False
    candidate_val = candidate.get(field, "")
    
    c_val_str = str(candidate_val) if candidate_val is not None else ""
    val_str = str(value) if value is not None else ""
    
    if operator in ("equals", "eq"):
        return c_val_str == val_str
    elif operator in ("not_equals", "ne"):
        return c_val_str != val_str
    elif operator == "contains":
        return val_str.lower() in c_val_str.lower()
    elif operator == "starts_with":
        return c_val_str.lower().startswith(val_str.lower())
    elif operator == "ends_with":
        return c_val_str.lower().endswith(val_str.lower())
    elif operator == "in":
        if isinstance(value, list):
            return candidate_val in value
        return candidate_val in val_str.split(",")
    return False


def evaluate_dynamic_rule(rule: dict, candidate: dict) -> bool:
    if "logical_operator" in rule or "conditions" in rule:
        op = rule.get("logical_operator", "AND").upper()
        conditions = rule.get("conditions", [])
        if not conditions:
            return True
        if op == "AND":
            return all(evaluate_dynamic_rule(cond, candidate) for cond in conditions)
        elif op == "OR":
            return any(evaluate_dynamic_rule(cond, candidate) for cond in conditions)
        elif op == "NOT":
            return not evaluate_dynamic_rule(conditions[0] if conditions else {}, candidate)
        return False
    else:
        return evaluate_dynamic_rule_condition(rule, candidate)


def is_user_in_group(user_doc: dict, membership_doc: dict, group_doc: dict) -> bool:
    if group_doc.get("type") == "static":
        member_doc = mongo.db.group_members.find_one({
            "group_id": group_doc["_id"],
            "user_id": user_doc["_id"],
            "is_deleted": False
        })
        return member_doc is not None
    elif group_doc.get("type") == "dynamic":
        rule = group_doc.get("dynamic_rule") or {}
        candidate = {
            "role": membership_doc.get("role"),
            "membership_status": membership_doc.get("status"),
            "email": user_doc.get("email"),
            "full_name": user_doc.get("full_name"),
            "status": user_doc.get("status"),
        }
        return evaluate_dynamic_rule(rule, candidate)
    return False
```

```python
# Updated claims resolution
def _active_org_claims(user_id):
    user_doc = mongo.db.users.find_one({"_id": _oid(user_id), "is_deleted": False})
    if not user_doc:
        return []
    memberships = mongo.db.org_memberships.find(
        {"user_id": _oid(user_id), "is_deleted": False, "status": "active"}
    )
    claims = []
    for membership in memberships:
        org_id_str = str(membership.get("org_id"))
        
        # Optimized group membership evaluation
        user_group_ids = []
        groups = mongo.db.groups.find({"org_id": membership.get("org_id"), "is_deleted": False})
        for group in groups:
            if is_user_in_group(user_doc, membership, group):
                user_group_ids.append(str(group["_id"]))
        
        claims.append(
            {
                "org_id": org_id_str,
                "role": membership.get("role", "org_viewer"),
                "status": membership.get("status", "active"),
                "group_ids": user_group_ids,
            }
        )
    return claims
```

### 3.2 Proposed Frontend Diffs (`frontend/lib/features/auth/presentation/widgets/dynamic_group_rule_builder.dart`)

```dart
// Stable Key Management in Parent State:
class _DynamicGroupRuleBuilderState extends State<DynamicGroupRuleBuilder> {
  late String _logicalOperator;
  late List<Map<String, dynamic>> _conditions;
  late List<String> _conditionKeys; // Added stable keys list

  // ...
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
        {'field': 'role', 'operator': 'equals', 'value': 'org_viewer'} // Corrected default value
      ];
    }
    // Generate unique stable keys
    _conditionKeys = List.generate(
      _conditions.length,
      (index) => DateTime.now().microsecondsSinceEpoch.toString() + index.toString(),
    );
  }

  void _addCondition() {
    setState(() {
      _conditions.add({
        'field': 'role',
        'operator': 'equals',
        'value': '',
      });
      _conditionKeys.add(DateTime.now().microsecondsSinceEpoch.toString());
      _notifyChange();
    });
  }

  void _removeCondition(int index) {
    setState(() {
      _conditions.removeAt(index);
      _conditionKeys.removeAt(index);
      _notifyChange();
    });
  }
  
  // ...
  // ListView rendering:
  ListView.builder(
    shrinkWrap: true,
    physics: const NeverScrollableScrollPhysics(),
    itemCount: _conditions.length,
    itemBuilder: (context, index) {
      return Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.sm),
        child: DynamicGroupRuleRow(
          key: ValueKey(_conditionKeys[index]), // Stable key
          condition: _conditions[index],
          fields: _fields,
          operators: _operators,
          onChanged: (newCond) {
            _conditions[index] = newCond;
            _notifyChange();
          },
          onRemove: () => _removeCondition(index),
        ),
      );
    },
  )
}
```

```dart
// DynamicGroupRuleRow (Modular, stateful row that handles its controller)
class DynamicGroupRuleRow extends StatefulWidget {
  final Map<String, dynamic> condition;
  final List<String> fields;
  final List<String> operators;
  final ValueChanged<Map<String, dynamic>> onChanged;
  final VoidCallback onRemove;

  const DynamicGroupRuleRow({
    required this.condition,
    required this.fields,
    required this.operators,
    required this.onChanged,
    required this.onRemove,
    super.key,
  });

  @override
  State<DynamicGroupRuleRow> createState() => _DynamicGroupRuleRowState();
}

class _DynamicGroupRuleRowState extends State<DynamicGroupRuleRow> {
  late TextEditingController _valueController;

  @override
  void initState() {
    super.initState();
    _valueController = TextEditingController(text: widget.condition['value']?.toString() ?? '');
  }

  @override
  void didUpdateWidget(covariant DynamicGroupRuleRow oldWidget) {
    super.didUpdateWidget(oldWidget);
    final newValue = widget.condition['value']?.toString() ?? '';
    if (_valueController.text != newValue) {
      _valueController.value = _valueController.value.copyWith(
        text: newValue,
        selection: TextSelection.collapsed(offset: newValue.length),
      );
    }
  }

  @override
  void dispose() {
    _valueController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Row(
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
                widget.onChanged({
                  ...widget.condition,
                  'field': val,
                });
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
                widget.onChanged({
                  ...widget.condition,
                  'operator': val,
                });
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
              widget.onChanged({
                ...widget.condition,
                'value': val,
              });
            },
          ),
        ),
        const SizedBox(width: AppSpacing.xs),
        IconButton(
          icon: const Icon(Icons.delete, color: Colors.redAccent),
          onPressed: widget.onRemove,
        ),
      ],
    );
  }
}
```
