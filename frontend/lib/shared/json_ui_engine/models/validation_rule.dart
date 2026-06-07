enum ValidationRuleType {
  min,
  max,
  minLength,
  maxLength,
  pattern,
  custom;

  static ValidationRuleType fromString(String val) {
    switch (val) {
      case 'min': return ValidationRuleType.min;
      case 'max': return ValidationRuleType.max;
      case 'minLength':
      case 'min_length': return ValidationRuleType.minLength;
      case 'maxLength':
      case 'max_length': return ValidationRuleType.maxLength;
      case 'pattern': return ValidationRuleType.pattern;
      default: return ValidationRuleType.custom;
    }
  }

  String toJson() => name;
}

class ValidationRule {
  final ValidationRuleType type;
  final dynamic value;
  final String message;

  const ValidationRule({
    required this.type,
    required this.value,
    required this.message,
  });

  factory ValidationRule.fromJson(Map<String, dynamic> json) {
    return ValidationRule(
      type: ValidationRuleType.fromString(json['type'] ?? ''),
      value: json['value'],
      message: json['message'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'type': type.toJson(),
      'value': value,
      'message': message,
    };
  }
}
