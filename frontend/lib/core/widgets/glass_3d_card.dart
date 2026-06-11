import 'dart:ui';
import 'package:flutter/material.dart';
import '../../core/theme/theme_presets.dart';
import '../theme/tokens.dart';

class Glass3DCard extends StatefulWidget {
  final Widget child;
  final ThemePreset theme;
  final double width;
  final double height;

  const Glass3DCard({
    super.key,
    required this.child,
    required this.theme,
    this.width = 450,
    this.height = 550,
  });

  @override
  State<Glass3DCard> createState() => _Glass3DCardState();
}

class _Glass3DCardState extends State<Glass3DCard> {
  double _tiltX = 0.0;
  double _tiltY = 0.0;
  bool _isHovered = false;

  void _onHover(PointerEvent event) {
    final RenderBox renderBox = context.findRenderObject() as RenderBox;
    final cardPosition = renderBox.localToGlobal(Offset.zero);
    final cardCenter = Offset(
      cardPosition.dx + widget.width / 2,
      cardPosition.dy + widget.height / 2,
    );

    final dx = event.position.dx - cardCenter.dx;
    final dy = event.position.dy - cardCenter.dy;

    setState(() {
      _isHovered = true;
      // Max tilt angle around 8 degrees (approx 0.14 radians)
      _tiltX = -(dy / (widget.height / 2)).clamp(-1.0, 1.0) * 0.14;
      _tiltY = (dx / (widget.width / 2)).clamp(-1.0, 1.0) * 0.14;
    });
  }

  void _onHoverExit(PointerEvent event) {
    setState(() {
      _isHovered = false;
      _tiltX = 0.0;
      _tiltY = 0.0;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onHover: _onHover,
      onExit: _onHoverExit,
      child: AnimatedScale(
        scale: _isHovered ? 1.04 : 1.0,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOutBack, // Playful bounce on hover scaling
        child: TweenAnimationBuilder<Offset>(
          tween: Tween<Offset>(begin: Offset.zero, end: Offset(_tiltX, _tiltY)),
          duration: const Duration(milliseconds: 150),
          curve: Curves.easeOutCubic, // Smooth damping on mouse move
          builder: (context, tilt, child) {
            return Transform(
              alignment: FractionalOffset.center,
              transform: Matrix4.identity()
                ..setEntry(3, 2, 0.0015) // perspective depth
                ..rotateX(tilt.dx)
                ..rotateY(tilt.dy),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 250),
                width: widget.width,
                height: widget.height,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(AppRadius.xxl),
                  boxShadow: [
                    BoxShadow(
                      color: _withAlpha(
                        widget.theme.glowColor,
                        _isHovered ? 0.35 : 0.12,
                      ),
                      blurRadius: _isHovered ? 36 : 16,
                      spreadRadius: _isHovered ? 6 : 1,
                      offset: Offset(0, _isHovered ? 12 : 6),
                    ),
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.xxl),
                  child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: 16.0, sigmaY: 16.0),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.xxxl,
                        vertical: AppSpacing.huge,
                      ),
                      decoration: BoxDecoration(
                        color: widget.theme.cardBg,
                        borderRadius: BorderRadius.circular(AppRadius.xxl),
                        border: Border.all(
                          color: _withAlpha(
                            widget.theme.cardBorder,
                            _isHovered ? 0.8 : 0.35,
                          ),
                          width: 1.5,
                        ),
                        gradient: LinearGradient(
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                          colors: [
                            _withAlpha(
                              widget.theme.glowColor,
                              _isHovered ? 0.10 : 0.06,
                            ),
                            _withAlpha(widget.theme.cardBg, 0.01),
                          ],
                        ),
                      ),
                      child: widget.child,
                    ),
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

Color _withAlpha(Color color, double opacity) {
  final clampedOpacity = opacity.clamp(0.0, 1.0);
  return color.withAlpha((clampedOpacity * 255).round());
}
