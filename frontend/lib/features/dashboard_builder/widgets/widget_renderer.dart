import 'package:flutter/material.dart';
import '../models/widget_model.dart';
import '../models/widget_data_model.dart';
import 'kpi_card_widget.dart';
import 'bar_chart_widget.dart';
import 'line_chart_widget.dart';
import 'pie_chart_widget.dart';
import 'data_table_widget.dart';
import 'text_label_widget.dart';
import 'image_widget.dart';
import 'filter_widget_widget.dart';
import 'divider_widget.dart';

class WidgetRenderer extends StatelessWidget {
  final WidgetModel widget;
  final WidgetDataResult? dataResult;

  const WidgetRenderer({
    super.key,
    required this.widget,
    this.dataResult,
  });

  @override
  Widget build(BuildContext context) {
    switch (widget.type) {
      case 'kpi_card':
        return KpiCardWidget(widget: widget, dataResult: dataResult);
      case 'bar_chart':
        return BarChartWidget(widget: widget, dataResult: dataResult);
      case 'line_chart':
        return LineChartWidget(widget: widget, dataResult: dataResult);
      case 'pie_chart':
        return PieChartWidget(widget: widget, dataResult: dataResult);
      case 'data_table':
        return DataTableWidget(widget: widget, dataResult: dataResult);
      case 'text_label':
        return TextLabelWidget(widget: widget, dataResult: dataResult);
      case 'image_widget':
        return ImageWidget(widget: widget);
      case 'filter_widget':
        return FilterWidgetWidget(widget: widget);
      case 'divider_widget':
        return DividerWidget(widget: widget);
      default:
        return Center(
          child: Text('Unknown widget type: ${widget.type}'),
        );
    }
  }
}
