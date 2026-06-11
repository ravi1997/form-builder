import 'package:flutter/material.dart';

import 'app_colors.dart';
import 'tokens.dart';

ThemeData buildAppTheme({required Brightness brightness}) {
  final colorScheme = ColorScheme.fromSeed(
    seedColor: AppColors.brandPrimary,
    brightness: brightness,
    primary: AppColors.brandPrimary,
    secondary: AppColors.brandPrimaryStrong,
    surface: brightness == Brightness.dark
        ? const Color(0xFF111827)
        : AppColors.surfaceCard,
    surfaceContainerHighest: brightness == Brightness.dark
        ? const Color(0xFF1F2937)
        : AppColors.surfaceCardAlt,
  );

  final baseTheme = ThemeData(
    useMaterial3: true,
    colorScheme: colorScheme,
    brightness: brightness,
    scaffoldBackgroundColor: brightness == Brightness.dark
        ? const Color(0xFF0F172A)
        : AppColors.surfaceCanvas,
  );

  return baseTheme.copyWith(
    appBarTheme: AppBarTheme(
      centerTitle: false,
      backgroundColor: brightness == Brightness.dark
          ? const Color(0xFF111827)
          : AppColors.surfaceCard,
      foregroundColor: colorScheme.onSurface,
      elevation: 0,
      scrolledUnderElevation: 0,
      surfaceTintColor: Colors.transparent,
    ),
    cardTheme: CardThemeData(
      color: brightness == Brightness.dark
          ? const Color(0xFF111827)
          : AppColors.surfaceCard,
      elevation: AppElevation.sm,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        side: BorderSide(
          color: brightness == Brightness.dark
              ? const Color(0xFF374151)
              : AppColors.borderSubtle,
        ),
      ),
      margin: EdgeInsets.zero,
    ),
    dialogTheme: DialogThemeData(
      backgroundColor: brightness == Brightness.dark
          ? const Color(0xFF111827)
          : AppColors.surfaceCard,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.xl),
      ),
    ),
    dividerTheme: DividerThemeData(
      color: brightness == Brightness.dark
          ? const Color(0xFF374151)
          : AppColors.builderDivider,
      thickness: 1,
      space: AppSpacing.lg,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: brightness == Brightness.dark
          ? const Color(0xFF1F2937)
          : AppColors.surfaceCardAlt,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.md,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: BorderSide(
          color: brightness == Brightness.dark
              ? const Color(0xFF374151)
              : AppColors.borderSubtle,
        ),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: BorderSide(
          color: brightness == Brightness.dark
              ? const Color(0xFF374151)
              : AppColors.borderSubtle,
        ),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: const BorderSide(color: AppColors.brandPrimary, width: 1.4),
      ),
    ),
    listTileTheme: ListTileThemeData(
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      contentPadding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.xs,
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: brightness == Brightness.dark
          ? const Color(0xFF1F2937)
          : AppColors.surfaceCardAlt,
      selectedColor: AppColors.brandPrimarySoft,
      side: BorderSide(
        color: brightness == Brightness.dark
            ? const Color(0xFF374151)
            : AppColors.borderSubtle,
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
      labelStyle: TextStyle(color: colorScheme.onSurface),
    ),
    textTheme: baseTheme.textTheme.apply(
      bodyColor: colorScheme.onSurface,
      displayColor: colorScheme.onSurface,
    ),
  );
}
