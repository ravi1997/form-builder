import 'package:flutter/material.dart';

class CanvasGrid extends StatelessWidget {
  final int gridSize;
  final bool showGrid;
  final Color gridColor;

  const CanvasGrid({
    super.key,
    required this.gridSize,
    required this.showGrid,
    this.gridColor = const Color(0xFFE0E0E0),
  });

  @override
  Widget build(BuildContext context) {
    if (!showGrid) return const SizedBox.shrink();

    return CustomPaint(
      painter: _GridPainter(gridSize: gridSize, gridColor: gridColor),
      child: Container(),
    );
  }
}

class _GridPainter extends CustomPainter {
  final int gridSize;
  final Color gridColor;

  _GridPainter({required this.gridSize, required this.gridColor});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = gridColor
      ..strokeWidth = 0.5;

    // Draw vertical lines
    for (double x = 0; x < size.width; x += gridSize) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }

    // Draw horizontal lines
    for (double y = 0; y < size.height; y += gridSize) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant _GridPainter oldDelegate) {
    return oldDelegate.gridSize != gridSize || oldDelegate.gridColor != gridColor;
  }
}
