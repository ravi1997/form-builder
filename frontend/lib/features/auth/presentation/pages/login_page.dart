import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/design_system.dart';
import '../../../../core/theme/tokens.dart';
import '../../../../core/theme/theme_presets.dart';
import '../../../../core/widgets/glass_3d_card.dart';

class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  @override
  void dispose() {
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
            // Ambient background glow effects using ImageFiltered
            Positioned(
              top: -100,
              left: -100,
              child: ImageFiltered(
                imageFilter: ImageFilter.blur(sigmaX: 80, sigmaY: 80),
                child: Container(
                  width: 300,
                  height: 300,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: activeTheme.glowColor.withOpacity(0.15),
                  ),
                ),
              ),
            ),
            Positioned(
              bottom: -100,
              right: -100,
              child: ImageFiltered(
                imageFilter: ImageFilter.blur(sigmaX: 90, sigmaY: 90),
                child: Container(
                  width: 350,
                  height: 350,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: activeTheme.glowColor.withOpacity(0.12),
                  ),
                ),
              ),
            ),

            // Main 3D Card
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
                            'Welcome Back',
                            style: activeTheme.headingStyle,
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: AppSpacing.sm),
                          Text(
                            'Sign in to build interactive workflows',
                            style: activeTheme.bodyStyle.copyWith(
                              color: activeTheme.bodyStyle.color?.withOpacity(
                                0.72,
                              ),
                            ),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: AppSpacing.xxxl),
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
                              'LOGIN',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                letterSpacing: 1.2,
                              ),
                            ),
                          ),
                          const SizedBox(height: AppSpacing.lg),
                          Wrap(
                            alignment: WrapAlignment.center,
                            runSpacing: AppSpacing.xs,
                            spacing: AppSpacing.lg,
                            children: [
                              TextButton(
                                onPressed: () => context.go('/register'),
                                child: Text(
                                  'Create Account',
                                  style: TextStyle(
                                    color: activeTheme.glowColor,
                                  ),
                                ),
                              ),
                              TextButton(
                                onPressed: () => context.go('/reset-password'),
                                child: Text(
                                  'Forgot Password?',
                                  style: TextStyle(
                                    color: activeTheme.bodyStyle.color
                                        ?.withOpacity(0.6),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),

            // Floating Customization Bar
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
        ? 420.0
        : responsive.isTablet
        ? 460.0
        : responsive.isLaptop
        ? 480.0
        : 500.0;
    return (availableWidth -
            AppSurfaceStyles.pagePadding(responsive).horizontal)
        .clamp(280.0, maxWidth);
  }

  double _cardHeight(AppResponsiveInfo responsive) {
    if (responsive.isMobile) {
      return 540;
    }
    if (responsive.isTablet) {
      return 520;
    }
    if (responsive.isLaptop) {
      return 500;
    }
    return 520;
  }
}
