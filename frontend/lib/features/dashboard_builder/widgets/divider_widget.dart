import 'package:flutter/material.dart';
import '../../../core/theme/app_colors.dart';
import '../models/widget_model.dart';

class DividerWidget extends StatelessWidget {
  final WidgetModel widget;

  const DividerWidget({super.key, required this.widget});

  @override
  Widget build(BuildContext context) {
    final props = widget.properties;
    final style = props['style'] ?? 'divider';
    final direction = props['direction'] ?? 'horizontal';
    final colorStr = props['line_color'] ?? '#E0E0E0';
    final thickness = (props['line_thickness'] as num?)?.toDouble() ?? 1.0;

    final color = _parseColor(colorStr);

    if (style == 'spacer') {
      return const SizedBox.shrink();
    }

    if (direction == 'vertical') {
      return Center(
        child: Container(width: thickness, color: color),
      );
    }

    return Center(
      child: Container(height: thickness, color: color),
    );
  }

  Color _parseColor(String hex) {
    try {
      final clean = hex.replaceAll('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return AppColors.borderSubtle;
    }
  }
}
