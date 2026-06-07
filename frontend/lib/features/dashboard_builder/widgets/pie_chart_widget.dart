import 'dart:math';
import 'package:flutter/material.dart';
import '../models/widget_model.dart';
import '../models/widget_data_model.dart';

class PieChartWidget extends StatelessWidget {
  final WidgetModel widget;
  final WidgetDataResult? dataResult;

  const PieChartWidget({
    super.key,
    required this.widget,
    this.dataResult,
  });

  @override
  Widget build(BuildContext context) {
    final props = widget.properties;
    final title = props['title'] ?? 'Pie Chart';
    final showTitle = props['show_title'] ?? true;
    final showLegend = props['show_legend'] ?? true;
    final legendPosition = props['legend_position'] ?? 'right';
    final donut = props['donut'] ?? false;
    final donutHoleRatio = (props['donut_hole_ratio'] as num?)?.toDouble() ?? 0.5;
    final colors = List<String>.from(props['color_palette'] ?? ['#1976D2', '#E91E63', '#388E3C', '#F57C00']);

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

    final pieData = PieChartData.fromJson(dataResult!.data);
    if (pieData.segments.isEmpty) {
      return Center(child: Text(props['no_data_message'] ?? 'No data available'));
    }

    final double totalValue = pieData.segments.fold(0, (sum, item) => sum + item.value);

    final chartContent = CustomPaint(
      painter: _PieChartPainter(
        segments: pieData.segments,
        totalValue: totalValue,
        colors: colors.map(_parseColor).toList(),
        donut: donut,
        donutHoleRatio: donutHoleRatio,
      ),
    );

    final legendContent = _buildLegend(pieData, colors, totalValue);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (showTitle) ...[
          Text(
            title,
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
          const SizedBox(height: 8),
        ],
        Expanded(
          child: legendPosition == 'right'
              ? Row(
                  children: [
                    Expanded(child: Center(child: SizedBox(width: 200, height: 200, child: chartContent))),
                    if (showLegend) SizedBox(width: 120, child: SingleChildScrollView(child: legendContent)),
                  ],
                )
              : Column(
                  children: [
                    Expanded(child: Center(child: SizedBox(width: 200, height: 200, child: chartContent))),
                    if (showLegend) ...[
                      const SizedBox(height: 8),
                      SingleChildScrollView(scrollDirection: Axis.horizontal, child: legendContent),
                    ],
                  ],
                ),
        ),
      ],
    );
  }

  Widget _buildLegend(PieChartData pieData, List<String> colors, double totalValue) {
    final widgets = List.generate(pieData.segments.length, (sIdx) {
      final segment = pieData.segments[sIdx];
      final color = _parseColor(colors[sIdx % colors.length]);
      final pct = totalValue == 0 ? 0.0 : (segment.value / totalValue) * 100;
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 2, horizontal: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(width: 12, height: 12, color: color),
            const SizedBox(width: 4),
            Expanded(
              child: Text(
                '${segment.label} (${pct.toStringAsFixed(1)}%)',
                style: const TextStyle(fontSize: 11),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      );
    });

    return Wrap(
      direction: Axis.vertical,
      spacing: 4,
      children: widgets,
    );
  }

  Color _parseColor(String hex) {
    try {
      final clean = hex.replaceAll('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return Colors.blue;
    }
  }
}

class _PieChartPainter extends CustomPainter {
  final List<PieSegment> segments;
  final double totalValue;
  final List<Color> colors;
  final bool donut;
  final double donutHoleRatio;

  _PieChartPainter({
    required this.segments,
    required this.totalValue,
    required this.colors,
    required this.donut,
    required this.donutHoleRatio,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (totalValue <= 0) return;

    final center = Offset(size.width / 2, size.height / 2);
    final radius = min(size.width, size.height) / 2;
    final rect = Rect.fromCircle(center: center, radius: radius);

    double startAngle = -pi / 2;

    for (int i = 0; i < segments.length; i++) {
      final segment = segments[i];
      final color = colors[i % colors.length];
      final sweepAngle = (segment.value / totalValue) * 2 * pi;

      if (donut) {
        final strokeWidth = radius * (1 - donutHoleRatio);
        final donutRect = Rect.fromCircle(center: center, radius: radius - strokeWidth / 2);
        final paint = Paint()
          ..color = color
          ..strokeWidth = strokeWidth
          ..style = PaintingStyle.stroke;

        canvas.drawArc(donutRect, startAngle, sweepAngle, false, paint);
      } else {
        final paint = Paint()
          ..color = color
          ..style = PaintingStyle.fill;

        canvas.drawArc(rect, startAngle, sweepAngle, true, paint);
      }

      startAngle += sweepAngle;
    }
  }

  @override
  bool shouldRepaint(covariant _PieChartPainter oldDelegate) {
    return true;
  }
}
