import '../models/validation_rule.dart';
import '../models/answer_value.dart';

class ValidationEngine {
  static List<String> validate(AnswerValue answer, List<ValidationRule> rules, bool required) {
    final errors = <String>[];
    if (required && _isEmpty(answer)) {
      errors.add('This field is required');
      return errors;
    }
    if (_isEmpty(answer)) return errors;
    for (final rule in rules) {
      switch (rule.type) {
        case ValidationRuleType.min:
          final limit = _toNumFromVal(rule.value);
          if (_toNum(answer) < limit) errors.add(rule.message);
          break;
        case ValidationRuleType.max:
          final limit = _toNumFromVal(rule.value);
          if (_toNum(answer) > limit) errors.add(rule.message);
          break;
        case ValidationRuleType.minLength:
          final limit = _toIntFromVal(rule.value);
          if (_toString(answer).length < limit) errors.add(rule.message);
          break;
        case ValidationRuleType.maxLength:
          final limit = _toIntFromVal(rule.value);
          if (_toString(answer).length > limit) errors.add(rule.message);
          break;
        case ValidationRuleType.pattern:
          if (!RegExp(rule.value as String).hasMatch(_toString(answer))) errors.add(rule.message);
          break;
        case ValidationRuleType.custom:
          break;
      }
    }
    return errors;
  }

  static bool _isEmpty(AnswerValue a) {
    final v = a.value;
    if (v == null) return true;
    if (v is String) return v.trim().isEmpty;
    if (v is List) return v.isEmpty;
    if (v is Map) return v.isEmpty;
    return false;
  }

  static num _toNum(AnswerValue a) {
    if (a.value is num) return a.value as num;
    return num.tryParse(a.value.toString()) ?? 0;
  }

  static num _toNumFromVal(dynamic v) {
    if (v is num) return v;
    return num.tryParse(v.toString()) ?? 0;
  }

  static int _toIntFromVal(dynamic v) {
    if (v is int) return v;
    return int.tryParse(v.toString()) ?? 0;
  }

  static String _toString(AnswerValue a) {
    return a.value?.toString() ?? '';
  }
}
