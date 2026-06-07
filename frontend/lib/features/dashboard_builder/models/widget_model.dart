class WidgetPosition {
  final double x;
  final double y;

  const WidgetPosition({required this.x, required this.y});

  factory WidgetPosition.fromJson(Map<String, dynamic> json) {
    return WidgetPosition(
      x: (json['x'] as num).toDouble(),
      y: (json['y'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {'x': x, 'y': y};

  WidgetPosition copyWith({double? x, double? y}) {
    return WidgetPosition(
      x: x ?? this.x,
      y: y ?? this.y,
    );
  }
}

class WidgetSize {
  final double width;
  final double height;

  const WidgetSize({required this.width, required this.height});

  factory WidgetSize.fromJson(Map<String, dynamic> json) {
    return WidgetSize(
      width: (json['width'] as num).toDouble(),
      height: (json['height'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {'width': width, 'height': height};

  WidgetSize copyWith({double? width, double? height}) {
    return WidgetSize(
      width: width ?? this.width,
      height: height ?? this.height,
    );
  }
}

class DataBinding {
  final String? analysisId;
  final String? nodeId;
  final String refreshMode; // with_dashboard | independent | never
  final int? refreshIntervalSeconds; // optional, for independent mode

  const DataBinding({
    this.analysisId,
    this.nodeId,
    required this.refreshMode,
    this.refreshIntervalSeconds,
  });

  factory DataBinding.fromJson(Map<String, dynamic> json) {
    return DataBinding(
      analysisId: json['analysis_id'] ?? json['analysisId'],
      nodeId: json['node_id'] ?? json['nodeId'],
      refreshMode: json['refresh_mode'] ?? json['refreshMode'] ?? 'with_dashboard',
      refreshIntervalSeconds: json['refresh_interval_seconds'] ?? json['refreshIntervalSeconds'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'analysis_id': analysisId,
      'node_id': nodeId,
      'refresh_mode': refreshMode,
      'refresh_interval_seconds': refreshIntervalSeconds,
    };
  }

  DataBinding copyWith({
    String? Function()? analysisId,
    String? Function()? nodeId,
    String? refreshMode,
    int? Function()? refreshIntervalSeconds,
  }) {
    return DataBinding(
      analysisId: analysisId != null ? analysisId() : this.analysisId,
      nodeId: nodeId != null ? nodeId() : this.nodeId,
      refreshMode: refreshMode ?? this.refreshMode,
      refreshIntervalSeconds: refreshIntervalSeconds != null ? refreshIntervalSeconds() : this.refreshIntervalSeconds,
    );
  }
}

class FilterBinding {
  final String filterWidgetId;
  final String boundField;

  const FilterBinding({
    required this.filterWidgetId,
    required this.boundField,
  });

  factory FilterBinding.fromJson(Map<String, dynamic> json) {
    return FilterBinding(
      filterWidgetId: json['filter_widget_id'] ?? json['filterWidgetId'] ?? '',
      boundField: json['bound_field'] ?? json['boundField'] ?? '',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'filter_widget_id': filterWidgetId,
      'bound_field': boundField,
    };
  }

  FilterBinding copyWith({
    String? filterWidgetId,
    String? boundField,
  }) {
    return FilterBinding(
      filterWidgetId: filterWidgetId ?? this.filterWidgetId,
      boundField: boundField ?? this.boundField,
    );
  }
}

class WidgetModel {
  final String id;
  final String type;
  final WidgetPosition position;
  final WidgetSize size;
  final int zIndex;
  final bool isLocked;
  final Map<String, dynamic> properties;
  final DataBinding? dataBinding;
  final List<FilterBinding> filters;

  const WidgetModel({
    required this.id,
    required this.type,
    required this.position,
    required this.size,
    this.zIndex = 0,
    this.isLocked = false,
    required this.properties,
    this.dataBinding,
    this.filters = const [],
  });

  factory WidgetModel.fromJson(Map<String, dynamic> json) {
    return WidgetModel(
      id: json['id'] ?? '',
      type: json['type'] ?? '',
      position: WidgetPosition.fromJson(json['position'] ?? {'x': 0, 'y': 0}),
      size: WidgetSize.fromJson(json['size'] ?? {'width': 100, 'height': 100}),
      zIndex: json['z_index'] ?? json['zIndex'] ?? 0,
      isLocked: json['is_locked'] ?? json['isLocked'] ?? false,
      properties: Map<String, dynamic>.from(json['properties'] ?? {}),
      dataBinding: json['data_binding'] != null ? DataBinding.fromJson(json['data_binding']) : null,
      filters: (json['filters'] as List?)?.map((f) => FilterBinding.fromJson(f)).toList() ?? const [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type,
      'position': position.toJson(),
      'size': size.toJson(),
      'z_index': zIndex,
      'is_locked': isLocked,
      'properties': properties,
      'data_binding': dataBinding?.toJson(),
      'filters': filters.map((f) => f.toJson()).toList(),
    };
  }

  WidgetModel copyWith({
    String? id,
    String? type,
    WidgetPosition? position,
    WidgetSize? size,
    int? zIndex,
    bool? isLocked,
    Map<String, dynamic>? properties,
    DataBinding? Function()? dataBinding,
    List<FilterBinding>? filters,
  }) {
    return WidgetModel(
      id: id ?? this.id,
      type: type ?? this.type,
      position: position ?? this.position,
      size: size ?? this.size,
      zIndex: zIndex ?? this.zIndex,
      isLocked: isLocked ?? this.isLocked,
      properties: properties ?? this.properties,
      dataBinding: dataBinding != null ? dataBinding() : this.dataBinding,
      filters: filters ?? this.filters,
    );
  }
}
