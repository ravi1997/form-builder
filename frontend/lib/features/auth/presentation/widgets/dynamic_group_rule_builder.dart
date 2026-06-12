import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/design_system.dart';
import '../../../../core/theme/tokens.dart';

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
  late List<String> _conditionKeys; // Stable unique keys for each row

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
    final currentRule = {
      'logical_operator': _logicalOperator,
      'conditions': _conditions,
    };
    if (!_areRulesEqual(widget.initialRule, currentRule)) {
      setState(() {
        _loadRule(widget.initialRule);
      });
    }
  }

  bool _areRulesEqual(Map<String, dynamic>? r1, Map<String, dynamic>? r2) {
    if (r1 == null && r2 == null) return true;
    if (r1 == null || r2 == null) return false;

    // Check logical_operator
    final op1 = r1['logical_operator'] ?? 'AND';
    final op2 = r2['logical_operator'] ?? 'AND';
    if (op1 != op2) return false;

    // If they represent a single condition style (not nested conditions list)
    final isSingle1 = r1.containsKey('field');
    final isSingle2 = r2.containsKey('field');
    if (isSingle1 != isSingle2) return false;

    if (isSingle1) {
      return r1['field'] == r2['field'] &&
          r1['operator'] == r2['operator'] &&
          r1['value']?.toString() == r2['value']?.toString();
    }

    final cond1 = r1['conditions'] as List?;
    final cond2 = r2['conditions'] as List?;
    if (cond1 == null && cond2 == null) return true;
    if (cond1 == null || cond2 == null) return false;
    if (cond1.length != cond2.length) return false;

    for (int i = 0; i < cond1.length; i++) {
      final c1 = cond1[i];
      final c2 = cond2[i];
      if (c1 is! Map || c2 is! Map) return false;
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
        {'field': 'role', 'operator': 'equals', 'value': 'org_viewer'}
      ];
    }

    // Generate unique stable keys for list items
    _conditionKeys = List.generate(
      _conditions.length,
      (index) => '${DateTime.now().microsecondsSinceEpoch}_${index}_${UniqueKey().toString()}',
    );
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
      _conditionKeys.add('${DateTime.now().microsecondsSinceEpoch}_${_conditions.length}_${UniqueKey().toString()}');
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
                  return Padding(
                    padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                    child: _ConditionRow(
                      key: ValueKey(_conditionKeys[index]),
                      condition: cond,
                      fields: _fields,
                      operators: _operators,
                      onChanged: (updated) => _updateCondition(index, updated),
                      onDeleted: () => _removeCondition(index),
                    ),
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
    );
  }
}
