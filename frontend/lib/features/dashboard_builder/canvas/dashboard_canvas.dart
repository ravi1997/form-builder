import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/canvas_state_provider.dart';
import '../widgets/draggable_widget_wrapper.dart';
import 'canvas_grid.dart';

class DashboardCanvas extends ConsumerWidget {
  final String dashboardId;

  const DashboardCanvas({
    super.key,
    required this.dashboardId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(canvasStateProvider(dashboardId));
    final sortedWidgets = List.from(state.widgets)
      ..sort((a, b) => a.zIndex.compareTo(b.zIndex));

    final canvasBgColor = _parseColor(state.backgroundColor);

    return InteractiveViewer(
      boundaryMargin: const EdgeInsets.all(400),
      minScale: 0.25,
      maxScale: 2.0,
      scaleEnabled: true,
      panEnabled: true,
      onInteractionUpdate: (details) {
        // Optional state sync for zoom/pan if needed
      },
      child: Center(
        child: Container(
          width: state.canvasWidth,
          height: state.canvasHeight,
          decoration: BoxDecoration(
            color: canvasBgColor,
            boxShadow: const [
              BoxShadow(
                color: Colors.black26,
                blurRadius: 10,
                offset: Offset(0, 4),
              ),
            ],
          ),
          child: Stack(
            children: [
              // Grid overlay
              Positioned.fill(
                child: CanvasGrid(
                  gridSize: state.gridSize,
                  showGrid: state.mode == CanvasMode.edit,
                ),
              ),
              // Widgets
              ...sortedWidgets.map((w) {
                return DraggableWidgetWrapper(
                  dashboardId: state.dashboardId,
                  widget: w,
                );
              }),
            ],
          ),
        ),
      ),
    );
  }

  Color _parseColor(String hex) {
    try {
      final clean = hex.replaceAll('#', '');
      return Color(int.parse('FF$clean', radix: 16));
    } catch (_) {
      return const Color(0xFFF5F5F5);
    }
  }
}
