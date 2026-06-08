import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
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
            SingleChildScrollView(
              child: Glass3DCard(
                theme: activeTheme,
                width: (MediaQuery.of(context).size.width * 0.95).clamp(280.0, 420.0),
                height: 520,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      'Welcome Back',
                      style: activeTheme.headingStyle,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Sign in to build interactive workflows',
                      style: activeTheme.bodyStyle.copyWith(
                        color: activeTheme.bodyStyle.color?.withOpacity(0.7),
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 36),
                    _buildTextField(
                      controller: _emailController,
                      label: 'Email Address',
                      icon: Icons.alternate_email,
                      theme: activeTheme,
                    ),
                    const SizedBox(height: 20),
                    _buildTextField(
                      controller: _passwordController,
                      label: 'Password',
                      icon: Icons.lock_outline,
                      obscureText: true,
                      theme: activeTheme,
                    ),
                    const SizedBox(height: 32),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: activeTheme.glowColor,
                        foregroundColor: activeTheme.brightness == Brightness.dark
                            ? Colors.black
                            : Colors.white,
                        shadowColor: activeTheme.glowColor.withOpacity(0.5),
                        elevation: 8,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      onPressed: () {
                        context.go('/');
                      },
                      child: const Text(
                        'LOGIN',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1.5,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
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
                              color: activeTheme.bodyStyle.color?.withOpacity(0.6),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),

            // Floating Customization Bar
            Positioned(
              bottom: 24,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.05),
                  borderRadius: BorderRadius.circular(30),
                  border: Border.all(
                    color: Colors.white.withOpacity(0.1),
                  ),
                ),
                child: Row(
                  children: ThemePresetType.values.map((presetType) {
                    final preset = themePresets[presetType]!;
                    final isSelected = activeTheme.type == presetType;
                    return Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      child: ChoiceChip(
                        label: Text(preset.name),
                        selected: isSelected,
                        onSelected: (val) {
                          if (val) {
                            ref.read(themePresetProvider.notifier).setPreset(presetType);
                          }
                        },
                        backgroundColor: Colors.transparent,
                        selectedColor: activeTheme.glowColor.withOpacity(0.25),
                        labelStyle: TextStyle(
                          color: isSelected
                              ? activeTheme.glowColor
                              : activeTheme.bodyStyle.color?.withOpacity(0.6),
                          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                        ),
                      ),
                    );
                  }).toList(),
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
        color: Colors.white.withOpacity(0.03),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: theme.cardBorder.withOpacity(0.2),
        ),
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
          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        ),
      ),
    );
  }
}
