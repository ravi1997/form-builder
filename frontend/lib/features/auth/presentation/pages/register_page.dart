import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/design_system.dart';
import '../../../../core/theme/tokens.dart';
import '../../../../core/theme/theme_presets.dart';
import '../../../../core/widgets/glass_3d_card.dart';

class RegisterPage extends ConsumerStatefulWidget {
  const RegisterPage({super.key});

  @override
  ConsumerState<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends ConsumerState<RegisterPage> {
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final activeTheme = ref.watch(themePresetProvider);
    final responsive = context.responsive;
    final pagePadding = AppSurfaceStyles.pagePadding(responsive);
    final cardWidth = _cardWidth(MediaQuery.sizeOf(context).width, responsive);
    final cardHeight = _cardHeight(responsive);
    final bottomReserve = responsive.isMobile ? 104.0 : 88.0;

    return Scaffold(
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: activeTheme.bgGradient,
          ),
        ),
        child: Stack(
          alignment: Alignment.center,
          children: [
            // Ambient glows using ImageFiltered
            Positioned(
              top: -100,
              right: -100,
              child: ImageFiltered(
                imageFilter: ImageFilter.blur(sigmaX: 85, sigmaY: 85),
                child: Container(
                  width: 320,
                  height: 320,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: activeTheme.glowColor.withOpacity(0.14),
                  ),
                ),
              ),
            ),
            Positioned(
              bottom: -100,
              left: -100,
              child: ImageFiltered(
                imageFilter: ImageFilter.blur(sigmaX: 80, sigmaY: 80),
                child: Container(
                  width: 300,
                  height: 300,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: activeTheme.glowColor.withOpacity(0.12),
                  ),
                ),
              ),
            ),

            // Card
            Positioned.fill(
              child: Padding(
                padding: pagePadding.copyWith(
                  bottom: pagePadding.bottom + bottomReserve,
                ),
                child: Center(
                  child: SingleChildScrollView(
                    child: Glass3DCard(
                      theme: activeTheme,
                      width: cardWidth,
                      height: cardHeight,
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            'Create Account',
                            style: activeTheme.headingStyle,
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          Text(
                            'Join the next-generation workflow studio',
                            style: activeTheme.bodyStyle.copyWith(
                              color: activeTheme.bodyStyle.color?.withOpacity(
                                0.72,
                              ),
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: AppSpacing.xxxl),
                          _buildTextField(
                            controller: _nameController,
                            label: 'Full Name',
                            icon: Icons.person_outline,
                            theme: activeTheme,
                          ),
                          const SizedBox(height: AppSpacing.xl),
                          _buildTextField(
                            controller: _emailController,
                            label: 'Email Address',
                            icon: Icons.alternate_email,
                            theme: activeTheme,
                          ),
                          const SizedBox(height: AppSpacing.xl),
                          _buildTextField(
                            controller: _passwordController,
                            label: 'Password',
                            icon: Icons.lock_outline,
                            obscureText: true,
                            theme: activeTheme,
                          ),
                          const SizedBox(height: AppSpacing.xxxl),
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: activeTheme.glowColor,
                              foregroundColor: Theme.of(
                                context,
                              ).colorScheme.onPrimary,
                              shadowColor: activeTheme.glowColor.withOpacity(
                                0.5,
                              ),
                              elevation: 8,
                              padding: const EdgeInsets.symmetric(
                                vertical: AppSpacing.lg,
                              ),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(
                                  AppRadius.md,
                                ),
                              ),
                            ),
                            onPressed: () {
                              context.go('/');
                            },
                            child: const Text(
                              'REGISTER',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                letterSpacing: 1.2,
                              ),
                            ),
                          ),
                          const SizedBox(height: AppSpacing.lg),
                          Center(
                            child: TextButton(
                              onPressed: () => context.go('/login'),
                              child: Text(
                                'Already have an account? Login',
                                style: TextStyle(color: activeTheme.glowColor),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),

            // Theme Customizer selector
            Positioned.fill(
              child: SafeArea(
                top: false,
                child: Align(
                  alignment: Alignment.bottomCenter,
                  child: Padding(
                    padding: EdgeInsets.only(
                      left: pagePadding.left,
                      right: pagePadding.right,
                      bottom: responsive.isMobile
                          ? AppSpacing.lg
                          : AppSpacing.xl,
                    ),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.lg,
                        vertical: AppSpacing.sm,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.surfaceCard.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(AppRadius.full),
                        border: Border.all(
                          color: AppColors.borderSubtle.withOpacity(0.35),
                        ),
                      ),
                      child: Wrap(
                        alignment: WrapAlignment.center,
                        runSpacing: AppSpacing.xs,
                        children: ThemePresetType.values.map((presetType) {
                          final preset = themePresets[presetType]!;
                          final isSelected = activeTheme.type == presetType;
                          return Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: AppSpacing.xs,
                            ),
                            child: ChoiceChip(
                              label: Text(preset.name),
                              selected: isSelected,
                              onSelected: (val) {
                                if (val) {
                                  ref
                                      .read(themePresetProvider.notifier)
                                      .setPreset(presetType);
                                }
                              },
                              backgroundColor: AppColors.surfaceCard
                                  .withOpacity(0.12),
                              selectedColor: activeTheme.glowColor.withOpacity(
                                0.25,
                              ),
                              labelStyle: TextStyle(
                                color: isSelected
                                    ? activeTheme.glowColor
                                    : activeTheme.bodyStyle.color?.withOpacity(
                                        0.6,
                                      ),
                                fontWeight: isSelected
                                    ? FontWeight.bold
                                    : FontWeight.normal,
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTextField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    bool obscureText = false,
    required ThemePreset theme,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surfaceCard.withOpacity(0.08),
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.borderSubtle.withOpacity(0.32)),
      ),
      child: TextField(
        controller: controller,
        obscureText: obscureText,
        style: TextStyle(color: theme.bodyStyle.color),
        decoration: InputDecoration(
          labelText: label,
          labelStyle: TextStyle(color: theme.bodyStyle.color?.withOpacity(0.5)),
          prefixIcon: Icon(icon, color: theme.glowColor.withOpacity(0.7)),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 16,
          ),
        ),
      ),
    );
  }

  double _cardWidth(double availableWidth, AppResponsiveInfo responsive) {
    final maxWidth = responsive.isMobile
        ? 440.0
        : responsive.isTablet
        ? 480.0
        : responsive.isLaptop
        ? 500.0
        : 520.0;
    return (availableWidth -
            AppSurfaceStyles.pagePadding(responsive).horizontal)
        .clamp(280.0, maxWidth);
  }

  double _cardHeight(AppResponsiveInfo responsive) {
    if (responsive.isMobile) {
      return 560;
    }
    if (responsive.isTablet) {
      return 580;
    }
    if (responsive.isLaptop) {
      return 600;
    }
    return 620;
  }
}
