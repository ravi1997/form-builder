import 'package:flutter/material.dart';
import '../models/answer_value.dart';
import '../models/component_schema.dart';
import 'primitive_wrapper.dart';

class DateRangePickerWidget extends StatelessWidget {
  final PrimitiveRef ref;
  final Map<String, dynamic> properties;
  final AnswerValue? currentValue;
  final void Function(AnswerValue) onChanged;
  final bool readOnly;
  final String? errorText;

  const DateRangePickerWidget({
    super.key,
    required this.ref,
    required this.properties,
    required this.currentValue,
    required this.onChanged,
    required this.readOnly,
    this.errorText,
  });

  String _formatDate(DateTime dt) {
    // Simple fallback format: YYYY-MM-DD
    return "${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')}";
  }

  @override
  Widget build(BuildContext context) {
    final label = properties['label'] ?? '';
    final placeholder = properties['placeholder'] ?? 'Select date range';
    final isRequired = properties['required'] ?? false;
    final isDisabled = properties['disabled'] ?? false;
    final isReadOnly = readOnly || (properties['readonly'] ?? false);
    final hintText = properties['hint_text'] ?? '';

    DateTime? startDate;
    DateTime? endDate;

    final currMap = currentValue?.value;
    if (currMap is Map) {
      if (currMap['start'] != null) {
        startDate = DateTime.tryParse(currMap['start'].toString());
      }
      if (currMap['end'] != null) {
        endDate = DateTime.tryParse(currMap['end'].toString());
      }
    }

    final displayString = currentValue?.displayValue ?? '';

    return PrimitiveFieldWrapper(
      label: label,
      hintText: hintText,
      errorText: errorText,
      required: isRequired,
      disabled: isDisabled,
      child: InkWell(
        onTap: (isReadOnly || isDisabled)
            ? null
            : () async {
                final initialRange = (startDate != null && endDate != null)
                    ? DateTimeRange(start: startDate, end: endDate)
                    : null;

                final pickedRange = await showDateRangePicker(
                  context: context,
                  firstDate: DateTime.now().subtract(const Duration(days: 365 * 10)),
                  lastDate: DateTime.now().add(const Duration(days: 365 * 10)),
                  initialDateRange: initialRange,
                );

                if (pickedRange != null) {
                  final startStr = _formatDate(pickedRange.start);
                  final endStr = _formatDate(pickedRange.end);
                  final disp = "$startStr – $endStr";

                  onChanged(
                    AnswerValue(
                      value: {'start': startStr, 'end': endStr},
                      displayValue: disp,
                      answeredAt: DateTime.now(),
                    ),
                  );
                }
              },
        child: InputDecorator(
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            suffixIcon: Icon(Icons.date_range),
            contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          ),
          child: Text(
            displayString.isNotEmpty ? displayString : placeholder,
            style: TextStyle(
              color: displayString.isNotEmpty ? Colors.black : Colors.grey[600],
            ),
          ),
        ),
      ),
    );
  }
}
