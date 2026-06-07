import 'package:flutter/material.dart';
import '../models/answer_value.dart';
import '../models/component_schema.dart';
import 'primitive_wrapper.dart';

class ToggleWidget extends StatelessWidget {
  final PrimitiveRef ref;
  final Map<String, dynamic> properties;
  final AnswerValue? currentValue;
  final void Function(AnswerValue) onChanged;
  final bool readOnly;
  final String? errorText;

  const ToggleWidget({
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
    final onLabel = properties['on_label'] ?? 'On';
    final offLabel = properties['off_label'] ?? 'Off';
    final isRequired = properties['required'] ?? false;
    final isDisabled = properties['disabled'] ?? false;
    final isReadOnly = readOnly || (properties['readonly'] ?? false);
    final hintText = properties['hint_text'] ?? '';

    final isToggled = currentValue?.value == true;

    return PrimitiveFieldWrapper(
      label: label,
      hintText: hintText,
      errorText: errorText,
      required: isRequired,
      disabled: isDisabled,
      child: SwitchListTile(
        title: Text(isToggled ? onLabel : offLabel),
        value: isToggled,
        contentPadding: EdgeInsets.zero,
        onChanged: (isReadOnly || isDisabled)
            ? null
            : (val) {
                onChanged(
                  AnswerValue(
                    value: val,
                    displayValue: val ? onLabel : offLabel,
                    answeredAt: DateTime.now(),
                  ),
                );
              },
      ),
    );
  }
}
