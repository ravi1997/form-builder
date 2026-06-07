import 'package:flutter/material.dart';
import '../models/widget_model.dart';
import '../models/widget_data_model.dart';

class TextLabelWidget extends StatelessWidget {
  final WidgetModel widget;
  final WidgetDataResult? dataResult;

  const TextLabelWidget({
    super.key,
    required this.widget,
    this.dataResult,
  });

  @override
  Widget build(BuildContext context) {
    final props = widget.properties;
    String rawText = props['text'] ?? 'Label';
    final fontSize = (props['font_size'] as num?)?.toDouble() ?? 16.0;
    final colorStr = props['text_color'] ?? '#212121';
    final alignStr = props['text_align'] ?? 'left';
    final weightStr = props['font_weight'] ?? 'regular';

    final color = _parseColor(colorStr);
    final align = _getAlign(alignStr);
    final weight = _getWeight(weightStr);

    // If bound to dynamic data, resolve templates like {{value}}
    if (widget.dataBinding != null && dataResult != null && dataResult!.status == 'ok' && dataResult!.data != null) {
      final kpi = KpiData.fromJson(dataResult!.data);
      rawText = rawText.replaceAll('{{value}}', kpi.value.toStringAsFixed(0));
    }

    return Text(
      rawText,
      textAlign: align,
      style: TextStyle(
        fontSize: fontSize,
        color: color,
        fontWeight: weight,
      ),
    );
  }

  TextAlign _getAlign(String val) {
    switch (val) {
      case 'center': return TextAlign.center;
      case 'right': return TextAlign.right;
      case 'justify': return TextAlign.justify;
      default: return TextAlign.left;
    }
  }

  FontWeight _getWeight(String val) {
    switch (val) {
      case 'thin': return FontWeight.w100;
      case 'light': return FontWeight.w300;
      case 'medium': return FontWeight.w500;
      case 'semibold': return FontWeight.w600;
      case 'bold': return FontWeight.bold;
      case 'heavy': return FontWeight.w900;
      default: return FontWeight.normal;
    }
  }

  Color _parseColor(String hex) {
    try {
      final clean = hex.replaceAll('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return Colors.black;
    }
  }
}
