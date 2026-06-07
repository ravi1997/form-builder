import 'package:flutter/material.dart';
import '../models/widget_model.dart';
import '../models/widget_data_model.dart';

class BarChartWidget extends StatelessWidget {
  final WidgetModel widget;
  final WidgetDataResult? dataResult;

  const BarChartWidget({
    super.key,
    required this.widget,
    this.dataResult,
  });

  @override
  Widget build(BuildContext context) {
    final props = widget.properties;
    final title = props['title'] ?? 'Bar Chart';
    final showTitle = props['show_title'] ?? true;
    final showLegend = props['show_legend'] ?? true;
    final orientation = props['orientation'] ?? 'vertical';
    final stacked = props['stacked'] ?? false;
    final colors = List<String>.from(props['color_palette'] ?? ['#1976D2', '#388E3C', '#F57C00', '#7B1FA2']);

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

    final chartData = ChartData.fromJson(dataResult!.data);
    if (chartData.labels.isEmpty || chartData.series.isEmpty) {
      return Center(child: Text(props['no_data_message'] ?? 'No data available'));
    }

    // Determine max value for scaling
    double maxVal = 0.01;
    if (stacked) {
      for (int i = 0; i < chartData.labels.length; i++) {
        double sum = 0;
        for (final s in chartData.series) {
          if (i < s.values.length) {
            sum += s.values[i];
          }
        }
        if (sum > maxVal) maxVal = sum;
      }
    } else {
      for (final s in chartData.series) {
        for (final v in s.values) {
          if (v > maxVal) maxVal = v;
        }
      }
    }

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
          child: orientation == 'horizontal'
              ? _buildHorizontalChart(chartData, maxVal, stacked, colors)
              : _buildVerticalChart(chartData, maxVal, stacked, colors),
        ),
        if (showLegend) ...[
          const SizedBox(height: 8),
          _buildLegend(chartData, colors),
        ],
      ],
    );
  }

  Widget _buildVerticalChart(ChartData chartData, double maxVal, bool stacked, List<String> colors) {
    return Row(
      children: [
        // Y Axis values
        Column(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(maxVal.toStringAsFixed(0), style: const TextStyle(fontSize: 10, color: Colors.grey)),
            Text((maxVal / 2).toStringAsFixed(0), style: const TextStyle(fontSize: 10, color: Colors.grey)),
            const Text('0', style: TextStyle(fontSize: 10, color: Colors.grey)),
          ],
        ),
        const SizedBox(width: 8),
        // Chart Area
        Expanded(
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: List.generate(chartData.labels.length, (idx) {
              final label = chartData.labels[idx];
              return Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    Expanded(
                      child: Container(
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        child: stacked
                            ? _buildVerticalStackedBars(chartData, idx, maxVal, colors)
                            : _buildVerticalGroupedBars(chartData, idx, maxVal, colors),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      label,
                      style: const TextStyle(fontSize: 10),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              );
            }),
          ),
        ),
      ],
    );
  }

  Widget _buildVerticalStackedBars(ChartData chartData, int labelIdx, double maxVal, List<String> colors) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final totalHeight = constraints.maxHeight;
        return Column(
          mainAxisAlignment: MainAxisAlignment.end,
          children: List.generate(chartData.series.length, (sIdx) {
            final series = chartData.series[sIdx];
            final val = labelIdx < series.values.length ? series.values[labelIdx] : 0.0;
            final h = (val / maxVal) * totalHeight;
            if (h <= 0) return const SizedBox.shrink();

            return Container(
              height: h,
              width: constraints.maxWidth * 0.6,
              color: _parseColor(colors[sIdx % colors.length]),
            );
          }),
        );
      },
    );
  }

  Widget _buildVerticalGroupedBars(ChartData chartData, int labelIdx, double maxVal, List<String> colors) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final totalHeight = constraints.maxHeight;
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: List.generate(chartData.series.length, (sIdx) {
            final series = chartData.series[sIdx];
            final val = labelIdx < series.values.length ? series.values[labelIdx] : 0.0;
            final h = (val / maxVal) * totalHeight;

            return Container(
              height: h > 0 ? h : 2, // minimum height so we see empty categories
              width: (constraints.maxWidth / chartData.series.length) * 0.7,
              margin: const EdgeInsets.symmetric(horizontal: 1),
              color: _parseColor(colors[sIdx % colors.length]),
            );
          }),
        );
      },
    );
  }

  Widget _buildHorizontalChart(ChartData chartData, double maxVal, bool stacked, List<String> colors) {
    return Column(
      children: List.generate(chartData.labels.length, (idx) {
        final label = chartData.labels[idx];
        return Expanded(
          child: Row(
            children: [
              SizedBox(
                width: 60,
                child: Text(
                  label,
                  style: const TextStyle(fontSize: 10),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Container(
                  margin: const EdgeInsets.symmetric(vertical: 4),
                  child: stacked
                      ? _buildHorizontalStackedBars(chartData, idx, maxVal, colors)
                      : _buildHorizontalGroupedBars(chartData, idx, maxVal, colors),
                ),
              ),
            ],
          ),
        );
      }),
    );
  }

  Widget _buildHorizontalStackedBars(ChartData chartData, int labelIdx, double maxVal, List<String> colors) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final totalWidth = constraints.maxWidth;
        return Row(
          children: List.generate(chartData.series.length, (sIdx) {
            final series = chartData.series[sIdx];
            final val = labelIdx < series.values.length ? series.values[labelIdx] : 0.0;
            final w = (val / maxVal) * totalWidth;
            if (w <= 0) return const SizedBox.shrink();

            return Container(
              width: w,
              height: constraints.maxHeight * 0.6,
              color: _parseColor(colors[sIdx % colors.length]),
            );
          }),
        );
      },
    );
  }

  Widget _buildHorizontalGroupedBars(ChartData chartData, int labelIdx, double maxVal, List<String> colors) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final totalWidth = constraints.maxWidth;
        return Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: List.generate(chartData.series.length, (sIdx) {
            final series = chartData.series[sIdx];
            final val = labelIdx < series.values.length ? series.values[labelIdx] : 0.0;
            final w = (val / maxVal) * totalWidth;

            return Container(
              width: w > 0 ? w : 2,
              height: (constraints.maxHeight / chartData.series.length) * 0.7,
              margin: const EdgeInsets.symmetric(vertical: 1),
              color: _parseColor(colors[sIdx % colors.length]),
            );
          }),
        );
      },
    );
  }

  Widget _buildLegend(ChartData chartData, List<String> colors) {
    return Wrap(
      spacing: 12,
      runSpacing: 4,
      children: List.generate(chartData.series.length, (sIdx) {
        final series = chartData.series[sIdx];
        final color = _parseColor(colors[sIdx % colors.length]);
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(width: 12, height: 12, color: color),
            const SizedBox(width: 4),
            Text(series.name, style: const TextStyle(fontSize: 11)),
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
      return Colors.blue;
    }
  }
}
