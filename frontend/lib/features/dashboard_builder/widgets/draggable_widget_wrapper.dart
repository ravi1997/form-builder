import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/widget_model.dart';
import '../models/widget_data_model.dart';
import '../providers/canvas_state_provider.dart';
import '../providers/widget_data_provider.dart';
import 'widget_renderer.dart';

class DraggableWidgetWrapper extends ConsumerStatefulWidget {
  final String dashboardId;
  final WidgetModel widget;

  const DraggableWidgetWrapper({
    super.key,
    required this.dashboardId,
    required this.widget,
  });

  @override
  ConsumerState<DraggableWidgetWrapper> createState() => _DraggableWidgetWrapperState();
}

class _DraggableWidgetWrapperState extends ConsumerState<DraggableWidgetWrapper> {
  Offset _dragStartOffset = Offset.zero;
  Offset _widgetStartPosition = Offset.zero;
  Offset _widgetStartSize = Offset.zero;

  @override
  Widget build(BuildContext context) {
    final canvasState = ref.watch(canvasStateProvider(widget.dashboardId));
    final isSelected = canvasState.selectedWidgetId == widget.widget.id;
    final isLocked = widget.widget.isLocked;
    final mode = canvasState.mode;

    // Get widget data results from state
    final dataState = ref.watch(widgetDataProvider(canvasState.dashboardId));
    final widgetData = dataState.widgetResults[widget.widget.id];

    final double x = widget.widget.position.x;
    final double y = widget.widget.position.y;
    final double w = widget.widget.size.width;
    final double h = widget.widget.size.height;

    final card = Container(
      width: w,
      height: h,
      padding: EdgeInsets.all(widget.widget.properties['padding']?.toDouble() ?? 16.0),
      decoration: BoxDecoration(
        color: _parseColor(widget.widget.properties['background_color'] ?? '#FFFFFF'),
        borderRadius: BorderRadius.circular(widget.widget.properties['border_radius']?.toDouble() ?? 8.0),
        border: Border.all(
          color: isSelected
              ? Theme.of(context).primaryColor
              : _parseColor(widget.widget.properties['border_color'] ?? '#E0E0E0'),
          width: isSelected ? 2.0 : (widget.widget.properties['border_width']?.toDouble() ?? 1.0),
        ),
      ),
      child: WidgetRenderer(
        widget: widget.widget,
        dataResult: widgetData,
      ),
    );

    if (mode == CanvasMode.preview) {
      return Positioned(
        left: x,
        top: y,
        child: card,
      );
    }

    return Positioned(
      left: x,
      top: y,
      child: GestureDetector(
        onTap: () {
          ref.read(canvasStateProvider(widget.dashboardId).notifier).selectWidget(widget.widget.id);
        },
        onPanStart: !isLocked
            ? (details) {
                ref.read(canvasStateProvider(widget.dashboardId).notifier).selectWidget(widget.widget.id);
                _dragStartOffset = details.globalPosition;
                _widgetStartPosition = Offset(x, y);
              }
            : null,
        onPanUpdate: !isLocked
            ? (details) {
                final delta = details.globalPosition - _dragStartOffset;
                final newX = _widgetStartPosition.dx + delta.dx;
                final newY = _widgetStartPosition.dy + delta.dy;
                ref.read(canvasStateProvider(widget.dashboardId).notifier).moveWidget(
                      widget.widget.id,
                      newX,
                      newY,
                    );
              }
            : null,
        child: Stack(
          clipBehavior: Clip.none,
          children: [
            card,
            if (isSelected && !isLocked) ...[
              // Corner Resize Handle (Bottom-Right)
              Positioned(
                right: 0,
                bottom: 0,
                child: GestureDetector(
                  onPanStart: (details) {
                    _dragStartOffset = details.globalPosition;
                    _widgetStartSize = Offset(w, h);
                    _widgetStartPosition = Offset(x, y);
                  },
                  onPanUpdate: (details) {
                    final delta = details.globalPosition - _dragStartOffset;
                    final newW = _widgetStartSize.dx + delta.dx;
                    final newH = _widgetStartSize.dy + delta.dy;
                    ref.read(canvasStateProvider(widget.dashboardId).notifier).resizeWidget(
                          widget.widget.id,
                          _widgetStartPosition.dx,
                          _widgetStartPosition.dy,
                          newW,
                          newH,
                        );
                  },
                  child: Container(
                    width: 14,
                    height: 14,
                    decoration: BoxDecoration(
                      color: Theme.of(context).primaryColor,
                      shape: BoxShape.circle,
                    ),
                  ),
                ),
              ),
              // Corner Lock Status Button
              Positioned(
                left: 4,
                top: 4,
                child: InkWell(
                  onTap: () {
                    ref.read(canvasStateProvider(widget.dashboardId).notifier).toggleLockWidget(widget.widget.id);
                  },
                  child: const Icon(Icons.lock_open, size: 16, color: Colors.grey),
                ),
              ),
            ] else if (isLocked) ...[
              Positioned(
                left: 4,
                top: 4,
                child: InkWell(
                  onTap: () {
                    ref.read(canvasStateProvider(widget.dashboardId).notifier).toggleLockWidget(widget.widget.id);
                  },
                  child: const Icon(Icons.lock, size: 16, color: Colors.red),
                ),
              ),
            ]
          ],
        ),
      ),
    );
  }

  Color _parseColor(String hex) {
    try {
      final clean = hex.replaceAll('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return Colors.white;
    }
  }
}
