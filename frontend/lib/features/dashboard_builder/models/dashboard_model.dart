import 'widget_model.dart';

class CanvasModel {
  final double width;
  final double height;
  final String backgroundColor;
  final List<WidgetModel> widgets;

  const CanvasModel({
    required this.width,
    required this.height,
    required this.backgroundColor,
    required this.widgets,
  });

  factory CanvasModel.fromJson(Map<String, dynamic> json) {
    return CanvasModel(
      width: (json['width'] as num?)?.toDouble() ?? 1920.0,
      height: (json['height'] as num?)?.toDouble() ?? 1080.0,
      backgroundColor: json['background_color'] ?? json['backgroundColor'] ?? '#F5F5F5',
      widgets: (json['widgets'] as List?)
              ?.map((w) => WidgetModel.fromJson(w as Map<String, dynamic>))
              .toList() ??
          const [],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'width': width,
      'height': height,
      'background_color': backgroundColor,
      'widgets': widgets.map((w) => w.toJson()).toList(),
    };
  }

  CanvasModel copyWith({
    double? width,
    double? height,
    String? backgroundColor,
    List<WidgetModel>? widgets,
  }) {
    return CanvasModel(
      width: width ?? this.width,
      height: height ?? this.height,
      backgroundColor: backgroundColor ?? this.backgroundColor,
      widgets: widgets ?? this.widgets,
    );
  }
}

class DashboardSettings {
  final bool autoRefresh;
  final int refreshIntervalSeconds;
  final Map<String, dynamic> theme;

  const DashboardSettings({
    this.autoRefresh = false,
    this.refreshIntervalSeconds = 60,
    this.theme = const {},
  });

  factory DashboardSettings.fromJson(Map<String, dynamic> json) {
    return DashboardSettings(
      autoRefresh: json['auto_refresh'] ?? json['autoRefresh'] ?? false,
      refreshIntervalSeconds: json['refresh_interval_seconds'] ?? json['refreshIntervalSeconds'] ?? 60,
      theme: Map<String, dynamic>.from(json['theme'] ?? {}),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'auto_refresh': autoRefresh,
      'refresh_interval_seconds': refreshIntervalSeconds,
      'theme': theme,
    };
  }

  DashboardSettings copyWith({
    bool? autoRefresh,
    int? refreshIntervalSeconds,
    Map<String, dynamic>? theme,
  }) {
    return DashboardSettings(
      autoRefresh: autoRefresh ?? this.autoRefresh,
      refreshIntervalSeconds: refreshIntervalSeconds ?? this.refreshIntervalSeconds,
      theme: theme ?? this.theme,
    );
  }
}

class DashboardModel {
  final String id;
  final String orgId;
  final String projectId;
  final String name;
  final String? description;
  final bool isPublic;
  final String? publicToken;
  final CanvasModel canvas;
  final DashboardSettings settings;
  final List<String> linkedAnalysisIds;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final String? createdBy;

  const DashboardModel({
    required this.id,
    required this.orgId,
    required this.projectId,
    required this.name,
    this.description,
    this.isPublic = false,
    this.publicToken,
    required this.canvas,
    required this.settings,
    required this.linkedAnalysisIds,
    this.createdAt,
    this.updatedAt,
    this.createdBy,
  });

  factory DashboardModel.fromJson(Map<String, dynamic> json) {
    return DashboardModel(
      id: json['_id'] ?? json['id'] ?? '',
      orgId: json['org_id'] ?? json['orgId'] ?? '',
      projectId: json['project_id'] ?? json['projectId'] ?? '',
      name: json['name'] ?? '',
      description: json['description'],
      isPublic: json['is_public'] ?? json['isPublic'] ?? false,
      publicToken: json['public_token'] ?? json['publicToken'],
      canvas: CanvasModel.fromJson(json['canvas'] ?? {}),
      settings: DashboardSettings.fromJson(json['settings'] ?? {}),
      linkedAnalysisIds: (json['linked_analysis_ids'] ?? json['linkedAnalysisIds'] as List?)
              ?.map((e) => e.toString())
              .toList() ??
          const [],
      createdAt: json['created_at'] != null ? DateTime.parse(json['created_at']) : null,
      updatedAt: json['updated_at'] != null ? DateTime.parse(json['updated_at']) : null,
      createdBy: json['created_by'] ?? json['createdBy'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      '_id': id,
      'org_id': orgId,
      'project_id': projectId,
      'name': name,
      'description': description,
      'is_public': isPublic,
      'public_token': publicToken,
      'canvas': canvas.toJson(),
      'settings': settings.toJson(),
      'linked_analysis_ids': linkedAnalysisIds,
      'created_at': createdAt?.toIso8601String(),
      'updated_at': updatedAt?.toIso8601String(),
      'created_by': createdBy,
    };
  }

  DashboardModel copyWith({
    String? id,
    String? orgId,
    String? projectId,
    String? name,
    String? Function()? description,
    bool? isPublic,
    String? Function()? publicToken,
    CanvasModel? canvas,
    DashboardSettings? settings,
    List<String>? linkedAnalysisIds,
    DateTime? createdAt,
    DateTime? updatedAt,
    String? createdBy,
  }) {
    return DashboardModel(
      id: id ?? this.id,
      orgId: orgId ?? this.orgId,
      projectId: projectId ?? this.projectId,
      name: name ?? this.name,
      description: description != null ? description() : this.description,
      isPublic: isPublic ?? this.isPublic,
      publicToken: publicToken != null ? publicToken() : this.publicToken,
      canvas: canvas ?? this.canvas,
      settings: settings ?? this.settings,
      linkedAnalysisIds: linkedAnalysisIds ?? this.linkedAnalysisIds,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      createdBy: createdBy ?? this.createdBy,
    );
  }
}
