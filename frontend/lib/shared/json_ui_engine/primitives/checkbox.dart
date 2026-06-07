import 'package:flutter/material.dart';
import '../models/answer_value.dart';
import '../models/component_schema.dart';
import 'primitive_wrapper.dart';

class CheckboxWidget extends StatelessWidget {
  final PrimitiveRef ref;
  final Map<String, dynamic> properties;
  final AnswerValue? currentValue;
  final void Function(AnswerValue) onChanged;
  final bool readOnly;
  final String? errorText;

  const CheckboxWidget({
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
    final checkLabel = properties['check_label'] ?? '';
    final isRequired = properties['required'] ?? false;
    final isDisabled = properties['disabled'] ?? false;
    final isReadOnly = readOnly || (properties['readonly'] ?? false);
    final hintText = properties['hint_text'] ?? '';

    final isChecked = currentValue?.value == true;

    return PrimitiveFieldWrapper(
      label: label,
      hintText: hintText,
      errorText: errorText,
      required: isRequired,
      disabled: isDisabled,
      child: CheckboxListTile(
        title: Text(checkLabel),
        value: isChecked,
        contentPadding: EdgeInsets.zero,
        controlAffinity: ListTileControlAffinity.leading,
        onChanged: (isReadOnly || isDisabled)
            ? null
            : (val) {
                if (val != null) {
                  onChanged(
                    AnswerValue(
                      value: val,
                      displayValue: val ? "Yes" : "No",
                      answeredAt: DateTime.now(),
                    ),
                  );
                }
              },
      ),
    );
  }
}
