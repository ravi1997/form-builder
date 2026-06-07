import 'package:flutter/material.dart';
import 'models/answer_value.dart';
import 'models/component_schema.dart';
import 'models/form_context.dart';
import 'models/validation_rule.dart';
import 'visibility/visibility_engine.dart';
import 'validation/validation_engine.dart';
import 'renderers/primitive_renderer.dart';

class JsonUiEngine {
  Widget render({
    required ComponentSchema schema,
    required Map<String, AnswerValue> currentValues,
    required void Function(String propertyKey, AnswerValue value) onValueChanged,
    required void Function(String propertyKey, bool isValid) onValidationChanged,
    required FormContext formContext,
    bool readOnly = false,
    Map<String, String>? validationErrors, // Pass current validation errors if any
  }) {
    final widgets = <Widget>[];

    for (final ref in schema.composition) {
      // 1. Evaluate visibility rules
      final isVisible = ref.visibility == null ||
          VisibilityEngine.evaluate(ref.visibility!, formContext, currentValues);

      if (!isVisible) continue;

      // 2. Resolve properties (merge schema defaults/values with static properties)
      final properties = <String, dynamic>{};
      
      // Default from component schema properties definition
      for (final pDef in schema.properties) {
        if (pDef.key == ref.propertyKey || pDef.key == ref.labelFromProperty) {
          properties[pDef.key] = pDef.defaultValue;
        }
      }

      // Question static overrides
      properties.addAll(ref.staticProperties);

      // Label resolution from properties
      if (ref.labelFromProperty != null && properties.containsKey(ref.labelFromProperty)) {
        properties['label'] = properties[ref.labelFromProperty]?.toString() ?? '';
      }

      // Check current value
      final val = currentValues[ref.propertyKey];

      // Parse validation rules from properties if any
      final List<ValidationRule> rules = [];
      if (properties['validation_rules'] is List) {
        for (final r in properties['validation_rules']) {
          if (r is Map<String, dynamic>) {
            rules.add(ValidationRule.fromJson(r));
          }
        }
      }

      final isRequired = properties['required'] ?? false;
      final errorText = validationErrors?[ref.propertyKey];

      widgets.add(
        PrimitiveRenderer.build(
          ref: ref,
          properties: properties,
          currentValue: val,
          readOnly: readOnly,
          errorText: errorText,
          onChanged: (newVal) {
            // Update value
            onValueChanged(ref.propertyKey, newVal);
            
            // Re-validate
            final errors = ValidationEngine.validate(newVal, rules, isRequired);
            onValidationChanged(ref.propertyKey, errors.isEmpty);
          },
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: widgets,
    );
  }
}
