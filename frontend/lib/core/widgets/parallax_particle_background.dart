import 'dart:math' as math;
import 'package:flutter/material.dart';

class ParallaxParticleBackground extends StatefulWidget {
  final double scrollOffset;
  final Offset mousePosition;
  final Color themeGlowColor;

  const ParallaxParticleBackground({
    super.key,
    required this.scrollOffset,
    required this.mousePosition,
    required this.themeGlowColor,
  });

  @override
  State<ParallaxParticleBackground> createState() => _ParallaxParticleBackgroundState();
}

class _ParallaxParticleBackgroundState extends State<ParallaxParticleBackground>
    with SingleTickerProviderStateMixin {
  late List<_Particle> _particles;
  late AnimationController _controller;
  final int _particleCount = 50;

  @override
  void initState() {
    super.initState();
    _particles = List.generate(_particleCount, (index) => _Particle.random());
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 10),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return CustomPaint(
          painter: _ParticlePainter(
            particles: _particles,
            scrollOffset: widget.scrollOffset,
            mousePosition: widget.mousePosition,
            time: _controller.value,
            glowColor: widget.themeGlowColor,
          ),
          child: Container(),
        );
      },
    );
  }
}

class _Particle {
  double x; // normalized coordinate (-1.0 to 1.0)
  double y; // normalized coordinate (-1.0 to 1.0)
  double z; // depth layer (1.0 to 5.0)
  double size;
  double speed;

  _Particle({
    required this.x,
    required this.y,
    required this.z,
    required this.size,
    required this.speed,
  });

  factory _Particle.random() {
    final rand = math.Random();
    return _Particle(
      x: rand.nextDouble() * 2.0 - 1.0,
      y: rand.nextDouble() * 2.0 - 1.0,
      z: rand.nextDouble() * 4.0 + 1.0,
      size: rand.nextDouble() * 3.0 + 1.0,
      speed: rand.nextDouble() * 0.1 + 0.05,
    );
  }
}

class _ParticlePainter extends CustomPainter {
  final List<_Particle> particles;
  final double scrollOffset;
  final Offset mousePosition;
  final double time;
  final Color glowColor;

  _ParticlePainter({
    required this.particles,
    required this.scrollOffset,
    required this.mousePosition,
    required this.time,
    required this.glowColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final maxDimension = math.max(size.width, size.height);

    // Normalize mouse input from center (-100 to 100 max influence)
    final mouseDx = (mousePosition.dx - center.dx).clamp(-400.0, 400.0) * 0.08;
    final mouseDy = (mousePosition.dy - center.dy).clamp(-400.0, 400.0) * 0.08;

    final paint = Paint()..style = PaintingStyle.fill;

    for (var particle in particles) {
      // Calculate dynamic Z depth based on scrollOffset
      // As scroll increases, particles get closer (decrease effective Z)
      double effectiveZ = particle.z - (scrollOffset * 0.002 * particle.speed);
      
      // Wrap depth around if it passes the camera (Z <= 0.2) or gets too far
      while (effectiveZ <= 0.2) {
        effectiveZ += 4.8;
      }
      while (effectiveZ > 5.0) {
        effectiveZ -= 4.8;
      }

      // Add gentle rotation/drift based on time
      final angle = time * 2 * math.pi * particle.speed;
      final driftX = math.sin(angle) * 0.05;
      final driftY = math.cos(angle) * 0.05;

      // Project 3D coordinate onto 2D viewport
      final double scaleFactor = 1.5 / effectiveZ;
      final double projectedX = center.dx + 
          (particle.x + driftX) * maxDimension * scaleFactor + 
          mouseDx * (5.0 - effectiveZ) * 0.4;
      final double projectedY = center.dy + 
          (particle.y + driftY) * maxDimension * scaleFactor + 
          mouseDy * (5.0 - effectiveZ) * 0.4;

      // Calculate fade and size based on depth layer
      final double currentSize = particle.size * scaleFactor;
      final double opacity = ((5.0 - effectiveZ) / 5.0).clamp(0.0, 1.0);

      paint.color = glowColor.withOpacity(opacity * 0.4);

      // Draw particle glow halo
      canvas.drawCircle(
        Offset(projectedX, projectedY),
        currentSize * 2.5,
        Paint()
          ..color = glowColor.withOpacity(opacity * 0.15)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8),
      );

      // Draw solid particle core
      canvas.drawCircle(Offset(projectedX, projectedY), currentSize, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _ParticlePainter oldDelegate) {
    return oldDelegate.scrollOffset != scrollOffset ||
        oldDelegate.mousePosition != mousePosition ||
        oldDelegate.time != time ||
        oldDelegate.glowColor != glowColor;
  }
}
