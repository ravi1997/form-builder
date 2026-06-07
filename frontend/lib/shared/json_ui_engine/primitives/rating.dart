import 'package:flutter/material.dart';
import '../models/answer_value.dart';
import '../models/component_schema.dart';
import 'primitive_wrapper.dart';

class RatingWidget extends StatelessWidget {
  final PrimitiveRef ref;
  final Map<String, dynamic> properties;
  final AnswerValue? currentValue;
  final void Function(AnswerValue) onChanged;
  final bool readOnly;
  final String? errorText;

  const RatingWidget({
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
    final isRequired = properties['required'] ?? false;
    final isDisabled = properties['disabled'] ?? false;
    final isReadOnly = readOnly || (properties['readonly'] ?? false);
    final hintText = properties['hint_text'] ?? '';
    final maxStars = properties['max_stars'] as int? ?? 5;

    final currentRating = currentValue?.value is num ? (currentValue!.value as num) : 0.0;

    return PrimitiveFieldWrapper(
      label: label,
      hintText: hintText,
      errorText: errorText,
      required: isRequired,
      disabled: isDisabled,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(maxStars, (index) {
          final starValue = index + 1;
          final isFilled = starValue <= currentRating;
          return IconButton(
            icon: Icon(
              isFilled ? Icons.star : Icons.star_border,
              color: isFilled ? Colors.amber : Colors.grey,
            ),
            iconSize: 32,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
            onPressed: (isReadOnly || isDisabled)
                ? null
                : () {
                    onChanged(
                      AnswerValue(
                        value: starValue,
                        displayValue: "$starValue / $maxStars",
                        answeredAt: DateTime.now(),
                      ),
                    );
                  },
          );
        }),
      ),
    );
  }
}
