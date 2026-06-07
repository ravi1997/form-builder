import 'package:flutter/material.dart';
import '../models/answer_value.dart';
import '../models/component_schema.dart';
import 'primitive_wrapper.dart';

class TextInputWidget extends StatefulWidget {
  final PrimitiveRef ref;
  final Map<String, dynamic> properties;
  final AnswerValue? currentValue;
  final void Function(AnswerValue) onChanged;
  final bool readOnly;
  final String? errorText;

  const TextInputWidget({
    super.key,
    required this.ref,
    required this.properties,
    required this.currentValue,
    required this.onChanged,
    required this.readOnly,
    this.errorText,
  });

  @override
  State<TextInputWidget> createState() => _TextInputWidgetState();
}

class _TextInputWidgetState extends State<TextInputWidget> {
  late TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.currentValue?.value?.toString() ?? '');
  }

  @override
  void didUpdateWidget(covariant TextInputWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.currentValue != oldWidget.currentValue) {
      final newVal = widget.currentValue?.value?.toString() ?? '';
      if (_controller.text != newVal) {
        _controller.text = newVal;
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  TextInputType _getKeyboardType() {
    final type = widget.properties['keyboard_type'] ?? 'text';
    switch (type) {
      case 'multiline': return TextInputType.multiline;
      case 'number': return const TextInputType.numberWithOptions(decimal: true);
      case 'phone': return TextInputType.phone;
      case 'email': return TextInputType.emailAddress;
      case 'url': return TextInputType.url;
      default: return TextInputType.text;
    }
  }

  @override
  Widget build(BuildContext context) {
    final label = widget.properties['label'] ?? '';
    final placeholder = widget.properties['placeholder'] ?? '';
    final isRequired = widget.properties['required'] ?? false;
    final isDisabled = widget.properties['disabled'] ?? false;
    final isReadOnly = widget.readOnly || (widget.properties['readonly'] ?? false);
    final hintText = widget.properties['hint_text'] ?? '';
    final maxLength = widget.properties['max_length'] as int?;
    final prefixText = widget.properties['prefix_text'] ?? '';
    final suffixText = widget.properties['suffix_text'] ?? '';

    return PrimitiveFieldWrapper(
      label: label,
      hintText: hintText,
      errorText: widget.errorText,
      required: isRequired,
      disabled: isDisabled,
      child: TextField(
        controller: _controller,
        maxLines: _getKeyboardType() == TextInputType.multiline ? 4 : 1,
        maxLength: maxLength,
        keyboardType: _getKeyboardType(),
        enabled: !isReadOnly && !isDisabled,
        decoration: InputDecoration(
          hintText: placeholder,
          prefixText: prefixText.isNotEmpty ? prefixText : null,
          suffixText: suffixText.isNotEmpty ? suffixText : null,
          border: const OutlineInputBorder(),
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        ),
        onChanged: (val) {
          widget.onChanged(AnswerValue(value: val, displayValue: val, answeredAt: DateTime.now()));
        },
      ),
    );
  }
}
