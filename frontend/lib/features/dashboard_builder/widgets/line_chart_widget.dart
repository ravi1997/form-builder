import 'package:flutter/material.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/tokens.dart';
import '../models/widget_model.dart';
import '../models/widget_data_model.dart';

class LineChartWidget extends StatelessWidget {
  final WidgetModel widget;
  final WidgetDataResult? dataResult;

  const LineChartWidget({super.key, required this.widget, this.dataResult});

  @override
  Widget build(BuildContext context) {
    final props = widget.properties;
    final title = props['title'] ?? 'Line Chart';
    final showTitle = props['show_title'] ?? true;
    final showLegend = props['show_legend'] ?? true;
    final colors = List<String>.from(
      props['color_palette'] ?? ['#1976D2', '#388E3C'],
    );
    final fillArea = props['fill_area'] ?? false;
    final fillOpacity = (props['fill_opacity'] as num?)?.toDouble() ?? 0.2;
    final showDots = props['show_dots'] ?? true;
    final dotRadius = (props['dot_radius'] as num?)?.toDouble() ?? 4.0;
    final lineWidth = (props['line_width'] as num?)?.toDouble() ?? 2.0;

    if (dataResult == null || dataResult!.status == 'loading') {
      return const Center(child: CircularProgressIndicator());
    }

    if (dataResult!.status == 'error') {
      return Center(
        child: Text(
          dataResult!.error ?? 'Error loading data',
          style: const TextStyle(color: AppColors.stateError),
        ),
      );
    }

    if (dataResult!.status == 'no_binding' || dataResult!.data == null) {
      return Center(
        child: Text(props['no_data_message'] ?? 'No data available'),
      );
    }

    final chartData = ChartData.fromJson(dataResult!.data);
    if (chartData.labels.isEmpty || chartData.series.isEmpty) {
      return Center(
        child: Text(props['no_data_message'] ?? 'No data available'),
      );
    }

    double maxVal = 0.01;
    for (final s in chartData.series) {
      for (final v in s.values) {
        if (v > maxVal) maxVal = v;
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (showTitle) ...[
          Text(
            title,
            style: Theme.of(
              context,
            ).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: AppSpacing.sm),
        ],
        Expanded(
          child: Row(
            children: [
              Column(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    maxVal.toStringAsFixed(0),
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: AppColors.textSubtle,
                    ),
                  ),
                  Text(
                    (maxVal / 2).toStringAsFixed(0),
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: AppColors.textSubtle,
                    ),
                  ),
                  Text(
                    '0',
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: AppColors.textSubtle,
                    ),
                  ),
                ],
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: CustomPaint(
                  painter: _LineChartPainter(
                    chartData: chartData,
                    maxVal: maxVal,
                    colors: colors.map(_parseColor).toList(),
                    fillArea: fillArea,
                    fillOpacity: fillOpacity,
                    showDots: showDots,
                    dotRadius: dotRadius,
                    lineWidth: lineWidth,
                  ),
                ),
              ),
            ],
          ),
        ),
        if (showLegend) ...[
          const SizedBox(height: AppSpacing.sm),
          _buildLegend(context, chartData, colors),
        ],
      ],
    );
  }

  Widget _buildLegend(
    BuildContext context,
    ChartData chartData,
    List<String> colors,
  ) {
    return Wrap(
      spacing: AppSpacing.lg,
      runSpacing: AppSpacing.xs,
      children: List.generate(chartData.series.length, (sIdx) {
        final series = chartData.series[sIdx];
        final color = _parseColor(colors[sIdx % colors.length]);
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(width: 12, height: 2, color: color),
            const SizedBox(width: AppSpacing.xs),
            Text(series.name, style: Theme.of(context).textTheme.labelSmall),
          ],
        );
      }),
    );
  }

  Color _parseColor(String hex) {
    try {
      final clean = hex.replaceAll('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return AppColors.brandPrimary;
    }
  }
}

class _LineChartPainter extends CustomPainter {
  final ChartData chartData;
  final double maxVal;
  final List<Color> colors;
  final bool fillArea;
  final double fillOpacity;
  final bool showDots;
  final double dotRadius;
  final double lineWidth;

  _LineChartPainter({
    required this.chartData,
    required this.maxVal,
    required this.colors,
    required this.fillArea,
    required this.fillOpacity,
    required this.showDots,
    required this.dotRadius,
    required this.lineWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final gridPaint = Paint()
      ..color = AppColors.textSubtle.withOpacity(0.2)
      ..strokeWidth = 0.5;

    // Draw horizontal grids
    canvas.drawLine(Offset(0, 0), Offset(size.width, 0), gridPaint);
    canvas.drawLine(
      Offset(0, size.height / 2),
      Offset(size.width, size.height / 2),
      gridPaint,
    );
    canvas.drawLine(
      Offset(0, size.height),
      Offset(size.width, size.height),
      gridPaint,
    );

    final stepX = size.width / (chartData.labels.length - 1).clamp(1, 999);

    for (int sIdx = 0; sIdx < chartData.series.length; sIdx++) {
      final series = chartData.series[sIdx];
      final color = colors[sIdx % colors.length];

      final linePaint = Paint()
        ..color = color
        ..strokeWidth = lineWidth
        ..style = PaintingStyle.stroke;

      final fillPaint = Paint()
        ..color = color.withOpacity(fillOpacity)
        ..style = PaintingStyle.fill;

      final path = Path();
      final fillPath = Path();

      for (int i = 0; i < series.values.length; i++) {
        final val = series.values[i];
        final x = i * stepX;
        final y = size.height - ((val / maxVal) * size.height);

        if (i == 0) {
          path.moveTo(x, y);
          fillPath.moveTo(x, size.height);
          fillPath.lineTo(x, y);
        } else {
          path.lineTo(x, y);
          fillPath.lineTo(x, y);
        }

        if (i == series.values.length - 1) {
          fillPath.lineTo(x, size.height);
          fillPath.close();
        }
      }

      if (fillArea && series.values.isNotEmpty) {
        canvas.drawPath(fillPath, fillPaint);
      }
      canvas.drawPath(path, linePaint);

      if (showDots) {
        final dotPaint = Paint()..color = color;
        for (int i = 0; i < series.values.length; i++) {
          final val = series.values[i];
          final x = i * stepX;
          final y = size.height - ((val / maxVal) * size.height);
          canvas.drawCircle(Offset(x, y), dotRadius, dotPaint);
        }
      }
    }
  }

  @override
  bool shouldRepaint(covariant _LineChartPainter oldDelegate) {
    return true;
  }
}
