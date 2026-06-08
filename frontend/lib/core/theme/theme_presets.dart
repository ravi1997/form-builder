import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

enum ThemePresetType { glassyDark, neonCyberpunk, minimalistLight }

class ThemePreset {
  final String name;
  final ThemePresetType type;
  final Brightness brightness;
  final Color seedColor;
  final List<Color> bgGradient;
  final Color cardBg;
  final Color cardBorder;
  final Color glowColor;
  final TextStyle headingStyle;
  final TextStyle bodyStyle;

  const ThemePreset({
    required this.name,
    required this.type,
    required this.brightness,
    required this.seedColor,
    required this.bgGradient,
    required this.cardBg,
    required this.cardBorder,
    required this.glowColor,
    required this.headingStyle,
    required this.bodyStyle,
  });
}

final themePresets = {
  ThemePresetType.glassyDark: const ThemePreset(
    name: 'Glassy Dark',
    type: ThemePresetType.glassyDark,
    brightness: Brightness.dark,
    seedColor: Colors.deepPurple,
    bgGradient: [
      Color(0xFF0F0C20),
      Color(0xFF15102A),
      Color(0xFF06040A),
    ],
    cardBg: Color(0x1FEEF0FF),
    cardBorder: Color(0x33FFFFFF),
    glowColor: Colors.purpleAccent,
    headingStyle: TextStyle(
      color: Colors.white,
      fontSize: 24,
      fontWeight: FontWeight.bold,
      letterSpacing: 1.2,
      shadows: [
        Shadow(color: Colors.purpleAccent, blurRadius: 8),
      ],
    ),
    bodyStyle: TextStyle(
      color: Color(0xFFE0E0FF),
      fontSize: 14,
    ),
  ),
  ThemePresetType.neonCyberpunk: const ThemePreset(
    name: 'Neon Cyberpunk',
    type: ThemePresetType.neonCyberpunk,
    brightness: Brightness.dark,
    seedColor: Colors.teal,
    bgGradient: [
      Color(0xFF000508),
      Color(0xFF001016),
      Color(0xFF000000),
    ],
    cardBg: Color(0x1400FFAA),
    cardBorder: Color(0xFF00FFAA),
    glowColor: Color(0xFF00FFAA),
    headingStyle: TextStyle(
      color: Color(0xFF00FFAA),
      fontSize: 24,
      fontFamily: 'monospace',
      fontWeight: FontWeight.w900,
      letterSpacing: 2.0,
      shadows: [
        Shadow(color: Color(0xFF00FFAA), blurRadius: 10),
      ],
    ),
    bodyStyle: TextStyle(
      color: Color(0xFFC0FFF0),
      fontSize: 14,
      fontFamily: 'monospace',
    ),
  ),
  ThemePresetType.minimalistLight: const ThemePreset(
    name: 'Minimalist Light',
    type: ThemePresetType.minimalistLight,
    brightness: Brightness.light,
    seedColor: Colors.blueGrey,
    bgGradient: [
      Color(0xFFF5F7FA),
      Color(0xFFE4E8F0),
    ],
    cardBg: Color(0xE6FFFFFF),
    cardBorder: Color(0x1F000000),
    glowColor: Colors.blueGrey,
    headingStyle: TextStyle(
      color: Color(0xFF202A35),
      fontSize: 24,
      fontWeight: FontWeight.w800,
      letterSpacing: 0.5,
    ),
    bodyStyle: TextStyle(
      color: Color(0xFF4A5568),
      fontSize: 14,
    ),
  ),
};

class ThemePresetNotifier extends Notifier<ThemePreset> {
  @override
  ThemePreset build() {
    return themePresets[ThemePresetType.glassyDark]!;
  }

  void setPreset(ThemePresetType type) {
    state = themePresets[type]!;
  }
}

final themePresetProvider = NotifierProvider<ThemePresetNotifier, ThemePreset>(() {
  return ThemePresetNotifier();
});
