import 'package:flutter/material.dart';
import '../models/answer_value.dart';
import '../models/component_schema.dart';
import '../primitives/text_input.dart';
import '../primitives/dropdown.dart';
import '../primitives/date_range_picker.dart';
import '../primitives/multi_select.dart';
import '../primitives/rating.dart';
import '../primitives/checkbox.dart';
import '../primitives/toggle.dart';

class PrimitiveRenderer {
  static Widget build({
    required PrimitiveRef ref,
    required Map<String, dynamic> properties,
    required AnswerValue? currentValue,
    required void Function(AnswerValue) onChanged,
    required bool readOnly,
    String? errorText,
  }) {
    switch (ref.primitive) {
      case 'text_input':
        return TextInputWidget(
          ref: ref,
          properties: properties,
          currentValue: currentValue,
          onChanged: onChanged,
          readOnly: readOnly,
          errorText: errorText,
        );
      case 'dropdown':
        return DropdownWidget(
          ref: ref,
          properties: properties,
          currentValue: currentValue,
          onChanged: onChanged,
          readOnly: readOnly,
          errorText: errorText,
        );
      case 'date_range_picker':
        return DateRangePickerWidget(
          ref: ref,
          properties: properties,
          currentValue: currentValue,
          onChanged: onChanged,
          readOnly: readOnly,
          errorText: errorText,
        );
      case 'multi_select':
        return MultiSelectWidget(
          ref: ref,
          properties: properties,
          currentValue: currentValue,
          onChanged: onChanged,
          readOnly: readOnly,
          errorText: errorText,
        );
      case 'rating':
        return RatingWidget(
          ref: ref,
          properties: properties,
          currentValue: currentValue,
          onChanged: onChanged,
          readOnly: readOnly,
          errorText: errorText,
        );
      case 'checkbox':
        return CheckboxWidget(
          ref: ref,
          properties: properties,
          currentValue: currentValue,
          onChanged: onChanged,
          readOnly: readOnly,
          errorText: errorText,
        );
      case 'toggle':
        return ToggleWidget(
          ref: ref,
          properties: properties,
          currentValue: currentValue,
          onChanged: onChanged,
          readOnly: readOnly,
          errorText: errorText,
        );
      default:
        return Container(
          padding: const EdgeInsets.all(8.0),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.red),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text('Unknown primitive: ${ref.primitive}', style: const TextStyle(color: Colors.red)),
        );
    }
  }
}
