import 'package:flutter/material.dart';

import 'app_colors.dart';
import 'tokens.dart';

enum AppBreakpointTier { mobile, tablet, laptop, desktop, wide }

class AppResponsiveInfo {
  final double width;
  final AppBreakpointTier tier;

  const AppResponsiveInfo({required this.width, required this.tier});

  factory AppResponsiveInfo.fromWidth(double width) {
    if (width >= AppBreakpoints.desktop) {
      return AppResponsiveInfo(width: width, tier: AppBreakpointTier.wide);
    }
    if (width >= AppBreakpoints.laptop) {
      return AppResponsiveInfo(width: width, tier: AppBreakpointTier.desktop);
    }
    if (width >= AppBreakpoints.tablet) {
      return AppResponsiveInfo(width: width, tier: AppBreakpointTier.laptop);
    }
    if (width >= AppBreakpoints.mobile) {
      return AppResponsiveInfo(width: width, tier: AppBreakpointTier.tablet);
    }
    return AppResponsiveInfo(width: width, tier: AppBreakpointTier.mobile);
  }

  bool get isMobile => tier == AppBreakpointTier.mobile;
  bool get isTablet => tier == AppBreakpointTier.tablet;
  bool get isLaptop => tier == AppBreakpointTier.laptop;
  bool get isDesktop => tier == AppBreakpointTier.desktop;
  bool get isWide => tier == AppBreakpointTier.wide;
  bool get usesCompactBuilderLayout => isMobile || isTablet;
}

extension AppResponsiveBuildContext on BuildContext {
  AppResponsiveInfo get responsive {
    return AppResponsiveInfo.fromWidth(MediaQuery.sizeOf(this).width);
  }
}

class AppSurfaceStyles {
  AppSurfaceStyles._();

  static EdgeInsets pagePadding(AppResponsiveInfo responsive) {
    if (responsive.isMobile) {
      return const EdgeInsets.all(AppSpacing.lg);
    }
    if (responsive.isTablet) {
      return const EdgeInsets.all(AppSpacing.xl);
    }
    return const EdgeInsets.all(AppSpacing.xxl);
  }

  static BorderRadius radius(double value) {
    return BorderRadius.circular(value);
  }

  static BoxDecoration card({
    bool selected = false,
    Color? tint,
    double radiusValue = AppRadius.lg,
  }) {
    return BoxDecoration(
      color: tint ?? AppColors.surfaceCard,
      borderRadius: radius(radiusValue),
      border: Border.all(
        color: selected ? AppColors.brandPrimary : AppColors.borderSubtle,
        width: selected ? 1.5 : 1,
      ),
      boxShadow: const [
        BoxShadow(
          color: Color(0x0D0F172A),
          blurRadius: 14,
          offset: Offset(0, 4),
        ),
      ],
    );
  }

  static double builderLibraryWidth(AppResponsiveInfo responsive) {
    if (responsive.isMobile) {
      return double.infinity;
    }
    if (responsive.isTablet) {
      return AppDimensions.builderLibraryTabletWidth;
    }
    if (responsive.isLaptop) {
      return AppDimensions.builderLibraryWidth - 24;
    }
    if (responsive.isDesktop) {
      return AppDimensions.builderLibraryWidth;
    }
    return AppDimensions.builderLibraryWidth + 24;
  }

  static double builderPropertiesWidth(AppResponsiveInfo responsive) {
    if (responsive.isMobile) {
      return double.infinity;
    }
    if (responsive.isTablet) {
      return AppDimensions.builderPropertiesTabletWidth;
    }
    if (responsive.isLaptop) {
      return AppDimensions.builderPropertiesWidth - 24;
    }
    if (responsive.isDesktop) {
      return AppDimensions.builderPropertiesWidth;
    }
    return AppDimensions.builderPropertiesWidth + 24;
  }

  static double builderGap(AppResponsiveInfo responsive) {
    if (responsive.isMobile) {
      return AppSpacing.md;
    }
    if (responsive.isTablet) {
      return AppSpacing.lg;
    }
    return AppSpacing.xl;
  }

  static BoxDecoration insetCard({
    bool selected = false,
    Color? tint,
    double radiusValue = AppRadius.md,
  }) {
    return BoxDecoration(
      color: tint ?? AppColors.surfaceCardAlt,
      borderRadius: radius(radiusValue),
      border: Border.all(
        color: selected ? AppColors.brandPrimarySoft : AppColors.borderSubtle,
        width: selected ? 1.5 : 1,
      ),
    );
  }
}
