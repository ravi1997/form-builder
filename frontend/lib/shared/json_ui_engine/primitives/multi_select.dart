import 'package:flutter/material.dart';
import '../models/answer_value.dart';
import '../models/component_schema.dart';
import 'primitive_wrapper.dart';

class MultiSelectWidget extends StatelessWidget {
  final PrimitiveRef ref;
  final Map<String, dynamic> properties;
  final AnswerValue? currentValue;
  final void Function(AnswerValue) onChanged;
  final bool readOnly;
  final String? errorText;

  const MultiSelectWidget({
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
    final placeholder = properties['placeholder'] ?? 'Select multiple options';
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

    final selectedValues = <String>[];
    final currVal = currentValue?.value;
    if (currVal is List) {
      selectedValues.addAll(currVal.map((e) => e.toString()));
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
                final result = await showDialog<List<String>>(
                  context: context,
                  builder: (context) {
                    final tempSelected = List<String>.from(selectedValues);
                    return StatefulBuilder(
                      builder: (context, setState) {
                        return AlertDialog(
                          title: Text(label.isNotEmpty ? label : 'Select Options'),
                          content: SingleChildScrollView(
                            child: ListBody(
                              children: options.map((opt) {
                                final isSelected = tempSelected.contains(opt['value']);
                                return CheckboxListTile(
                                  title: Text(opt['label'] ?? ''),
                                  value: isSelected,
                                  onChanged: (checked) {
                                    setState(() {
                                      if (checked == true) {
                                        tempSelected.add(opt['value']!);
                                      } else {
                                        tempSelected.remove(opt['value']);
                                      }
                                    });
                                  },
                                );
                              }).toList(),
                            ),
                          ),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.pop(context),
                              child: const Text('Cancel'),
                            ),
                            TextButton(
                              onPressed: () => Navigator.pop(context, tempSelected),
                              child: const Text('OK'),
                            ),
                          ],
                        );
                      },
                    );
                  },
                );

                if (result != null) {
                  final labels = result.map((v) {
                    return options.firstWhere((o) => o['value'] == v)['label'] ?? v;
                  }).join(', ');
                  onChanged(
                    AnswerValue(
                      value: result,
                      displayValue: labels,
                      answeredAt: DateTime.now(),
                    ),
                  );
                }
              },
        child: InputDecorator(
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            suffixIcon: Icon(Icons.arrow_drop_down),
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
