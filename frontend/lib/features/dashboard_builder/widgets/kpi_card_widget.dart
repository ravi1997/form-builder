import 'package:flutter/material.dart';
import '../models/widget_model.dart';
import '../models/widget_data_model.dart';

class KpiCardWidget extends StatelessWidget {
  final WidgetModel widget;
  final WidgetDataResult? dataResult;

  const KpiCardWidget({
    super.key,
    required this.widget,
    this.dataResult,
  });

  @override
  Widget build(BuildContext context) {
    final props = widget.properties;
    final title = props['title'] ?? 'KPI Card';
    final showTitle = props['show_title'] ?? true;
    final titleFontSize = (props['title_font_size'] as num?)?.toDouble() ?? 14.0;
    final titleColorStr = props['title_color'] ?? '#757575';
    final valFontSize = (props['value_font_size'] as num?)?.toDouble() ?? 36.0;
    final valColorStr = props['value_color'] ?? '#212121';
    final iconName = props['icon'] ?? '';
    final iconColorStr = props['icon_color'] ?? '#1976D2';

    final valueColor = _parseColor(valColorStr);
    final titleColor = _parseColor(titleColorStr);
    final iconColor = _parseColor(iconColorStr);

    if (dataResult == null || dataResult!.status == 'loading') {
      return const Center(child: CircularProgressIndicator());
    }

    if (dataResult!.status == 'error') {
      return Center(
        child: Text(
          dataResult!.error ?? 'Error loading data',
          style: const TextStyle(color: Colors.red),
        ),
      );
    }

    if (dataResult!.status == 'no_binding' || dataResult!.data == null) {
      return Center(
        child: Text(props['no_data_message'] ?? 'No data available'),
      );
    }

    final kpiData = KpiData.fromJson(dataResult!.data);
    final double value = kpiData.value;
    final String formattedValue = _formatValue(value, props);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (showTitle)
          Row(
            children: [
              if (iconName.isNotEmpty) ...[
                Icon(_getIconData(iconName), color: iconColor, size: titleFontSize + 2),
                const SizedBox(width: 8),
              ],
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    fontSize: titleFontSize,
                    color: titleColor,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
            ],
          ),
        const SizedBox(height: 8),
        Text(
          formattedValue,
          style: TextStyle(
            fontSize: valFontSize,
            color: valueColor,
            fontWeight: FontWeight.bold,
          ),
        ),
        if (props['show_comparison'] == true && kpiData.previousValue != null) ...[
          const SizedBox(height: 4),
          _buildComparisonRow(value, kpiData.previousValue!, props),
        ]
      ],
    );
  }

  Widget _buildComparisonRow(double value, double previousValue, Map<String, dynamic> props) {
    final delta = value - previousValue;
    final deltaPct = previousValue == 0 ? 0.0 : (delta / previousValue) * 100;
    final positiveIsGood = props['positive_is_good'] ?? true;
    final isPositive = delta >= 0;

    final Color color = (isPositive == positiveIsGood) ? Colors.green : Colors.red;
    final icon = isPositive ? Icons.arrow_upward : Icons.arrow_downward;
    final label = props['comparison_label'] ?? 'vs last period';

    return Row(
      children: [
        Icon(icon, color: color, size: 14),
        const SizedBox(width: 4),
        Text(
          '${deltaPct.abs().toStringAsFixed(1)}%',
          style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 12),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(color: Colors.grey, fontSize: 12),
        ),
      ],
    );
  }

  String _formatValue(double value, Map<String, dynamic> props) {
    final format = props['value_format'] ?? 'number';
    final decimals = props['decimal_places'] ?? 0;
    final prefix = props['prefix'] ?? '';
    final suffix = props['suffix'] ?? '';

    String numStr = value.toStringAsFixed(decimals);
    if (format == 'compact') {
      if (value >= 1e9) {
        numStr = '${(value / 1e9).toStringAsFixed(1)}B';
      } else if (value >= 1e6) {
        numStr = '${(value / 1e6).toStringAsFixed(1)}M';
      } else if (value >= 1e3) {
        numStr = '${(value / 1e3).toStringAsFixed(1)}K';
      }
    } else if (format == 'currency') {
      numStr = '\$$numStr'; // simplified locale
    } else if (format == 'percentage') {
      numStr = '$numStr%';
    }

    return '$prefix$numStr$suffix';
  }

  IconData _getIconData(String name) {
    switch (name) {
      case 'trending_up': return Icons.trending_up;
      case 'people': return Icons.people;
      case 'bar_chart': return Icons.bar_chart;
      case 'attach_money': return Icons.attach_money;
      case 'show_chart': return Icons.show_chart;
      case 'pie_chart': return Icons.pie_chart;
      default: return Icons.info_outline;
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
