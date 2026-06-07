import 'dart:ui';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/dashboard_model.dart';
import '../models/widget_model.dart';
import 'dashboard_provider.dart';

enum CanvasMode { edit, preview }

class CanvasState {
  final String dashboardId;
  final double canvasWidth;
  final double canvasHeight;
  final String backgroundColor;
  final List<WidgetModel> widgets;
  final String? selectedWidgetId;
  final bool isDirty;
  final bool isLoading;
  final CanvasMode mode;
  final double zoomLevel;
  final Offset panOffset;
  final bool snapToGrid;
  final int gridSize;

  const CanvasState({
    required this.dashboardId,
    this.canvasWidth = 1920.0,
    this.canvasHeight = 1080.0,
    this.backgroundColor = '#F5F5F5',
    this.widgets = const [],
    this.selectedWidgetId,
    this.isDirty = false,
    this.isLoading = false,
    this.mode = CanvasMode.edit,
    this.zoomLevel = 1.0,
    this.panOffset = Offset.zero,
    this.snapToGrid = false,
    this.gridSize = 8,
  });

  CanvasState copyWith({
    String? dashboardId,
    double? canvasWidth,
    double? canvasHeight,
    String? backgroundColor,
    List<WidgetModel>? widgets,
    String? Function()? selectedWidgetId,
    bool? isDirty,
    bool? isLoading,
    CanvasMode? mode,
    double? zoomLevel,
    Offset? panOffset,
    bool? snapToGrid,
    int? gridSize,
  }) {
    return CanvasState(
      dashboardId: dashboardId ?? this.dashboardId,
      canvasWidth: canvasWidth ?? this.canvasWidth,
      canvasHeight: canvasHeight ?? this.canvasHeight,
      backgroundColor: backgroundColor ?? this.backgroundColor,
      widgets: widgets ?? this.widgets,
      selectedWidgetId: selectedWidgetId != null ? selectedWidgetId() : this.selectedWidgetId,
      isDirty: isDirty ?? this.isDirty,
      isLoading: isLoading ?? this.isLoading,
      mode: mode ?? this.mode,
      zoomLevel: zoomLevel ?? this.zoomLevel,
      panOffset: panOffset ?? this.panOffset,
      snapToGrid: snapToGrid ?? this.snapToGrid,
      gridSize: gridSize ?? this.gridSize,
    );
  }
}

class CanvasStateNotifier extends Notifier<CanvasState> {
  final String dashboardId;
  final List<List<WidgetModel>> _undoStack = [];
  final List<List<WidgetModel>> _redoStack = [];

  CanvasStateNotifier(this.dashboardId);

  @override
  CanvasState build() {
    return CanvasState(dashboardId: dashboardId);
  }

  void loadDashboard(DashboardModel dashboard) {
    state = CanvasState(
      dashboardId: dashboard.id,
      canvasWidth: dashboard.canvas.width,
      canvasHeight: dashboard.canvas.height,
      backgroundColor: dashboard.canvas.backgroundColor,
      widgets: dashboard.canvas.widgets,
      mode: CanvasMode.edit,
      isDirty: false,
    );
    _undoStack.clear();
    _redoStack.clear();
  }

  void toggleMode() {
    state = state.copyWith(
      mode: state.mode == CanvasMode.edit ? CanvasMode.preview : CanvasMode.edit,
      selectedWidgetId: const ValueCell<String?>(null).call,
    );
  }

  void setZoom(double zoom) {
    state = state.copyWith(zoomLevel: zoom.clamp(0.25, 2.0));
  }

  void setPan(Offset offset) {
    state = state.copyWith(panOffset: offset);
  }

  void toggleSnapToGrid() {
    state = state.copyWith(snapToGrid: !state.snapToGrid);
  }

  void setGridSize(int size) {
    state = state.copyWith(gridSize: size.clamp(4, 64));
  }

  void selectWidget(String? id) {
    if (state.mode == CanvasMode.edit) {
      state = state.copyWith(selectedWidgetId: () => id);
    }
  }

  double _snap(double val) {
    if (!state.snapToGrid) return val;
    return (val / state.gridSize).round() * state.gridSize.toDouble();
  }

  void _pushHistory() {
    if (_undoStack.length >= 50) {
      _undoStack.removeAt(0);
    }
    _undoStack.add(List<WidgetModel>.from(state.widgets));
    _redoStack.clear();
  }

  void undo() {
    if (_undoStack.isEmpty) return;
    final previous = _undoStack.removeLast();
    _redoStack.add(List<WidgetModel>.from(state.widgets));
    state = state.copyWith(
      widgets: previous,
      isDirty: true,
    );
  }

  void redo() {
    if (_redoStack.isEmpty) return;
    final next = _redoStack.removeLast();
    _undoStack.add(List<WidgetModel>.from(state.widgets));
    state = state.copyWith(
      widgets: next,
      isDirty: true,
    );
  }

  void addWidget({required String type, required Offset position}) {
    _pushHistory();
    final id = 'widget_${DateTime.now().microsecondsSinceEpoch}';
    double defaultW = 280;
    double defaultH = 140;

    switch (type) {
      case 'kpi_card':
        defaultW = 280; defaultH = 140;
        break;
      case 'bar_chart':
      case 'line_chart':
        defaultW = 480; defaultH = 320;
        break;
      case 'pie_chart':
        defaultW = 340; defaultH = 320;
        break;
      case 'data_table':
        defaultW = 600; defaultH = 400;
        break;
      case 'text_label':
        defaultW = 240; defaultH = 60;
        break;
      case 'image_widget':
        defaultW = 300; defaultH = 200;
        break;
      case 'filter_widget':
        defaultW = 240; defaultH = 90;
        break;
      case 'divider_widget':
        defaultW = 400; defaultH = 10;
        break;
    }

    final maxZ = state.widgets.isEmpty ? 0 : state.widgets.map((w) => w.zIndex).reduce((a, b) => a > b ? a : b);

    final newWidget = WidgetModel(
      id: id,
      type: type,
      position: WidgetPosition(x: _snap(position.dx), y: _snap(position.dy)),
      size: WidgetSize(width: defaultW, height: defaultH),
      zIndex: maxZ + 1,
      properties: _getDefaultProperties(type),
    );

    state = state.copyWith(
      widgets: [...state.widgets, newWidget],
      selectedWidgetId: () => id,
      isDirty: true,
    );
  }

  void deleteWidget(String id) {
    _pushHistory();
    state = state.copyWith(
      widgets: state.widgets.where((w) => w.id != id).toList(),
      selectedWidgetId: state.selectedWidgetId == id ? () => null : null,
      isDirty: true,
    );
  }

  void moveWidget(String id, double x, double y) {
    _pushHistory();
    state = state.copyWith(
      widgets: state.widgets.map((w) {
        if (w.id != id || w.isLocked) return w;
        final snappedX = _snap(x).clamp(0.0, state.canvasWidth - w.size.width);
        final snappedY = _snap(y).clamp(0.0, state.canvasHeight - w.size.height);
        return w.copyWith(position: WidgetPosition(x: snappedX, y: snappedY));
      }).toList(),
      isDirty: true,
    );
  }

  void resizeWidget(String id, double x, double y, double w, double h) {
    _pushHistory();
    state = state.copyWith(
      widgets: state.widgets.map((widget) {
        if (widget.id != id || widget.isLocked) return widget;
        final snappedW = _snap(w).clamp(20.0, state.canvasWidth);
        final snappedH = _snap(h).clamp(20.0, state.canvasHeight);
        final snappedX = _snap(x).clamp(0.0, state.canvasWidth - snappedW);
        final snappedY = _snap(y).clamp(0.0, state.canvasHeight - snappedH);

        return widget.copyWith(
          position: WidgetPosition(x: snappedX, y: snappedY),
          size: WidgetSize(width: snappedW, height: snappedH),
        );
      }).toList(),
      isDirty: true,
    );
  }

  void updateWidgetProperties(String id, Map<String, dynamic> props) {
    _pushHistory();
    state = state.copyWith(
      widgets: state.widgets.map((w) {
        if (w.id != id) return w;
        final newProps = Map<String, dynamic>.from(w.properties)..addAll(props);
        return w.copyWith(properties: newProps);
      }).toList(),
      isDirty: true,
    );
  }

  void updateWidgetBinding(String id, DataBinding? binding) {
    _pushHistory();
    state = state.copyWith(
      widgets: state.widgets.map((w) {
        if (w.id != id) return w;
        return w.copyWith(dataBinding: () => binding);
      }).toList(),
      isDirty: true,
    );
  }

  void toggleLockWidget(String id) {
    _pushHistory();
    state = state.copyWith(
      widgets: state.widgets.map((w) {
        if (w.id != id) return w;
        return w.copyWith(isLocked: !w.isLocked);
      }).toList(),
      isDirty: true,
    );
  }

  void bringToFront(String id) {
    _pushHistory();
    if (state.widgets.isEmpty) return;
    final maxZ = state.widgets.map((w) => w.zIndex).reduce((a, b) => a > b ? a : b);
    state = state.copyWith(
      widgets: state.widgets.map((w) {
        if (w.id != id) return w;
        return w.copyWith(zIndex: maxZ + 1);
      }).toList(),
      isDirty: true,
    );
  }

  void sendToBack(String id) {
    _pushHistory();
    if (state.widgets.isEmpty) return;
    final minZ = state.widgets.map((w) => w.zIndex).reduce((a, b) => a < b ? a : b);
    state = state.copyWith(
      widgets: state.widgets.map((w) {
        if (w.id != id) return w;
        return w.copyWith(zIndex: minZ - 1);
      }).toList(),
      isDirty: true,
    );
  }

  Future<void> saveCanvasState() async {
    state = state.copyWith(isLoading: true);
    try {
      final service = ref.read(dashboardServiceProvider);
      final token = ref.read(authTokenProvider);
      final canvas = CanvasModel(
        width: state.canvasWidth,
        height: state.canvasHeight,
        backgroundColor: state.backgroundColor,
        widgets: state.widgets,
      );

      await service.saveCanvas(
        dashboardId: state.dashboardId,
        canvas: canvas,
        token: token,
      );
      state = state.copyWith(isDirty: false);
    } catch (_) {
      // Keep it dirty if saving failed
    } finally {
      state = state.copyWith(isLoading: false);
    }
  }

  Map<String, dynamic> _getDefaultProperties(String type) {
    final Map<String, dynamic> common = {
      'title': 'New Widget',
      'show_title': true,
      'title_font_size': 16.0,
      'title_color': '#212121',
      'background_color': '#FFFFFF',
      'border_radius': 8.0,
      'border_width': 1.0,
      'border_color': '#E0E0E0',
      'padding': 16.0,
      'show_loading_spinner': true,
      'no_data_message': 'No data available',
    };

    switch (type) {
      case 'kpi_card':
        return {
          ...common,
          'title': 'KPI Card',
          'value_format': 'number',
          'decimal_places': 0,
          'prefix': '',
          'suffix': '',
          'show_comparison': false,
          'comparison_label': 'vs last period',
          'positive_is_good': true,
          'icon': 'trending_up',
          'icon_color': '#1976D2',
          'value_font_size': 36.0,
          'value_color': '#212121',
        };
      case 'bar_chart':
        return {
          ...common,
          'title': 'Bar Chart',
          'orientation': 'vertical',
          'stacked': false,
          'show_legend': true,
          'legend_position': 'bottom',
          'show_grid_lines': true,
          'show_values_on_bars': false,
          'bar_width_ratio': 0.6,
          'color_palette': ['#1976D2', '#388E3C', '#F57C00', '#7B1FA2'],
          'x_axis_label': '',
          'y_axis_label': '',
          'animate': true,
        };
      case 'line_chart':
        return {
          ...common,
          'title': 'Line Chart',
          'fill_area': false,
          'fill_opacity': 0.2,
          'show_dots': true,
          'dot_radius': 4.0,
          'line_width': 2.0,
          'smooth': true,
          'show_legend': true,
          'legend_position': 'bottom',
          'show_grid_lines': true,
          'color_palette': ['#1976D2', '#388E3C'],
          'animate': true,
        };
      case 'pie_chart':
        return {
          ...common,
          'title': 'Pie Chart',
          'donut': false,
          'donut_hole_ratio': 0.5,
          'center_label': '',
          'show_legend': true,
          'legend_position': 'right',
          'show_percentage_labels': true,
          'show_value_labels': false,
          'min_slice_percentage': 2.0,
          'color_palette': ['#1976D2', '#E91E63', '#388E3C', '#F57C00'],
          'animate': true,
        };
      case 'data_table':
        return {
          ...common,
          'title': 'Data Table',
          'show_row_numbers': false,
          'striped_rows': true,
          'row_height': 48.0,
          'header_background': '#F5F5F5',
          'header_text_color': '#424242',
          'font_size': 13.0,
          'allow_sort': true,
          'default_sort_column': '',
          'default_sort_direction': 'asc',
          'column_overrides': [],
          'max_rows_display': 100,
          'show_pagination': true,
          'show_search': false,
          'wrap_text': false,
        };
      case 'text_label':
        return {
          ...common,
          'title': 'Text Label',
          'show_title': false,
          'text': 'Label Description',
          'font_size': 16.0,
          'font_weight': 'regular',
          'text_color': '#212121',
          'text_align': 'left',
          'allow_markdown': false,
          'value_format': 'number',
          'prefix': '',
          'suffix': '',
        };
      case 'image_widget':
        return {
          ...common,
          'title': 'Image',
          'show_title': false,
          'image_url': '',
          'fit': 'contain',
          'alt_text': '',
          'link_url': '',
          'border_radius': 0.0,
        };
      case 'filter_widget':
        return {
          ...common,
          'title': 'Filter',
          'show_title': false,
          'filter_type': 'dropdown',
          'label': 'Filter Label',
          'placeholder': 'Select...',
          'options_source': 'static',
          'static_options': [],
          'dynamic_analysis_id': null,
          'dynamic_node_id': null,
          'dynamic_column': null,
          'default_value': null,
          'allow_clear': true,
          'clear_label': 'All',
        };
      case 'divider_widget':
        return {
          ...common,
          'title': 'Divider',
          'show_title': false,
          'style': 'divider',
          'direction': 'horizontal',
          'line_color': '#E0E0E0',
          'line_thickness': 1.0,
          'line_style': 'solid',
        };
    }
    return common;
  }
}

// Simple value holder for copyWith constructor logic
class ValueCell<T> {
  final T value;
  const ValueCell(this.value);
  T call() => value;
}

final canvasStateProvider = NotifierProvider.family<CanvasStateNotifier, CanvasState, String>((dashboardId) {
  return CanvasStateNotifier(dashboardId);
});
