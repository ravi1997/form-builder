import '../models/visibility_rule.dart';
import '../models/form_context.dart';
import '../models/answer_value.dart';

class VisibilityEngine {
  static bool evaluate(VisibilityRules rules, FormContext ctx, Map<String, AnswerValue> answers) {
    if (rules.conditions.isEmpty) return true;
    final results = rules.conditions.map((c) => evaluateCondition(c, ctx, answers)).toList();
    if (rules.operator == LogicalOperator.and) {
      return results.every((r) => r == true);
    } else {
      return results.any((r) => r == true);
    }
  }

  static bool evaluateCondition(Condition c, FormContext ctx, Map<String, AnswerValue> answers) {
    if (c is AlwaysVisibleCondition) return true;
    if (c is AlwaysHiddenCondition) return false;
    if (c is RoleCondition) {
      return c.roles.contains(ctx.userRole);
    }
    if (c is GroupCondition) {
      return c.groupIds.any((g) => ctx.userGroupIds.contains(g));
    }
    if (c is AnswerCondition) {
      final ans = answers[c.fieldId];
      final val = ans?.value;
      switch (c.operator) {
        case AnswerOperator.isEmpty:
          return val == null || val == '' || (val is List && val.isEmpty);
        case AnswerOperator.isNotEmpty:
          return val != null && val != '' && (val is! List || val.isNotEmpty);
        case AnswerOperator.equals:
          if (val == null) return c.value == null;
          return val.toString() == c.value.toString();
        case AnswerOperator.notEquals:
          if (val == null) return c.value != null;
          return val.toString() != c.value.toString();
        case AnswerOperator.contains:
          if (val == null) return false;
          if (val is List) return val.map((x) => x.toString()).contains(c.value.toString());
          return val.toString().contains(c.value.toString());
        case AnswerOperator.greaterThan:
          if (val is num && c.value is num) return val > c.value;
          return false;
        case AnswerOperator.lessThan:
          if (val is num && c.value is num) return val < c.value;
          return false;
        case AnswerOperator.inList:
          if (c.value is List) return (c.value as List).map((x) => x.toString()).contains(val?.toString() ?? '');
          return false;
        case AnswerOperator.notInList:
          if (c.value is List) return !(c.value as List).map((x) => x.toString()).contains(val?.toString() ?? '');
          return false;
      }
    }
    return true;
  }
}
