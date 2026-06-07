import 'package:flutter/material.dart';

class PrimitiveFieldWrapper extends StatelessWidget {
  final String label;
  final String hintText;
  final String? errorText;
  final bool required;
  final bool disabled;
  final Widget child;

  const PrimitiveFieldWrapper({
    super.key,
    required this.label,
    required this.hintText,
    this.errorText,
    required this.required,
    required this.disabled,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Opacity(
        opacity: disabled ? 0.6 : 1.0,
        child: IgnorePointer(
          ignoring: disabled,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              if (label.isNotEmpty) ...[
                Row(
                  children: [
                    Text(
                      label,
                      style: theme.textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (required) ...[
                      const SizedBox(width: 4),
                      Text(
                        '*',
                        style: TextStyle(
                          color: theme.colorScheme.error,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 6),
              ],
              child,
              if (errorText != null && errorText!.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  errorText!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.error,
                  ),
                ),
              ] else if (hintText.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  hintText,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.hintColor,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
