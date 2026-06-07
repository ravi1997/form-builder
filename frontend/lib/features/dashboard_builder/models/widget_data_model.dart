class WidgetDataResult {
  final String status; // ok | loading | error | no_binding | no_run
  final dynamic data;  // raw map or list returned from backend
  final String? error;
  final DateTime? generatedAt;

  const WidgetDataResult({
    required this.status,
    this.data,
    this.error,
    this.generatedAt,
  });

  factory WidgetDataResult.fromJson(Map<String, dynamic> json) {
    return WidgetDataResult(
      status: json['status'] ?? 'no_binding',
      data: json['data'],
      error: json['error'],
      generatedAt: json['generated_at'] != null || json['generatedAt'] != null
          ? DateTime.tryParse(json['generated_at'] ?? json['generatedAt'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'status': status,
      'data': data,
      'error': error,
      'generated_at': generatedAt?.toIso8601String(),
    };
  }
}

class KpiData {
  final double value;
  final String? label;
  final double? previousValue;
  final String? unit;

  const KpiData({
    required this.value,
    this.label,
    this.previousValue,
    this.unit,
  });

  factory KpiData.fromJson(Map<String, dynamic> json) {
    return KpiData(
      value: (json['value'] as num?)?.toDouble() ?? 0.0,
      label: json['label'],
      previousValue: (json['previous_value'] ?? json['previousValue'] as num?)?.toDouble(),
      unit: json['unit'],
    );
  }
}

class ChartSeries {
  final String name;
  final List<double> values;
  final String? color;

  const ChartSeries({
    required this.name,
    required this.values,
    this.color,
  });

  factory ChartSeries.fromJson(Map<String, dynamic> json) {
    return ChartSeries(
      name: json['name'] ?? '',
      values: (json['values'] as List?)?.map((v) => (v as num).toDouble()).toList() ?? const [],
      color: json['color'],
    );
  }
}

class ChartData {
  final String chartType;
  final List<String> labels;
  final List<ChartSeries> series;
  final String? xAxisLabel;
  final String? yAxisLabel;

  const ChartData({
    required this.chartType,
    required this.labels,
    required this.series,
    this.xAxisLabel,
    this.yAxisLabel,
  });

  factory ChartData.fromJson(Map<String, dynamic> json) {
    return ChartData(
      chartType: json['chart_type'] ?? json['chartType'] ?? 'bar',
      labels: (json['labels'] as List?)?.map((l) => l.toString()).toList() ?? const [],
      series: (json['series'] as List?)?.map((s) => ChartSeries.fromJson(s)).toList() ?? const [],
      xAxisLabel: json['x_axis_label'] ?? json['xAxisLabel'],
      yAxisLabel: json['y_axis_label'] ?? json['yAxisLabel'],
    );
  }
}

class PieSegment {
  final String label;
  final double value;
  final String? color;

  const PieSegment({
    required this.label,
    required this.value,
    this.color,
  });

  factory PieSegment.fromJson(Map<String, dynamic> json) {
    return PieSegment(
      label: json['label'] ?? '',
      value: (json['value'] as num?)?.toDouble() ?? 0.0,
      color: json['color'],
    );
  }
}

class PieChartData {
  final String chartType;
  final List<PieSegment> segments;

  const PieChartData({
    required this.chartType,
    required this.segments,
  });

  factory PieChartData.fromJson(Map<String, dynamic> json) {
    return PieChartData(
      chartType: json['chart_type'] ?? json['chartType'] ?? 'pie',
      segments: (json['segments'] as List?)?.map((s) => PieSegment.fromJson(s)).toList() ?? const [],
    );
  }
}

class TableColumnDef {
  final String name;
  final String label;
  final String type; // string | number | boolean | date

  const TableColumnDef({
    required this.name,
    required this.label,
    required this.type,
  });

  factory TableColumnDef.fromJson(Map<String, dynamic> json) {
    return TableColumnDef(
      name: json['name'] ?? '',
      label: json['label'] ?? '',
      type: json['type'] ?? 'string',
    );
  }
}

class TableData {
  final List<Map<String, dynamic>> rows;
  final int rowCount;
  final List<TableColumnDef> columns;

  const TableData({
    required this.rows,
    required this.rowCount,
    required this.columns,
  });

  factory TableData.fromJson(Map<String, dynamic> json) {
    return TableData(
      rows: (json['rows'] as List?)?.map((r) => Map<String, dynamic>.from(r)).toList() ?? const [],
      rowCount: json['row_count'] ?? json['rowCount'] ?? 0,
      columns: (json['columns'] as List?)?.map((c) => TableColumnDef.fromJson(c)).toList() ?? const [],
    );
  }
}
