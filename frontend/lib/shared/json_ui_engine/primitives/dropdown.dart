import 'package:flutter/material.dart';
import '../models/answer_value.dart';
import '../models/component_schema.dart';
import 'primitive_wrapper.dart';

class DropdownWidget extends StatelessWidget {
  final PrimitiveRef ref;
  final Map<String, dynamic> properties;
  final AnswerValue? currentValue;
  final void Function(AnswerValue) onChanged;
  final bool readOnly;
  final String? errorText;

  const DropdownWidget({
    super.key,
    required this.ref,
    required this.properties,
    required this.currentValue,
    required this.onChanged,
    required this.readOnly,
    this.errorText,
  });

  @override
  Widget build(BuildContext context) {
    final label = properties['label'] ?? '';
    final placeholder = properties['empty_option_label'] ?? properties['placeholder'] ?? 'Select...';
    final isRequired = properties['required'] ?? false;
    final isDisabled = properties['disabled'] ?? false;
    final isReadOnly = readOnly || (properties['readonly'] ?? false);
    final hintText = properties['hint_text'] ?? '';

    // Options parsing
    final List<Map<String, String>> options = [];
    final rawOptions = properties['options'];
    if (rawOptions is List) {
      for (final opt in rawOptions) {
        if (opt is Map) {
          options.add({
            'value': opt['value']?.toString() ?? '',
            'label': opt['label']?.toString() ?? opt['value']?.toString() ?? '',
          });
        }
      }
    }

    final selectedValue = currentValue?.value?.toString();
    final hasValidSelection = options.any((opt) => opt['value'] == selectedValue);

    return PrimitiveFieldWrapper(
      label: label,
      hintText: hintText,
      errorText: errorText,
      required: isRequired,
      disabled: isDisabled,
      child: DropdownButtonFormField<String>(
        value: hasValidSelection ? selectedValue : null,
        hint: Text(placeholder),
        decoration: const InputDecoration(
          border: OutlineInputBorder(),
          contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        ),
        items: [
          ...options.map((opt) {
            return DropdownMenuItem<String>(
              value: opt['value'],
              child: Text(opt['label'] ?? ''),
            );
          }),
        ],
        onChanged: (isReadOnly || isDisabled)
            ? null
            : (val) {
                if (val != null) {
                  final labelSelected = options.firstWhere((o) => o['value'] == val)['label'] ?? val;
                  onChanged(AnswerValue(value: val, displayValue: labelSelected, answeredAt: DateTime.now()));
                }
              },
      ),
    );
  }
}
