import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/theme/theme_presets.dart';
import '../../../../core/widgets/glass_3d_card.dart';
import '../../../../core/widgets/parallax_particle_background.dart';

class HomePage extends ConsumerStatefulWidget {
  const HomePage({super.key});

  @override
  ConsumerState<HomePage> createState() => _HomePageState();
}

class _HomePageState extends ConsumerState<HomePage> {
  final ScrollController _scrollController = ScrollController();
  double _scrollOffset = 0.0;
  Offset _mousePosition = Offset.zero;

  final List<Map<String, dynamic>> _launcherItems = [
    {
      'title': 'Form Editor',
      'description': 'Build robust DAG structures, version forms, and handle conflicts.',
      'icon': Icons.alt_route_rounded,
      'path': '/form-builder',
    },
    {
      'title': 'Dashboard Builder',
      'description': 'Design free-form visual canvases with real-time analytics integrations.',
      'icon': Icons.dashboard_customize_rounded,
      'path': '/dashboard-builder/default_db',
    },
    {
      'title': 'Offline Sync Center',
      'description': 'Monitor SQLite caching and synchronize response data safely.',
      'icon': Icons.cloud_sync_rounded,
      'path': '/',
    },
  ];

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    setState(() {
      _scrollOffset = _scrollController.offset;
    });
  }

  @override
  Widget build(BuildContext context) {
    final activeTheme = ref.watch(themePresetProvider);

    return Scaffold(
      body: MouseRegion(
        onHover: (event) {
          setState(() {
            _mousePosition = event.position;
          });
        },
        child: Container(
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
            children: [
              // 3D Parallax Particle Layer
              Positioned.fill(
                child: ParallaxParticleBackground(
                  scrollOffset: _scrollOffset,
                  mousePosition: _mousePosition,
                  themeGlowColor: activeTheme.glowColor,
                ),
              ),

              // Ambient blur background glows
              Positioned(
                top: 50,
                left: 100,
                child: ImageFiltered(
                  imageFilter: ImageFilter.blur(sigmaX: 90, sigmaY: 90),
                  child: Container(
                    width: 250,
                    height: 250,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: activeTheme.glowColor.withOpacity(0.08),
                    ),
                  ),
                ),
              ),

              SafeArea(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Header Area
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 24),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Form Builder Engine',
                                style: activeTheme.headingStyle.copyWith(fontSize: 28),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'Next-Gen Workflow & Analytics Studio',
                                style: activeTheme.bodyStyle.copyWith(
                                  color: activeTheme.bodyStyle.color?.withOpacity(0.6),
                                ),
                              ),
                            ],
                          ),
                          Row(
                            children: [
                              IconButton(
                                icon: const Icon(Icons.settings_suggest_outlined),
                                color: activeTheme.glowColor,
                                onPressed: () {},
                              ),
                              const SizedBox(width: 8),
                              ElevatedButton.icon(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.white.withOpacity(0.08),
                                  foregroundColor: activeTheme.bodyStyle.color,
                                  side: BorderSide(
                                    color: activeTheme.cardBorder.withOpacity(0.2),
                                  ),
                                  shape: RoundedRectangleBorder(
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                ),
                                onPressed: () => context.go('/login'),
                                icon: const Icon(Icons.logout_rounded, size: 18),
                                label: const Text('Logout'),
                              ),
                            ],
                          )
                        ],
                      ),
                    ),

                    const SizedBox(height: 16),

                    // Centered 3D Card Deck Wheel
                    Expanded(
                      child: Center(
                        child: SizedBox(
                          height: 380,
                          child: ListWheelScrollView.useDelegate(
                            controller: FixedExtentScrollController(),
                            itemExtent: 320,
                            perspective: 0.003,
                            diameterRatio: 1.8,
                            physics: const BouncingScrollPhysics(),
                            onSelectedItemChanged: (index) {},
                            childDelegate: ListWheelChildBuilderDelegate(
                              builder: (context, index) {
                                if (index < 0 || index >= _launcherItems.length) return null;
                                final item = _launcherItems[index];
                                return Center(
                                  child: SizedBox(
                                    width: (MediaQuery.of(context).size.width * 0.9).clamp(280.0, 480.0),
                                    height: 280,
                                    child: _build3DCard(
                                      title: item['title'],
                                      description: item['description'],
                                      icon: item['icon'],
                                      theme: activeTheme,
                                      onTap: () {
                                        if (item['path'] != null) {
                                          context.go(item['path']);
                                        }
                                      },
                                    ),
                                  ),
                                );
                              },
                              childCount: _launcherItems.length,
                            ),
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: 16),

                    // Theme dynamic settings / customization presets row
                    Padding(
                      padding: const EdgeInsets.only(bottom: 24),
                      child: Center(
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.04),
                            borderRadius: BorderRadius.circular(28),
                            border: Border.all(
                              color: Colors.white.withOpacity(0.08),
                            ),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.palette_outlined, color: activeTheme.glowColor, size: 20),
                              const SizedBox(width: 12),
                              Text(
                                'Visual Customizer:',
                                style: TextStyle(
                                  color: activeTheme.bodyStyle.color?.withOpacity(0.8),
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(width: 16),
                              Row(
                                children: ThemePresetType.values.map((presetType) {
                                  final preset = themePresets[presetType]!;
                                  final isSelected = activeTheme.type == presetType;
                                  return Padding(
                                    padding: const EdgeInsets.symmetric(horizontal: 6),
                                    child: ChoiceChip(
                                      label: Text(preset.name),
                                      selected: isSelected,
                                      onSelected: (val) {
                                        if (val) {
                                          ref.read(themePresetProvider.notifier).setPreset(presetType);
                                        }
                                      },
                                      backgroundColor: Colors.transparent,
                                      selectedColor: activeTheme.glowColor.withOpacity(0.2),
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
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _build3DCard({
    required String title,
    required String description,
    required IconData icon,
    required ThemePreset theme,
    required VoidCallback onTap,
  }) {
    return Glass3DCard(
      theme: theme,
      width: double.infinity,
      height: double.infinity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: theme.glowColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(icon, color: theme.glowColor, size: 28),
              ),
              IconButton(
                icon: const Icon(Icons.arrow_forward_rounded),
                color: theme.bodyStyle.color?.withOpacity(0.5),
                hoverColor: theme.glowColor.withOpacity(0.2),
                onPressed: onTap,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: theme.headingStyle.copyWith(fontSize: 20),
              ),
              const SizedBox(height: 8),
              Text(
                description,
                style: theme.bodyStyle.copyWith(
                  color: theme.bodyStyle.color?.withOpacity(0.65),
                  height: 1.4,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
