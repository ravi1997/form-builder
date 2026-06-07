enum LogicalOperator {
  and,
  or;

  static LogicalOperator fromString(String val) {
    return val.toLowerCase() == 'or' ? LogicalOperator.or : LogicalOperator.and;
  }
}

enum AnswerOperator {
  equals,
  notEquals,
  contains,
  greaterThan,
  lessThan,
  inList,
  notInList,
  isEmpty,
  isNotEmpty;

  static AnswerOperator fromString(String val) {
    switch (val) {
      case 'equals': return AnswerOperator.equals;
      case 'notEquals':
      case 'not_equals': return AnswerOperator.notEquals;
      case 'contains': return AnswerOperator.contains;
      case 'greaterThan':
      case 'greater_than': return AnswerOperator.greaterThan;
      case 'lessThan':
      case 'less_than': return AnswerOperator.lessThan;
      case 'inList':
      case 'in_list': return AnswerOperator.inList;
      case 'notInList':
      case 'not_in_list': return AnswerOperator.notInList;
      case 'isEmpty':
      case 'is_empty': return AnswerOperator.isEmpty;
      case 'isNotEmpty':
      case 'is_not_empty': return AnswerOperator.isNotEmpty;
      default: return AnswerOperator.equals;
    }
  }
}

abstract class Condition {
  const Condition();

  factory Condition.fromJson(Map<String, dynamic> json) {
    final type = json['type'] ?? '';
    switch (type) {
      case 'role':
        return RoleCondition(roles: List<String>.from(json['roles'] ?? const []));
      case 'group':
        return GroupCondition(groupIds: List<String>.from(json['groupIds'] ?? json['group_ids'] ?? const []));
      case 'answer':
        return AnswerCondition(
          fieldId: json['fieldId'] ?? json['field_id'] ?? '',
          operator: AnswerOperator.fromString(json['operator'] ?? ''),
          value: json['value'],
        );
      case 'alwaysHidden':
      case 'always_hidden':
        return const AlwaysHiddenCondition();
      case 'alwaysVisible':
      case 'always_visible':
      default:
        return const AlwaysVisibleCondition();
    }
  }

  Map<String, dynamic> toJson();
}

class RoleCondition extends Condition {
  final List<String> roles;
  const RoleCondition({required this.roles});

  @override
  Map<String, dynamic> toJson() => {'type': 'role', 'roles': roles};
}

class GroupCondition extends Condition {
  final List<String> groupIds;
  const GroupCondition({required this.groupIds});

  @override
  Map<String, dynamic> toJson() => {'type': 'group', 'groupIds': groupIds};
}

class AnswerCondition extends Condition {
  final String fieldId;
  final AnswerOperator operator;
  final dynamic value;

  const AnswerCondition({
    required this.fieldId,
    required this.operator,
    this.value,
  });

  @override
  Map<String, dynamic> toJson() => {
    'type': 'answer',
    'fieldId': fieldId,
    'operator': operator.name,
    'value': value,
  };
}

class AlwaysVisibleCondition extends Condition {
  const AlwaysVisibleCondition();
  @override
  Map<String, dynamic> toJson() => {'type': 'alwaysVisible'};
}

class AlwaysHiddenCondition extends Condition {
  const AlwaysHiddenCondition();
  @override
  Map<String, dynamic> toJson() => {'type': 'alwaysHidden'};
}

class VisibilityRules {
  final LogicalOperator operator;
  final List<Condition> conditions;

  const VisibilityRules({
    required this.operator,
    required this.conditions,
  });

  factory VisibilityRules.fromJson(Map<String, dynamic> json) {
    return VisibilityRules(
      operator: LogicalOperator.fromString(json['operator'] ?? 'and'),
      conditions: (json['conditions'] as List?)
              ?.map((c) => Condition.fromJson(c as Map<String, dynamic>))
              .toList() ??
          const [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'operator': operator.name,
      'conditions': conditions.map((c) => c.toJson()).toList(),
    };
  }
}
